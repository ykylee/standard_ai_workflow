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
}
