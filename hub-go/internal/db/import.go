package db

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"time"
)

type ImportTable struct {
	Rows   int    `json:"rows"`
	SHA256 string `json:"sha256"`
}
type ImportSummary struct {
	Status         string                 `json:"status"`
	Tables         map[string]ImportTable `json:"tables"`
	SourceRetained bool                   `json:"source_retained"`
}

// CopySQLiteToPostgres takes a consistent SQLite backup, upgrades only that temporary
// snapshot, and copies its rows in a single PostgreSQL transaction into an empty hub.
func CopySQLiteToPostgres(sourcePath, targetURL string, now time.Time) (ImportSummary, error) {
	if !isPostgres(targetURL) {
		return ImportSummary{}, fmt.Errorf("대상은 PostgreSQL URL이어야 한다")
	}
	tmp, err := os.MkdirTemp("", "workflow-hub-import-")
	if err != nil {
		return ImportSummary{}, err
	}
	defer os.RemoveAll(tmp)
	snapshot := filepath.Join(tmp, "snapshot.db")
	if err := Backup(sourcePath, snapshot); err != nil {
		return ImportSummary{}, err
	}
	if _, err := OpenDB(snapshot, now); err != nil {
		return ImportSummary{}, err
	}
	if _, err := OpenDB(targetURL, now); err != nil {
		return ImportSummary{}, err
	}
	src, err := Connect(snapshot)
	if err != nil {
		return ImportSummary{}, err
	}
	defer src.Close()
	dst, err := Connect(targetURL)
	if err != nil {
		return ImportSummary{}, err
	}
	defer dst.Close()
	rows, err := src.Query("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY rowid")
	if err != nil {
		return ImportSummary{}, err
	}
	var tables []string
	for rows.Next() {
		var name string
		if err := rows.Scan(&name); err != nil {
			rows.Close()
			return ImportSummary{}, err
		}
		tables = append(tables, name)
	}
	if err := rows.Err(); err != nil {
		rows.Close()
		return ImportSummary{}, err
	}
	rows.Close()
	targetTables, err := dst.Query("SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE' AND table_name <> 'meta'")
	if err != nil {
		return ImportSummary{}, err
	}
	var existingTables []string
	for targetTables.Next() {
		var name string
		if err := targetTables.Scan(&name); err != nil {
			targetTables.Close()
			return ImportSummary{}, err
		}
		existingTables = append(existingTables, name)
	}
	if err := targetTables.Err(); err != nil {
		targetTables.Close()
		return ImportSummary{}, err
	}
	targetTables.Close()
	for _, table := range existingTables {
		var count int64
		if err := dst.QueryRow("SELECT count(*) FROM \"" + table + "\"").Scan(&count); err != nil {
			return ImportSummary{}, err
		}
		if count > 0 {
			return ImportSummary{}, &Error{Status: 409, Code: "postgres_target_not_empty", Message: "PostgreSQL 대상에 이미 데이터가 있어요 — 빈 대상으로 다시 시도해요", Detail: map[string]any{"table": table}}
		}
	}
	tx, err := dst.Begin()
	if err != nil {
		return ImportSummary{}, err
	}
	defer func() { _ = tx.Rollback() }()
	summary := ImportSummary{Status: "ok", Tables: map[string]ImportTable{}, SourceRetained: true}
	for _, table := range tables {
		colRows, err := src.Query("PRAGMA table_info(\"" + table + "\")")
		if err != nil {
			return ImportSummary{}, err
		}
		type col struct {
			name string
			pk   int
		}
		var cols []col
		for colRows.Next() {
			var cid, notnull, pk int
			var name, typ string
			var def any
			if err := colRows.Scan(&cid, &name, &typ, &notnull, &def, &pk); err != nil {
				colRows.Close()
				return ImportSummary{}, err
			}
			cols = append(cols, col{name, pk})
		}
		colRows.Close()
		order := append([]col(nil), cols...)
		withPK := false
		for _, c := range cols {
			if c.pk > 0 {
				withPK = true
			}
		}
		if withPK {
			sort.Slice(order, func(i, j int) bool { return order[i].pk < order[j].pk })
		}
		quote := func(s string) string { return `"` + strings.ReplaceAll(s, `"`, `""`) + `"` }
		colNames, sortNames := make([]string, len(cols)), make([]string, len(order))
		for i, c := range cols {
			colNames[i] = quote(c.name)
		}
		for i, c := range order {
			sortNames[i] = quote(c.name)
		}
		placeholders := make([]string, len(cols))
		for i := range placeholders {
			placeholders[i] = "?"
		}
		insert := "INSERT INTO " + quote(table) + " (" + strings.Join(colNames, ",") + ") VALUES (" + strings.Join(placeholders, ",") + ")"
		if table == "meta" {
			insert += " ON CONFLICT(key) DO UPDATE SET value=excluded.value"
		}
		selectSQL := "SELECT " + strings.Join(colNames, ",") + " FROM " + quote(table) + " ORDER BY " + strings.Join(sortNames, ",")
		srcRows, err := src.Query(selectSQL)
		if err != nil {
			return ImportSummary{}, err
		}
		hash := sha256.New()
		count := 0
		for srcRows.Next() {
			vals := make([]any, len(cols))
			ptrs := make([]any, len(cols))
			for i := range vals {
				ptrs[i] = &vals[i]
			}
			if err := srcRows.Scan(ptrs...); err != nil {
				srcRows.Close()
				return ImportSummary{}, err
			}
			vals = canonicalValues(vals)
			if _, err := tx.Exec(insert, vals...); err != nil {
				srcRows.Close()
				return ImportSummary{}, err
			}
			b, _ := json.Marshal(vals)
			hash.Write(b)
			hash.Write([]byte{'\n'})
			count++
		}
		if err := srcRows.Err(); err != nil {
			srcRows.Close()
			return ImportSummary{}, err
		}
		srcRows.Close()
		verifyRows, err := tx.Query(selectSQL)
		if err != nil {
			return ImportSummary{}, err
		}
		verifyHash := sha256.New()
		verifyCount := 0
		for verifyRows.Next() {
			vals := make([]any, len(cols))
			ptrs := make([]any, len(cols))
			for i := range vals {
				ptrs[i] = &vals[i]
			}
			if err := verifyRows.Scan(ptrs...); err != nil {
				verifyRows.Close()
				return ImportSummary{}, err
			}
			vals = canonicalValues(vals)
			b, _ := json.Marshal(vals)
			verifyHash.Write(b)
			verifyHash.Write([]byte{'\n'})
			verifyCount++
		}
		if err := verifyRows.Err(); err != nil {
			verifyRows.Close()
			return ImportSummary{}, err
		}
		verifyRows.Close()
		if count != verifyCount || !equalBytes(hash.Sum(nil), verifyHash.Sum(nil)) {
			return ImportSummary{}, &Error{Status: 500, Code: "postgres_import_mismatch", Message: "SQLite와 PostgreSQL 데이터 검증이 맞지 않아요 — 이관을 롤백해요", Detail: map[string]any{"table": table, "source_rows": count, "target_rows": verifyCount}}
		}
		summary.Tables[table] = ImportTable{Rows: count, SHA256: hex.EncodeToString(hash.Sum(nil))}
	}
	if _, err := tx.Exec("SELECT setval(pg_get_serial_sequence('public.event','seq'), COALESCE(MAX(seq),1), MAX(seq) IS NOT NULL) FROM event"); err != nil {
		return ImportSummary{}, err
	}
	if err := tx.Commit(); err != nil {
		return ImportSummary{}, err
	}
	return summary, nil
}

func canonicalValues(values []any) []any {
	for i, value := range values {
		if b, ok := value.([]byte); ok {
			values[i] = string(b)
		}
	}
	return values
}

func equalBytes(a, b []byte) bool {
	if len(a) != len(b) {
		return false
	}
	var diff byte
	for i := range a {
		diff |= a[i] ^ b[i]
	}
	return diff == 0
}
