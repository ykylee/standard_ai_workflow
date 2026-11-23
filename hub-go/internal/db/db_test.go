package db

import (
	"errors"
	"net/url"
	"os"
	"path/filepath"
	"strings"
	"sync/atomic"
	"testing"
	"time"
)

func testNow() time.Time {
	return time.Date(2026, 11, 22, 12, 0, 0, 0, time.UTC)
}

func TestDSNForWindowsDrivePathIsAbsoluteURI(t *testing.T) {
	dsn := dsnForAbsolutePath("C:/Users/A User/워크 폴더/hub.db", true)
	u, err := url.Parse(dsn)
	if err != nil {
		t.Fatalf("url.Parse(%q): %v", dsn, err)
	}
	if u.Scheme != "file" || u.Host != "" || u.Path != "/C:/Users/A User/워크 폴더/hub.db" {
		t.Fatalf("Windows DSN URI = scheme %q host %q path %q; want file URI with /C:/ drive path", u.Scheme, u.Host, u.Path)
	}
	if !strings.HasPrefix(dsn, "file:///C:/") {
		t.Fatalf("Windows DSN = %q; want file:///C:/...", dsn)
	}
	q := u.Query()
	if q.Get("_txlock") != "immediate" || len(q["_pragma"]) != 2 {
		t.Fatalf("Windows DSN query options lost: %v", q)
	}
}

func TestPostgresSQLCompatibilityRewrite(t *testing.T) {
	got := pgSQL("INSERT OR IGNORE INTO inbox_message(id, body) VALUES (?, '?') AND callsign IS NOT ? ORDER BY rowid")
	want := "INSERT INTO inbox_message(id, body) VALUES ($1, '?') AND callsign IS DISTINCT FROM $2 ORDER BY ctid ON CONFLICT DO NOTHING"
	if got != want {
		t.Fatalf("pgSQL rewrite\n got: %s\nwant: %s", got, want)
	}
}

func TestDSNForUnixPathRemainsAbsoluteURI(t *testing.T) {
	dsn := dsnForAbsolutePath("/var/lib/workflow hub/hub.db", false)
	u, err := url.Parse(dsn)
	if err != nil {
		t.Fatalf("url.Parse(%q): %v", dsn, err)
	}
	if u.Scheme != "file" || u.Host != "" || u.Path != "/var/lib/workflow hub/hub.db" {
		t.Fatalf("Unix DSN URI = scheme %q host %q path %q", u.Scheme, u.Host, u.Path)
	}
}

func TestMigrationsAndAtomicity(t *testing.T) {
	dir := t.TempDir()
	dbPath := filepath.Join(dir, "hub.db")

	c1, err := OpenDB(dbPath, testNow())
	if err != nil {
		t.Fatalf("initial OpenDB failed: %v", err)
	}
	if len(c1) != 0 {
		t.Fatalf("expected 0 backup copies on fresh DB, got %v", c1)
	}
	c2, err := OpenDB(dbPath, testNow())
	if err != nil {
		t.Fatalf("second OpenDB failed: %v", err)
	}
	if len(c2) != 0 {
		t.Fatalf("expected 0 backup copies on up-to-date DB, got %v", c2)
	}

	conn, err := Connect(dbPath)
	if err != nil {
		t.Fatalf("Connect failed: %v", err)
	}
	v, err := SchemaVersion(conn)
	if err != nil || v != LatestVersion() {
		conn.Close()
		t.Fatalf("SchemaVersion=%d err=%v, want %d", v, err, LatestVersion())
	}
	var fk int
	if err := conn.QueryRow("PRAGMA foreign_keys").Scan(&fk); err != nil || fk != 1 {
		conn.Close()
		t.Fatalf("expected foreign_keys=1, got %d (err=%v)", fk, err)
	}
	conn.Close()

	// DB newer than hub must be rejected
	newer := filepath.Join(dir, "newer.db")
	if _, err := OpenDB(newer, testNow()); err != nil {
		t.Fatalf("OpenDB newer failed: %v", err)
	}
	nConn, err := Connect(newer)
	if err != nil {
		t.Fatalf("Connect newer failed: %v", err)
	}
	if _, err := nConn.Exec("UPDATE meta SET value = '99' WHERE key = 'schema_version'"); err != nil {
		nConn.Close()
		t.Fatalf("update newer meta failed: %v", err)
	}
	nConn.Close()

	_, err = OpenDB(newer, testNow())
	var dbErr *Error
	if !errors.As(err, &dbErr) || dbErr.Code != "db_newer_than_hub" {
		t.Fatalf("expected db_newer_than_hub error, got %v", err)
	}

	// Pre-migration copy + rollback atomicity when appending a broken migration
	saved := make([]string, len(Migrations))
	copy(saved, Migrations)
	t.Cleanup(func() { Migrations = saved })

	Migrations = append(Migrations, "CREATE TABLE probe_ok (x INTEGER);")
	copies, err := OpenDB(dbPath, testNow())
	if err != nil {
		t.Fatalf("v+1 migration failed: %v", err)
	}
	if len(copies) != 1 {
		t.Fatalf("expected 1 backup copy, got %v", copies)
	}
	if _, err := os.Stat(copies[0]); err != nil {
		t.Fatalf("backup copy missing: %v", err)
	}
	conn, err = Connect(dbPath)
	if err != nil {
		t.Fatalf("Connect after v+1 failed: %v", err)
	}
	if v, err = SchemaVersion(conn); err != nil || v != len(saved)+1 {
		conn.Close()
		t.Fatalf("got version=%d err=%v, want %d", v, err, len(saved)+1)
	}
	conn.Close()

	Migrations = append(Migrations, "CREATE TABLE probe_half (x INTEGER); THIS IS NOT SQL;")
	_, err = OpenDB(dbPath, testNow())
	if err == nil {
		t.Fatalf("expected broken migration to fail")
	}
	conn, err = Connect(dbPath)
	if err != nil {
		t.Fatalf("Connect after failed migration error: %v", err)
	}
	defer conn.Close()
	if v, err = SchemaVersion(conn); err != nil || v != len(saved)+1 {
		t.Fatalf("expected version %d preserved after rollback, got %d (err=%v)", len(saved)+1, v, err)
	}
	var dummy int
	err = conn.QueryRow("SELECT 1 FROM sqlite_master WHERE name = 'probe_half'").Scan(&dummy)
	if err == nil {
		t.Fatalf("probe_half should have been rolled back")
	}
}

func TestOnlineBackupWhileWriting(t *testing.T) {
	dir := t.TempDir()
	dbPath := filepath.Join(dir, "live.db")
	if _, err := OpenDB(dbPath, testNow()); err != nil {
		t.Fatalf("OpenDB failed: %v", err)
	}
	conn, err := Connect(dbPath)
	if err != nil {
		t.Fatalf("Connect failed: %v", err)
	}
	defer conn.Close()

	if _, err := conn.Exec(
		`INSERT INTO project (id, display_name, owner_callsign, created_at) VALUES ('P-1', 'demo', 'owner-a', '2026-11-22T12:00:00+00:00')`,
	); err != nil {
		t.Fatalf("seed project failed: %v", err)
	}

	var stop atomic.Bool
	done := make(chan error, 1)
	go func() {
		wConn, err := Connect(dbPath)
		if err != nil {
			done <- err
			return
		}
		defer wConn.Close()
		i := 0
		for !stop.Load() {
			i++
			id := "T-" + time.Now().Format("150405") + "-" + string(rune('a'+(i%26))) + "-" + string(rune('0'+(i%10)))
			_, _ = wConn.Exec(
				`INSERT OR IGNORE INTO task (project_id, id, title, status, created_by, created_at, updated_at) VALUES ('P-1', ?, 'title', 'planned', 'owner-a', '2026-11-22T12:00:00+00:00', '2026-11-22T12:00:00+00:00')`,
				id,
			)
		}
		done <- nil
	}()

	time.Sleep(50 * time.Millisecond)
	outPath := filepath.Join(dir, "backup.db")
	if err := Backup(dbPath, outPath); err != nil {
		stop.Store(true)
		<-done
		t.Fatalf("Backup failed: %v", err)
	}
	// Duplicate target must return 409 backup_target_exists
	if err := Backup(dbPath, outPath); err == nil {
		stop.Store(true)
		<-done
		t.Fatalf("expected backup_target_exists")
	}
	stop.Store(true)
	if wErr := <-done; wErr != nil {
		t.Fatalf("writer failed: %v", wErr)
	}

	bConn, err := Connect(outPath)
	if err != nil {
		t.Fatalf("Connect backup failed: %v", err)
	}
	defer bConn.Close()
	var integrity string
	if err := bConn.QueryRow("PRAGMA integrity_check").Scan(&integrity); err != nil || integrity != "ok" {
		t.Fatalf("integrity_check=%q err=%v", integrity, err)
	}
}
