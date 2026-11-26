package store

import (
	"path/filepath"
	"testing"
	"time"

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

// TestSessionExpireAfterSilence — 신호가 24시간 끊긴 세션은 허브가 ended 로 만료한다 (TASK-2026-11-26-claude-plex-019, Python check_hub_orch case 13).
func TestSessionExpireAfterSilence(t *testing.T) {
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
	reg, err := st.RegisterProject(Ctx{Now: now, Via: "test"}, "https://github.com/acme/session-expire", "session expire", "owner-human", "human", "", "")
	if err != nil {
		t.Fatal(err)
	}
	pid := reg["project_id"].(string)
	p, err := st.Authenticate(reg["token"].(string), &now, "test")
	if err != nil {
		t.Fatal(err)
	}
	ins := func(id, last, status, ended string) {
		var endedAt any
		if ended != "" {
			endedAt = ended
		}
		if _, err := st.DB().Exec(`INSERT INTO session (project_id,id,callsign,harness,harness_session_id,kind,allow_wait,delivery_json,status,last_signal_at,started_at,ended_at)
			VALUES (?,?,?,?,?,?,?,?,?,?,?,?)`, pid, id, p.Callsign, "codex", id, "worker", 0, `[]`, status, last, db.FormatISO(now), endedAt); err != nil {
			t.Fatal(err)
		}
	}
	old, fresh, done := "S-20261122-0000aaaa", "S-20261122-0000bbbb", "S-20261122-0000cccc"
	ins(old, db.FormatISO(now), "active", "")
	ins(fresh, db.FormatISO(now.Add(2*time.Hour)), "active", "")
	ins(done, db.FormatISO(now), "ended", db.FormatISO(now))
	if _, err := st.DB().Exec(`INSERT INTO assignment (project_id,task_id,session_id,callsign,message_id,state,offered_at) VALUES (?,?,?,?,?,?,?)`,
		pid, "T-exp", old, p.Callsign, "M-exp", "accepted", db.FormatISO(now)); err != nil {
		t.Fatal(err)
	}
	byID := func(at time.Time) map[string]map[string]any {
		out, err := st.SessionList(Ctx{Now: at, Via: "http", Principal: p}, "", "")
		if err != nil {
			t.Fatal(err)
		}
		m := map[string]map[string]any{}
		for _, v := range out["sessions"].([]map[string]any) {
			m[v["id"].(string)] = v
		}
		return m
	}
	before := byID(now.Add(23 * time.Hour))
	if before[old]["status"] != "unknown" || before[old]["end_reason"] != nil {
		t.Fatalf("23h: expected unknown, got %#v", before[old])
	}
	at := now.Add(25 * time.Hour)
	after := byID(at)
	if after[old]["status"] != "ended" || after[old]["end_reason"] != "expired" || after[old]["ended_at"] == nil {
		t.Fatalf("25h: expected expired, got %#v", after[old])
	}
	if after[fresh]["status"] != "unknown" || after[done]["end_reason"] != "ended" {
		t.Fatalf("fresh=%#v done=%#v", after[fresh], after[done])
	}
	var state, reason, by string
	if err := st.DB().QueryRow("SELECT state,return_reason FROM assignment WHERE project_id=? AND task_id='T-exp'", pid).Scan(&state, &reason); err != nil {
		t.Fatal(err)
	}
	if err := st.DB().QueryRow("SELECT callsign FROM event WHERE project_id=? AND target_kind='session' AND target_id=? AND op='expire'", pid, old).Scan(&by); err != nil {
		t.Fatal(err)
	}
	if state != "returned" || reason != "session_expired" || by != "hub" {
		t.Fatalf("assignment=%s/%s event by=%s", state, reason, by)
	}
	_, err = st.SessionUpdate(Ctx{Now: at, Via: "http", Principal: p}, old, map[string]any{"kind": "worker"})
	if he, ok := AsHubError(err); !ok || he.Code != "session_ended" {
		t.Fatalf("expected session_ended, got %v", err)
	}
}
