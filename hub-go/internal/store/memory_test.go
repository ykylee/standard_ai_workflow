package store

import (
	"path/filepath"
	"testing"

	"github.com/ykylee/standard_ai_workflow/hub-go/internal/db"
)

func TestSessionEndWritesHandoffProgressAndClosesSessionAtomically(t *testing.T) {
	now := testNow()
	path := filepath.Join(t.TempDir(), "hub.db")
	if _, err := db.OpenDB(path, now); err != nil {
		t.Fatal(err)
	}
	st, err := New(path)
	if err != nil {
		t.Fatal(err)
	}
	defer st.Close()
	reg, err := st.RegisterProject(Ctx{Now: now, Via: "test"}, "https://github.com/acme/session-end", "session end", "owner-human", "human", "", "")
	if err != nil {
		t.Fatal(err)
	}
	p, err := st.Authenticate(reg["token"].(string), &now, "test")
	if err != nil {
		t.Fatal(err)
	}
	ctx := Ctx{Now: now, Via: "http", Principal: p}
	task, err := st.TaskCreate(ctx, map[string]any{"title": "handoff task"}, "", nil)
	if err != nil {
		t.Fatal(err)
	}
	taskID := task["task"].(map[string]any)["id"].(string)
	sid := "S-20261122-fff0ee11"
	if _, err := st.DB().Exec(`INSERT INTO session (project_id,id,callsign,harness,kind,delivery_json,last_signal_at,started_at)
		VALUES (?,?,?,?,?,?,?,?)`, p.ProjectID, sid, p.Callsign, "codex", "interactive", `["piggyback"]`, db.FormatISO(now), db.FormatISO(now)); err != nil {
		t.Fatal(err)
	}
	handoff := map[string]any{"baseline": "base", "focus": "focus", "in_progress": []any{"TASK-2026-11-23-main-001"}}
	badVersion := 1
	_, err = st.SessionEnd(ctx, sid, handoff, &badVersion, []any{map[string]any{"task_id": taskID, "note": "progress"}})
	if he, ok := AsHubError(err); !ok || he.Code != "version_conflict" {
		t.Fatalf("expected handoff version conflict, got %v", err)
	}
	untouched, err := st.GetTask(st.DB(), p.ProjectID, taskID)
	if err != nil {
		t.Fatal(err)
	}
	if untouched["progress_note"] != "" {
		t.Fatalf("failed transaction changed task progress: %#v", untouched)
	}
	result, err := st.SessionEnd(ctx, sid, handoff, nil, []any{map[string]any{"task_id": taskID, "note": "progress"}})
	if err != nil {
		t.Fatal(err)
	}
	if result["progress_written"] != 1 || result["version"] != 1 {
		t.Fatalf("unexpected result: %#v", result)
	}
	updated, err := st.GetTask(st.DB(), p.ProjectID, taskID)
	if err != nil {
		t.Fatal(err)
	}
	if updated["progress_note"] != "[2026-11-22 12:00] progress" {
		t.Fatalf("progress not written: %#v", updated)
	}
	var status string
	if err := st.DB().QueryRow("SELECT status FROM session WHERE project_id=? AND id=?", p.ProjectID, sid).Scan(&status); err != nil {
		t.Fatal(err)
	}
	if status != "ended" {
		t.Fatalf("session status=%s", status)
	}
}
