package mcpserver

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"strings"
	"time"

	"github.com/ykylee/standard_ai_workflow/hub-go/internal/store"
	"github.com/ykylee/standard_ai_workflow/hub-go/internal/tools"
)

const (
	maxMCPBody             = 64 * 1024 * 1024
	defaultProtocolVersion = "2025-11-25"
)

var supportedProtocolVersions = map[string]bool{
	"2024-11-05": true,
	"2025-03-26": true,
	"2025-06-18": true,
	"2025-11-25": true,
}

// Server serves stateless JSON-response Streamable HTTP MCP requests on /mcp.
type Server struct {
	Store     *store.Store
	PublicURL string
	Clock     func() time.Time
}

func (s *Server) now() time.Time {
	if s.Clock != nil {
		return s.Clock().UTC().Truncate(time.Second)
	}
	return time.Now().UTC().Truncate(time.Second)
}

func bearerToken(h http.Header) string {
	raw := h.Get("Authorization")
	if len(raw) >= 7 && strings.EqualFold(raw[:7], "bearer ") {
		return strings.TrimSpace(raw[7:])
	}
	return ""
}

func writeJSON(w http.ResponseWriter, status int, v any) {
	var buf bytes.Buffer
	enc := json.NewEncoder(&buf)
	enc.SetEscapeHTML(false)
	_ = enc.Encode(v)
	w.Header().Set("Content-Type", "application/json; charset=utf-8")
	w.WriteHeader(status)
	_, _ = w.Write(buf.Bytes())
}

func jsonRPCErr(id any, code int, msg string) map[string]any {
	return map[string]any{
		"jsonrpc": "2.0",
		"id":      id,
		"error": map[string]any{
			"code":    code,
			"message": msg,
		},
	}
}

func jsonRPCResult(id any, result any) map[string]any {
	return map[string]any{
		"jsonrpc": "2.0",
		"id":      id,
		"result":  result,
	}
}

func (s *Server) principalFromRequest(r *http.Request) (*store.Principal, bool, time.Time, error) {
	now := s.now()
	tok := bearerToken(r.Header)
	if tok == "" {
		return nil, false, now, nil
	}
	clientVer := r.Header.Get("X-Hub-Client")
	p, err := s.Store.Authenticate(tok, &now, clientVer)
	if err != nil {
		return nil, true, now, err
	}
	return p, true, now, nil
}

func callToolErrorResult(he *store.HubError) map[string]any {
	payload := he.Payload()
	return map[string]any{
		"content": []map[string]any{
			{"type": "text", "text": store.MustJSON(payload)},
		},
		"structuredContent": payload,
		"isError":           true,
	}
}

func (s *Server) handleOne(r *http.Request, msg map[string]any) (map[string]any, bool) {
	method, _ := msg["method"].(string)
	id, hasID := msg["id"]
	isNotification := !hasID || id == nil

	if strings.HasPrefix(method, "notifications/") && isNotification {
		return nil, true
	}

	params, _ := msg["params"].(map[string]any)
	if params == nil {
		params = map[string]any{}
	}

	switch method {
	case "initialize":
		proto := defaultProtocolVersion
		if clientProto, ok := params["protocolVersion"].(string); ok && supportedProtocolVersions[clientProto] {
			proto = clientProto
		}
		res := map[string]any{
			"protocolVersion": proto,
			"capabilities": map[string]any{
				"tools": map[string]any{"listChanged": false},
			},
			"serverInfo": map[string]any{
				"name":    "workflow-hub",
				"version": tools.KitVersion,
			},
		}
		return jsonRPCResult(id, res), false

	case "ping":
		return jsonRPCResult(id, map[string]any{}), false

	case "tools/list":
		p, _, _, err := s.principalFromRequest(r)
		if err != nil {
			return jsonRPCErr(id, -32603, err.Error()), false
		}
		authed := p != nil && p.Kind == "callsign"
		specs := tools.VisibleTools(authed)
		list := make([]map[string]any, len(specs))
		for i, sp := range specs {
			list[i] = map[string]any{
				"name":        sp.Name,
				"description": sp.Description,
				"inputSchema": sp.Schema(),
			}
		}
		return jsonRPCResult(id, map[string]any{"tools": list}), false

	case "tools/call":
		toolName, ok := params["name"].(string)
		if !ok || toolName == "" {
			return jsonRPCErr(id, -32602, "missing tool name"), false
		}
		var args any = map[string]any{}
		if rawArgs, exists := params["arguments"]; exists && rawArgs != nil {
			args = rawArgs
		}

		p, sent, now, authErr := s.principalFromRequest(r)
		if authErr != nil {
			return jsonRPCErr(id, -32603, authErr.Error()), false
		}
		spec := tools.Tools[toolName]
		if sent && p == nil && spec != nil && spec.Bundle != "bootstrap" {
			return jsonRPCResult(id, callToolErrorResult(store.Unauthorized("토큰이 틀렸거나 거둔 토큰이다"))), false
		}

		ctx := store.Ctx{
			Now:       now,
			Via:       "mcp",
			Principal: p,
			PublicURL: s.PublicURL,
		}
		res, err := tools.Call(s.Store, toolName, args, ctx)
		if err != nil {
			if he, ok := store.AsHubError(err); ok {
				return jsonRPCResult(id, callToolErrorResult(he)), false
			}
			return jsonRPCResult(id, callToolErrorResult(&store.HubError{
				Status:  500,
				Code:    "internal_error",
				Message: fmt.Sprintf("도구 실행 오류: %v", err),
			})), false
		}
		return jsonRPCResult(id, map[string]any{
			"content": []map[string]any{
				{"type": "text", "text": store.MustJSON(res)},
			},
			"structuredContent": res,
		}), false

	default:
		if isNotification {
			return nil, true
		}
		return jsonRPCErr(id, -32601, fmt.Sprintf("Method not found: %s", method)), false
	}
}

// ServeHTTP handles stateless streamable HTTP MCP requests.
func (s *Server) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	switch r.Method {
	case http.MethodPost:
	case http.MethodGet, http.MethodDelete:
		w.Header().Set("Allow", "POST")
		writeJSON(w, http.StatusMethodNotAllowed, jsonRPCErr(nil, -32000, "Method not allowed"))
		return
	default:
		w.Header().Set("Allow", "POST")
		w.WriteHeader(http.StatusMethodNotAllowed)
		return
	}

	raw, err := io.ReadAll(io.LimitReader(r.Body, maxMCPBody+1))
	if err != nil {
		writeJSON(w, http.StatusBadRequest, jsonRPCErr(nil, -32700, "Read error"))
		return
	}
	if len(raw) > maxMCPBody {
		writeJSON(w, http.StatusRequestEntityTooLarge, jsonRPCErr(nil, -32600, "Payload too large"))
		return
	}
	parsed, err := tools.DecodeJSONValue(bytes.TrimSpace(raw))
	if err != nil {
		writeJSON(w, http.StatusBadRequest, jsonRPCErr(nil, -32700, fmt.Sprintf("Parse error: %v", err)))
		return
	}

	switch payload := parsed.(type) {
	case map[string]any:
		resp, notifyOnly := s.handleOne(r, payload)
		if notifyOnly {
			w.WriteHeader(http.StatusAccepted)
			return
		}
		writeJSON(w, http.StatusOK, resp)
	case []any:
		if len(payload) == 0 {
			writeJSON(w, http.StatusBadRequest, jsonRPCErr(nil, -32600, "Empty batch"))
			return
		}
		responses := make([]map[string]any, 0, len(payload))
		for _, item := range payload {
			obj, ok := item.(map[string]any)
			if !ok {
				responses = append(responses, jsonRPCErr(nil, -32600, "Invalid Request"))
				continue
			}
			resp, notifyOnly := s.handleOne(r, obj)
			if !notifyOnly {
				responses = append(responses, resp)
			}
		}
		if len(responses) == 0 {
			w.WriteHeader(http.StatusAccepted)
			return
		}
		writeJSON(w, http.StatusOK, responses)
	default:
		writeJSON(w, http.StatusBadRequest, jsonRPCErr(nil, -32600, "Invalid Request"))
	}
}
