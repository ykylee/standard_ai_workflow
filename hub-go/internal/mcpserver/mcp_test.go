package mcpserver

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"path/filepath"
	"testing"
	"time"

	"github.com/ykylee/standard_ai_workflow/hub-go/internal/db"
	"github.com/ykylee/standard_ai_workflow/hub-go/internal/store"
)

func postMCP(t *testing.T, h http.Handler, tok string, reqBody any) *httptest.ResponseRecorder {
	t.Helper()
	b, _ := json.Marshal(reqBody)
	req := httptest.NewRequest(http.MethodPost, "/mcp", bytes.NewReader(b))
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Accept", "application/json, text/event-stream")
	if tok != "" {
		req.Header.Set("Authorization", "Bearer "+tok)
	}
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, req)
	return rec
}

func postModernMCP(t *testing.T, h http.Handler, method string, params map[string]any) *httptest.ResponseRecorder {
	t.Helper()
	params["_meta"] = map[string]any{
		protocolVersionMetaKey:               modernProtocolVersion,
		clientCapsMetaKey:                    map[string]any{},
		"io.modelcontextprotocol/clientInfo": map[string]any{"name": "test-client", "version": "1"},
	}
	body := map[string]any{"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
	b, _ := json.Marshal(body)
	req := httptest.NewRequest(http.MethodPost, "/mcp", bytes.NewReader(b))
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Accept", "application/json, text/event-stream")
	req.Header.Set("MCP-Protocol-Version", modernProtocolVersion)
	req.Header.Set("Mcp-Method", method)
	if name, ok := params["name"].(string); ok {
		req.Header.Set("Mcp-Name", name)
	}
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, req)
	return rec
}

func TestModernProtocolDiscoveryAndTools(t *testing.T) {
	dbPath := filepath.Join(t.TempDir(), "hub.db")
	now := time.Date(2026, 11, 22, 12, 0, 0, 0, time.UTC)
	if _, err := db.OpenDB(dbPath, now); err != nil {
		t.Fatalf("OpenDB: %v", err)
	}
	st, err := store.New(dbPath)
	if err != nil {
		t.Fatalf("store.New: %v", err)
	}
	t.Cleanup(func() { _ = st.Close() })
	srv := &Server{Store: st, PublicURL: "http://127.0.0.1:8770", Clock: func() time.Time { return now }}

	init := postModernMCP(t, srv, "initialize", map[string]any{})
	if init.Code != http.StatusNotFound || !bytes.Contains(init.Body.Bytes(), []byte(`"code":-32601`)) {
		t.Fatalf("modern protocol must not fall back to initialize: status=%d body=%s", init.Code, init.Body.String())
	}

	discover := postModernMCP(t, srv, "server/discover", map[string]any{})
	if discover.Code != http.StatusOK {
		t.Fatalf("discover status=%d body=%s", discover.Code, discover.Body.String())
	}
	var discoverRPC map[string]any
	if err := json.Unmarshal(discover.Body.Bytes(), &discoverRPC); err != nil {
		t.Fatal(err)
	}
	discoverResult := discoverRPC["result"].(map[string]any)
	if discoverResult["resultType"] != "complete" || discoverResult["supportedVersions"].([]any)[0] != modernProtocolVersion {
		t.Fatalf("unexpected discover result: %#v", discoverResult)
	}
	if discoverResult["_meta"].(map[string]any)[serverInfoMetaKey].(map[string]any)["name"] != "workflow-hub" {
		t.Fatalf("serverInfo stamp missing: %#v", discoverResult)
	}

	list := postModernMCP(t, srv, "tools/list", map[string]any{})
	if list.Code != http.StatusOK {
		t.Fatalf("tools/list status=%d body=%s", list.Code, list.Body.String())
	}
	var listRPC map[string]any
	if err := json.Unmarshal(list.Body.Bytes(), &listRPC); err != nil {
		t.Fatal(err)
	}
	listResult := listRPC["result"].(map[string]any)
	if listResult["resultType"] != "complete" || len(listResult["tools"].([]any)) != 6 {
		t.Fatalf("unexpected modern tools/list result: %#v", listResult)
	}

	call := postModernMCP(t, srv, "tools/call", map[string]any{
		"name":      "hub_project_lookup",
		"arguments": map[string]any{"remote_url": "https://example.invalid/team/repo"},
	})
	if call.Code != http.StatusOK {
		t.Fatalf("tools/call status=%d body=%s", call.Code, call.Body.String())
	}
	var callRPC map[string]any
	if err := json.Unmarshal(call.Body.Bytes(), &callRPC); err != nil {
		t.Fatal(err)
	}
	callResult := callRPC["result"].(map[string]any)
	if callResult["resultType"] != "complete" || callResult["structuredContent"].(map[string]any)["project_id"] != nil {
		t.Fatalf("unexpected modern tools/call result: %#v", callResult)
	}
}

func TestModernProtocolRejectsHeaderAndVersionMismatch(t *testing.T) {
	dbPath := filepath.Join(t.TempDir(), "hub.db")
	now := time.Date(2026, 11, 22, 12, 0, 0, 0, time.UTC)
	if _, err := db.OpenDB(dbPath, now); err != nil {
		t.Fatalf("OpenDB: %v", err)
	}
	st, err := store.New(dbPath)
	if err != nil {
		t.Fatalf("store.New: %v", err)
	}
	t.Cleanup(func() { _ = st.Close() })
	srv := &Server{Store: st, PublicURL: "http://127.0.0.1:8770", Clock: func() time.Time { return now }}

	// The canonical client headers and body method must agree.
	params := map[string]any{"_meta": map[string]any{protocolVersionMetaKey: modernProtocolVersion, clientCapsMetaKey: map[string]any{}}}
	body, _ := json.Marshal(map[string]any{"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": params})
	req := httptest.NewRequest(http.MethodPost, "/mcp", bytes.NewReader(body))
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("MCP-Protocol-Version", modernProtocolVersion)
	req.Header.Set("Mcp-Method", "tools/call")
	rec := httptest.NewRecorder()
	srv.ServeHTTP(rec, req)
	if rec.Code != http.StatusBadRequest || !bytes.Contains(rec.Body.Bytes(), []byte(`"code":-32020`)) {
		t.Fatalf("expected method-header mismatch 400/-32020, got status=%d body=%s", rec.Code, rec.Body.String())
	}

	// An unsupported per-request version is a modern protocol error with the supported list.
	params = map[string]any{"_meta": map[string]any{protocolVersionMetaKey: "2025-11-25", clientCapsMetaKey: map[string]any{}}}
	body, _ = json.Marshal(map[string]any{"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": params})
	req = httptest.NewRequest(http.MethodPost, "/mcp", bytes.NewReader(body))
	req.Header.Set("MCP-Protocol-Version", "2025-11-25")
	req.Header.Set("Mcp-Method", "tools/list")
	rec = httptest.NewRecorder()
	srv.ServeHTTP(rec, req)
	if rec.Code != http.StatusBadRequest || !bytes.Contains(rec.Body.Bytes(), []byte(`"code":-32022`)) || !bytes.Contains(rec.Body.Bytes(), []byte(modernProtocolVersion)) {
		t.Fatalf("expected unsupported version 400/-32022, got status=%d body=%s", rec.Code, rec.Body.String())
	}

	// Browser-origin requests are accepted only when they match the endpoint origin.
	req = httptest.NewRequest(http.MethodPost, "http://127.0.0.1/mcp", bytes.NewReader(body))
	req.Header.Set("Origin", "https://evil.invalid")
	rec = httptest.NewRecorder()
	srv.ServeHTTP(rec, req)
	if rec.Code != http.StatusForbidden {
		t.Fatalf("expected foreign Origin to be rejected, got status=%d", rec.Code)
	}
}

func TestMCPAuthAndToolParity(t *testing.T) {
	dbPath := filepath.Join(t.TempDir(), "hub.db")
	now := time.Date(2026, 11, 22, 12, 0, 0, 0, time.UTC)
	if _, err := db.OpenDB(dbPath, now); err != nil {
		t.Fatalf("OpenDB: %v", err)
	}
	st, err := store.New(dbPath)
	if err != nil {
		t.Fatalf("store.New: %v", err)
	}
	t.Cleanup(func() { _ = st.Close() })

	srv := &Server{
		Store:     st,
		PublicURL: "http://127.0.0.1:8770",
		Clock:     func() time.Time { return now },
	}

	// initialize
	initRec := postMCP(t, srv, "", map[string]any{
		"jsonrpc": "2.0",
		"id":      1,
		"method":  "initialize",
		"params":  map[string]any{"protocolVersion": "2025-11-25"},
	})
	if initRec.Code != http.StatusOK {
		t.Fatalf("initialize status=%d body=%s", initRec.Code, initRec.Body.String())
	}

	// notification returns 202
	notiRec := postMCP(t, srv, "", map[string]any{
		"jsonrpc": "2.0",
		"method":  "notifications/initialized",
	})
	if notiRec.Code != http.StatusAccepted {
		t.Fatalf("notification status=%d", notiRec.Code)
	}

	// Unauthenticated tools/list returns only 6 bootstrap tools
	listAnon := postMCP(t, srv, "", map[string]any{
		"jsonrpc": "2.0",
		"id":      2,
		"method":  "tools/list",
	})
	var listResp map[string]any
	_ = json.Unmarshal(listAnon.Body.Bytes(), &listResp)
	toolsAnon := listResp["result"].(map[string]any)["tools"].([]any)
	if len(toolsAnon) != 6 {
		t.Fatalf("expected 6 bootstrap tools unauthenticated, got %d", len(toolsAnon))
	}

	// Register project via MCP tools/call
	regRec := postMCP(t, srv, "", map[string]any{
		"jsonrpc": "2.0",
		"id":      3,
		"method":  "tools/call",
		"params": map[string]any{
			"name": "hub_project_register",
			"arguments": map[string]any{
				"remote_url":   "git@github.com:Acme/MCPDemo.git",
				"display_name": "MCP Demo",
				"callsign":     "claude-a",
				"kind":         "human",
			},
		},
	})
	var regRPC map[string]any
	_ = json.Unmarshal(regRec.Body.Bytes(), &regRPC)
	tok := regRPC["result"].(map[string]any)["structuredContent"].(map[string]any)["token"].(string)

	// Unauthenticated token tool call fails with isError=true unauthorized
	unauthCall := postMCP(t, srv, "", map[string]any{
		"jsonrpc": "2.0",
		"id":      4,
		"method":  "tools/call",
		"params":  map[string]any{"name": "hub_task_list", "arguments": map[string]any{}},
	})
	var unauthRPC map[string]any
	_ = json.Unmarshal(unauthCall.Body.Bytes(), &unauthRPC)
	unauthRes := unauthRPC["result"].(map[string]any)
	if unauthRes["isError"] != true {
		t.Fatalf("expected isError=true, got %#v", unauthRes)
	}
	if unauthRes["structuredContent"].(map[string]any)["error_code"] != "unauthorized" {
		t.Fatalf("expected unauthorized, got %#v", unauthRes)
	}

	// Authenticated tools/list returns all 74 tools
	listAuth := postMCP(t, srv, tok, map[string]any{
		"jsonrpc": "2.0",
		"id":      5,
		"method":  "tools/list",
	})
	var authResp map[string]any
	_ = json.Unmarshal(listAuth.Body.Bytes(), &authResp)
	toolsAuth := authResp["result"].(map[string]any)["tools"].([]any)
	if len(toolsAuth) != 74 {
		t.Fatalf("expected 74 authed tools, got %d", len(toolsAuth))
	}

	startRec := postMCP(t, srv, tok, map[string]any{
		"jsonrpc": "2.0", "id": 6, "method": "tools/call",
		"params": map[string]any{"name": "hub_session_start", "arguments": map[string]any{
			"session": map[string]any{"harness": "codex", "kind": "worker", "delivery": []string{"wait"}},
		}},
	})
	var startRPC map[string]any
	if err := json.Unmarshal(startRec.Body.Bytes(), &startRPC); err != nil {
		t.Fatal(err)
	}
	startContent := startRPC["result"].(map[string]any)["structuredContent"].(map[string]any)
	sessionID := startContent["session"].(map[string]any)["id"].(string)
	waitRec := postMCP(t, srv, tok, map[string]any{
		"jsonrpc": "2.0", "id": 7, "method": "tools/call",
		"params": map[string]any{"name": "hub_wait", "arguments": map[string]any{"session": sessionID, "timeout_s": 1}},
	})
	var waitRPC map[string]any
	if err := json.Unmarshal(waitRec.Body.Bytes(), &waitRPC); err != nil {
		t.Fatal(err)
	}
	waitResult := waitRPC["result"].(map[string]any)["structuredContent"].(map[string]any)
	if waitResult["call_again"] != true || waitResult["waited_s"].(float64) < 1 {
		t.Fatalf("MCP wait did not long-poll to timeout: %#v", waitResult)
	}
}
