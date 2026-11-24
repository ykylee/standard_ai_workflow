package mcpserver

import (
	"bytes"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"strings"
	"time"

	"github.com/ykylee/standard_ai_workflow/hub-go/internal/store"
	"github.com/ykylee/standard_ai_workflow/hub-go/internal/tools"
	"github.com/ykylee/standard_ai_workflow/hub-go/internal/waiter"
)

const (
	maxMCPBody             = 64 * 1024 * 1024
	defaultProtocolVersion = "2025-11-25"
	modernProtocolVersion  = "2026-07-28"
	protocolVersionMetaKey = "io.modelcontextprotocol/protocolVersion"
	clientCapsMetaKey      = "io.modelcontextprotocol/clientCapabilities"
	serverInfoMetaKey      = "io.modelcontextprotocol/serverInfo"
)

var supportedProtocolVersions = map[string]bool{
	"2024-11-05": true,
	"2025-03-26": true,
	"2025-06-18": true,
	"2025-11-25": true,
}

// Server serves stateless JSON-response Streamable HTTP MCP requests on /mcp.
type Server struct {
	Store      *store.Store
	HubVersion string
	PublicURL  string
	Clock      func() time.Time
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

func modernRequest(msg map[string]any, r *http.Request) bool {
	if method, _ := msg["method"].(string); method == "server/discover" {
		return true
	}
	if r != nil && r.Header.Get("MCP-Protocol-Version") != "" {
		return true
	}
	params, _ := msg["params"].(map[string]any)
	meta, _ := params["_meta"].(map[string]any)
	_, ok := meta[protocolVersionMetaKey]
	return ok
}

func protocolError(id any, code int, message string, data map[string]any) map[string]any {
	resp := jsonRPCErr(id, code, message)
	if data != nil {
		resp["error"].(map[string]any)["data"] = data
	}
	return resp
}

func modernErrorStatus(resp map[string]any) int {
	errObj, _ := resp["error"].(map[string]any)
	var code int
	switch raw := errObj["code"].(type) {
	case int:
		code = raw
	case float64:
		code = int(raw)
	}
	switch code {
	case -32020, -32021, -32022, -32602:
		return http.StatusBadRequest
	case -32601:
		return http.StatusNotFound
	default:
		return http.StatusOK
	}
}

func decodedHeaderValue(value string) (string, bool) {
	const prefix, suffix = "=?base64?", "?="
	if !strings.HasPrefix(value, prefix) || !strings.HasSuffix(value, suffix) {
		return value, true
	}
	raw, err := base64.StdEncoding.DecodeString(strings.TrimSuffix(strings.TrimPrefix(value, prefix), suffix))
	if err != nil {
		return "", false
	}
	return string(raw), true
}

func validateModernRequest(r *http.Request, msg map[string]any) map[string]any {
	id := msg["id"]
	params, ok := msg["params"].(map[string]any)
	if !ok {
		return protocolError(id, -32602, "Invalid params: modern requests require params._meta", nil)
	}
	meta, ok := params["_meta"].(map[string]any)
	if !ok {
		return protocolError(id, -32602, "Invalid params: modern requests require params._meta", nil)
	}
	version, ok := meta[protocolVersionMetaKey].(string)
	if !ok || version == "" {
		return protocolError(id, -32602, "Invalid params: protocolVersion metadata is required", nil)
	}
	if _, ok := meta[clientCapsMetaKey].(map[string]any); !ok {
		return protocolError(id, -32602, "Invalid params: clientCapabilities metadata is required", nil)
	}
	if version != modernProtocolVersion {
		return protocolError(id, -32022, "Unsupported protocol version", map[string]any{
			"supported": []string{modernProtocolVersion}, "requested": version,
		})
	}
	if r == nil {
		return nil
	}
	method, _ := msg["method"].(string)
	if r.Header.Get("MCP-Protocol-Version") != version || r.Header.Get("Mcp-Method") != method {
		return protocolError(id, -32020, "Header mismatch: MCP-Protocol-Version and Mcp-Method must match the request body", nil)
	}
	if method == "tools/call" {
		name, _ := params["name"].(string)
		headerName, valid := decodedHeaderValue(r.Header.Get("Mcp-Name"))
		if !valid || name == "" || headerName != name {
			return protocolError(id, -32020, "Header mismatch: Mcp-Name must match params.name", nil)
		}
	} else if r.Header.Get("Mcp-Name") != "" {
		return protocolError(id, -32020, "Header mismatch: Mcp-Name is only valid when the method has a name", nil)
	}
	return nil
}

func (s *Server) modernResult(result map[string]any) map[string]any {
	result["resultType"] = "complete"
	meta, _ := result["_meta"].(map[string]any)
	if meta == nil {
		meta = map[string]any{}
	}
	meta[serverInfoMetaKey] = map[string]any{"name": "workflow-hub", "version": s.HubVersion, "_meta": map[string]any{"kitVersion": tools.KitVersion}}
	result["_meta"] = meta
	return result
}

func (s *Server) discoveryResult() map[string]any {
	return s.modernResult(map[string]any{
		"supportedVersions": []string{modernProtocolVersion},
		"capabilities":      map[string]any{"tools": map[string]any{}},
		"ttlMs":             0,
		"cacheScope":        "private",
	})
}

func validOrigin(r *http.Request) bool {
	origin := r.Header.Get("Origin")
	if origin == "" {
		return true
	}
	parsed, err := url.Parse(origin)
	if err != nil || parsed.Scheme == "" || parsed.Host == "" || parsed.Path != "" || parsed.RawQuery != "" || parsed.Fragment != "" {
		return false
	}
	scheme := "http"
	if r.TLS != nil {
		scheme = "https"
	}
	return strings.EqualFold(parsed.Scheme, scheme) && strings.EqualFold(parsed.Host, r.Host)
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
	modern := modernRequest(msg, r)
	if modern {
		if isNotification {
			return protocolError(nil, -32600, "Modern requests require a non-null id", nil), false
		}
		if invalid := validateModernRequest(r, msg); invalid != nil {
			return invalid, false
		}
		if method == "server/discover" {
			return jsonRPCResult(id, s.discoveryResult()), false
		}
		if method == "initialize" {
			return jsonRPCErr(id, -32601, "Method not found: initialize is not part of the modern protocol"), false
		}
		if method == "notifications/cancelled" {
			return nil, true
		}
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
				"version": s.HubVersion,
				"_meta":   map[string]any{"kitVersion": tools.KitVersion},
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
		kind := ""
		if p != nil {
			kind = p.Kind
		}
		specs := tools.VisibleToolsFor(kind)
		list := make([]map[string]any, len(specs))
		for i, sp := range specs {
			list[i] = map[string]any{
				"name":        sp.Name,
				"description": sp.Description,
				"inputSchema": sp.Schema(),
			}
		}
		result := map[string]any{"tools": list}
		if modern {
			result["ttlMs"] = 0
			result["cacheScope"] = "private"
			return jsonRPCResult(id, s.modernResult(result)), false
		}
		return jsonRPCResult(id, result), false

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
			result := callToolErrorResult(store.Unauthorized("토큰이 틀렸거나 거둔 토큰이다"))
			if modern {
				result = s.modernResult(result)
			}
			return jsonRPCResult(id, result), false
		}

		ctx := store.Ctx{
			Now:       now,
			Via:       "mcp",
			Principal: p,
			PublicURL: s.PublicURL,
		}
		var res map[string]any
		var err error
		if toolName == "hub_wait" {
			res, err = waiter.Call(r.Context(), s.Store, args, ctx, s.Clock)
		} else {
			res, err = tools.Call(s.Store, toolName, args, ctx)
		}
		if err != nil {
			if he, ok := store.AsHubError(err); ok {
				result := callToolErrorResult(he)
				if modern {
					result = s.modernResult(result)
				}
				return jsonRPCResult(id, result), false
			}
			result := callToolErrorResult(&store.HubError{
				Status:  500,
				Code:    "internal_error",
				Message: fmt.Sprintf("도구 실행 오류: %v", err),
			})
			if modern {
				result = s.modernResult(result)
			}
			return jsonRPCResult(id, result), false
		}
		result := map[string]any{
			"content": []map[string]any{
				{"type": "text", "text": store.MustJSON(res)},
			},
			"structuredContent": res,
		}
		if modern {
			result = s.modernResult(result)
		}
		return jsonRPCResult(id, result), false

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
	if !validOrigin(r) {
		writeJSON(w, http.StatusForbidden, jsonRPCErr(nil, -32000, "Forbidden origin"))
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
		if modernRequest(payload, r) && strings.HasPrefix(fmt.Sprint(payload["method"]), "notifications/") {
			writeJSON(w, http.StatusBadRequest, jsonRPCErr(payload["id"], -32600, "Notifications are not supported over Streamable HTTP"))
			return
		}
		resp, notifyOnly := s.handleOne(r, payload)
		if notifyOnly {
			w.WriteHeader(http.StatusAccepted)
			return
		}
		status := http.StatusOK
		if modernRequest(payload, r) {
			status = modernErrorStatus(resp)
		}
		writeJSON(w, status, resp)
	case []any:
		modernBatch := r.Header.Get("MCP-Protocol-Version") == modernProtocolVersion
		for _, item := range payload {
			if obj, ok := item.(map[string]any); ok && modernRequest(obj, r) {
				modernBatch = true
				break
			}
		}
		if modernBatch {
			writeJSON(w, http.StatusBadRequest, jsonRPCErr(nil, -32600, "JSON-RPC batches are not supported"))
			return
		}
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
