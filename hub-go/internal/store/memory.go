package store

import (
	"database/sql"
	"encoding/json"
	"errors"
	"fmt"
	"strings"

	"github.com/ykylee/standard_ai_workflow/hub-go/internal/db"
)

var handoffStringKeys = []string{"baseline", "focus"}
var handoffListKeys = []string{"in_progress", "blocked", "recent_done", "next", "risks"}

func validateHandoff(raw map[string]any) (map[string]any, error) {
	allowed := map[string]bool{}
	for _, k := range handoffStringKeys {
		allowed[k] = true
	}
	for _, k := range handoffListKeys {
		allowed[k] = true
	}
	extra := []string{}
	for k := range raw {
		if !allowed[k] {
			extra = append(extra, "handoff."+k)
		}
	}
	if len(extra) > 0 {
		return nil, UnknownField(extra)
	}
	out := map[string]any{}
	for _, k := range handoffStringKeys {
		value := ""
		if v, ok := raw[k]; ok {
			var valid bool
			value, valid = v.(string)
			if !valid {
				return nil, InvalidField("handoff."+k, "문자열")
			}
		}
		out[k] = value
	}
	for _, k := range handoffListKeys {
		values := []string{}
		if v, ok := raw[k]; ok {
			switch list := v.(type) {
			case []any:
				for _, item := range list {
					s, ok := item.(string)
					if !ok || strings.TrimSpace(s) == "" {
						return nil, InvalidField("handoff."+k, "비지 않은 문자열 목록")
					}
					values = append(values, strings.TrimSpace(s))
				}
			case []string:
				for _, s := range list {
					if strings.TrimSpace(s) == "" {
						return nil, InvalidField("handoff."+k, "비지 않은 문자열 목록")
					}
					values = append(values, strings.TrimSpace(s))
				}
			default:
				return nil, InvalidField("handoff."+k, "비지 않은 문자열 목록")
			}
		}
		if k == "in_progress" || k == "blocked" || k == "recent_done" {
			for _, value := range values {
				if !strings.HasPrefix(value, "TASK-") {
					return nil, InvalidField("handoff."+k, "항목은 TASK- 로 시작해요 (R6.2): "+fmt.Sprintf("%q", value))
				}
			}
		}
		out[k] = values
	}
	if err := ScanSecrets(out, "handoff"); err != nil {
		return nil, err
	}
	return out, nil
}

func putHandoff(tx *sql.Tx, ctx Ctx, p *Principal, expected *int, sections map[string]any) (map[string]any, error) {
	var current int
	var oldJSON string
	err := tx.QueryRow("SELECT version,sections_json FROM handoff WHERE project_id=? AND callsign=?", p.ProjectID, p.Callsign).Scan(&current, &oldJSON)
	if errors.Is(err, sql.ErrNoRows) {
		current = 0
	} else if err != nil {
		return nil, err
	}
	if expected != nil && *expected != current {
		var old any
		if oldJSON != "" {
			var parsed map[string]any
			if err := json.Unmarshal([]byte(oldJSON), &parsed); err != nil {
				return nil, err
			}
			old = parsed
		}
		return nil, &HubError{Status: 409, Code: "version_conflict", Message: fmt.Sprintf("version 이 달라요 — 지금 %d", current), Detail: map[string]any{"current_version": current, "current": old}}
	}
	recent := sections["recent_done"].([]string)
	moved := []string{}
	if len(recent) > 10 {
		moved = append(moved, recent[10:]...)
		recent = recent[:10]
		sections["recent_done"] = recent
	}
	for _, item := range moved {
		title := strings.Fields(item)
		if len(title) == 0 {
			continue
		}
		if _, err := tx.Exec("INSERT INTO memory_note (project_id,callsign,kind,title,body_md,meta_json,created_at) VALUES (?,?,'handoff_rollover',?,?,'{}',?)", p.ProjectID, p.Callsign, title[0], item, db.FormatISO(ctx.Now)); err != nil {
			return nil, err
		}
	}
	body, err := json.Marshal(sections)
	if err != nil {
		return nil, err
	}
	if _, err := tx.Exec("INSERT INTO handoff (project_id,callsign,sections_json,updated_at,version) VALUES (?,?,?,?,1) ON CONFLICT(project_id,callsign) DO UPDATE SET sections_json=excluded.sections_json,updated_at=excluded.updated_at,version=handoff.version+1", p.ProjectID, p.Callsign, string(body), db.FormatISO(ctx.Now)); err != nil {
		return nil, err
	}
	if err := (&Store{}).RecordEvent(tx, ctx, &p.ProjectID, "handoff", p.Callsign, "put", map[string]any{"version": current}, map[string]any{"version": current + 1, "rolled_over": len(moved)}, nil); err != nil {
		return nil, err
	}
	return map[string]any{"callsign": p.Callsign, "version": current + 1, "rolled_over": moved}, nil
}

// SessionEnd writes handoff/progress atomically, ends the session, and returns open assignments.
func (s *Store) SessionEnd(ctx Ctx, sessionID string, handoff map[string]any, expected *int, progress []any) (map[string]any, error) {
	p, err := NeedCallsign(ctx)
	if err != nil {
		return nil, err
	}
	clean, err := validateHandoff(handoff)
	if err != nil {
		return nil, err
	}
	progressItems := []map[string]string{}
	for i, raw := range progress {
		item, ok := raw.(map[string]any)
		if !ok || len(item) != 2 {
			return nil, InvalidField(fmt.Sprintf("progress[%d]", i), "{task_id, note}")
		}
		taskID, ok1 := item["task_id"].(string)
		note, ok2 := item["note"].(string)
		if !ok1 || !ok2 {
			return nil, InvalidField(fmt.Sprintf("progress[%d]", i), "{task_id, note}")
		}
		progressItems = append(progressItems, map[string]string{"task_id": taskID, "note": note})
	}
	return s.withWriteTx(func(tx *sql.Tx) (map[string]any, error) {
		if sessionID != "" {
			if err := s.checkOwnSession(tx, p, sessionID); err != nil {
				return nil, err
			}
		}
		stamp := ctx.Now.Format("2006-01-02 15:04")
		for _, item := range progressItems {
			if err := ScanSecrets(item["note"], "progress.note"); err != nil {
				return nil, err
			}
			task, err := s.GetTask(tx, p.ProjectID, item["task_id"])
			if err != nil {
				return nil, err
			}
			if strings.TrimSpace(item["note"]) == "" {
				return nil, InvalidField("progress.note", "비었어요")
			}
			note := fmt.Sprintf("[%s] %s", stamp, strings.TrimSpace(item["note"]))
			if _, err := tx.Exec("UPDATE task SET progress_note=?,progress_at=?,version=version+1,updated_at=? WHERE project_id=? AND id=?", note, db.FormatISO(ctx.Now), db.FormatISO(ctx.Now), p.ProjectID, item["task_id"]); err != nil {
				return nil, err
			}
			if err := s.RecordEvent(tx, ctx, &p.ProjectID, "task", item["task_id"], "progress", map[string]any{"progress_note": task["progress_note"]}, map[string]any{"progress_note": strings.TrimSpace(item["note"])}, nil); err != nil {
				return nil, err
			}
		}
		out, err := putHandoff(tx, ctx, p, expected, clean)
		if err != nil {
			return nil, err
		}
		out["progress_written"] = len(progressItems)
		out["next"] = "커밋 → push. 진입 파일의 허브 렌더 영역이 바뀌었으면 그 변경도 커밋한다 (D10)"
		if sessionID == "" { // 세션을 등록하지 않은 클라이언트 — handoff · 진행만 쓴다
			return out, nil
		}
		if _, err := tx.Exec("UPDATE session SET status='ended',ended_at=?,waiting_since=NULL,version=version+1 WHERE project_id=? AND id=?", db.FormatISO(ctx.Now), p.ProjectID, sessionID); err != nil {
			return nil, err
		}
		if err := s.RecordEvent(tx, ctx, &p.ProjectID, "session", sessionID, "end", nil, nil, nil); err != nil {
			return nil, err
		}
		rows, err := tx.Query("SELECT task_id FROM assignment WHERE project_id=? AND session_id=? AND state IN ('offered','accepted')", p.ProjectID, sessionID)
		if err != nil {
			return nil, err
		}
		tasks := []string{}
		for rows.Next() {
			var task string
			if err := rows.Scan(&task); err != nil {
				_ = rows.Close()
				return nil, err
			}
			tasks = append(tasks, task)
		}
		if err := rows.Err(); err != nil {
			_ = rows.Close()
			return nil, err
		}
		if err := rows.Close(); err != nil {
			return nil, err
		}
		for _, task := range tasks {
			if err := s.returnOfferedAssignment(tx, ctx, p.ProjectID, task, "session_ended"); err != nil {
				return nil, err
			}
		}
		return out, nil
	})
}
