package db

import (
	"context"
	"database/sql"
	"errors"
	"fmt"
	"net/url"
	"os"
	"path/filepath"
	"runtime"
	"strconv"
	"strings"
	"time"

	"modernc.org/sqlite"
)

// Error matches HubError fields so internal/store can translate cleanly into HTTP/tool errors.
type Error struct {
	Status  int
	Code    string
	Message string
	Detail  map[string]any
}

func (e *Error) Error() string {
	return e.Code + ": " + e.Message
}

func FormatISO(t time.Time) string {
	return t.Truncate(time.Second).Format("2006-01-02T15:04:05-07:00")
}

func quoteSQL(value string) string {
	return "'" + strings.ReplaceAll(value, "'", "''") + "'"
}

func dsnForPath(dbPath string) string {
	abs := dbPath
	if a, err := filepath.Abs(dbPath); err == nil {
		abs = a
	}
	return dsnForAbsolutePath(abs, runtime.GOOS == "windows")
}

// dsnForAbsolutePath builds a file URI from an absolute filesystem path. Windows drive paths
// need a leading slash in the URI path (`file:///C:/...`); without it URL serialization produces
// `file:C:/...`, which modernc SQLite interprets as a relative URI.
func dsnForAbsolutePath(abs string, windows bool) string {
	path := filepath.ToSlash(abs)
	if windows && len(path) >= 3 && isDriveLetter(path[0]) && path[1] == ':' && path[2] == '/' {
		path = "/" + path
	}
	u := url.URL{
		Scheme: "file",
		Path:   path,
	}
	q := url.Values{}
	q.Add("_txlock", "immediate")
	q.Add("_pragma", "foreign_keys(1)")
	q.Add("_pragma", "busy_timeout(10000)")
	u.RawQuery = q.Encode()
	return u.String()
}

func isDriveLetter(c byte) bool {
	return (c >= 'A' && c <= 'Z') || (c >= 'a' && c <= 'z')
}

// Connect opens a SQLite connection pool configured with foreign_keys=ON, busy_timeout=10000,
// and immediate transactions by default.
func Connect(dbPath string) (*sql.DB, error) {
	conn, err := sql.Open("sqlite", dsnForPath(dbPath))
	if err != nil {
		return nil, err
	}
	// Serialize writes in-process on a single pool slot to prevent SQLITE_BUSY between goroutines.
	conn.SetMaxOpenConns(1)
	if _, err := conn.Exec("PRAGMA foreign_keys = ON; PRAGMA busy_timeout = 10000;"); err != nil {
		_ = conn.Close()
		return nil, err
	}
	return conn, nil
}

// SchemaVersion reads meta.schema_version; returns 0 when the meta table or key does not exist yet.
func SchemaVersion(conn *sql.DB) (int, error) {
	var present int
	err := conn.QueryRow("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'meta'").Scan(&present)
	if errors.Is(err, sql.ErrNoRows) {
		return 0, nil
	}
	if err != nil {
		return 0, err
	}
	var raw string
	err = conn.QueryRow("SELECT value FROM meta WHERE key = 'schema_version'").Scan(&raw)
	if errors.Is(err, sql.ErrNoRows) {
		return 0, nil
	}
	if err != nil {
		return 0, err
	}
	v, err := strconv.Atoi(raw)
	if err != nil {
		return 0, err
	}
	return v, nil
}

// Backup performs a consistent SQLite online backup from srcPath to outPath (requiring outPath not to exist).
func Backup(srcPath, outPath string) error {
	if _, err := os.Stat(outPath); err == nil {
		return &Error{
			Status:  409,
			Code:    "backup_target_exists",
			Message: "백업 대상이 이미 있다: " + outPath,
		}
	} else if !errors.Is(err, os.ErrNotExist) {
		return err
	}
	if err := os.MkdirAll(filepath.Dir(outPath), 0o755); err != nil {
		return err
	}

	srcDB, err := sql.Open("sqlite", dsnForPath(srcPath))
	if err != nil {
		return err
	}
	defer srcDB.Close()

	type backuper interface {
		NewBackup(dstURI string) (*sqlite.Backup, error)
	}

	ctx := context.Background()
	c, err := srcDB.Conn(ctx)
	if err != nil {
		return err
	}
	defer c.Close()

	return c.Raw(func(driverConn any) error {
		bk, ok := driverConn.(backuper)
		if !ok {
			return fmt.Errorf("sqlite driver does not implement NewBackup")
		}
		bck, err := bk.NewBackup(outPath)
		if err != nil {
			return err
		}
		for more := true; more; {
			more, err = bck.Step(-1)
			if err != nil {
				_ = bck.Finish()
				return err
			}
		}
		return bck.Finish()
	})
}

// OpenDB brings dbPath up to LatestVersion() using Migrations[current:], creating pre-migration
// backup copies when upgrading existing databases (current > 0).
func OpenDB(dbPath string, now time.Time) ([]string, error) {
	if err := os.MkdirAll(filepath.Dir(dbPath), 0o755); err != nil {
		return nil, err
	}
	conn, err := Connect(dbPath)
	if err != nil {
		return nil, err
	}
	_, walErr := conn.Exec("PRAGMA journal_mode = WAL")
	current, verErr := SchemaVersion(conn)
	_ = conn.Close()
	if walErr != nil {
		return nil, walErr
	}
	if verErr != nil {
		return nil, verErr
	}

	latest := LatestVersion()
	if current > latest {
		return nil, &Error{
			Status:  500,
			Code:    "db_newer_than_hub",
			Message: fmt.Sprintf("DB 판 %d 이 이 허브가 아는 최신 판 %d 보다 새롭다 — 허브를 올린다", current, latest),
			Detail:  map[string]any{"db_version": current, "hub_version": latest},
		}
	}

	var copies []string
	for n := current + 1; n <= latest; n++ {
		if current > 0 {
			stamp := now.UTC().Format("20060102T150405Z")
			copyPath := filepath.Join(filepath.Dir(dbPath), fmt.Sprintf("%s.pre-v%d-%s", filepath.Base(dbPath), n, stamp))
			if err := Backup(dbPath, copyPath); err != nil {
				return copies, err
			}
			copies = append(copies, copyPath)
		}
		if err := applyMigration(dbPath, n, now); err != nil {
			return copies, err
		}
	}
	return copies, nil
}

func applyMigration(dbPath string, n int, now time.Time) error {
	meta := fmt.Sprintf(
		"INSERT INTO meta (key, value) VALUES ('schema_version', %s) ON CONFLICT(key) DO UPDATE SET value = excluded.value;\n",
		quoteSQL(strconv.Itoa(n)),
	)
	if n == 1 {
		meta += fmt.Sprintf("INSERT INTO meta (key, value) VALUES ('created_at', %s);\n", quoteSQL(FormatISO(now)))
	}
	// Run using explicit BEGIN IMMEDIATE / COMMIT so the entire migration is atomic.
	conn, err := Connect(dbPath)
	if err != nil {
		return err
	}
	defer conn.Close()

	if _, err := conn.Exec("BEGIN IMMEDIATE"); err != nil {
		return err
	}
	if _, err := conn.Exec(Migrations[n-1] + "\n" + meta); err != nil {
		_, _ = conn.Exec("ROLLBACK")
		return err
	}
	_, err = conn.Exec("COMMIT")
	return err
}
