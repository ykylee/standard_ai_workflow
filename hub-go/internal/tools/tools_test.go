package tools

import (
	"database/sql"
	"fmt"
	"path/filepath"
	"strings"
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
	if len(ToolOrder) != 91 || len(Tools) != 91 {
		t.Fatalf("expected 91 tools, got order=%d map=%d", len(ToolOrder), len(Tools))
	}
	anon := VisibleTools(false)
	if len(anon) != 6 {
		t.Fatalf("expected 6 bootstrap tools, got %d", len(anon))
	}
	authed := VisibleTools(true)
	if len(authed) != 91 {
		t.Fatalf("expected 91 callsign tools, got %d", len(authed))
	}
	admin := VisibleToolsFor("admin")
	if len(admin) != 6 {
		t.Fatalf("expected 6 admin-visible tools, got %d", len(admin))
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

func TestHarnessIntakeToolScopesAndDispatch(t *testing.T) {
	st := openTestStore(t)
	now := time.Date(2026, 11, 24, 12, 0, 0, 0, time.UTC)
	project, err := st.RegisterProject(store.Ctx{Now: now, Via: "test"}, "https://github.com/acme/intake", "Intake", "owner-human", "human", "", "")
	if err != nil {
		t.Fatal(err)
	}
	owner, err := st.Authenticate(project["token"].(string), &now, "client-test")
	if err != nil {
		t.Fatal(err)
	}
	ownerCtx := store.Ctx{Now: now, Via: "mcp", Principal: owner, ClientVersion: "client-test"}
	adminToken, err := st.IssueHubToken("admin", "reviewer", now)
	if err != nil {
		t.Fatal(err)
	}
	admin, err := st.Authenticate(adminToken, &now, "")
	if err != nil {
		t.Fatal(err)
	}
	adminCtx := store.Ctx{Now: now, Via: "mcp", Principal: admin}
	started, err := Call(st, "hub_session_start", map[string]any{"session": map[string]any{
		"harness": "tool-agent", "kind": "worker", "delivery": []any{"wait"},
	}}, ownerCtx)
	if err != nil {
		t.Fatal(err)
	}
	startHub := started["hub"].(map[string]any)
	if startHub["harness_support"].(map[string]any)["status"] != "unknown" {
		t.Fatalf("unknown harness was not flagged: %#v", started)
	}
	report := map[string]any{"harness_id": "tool-agent", "display_name": "Tool Agent", "platforms": []any{"linux"}, "entry_file_candidates": []any{"AGENTS.md"}}
	created, err := Call(st, "hub_harness_report", map[string]any{"report": report}, ownerCtx)
	if err != nil {
		t.Fatal(err)
	}
	if created["status"] != "pending" {
		t.Fatalf("report=%#v", created)
	}
	if _, err := Call(st, "hub_harness_admin_decide", map[string]any{"report_id": created["report_id"], "decision": "approve"}, adminCtx); err == nil {
		t.Fatal("human approval MCP tool must not exist")
	}
	registry, err := Call(st, "hub_harness_registry_list", map[string]any{}, ownerCtx)
	if err != nil || len(registry["harnesses"].([]map[string]any)) != 0 {
		t.Fatalf("registry=%#v err=%v", registry, err)
	}
	for _, spec := range VisibleToolsFor("callsign") {
		if spec.Bundle == "hub_admin" {
			t.Fatalf("callsign sees admin tool %q", spec.Name)
		}
	}
	adminVisible := map[string]bool{}
	for _, spec := range VisibleToolsFor("admin") {
		adminVisible[spec.Name] = true
	}
	if adminVisible["hub_harness_admin_reports"] || adminVisible["hub_harness_admin_decide"] {
		t.Fatalf("human review tools must not be exposed over MCP: %#v", adminVisible)
	}
}

func TestCallSessionAndInboxTools(t *testing.T) {
	st := openTestStore(t)
	now := time.Date(2026, 11, 22, 12, 0, 0, 0, time.UTC)
	reg, err := st.RegisterProject(store.Ctx{Now: now, Via: "test"}, "https://github.com/acme/session-tools", "session tools", "owner-human", "human", "", "")
	if err != nil {
		t.Fatal(err)
	}
	p, err := st.Authenticate(reg["token"].(string), &now, "test")
	if err != nil {
		t.Fatal(err)
	}
	sid := "S-20261122-aabbccdd"
	if _, err := st.DB().Exec(`INSERT INTO session (project_id,id,callsign,harness,kind,delivery_json,last_signal_at,started_at)
		VALUES (?,?,?,?,?,?,?,?)`, p.ProjectID, sid, p.Callsign, "codex", "interactive", `[]`, db.FormatISO(now), db.FormatISO(now)); err != nil {
		t.Fatal(err)
	}
	ctx := store.Ctx{Now: now, Via: "http", Principal: p}
	updated, err := Call(st, "hub_session_update", map[string]any{"session": sid, "kind": "worker", "delivery": []any{"wait"}}, ctx)
	if err != nil {
		t.Fatal(err)
	}
	view := updated["session"].(map[string]any)
	if view["kind"] != "worker" {
		t.Fatalf("session update not dispatched: %#v", updated)
	}
	inbox, err := Call(st, "hub_inbox_list", map[string]any{"session": sid}, ctx)
	if err != nil {
		t.Fatal(err)
	}
	if len(inbox["messages"].([]map[string]any)) != 0 {
		t.Fatalf("unexpected inbox: %#v", inbox)
	}
	if _, err := st.WriteTx(func(tx *sql.Tx) (map[string]any, error) {
		_, err := st.EnqueueMessage(tx, ctx, p.ProjectID, "session", sid, "note", map[string]any{"text": "hello"}, p.Callsign, "", false, "")
		return nil, err
	}); err != nil {
		t.Fatal(err)
	}
	listed, err := Call(st, "hub_task_list", map[string]any{"session": sid}, ctx)
	if err != nil {
		t.Fatal(err)
	}
	if _, ok := listed["hub_inbox"]; !ok {
		t.Fatalf("expected piggyback inbox: %#v", listed)
	}
	started, err := Call(st, "hub_session_start", map[string]any{"session": map[string]any{"harness": "codex", "kind": "worker"}}, ctx)
	if err != nil {
		t.Fatal(err)
	}
	if started["phase"] != 1 || started["session"].(map[string]any)["resumed"] != false {
		t.Fatalf("unexpected session start response: %#v", started)
	}
	checked, err := Call(st, "hub_session_start", map[string]any{"repo_results": map[string]any{
		"fetch":        map[string]any{"rc": 0, "output": ""},
		"status":       map[string]any{"rc": 0, "output": "# branch.upstream origin/main\n# branch.ab +0 -0\n"},
		"check_ignore": map[string]any{"rc": 0, "output": ".gitignore:1:/.workflow-hub/ .workflow-hub/env\n"},
	}}, ctx)
	if err != nil || checked["phase"] != 2 || checked["verdict"] != "start" {
		t.Fatalf("unexpected session start verdict: %#v err=%v", checked, err)
	}
	sessionID := started["session"].(map[string]any)["id"].(string)
	ended, err := Call(st, "hub_session_end", map[string]any{"session": sessionID, "handoff": map[string]any{}}, ctx)
	if err != nil || ended["progress_written"] != 0 {
		t.Fatalf("unexpected session end: %#v err=%v", ended, err)
	}
	if _, attached := ended["hub_inbox"]; attached {
		t.Fatalf("session end must not piggyback: %#v", ended)
	}
}

func TestGuideAndSetupToolsAreImplemented(t *testing.T) {
	st := openTestStore(t)
	now := time.Date(2026, 11, 24, 12, 0, 0, 0, time.UTC)
	bootstrap := store.Ctx{Now: now, Via: "http", PublicURL: "https://hub.example/workflow"}
	reg, err := st.RegisterProject(bootstrap, "https://github.com/acme/guide-tools", "Guide Tools", "guide-owner", "human", "", "")
	if err != nil {
		t.Fatal(err)
	}
	projectID, token := reg["project_id"].(string), reg["token"].(string)
	principal, err := st.Authenticate(token, &now, "test")
	if err != nil {
		t.Fatal(err)
	}
	ctx := store.Ctx{Now: now, Via: "http", Principal: principal, PublicURL: bootstrap.PublicURL}

	plan, err := Call(st, "hub_setup_plan", map[string]any{"project_id": projectID, "token": token, "harnesses": []any{"codex"}, "scan": map[string]any{"files": map[string]any{".gitignore": "node_modules/\n"}, "relay": map[string]any{"required": false}}}, bootstrap)
	if err != nil || plan["stage"] != "gitignore" {
		t.Fatalf("setup plan was not dispatched: %#v err=%v", plan, err)
	}
	if _, err := st.DB().Exec("UPDATE setup_step SET status='confirmed' WHERE project_id=? AND callsign=? AND step_id='gitignore'", projectID, principal.Callsign); err != nil {
		t.Fatal(err)
	}
	plan, err = Call(st, "hub_setup_plan", map[string]any{"project_id": projectID, "token": token, "harnesses": []any{"codex"}, "scan": map[string]any{"files": map[string]any{}, "relay": map[string]any{"required": false}}}, bootstrap)
	if err != nil || plan["stage"] != "files" {
		t.Fatalf("setup file plan was not dispatched: %#v err=%v", plan, err)
	}
	legacyStart := "- Restore the session with `python -m workflow_kit session-start` — it reads `ai-workflow/memory/active/<branch>/` (`state.json`, handoff, backlog), `docs/PROJECT_PROFILE.md`, and `PURPOSE.md` (`<branch>` = current git branch)."
	legacyEntry := "# Project\n\n" + legacyStart + "\n\n<!-- standard-ai-workflow-kit: v1.29.0 -->\n\n## User notes\nKeep this paragraph.\n"
	legacyPlan, err := Call(st, "hub_setup_plan", map[string]any{"project_id": projectID, "token": token, "harnesses": []any{"codex"}, "scan": map[string]any{"files": map[string]any{"AGENTS.md": legacyEntry}, "relay": map[string]any{"required": false}}}, bootstrap)
	if err != nil {
		t.Fatalf("legacy setup plan failed: %v", err)
	}
	legacyBlocked := false
	for _, row := range legacyPlan["blocked"].([]any) {
		if row.(map[string]any)["id"] == "entry:codex" {
			legacyBlocked = true
		}
	}
	if !legacyBlocked {
		t.Fatalf("legacy entrypoint must remain unchanged before migration marker: %#v", legacyPlan)
	}
	marker := fmt.Sprintf(`{"format":"workflow-hub-migrated/1","hub":%q,"project_id":%q}`, bootstrap.PublicURL, projectID)
	readyPlan, err := Call(st, "hub_setup_plan", map[string]any{"project_id": projectID, "token": token, "harnesses": []any{"codex"}, "scan": map[string]any{"files": map[string]any{"AGENTS.md": legacyEntry, "ai-workflow/HUB_MIGRATED.json": marker}, "relay": map[string]any{"required": false}}}, bootstrap)
	if err != nil {
		t.Fatalf("post-migration setup plan failed: %v", err)
	}
	updatedEntry := ""
	for _, row := range readyPlan["steps"].([]any) {
		step, ok := row.(map[string]any)
		if ok && step["id"] == "entry:codex" {
			updatedEntry = step["content"].(string)
		}
	}
	if updatedEntry == "" || strings.Contains(updatedEntry, legacyStart) || !strings.Contains(updatedEntry, "hub_session_start") || !strings.Contains(updatedEntry, "## User notes\nKeep this paragraph.") {
		t.Fatalf("post-migration entrypoint should use Hub start and preserve user text: %#v", readyPlan)
	}
	customEntry := strings.Replace(legacyEntry, legacyStart, "- Locally customized 1.x startup instructions.", 1)
	customPlan, err := Call(st, "hub_setup_plan", map[string]any{"project_id": projectID, "token": token, "harnesses": []any{"codex"}, "scan": map[string]any{"files": map[string]any{"AGENTS.md": customEntry, "ai-workflow/HUB_MIGRATED.json": marker}, "relay": map[string]any{"required": false}}}, bootstrap)
	if err != nil {
		t.Fatalf("custom legacy setup plan failed: %v", err)
	}
	customBlocked := false
	for _, row := range customPlan["blocked"].([]any) {
		if row.(map[string]any)["reason"] == "legacy_entry_needs_review" {
			customBlocked = true
		}
	}
	if !customBlocked {
		t.Fatalf("custom legacy startup text must require review, got %#v", customPlan)
	}

	guide, err := Call(st, "hub_guide_get", map[string]any{}, ctx)
	if err != nil || guide["version"] != 0 {
		t.Fatalf("guide get was not dispatched: %#v err=%v", guide, err)
	}
	if _, err := Call(st, "hub_guide_propose", map[string]any{"base_version": 0, "body": "Use the project's documented conventions."}, ctx); err != nil {
		t.Fatalf("guide proposal failed: %v", err)
	}
	guide, err = Call(st, "hub_guide_get", map[string]any{}, ctx)
	if err != nil || guide["version"] != 1 || len(guide["history"].([]map[string]any)) != 1 || len(guide["proposals"].([]map[string]any)) != 1 {
		t.Fatalf("guide history/proposal response was not dispatched: %#v err=%v", guide, err)
	}
	rendered, err := Call(st, "hub_guide_render", map[string]any{"harness": "codex"}, ctx)
	if err != nil || rendered["blocked"] != false {
		t.Fatalf("guide render was not dispatched: %#v err=%v", rendered, err)
	}
	step := rendered["step"].(map[string]any)
	if step["path"] != "AGENTS.md" || !strings.Contains(step["content"].(string), "workflow-hub:begin") {
		t.Fatalf("unexpected render output: %#v", rendered)
	}
	modified := strings.Replace(step["content"].(string), "Use the project's documented conventions.", "locally changed guidance", 1)
	blocked, err := Call(st, "hub_guide_render", map[string]any{"harness": "codex", "current": modified}, ctx)
	if err != nil || blocked["blocked"] != true || blocked["reason"] != "local_edit_detected" {
		t.Fatalf("local guide edit was not protected: %#v err=%v", blocked, err)
	}
}

func TestCallOrchestratorTools(t *testing.T) {
	st := openTestStore(t)
	now := time.Date(2026, 11, 22, 12, 0, 0, 0, time.UTC)
	reg, err := st.RegisterProject(store.Ctx{Now: now, Via: "test"}, "https://github.com/acme/orch-tools", "Orch Tools", "owner-human", "human", "", "")
	if err != nil {
		t.Fatal(err)
	}
	p, err := st.Authenticate(reg["token"].(string), &now, "test")
	if err != nil {
		t.Fatal(err)
	}
	ctx := store.Ctx{Now: now, Via: "test", Principal: p}
	session, err := st.RegisterSession(ctx, map[string]any{"harness": "codex", "kind": "worker"})
	if err != nil {
		t.Fatal(err)
	}
	sid := session["id"].(string)
	declared, err := Call(st, "hub_orch_declare", map[string]any{"session": sid}, ctx)
	if err != nil || declared["orchestrator"] == nil {
		t.Fatalf("declare=%#v err=%v", declared, err)
	}
	second, err := st.RegisterSession(ctx, map[string]any{"harness": "codex", "harness_session_id": "second-orch", "kind": "worker"})
	if err != nil {
		t.Fatal(err)
	}
	transferred, err := Call(st, "hub_orch_transfer", map[string]any{"session": second["id"]}, ctx)
	if err != nil || transferred["orchestrator"] == nil {
		t.Fatalf("transfer=%#v err=%v", transferred, err)
	}
	if _, err := Call(st, "hub_orch_transfer", map[string]any{"session": sid}, ctx); err != nil {
		t.Fatal(err)
	}
	halted, err := Call(st, "hub_orch_halt", map[string]any{"on": true}, ctx)
	if err != nil || halted["halted"] != true {
		t.Fatalf("halt=%#v err=%v", halted, err)
	}
	resumed, err := Call(st, "hub_orch_halt", map[string]any{"on": false}, ctx)
	if err != nil || resumed["halted"] != false {
		t.Fatalf("resume=%#v err=%v", resumed, err)
	}
	worker, err := st.RegisterSession(ctx, map[string]any{"harness": "codex", "harness_session_id": "worker", "kind": "worker", "delivery": []any{"wait"}})
	if err != nil {
		t.Fatal(err)
	}
	task, err := st.TaskCreate(ctx, map[string]any{"title": "tool routed task"}, "", nil)
	if err != nil {
		t.Fatal(err)
	}
	taskID := task["task"].(map[string]any)["id"].(string)
	assigned, err := Call(st, "hub_orch_assign", map[string]any{"session": sid, "task_id": taskID, "to_session": worker["id"], "request_id": "routed-assign"}, ctx)
	if err != nil || assigned["assignment"] == nil {
		t.Fatalf("assign=%#v err=%v", assigned, err)
	}
	if _, err := Call(st, "hub_orch_recall", map[string]any{"session": sid, "task_id": taskID, "reason": "change"}, ctx); err != nil {
		t.Fatal(err)
	}
	message, err := Call(st, "hub_orch_message", map[string]any{"session": sid, "to": worker["id"], "body": map[string]any{"text": "hello"}, "request_id": "routed-message"}, ctx)
	if err != nil || message["message_id"] == nil {
		t.Fatalf("message=%#v err=%v", message, err)
	}
	if _, err := st.DB().Exec("INSERT INTO relay_host(host_id,name,token_hash,owner_callsign,projects_json,harnesses_json) VALUES(?,?,?,?,?,?)", "H-routed", "host", store.HashToken("relay-token"), p.Callsign, store.MustJSON([]string{p.ProjectID}), store.MustJSON([]string{"codex"})); err != nil {
		t.Fatal(err)
	}
	request, err := Call(st, "hub_orch_request_session", map[string]any{"session": sid, "host_id": "H-routed", "dir_alias": "repo", "harness": "codex"}, ctx)
	if err != nil {
		t.Fatal(err)
	}
	requestID := request["request"].(map[string]any)["id"].(string)
	if _, err := Call(st, "hub_approval_decide", map[string]any{"request_id": requestID, "decision": "approve"}, ctx); err != nil {
		t.Fatal(err)
	}
	if _, err := st.DB().Exec("UPDATE session SET host_id='H-routed' WHERE project_id=? AND id=?", p.ProjectID, worker["id"]); err != nil {
		t.Fatal(err)
	}
	stop, err := Call(st, "hub_orch_request_stop", map[string]any{"session": sid, "target_session": worker["id"], "reason": "stop"}, ctx)
	if err != nil {
		t.Fatal(err)
	}
	stopID := stop["request"].(map[string]any)["id"].(string)
	if _, err := Call(st, "hub_approval_decide", map[string]any{"request_id": stopID, "decision": "reject", "note": "keep running"}, ctx); err != nil {
		t.Fatal(err)
	}
	released, err := Call(st, "hub_orch_release", map[string]any{}, ctx)
	if err != nil || released["released"] != true {
		t.Fatalf("release=%#v err=%v", released, err)
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
