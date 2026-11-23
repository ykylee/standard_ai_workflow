package httpapi

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"path/filepath"
	"strings"
	"testing"
	"time"

	"github.com/ykylee/standard_ai_workflow/hub-go/internal/db"
	"github.com/ykylee/standard_ai_workflow/hub-go/internal/store"
)

func newTestServer(t *testing.T) (*Server, *store.Store) {
	t.Helper()
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
	srv := New(Config{
		Store:     st,
		PublicURL: "http://127.0.0.1:8770",
		Exposure:  "loopback",
		Clock:     func() time.Time { return now },
	})
	return srv, st
}

func doReq(t *testing.T, h http.Handler, method, target, tok string, body []byte, extra map[string]string) *httptest.ResponseRecorder {
	t.Helper()
	req := httptest.NewRequest(method, target, bytes.NewReader(body))
	if tok != "" {
		req.Header.Set("Authorization", "Bearer "+tok)
	}
	for k, v := range extra {
		req.Header.Set(k, v)
	}
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, req)
	return rec
}

func TestHTTPHealthzAndToolsAndLimits(t *testing.T) {
	srv, _ := newTestServer(t)

	hz := doReq(t, srv, http.MethodGet, "/healthz", "", nil, nil)
	if hz.Code != http.StatusOK {
		t.Fatalf("/healthz status=%d body=%s", hz.Code, hz.Body.String())
	}
	if hz.Header().Get("X-Hub-Contract") != "hub/1" || hz.Header().Get("X-Hub-Kit") != "2.1.0" {
		t.Fatalf("missing hub headers: %#v", hz.Header())
	}
	var hzJSON map[string]any
	_ = json.Unmarshal(hz.Body.Bytes(), &hzJSON)
	if hzJSON["ok"] != true || hzJSON["exposure"] != "loopback" {
		t.Fatalf("unexpected healthz JSON: %#v", hzJSON)
	}

	hc := doReq(t, srv, http.MethodGet, "/v1/bootstrap/hub_client.py", "", nil, nil)
	if hc.Code != http.StatusOK || !strings.Contains(hc.Header().Get("Content-Type"), "text/x-python") || len(hc.Body.Bytes()) == 0 {
		t.Fatalf("unexpected hub_client.py response code=%d ct=%s", hc.Code, hc.Header().Get("Content-Type"))
	}

	// Contract mismatch rejected
	badContract := doReq(t, srv, http.MethodPost, "/v1/tools/hub_project_lookup", "", []byte(`{"remote_url":"https://github.com/a/b"}`), map[string]string{"X-Hub-Contract": "hub/999"})
	if badContract.Code != http.StatusBadRequest {
		t.Fatalf("expected 400 on bad contract header, got %d", badContract.Code)
	}

	// Body limit 413
	huge := append([]byte(`{"remote_url":"`), bytes.Repeat([]byte("a"), MaxBody+10)...)
	huge = append(huge, []byte(`"}`)...)
	tooBig := doReq(t, srv, http.MethodPost, "/v1/tools/hub_project_lookup", "", huge, nil)
	if tooBig.Code != http.StatusRequestEntityTooLarge {
		t.Fatalf("expected 413, got %d", tooBig.Code)
	}

	// Invalid JSON 400
	badJSON := doReq(t, srv, http.MethodPost, "/v1/tools/hub_project_lookup", "", []byte(`{bad`), nil)
	if badJSON.Code != http.StatusBadRequest {
		t.Fatalf("expected 400 invalid_json, got %d", badJSON.Code)
	}

	// Register + task flow over HTTP
	reg := doReq(t, srv, http.MethodPost, "/v1/tools/hub_project_register", "", []byte(`{"remote_url":"git@github.com:Acme/HttpDemo.git","display_name":"HTTP Demo","callsign":"claude-a","kind":"human"}`), nil)
	if reg.Code != http.StatusOK {
		t.Fatalf("register failed code=%d body=%s", reg.Code, reg.Body.String())
	}
	var regJSON map[string]any
	_ = json.Unmarshal(reg.Body.Bytes(), &regJSON)
	tok := regJSON["token"].(string)

	// Unauthenticated token call fails 401
	unauth := doReq(t, srv, http.MethodPost, "/v1/tools/hub_task_list", "", []byte(`{}`), nil)
	if unauth.Code != http.StatusUnauthorized {
		t.Fatalf("expected 401, got %d", unauth.Code)
	}

	// Authenticated create & list
	tc := doReq(t, srv, http.MethodPost, "/v1/tools/hub_task_create", tok, []byte(`{"title":"hello http"}`), nil)
	if tc.Code != http.StatusOK {
		t.Fatalf("create failed code=%d body=%s", tc.Code, tc.Body.String())
	}
	tl := doReq(t, srv, http.MethodPost, "/v1/tools/hub_task_list", tok, nil, nil)
	if tl.Code != http.StatusOK {
		t.Fatalf("list failed code=%d body=%s", tl.Code, tl.Body.String())
	}
}

func TestHTTPHubWaitLongPollTimeout(t *testing.T) {
	srv, _ := newTestServer(t)
	reg := doReq(t, srv, http.MethodPost, "/v1/tools/hub_project_register", "", []byte(`{"remote_url":"https://github.com/acme/wait-demo","display_name":"Wait Demo","callsign":"worker","kind":"human"}`), nil)
	if reg.Code != http.StatusOK {
		t.Fatalf("register failed code=%d body=%s", reg.Code, reg.Body.String())
	}
	var registered map[string]any
	if err := json.Unmarshal(reg.Body.Bytes(), &registered); err != nil {
		t.Fatal(err)
	}
	token := registered["token"].(string)
	started := doReq(t, srv, http.MethodPost, "/v1/tools/hub_session_start", token, []byte(`{"session":{"harness":"codex","kind":"worker","delivery":["wait"]}}`), nil)
	if started.Code != http.StatusOK {
		t.Fatalf("session start failed code=%d body=%s", started.Code, started.Body.String())
	}
	var startedJSON map[string]any
	if err := json.Unmarshal(started.Body.Bytes(), &startedJSON); err != nil {
		t.Fatal(err)
	}
	sessionID := startedJSON["session"].(map[string]any)["id"].(string)
	waited := doReq(t, srv, http.MethodPost, "/v1/tools/hub_wait", token, []byte(`{"session":"`+sessionID+`","timeout_s":1}`), nil)
	if waited.Code != http.StatusOK {
		t.Fatalf("wait failed code=%d body=%s", waited.Code, waited.Body.String())
	}
	var result map[string]any
	if err := json.Unmarshal(waited.Body.Bytes(), &result); err != nil {
		t.Fatal(err)
	}
	if result["call_again"] != true || result["waited_s"].(float64) < 1 {
		t.Fatalf("expected timeout response after long poll, got %#v", result)
	}
}
