package store

import (
	"path/filepath"
	"testing"
	"time"

	"github.com/ykylee/standard_ai_workflow/hub-go/internal/db"
)

func TestAccountEnrollmentLoginAndConfirmationA2A(t *testing.T) {
	now := time.Date(2026, 11, 24, 12, 0, 0, 0, time.UTC)
	path := filepath.Join(t.TempDir(), "hub.db")
	if _, err := db.OpenDB(path, now); err != nil {
		t.Fatal(err)
	}
	s, err := New(path)
	if err != nil {
		t.Fatal(err)
	}
	defer s.Close()
	project, err := s.RegisterProject(Ctx{Now: now, Via: "test"}, "https://github.com/acme/confirm", "Confirm", "owner-human", "human", "", "")
	if err != nil {
		t.Fatal(err)
	}
	ownerToken := project["token"].(string)
	pid := project["project_id"].(string)
	owner, err := s.Authenticate(ownerToken, &now, "")
	if err != nil {
		t.Fatal(err)
	}
	agentReg, err := s.RegisterCallsign(Ctx{Now: now, Via: "test", Principal: owner}, pid, "agent-confirm", "agent", "", "")
	if err != nil {
		t.Fatal(err)
	}
	agentToken := agentReg["token"].(string)
	agent, err := s.Authenticate(agentToken, &now, "")
	if err != nil {
		t.Fatal(err)
	}
	sid := "S-20261124-a1b2c3d4"
	if _, err := s.DB().Exec("INSERT INTO session(project_id,id,callsign,harness,kind,delivery_json,last_signal_at,started_at) VALUES(?,?,?,?,?,?,?,?)", pid, sid, agent.Callsign, "codex", "worker", `["piggyback"]`, db.FormatISO(now), db.FormatISO(now)); err != nil {
		t.Fatal(err)
	}
	requested, err := s.ConfirmationRequest(Ctx{Now: now, Via: "mcp", Principal: agent}, sid, "운영 배포", "배포할까요?", "회귀 통과", nil)
	if err != nil {
		t.Fatal(err)
	}
	rid := requested["request"].(map[string]any)["id"].(string)
	ownerCtx := Ctx{Now: now, Via: "ui", Principal: owner}
	ownerSession := "S-20261124-b2c3d4e5"
	if _, err := s.DB().Exec("INSERT INTO session(project_id,id,callsign,harness,kind,delivery_json,last_signal_at,started_at) VALUES(?,?,?,?,?,?,?,?)", pid, ownerSession, owner.Callsign, "codex", "interactive", `["piggyback"]`, db.FormatISO(now), db.FormatISO(now)); err != nil {
		t.Fatal(err)
	}
	queue, err := s.ConfirmationList(ownerCtx)
	if err != nil || len(queue["requests"].([]map[string]any)) != 1 {
		t.Fatalf("queue=%#v err=%v", queue, err)
	}
	if _, err := s.ConfirmationList(Ctx{Now: now, Via: "ui", Principal: agent}); err == nil {
		t.Fatal("agent saw owner confirmation queue")
	}
	if _, err := s.InboxAck(ownerCtx, ownerSession, rid, "seen", "", "ack-confirm"); err == nil {
		t.Fatal("generic A2A ack bypassed human confirmation decision")
	} else if he, ok := AsHubError(err); !ok || he.Code != "human_decision_required" {
		t.Fatalf("generic A2A ack error=%v", err)
	}
	decision, err := s.ConfirmationDecide(ownerCtx, rid, "approve", "go ahead")
	if err != nil || decision["request"].(map[string]any)["state"] != "approved" {
		t.Fatalf("decision=%#v err=%v", decision, err)
	}
	second, err := s.ConfirmationRequest(Ctx{Now: now, Via: "mcp", Principal: agent}, sid, "Rotate secret", "Rotate now?", "", nil)
	if err != nil {
		t.Fatal(err)
	}
	rid2 := second["request"].(map[string]any)["id"].(string)
	rejected, err := s.ConfirmationDecide(ownerCtx, rid2, "reject", "not in change window")
	if err != nil || rejected["request"].(map[string]any)["state"] != "rejected" {
		t.Fatalf("rejection=%#v err=%v", rejected, err)
	}
	list, err := s.InboxList(Ctx{Now: now, Via: "mcp", Principal: agent}, sid, "")
	if err != nil {
		t.Fatal(err)
	}
	msgs := list["messages"].([]map[string]any)
	found := false
	for _, m := range msgs {
		if m["body"].(map[string]any)["event"] == "confirmation_result" {
			found = true
		}
	}
	count := 0
	for _, m := range msgs {
		if m["body"].(map[string]any)["event"] == "confirmation_result" {
			count++
		}
	}
	if !found || count != 2 {
		t.Fatalf("A2A confirmation result missing: %#v", list)
	}
	session, account, linked, err := s.AccountEnroll(ownerToken, "owner.one", "Owner One", "long-test-password-123", now)
	if err != nil {
		t.Fatal(err)
	}
	if linked["callsign"] != "owner-human" || account.Username != "owner.one" {
		t.Fatalf("enrollment=%#v %#v", account, linked)
	}
	active, err := s.AccountBySession(session, now)
	if err != nil || active == nil || active.ID != account.ID {
		t.Fatalf("account session=%#v err=%v", active, err)
	}
	linkedPrincipal, err := s.AccountCallsign(account.ID, pid)
	if err != nil || linkedPrincipal == nil || linkedPrincipal.Callsign != "owner-human" {
		t.Fatalf("linked principal=%#v err=%v", linkedPrincipal, err)
	}
	if _, _, err := s.AccountLogin("owner.one", "long-test-password-123", now); err != nil {
		t.Fatal(err)
	}
	if _, _, err := s.AccountLogin("owner.one", "wrong", now); err == nil {
		t.Fatal("wrong account password accepted")
	}
	for i := 0; i < 7; i++ {
		_, _, _ = s.AccountLogin("owner.one", "wrong", now)
	}
	if _, _, err := s.AccountLogin("owner.one", "wrong", now); err == nil {
		t.Fatal("login burst was not limited")
	} else if he, ok := AsHubError(err); !ok || he.Status != 429 {
		t.Fatalf("rate limit error=%v", err)
	}
	if _, _, _, err := s.AccountEnroll(ownerToken, "second.user", "Second", "long-test-password-123", now); err == nil {
		t.Fatal("callsign enrolled twice")
	}
}
