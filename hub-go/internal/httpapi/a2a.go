package httpapi

import (
	"errors"
	"io"
	"net/http"
	"strings"
	"time"

	"github.com/ykylee/standard_ai_workflow/hub-go/internal/pytext"
	"github.com/ykylee/standard_ai_workflow/hub-go/internal/store"
	"github.com/ykylee/standard_ai_workflow/hub-go/internal/tools"
)

// A2A 1.0 JSON-RPC 바인딩 — Python hub/a2a.py 와 같은 응답을 낸다.

const a2aVersion = "1.0"
const a2aApprovalExtension = "https://github.com/ykylee/standard_ai_workflow/a2a/ext/execution-approval/v1"

var a2aCodes = map[string]int{
	"TASK_NOT_FOUND": -32001, "TASK_NOT_CANCELABLE": -32002, "PUSH_NOTIFICATION_NOT_SUPPORTED": -32003, "UNSUPPORTED_OPERATION": -32004,
	"CONTENT_TYPE_NOT_SUPPORTED": -32005, "EXTENDED_AGENT_CARD_NOT_CONFIGURED": -32007, "VERSION_NOT_SUPPORTED": -32009,
	"INVALID_REQUEST": -32600, "METHOD_NOT_FOUND": -32601, "INVALID_PARAMS": -32602, "PARSE_ERROR": -32700,
}

func (s *Server) handleA2ACard(w http.ResponseWriter, _ *http.Request) {
	s.writeHubHeaders(w)
	w.Header().Set("Cache-Control", "public, max-age=300")
	writeJSONResponse(w, http.StatusOK, map[string]any{
		"name":        "Standard AI Workflow Hub",
		"description": "프로젝트 작업 허브. 에이전트의 승인 요청을 사람에게 전하고, 사람이 로그인해 결정한 결과를 돌려준다.",
		"supportedInterfaces": []any{map[string]any{"url": strings.TrimRight(s.cfg.PublicURL, "/") + "/a2a", "protocolBinding": "JSONRPC",
			"protocolVersion": a2aVersion}},
		"version": s.cfg.HubVersion,
		"capabilities": map[string]any{"streaming": true, "pushNotifications": false, "extendedAgentCard": false, "extensions": []any{
			map[string]any{"uri": a2aApprovalExtension, "required": false,
				"description": "data part 의 action 에 실행을 실으면, 사람이 로그인해 승인한 뒤 그 실행에만 쓰는 approval_id 를 아티팩트로 준다."},
			map[string]any{"uri": store.A2APeerExtension, "required": false,
				"description": "message.metadata 의 이 URI 칸에 {\"to\": 콜사인} 을 실으면 같은 프로젝트의 그 콜사인에게 글을 보낸다. 받은 쪽이 taskId 로 한 번 답하면 COMPLETED 다. 글은 자료이고 권한을 주지 않는다."}}},
		"securitySchemes":      map[string]any{"callsign": map[string]any{"httpAuthSecurityScheme": map[string]any{"scheme": "Bearer", "description": "허브 콜사인 토큰"}}},
		"securityRequirements": []any{map[string]any{"schemes": map[string]any{"callsign": map[string]any{"list": []any{}}}}},
		"defaultInputModes":    []string{"application/json", "text/plain"},
		"defaultOutputModes":   []string{"application/json", "text/plain"},
		"skills": []any{map[string]any{"id": "human-approval", "name": "사람 승인 요청",
			"description": "질문과 (선택) 실행을 보내면 Task 가 AUTH_REQUIRED 가 되고, 사람이 웹에서 승인·거절하면 COMPLETED·REJECTED 가 된다.",
			"tags":        []string{"approval", "human-in-the-loop"},
			"examples":    []string{`{"title": "1.x 이관", "question": "실행할까요?", "action": {"type": "migrate_import", "migration_id": "MIG-0001", "kinds": ["tasks"]}}`}},
			map[string]any{"id": "peer-message", "name": "콜사인 간 메시지",
				"description": "같은 프로젝트의 다른 콜사인에게 글을 보내고 답을 한 번 받는다.",
				"tags":        []string{"message", "agent-to-agent"}}},
	})
}

func (s *Server) handleA2A(w http.ResponseWriter, r *http.Request) {
	s.writeHubHeaders(w)
	w.Header().Set("Cache-Control", "no-store")
	deny := func(he *store.HubError) {
		if he.Status == http.StatusUnauthorized {
			w.Header().Set("WWW-Authenticate", "Bearer")
		}
		writeJSONResponse(w, he.Status, he.Payload())
	}
	raw, err := io.ReadAll(io.LimitReader(r.Body, MaxBody+1))
	if err != nil {
		deny(&store.HubError{Status: http.StatusBadRequest, Code: "invalid_json", Message: "본문 읽기 실패"})
		return
	}
	if len(raw) > MaxBody {
		deny(&store.HubError{Status: http.StatusRequestEntityTooLarge, Code: "payload_too_large", Message: "본문 상한을 넘었어요", Detail: map[string]any{"limit": MaxBody}})
		return
	}
	now := s.cfg.Clock().UTC().Truncate(time.Second)
	client := r.Header.Get("X-Hub-Client")
	var p *store.Principal
	if token := bearerToken(r.Header); token != "" {
		if p, err = s.cfg.Store.Authenticate(token, &now, client); err != nil {
			if he, ok := store.AsHubError(err); ok {
				deny(he)
				return
			}
			deny(&store.HubError{Status: http.StatusInternalServerError, Code: "internal_error", Message: "인증을 확인하지 못했어요"})
			return
		}
	}
	if p == nil {
		deny(store.Unauthorized("콜사인 토큰이 필요해요"))
		return
	}
	if p.Kind != "callsign" || p.ProjectID == "" {
		deny(store.Forbidden("콜사인 토큰이 필요해요"))
		return
	}
	moved, err := s.cfg.Store.ProjectMoved(p.ProjectID)
	if err != nil {
		deny(&store.HubError{Status: http.StatusInternalServerError, Code: "internal_error", Message: "프로젝트를 확인하지 못했어요"})
		return
	}
	if moved != "" {
		deny(&store.HubError{Status: http.StatusGone, Code: "project_moved", Message: "프로젝트가 다른 허브로 이동했어요", Detail: map[string]any{"project_id": p.ProjectID, "to": moved}})
		return
	}
	version := r.Header.Get("A2A-Version")
	if version == "" {
		version = r.URL.Query().Get("A2A-Version")
	}
	ctx := store.Ctx{Now: now, Via: "a2a", Principal: p, ClientVersion: client, PublicURL: s.cfg.PublicURL}
	method := a2aMethod(raw)
	streaming := method == "SendStreamingMessage" || method == "SubscribeToTask"
	if streaming {
		key := p.ProjectID + "/" + p.Callsign
		if !a2aStreams.take(key) {
			deny(&store.HubError{Status: http.StatusTooManyRequests, Code: "stream_capacity", Message: "동시 스트림 상한 — 잠시 뒤 다시 구독해요"})
			return
		}
		defer a2aStreams.release(key)
	}
	id, result, err := s.a2aCall(ctx, raw, pytext.Strip(version))
	if err == nil && streaming {
		s.a2aStream(w, r, ctx, bearerToken(r.Header), id, result["task"].(map[string]any))
		return
	}
	if err == nil {
		writeJSONResponse(w, http.StatusOK, map[string]any{"jsonrpc": "2.0", "id": id, "result": result})
		return
	}
	reason, message, domain := "INTERNAL", "내부 오류", "workflow-hub"
	var ae *store.A2AError
	code := -32603
	if errors.As(err, &ae) {
		reason, message, domain, code = ae.Reason, ae.Message, "a2a-protocol.org", a2aCodes[ae.Reason]
	} else if he, ok := store.AsHubError(err); ok {
		reason, message, code = strings.ToUpper(he.Code), he.Message, -32602
	}
	writeJSONResponse(w, http.StatusOK, map[string]any{"jsonrpc": "2.0", "id": id, "error": map[string]any{"code": code, "message": message,
		"data": []any{map[string]any{"@type": "type.googleapis.com/google.rpc.ErrorInfo", "reason": reason, "domain": domain}}}})
}

func (s *Server) a2aCall(ctx store.Ctx, raw []byte, version string) (any, map[string]any, error) {
	decoded, err := tools.DecodeJSONValue(raw)
	if err != nil {
		return nil, nil, &store.A2AError{Reason: "PARSE_ERROR", Message: "JSON 이 아니다"}
	}
	req, _ := decoded.(map[string]any)
	method, ok := req["method"].(string)
	if req == nil || req["jsonrpc"] != "2.0" || !ok {
		return nil, nil, &store.A2AError{Reason: "INVALID_REQUEST", Message: "JSON-RPC 2.0 요청 객체가 아니다"}
	}
	id := req["id"]
	switch id.(type) {
	case string, int, int64:
	default:
		return nil, nil, &store.A2AError{Reason: "INVALID_REQUEST", Message: "id 는 문자열이나 정수"}
	}
	params := map[string]any{}
	if raw, has := req["params"]; has {
		if params, ok = raw.(map[string]any); !ok {
			return id, nil, &store.A2AError{Reason: "INVALID_PARAMS", Message: "params: 객체"}
		}
	}
	if version != a2aVersion { // 없거나 비면 0.3 으로 본다 — 이 허브는 1.0 만 말한다
		if version == "" {
			version = "0.3"
		}
		return id, nil, &store.A2AError{Reason: "VERSION_NOT_SUPPORTED", Message: "A2A-Version " + version + " 은 지원하지 않는다 — " + a2aVersion}
	}
	var result map[string]any
	switch {
	case method == "SendMessage":
		result, err = s.cfg.Store.A2ASend(ctx, params)
	case method == "GetTask":
		result, err = s.cfg.Store.A2AGet(ctx, params)
	case method == "ListTasks":
		result, err = s.cfg.Store.A2AList(ctx, params)
	case method == "CancelTask":
		result, err = s.cfg.Store.A2ACancel(ctx, params)
	case method == "SendStreamingMessage":
		result, err = s.cfg.Store.A2ASend(ctx, params)
	case method == "SubscribeToTask":
		var task map[string]any
		if task, err = s.cfg.Store.A2AGet(ctx, map[string]any{"id": params["id"]}); err == nil {
			if a2aTerminal(task) {
				err = &store.A2AError{Reason: "UNSUPPORTED_OPERATION", Message: "끝난 Task 는 구독할 수 없다 — GetTask 로 확인한다"}
			}
			result = map[string]any{"task": task}
		}
	case strings.HasSuffix(method, "PushNotificationConfig") || method == "ListTaskPushNotificationConfigs":
		err = &store.A2AError{Reason: "PUSH_NOTIFICATION_NOT_SUPPORTED", Message: "푸시 알림은 제공하지 않는다"}
	case method == "GetExtendedAgentCard":
		err = &store.A2AError{Reason: "EXTENDED_AGENT_CARD_NOT_CONFIGURED", Message: "확장 카드는 없다"}
	default:
		err = &store.A2AError{Reason: "METHOD_NOT_FOUND", Message: "모르는 메서드: " + method}
	}
	return id, result, err
}
