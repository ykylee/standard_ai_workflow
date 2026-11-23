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
	// KitVersion matches workflow_kit.__version__ emitted in healthz and response headers.
	KitVersion = "2.1.0"
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

// VisibleTools returns bootstrap tools when unauthenticated, or all 74 tools when authenticated.
func VisibleTools(authenticated bool) []*ToolSpec {
	out := make([]*ToolSpec, 0, len(ToolOrder))
	for _, spec := range ToolOrder {
		if authenticated || spec.Bundle == "bootstrap" {
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
	if spec.Bundle != "bootstrap" {
		if ctx.Principal == nil {
			return nil, nil, store.Unauthorized("")
		}
		if ctx.Principal.Kind != "callsign" {
			return nil, nil, store.Forbidden("이 도구는 콜사인 토큰이 필요하다 (web · admin 토큰은 쓸 수 없다)")
		}
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
func Call(s *store.Store, name string, rawArgs any, ctx store.Ctx) (map[string]any, error) {
	_, clean, err := Prepare(s, name, rawArgs, ctx)
	if err != nil {
		return nil, err
	}
	jb := &JudgeBridge{Store: s}

	switch name {
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
	default:
		return nil, &store.HubError{
			Status:  501,
			Code:    "not_implemented_in_go",
			Message: fmt.Sprintf("%s 는 Go 허브에 아직 포팅되지 않았다 (S2-c/d)", name),
			Detail:  map[string]any{"tool": name},
		}
	}
}
