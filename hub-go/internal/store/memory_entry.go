package store

import (
	"database/sql"
	"encoding/json"
	"errors"
	"fmt"
	"regexp"
	"strings"
	"time"
	"unicode/utf8"

	"github.com/ykylee/standard_ai_workflow/hub-go/internal/db"
)

// memory_index entry — 1.x MemoryEntry 스키마 (common/schemas/memory_index.py) 와 같은 칸 · 제약.

var memoryEntryID = regexp.MustCompile(`^MEM-\d{4}-\d{2}-\d{2}-\d{3}$`)

func entryError(field, message string) error {
	return InvalidField("entry."+field, "1.x memory entry 스키마 — "+message)
}

// entryTime accepts ISO dates/datetimes and renders them the way pydantic serializes them.
func entryTime(raw any, field string) (string, error) {
	text, ok := raw.(string)
	if !ok {
		return "", entryError(field, "ISO 시각 문자열이 필요하다")
	}
	text = strings.TrimSpace(text)
	for _, layout := range []string{"2006-01-02T15:04:05.999999999Z07:00", "2006-01-02 15:04:05.999999999Z07:00", "2006-01-02T15:04Z07:00"} {
		if t, err := time.Parse(layout, text); err == nil {
			out := t.Format("2006-01-02T15:04:05")
			if us := t.Nanosecond() / 1000; us > 0 {
				out += fmt.Sprintf(".%06d", us)
			}
			return out + t.Format("Z07:00"), nil
		}
	}
	for _, layout := range []string{"2006-01-02T15:04:05.999999999", "2006-01-02 15:04:05.999999999", "2006-01-02T15:04", "2006-01-02"} {
		if t, err := time.Parse(layout, text); err == nil {
			out := t.Format("2006-01-02T15:04:05")
			if us := t.Nanosecond() / 1000; us > 0 {
				out += fmt.Sprintf(".%06d", us)
			}
			return out, nil
		}
	}
	return "", entryError(field, "ISO 시각이 아니다")
}

func validateMemoryEntry(raw any) (map[string]any, error) {
	entry, ok := raw.(map[string]any)
	if !ok {
		return nil, InvalidField("entry", "객체여야 한다")
	}
	if err := ScanSecrets(entry, "entry"); err != nil {
		return nil, err
	}
	out := map[string]any{}
	id, ok := entry["id"].(string)
	if !ok || !memoryEntryID.MatchString(id) {
		return nil, entryError("id", "MEM-YYYY-MM-DD-NNN")
	}
	out["id"] = id
	out["schema_version"] = 1
	if v, exists := entry["schema_version"]; exists {
		n, ok := v.(int)
		if f, isFloat := v.(float64); isFloat && f == float64(int(f)) {
			n, ok = int(f), true
		}
		if !ok || n < 1 || n > 99 {
			return nil, entryError("schema_version", "1~99 정수")
		}
		out["schema_version"] = n
	}
	abstraction, ok := entry["primary_abstraction"].(string)
	if n := utf8.RuneCountInString(abstraction); !ok || n < 1 || n > 200 {
		return nil, entryError("primary_abstraction", "1~200자")
	}
	out["primary_abstraction"] = abstraction
	for _, key := range []string{"source_paths", "cue_anchors", "owners", "scope", "mentioned_in", "related_ids"} {
		list := []string{}
		if v, exists := entry[key]; exists {
			items, ok := v.([]any)
			if !ok {
				return nil, entryError(key, "문자열 목록")
			}
			for _, item := range items {
				text, ok := item.(string)
				if !ok {
					return nil, entryError(key, "문자열 목록")
				}
				list = append(list, text)
			}
		}
		if key == "related_ids" && len(list) > 16 {
			return nil, entryError(key, "16개까지")
		}
		out[key] = list
	}
	out["value_digest"] = ""
	if v, exists := entry["value_digest"]; exists {
		text, ok := v.(string)
		if !ok {
			return nil, entryError("value_digest", "문자열")
		}
		out["value_digest"] = text
	}
	out["merge_state"] = "active"
	if v, exists := entry["merge_state"]; exists {
		if v != "active" && v != "linked" && v != "merged" {
			return nil, entryError("merge_state", "active · linked · merged")
		}
		out["merge_state"] = v
	}
	for _, key := range []string{"created_at", "updated_at"} {
		at, err := entryTime(entry[key], key)
		if err != nil {
			return nil, err
		}
		out[key] = at
	}
	return out, nil
}

// MemoryEntryPut validates and stores one memory_index entry (new entries use version 0).
func (s *Store) MemoryEntryPut(ctx Ctx, raw any, expected int) (map[string]any, error) {
	p, err := NeedCallsign(ctx)
	if err != nil {
		return nil, err
	}
	entry, err := validateMemoryEntry(raw)
	if err != nil {
		return nil, err
	}
	id := entry["id"].(string)
	encoded, err := EncodeJSON(entry)
	if err != nil {
		return nil, err
	}
	return s.withWriteTx(func(tx *sql.Tx) (map[string]any, error) {
		var current int
		err := tx.QueryRow("SELECT version FROM memory_entry WHERE project_id=? AND id=?", p.ProjectID, id).Scan(&current)
		if err != nil && !errors.Is(err, sql.ErrNoRows) {
			return nil, err
		}
		if expected != current {
			return nil, &HubError{Status: 409, Code: "version_conflict", Message: fmt.Sprintf("version 이 다르다 — 지금 %d (새 entry 는 0)", current), Detail: map[string]any{"current_version": current, "id": id}}
		}
		if _, err := tx.Exec("INSERT INTO memory_entry (project_id,id,body_json,version,updated_by,updated_at) VALUES (?,?,?,1,?,?) ON CONFLICT(project_id,id) DO UPDATE SET body_json=excluded.body_json,version=memory_entry.version+1,updated_by=excluded.updated_by,updated_at=excluded.updated_at", p.ProjectID, id, encoded, p.Callsign, db.FormatISO(ctx.Now)); err != nil {
			return nil, err
		}
		if err := s.RecordEvent(tx, ctx, &p.ProjectID, "memory_entry", id, "put", map[string]any{"version": current}, map[string]any{"version": current + 1}, nil); err != nil {
			return nil, err
		}
		return map[string]any{"id": id, "version": current + 1}, nil
	})
}

// MemoryEntryGet reads one entry of the caller's project.
func (s *Store) MemoryEntryGet(ctx Ctx, id string) (map[string]any, error) {
	p, err := NeedCallsign(ctx)
	if err != nil {
		return nil, err
	}
	var raw, by, at string
	var version int
	err = s.pool.QueryRow("SELECT body_json,version,updated_by,updated_at FROM memory_entry WHERE project_id=? AND id=?", p.ProjectID, id).Scan(&raw, &version, &by, &at)
	if errors.Is(err, sql.ErrNoRows) {
		return nil, &HubError{Status: 404, Code: "not_found", Message: "memory entry 가 없다: " + id, Detail: map[string]any{"id": id}}
	}
	if err != nil {
		return nil, err
	}
	var entry map[string]any
	if err := json.Unmarshal([]byte(raw), &entry); err != nil {
		return nil, err
	}
	return map[string]any{"id": id, "entry": entry, "version": version, "updated_by": by, "updated_at": at}, nil
}

// MemoryEntryList lists entries of the caller's project.
func (s *Store) MemoryEntryList(ctx Ctx) (map[string]any, error) {
	p, err := NeedCallsign(ctx)
	if err != nil {
		return nil, err
	}
	rows, err := s.pool.Query("SELECT id,body_json,version FROM memory_entry WHERE project_id=? ORDER BY id", p.ProjectID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	out := []map[string]any{}
	for rows.Next() {
		var id, raw string
		var version int
		if err := rows.Scan(&id, &raw, &version); err != nil {
			return nil, err
		}
		var entry struct {
			Primary string `json:"primary_abstraction"`
		}
		if err := json.Unmarshal([]byte(raw), &entry); err != nil {
			return nil, err
		}
		out = append(out, map[string]any{"id": id, "version": version, "primary_abstraction": entry.Primary})
	}
	if err := rows.Err(); err != nil {
		return nil, err
	}
	return map[string]any{"entries": out}, nil
}
