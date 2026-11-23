package store

import (
	"database/sql"
	"path/filepath"
	"testing"
	"time"

	"github.com/ykylee/standard_ai_workflow/hub-go/internal/db"
)

func TestInboxListTakeAndAck(t *testing.T) {
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
	reg, err := st.RegisterProject(Ctx{Now: now, Via: "test"}, "https://github.com/acme/inbox-test", "inbox test", "owner-human", "human", "", "")
	if err != nil {
		t.Fatal(err)
	}
	p, err := st.Authenticate(reg["token"].(string), &now, "test")
	if err != nil {
		t.Fatal(err)
	}
	ctx := Ctx{Now: now, Via: "http", Principal: p}
	sid := "S-20261122-a1b2c3d4"
	if _, err := st.DB().Exec(`INSERT INTO session (project_id,id,callsign,harness,kind,delivery_json,last_signal_at,started_at)
		VALUES (?,?,?,?,?,?,?,?)`, p.ProjectID, sid, p.Callsign, "codex", "worker", `["piggyback"]`, db.FormatISO(now), db.FormatISO(now)); err != nil {
		t.Fatal(err)
	}
	var messageID string
	if _, err := st.WriteTx(func(tx *sql.Tx) (map[string]any, error) {
		id, err := st.EnqueueMessage(tx, ctx, p.ProjectID, "session", sid, "note", map[string]any{"text": "hello"}, p.Callsign, "", false, "")
		messageID = id
		return nil, err
	}); err != nil {
		t.Fatal(err)
	}
	listed, err := st.InboxList(ctx, sid, "")
	if err != nil {
		t.Fatal(err)
	}
	messages := listed["messages"].([]map[string]any)
	if len(messages) != 1 || messages[0]["state"] != "queued" {
		t.Fatalf("unexpected initial inbox: %#v", listed)
	}
	taken, err := st.InboxTake(ctx, sid, "piggyback")
	if err != nil {
		t.Fatal(err)
	}
	if len(taken["messages"].([]map[string]any)) != 1 {
		t.Fatalf("unexpected delivery: %#v", taken)
	}
	acked, err := st.InboxAck(ctx, sid, messageID, "seen", "", "ack-1")
	if err != nil || acked["state"] != "acked" {
		t.Fatalf("ack=%#v err=%v", acked, err)
	}
	replay, err := st.InboxAck(ctx, sid, messageID, "seen", "", "ack-1")
	if err != nil || replay["replayed"] != true {
		t.Fatalf("replay=%#v err=%v", replay, err)
	}
	listed, err = st.InboxList(ctx, sid, "acked")
	if err != nil || len(listed["messages"].([]map[string]any)) != 1 {
		t.Fatalf("acked inbox=%#v err=%v", listed, err)
	}
	if _, err := st.WriteTx(func(tx *sql.Tx) (map[string]any, error) {
		_, err := st.EnqueueMessage(tx, ctx, p.ProjectID, "session", sid, "note", map[string]any{"text": "late ack"}, p.Callsign, "", false, "")
		return nil, err
	}); err != nil {
		t.Fatal(err)
	}
	if _, err := st.InboxTake(ctx, sid, "piggyback"); err != nil {
		t.Fatal(err)
	}
	later := ctx
	later.Now = now.Add(11 * time.Minute)
	if _, err := st.InboxTake(later, sid, "piggyback"); err != nil {
		t.Fatal(err)
	}
	unacknowledged, err := st.InboxList(later, sid, "unacknowledged")
	if err != nil || len(unacknowledged["messages"].([]map[string]any)) != 1 {
		t.Fatalf("unacknowledged inbox=%#v err=%v", unacknowledged, err)
	}
}

func TestWaitAndReport(t *testing.T) {
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
	reg, err := st.RegisterProject(Ctx{Now: now, Via: "test"}, "https://github.com/acme/wait-report", "wait report", "owner-human", "human", "", "")
	if err != nil {
		t.Fatal(err)
	}
	p, err := st.Authenticate(reg["token"].(string), &now, "test")
	if err != nil {
		t.Fatal(err)
	}
	ctx := Ctx{Now: now, Via: "http", Principal: p}
	sid := "S-20261122-01020304"
	if _, err := st.DB().Exec(`INSERT INTO session (project_id,id,callsign,harness,kind,allow_wait,delivery_json,last_signal_at,started_at)
		VALUES (?,?,?,?,?,?,?,?,?)`, p.ProjectID, sid, p.Callsign, "codex", "worker", 1, `["wait"]`, db.FormatISO(now), db.FormatISO(now)); err != nil {
		t.Fatal(err)
	}
	waited, err := st.Wait(ctx, sid)
	if err != nil || waited["call_again"] != true {
		t.Fatalf("wait=%#v err=%v", waited, err)
	}
	if _, err := st.DB().Exec(`INSERT INTO assignment (project_id,task_id,session_id,callsign,message_id,state,offered_at,accepted_at)
		VALUES (?,?,?,?,?,'accepted',?,?)`, p.ProjectID, "TASK-1", sid, p.Callsign, "MSG-20261122-111111111111", db.FormatISO(now), db.FormatISO(now)); err != nil {
		t.Fatal(err)
	}
	report, err := st.Report(ctx, sid, "TASK-1", "completed", "go test passed", "report-1")
	if err != nil || report["state"] != "reported" {
		t.Fatalf("report=%#v err=%v", report, err)
	}
	inbox, err := st.InboxList(ctx, "", "queued")
	if err != nil || len(inbox["messages"].([]map[string]any)) != 1 {
		t.Fatalf("report inbox=%#v err=%v", inbox, err)
	}
}
