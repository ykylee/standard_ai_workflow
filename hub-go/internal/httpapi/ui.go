package httpapi

import (
	"database/sql"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"path"
	"regexp"
	"sort"
	"strconv"
	"strings"
	"time"

	"github.com/ykylee/standard_ai_workflow/hub-go/internal/judge"
	"github.com/ykylee/standard_ai_workflow/hub-go/internal/store"
	"github.com/ykylee/standard_ai_workflow/hub-go/internal/tools"
)

func (s *Server) handleUIAPI(w http.ResponseWriter, r *http.Request) {
	for k, v := range screenHeaders {
		w.Header().Set(k, v)
	}
	w.Header().Set("Cache-Control", "no-store")
	s.writeHubHeaders(w)
	if r.Method != http.MethodGet && r.Method != http.MethodPost {
		writeJSONResponse(w, http.StatusMethodNotAllowed, map[string]any{"error_code": "method_not_allowed", "message": "GET · POST 만 지원한다", "detail": map[string]any{}})
		return
	}
	now := s.cfg.Clock().UTC().Truncate(time.Second)
	principal, err := s.screenPrincipal(r, now)
	if err != nil {
		writeScreenError(w, err)
		return
	}
	switch r.URL.Path {
	case "/api/session":
		writeJSONResponse(w, http.StatusOK, map[string]any{"principal": principalSummary(principal), "web_token": s.cfg.WebTokenName != ""})
	case "/api/projects":
		pid := ""
		if principal.Kind == "callsign" {
			pid = principal.ProjectID
		}
		projects, listErr := s.screenProjects(pid)
		if listErr != nil {
			writeScreenError(w, listErr)
			return
		}
		writeJSONResponse(w, http.StatusOK, map[string]any{"projects": projects, "principal": principalSummary(principal)})
	case "/api/harness-reports":
		if principal.Kind != "admin" {
			writeScreenError(w, store.Forbidden("허브 관리자 웹 토큰만 하네스 제보를 검토할 수 있다"))
			return
		}
		if r.Method != http.MethodGet {
			writeJSONResponse(w, http.StatusMethodNotAllowed, map[string]any{"error_code": "method_not_allowed", "message": "GET 만 지원한다", "detail": map[string]any{}})
			return
		}
		result, err := s.cfg.Store.HarnessReportList(store.Ctx{Now: now, Via: "ui", Principal: principal}, r.URL.Query().Get("status"), true)
		if err != nil {
			writeScreenError(w, err)
			return
		}
		writeJSONResponse(w, http.StatusOK, result)
	case "/api/harness-people":
		if principal.Kind != "admin" {
			writeScreenError(w, store.Forbidden("허브 관리자 웹 토큰만 사람 명부를 관리할 수 있다"))
			return
		}
		ctx := store.Ctx{Now: now, Via: "ui", Principal: principal}
		if r.Method == http.MethodGet {
			result, err := s.cfg.Store.HarnessPeopleList(ctx)
			if err != nil {
				writeScreenError(w, err)
				return
			}
			writeJSONResponse(w, http.StatusOK, result)
			return
		}
		body, err := readScreenJSON(r)
		if err != nil {
			writeScreenError(w, err)
			return
		}
		name, ok := body["display_name"].(string)
		if !ok {
			writeScreenError(w, store.InvalidField("display_name", "문자열이어야 한다"))
			return
		}
		result, err := s.cfg.Store.HarnessPersonCreate(ctx, name)
		if err != nil {
			writeScreenError(w, err)
			return
		}
		writeJSONResponse(w, http.StatusOK, result)
		return
	case "/api/harness-registry":
		if principal.Kind != "admin" {
			writeScreenError(w, store.Forbidden("허브 관리자 웹 토큰만 전역 등록부를 조회할 수 있다"))
			return
		}
		if r.Method != http.MethodGet {
			writeJSONResponse(w, http.StatusMethodNotAllowed, map[string]any{"error_code": "method_not_allowed", "message": "GET 만 지원한다", "detail": map[string]any{}})
			return
		}
		result, err := s.cfg.Store.HarnessRegistryList(store.Ctx{Now: now, Via: "ui", Principal: principal}, true)
		if err != nil {
			writeScreenError(w, err)
			return
		}
		writeJSONResponse(w, http.StatusOK, result)
	default:
		if strings.HasPrefix(r.URL.Path, "/api/harness-reports/") {
			s.handleHarnessDecisionUIAPI(w, r, principal, now)
			return
		}
		s.handleProjectUIAPI(w, r, principal, now)
	}
}

func (s *Server) handleHarnessDecisionUIAPI(w http.ResponseWriter, r *http.Request, principal *store.Principal, now time.Time) {
	if principal.Kind != "admin" {
		writeScreenError(w, store.Forbidden("허브 관리자 웹 토큰만 하네스 제보를 결정할 수 있다"))
		return
	}
	parts := strings.Split(strings.TrimPrefix(r.URL.Path, "/api/harness-reports/"), "/")
	if len(parts) != 2 || parts[0] == "" || parts[1] != "decision" || r.Method != http.MethodPost {
		writeJSONResponse(w, http.StatusNotFound, map[string]any{"error_code": "not_found", "message": "없는 하네스 화면 API", "detail": map[string]any{}})
		return
	}
	reportID, err := url.PathUnescape(parts[0])
	if err != nil || reportID == "" {
		writeScreenError(w, store.InvalidField("report_id", "경로 인코딩"))
		return
	}
	body, err := readScreenJSON(r)
	if err != nil {
		writeScreenError(w, err)
		return
	}
	decision, ok := body["decision"].(string)
	if !ok {
		writeScreenError(w, store.InvalidField("decision", "문자열이어야 한다"))
		return
	}
	note, _ := body["note"].(string)
	ownerIDs := []string{}
	if raw, exists := body["owner_ids"]; exists {
		values, ok := raw.([]any)
		if !ok {
			writeScreenError(w, store.InvalidField("owner_ids", "문자열 목록이어야 한다"))
			return
		}
		for _, value := range values {
			id, ok := value.(string)
			if !ok {
				writeScreenError(w, store.InvalidField("owner_ids", "문자열 목록이어야 한다"))
				return
			}
			ownerIDs = append(ownerIDs, id)
		}
	}
	result, err := s.cfg.Store.HarnessReportDecide(store.Ctx{Now: now, Via: "ui", Principal: principal}, reportID, decision, note, ownerIDs)
	if err != nil {
		writeScreenError(w, err)
		return
	}
	writeJSONResponse(w, http.StatusOK, result)
}

func (s *Server) handleProjectUIAPI(w http.ResponseWriter, r *http.Request, principal *store.Principal, now time.Time) {
	parts := strings.Split(strings.TrimPrefix(r.URL.Path, "/api/"), "/")
	if len(parts) < 2 || parts[0] != "projects" || parts[1] == "" {
		writeJSONResponse(w, http.StatusNotFound, map[string]any{"error_code": "not_found", "message": "없는 화면 API", "detail": map[string]any{}})
		return
	}
	pid, err := url.PathUnescape(parts[1])
	if err != nil || pid == "" {
		writeScreenError(w, store.InvalidField("project_id", "경로 인코딩"))
		return
	}
	if principal.Kind == "callsign" && principal.ProjectID != pid {
		writeScreenError(w, store.Forbidden("이 토큰의 프로젝트가 아니다"))
		return
	}
	moved, err := s.cfg.Store.ProjectMoved(pid)
	if err != nil {
		writeScreenError(w, err)
		return
	}
	if moved != "" {
		writeScreenError(w, &store.HubError{Status: http.StatusGone, Code: "project_moved", Message: "프로젝트가 다른 허브로 이동했다", Detail: map[string]any{"project_id": pid, "to": moved}})
		return
	}
	projectRows, err := s.screenProjects(pid)
	if err != nil {
		writeScreenError(w, err)
		return
	}
	if len(projectRows) == 0 {
		writeScreenError(w, store.NotFound("프로젝트가 없다: "+pid))
		return
	}
	viewer := &store.Principal{Kind: "viewer", ProjectID: pid, Callsign: principal.Callsign, CallsignKind: principal.CallsignKind, HumanApproved: principal.HumanApproved, Role: principal.Role, Name: principal.Name}
	ctx := store.Ctx{Now: now, Via: "ui", Principal: viewer, PublicURL: s.cfg.PublicURL}
	if len(parts) == 2 && r.Method == http.MethodGet {
		result, err := s.screenProjectSummary(pid, projectRows[0], ctx, principal)
		if err != nil {
			writeScreenError(w, err)
			return
		}
		writeJSONResponse(w, http.StatusOK, result)
		return
	}
	if len(parts) == 3 && parts[2] == "tasks" && r.Method == http.MethodGet {
		filters := map[string]string{}
		for _, key := range []string{"status", "roadmap", "milestone", "wbs", "category_level_1", "category_level_2", "category_level_3"} {
			filters[key] = r.URL.Query().Get(key)
		}
		result, err := s.cfg.Store.TaskListPage(ctx, filters, queryInt(r, "limit", 25), queryInt(r, "offset", 0))
		if err != nil {
			writeScreenError(w, err)
			return
		}
		writeJSONResponse(w, http.StatusOK, result)
		return
	}
	if len(parts) == 4 && parts[2] == "tasks" && r.Method == http.MethodGet {
		result, err := s.screenTask(pid, parts[3], ctx)
		if err != nil {
			writeScreenError(w, err)
			return
		}
		writeJSONResponse(w, http.StatusOK, result)
		return
	}
	if len(parts) == 5 && parts[2] == "tasks" && parts[4] == "responses" && r.Method == http.MethodPost {
		if principal.Kind != "callsign" {
			writeScreenError(w, store.Forbidden("결정 답은 콜사인 토큰으로만 쓴다 (화면 공용 토큰은 읽기 · 등록만)"))
			return
		}
		if principal.ProjectID != pid {
			writeScreenError(w, store.Forbidden("이 토큰의 프로젝트가 아니다"))
			return
		}
		body, err := readScreenJSON(r)
		if err != nil {
			writeScreenError(w, err)
			return
		}
		result, err := s.screenPlanResponse(pid, parts[3], body, principal, now)
		if err != nil {
			writeScreenError(w, err)
			return
		}
		writeJSONResponse(w, http.StatusOK, result)
		return
	}
	if len(parts) == 3 && parts[2] == "callsigns" && r.Method == http.MethodGet {
		result, err := s.screenCallsignBoard(pid)
		if err != nil {
			writeScreenError(w, err)
			return
		}
		writeJSONResponse(w, http.StatusOK, result)
		return
	}
	if len(parts) == 4 && parts[2] == "callsigns" && r.Method == http.MethodGet {
		result, err := s.screenCallsign(pid, parts[3], ctx)
		if err != nil {
			writeScreenError(w, err)
			return
		}
		writeJSONResponse(w, http.StatusOK, result)
		return
	}
	if len(parts) == 3 && parts[2] == "callsigns" && r.Method == http.MethodPost {
		body, err := readScreenJSON(r)
		if err != nil {
			writeScreenError(w, err)
			return
		}
		callsign, ok1 := body["callsign"].(string)
		kind, ok2 := body["kind"].(string)
		label, ok3 := body["label"].(string)
		if _, exists := body["callsign"]; exists && !ok1 {
			writeScreenError(w, store.InvalidField("callsign", "문자열이어야 한다"))
			return
		}
		if _, exists := body["kind"]; exists && !ok2 {
			writeScreenError(w, store.InvalidField("kind", "문자열이어야 한다"))
			return
		}
		if _, exists := body["label"]; exists && !ok3 {
			writeScreenError(w, store.InvalidField("label", "문자열이어야 한다"))
			return
		}
		ctxWrite := store.Ctx{Now: now, Via: "ui", Principal: principal, PublicURL: s.cfg.PublicURL}
		result, err := s.cfg.Store.RegisterCallsign(ctxWrite, pid, callsign, kind, label, "browser")
		if err != nil {
			writeScreenError(w, err)
			return
		}
		writeJSONResponse(w, http.StatusOK, result)
		return
	}
	if len(parts) == 5 && parts[2] == "callsigns" && parts[4] == "approve" && r.Method == http.MethodPost {
		if principal.Kind != "callsign" || principal.ProjectID != pid {
			writeScreenError(w, store.Forbidden("승인은 이 프로젝트의 소유자 콜사인 토큰으로만 한다"))
			return
		}
		if _, err := readScreenJSON(r); err != nil {
			writeScreenError(w, err)
			return
		}
		result, err := s.cfg.Store.ApproveCallsign(store.Ctx{Now: now, Via: "ui", Principal: principal}, parts[3])
		if err != nil {
			writeScreenError(w, err)
			return
		}
		writeJSONResponse(w, http.StatusOK, result)
		return
	}
	if len(parts) == 3 && parts[2] == "events" && r.Method == http.MethodGet {
		args := map[string]any{"limit": queryInt(r, "limit", 200), "after_seq": queryInt(r, "after_seq", 0)}
		for _, key := range []string{"target_kind", "target_id"} {
			if value := r.URL.Query().Get(key); value != "" {
				args[key] = value
			}
		}
		result, err := s.cfg.Store.Events(ctx, stringArg(args, "target_kind"), stringArg(args, "target_id"), args["after_seq"].(int), args["limit"].(int))
		if err != nil {
			writeScreenError(w, err)
			return
		}
		writeJSONResponse(w, http.StatusOK, result)
		return
	}
	if len(parts) == 3 && parts[2] == "guide" && r.Method == http.MethodGet {
		result, err := s.screenGuide(pid, principal)
		if err != nil {
			writeScreenError(w, err)
			return
		}
		writeJSONResponse(w, http.StatusOK, result)
		return
	}
	if len(parts) == 3 && parts[2] == "guide" && r.Method == http.MethodPost {
		if principal.Kind != "callsign" || principal.ProjectID != pid {
			writeScreenError(w, store.Forbidden("쓰기는 이 프로젝트의 콜사인 토큰으로만 한다 (화면 공용 토큰은 읽기 · 등록만)"))
			return
		}
		body, err := readScreenJSON(r)
		if err != nil {
			writeScreenError(w, err)
			return
		}
		baseValue, ok := body["base_version"].(json.Number)
		base, parseErr := strconv.Atoi(baseValue.String())
		if !ok || parseErr != nil {
			writeScreenError(w, store.InvalidField("base_version", "정수"))
			return
		}
		text := ""
		if value, present := body["body"]; present {
			var valid bool
			text, valid = value.(string)
			if !valid {
				writeScreenError(w, store.InvalidField("body", "문자열"))
				return
			}
		}
		note := ""
		if value, present := body["note"]; present {
			var valid bool
			note, valid = value.(string)
			if !valid {
				writeScreenError(w, store.InvalidField("note", "문자열"))
				return
			}
		}
		result, err := s.cfg.Store.GuidePropose(store.Ctx{Now: now, Via: "ui", Principal: principal}, base, text, note)
		if err != nil {
			writeScreenError(w, err)
			return
		}
		writeJSONResponse(w, http.StatusOK, result)
		return
	}
	if len(parts) == 5 && parts[2] == "guide" && parts[3] == "proposals" && r.Method == http.MethodPost {
		if principal.Kind != "callsign" || principal.ProjectID != pid {
			writeScreenError(w, store.Forbidden("쓰기는 이 프로젝트의 콜사인 토큰으로만 한다 (화면 공용 토큰은 읽기 · 등록만)"))
			return
		}
		body, err := readScreenJSON(r)
		if err != nil {
			writeScreenError(w, err)
			return
		}
		approve, ok := body["approve"].(bool)
		if !ok {
			writeScreenError(w, store.InvalidField("approve", "true · false"))
			return
		}
		result, err := s.cfg.Store.GuideDecide(store.Ctx{Now: now, Via: "ui", Principal: principal}, parts[4], approve)
		if err != nil {
			writeScreenError(w, err)
			return
		}
		writeJSONResponse(w, http.StatusOK, result)
		return
	}
	if len(parts) == 3 && parts[2] == "roadmap" && r.Method == http.MethodGet {
		result, err := (&tools.JudgeBridge{Store: s.cfg.Store}).RoadmapState(ctx)
		if err != nil {
			writeScreenError(w, err)
			return
		}
		if result["roadmap_state"] == nil && result["reason"] == nil {
			result["reason"] = "로드맵이 없다 (index.md 없음)"
		}
		writeJSONResponse(w, http.StatusOK, result)
		return
	}
	if len(parts) == 3 && parts[2] == "orchestration" && r.Method == http.MethodGet {
		result, err := s.screenOrchestration(pid, principal, now, r)
		if err != nil {
			writeScreenError(w, err)
			return
		}
		writeJSONResponse(w, http.StatusOK, result)
		return
	}
	if len(parts) == 4 && parts[2] == "orchestration" && parts[3] == "halt" && r.Method == http.MethodPost {
		body, err := readScreenJSON(r)
		if err != nil {
			writeScreenError(w, err)
			return
		}
		on, ok := body["on"].(bool)
		if !ok {
			writeScreenError(w, store.InvalidField("on", "true · false"))
			return
		}
		result, err := s.cfg.Store.OrchHalt(store.Ctx{Now: now, Via: "ui", Principal: principal}, on)
		if err != nil {
			writeScreenError(w, err)
			return
		}
		writeJSONResponse(w, http.StatusOK, result)
		return
	}
	if len(parts) == 4 && parts[2] == "orchestration" && parts[3] == "lease" && r.Method == http.MethodPost {
		body, err := readScreenJSON(r)
		if err != nil {
			writeScreenError(w, err)
			return
		}
		action, _ := body["action"].(string)
		session, _ := body["session"].(string)
		ctxWrite := store.Ctx{Now: now, Via: "ui", Principal: principal}
		var result map[string]any
		switch action {
		case "declare":
			result, err = s.cfg.Store.OrchDeclare(ctxWrite, session)
		case "transfer":
			result, err = s.cfg.Store.OrchTransfer(ctxWrite, session)
		case "release":
			result, err = s.cfg.Store.OrchRelease(ctxWrite, "")
		default:
			err = store.InvalidField("action", "declare · transfer · release 중 하나")
		}
		if err != nil {
			writeScreenError(w, err)
			return
		}
		writeJSONResponse(w, http.StatusOK, result)
		return
	}
	if len(parts) == 5 && parts[2] == "orchestration" && parts[3] == "approvals" && r.Method == http.MethodPost {
		body, err := readScreenJSON(r)
		if err != nil {
			writeScreenError(w, err)
			return
		}
		decision, _ := body["decision"].(string)
		note, _ := body["note"].(string)
		if _, present := body["note"]; present {
			if _, ok := body["note"].(string); !ok {
				writeScreenError(w, store.InvalidField("note", "문자열"))
				return
			}
		}
		result, err := s.cfg.Store.ApprovalDecide(store.Ctx{Now: now, Via: "ui", Principal: principal}, parts[4], decision, note)
		if err != nil {
			writeScreenError(w, err)
			return
		}
		writeJSONResponse(w, http.StatusOK, result)
		return
	}
	if len(parts) == 5 && parts[2] == "orchestration" && parts[3] == "relays" && parts[4] == "invite" && r.Method == http.MethodPost {
		if _, err := readScreenJSON(r); err != nil {
			writeScreenError(w, err)
			return
		}
		ctxWrite := store.Ctx{Now: now, Via: "ui", Principal: principal, PublicURL: s.cfg.PublicURL}
		result, err := s.cfg.Store.RelayInvite(ctxWrite)
		if err != nil {
			writeScreenError(w, err)
			return
		}
		writeJSONResponse(w, http.StatusOK, result)
		return
	}
	if len(parts) == 6 && parts[2] == "orchestration" && parts[3] == "relays" && parts[5] == "revoke" && r.Method == http.MethodPost {
		if _, err := readScreenJSON(r); err != nil {
			writeScreenError(w, err)
			return
		}
		result, err := s.cfg.Store.RelayRevoke(store.Ctx{Now: now, Via: "ui", Principal: principal}, parts[4])
		if err != nil {
			writeScreenError(w, err)
			return
		}
		writeJSONResponse(w, http.StatusOK, result)
		return
	}
	if len(parts) == 3 && parts[2] == "wiki" && r.Method == http.MethodGet {
		result, err := s.screenWiki(pid, r, ctx)
		if err != nil {
			writeScreenError(w, err)
			return
		}
		writeJSONResponse(w, http.StatusOK, result)
		return
	}
	if len(parts) == 4 && parts[2] == "knowledge" && parts[3] == "ref" && r.Method == http.MethodGet {
		ref := r.URL.Query().Get("ref")
		result, err := s.cfg.Store.KnowledgeGet(ctx, ref)
		if err != nil {
			writeScreenError(w, err)
			return
		}
		writeJSONResponse(w, http.StatusOK, result)
		return
	}
	if len(parts) == 3 && parts[2] == "dcr" && r.Method == http.MethodGet {
		result, err := s.cfg.Store.DCRList(ctx, r.URL.Query().Get("status"))
		if err != nil {
			writeScreenError(w, err)
			return
		}
		writeJSONResponse(w, http.StatusOK, result)
		return
	}
	if len(parts) == 4 && parts[2] == "dcr" && r.Method == http.MethodGet {
		result, err := s.cfg.Store.DCRGet(ctx, parts[3])
		if err != nil {
			writeScreenError(w, err)
			return
		}
		writeJSONResponse(w, http.StatusOK, result)
		return
	}
	if len(parts) == 4 && parts[2] == "wiki" && parts[3] == "page" && r.Method == http.MethodGet {
		result, err := s.screenWikiPage(pid, r.URL.Query().Get("path"))
		if err != nil {
			writeScreenError(w, err)
			return
		}
		writeJSONResponse(w, http.StatusOK, result)
		return
	}
	writeJSONResponse(w, http.StatusNotFound, map[string]any{"error_code": "not_found", "message": "없는 화면 API", "detail": map[string]any{}})
}

func (s *Server) screenPlanResponse(pid, taskID string, body map[string]any, principal *store.Principal, now time.Time) (map[string]any, error) {
	ctx := store.Ctx{Now: now, Via: "ui", Principal: principal, ClientVersion: "hub-ui"}
	taskResult, err := s.cfg.Store.TaskGet(store.Ctx{Now: now, Via: "ui", Principal: &store.Principal{Kind: "viewer", ProjectID: pid}}, taskID)
	if err != nil {
		return nil, err
	}
	task := taskResult["task"].(map[string]any)
	fields, _ := task["fields"].(map[string]any)
	lines, _ := tools.TaskLines(stringArg(task, "plan_md"), fields)
	plan := judge.ParsePlan(lines)
	if body["plan_digest"] != judge.PlanDigest(plan) {
		return nil, &store.HubError{Status: 409, Code: "version_conflict", Message: "계획이 바뀌었다 — 다시 열어라", Detail: map[string]any{"current_digest": judge.PlanDigest(plan)}}
	}
	values, valuesOK := body["values"].(map[string]any)
	opened, openedOK := body["opened"].(map[string]any)
	comments, commentsOK := body["comments"].(map[string]any)
	for key, ok := range map[string]bool{"values": valuesOK, "opened": openedOK, "comments": commentsOK} {
		if _, present := body[key]; present && !ok {
			return nil, store.InvalidField(key, "객체여야 한다")
		}
	}
	if values == nil {
		values = map[string]any{}
	}
	if opened == nil {
		opened = map[string]any{}
	}
	if comments == nil {
		comments = map[string]any{}
	}
	status, err := (&tools.JudgeBridge{Store: s.cfg.Store}).PlanStatus(store.Ctx{Now: now, Via: "ui", Principal: &store.Principal{Kind: "viewer", ProjectID: pid}}, taskID)
	if err != nil {
		return nil, err
	}
	openSet := map[string]bool{}
	for _, id := range status["open_decisions"].([]string) {
		openSet[id] = true
	}
	var out strings.Builder
	out.WriteString("---\nformat: workflow-kit-plan-response/1\ntask: " + taskID + "\nplan_digest: " + judge.PlanDigest(plan) + "\nresponder: " + principal.Callsign + "\nrole: approver\nreceived_at: " + now.UTC().Format("2006-01-02T15:04:05-07:00") + "\nclient: hub-ui\n---\n\n## Decisions\n\n")
	for _, d := range plan.Decisions {
		value := d.Default
		flag := "no"
		if openSet[d.ID] {
			v, ok := values[d.ID].(string)
			valid := false
			for _, opt := range d.Options {
				if len(opt) > 0 && opt[0] == v {
					valid = true
				}
			}
			if !ok || !valid {
				return nil, store.InvalidField("values."+d.ID, "선택지 가운데 하나")
			}
			value = v
			if opened[d.ID] == true {
				flag = "yes"
			}
		}
		out.WriteString("- " + d.ID + " [" + d.ClaimID + "] value: " + value + " | default: " + d.Default + " | opened: " + flag + "\n")
	}
	allowed := map[string]bool{"-": true}
	for _, c := range plan.Claims {
		allowed[c.ID] = true
	}
	for _, d := range plan.Decisions {
		allowed[d.ID] = true
	}
	keys := make([]string, 0, len(comments))
	for k := range comments {
		keys = append(keys, k)
	}
	sort.Strings(keys)
	validComments := []string{}
	for _, key := range keys {
		txt, ok := comments[key].(string)
		if !ok {
			return nil, store.InvalidField("comments."+key, "문자열")
		}
		txt = strings.ReplaceAll(strings.ReplaceAll(txt, "\r\n", "\n"), "\r", "\n")
		if strings.TrimSpace(txt) == "" {
			continue
		}
		if !allowed[key] {
			return nil, store.InvalidField("comments."+key, "계획에 없는 대상")
		}
		for _, r := range txt {
			if (r < 0x20 && r != '\n' && r != '\t') || r == 0x7f {
				return nil, store.InvalidField("comments."+key, "제어 문자")
			}
		}
		validComments = append(validComments, key+"\x00"+txt)
	}
	if len(validComments) > 20 {
		return nil, store.InvalidField("comments", "최대 20개")
	}
	if len(validComments) > 0 {
		out.WriteString("\n## Comments\n\n")
		for _, item := range validComments {
			p := strings.SplitN(item, "\x00", 2)
			out.WriteString("- [" + p[0] + "]\n")
			for _, line := range strings.Split(p[1], "\n") {
				out.WriteString("  > " + line + "\n")
			}
		}
	}
	return (&tools.JudgeBridge{Store: s.cfg.Store}).PlanRespond(ctx, taskID, out.String())
}

func (s *Server) screenCallsign(pid, callsign string, ctx store.Ctx) (map[string]any, error) {
	board, err := s.screenCallsignBoard(pid)
	if err != nil {
		return nil, err
	}
	for _, item := range board["callsigns"].([]map[string]any) {
		if item["id"] == callsign {
			handoff := any(nil)
			version := 0
			var sections string
			var updated string
			var revoked sql.NullString
			if e := s.cfg.Store.DB().QueryRow("SELECT revoked_at FROM callsign WHERE project_id=? AND id=?", pid, callsign).Scan(&revoked); e == sql.ErrNoRows {
				return nil, store.NotFound("콜사인이 없다: " + callsign)
			} else if e != nil {
				return nil, e
			}
			err := s.cfg.Store.DB().QueryRow("SELECT sections_json,version,updated_at FROM handoff WHERE project_id=? AND callsign=?", pid, callsign).Scan(&sections, &version, &updated)
			if err != nil && err != sql.ErrNoRows {
				return nil, err
			}
			if err == nil {
				var parsed map[string]any
				if e := json.Unmarshal([]byte(sections), &parsed); e != nil {
					return nil, e
				}
				handoff = map[string]any{"callsign": callsign, "handoff": parsed, "version": version, "updated_at": updated, "archived": revoked.Valid}
			} else {
				handoff = map[string]any{"callsign": callsign, "handoff": nil, "version": 0, "archived": revoked.Valid}
			}
			return map[string]any{"guide_current": board["guide_current"], "callsign": item, "handoff": handoff}, nil
		}
	}
	return nil, store.NotFound("콜사인이 없다: " + callsign)
}

func (s *Server) screenGuide(pid string, principal *store.Principal) (map[string]any, error) {
	db := s.cfg.Store.DB()
	var version int
	var body string
	if err := db.QueryRow("SELECT version,body_md FROM guide WHERE project_id=? ORDER BY version DESC LIMIT 1", pid).Scan(&version, &body); err != nil && err != sql.ErrNoRows {
		return nil, err
	}
	history := []map[string]any{}
	rows, err := db.Query("SELECT version,updated_by,updated_at,length(body_md) FROM guide WHERE project_id=? ORDER BY version DESC", pid)
	if err != nil {
		return nil, err
	}
	for rows.Next() {
		var v, size int
		var by, at string
		if err := rows.Scan(&v, &by, &at, &size); err != nil {
			rows.Close()
			return nil, err
		}
		history = append(history, map[string]any{"version": v, "updated_by": by, "updated_at": at, "size": size})
	}
	if err := rows.Err(); err != nil {
		rows.Close()
		return nil, err
	}
	rows.Close()
	proposals := []map[string]any{}
	pr, err := db.Query("SELECT id,base_version,body_md,note,proposed_by,proposed_at,status,decided_by,decided_at,applied_version FROM guide_proposal WHERE project_id=? ORDER BY proposed_at DESC,id DESC LIMIT 100", pid)
	if err != nil {
		return nil, err
	}
	for pr.Next() {
		var id, proposalBody, note, by, at, status string
		var base int
		var decided, decidedAt, applied sql.NullString
		if err := pr.Scan(&id, &base, &proposalBody, &note, &by, &at, &status, &decided, &decidedAt, &applied); err != nil {
			pr.Close()
			return nil, err
		}
		item := map[string]any{"id": id, "base_version": base, "body_md": proposalBody, "note": note, "proposed_by": by, "proposed_at": at, "status": status, "decided_by": nil, "decided_at": nil, "applied_version": nil, "diff": "", "stale": status == "open" && base != version}
		if decided.Valid {
			item["decided_by"] = decided.String
		}
		if decidedAt.Valid {
			item["decided_at"] = decidedAt.String
		}
		if applied.Valid {
			item["applied_version"] = applied.String
		}
		proposals = append(proposals, item)
	}
	if err := pr.Err(); err != nil {
		pr.Close()
		return nil, err
	}
	pr.Close()
	guideVersion := tools.KitVersion + "+p" + strconv.Itoa(version)
	canAnswer := principal.Kind == "callsign" && principal.CallsignKind == "human" && principal.HumanApproved && principal.ProjectID == pid
	return map[string]any{"version": version, "guide_version": guideVersion, "body": body, "history": history, "proposals": proposals, "can_decide": canAnswer && principal.Role == "owner", "can_propose": principal.Kind == "callsign" && principal.ProjectID == pid}, nil
}

var wikiPathPattern = regexp.MustCompile(`^(?:[A-Za-z0-9_][A-Za-z0-9_.-]*/)*[A-Za-z0-9_][A-Za-z0-9_.-]*\.md$`)

type wikiIndexPage struct{ path, body string }

func (s *Server) screenWiki(pid string, r *http.Request, ctx store.Ctx) (map[string]any, error) {
	q := strings.TrimSpace(r.URL.Query().Get("q"))
	prefix := r.URL.Query().Get("prefix")
	if q != "" {
		return s.cfg.Store.KnowledgeSearch(ctx, q, 50)
	}
	rows, err := s.cfg.Store.DB().Query("SELECT path,body_md,version,updated_by,updated_at FROM wiki_page WHERE project_id=? ORDER BY path", pid)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	type wikiRow struct {
		path, body, by, at string
		version            int
	}
	items := []wikiRow{}
	for rows.Next() {
		var x wikiRow
		if err := rows.Scan(&x.path, &x.body, &x.version, &x.by, &x.at); err != nil {
			return nil, err
		}
		items = append(items, x)
	}
	if err := rows.Err(); err != nil {
		return nil, err
	}
	if q != "" {
		words := strings.Fields(strings.ToLower(q))
		hits := []map[string]any{}
		for _, x := range items {
			title := wikiTitle(x.path, x.body)
			hay := strings.ToLower(x.path + "\n" + title + "\n" + x.body)
			match := true
			score := 0
			for _, word := range words {
				if !strings.Contains(hay, word) {
					match = false
					break
				}
				if strings.Contains(strings.ToLower(x.path), word) || strings.Contains(strings.ToLower(title), word) {
					score += 3
				}
				score += strings.Count(hay, word)
			}
			if match {
				at := strings.Index(strings.ToLower(x.body), words[0])
				snippet := ""
				if at >= 0 {
					start := 0
					if at > 60 {
						start = at - 60
					}
					end := len(x.body)
					if at+120 < end {
						end = at + 120
					}
					snippet = strings.ReplaceAll(x.body[start:end], "\n", " ")
				}
				hits = append(hits, map[string]any{"path": x.path, "title": title, "score": score, "snippet": snippet})
			}
		}
		sort.Slice(hits, func(i, j int) bool {
			if hits[i]["score"].(int) != hits[j]["score"].(int) {
				return hits[i]["score"].(int) > hits[j]["score"].(int)
			}
			return hits[i]["path"].(string) < hits[j]["path"].(string)
		})
		total := len(hits)
		limit := queryInt(r, "limit", 50)
		if limit < 1 {
			limit = 1
		}
		if limit > 100 {
			limit = 100
		}
		if len(hits) > limit {
			hits = hits[:limit]
		}
		return map[string]any{"query": q, "hits": hits, "total": total}, nil
	}
	pages := []map[string]any{}
	for _, x := range items {
		if strings.HasPrefix(x.path, prefix) {
			pages = append(pages, map[string]any{"path": x.path, "title": wikiTitle(x.path, x.body), "version": x.version, "updated_by": x.by, "updated_at": x.at})
		}
	}
	return map[string]any{"pages": pages, "generated": []string{"index.md", "log.md"}}, nil
}
func wikiTitle(p, b string) string {
	if strings.HasPrefix(b, "---\n") {
		if i := strings.Index(b[4:], "\n---"); i >= 0 {
			fm := b[4 : 4+i]
			for _, line := range strings.Split(fm, "\n") {
				if strings.HasPrefix(line, "title:") {
					return strings.Trim(strings.Trim(strings.TrimSpace(strings.TrimPrefix(line, "title:")), "\\\""), "'")
				}
			}
		}
	}
	for _, line := range strings.Split(b, "\n") {
		if strings.HasPrefix(line, "# ") {
			return strings.TrimSpace(strings.TrimPrefix(line, "# "))
		}
	}
	return strings.TrimSuffix(path.Base(p), ".md")
}
func (s *Server) screenWikiPage(pid, p string) (map[string]any, error) {
	if p == "" {
		return nil, store.InvalidField("path", "필수")
	}
	if p == "index.md" {
		rows, err := s.cfg.Store.DB().Query("SELECT path,body_md FROM wiki_page WHERE project_id=? ORDER BY path", pid)
		if err != nil {
			return nil, err
		}
		defer rows.Close()
		pages := []wikiIndexPage{}
		for rows.Next() {
			var x wikiIndexPage
			if err := rows.Scan(&x.path, &x.body); err != nil {
				return nil, err
			}
			pages = append(pages, x)
		}
		if err := rows.Err(); err != nil {
			return nil, err
		}
		return map[string]any{"path": p, "generated": true, "body": renderWikiIndex(pages)}, nil
	}
	if p == "log.md" {
		rows, err := s.cfg.Store.DB().Query("SELECT id,callsign,at,log_line,pages_json FROM wiki_ingest WHERE project_id=? ORDER BY seq", pid)
		if err != nil {
			return nil, err
		}
		defer rows.Close()
		var b strings.Builder
		b.WriteString("# Wiki Ingest Log\n\n- 허브가 ingest 기록에서 생성한다 — 손으로 고치지 않는다.\n")
		for rows.Next() {
			var id, cs, at, line, pagesJSON string
			if err := rows.Scan(&id, &cs, &at, &line, &pagesJSON); err != nil {
				return nil, err
			}
			var pages []map[string]any
			if err := json.Unmarshal([]byte(pagesJSON), &pages); err != nil {
				return nil, err
			}
			b.WriteString("\n" + line + "\n\n- " + id + " · " + cs + " · " + at + "\n- ")
			labels := []string{}
			for _, page := range pages {
				v := "삭제"
				if page["deleted"] != true {
					v = "v" + fmt.Sprint(page["version"])
				}
				labels = append(labels, fmt.Sprint(page["path"])+" ("+v+")")
			}
			b.WriteString(strings.Join(labels, ", ") + "\n")
		}
		if err := rows.Err(); err != nil {
			return nil, err
		}
		return map[string]any{"path": p, "generated": true, "body": strings.TrimRight(b.String(), "\n") + "\n"}, nil
	}
	if !wikiPathPattern.MatchString(p) || strings.Contains(p, "..") {
		return nil, store.InvalidField("path", "위키 안 상대 경로 · .md (예: concepts/foo.md)")
	}
	var body, by, at, last, repo, sha string
	var version int
	err := s.cfg.Store.DB().QueryRow("SELECT body_md,version,updated_by,updated_at,last_ingest,source_repo_key,source_sha FROM wiki_page WHERE project_id=? AND path=?", pid, p).Scan(&body, &version, &by, &at, &last, &repo, &sha)
	if err == sql.ErrNoRows {
		return nil, store.NotFound("위키 페이지가 없다: " + p)
	}
	if err != nil {
		return nil, err
	}
	return map[string]any{"path": p, "body": body, "version": version, "updated_by": by, "updated_at": at, "last_ingest": last, "source": map[string]any{"repo_key": nullableString(repo), "sha": nullableString(sha)}}, nil
}

func wikiSlug(s string) string {
	var b strings.Builder
	dash := false
	for _, r := range strings.ToLower(s) {
		if r >= 'a' && r <= 'z' || r >= '0' && r <= '9' {
			b.WriteRune(r)
			dash = false
		} else if !dash && b.Len() > 0 {
			b.WriteByte('-')
			dash = true
		}
	}
	v := strings.Trim(b.String(), "-")
	if v == "" {
		return "page"
	}
	return v
}
func renderWikiIndex(pages []wikiIndexPage) string {
	sections := map[string][]string{}
	counts := map[string]int{}
	for _, p := range pages {
		stem := strings.TrimSuffix(p.path, ".md")
		name := path.Base(stem)
		counts[wikiSlug(name)]++
	}
	for _, p := range pages {
		stem := strings.TrimSuffix(p.path, ".md")
		name := path.Base(stem)
		anchor := wikiSlug(name)
		if counts[anchor] > 1 {
			anchor = wikiSlug(stem)
		}
		top := ""
		if i := strings.IndexByte(stem, '/'); i >= 0 {
			top = stem[:i]
		}
		sections[top] = append(sections[top], "### [["+stem+"]] {#"+anchor+"}")
	}
	titles := map[string]string{"": "Meta", "concepts": "Concepts", "decisions": "Decisions", "entities": "Entities", "patterns": "Patterns", "queries": "Queries", "sources": "Sources", "topics": "Topics"}
	order := []string{"concepts", "decisions", "entities", "patterns", "queries", "sources", "topics"}
	rank := func(k string) int {
		if k == "" {
			return 0
		}
		for i, v := range order {
			if v == k {
				return i + 1
			}
		}
		return len(order) + 1
	}
	keys := make([]string, 0, len(sections))
	for k := range sections {
		keys = append(keys, k)
	}
	sort.Slice(keys, func(i, j int) bool {
		if rank(keys[i]) != rank(keys[j]) {
			return rank(keys[i]) < rank(keys[j])
		}
		return keys[i] < keys[j]
	})
	var b strings.Builder
	b.WriteString("# Master Knowledge Index\n\n")
	for _, k := range keys {
		title := titles[k]
		if title == "" {
			title = k
		}
		b.WriteString("## " + title + "\n\n")
		for _, item := range sections[k] {
			b.WriteString(item + "\n")
		}
		b.WriteByte('\n')
	}
	return strings.TrimRight(b.String(), "\n") + "\n"
}

func readScreenJSON(r *http.Request) (map[string]any, error) {
	contentType := strings.ToLower(strings.TrimSpace(strings.Split(r.Header.Get("Content-Type"), ";")[0]))
	if contentType != "application/json" {
		return nil, &store.HubError{Status: http.StatusUnsupportedMediaType, Code: "unsupported_media_type", Message: "본문은 application/json 이어야 한다"}
	}
	raw, err := io.ReadAll(io.LimitReader(r.Body, MaxBody+1))
	if err != nil {
		return nil, err
	}
	if len(raw) > MaxBody {
		return nil, &store.HubError{Status: http.StatusRequestEntityTooLarge, Code: "payload_too_large", Message: fmt.Sprintf("본문 상한 %d 바이트", MaxBody)}
	}
	if len(strings.TrimSpace(string(raw))) == 0 {
		return map[string]any{}, nil
	}
	var body map[string]any
	dec := json.NewDecoder(strings.NewReader(string(raw)))
	dec.UseNumber()
	if err := dec.Decode(&body); err != nil || body == nil {
		return nil, &store.HubError{Status: http.StatusBadRequest, Code: "invalid_json", Message: "본문은 JSON 객체다"}
	}
	var extra any
	if err := dec.Decode(&extra); err != io.EOF {
		return nil, &store.HubError{Status: http.StatusBadRequest, Code: "invalid_json", Message: "본문은 JSON 객체다"}
	}
	return body, nil
}

func (s *Server) screenTask(projectID, taskID string, ctx store.Ctx) (map[string]any, error) {
	ctx.Principal = &store.Principal{Kind: "viewer", ProjectID: projectID}
	taskResult, err := s.cfg.Store.TaskGet(ctx, taskID)
	if err != nil {
		return nil, err
	}
	task, ok := taskResult["task"].(map[string]any)
	if !ok {
		return nil, store.NotFound("task 가 없다: " + taskID)
	}
	planMD, _ := task["plan_md"].(string)
	fields, _ := task["fields"].(map[string]any)
	lines, _ := tools.TaskLines(planMD, fields)
	plan := judge.ParsePlan(lines)
	status, err := (&tools.JudgeBridge{Store: s.cfg.Store}).PlanStatus(ctx, taskID)
	if err != nil {
		return nil, err
	}
	states, _ := status["states"].(map[string]string)
	if states == nil {
		states = map[string]string{}
	}
	claims := make([]map[string]any, 0, len(plan.Claims))
	for _, c := range plan.Claims {
		claims = append(claims, map[string]any{"id": c.ID, "text": c.Text})
	}
	decisions := make([]map[string]any, 0, len(plan.Decisions))
	for _, d := range plan.Decisions {
		options := make([][]string, 0, len(d.Options))
		for _, o := range d.Options {
			options = append(options, []string{o[0], o[1]})
		}
		state := states[d.ID]
		if state == "" {
			state = d.State
		}
		decisions = append(decisions, map[string]any{"id": d.ID, "claim_id": d.ClaimID, "question": d.Question, "default": d.Default, "options": options, "state": state, "problems": d.Problems})
	}
	issues := judge.LintPlan(plan, nil, nil)
	lint := make([]map[string]any, 0, len(issues))
	for _, issue := range issues {
		lint = append(lint, map[string]any{"rule": issue.Rule, "severity": issue.Severity, "message": issue.Message, "ref": issue.Ref})
	}
	events, err := s.cfg.Store.Events(ctx, "task", taskID, 0, 1000)
	if err != nil {
		return nil, err
	}
	return map[string]any{"task": task, "plan": map[string]any{"digest": status["plan_digest"], "claims": claims, "decisions": decisions, "open_decisions": status["open_decisions"], "responses": status["responses"], "has_errors": judge.HasErrorRules(plan), "lint": lint}, "events": events["events"]}, nil
}

func (s *Server) screenProjectSummary(pid string, project map[string]any, ctx store.Ctx, principal *store.Principal) (map[string]any, error) {
	sessionList, err := s.cfg.Store.SessionList(ctx, "", "")
	if err != nil {
		return nil, err
	}
	var pendingApprovals, unacknowledged, openAssignments int
	for _, q := range []struct {
		sql string
		to  *int
	}{
		{"SELECT COUNT(*) FROM session_request WHERE project_id=? AND state='pending_approval'", &pendingApprovals},
		{"SELECT COUNT(*) FROM inbox_message WHERE project_id=? AND state='unacknowledged'", &unacknowledged},
		{"SELECT COUNT(*) FROM assignment WHERE project_id=? AND state IN ('offered','accepted')", &openAssignments},
	} {
		if err := s.cfg.Store.DB().QueryRow(q.sql, pid).Scan(q.to); err != nil {
			return nil, err
		}
	}
	planRows, err := s.cfg.Store.DB().Query("SELECT id FROM task WHERE project_id=? AND status!='done' AND plan_md!=''", pid)
	if err != nil {
		return nil, err
	}
	planTaskIDs := []string{}
	for planRows.Next() {
		var id string
		if err := planRows.Scan(&id); err != nil {
			planRows.Close()
			return nil, err
		}
		planTaskIDs = append(planTaskIDs, id)
	}
	if err := planRows.Err(); err != nil {
		planRows.Close()
		return nil, err
	}
	if err := planRows.Close(); err != nil {
		return nil, err
	}
	judgeBridge := tools.JudgeBridge{Store: s.cfg.Store}
	openDecisionTasks := 0
	for _, taskID := range planTaskIDs {
		status, err := judgeBridge.PlanStatus(ctx, taskID)
		if err != nil {
			return nil, err
		}
		if len(status["open_decisions"].([]string)) > 0 {
			openDecisionTasks++
		}
	}
	return map[string]any{
		"project": project, "principal": principalSummary(principal),
		"summary": map[string]any{
			"open_decision_tasks": openDecisionTasks, "pending_approvals": pendingApprovals, "unacknowledged": unacknowledged,
			"open_assignments": openAssignments, "session_counts": sessionList["counts"],
			"unknown_sessions": sessionList["unknown"], "sessions_total": len(sessionList["sessions"].([]map[string]any)),
			"orchestrator": sessionList["orchestrator"],
		},
	}, nil
}

func (s *Server) screenCallsignBoard(projectID string) (map[string]any, error) {
	var version int
	if err := s.cfg.Store.DB().QueryRow("SELECT COALESCE(MAX(version),0) FROM guide WHERE project_id=?", projectID).Scan(&version); err != nil {
		return nil, err
	}
	currentGuide := fmt.Sprintf("%s+p%d", tools.KitVersion, version)
	rows, err := s.cfg.Store.DB().Query("SELECT id,kind,human_approved,role,label,host,created_at,last_seen_at,revoked_at,guide_version_seen,client_version_seen,setup_complete FROM callsign WHERE project_id=? ORDER BY revoked_at IS NOT NULL,COALESCE(last_seen_at,created_at) DESC,id", projectID)
	if err != nil {
		return nil, err
	}
	type row struct {
		id, kind, role, label, host, created     string
		approved, setup                          int
		lastSeen, revoked, guideSeen, clientSeen sql.NullString
	}
	items := []row{}
	for rows.Next() {
		var item row
		if err := rows.Scan(&item.id, &item.kind, &item.approved, &item.role, &item.label, &item.host, &item.created, &item.lastSeen, &item.revoked, &item.guideSeen, &item.clientSeen, &item.setup); err != nil {
			rows.Close()
			return nil, err
		}
		items = append(items, item)
	}
	if err := rows.Err(); err != nil {
		rows.Close()
		return nil, err
	}
	if err := rows.Close(); err != nil {
		return nil, err
	}
	callsigns := make([]map[string]any, 0, len(items))
	for _, item := range items {
		var seen, last, revoked, client any
		if item.guideSeen.Valid {
			seen = item.guideSeen.String
		}
		if item.lastSeen.Valid {
			last = item.lastSeen.String
		}
		if item.revoked.Valid {
			revoked = item.revoked.String
		}
		if item.clientSeen.Valid {
			client = item.clientSeen.String
		}
		state := "never"
		if item.guideSeen.Valid {
			state = "stale"
			if item.guideSeen.String == currentGuide {
				state = "current"
			}
		}
		tasks, err := s.cfg.Store.DB().Query("SELECT id,title,status,progress_note,progress_at,updated_at FROM task WHERE project_id=? AND assignee=? AND status!='done' ORDER BY updated_at DESC,id", projectID, item.id)
		if err != nil {
			return nil, err
		}
		openTasks := []map[string]any{}
		for tasks.Next() {
			var id, title, status, note, updated string
			var progress sql.NullString
			if err := tasks.Scan(&id, &title, &status, &note, &progress, &updated); err != nil {
				tasks.Close()
				return nil, err
			}
			var progressAt any
			if progress.Valid {
				progressAt = progress.String
			}
			openTasks = append(openTasks, map[string]any{"id": id, "title": title, "status": status, "progress_note": note, "progress_at": progressAt, "updated_at": updated})
		}
		if err := tasks.Err(); err != nil {
			tasks.Close()
			return nil, err
		}
		tasks.Close()
		var handoff sql.NullString
		err = s.cfg.Store.DB().QueryRow("SELECT updated_at FROM handoff WHERE project_id=? AND callsign=?", projectID, item.id).Scan(&handoff)
		if err != nil && !errors.Is(err, sql.ErrNoRows) {
			return nil, err
		}
		var handoffAt any
		if handoff.Valid {
			handoffAt = handoff.String
		}
		callsigns = append(callsigns, map[string]any{"id": item.id, "kind": item.kind, "human_approved": item.approved != 0, "role": item.role, "label": item.label, "host": item.host, "created_at": item.created, "last_seen_at": last, "revoked_at": revoked, "guide_version_seen": seen, "client_version_seen": client, "setup_complete": item.setup != 0, "guide_state": state, "archived": item.revoked.Valid, "handoff_updated_at": handoffAt, "open_tasks": openTasks})
	}
	return map[string]any{"guide_current": currentGuide, "callsigns": callsigns}, nil
}

func queryInt(r *http.Request, key string, fallback int) int {
	value := r.URL.Query().Get(key)
	if value == "" {
		return fallback
	}
	n, err := strconv.Atoi(value)
	if err != nil {
		return fallback
	}
	return n
}

func stringArg(m map[string]any, key string) string {
	v, _ := m[key].(string)
	return v
}

func (s *Server) screenPrincipal(r *http.Request, now time.Time) (*store.Principal, error) {
	token := bearerToken(r.Header)
	if token != "" {
		principal, err := s.cfg.Store.Authenticate(token, &now, r.Header.Get("X-Hub-Client"))
		if err != nil {
			return nil, err
		}
		if principal == nil {
			return nil, store.Unauthorized("토큰이 틀렸거나 거둔 토큰이다 — 이 브라우저에서 지운 뒤 다시 등록한다")
		}
		return principal, nil
	}
	if s.cfg.WebTokenName != "" {
		principal, err := s.cfg.Store.WebPrincipal(s.cfg.WebTokenName)
		if err != nil {
			return nil, err
		}
		if principal != nil {
			return principal, nil
		}
	}
	return nil, store.Unauthorized("토큰이 없다 — 화면 공용 토큰이 꺼져 있다. 콜사인 토큰을 넣는다")
}

func principalSummary(p *store.Principal) map[string]any {
	isOwner := p.Kind == "callsign" && p.CallsignKind == "human" && p.HumanApproved && p.Role == "owner"
	return map[string]any{
		"kind": p.Kind, "project_id": p.ProjectID, "callsign": nullableString(p.Callsign),
		"callsign_kind": nullableString(p.CallsignKind), "human_approved": p.HumanApproved,
		"role": nullableString(p.Role), "name": nullableString(p.Name),
		"can_answer": p.Kind == "callsign" && p.CallsignKind == "human" && p.HumanApproved,
		"can_manage": isOwner,
	}
}

func nullableString(s string) any {
	if s == "" {
		return nil
	}
	return s
}

func (s *Server) screenProjects(projectID string) ([]map[string]any, error) {
	query := "SELECT id, display_name, owner_callsign, created_at FROM project"
	args := []any{}
	if projectID != "" {
		query += " WHERE id = ?"
		args = append(args, projectID)
	}
	query += " ORDER BY created_at, id"
	rows, err := s.cfg.Store.DB().Query(query, args...)
	if err != nil {
		return nil, err
	}
	type projectRow struct{ id, name, owner, created string }
	projectRows := []projectRow{}
	for rows.Next() {
		var id, name, owner, created string
		if err := rows.Scan(&id, &name, &owner, &created); err != nil {
			rows.Close()
			return nil, err
		}
		projectRows = append(projectRows, projectRow{id: id, name: name, owner: owner, created: created})
	}
	if err := rows.Err(); err != nil {
		rows.Close()
		return nil, err
	}
	if err := rows.Close(); err != nil {
		return nil, err
	}
	projects := make([]map[string]any, 0, len(projectRows))
	for _, project := range projectRows {
		counts := map[string]int{}
		countRows, err := s.cfg.Store.DB().Query("SELECT status, COUNT(*) FROM task WHERE project_id = ? GROUP BY status", project.id)
		if err != nil {
			return nil, err
		}
		for countRows.Next() {
			var status string
			var count int
			if err := countRows.Scan(&status, &count); err != nil {
				countRows.Close()
				return nil, err
			}
			counts[status] = count
		}
		if err := countRows.Err(); err != nil {
			countRows.Close()
			return nil, err
		}
		countRows.Close()
		projects = append(projects, map[string]any{"id": project.id, "display_name": project.name, "owner_callsign": project.owner, "created_at": project.created, "task_counts": counts})
	}
	return projects, nil
}

func writeScreenError(w http.ResponseWriter, err error) {
	if hubErr, ok := store.AsHubError(err); ok {
		writeJSONResponse(w, hubErr.Status, hubErr.Payload())
		return
	}
	status := http.StatusInternalServerError
	if errors.Is(err, sql.ErrNoRows) {
		status = http.StatusNotFound
	}
	writeJSONResponse(w, status, map[string]any{"error_code": "internal_error", "message": err.Error(), "detail": map[string]any{}})
}
