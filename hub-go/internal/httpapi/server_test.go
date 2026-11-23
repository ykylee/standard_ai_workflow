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
	"github.com/ykylee/standard_ai_workflow/hub-go/internal/judge"
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

func TestHTTPGuidePages(t *testing.T) {
	srv, _ := newTestServer(t)
	landing := doReq(t, srv, http.MethodGet, "/", "", nil, nil)
	if landing.Code != http.StatusOK || !strings.Contains(landing.Header().Get("Content-Type"), "text/html") {
		t.Fatalf("landing page code=%d content-type=%q", landing.Code, landing.Header().Get("Content-Type"))
	}
	if landing.Header().Get("Content-Security-Policy") != "default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; frame-ancestors 'none'" || landing.Header().Get("Referrer-Policy") != "same-origin" {
		t.Fatalf("landing security headers missing: %#v", landing.Header())
	}
	for _, want := range []string{"http://127.0.0.1:8770/setup.md", "claude-code", "codex", "minimax-code", "antigravity", "CLAUDE.md", "AGENTS.md", "MiniMax.md", "ANTIGRAVITY.md", "${WORKFLOW_HUB_TOKEN}"} {
		if !strings.Contains(landing.Body.String(), want) {
			t.Errorf("landing page is missing %q", want)
		}
	}

	setup := doReq(t, srv, http.MethodGet, "/setup.md", "", nil, nil)
	if setup.Code != http.StatusOK || !strings.Contains(setup.Header().Get("Content-Type"), "text/markdown") {
		t.Fatalf("setup guide code=%d content-type=%q", setup.Code, setup.Header().Get("Content-Type"))
	}
	for _, want := range []string{"토큰을 출력 · 기록하지 않는다", "커밋 · push 는 하지 않는다", "hub_setup_plan", "hub_setup_confirm", "Python 이 없을 때", "claude mcp add", "codex mcp add", "agy mcp add", "MiniMax.md"} {
		if !strings.Contains(setup.Body.String(), want) {
			t.Errorf("setup guide is missing %q", want)
		}
	}
	if strings.Contains(setup.Body.String(), "secret-token") {
		t.Fatal("setup guide must not include a token")
	}

	missing := doReq(t, srv, http.MethodGet, "/not-a-guide", "", nil, nil)
	if missing.Code != http.StatusNotFound {
		t.Fatalf("unknown GET path status=%d, want 404", missing.Code)
	}
}

func TestHTTPUIStaticAssetsAndRedirect(t *testing.T) {
	srv, _ := newTestServer(t)
	redirect := doReq(t, srv, http.MethodGet, "/ui", "", nil, nil)
	if redirect.Code != http.StatusTemporaryRedirect || redirect.Header().Get("Location") != "ui/" {
		t.Fatalf("/ui redirect code=%d location=%q", redirect.Code, redirect.Header().Get("Location"))
	}
	for name, contentType := range map[string]string{
		"/ui/":            "text/html",
		"/ui/hub.js":      "text/javascript",
		"/ui/hub.css":     "text/css",
		"/ui/favicon.svg": "image/svg+xml",
	} {
		res := doReq(t, srv, http.MethodGet, name, "", nil, nil)
		if res.Code != http.StatusOK || !strings.Contains(res.Header().Get("Content-Type"), contentType) || len(res.Body.Bytes()) == 0 {
			t.Errorf("%s status=%d content-type=%q size=%d", name, res.Code, res.Header().Get("Content-Type"), res.Body.Len())
		}
		if res.Header().Get("X-Content-Type-Options") != "nosniff" || res.Header().Get("Cache-Control") != "no-cache" {
			t.Errorf("%s missing screen security/cache headers: %#v", name, res.Header())
		}
	}
	missing := doReq(t, srv, http.MethodGet, "/ui/unknown.js", "", nil, nil)
	if missing.Code != http.StatusNotFound {
		t.Fatalf("unknown UI asset status=%d, want 404", missing.Code)
	}
}

func TestHTTPUIScreenSessionAndProjectScope(t *testing.T) {
	srv, _ := newTestServer(t)
	unauth := doReq(t, srv, http.MethodGet, "/api/session", "", nil, nil)
	if unauth.Code != http.StatusUnauthorized || unauth.Header().Get("Cache-Control") != "no-store" {
		t.Fatalf("unauthenticated UI session status=%d headers=%#v", unauth.Code, unauth.Header())
	}
	reg := doReq(t, srv, http.MethodPost, "/v1/tools/hub_project_register", "", []byte(`{"remote_url":"https://github.com/acme/ui-screen","display_name":"UI Screen","callsign":"owner-human","kind":"human"}`), nil)
	if reg.Code != http.StatusOK {
		t.Fatalf("project registration failed status=%d body=%s", reg.Code, reg.Body.String())
	}
	var registered map[string]any
	if err := json.Unmarshal(reg.Body.Bytes(), &registered); err != nil {
		t.Fatal(err)
	}
	token := registered["token"].(string)
	projectID := registered["project_id"].(string)
	session := doReq(t, srv, http.MethodGet, "/api/session", token, nil, nil)
	if session.Code != http.StatusOK {
		t.Fatalf("authenticated UI session status=%d body=%s", session.Code, session.Body.String())
	}
	var sessionJSON map[string]any
	if err := json.Unmarshal(session.Body.Bytes(), &sessionJSON); err != nil {
		t.Fatal(err)
	}
	principal := sessionJSON["principal"].(map[string]any)
	if principal["kind"] != "callsign" || principal["project_id"] != projectID || principal["callsign"] != "owner-human" || sessionJSON["web_token"] != false {
		t.Fatalf("unexpected UI principal summary: %#v", sessionJSON)
	}
	projects := doReq(t, srv, http.MethodGet, "/api/projects", token, nil, nil)
	if projects.Code != http.StatusOK {
		t.Fatalf("authenticated UI projects status=%d body=%s", projects.Code, projects.Body.String())
	}
	var projectsJSON map[string]any
	if err := json.Unmarshal(projects.Body.Bytes(), &projectsJSON); err != nil {
		t.Fatal(err)
	}
	rows := projectsJSON["projects"].([]any)
	if len(rows) != 1 || rows[0].(map[string]any)["id"] != projectID {
		t.Fatalf("callsign token did not scope project list: %#v", rows)
	}
}

func TestHTTPUIProjectReadAPIs(t *testing.T) {
	srv, _ := newTestServer(t)
	reg := doReq(t, srv, http.MethodPost, "/v1/tools/hub_project_register", "", []byte(`{"remote_url":"https://github.com/acme/ui-read-api","display_name":"UI Read API","callsign":"owner-human","kind":"human"}`), nil)
	if reg.Code != http.StatusOK {
		t.Fatalf("project registration failed status=%d body=%s", reg.Code, reg.Body.String())
	}
	var registered map[string]any
	if err := json.Unmarshal(reg.Body.Bytes(), &registered); err != nil {
		t.Fatal(err)
	}
	token, pid := registered["token"].(string), registered["project_id"].(string)
	task := doReq(t, srv, http.MethodPost, "/v1/tools/hub_task_create", token, []byte(`{"title":"screen read task"}`), nil)
	if task.Code != http.StatusOK {
		t.Fatalf("task creation failed status=%d body=%s", task.Code, task.Body.String())
	}
	var taskJSON map[string]any
	if err := json.Unmarshal(task.Body.Bytes(), &taskJSON); err != nil {
		t.Fatal(err)
	}
	taskID := taskJSON["task"].(map[string]any)["id"].(string)
	for _, endpoint := range []string{"/api/projects/" + pid, "/api/projects/" + pid + "/tasks", "/api/projects/" + pid + "/tasks/" + taskID, "/api/projects/" + pid + "/callsigns", "/api/projects/" + pid + "/events"} {
		res := doReq(t, srv, http.MethodGet, endpoint, token, nil, nil)
		if res.Code != http.StatusOK {
			t.Errorf("%s status=%d body=%s", endpoint, res.Code, res.Body.String())
			continue
		}
		var payload map[string]any
		if err := json.Unmarshal(res.Body.Bytes(), &payload); err != nil {
			t.Errorf("%s invalid JSON: %v", endpoint, err)
			continue
		}
		switch {
		case strings.HasSuffix(endpoint, "/tasks"):
			if payload["total"] != float64(1) || len(payload["tasks"].([]any)) != 1 {
				t.Errorf("unexpected tasks response: %#v", payload)
			}
		case strings.Contains(endpoint, "/tasks/"):
			if payload["task"].(map[string]any)["id"] != taskID || payload["plan"] == nil {
				t.Errorf("unexpected task detail: %#v", payload)
			}
		case strings.HasSuffix(endpoint, "/callsigns"):
			if len(payload["callsigns"].([]any)) != 1 {
				t.Errorf("unexpected callsign board: %#v", payload)
			}
		case strings.HasSuffix(endpoint, "/events"):
			if _, ok := payload["events"].([]any); !ok {
				t.Errorf("unexpected events response: %#v", payload)
			}
		default:
			if payload["project"].(map[string]any)["id"] != pid {
				t.Errorf("unexpected project response: %#v", payload)
			}
		}
	}
}

func TestHTTPUIExtendedReadAPIs(t *testing.T) {
	srv, st := newTestServer(t)
	reg := doReq(t, srv, http.MethodPost, "/v1/tools/hub_project_register", "", []byte(`{"remote_url":"https://github.com/acme/ui-extended","display_name":"UI Extended","callsign":"owner-human","kind":"human"}`), nil)
	if reg.Code != http.StatusOK {
		t.Fatalf("register status=%d body=%s", reg.Code, reg.Body.String())
	}
	var registered map[string]any
	if err := json.Unmarshal(reg.Body.Bytes(), &registered); err != nil {
		t.Fatal(err)
	}
	token, pid := registered["token"].(string), registered["project_id"].(string)
	if _, err := st.DB().Exec("INSERT INTO wiki_page(project_id,path,body_md,version,updated_by,updated_at,last_ingest) VALUES(?,?,?,?,?,?,?)", pid, "concepts/alpha.md", "# Alpha\nwiki needle", 1, "owner-human", "2026-01-01T00:00:00Z", "ingest-1"); err != nil {
		t.Fatal(err)
	}
	for _, endpoint := range []string{"/api/projects/" + pid + "/callsigns/owner-human", "/api/projects/" + pid + "/guide", "/api/projects/" + pid + "/roadmap", "/api/projects/" + pid + "/wiki", "/api/projects/" + pid + "/wiki?q=needle", "/api/projects/" + pid + "/wiki/page?path=concepts%2Falpha.md", "/api/projects/" + pid + "/wiki/page?path=index.md"} {
		res := doReq(t, srv, http.MethodGet, endpoint, token, nil, nil)
		if res.Code != http.StatusOK {
			t.Errorf("%s status=%d body=%s", endpoint, res.Code, res.Body.String())
			continue
		}
		var payload map[string]any
		if err := json.Unmarshal(res.Body.Bytes(), &payload); err != nil {
			t.Errorf("%s JSON: %v", endpoint, err)
			continue
		}
		if strings.Contains(endpoint, "callsigns/owner-human") && payload["callsign"] == nil {
			t.Errorf("callsign detail missing: %#v", payload)
		}
		if strings.HasSuffix(endpoint, "/guide") && payload["history"] == nil {
			t.Errorf("guide response missing history: %#v", payload)
		}
		if strings.Contains(endpoint, "wiki?q=") && payload["total"] != float64(1) {
			t.Errorf("wiki search mismatch: %#v", payload)
		}
		if strings.Contains(endpoint, "wiki/page?path=concepts") && payload["body"] != "# Alpha\nwiki needle" {
			t.Errorf("wiki page mismatch: %#v", payload)
		}
	}
	planMD := "- Claims: C1 화면에서 결정에 답한다\n- Decisions: D1 [C1] 어느 저장소? | default: sqlite | options: sqlite = 파일 하나; pg = 서버 | state: proposed\n"
	taskBody, _ := json.Marshal(map[string]any{"title": "response route task", "plan_md": planMD})
	task := doReq(t, srv, http.MethodPost, "/v1/tools/hub_task_create", token, taskBody, nil)
	if task.Code != http.StatusOK {
		t.Fatalf("task create: %d %s", task.Code, task.Body.String())
	}
	var created map[string]any
	if err := json.Unmarshal(task.Body.Bytes(), &created); err != nil {
		t.Fatal(err)
	}
	tid := created["task"].(map[string]any)["id"].(string)
	stale := doReq(t, srv, http.MethodPost, "/api/projects/"+pid+"/tasks/"+tid+"/responses", token, []byte(`{"plan_digest":"stale"}`), map[string]string{"Content-Type": "application/json"})
	if stale.Code != http.StatusConflict {
		t.Fatalf("stale response digest status=%d body=%s", stale.Code, stale.Body.String())
	}
	parsed := judge.ParsePlan(strings.Split(strings.TrimSuffix(planMD, "\n"), "\n"))
	digest := judge.PlanDigest(parsed)
	responseBody, _ := json.Marshal(map[string]any{"plan_digest": digest, "values": map[string]string{"D1": "pg"}, "opened": map[string]bool{"D1": true}, "comments": map[string]string{"C1": "checked"}})
	response := doReq(t, srv, http.MethodPost, "/api/projects/"+pid+"/tasks/"+tid+"/responses", token, responseBody, map[string]string{"Content-Type": "application/json"})
	if response.Code != http.StatusOK {
		t.Fatalf("screen response status=%d body=%s", response.Code, response.Body.String())
	}
}

func TestHTTPUICallsignRegisterAndApprove(t *testing.T) {
	srv, _ := newTestServer(t)
	reg := doReq(t, srv, http.MethodPost, "/v1/tools/hub_project_register", "", []byte(`{"remote_url":"https://github.com/acme/ui-callsign-write","display_name":"UI Callsign Write","callsign":"owner-human","kind":"human"}`), nil)
	if reg.Code != http.StatusOK {
		t.Fatalf("project registration failed status=%d body=%s", reg.Code, reg.Body.String())
	}
	var registered map[string]any
	if err := json.Unmarshal(reg.Body.Bytes(), &registered); err != nil {
		t.Fatal(err)
	}
	token, pid := registered["token"].(string), registered["project_id"].(string)
	badType := doReq(t, srv, http.MethodPost, "/api/projects/"+pid+"/callsigns", token, []byte(`{"callsign":"new-human","kind":"human"}`), nil)
	if badType.Code != http.StatusUnsupportedMediaType {
		t.Fatalf("missing JSON content-type status=%d", badType.Code)
	}
	created := doReq(t, srv, http.MethodPost, "/api/projects/"+pid+"/callsigns", token, []byte(`{"callsign":"new-human","kind":"human","label":"test"}`), map[string]string{"Content-Type": "application/json"})
	if created.Code != http.StatusOK {
		t.Fatalf("callsign registration status=%d body=%s", created.Code, created.Body.String())
	}
	var newCallsign map[string]any
	if err := json.Unmarshal(created.Body.Bytes(), &newCallsign); err != nil {
		t.Fatal(err)
	}
	if newCallsign["human_pending"] != true {
		t.Fatalf("unexpected registration result: %#v", newCallsign)
	}
	approve := doReq(t, srv, http.MethodPost, "/api/projects/"+pid+"/callsigns/new-human/approve", token, []byte(`{}`), map[string]string{"Content-Type": "application/json"})
	if approve.Code != http.StatusOK {
		t.Fatalf("callsign approval status=%d body=%s", approve.Code, approve.Body.String())
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
