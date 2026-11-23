package tools

import (
	"path/filepath"
	"testing"
	"time"

	"github.com/ykylee/standard_ai_workflow/hub-go/internal/db"
	"github.com/ykylee/standard_ai_workflow/hub-go/internal/store"
)

func openTestStore(t *testing.T) *store.Store {
	t.Helper()
	dbPath := filepath.Join(t.TempDir(), "hub.db")
	now := time.Date(2026, 11, 22, 12, 0, 0, 0, time.UTC)
	if _, err := db.OpenDB(dbPath, now); err != nil {
		t.Fatalf("OpenDB: %v", err)
	}
	s, err := store.New(dbPath)
	if err != nil {
		t.Fatalf("store.New: %v", err)
	}
	t.Cleanup(func() { _ = s.Close() })
	return s
}

func TestVisibleToolsAndSchemas(t *testing.T) {
	if len(ToolOrder) != 74 || len(Tools) != 74 {
		t.Fatalf("expected 74 tools, got order=%d map=%d", len(ToolOrder), len(Tools))
	}
	anon := VisibleTools(false)
	if len(anon) != 6 {
		t.Fatalf("expected 6 bootstrap tools, got %d", len(anon))
	}
	authed := VisibleTools(true)
	if len(authed) != 74 {
		t.Fatalf("expected 74 authed tools, got %d", len(authed))
	}
	listSchema := Tools["hub_task_list"].Schema()
	props := listSchema["properties"].(map[string]any)
	if _, ok := props["contract"]; !ok {
		t.Fatal("missing contract property")
	}
	if _, ok := props["session"]; !ok {
		t.Fatal("missing shared session property on token tool")
	}
	lookupSchema := Tools["hub_project_lookup"].Schema()
	lookupProps := lookupSchema["properties"].(map[string]any)
	if _, ok := lookupProps["session"]; ok {
		t.Fatal("bootstrap tool should not inject shared session property")
	}
}

func TestValidateAndCallCoreLifecycle(t *testing.T) {
	s := openTestStore(t)
	now := time.Date(2026, 11, 22, 12, 0, 0, 0, time.UTC)
	ctx := store.Ctx{Now: now, Via: "test"}

	reg, err := Call(s, "hub_project_register", map[string]any{
		"remote_url":   "git@github.com:Acme/Demo.git",
		"display_name": "Demo",
		"callsign":     "claude-a",
		"kind":         "human",
	}, ctx)
	if err != nil {
		t.Fatalf("register: %v", err)
	}
	tokA := reg["token"].(string)
	pA, err := s.Authenticate(tokA, &now, "test/1")
	if err != nil || pA == nil {
		t.Fatalf("auth A: %v %v", pA, err)
	}
	ctxA := store.Ctx{Now: now, Via: "test", Principal: pA}

	// Non-object arguments rejected
	if _, err := Call(s, "hub_project_lookup", "bogus", ctx); err == nil {
		t.Fatal("expected error for non-object arguments")
	}
	// Unknown field rejected
	if _, err := Call(s, "hub_task_create", map[string]any{"title": "x", "bogus": 1}, ctxA); err == nil {
		t.Fatal("expected unknown_field error")
	} else if he, ok := store.AsHubError(err); !ok || he.Code != "unknown_field" {
		t.Fatalf("expected unknown_field, got %v", err)
	}
	// Float rejected for integer field
	if _, err := Call(s, "hub_task_list", map[string]any{"limit": 1.5}, ctxA); err == nil {
		t.Fatal("expected invalid_field for float limit")
	}

	// Create task with plan_md & WBS not applicable (no roadmap)
	created, err := Call(s, "hub_task_create", map[string]any{
		"title":   "첫 task",
		"plan_md": "- C1 주장",
	}, ctxA)
	if err != nil {
		t.Fatalf("create: %v", err)
	}
	task := created["task"].(map[string]any)
	taskID := task["id"].(string)

	// Close gate requires validation_result and succeeds once provided
	if _, err := Call(s, "hub_task_close", map[string]any{
		"id":                taskID,
		"expected_version":  1,
		"validation_result": "",
	}, ctxA); err == nil {
		t.Fatal("expected gate_denied for empty validation_result")
	}
	closed, err := Call(s, "hub_task_close", map[string]any{
		"id":                taskID,
		"expected_version":  1,
		"validation_result": "go test ./... PASS",
	}, ctxA)
	if err != nil {
		t.Fatalf("close: %v", err)
	}
	if closed["task"].(map[string]any)["status"] != "done" {
		t.Fatalf("expected done, got %#v", closed)
	}

	// Active roadmap enforces WBS gate on task create
	_, err = Call(s, "hub_roadmap_put", map[string]any{
		"path": "M-001-core.md",
		"body": "---\nid: M-001\ntitle: Core\nsdlc_phase: design\nstatus: in_progress\norder: 1\n---\n\n# M-001\n\n## WBS\n- **WBS-1.1** Leaf task\n",
	}, ctxA)
	if err != nil {
		t.Fatalf("roadmap milestone put: %v", err)
	}
	_, err = Call(s, "hub_roadmap_put", map[string]any{
		"path": "index.md",
		"body": "---\nstatus: active\n---\n\n# Index\n\n## 마일스톤\n- **M-001** [design] Core — status: in_progress\n  - path: [M-001-core.md](M-001-core.md)\n",
	}, ctxA)
	if err != nil {
		t.Fatalf("roadmap index put: %v", err)
	}
	if _, err := Call(s, "hub_task_create", map[string]any{"title": "no wbs"}, ctxA); err == nil {
		t.Fatal("expected wbs_gate_denied")
	} else if he, ok := store.AsHubError(err); !ok || he.Code != "gate_denied" {
		t.Fatalf("expected gate_denied, got %v", err)
	}
	if _, err := Call(s, "hub_task_create", map[string]any{"title": "with wbs", "wbs": "M-001/WBS-1.1"}, ctxA); err != nil {
		t.Fatalf("task with valid wbs: %v", err)
	}
	rmState, err := Call(s, "hub_roadmap_state", map[string]any{}, ctxA)
	if err != nil {
		t.Fatalf("roadmap_state: %v", err)
	}
	if rmState["roadmap_state"] == nil {
		t.Fatalf("expected roadmap_state, got %#v", rmState)
	}
}
