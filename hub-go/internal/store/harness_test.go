package store

import (
	"path/filepath"
	"testing"
	"time"

	"github.com/ykylee/standard_ai_workflow/hub-go/internal/db"
)

func TestHarnessReportReviewAndRegistry(t *testing.T) {
	now := time.Date(2026, 11, 24, 12, 0, 0, 0, time.UTC)
	dbPath := filepath.Join(t.TempDir(), "hub.db")
	if _, err := db.OpenDB(dbPath, now); err != nil {
		t.Fatal(err)
	}
	s, err := New(dbPath)
	if err != nil {
		t.Fatal(err)
	}
	defer s.Close()
	project, err := s.RegisterProject(Ctx{Now: now, Via: "test"}, "https://github.com/acme/harness", "Harness", "owner-human", "human", "", "")
	if err != nil {
		t.Fatal(err)
	}
	owner, err := s.Authenticate(project["token"].(string), &now, "client-test")
	if err != nil {
		t.Fatal(err)
	}
	ownerCtx := Ctx{Now: now, Via: "mcp", Principal: owner, ClientVersion: "client-test"}
	adminToken, err := s.IssueHubToken("admin", "test-reviewer", now)
	if err != nil {
		t.Fatal(err)
	}
	admin, err := s.Authenticate(adminToken, &now, "")
	if err != nil {
		t.Fatal(err)
	}
	adminCtx := Ctx{Now: now, Via: "mcp", Principal: admin}
	report := map[string]any{
		"harness_id": "new-agent", "display_name": "New Agent", "version": "1.2.3",
		"platforms": []any{"windows"}, "mcp_transports": []any{"stdio"}, "config_formats": []any{"json"},
		"entry_file_candidates": []any{"AGENTS.md"}, "documentation_url": "https://example.com/docs", "notes": "Observed MCP support.",
	}
	submitted, err := s.HarnessReportSubmit(ownerCtx, report)
	if err != nil {
		t.Fatal(err)
	}
	reportID := submitted["report_id"].(string)
	if submitted["status"] != "pending" || submitted["registered"] != false {
		t.Fatalf("submit=%#v", submitted)
	}
	replay, err := s.HarnessReportSubmit(ownerCtx, report)
	if err != nil || replay["report_id"] != reportID || replay["replayed"] != true {
		t.Fatalf("dedupe replay=%#v err=%v", replay, err)
	}
	registry, err := s.HarnessRegistryList(ownerCtx, false)
	if err != nil || len(registry["harnesses"].([]map[string]any)) != 0 {
		t.Fatalf("pending report changed registry: %#v err=%v", registry, err)
	}
	if _, err = s.HarnessReportDecide(ownerCtx, reportID, "approve", "", nil); err == nil {
		t.Fatal("project owner used project token to alter the hub-global registry")
	}
	queue, err := s.HarnessReportList(adminCtx, "pending", true)
	if err != nil || len(queue["reports"].([]map[string]any)) != 1 {
		t.Fatalf("admin queue=%#v err=%v", queue, err)
	}
	person1, err := s.HarnessPersonCreate(adminCtx, "Registry Maintainer")
	if err != nil {
		t.Fatal(err)
	}
	person2, err := s.HarnessPersonCreate(adminCtx, "Compatibility Reviewer")
	if err != nil {
		t.Fatal(err)
	}
	if _, err = s.HarnessReportDecide(adminCtx, reportID, "approve", "", nil); err == nil {
		t.Fatal("approved registry without a designated human owner")
	}
	decision, err := s.HarnessReportDecide(adminCtx, reportID, "approve", "metadata reviewed", []string{
		person1["person"].(map[string]any)["id"].(string), person2["person"].(map[string]any)["id"].(string),
	})
	if err != nil || decision["registered"] != true || decision["setup_ready"] != false {
		t.Fatalf("decision=%#v err=%v", decision, err)
	}
	registry, err = s.HarnessRegistryList(ownerCtx, false)
	if err != nil || len(registry["harnesses"].([]map[string]any)) != 1 || registry["harnesses"].([]map[string]any)[0]["harness_id"] != "new-agent" {
		t.Fatalf("registry=%#v err=%v", registry, err)
	}
	if len(registry["harnesses"].([]map[string]any)[0]["owners"].([]map[string]any)) != 2 {
		t.Fatalf("expected two independently registered people: %#v", registry)
	}
	unsafe := map[string]any{"harness_id": "other", "display_name": "Other", "entry_file_candidates": []any{"../../secret"}}
	if _, err = s.HarnessReportSubmit(ownerCtx, unsafe); err == nil {
		t.Fatal("unsafe relative path accepted")
	}
	secret := map[string]any{"harness_id": "other", "display_name": "Other", "notes": "wfh_aaaaaaaaaaaaaaaaaaaaaaaa"}
	if _, err = s.HarnessReportSubmit(ownerCtx, secret); err == nil {
		t.Fatal("secret-shaped report text accepted")
	}
}
