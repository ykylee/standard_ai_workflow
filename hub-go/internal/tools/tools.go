package tools

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"math"
	"sort"
	"strconv"
	"strings"

	"github.com/ykylee/standard_ai_workflow/hub-go/internal/store"
)

const (
	// Contract is the wire contract version enforced by HTTP and tool arguments.
	Contract = "hub/1"
	// KitVersion is the compatibility contract version emitted in healthz and response headers.
	KitVersion = store.HubKitVersion
)

// SealedAllowed enumerates tools permitted on sealed (migrated-away) projects.
var SealedAllowed = map[string]bool{
	"hub_project_lookup": true,
	"hub_project_export": true,
	"hub_project_unseal": true,
}

var taskValueKeys = []string{
	"title", "status", "priority", "branch", "wbs",
	"wbs_exempt_reason", "description", "plan_md", "fields",
}

// DecodeJSONValue decodes JSON bytes preserving exact distinction between integers and floats.
func DecodeJSONValue(raw []byte) (any, error) {
	dec := json.NewDecoder(bytes.NewReader(raw))
	dec.UseNumber()
	var val any
	if err := dec.Decode(&val); err != nil {
		return nil, err
	}
	var extra any
	if err := dec.Decode(&extra); err != io.EOF {
		return nil, fmt.Errorf("unexpected trailing JSON data")
	}
	return normalizeJSONValue(val), nil
}

func normalizeJSONValue(v any) any {
	switch tv := v.(type) {
	case json.Number:
		s := tv.String()
		if !strings.ContainsAny(s, ".eE") {
			if n, err := strconv.ParseInt(s, 10, 64); err == nil {
				if n >= math.MinInt && n <= math.MaxInt {
					return int(n)
				}
				return n
			}
		}
		if f, err := strconv.ParseFloat(s, 64); err == nil {
			return f
		}
		return s
	case map[string]any:
		out := make(map[string]any, len(tv))
		for k, item := range tv {
			out[k] = normalizeJSONValue(item)
		}
		return out
	case []any:
		out := make([]any, len(tv))
		for i, item := range tv {
			out[i] = normalizeJSONValue(item)
		}
		return out
	default:
		return v
	}
}

// VisibleTools returns bootstrap tools when unauthenticated, or the callsign bundle when authenticated.
func VisibleTools(authenticated bool) []*ToolSpec {
	kind := ""
	if authenticated {
		kind = "callsign"
	}
	return VisibleToolsFor(kind)
}

// VisibleToolsFor exposes only the tool bundle belonging to the caller's credential.
func VisibleToolsFor(kind string) []*ToolSpec {
	out := make([]*ToolSpec, 0, len(ToolOrder))
	for _, spec := range ToolOrder {
		if spec.Bundle == "bootstrap" || spec.Bundle == "token" && kind == "callsign" || spec.Bundle == "hub_admin" && kind == "admin" {
			out = append(out, spec)
		}
	}
	return out
}

func matchesJSONType(val any, want string) bool {
	switch want {
	case "string":
		_, ok := val.(string)
		return ok
	case "integer":
		switch val.(type) {
		case int, int64, int32:
			return true
		default:
			return false
		}
	case "object":
		switch val.(type) {
		case map[string]any, map[string]string:
			return true
		default:
			return false
		}
	case "array":
		switch val.(type) {
		case []any, []string, []map[string]any:
			return true
		default:
			return false
		}
	case "boolean":
		_, ok := val.(bool)
		return ok
	default:
		return true
	}
}

func formatWantType(raw any) string {
	switch tv := raw.(type) {
	case string:
		return tv
	case []string:
		return "[" + strings.Join(tv, ", ") + "]"
	default:
		return fmt.Sprint(raw)
	}
}

func checkPropType(val any, prop map[string]any) bool {
	rawType := prop["type"]
	switch want := rawType.(type) {
	case string:
		return matchesJSONType(val, want)
	case []string:
		for _, option := range want {
			if matchesJSONType(val, option) {
				return true
			}
		}
		return false
	default:
		return true
	}
}

// ValidateArgs checks tool argument keys, required fields, JSON types, and optional contract field.
func ValidateArgs(spec *ToolSpec, rawArgs any) (map[string]any, error) {
	var args map[string]any
	if rawArgs == nil {
		return nil, store.InvalidField("arguments", "객체여야 한다")
	}
	m, ok := rawArgs.(map[string]any)
	if !ok {
		return nil, store.InvalidField("arguments", "객체여야 한다")
	}
	args = m

	props := spec.AllProperties()
	var extra []string
	for k := range args {
		if k == "contract" {
			continue
		}
		if _, ok := props[k]; !ok {
			extra = append(extra, k)
		}
	}
	if len(extra) > 0 {
		sort.Strings(extra)
		return nil, store.UnknownField(extra)
	}

	for _, req := range spec.Required {
		if v, ok := args[req]; !ok || v == nil {
			return nil, store.InvalidField(req, "필수")
		}
	}

	for k, v := range args {
		if v == nil || k == "contract" {
			continue
		}
		prop := props[k]
		if !checkPropType(v, prop) {
			return nil, store.InvalidField(k, formatWantType(prop["type"])+" 이어야 한다")
		}
	}

	if rawContract, hasContract := args["contract"]; hasContract && rawContract != nil {
		if cs, ok := rawContract.(string); !ok || cs != Contract {
			return nil, &store.HubError{
				Status:  400,
				Code:    "unknown_contract",
				Message: fmt.Sprintf("모르는 계약 판: %v — 이 허브는 %s", rawContract, Contract),
				Detail:  map[string]any{"contract": rawContract},
			}
		}
	}

	clean := make(map[string]any, len(args))
	for k, v := range args {
		if k == "contract" {
			continue
		}
		clean[k] = v
	}
	return clean, nil
}

// Prepare authenticates the caller, validates tool args, checks sealed-project state, and scans secrets.
func Prepare(s *store.Store, name string, rawArgs any, ctx store.Ctx) (*ToolSpec, map[string]any, error) {
	spec, ok := Tools[name]
	if !ok {
		return nil, nil, &store.HubError{
			Status:  404,
			Code:    "unknown_tool",
			Message: "모르는 도구: " + name,
			Detail:  map[string]any{"tool": name},
		}
	}
	if spec.Bundle == "token" && (ctx.Principal == nil || ctx.Principal.Kind != "callsign") {
		if ctx.Principal == nil {
			return nil, nil, store.Unauthorized("")
		}
		return nil, nil, store.Forbidden("이 도구는 프로젝트 콜사인 토큰이 필요하다")
	}
	if spec.Bundle == "hub_admin" && (ctx.Principal == nil || ctx.Principal.Kind != "admin") {
		if ctx.Principal == nil {
			return nil, nil, store.Unauthorized("")
		}
		return nil, nil, store.Forbidden("이 도구는 hub admin 토큰이 필요하다")
	}
	clean, err := ValidateArgs(spec, rawArgs)
	if err != nil {
		return nil, nil, err
	}

	pid := ""
	if ctx.Principal != nil {
		pid = ctx.Principal.ProjectID
	} else {
		pid, _ = clean["project_id"].(string)
	}
	if pid != "" && !SealedAllowed[name] {
		movedTo, err := s.ProjectMoved(pid)
		if err != nil {
			return nil, nil, err
		}
		if movedTo != "" {
			return nil, nil, &store.HubError{
				Status:  410,
				Code:    "project_moved",
				Message: fmt.Sprintf("프로젝트 %s 는 %s 로 이전되어 봉인됐다", pid, movedTo),
				Detail:  map[string]any{"project_id": pid, "moved_to": movedTo},
			}
		}
	}

	scanTarget := make(map[string]any, len(clean))
	for k, v := range clean {
		if k == "token" {
			continue
		}
		scanTarget[k] = v
	}
	if err := store.ScanSecrets(scanTarget, ""); err != nil {
		return nil, nil, err
	}
	return spec, clean, nil
}

func strArg(args map[string]any, key, def string) string {
	raw, ok := args[key]
	if !ok || raw == nil {
		return def
	}
	s, ok := raw.(string)
	if !ok {
		return def
	}
	return s
}

func optStrArg(args map[string]any, key string) *string {
	raw, ok := args[key]
	if !ok || raw == nil {
		return nil
	}
	s, ok := raw.(string)
	if !ok {
		return nil
	}
	return &s
}

func intArg(args map[string]any, key string, def int) int {
	raw, ok := args[key]
	if !ok || raw == nil {
		return def
	}
	switch n := raw.(type) {
	case int:
		return n
	case int64:
		return int(n)
	case int32:
		return int(n)
	default:
		return def
	}
}

func optIntArg(args map[string]any, key string) *int {
	raw, ok := args[key]
	if !ok || raw == nil {
		return nil
	}
	switch n := raw.(type) {
	case int:
		v := n
		return &v
	case int64:
		v := int(n)
		return &v
	case int32:
		v := int(n)
		return &v
	default:
		return nil
	}
}

// Call executes the named hub tool under ctx using the single validation/auth gate.
func Call(s *store.Store, name string, rawArgs any, ctx store.Ctx) (result map[string]any, callErr error) {
	_, clean, err := Prepare(s, name, rawArgs, ctx)
	if err != nil {
		return nil, err
	}
	sessionID, _ := clean["session"].(string)
	if sessionID, ok := clean["session"].(string); ok && sessionID != "" &&
		name != "hub_session_update" && name != "hub_wait" && name != "hub_inbox_ack" &&
		name != "hub_orch_declare" && name != "hub_orch_transfer" {
		if err := s.Signal(ctx, sessionID); err != nil {
			return nil, err
		}
	}
	defer func() {
		if callErr != nil || result == nil || name == "hub_wait" || name == "hub_inbox_ack" || name == "hub_inbox_list" || name == "hub_session_end" || name == "hub_orch_declare" || name == "hub_orch_transfer" {
			return
		}
		if name == "hub_session_start" {
			if session, ok := result["session"].(map[string]any); ok {
				if id, ok := session["id"].(string); ok {
					sessionID = id
				}
			}
		}
		if sessionID == "" {
			return
		}
		inbox, err := s.InboxTake(ctx, sessionID, "piggyback")
		if err != nil {
			result, callErr = nil, err
			return
		}
		messages, _ := inbox["messages"].([]map[string]any)
		if len(messages) > 0 {
			result["hub_inbox"] = map[string]any{"for_session": sessionID, "messages": messages, "remaining": inbox["remaining"]}
		}
	}()
	jb := &JudgeBridge{Store: s}

	switch name {
	case "hub_harness_report":
		return s.HarnessReportSubmit(ctx, clean["report"])
	case "hub_harness_report_list":
		return s.HarnessReportList(ctx, strArg(clean, "status", ""), false)
	case "hub_harness_registry_list":
		return s.HarnessRegistryList(ctx, false)
	case "hub_approval_request":
		return s.ConfirmationRequest(ctx, strArg(clean, "session", ""), strArg(clean, "title", ""),
			strArg(clean, "question", ""), strArg(clean, "details", ""), clean["action"])
	case "hub_setup_plan":
		return setupPlan(s, ctx, clean)
	case "hub_setup_confirm":
		return setupConfirm(s, ctx, clean)
	case "hub_migrate_plan":
		return migratePlan(s, ctx, clean["scan"])
	case "hub_migrate_import":
		return migrateImport(s, ctx, clean)
	case "hub_migrate_marker":
		return migrateMarker(s, ctx, clean)
	case "hub_migrate_report":
		return migrateReport(s, ctx, strArg(clean, "migration_id", ""))
	case "hub_state":
		return hubState(s, ctx, strArg(clean, "callsign", ""))
	case "hub_project_doc_get":
		return s.ProjectDocGet(ctx, strArg(clean, "name", ""))
	case "hub_project_doc_put":
		return s.ProjectDocPut(ctx, strArg(clean, "name", ""), strArg(clean, "body", ""), optIntArg(clean, "expected_version"), strArg(clean, "approval_id", ""))
	case "hub_handoff_get":
		return s.HandoffGet(ctx, strArg(clean, "callsign", ""))
	case "hub_handoff_put":
		handoff, ok := clean["handoff"].(map[string]any)
		if !ok {
			return nil, store.InvalidField("handoff", "객체여야 한다")
		}
		return s.HandoffPut(ctx, optIntArg(clean, "expected_version"), handoff)
	case "hub_checkpoint_put":
		return s.CheckpointPut(ctx, clean["body"])
	case "hub_compact_resume":
		return s.CompactResume(ctx, clean["summary_ids"])
	case "hub_memory_entry_put":
		return s.MemoryEntryPut(ctx, clean["entry"], intArg(clean, "expected_version", 0))
	case "hub_memory_entry_get":
		return s.MemoryEntryGet(ctx, strArg(clean, "id", ""))
	case "hub_memory_entry_list":
		return s.MemoryEntryList(ctx)
	case "hub_wiki_import_dir":
		overwrite, _ := clean["overwrite"].(bool)
		return s.WikiImportDir(ctx, clean["files"], strArg(clean, "summary", ""), overwrite, strArg(clean, "request_id", ""))
	case "hub_project_export":
		return s.ProjectExport(ctx, strArg(clean, "seal_to", ""))
	case "hub_project_unseal":
		return s.ProjectUnseal(ctx)
	case "hub_project_import":
		return s.ProjectImport(ctx, strArg(clean, "invite", ""), clean["bundle"])
	case "hub_relay_invite":
		return s.RelayInvite(ctx)
	case "hub_relay_list":
		return s.RelayList(ctx)
	case "hub_relay_revoke":
		return s.RelayRevoke(ctx, strArg(clean, "host_id", ""))
	case "hub_wiki_remote_set":
		return s.WikiRemoteSet(ctx, strArg(clean, "fetch_url", ""))
	case "hub_wiki_lint":
		return wikiLint(s, ctx)
	case "hub_wiki_export":
		return wikiExport(s, ctx, strArg(clean, "format", ""), optStrArg(clean, "out_dir"), intArg(clean, "cursor", 0))
	case "hub_wiki_import_okf":
		return wikiImportOKF(s, ctx, clean["files"], strArg(clean, "summary", ""), strArg(clean, "request_id", ""))
	case "hub_guide_render":
		return guideRender(s, ctx, strArg(clean, "harness", ""), optStrArg(clean, "current"))
	case "hub_guide_get":
		return guideGet(s, ctx)
	case "hub_guide_propose":
		return s.GuidePropose(ctx, intArg(clean, "base_version", 0), strArg(clean, "body", ""), strArg(clean, "note", ""))
	case "hub_guide_decide":
		approve, _ := clean["approve"].(bool)
		return s.GuideDecide(ctx, strArg(clean, "proposal_id", ""), approve)
	case "hub_project_lookup":
		return s.LookupProject(strArg(clean, "remote_url", ""))
	case "hub_project_register":
		return s.RegisterProject(
			ctx,
			strArg(clean, "remote_url", ""),
			strArg(clean, "display_name", ""),
			strArg(clean, "callsign", ""),
			strArg(clean, "kind", ""),
			strArg(clean, "label", ""),
			strArg(clean, "host", ""),
		)
	case "hub_project_bind_remote":
		return s.BindRemote(ctx, strArg(clean, "remote_url", ""))
	case "hub_callsign_register":
		return s.RegisterCallsign(
			ctx,
			strArg(clean, "project_id", ""),
			strArg(clean, "callsign", ""),
			strArg(clean, "kind", ""),
			strArg(clean, "label", ""),
			strArg(clean, "host", ""),
		)
	case "hub_callsign_approve":
		return s.ApproveCallsign(ctx, strArg(clean, "callsign", ""))
	case "hub_whoami":
		p := ctx.Principal
		return map[string]any{
			"project_id":     p.ProjectID,
			"callsign":       p.Callsign,
			"kind":           p.CallsignKind,
			"human_approved": p.HumanApproved,
			"role":           p.Role,
		}, nil
	case "hub_wiki_ingest":
		return s.WikiIngest(ctx, clean["pages"], strArg(clean, "summary", ""), strArg(clean, "request_id", ""))
	case "hub_wiki_get":
		return s.WikiGet(ctx, strArg(clean, "path", ""))
	case "hub_wiki_list":
		return s.WikiList(ctx, strArg(clean, "prefix", ""))
	case "hub_wiki_search":
		return s.WikiSearch(ctx, strArg(clean, "query", ""), intArg(clean, "limit", 20))
	case "hub_knowledge_source_register":
		return s.KnowledgeSourceRegister(ctx, strArg(clean, "source_id", ""), strArg(clean, "repo_key", ""), clean["allowlist"])
	case "hub_knowledge_sync":
		return s.KnowledgeSync(ctx, strArg(clean, "source_id", ""), strArg(clean, "commit_sha", ""), clean["documents"])
	case "hub_knowledge_search":
		return s.KnowledgeSearch(ctx, strArg(clean, "query", ""), intArg(clean, "limit", 20))
	case "hub_knowledge_get":
		return s.KnowledgeGet(ctx, strArg(clean, "ref", ""))
	case "hub_idea_add":
		return s.IdeaAdd(ctx, clean["body"], clean["request_id"], false)
	case "hub_idea_list":
		return s.IdeaList(ctx, clean["status"])
	case "hub_idea_get":
		return s.IdeaGet(ctx, strArg(clean, "id", ""))
	case "hub_idea_claim":
		return s.IdeaClaim(ctx, strArg(clean, "id", ""))
	case "hub_idea_reply":
		return s.IdeaReply(ctx, clean)
	case "hub_dcr_create":
		return s.DCRCreate(ctx, strArg(clean, "title", ""), strArg(clean, "rationale", ""), strArg(clean, "proposal", ""), clean["target_refs"])
	case "hub_dcr_decide":
		return s.DCRDecide(ctx, strArg(clean, "id", ""), intArg(clean, "expected_version", 0), strArg(clean, "outcome", ""), strArg(clean, "rationale", ""))
	case "hub_dcr_list":
		return s.DCRList(ctx, strArg(clean, "status", ""))
	case "hub_dcr_get":
		return s.DCRGet(ctx, strArg(clean, "id", ""))
	case "hub_task_list":
		return s.TaskList(ctx, optStrArg(clean, "status"), optStrArg(clean, "assignee"), intArg(clean, "limit", 100), false)
	case "hub_task_get":
		return s.TaskGet(ctx, strArg(clean, "id", ""))
	case "hub_task_create":
		vals := map[string]any{}
		for _, k := range taskValueKeys {
			if v, ok := clean[k]; ok && v != nil {
				vals[k] = v
			}
		}
		return s.TaskCreate(ctx, vals, strArg(clean, "request_id", ""), jb.PrepareCreate)
	case "hub_task_update":
		states := map[string]string{}
		if rawStates, has := clean["decision_states"]; has && rawStates != nil {
			switch m := rawStates.(type) {
			case map[string]string:
				states = m
			case map[string]any:
				for k, v := range m {
					sv, ok := v.(string)
					if !ok {
						return nil, store.InvalidField("decision_states", "{D<n>: answered:<value> | proposed}")
					}
					states[k] = sv
				}
			default:
				return nil, store.InvalidField("decision_states", "{D<n>: answered:<value> | proposed}")
			}
		}
		vals := map[string]any{}
		if rawVals, ok := clean["values"].(map[string]any); ok && rawVals != nil {
			vals = rawVals
		}
		pid := ""
		if ctx.Principal != nil {
			pid = ctx.Principal.ProjectID
		}
		return s.TaskUpdate(
			ctx,
			strArg(clean, "id", ""),
			intArg(clean, "expected_version", 0),
			vals,
			strArg(clean, "request_id", ""),
			jb.PrepareUpdate(pid, states, optStrArg(clean, "note")),
		)
	case "hub_task_close":
		return jb.TaskClose(
			ctx,
			strArg(clean, "id", ""),
			intArg(clean, "expected_version", 0),
			strArg(clean, "validation_result", ""),
			strArg(clean, "request_id", ""),
		)
	case "hub_plan_respond":
		return jb.PlanRespond(ctx, strArg(clean, "task_id", ""), strArg(clean, "body", ""))
	case "hub_plan_status":
		return jb.PlanStatus(ctx, strArg(clean, "task_id", ""))
	case "hub_roadmap_get":
		return jb.RoadmapGet(ctx)
	case "hub_roadmap_put":
		return jb.RoadmapPut(ctx, strArg(clean, "path", ""), optIntArg(clean, "expected_version"), strArg(clean, "body", ""))
	case "hub_roadmap_state":
		return jb.RoadmapState(ctx)
	case "hub_task_claim":
		return s.TaskClaim(ctx, strArg(clean, "id", ""), strArg(clean, "request_id", ""))
	case "hub_task_release":
		return s.TaskRelease(ctx, strArg(clean, "id", ""), strArg(clean, "request_id", ""))
	case "hub_task_progress":
		return s.TaskProgress(ctx, strArg(clean, "id", ""), strArg(clean, "note", ""), strArg(clean, "request_id", ""))
	case "hub_task_link_commit":
		return s.TaskLinkCommit(ctx, strArg(clean, "id", ""), strArg(clean, "sha", ""), strArg(clean, "branch", ""), strArg(clean, "request_id", ""))
	case "hub_events":
		return s.Events(ctx, strArg(clean, "target_kind", ""), strArg(clean, "target_id", ""), intArg(clean, "after_seq", 0), intArg(clean, "limit", 200))
	case "hub_session_update":
		values := map[string]any{}
		for _, key := range []string{"kind", "allow_wait", "delivery", "harness_session_id"} {
			if value, ok := clean[key]; ok {
				values[key] = value
			}
		}
		return s.SessionUpdate(ctx, strArg(clean, "session", ""), values)
	case "hub_session_list":
		return s.SessionList(ctx, strArg(clean, "callsign", ""), strArg(clean, "status", ""))
	case "hub_session_start":
		out, err := sessionStart(s, ctx, clean)
		if err != nil {
			return nil, err
		}
		sid, _ := clean["session"].(string)
		if spec, ok := clean["session"].(map[string]any); ok {
			session, err := s.RegisterSession(ctx, spec)
			if err != nil {
				return nil, err
			}
			out["session"] = session
			sid, _ = session["id"].(string)
		}
		// 일하는 세션(worker)에는 아이디어를 싣지 않는다 — 인자가 아니라 등록된 종류를 본다
		if hub, ok := out["hub"].(map[string]any); ok && clean["repo_results"] == nil {
			kind, err := s.SessionKind(ctx, sid)
			if err != nil {
				return nil, err
			}
			if kind != "worker" {
				if hub["ideas"], err = s.IdeaWaiting(ctx); err != nil {
					return nil, err
				}
			}
		}
		return out, nil
	case "hub_session_end":
		handoff, ok := clean["handoff"].(map[string]any)
		if !ok {
			return nil, store.InvalidField("handoff", "객체여야 한다")
		}
		var expected *int
		if raw, exists := clean["expected_version"]; exists {
			expected = optIntArg(map[string]any{"v": raw}, "v")
		}
		progress, _ := clean["progress"].([]any)
		if progress == nil {
			progress = []any{}
		}
		return s.SessionEnd(ctx, strArg(clean, "session", ""), handoff, expected, progress)
	case "hub_inbox_list":
		return s.InboxList(ctx, strArg(clean, "session", ""), strArg(clean, "state", ""))
	case "hub_inbox_ack":
		return s.InboxAck(ctx, strArg(clean, "session", ""), strArg(clean, "message_id", ""),
			strArg(clean, "decision", ""), strArg(clean, "reason", ""), strArg(clean, "request_id", ""))
	case "hub_wait":
		return s.Wait(ctx, strArg(clean, "session", ""))
	case "hub_report":
		return s.Report(ctx, strArg(clean, "session", ""), strArg(clean, "task_id", ""),
			strArg(clean, "summary", ""), strArg(clean, "verification", ""), strArg(clean, "request_id", ""))
	case "hub_orch_declare":
		return s.OrchDeclare(ctx, strArg(clean, "session", ""))
	case "hub_orch_transfer":
		return s.OrchTransfer(ctx, strArg(clean, "session", ""))
	case "hub_orch_release":
		return s.OrchRelease(ctx, strArg(clean, "session", ""))
	case "hub_orch_halt":
		on, _ := clean["on"].(bool)
		return s.OrchHalt(ctx, on)
	case "hub_orch_assign":
		return s.OrchAssign(ctx, strArg(clean, "session", ""), strArg(clean, "task_id", ""),
			strArg(clean, "to_session", ""), strArg(clean, "note", ""), strArg(clean, "request_id", ""))
	case "hub_orch_recall":
		return s.OrchRecall(ctx, strArg(clean, "session", ""), strArg(clean, "task_id", ""), strArg(clean, "reason", ""))
	case "hub_orch_message":
		return s.OrchMessage(ctx, strArg(clean, "session", ""), strArg(clean, "to", ""), strArg(clean, "kind", ""), clean["body"], strArg(clean, "request_id", ""))
	case "hub_orch_request_session":
		return s.OrchRequestSession(ctx, strArg(clean, "session", ""), strArg(clean, "host_id", ""), strArg(clean, "dir_alias", ""),
			strArg(clean, "harness", ""), strArg(clean, "permission_mode", ""), strArg(clean, "prompt", ""), strArg(clean, "request_id", ""))
	case "hub_orch_request_stop":
		return s.OrchRequestStop(ctx, strArg(clean, "session", ""), strArg(clean, "target_session", ""), strArg(clean, "reason", ""))
	case "hub_approval_decide":
		return s.ApprovalDecide(ctx, strArg(clean, "request_id", ""), strArg(clean, "decision", ""), strArg(clean, "note", ""))
	default:
		return nil, &store.HubError{
			Status:  501,
			Code:    "not_implemented_in_go",
			Message: fmt.Sprintf("%s 는 Go 허브에 아직 포팅되지 않았다 (S2-c/d)", name),
			Detail:  map[string]any{"tool": name},
		}
	}
}
