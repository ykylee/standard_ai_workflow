package store

import (
	"path/filepath"
	"testing"

	"github.com/ykylee/standard_ai_workflow/hub-go/internal/db"
)

func TestSessionUpdateAndList(t *testing.T) {
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
	reg, err := st.RegisterProject(Ctx{Now: now, Via: "test"}, "https://github.com/acme/session-test", "session test", "owner-human", "human", "", "")
	if err != nil {
		t.Fatal(err)
	}
	pid := reg["project_id"].(string)
	token := reg["token"].(string)
	p, err := st.Authenticate(token, &now, "test")
	if err != nil {
		t.Fatal(err)
	}
	ctx := Ctx{Now: now, Via: "http", Principal: p}
	sid := "S-20261122-1234abcd"
	if _, err := st.DB().Exec(`INSERT INTO session (project_id,id,callsign,harness,kind,allow_wait,delivery_json,last_signal_at,started_at)
		VALUES (?,?,?,?,?,?,?,?,?)`, pid, sid, p.Callsign, "codex", "interactive", 0, `["piggyback"]`, db.FormatISO(now), db.FormatISO(now)); err != nil {
		t.Fatal(err)
	}
	updated, err := st.SessionUpdate(ctx, sid, map[string]any{"kind": "worker", "delivery": []any{"wait", "hook"}})
	if err != nil {
		t.Fatal(err)
	}
	view := updated["session"].(map[string]any)
	delivery := view["delivery"].([]string)
	if view["kind"] != "worker" || delivery[0] != "wait" {
		t.Fatalf("unexpected session view: %#v", view)
	}
	listed, err := st.SessionList(ctx, "", "idle")
	if err != nil {
		t.Fatal(err)
	}
	if len(listed["sessions"].([]map[string]any)) != 1 {
		t.Fatalf("expected working session in list: %#v", listed)
	}
}

func TestSessionUpdateWaitPermission(t *testing.T) {
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
	reg, err := st.RegisterProject(Ctx{Now: now, Via: "test"}, "https://github.com/acme/session-agent", "session agent", "owner-human", "human", "", "")
	if err != nil {
		t.Fatal(err)
	}
	joined, err := st.RegisterCallsign(Ctx{Now: now, Via: "test"}, reg["project_id"].(string), "worker-a", "agent", "", "")
	if err != nil {
		t.Fatal(err)
	}
	token := joined["token"].(string)
	p, err := st.Authenticate(token, &now, "test")
	if err != nil {
		t.Fatal(err)
	}
	sid := "S-20261122-1234abcd"
	if _, err := st.DB().Exec(`INSERT INTO session (project_id,id,callsign,harness,kind,allow_wait,delivery_json,last_signal_at,started_at)
		VALUES (?,?,?,?,?,?,?,?,?)`, reg["project_id"], sid, p.Callsign, "codex", "worker", 0, `[]`, db.FormatISO(now), db.FormatISO(now)); err != nil {
		t.Fatal(err)
	}
	_, err = st.SessionUpdate(Ctx{Now: now, Via: "http", Principal: p}, sid, map[string]any{"allow_wait": true})
	if he, ok := AsHubError(err); !ok || he.Code != "forbidden" {
		t.Fatalf("expected forbidden, got %v", err)
	}
}
