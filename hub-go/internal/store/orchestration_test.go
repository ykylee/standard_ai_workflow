package store

import (
	"path/filepath"
	"testing"
	"time"

	"github.com/ykylee/standard_ai_workflow/hub-go/internal/db"
)

func orchestrationTestStore(t *testing.T) *Store {
	t.Helper()
	path := filepath.Join(t.TempDir(), "hub.db")
	now := time.Date(2026, 11, 23, 12, 0, 0, 0, time.UTC)
	if _, err := db.OpenDB(path, now); err != nil {
		t.Fatal(err)
	}
	s, err := New(path)
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { _ = s.Close() })
	return s
}

func TestOrchestrationLeaseAssignmentAndRecall(t *testing.T) {
	s := orchestrationTestStore(t)
	now := time.Date(2026, 11, 23, 12, 0, 0, 0, time.UTC)
	reg, err := s.RegisterProject(Ctx{Now: now, Via: "test"}, "https://github.com/acme/orchestration", "Orchestration", "owner-human", "human", "", "")
	if err != nil {
		t.Fatal(err)
	}
	p, err := s.Authenticate(reg["token"].(string), &now, "test")
	if err != nil {
		t.Fatal(err)
	}
	ctx := Ctx{Now: now, Via: "test", Principal: p}
	orch, err := s.RegisterSession(ctx, map[string]any{"harness": "codex", "kind": "worker", "delivery": []any{"wait"}})
	if err != nil {
		t.Fatal(err)
	}
	worker, err := s.RegisterSession(ctx, map[string]any{"harness": "codex", "harness_session_id": "worker-2", "kind": "worker", "delivery": []any{"piggyback"}})
	if err != nil {
		t.Fatal(err)
	}
	if _, err = s.OrchDeclare(ctx, orch["id"].(string)); err != nil {
		t.Fatal(err)
	}
	if _, err = s.OrchDeclare(ctx, orch["id"].(string)); err == nil {
		t.Fatal("second declaration should fail")
	} else if he, _ := AsHubError(err); he == nil || he.Code != "orchestrator_exists" {
		t.Fatalf("unexpected second declaration error: %v", err)
	}
	task, err := s.TaskCreate(ctx, map[string]any{"title": "delegated task"}, "", nil)
	if err != nil {
		t.Fatal(err)
	}
	taskID := task["task"].(map[string]any)["id"].(string)
	assigned, err := s.OrchAssign(ctx, orch["id"].(string), taskID, worker["id"].(string), "please handle", "assign-1")
	if err != nil {
		t.Fatal(err)
	}
	assignment := assigned["assignment"].(map[string]any)
	messageID := assignment["message_id"].(string)
	accepted, err := s.InboxAck(ctx, worker["id"].(string), messageID, "accept", "", "ack-1")
	if err != nil {
		t.Fatal(err)
	}
	if accepted["state"] != "acked" {
		t.Fatalf("ack response=%#v", accepted)
	}
	var state, assignee string
	if err := s.DB().QueryRow("SELECT state FROM assignment WHERE project_id=? AND task_id=?", p.ProjectID, taskID).Scan(&state); err != nil {
		t.Fatal(err)
	}
	if err := s.DB().QueryRow("SELECT assignee FROM task WHERE project_id=? AND id=?", p.ProjectID, taskID).Scan(&assignee); err != nil {
		t.Fatal(err)
	}
	if state != "accepted" || assignee != p.Callsign {
		t.Fatalf("assignment=%s assignee=%s", state, assignee)
	}
	if _, err := s.OrchRecall(ctx, orch["id"].(string), taskID, "priority changed"); err != nil {
		t.Fatal(err)
	}
	if err := s.DB().QueryRow("SELECT state FROM assignment WHERE project_id=? AND task_id=?", p.ProjectID, taskID).Scan(&state); err != nil {
		t.Fatal(err)
	}
	if state != "returned" {
		t.Fatalf("recalled assignment state=%s", state)
	}
}

func TestOrchestrationApprovalAndSpawnLink(t *testing.T) {
	s := orchestrationTestStore(t)
	now := time.Date(2026, 11, 23, 12, 0, 0, 0, time.UTC)
	reg, err := s.RegisterProject(Ctx{Now: now, Via: "test"}, "https://github.com/acme/relay-approval", "Relay Approval", "owner-human", "human", "", "")
	if err != nil {
		t.Fatal(err)
	}
	p, err := s.Authenticate(reg["token"].(string), &now, "test")
	if err != nil {
		t.Fatal(err)
	}
	ctx := Ctx{Now: now, Via: "test", Principal: p}
	orch, err := s.RegisterSession(ctx, map[string]any{"harness": "codex", "kind": "worker"})
	if err != nil {
		t.Fatal(err)
	}
	if _, err := s.OrchDeclare(ctx, orch["id"].(string)); err != nil {
		t.Fatal(err)
	}
	if _, err := s.DB().Exec("INSERT INTO relay_host(host_id,name,token_hash,owner_callsign,projects_json,harnesses_json) VALUES(?,?,?,?,?,?)", "H-test", "test host", HashToken("relay-token"), p.Callsign, MustJSON([]string{p.ProjectID}), MustJSON([]string{"codex"})); err != nil {
		t.Fatal(err)
	}
	requested, err := s.OrchRequestSession(ctx, orch["id"].(string), "H-test", "repo", "codex", "", "do work", "req-1")
	if err != nil {
		t.Fatal(err)
	}
	rid := requested["request"].(map[string]any)["id"].(string)
	decided, err := s.ApprovalDecide(ctx, rid, "approve", "approved")
	if err != nil || decided["request"].(map[string]any)["state"] != "approved" {
		t.Fatalf("decision=%#v err=%v", decided, err)
	}
	if _, err := s.DB().Exec("UPDATE session_request SET state='dispatched' WHERE project_id=? AND id=?", p.ProjectID, rid); err != nil {
		t.Fatal(err)
	}
	spawned, err := s.RegisterSession(ctx, map[string]any{"harness": "codex", "kind": "interactive", "spawn_request": rid})
	if err != nil {
		t.Fatal(err)
	}
	if spawned["kind"] != "worker" || spawned["allow_wait"] != true {
		t.Fatalf("spawn link did not set worker session: %#v", spawned)
	}
	var host string
	if err := s.DB().QueryRow("SELECT host_id FROM session WHERE project_id=? AND id=?", p.ProjectID, spawned["id"]).Scan(&host); err != nil {
		t.Fatal(err)
	}
	if host != "H-test" {
		t.Fatalf("spawned session host=%q", host)
	}
	stop, err := s.OrchRequestStop(ctx, orch["id"].(string), spawned["id"].(string), "finished")
	if err != nil {
		t.Fatal(err)
	}
	stopID := stop["request"].(map[string]any)["id"].(string)
	var stopKind, stopState string
	if err := s.DB().QueryRow("SELECT kind,state FROM session_request WHERE project_id=? AND id=?", p.ProjectID, stopID).Scan(&stopKind, &stopState); err != nil {
		t.Fatal(err)
	}
	if stopKind != "stop" || stopState != "pending_approval" {
		t.Fatalf("stop request kind=%s state=%s", stopKind, stopState)
	}
	rejected, err := s.ApprovalDecide(ctx, stopID, "reject", "keep running")
	if err != nil || rejected["request"].(map[string]any)["state"] != "rejected" {
		t.Fatalf("stop decision=%#v err=%v", rejected, err)
	}
}
