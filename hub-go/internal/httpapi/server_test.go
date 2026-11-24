package httpapi

import (
	"bytes"
	"encoding/json"
	"fmt"
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
		Store:      st,
		HubVersion: "3.2.0",
		PublicURL:  "http://127.0.0.1:8770",
		Exposure:   "loopback",
		Clock:      func() time.Time { return now },
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
	if hz.Header().Get("X-Hub-Contract") != "hub/1" || hz.Header().Get("X-Hub-Kit") != "2.1.0" || hz.Header().Get("X-Hub-Version") != "3.2.0" {
		t.Fatalf("missing hub headers: %#v", hz.Header())
	}
	var hzJSON map[string]any
	_ = json.Unmarshal(hz.Body.Bytes(), &hzJSON)
	if hzJSON["ok"] != true || hzJSON["exposure"] != "loopback" || hzJSON["hub_version"] != "3.2.0" || hzJSON["kit_version"] != "2.1.0" {
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
	for _, want := range []string{"http://127.0.0.1:8770/setup.md", "Hub 3.2.0", "kit 호환 2.1.0", "claude-code", "codex", "minimax-code", "antigravity", "CLAUDE.md", "AGENTS.md", "MiniMax.md", "ANTIGRAVITY.md", "${WORKFLOW_HUB_TOKEN}"} {
		if !strings.Contains(landing.Body.String(), want) {
			t.Errorf("landing page is missing %q", want)
		}
	}

	setup := doReq(t, srv, http.MethodGet, "/setup.md", "", nil, nil)
	if setup.Code != http.StatusOK || !strings.Contains(setup.Header().Get("Content-Type"), "text/markdown") {
		t.Fatalf("setup guide code=%d content-type=%q", setup.Code, setup.Header().Get("Content-Type"))
	}
	for _, want := range []string{"Hub 3.2.0", "kit 호환 2.1.0", "토큰을 출력 · 기록하지 않는다", "커밋 · push 는 하지 않는다", "hub_setup_plan", "hub_setup_confirm", "--relay", "PC 로컬 중계", "python -m workflow_kit hub relay status", "Python 이 없을 때", "claude mcp add", "codex mcp add", "agy mcp add", "MiniMax.md"} {
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

func TestHTTPUIHarnessReviewRequiresAdminAndHumanOwners(t *testing.T) {
	srv, st := newTestServer(t)
	now := time.Date(2026, 11, 22, 12, 0, 0, 0, time.UTC)
	project, err := st.RegisterProject(store.Ctx{Now: now, Via: "test"}, "https://github.com/acme/harness-review", "Harness review", "owner-human", "human", "", "")
	if err != nil {
		t.Fatal(err)
	}
	owner, err := st.Authenticate(project["token"].(string), &now, "test")
	if err != nil {
		t.Fatal(err)
	}
	report, err := st.HarnessReportSubmit(store.Ctx{Now: now, Via: "mcp", Principal: owner}, map[string]any{
		"harness_id": "review-agent", "display_name": "Review Agent",
		"mcp_transports": []any{"streamable-http"}, "config_formats": []any{"mcp-http-json-v1"},
		"entry_file_candidates": []any{"AGENTS.md"}, "mcp_config_candidates": []any{"review-mcp.json"},
	})
	if err != nil {
		t.Fatal(err)
	}
	adminToken, err := st.IssueHubToken("admin", "reviewer", now)
	if err != nil {
		t.Fatal(err)
	}
	if got := doReq(t, srv, http.MethodGet, "/api/harness-reports", project["token"].(string), nil, nil); got.Code != http.StatusForbidden {
		t.Fatalf("callsign listed global queue: %d %s", got.Code, got.Body.String())
	}
	queued := doReq(t, srv, http.MethodGet, "/api/harness-reports?status=pending", adminToken, nil, nil)
	if queued.Code != http.StatusOK {
		t.Fatalf("admin queue status=%d body=%s", queued.Code, queued.Body.String())
	}
	personRec := doReq(t, srv, http.MethodPost, "/api/harness-people", adminToken, []byte(`{"display_name":"Harness Steward"}`), map[string]string{"Content-Type": "application/json"})
	if personRec.Code != http.StatusOK {
		t.Fatalf("person create status=%d body=%s", personRec.Code, personRec.Body.String())
	}
	var personBody map[string]any
	if err := json.Unmarshal(personRec.Body.Bytes(), &personBody); err != nil {
		t.Fatal(err)
	}
	personID := personBody["person"].(map[string]any)["id"].(string)
	decisionURL := "/api/harness-reports/" + report["report_id"].(string) + "/decision"
	missingOwner := doReq(t, srv, http.MethodPost, decisionURL, adminToken, []byte(`{"decision":"approve"}`), map[string]string{"Content-Type": "application/json"})
	if missingOwner.Code != http.StatusBadRequest {
		t.Fatalf("approval without owner status=%d body=%s", missingOwner.Code, missingOwner.Body.String())
	}
	body, _ := json.Marshal(map[string]any{
		"decision": "approve", "owner_ids": []string{personID}, "note": "reviewed",
		"setup_profile": map[string]any{"kind": "mcp-http-json-v1", "entry_file": "AGENTS.md", "mcp_config_path": "review-mcp.json"},
	})
	approved := doReq(t, srv, http.MethodPost, decisionURL, adminToken, body, map[string]string{"Content-Type": "application/json"})
	if approved.Code != http.StatusOK {
		t.Fatalf("admin decision status=%d body=%s", approved.Code, approved.Body.String())
	}
	registry := doReq(t, srv, http.MethodGet, "/api/harness-registry", adminToken, nil, nil)
	if registry.Code != http.StatusOK || !strings.Contains(registry.Body.String(), "Harness Steward") {
		t.Fatalf("registry owner missing status=%d body=%s", registry.Code, registry.Body.String())
	}
}

func TestHTTPUITaskListFiltersAndPagination(t *testing.T) {
	srv, st := newTestServer(t)
	now := time.Date(2026, 11, 24, 12, 0, 0, 0, time.UTC)
	project, err := st.RegisterProject(store.Ctx{Now: now, Via: "test"}, "https://github.com/acme/task-page-api", "Task page", "owner-human", "human", "", "")
	if err != nil {
		t.Fatal(err)
	}
	p, err := st.Authenticate(project["token"].(string), &now, "test")
	if err != nil {
		t.Fatal(err)
	}
	ctx := store.Ctx{Now: now, Via: "test", Principal: p}
	category := map[string]any{"category": map[string]any{"level_1": "Product", "level_2": "Hub", "level_3": "Listing"}}
	for _, values := range []map[string]any{
		{"title": "page one", "wbs": "M-061/WBS-61.1", "fields": category},
		{"title": "page two", "wbs": "M-061/WBS-61.2", "fields": category},
		{"title": "unlinked", "fields": map[string]any{"category": map[string]any{"level_1": "Operations", "level_2": "Support", "level_3": "Triage"}}},
	} {
		if _, err := st.TaskCreate(ctx, values, "", nil); err != nil {
			t.Fatal(err)
		}
	}
	target := "/api/projects/" + project["project_id"].(string) + "/tasks?roadmap=linked&milestone=M-061&category_level_1=Product&limit=1&offset=1"
	response := doReq(t, srv, http.MethodGet, target, project["token"].(string), nil, nil)
	if response.Code != http.StatusOK {
		t.Fatalf("task page status=%d body=%s", response.Code, response.Body.String())
	}
	var page map[string]any
	if err := json.Unmarshal(response.Body.Bytes(), &page); err != nil {
		t.Fatal(err)
	}
	if page["total"] != float64(2) || page["offset"] != float64(1) || len(page["tasks"].([]any)) != 1 {
		t.Fatalf("unexpected filtered page: %#v", page)
	}
	facets := page["facets"].(map[string]any)
	if len(facets["wbs"].([]any)) != 2 {
		t.Fatalf("missing WBS facets: %#v", facets)
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

func TestHTTPUIGuideProposeAndDecide(t *testing.T) {
	srv, st := newTestServer(t)
	reg := doReq(t, srv, http.MethodPost, "/v1/tools/hub_project_register", "", []byte(`{"remote_url":"https://github.com/acme/ui-guide-write","display_name":"UI Guide Write","callsign":"owner-human","kind":"human"}`), nil)
	if reg.Code != http.StatusOK {
		t.Fatalf("register status=%d body=%s", reg.Code, reg.Body.String())
	}
	var owner map[string]any
	if err := json.Unmarshal(reg.Body.Bytes(), &owner); err != nil {
		t.Fatal(err)
	}
	ownerToken, pid := owner["token"].(string), owner["project_id"].(string)

	direct := doReq(t, srv, http.MethodPost, "/api/projects/"+pid+"/guide", ownerToken, []byte(`{"base_version":0,"body":"owner guide"}`), map[string]string{"Content-Type": "application/json"})
	if direct.Code != http.StatusOK {
		t.Fatalf("direct guide status=%d body=%s", direct.Code, direct.Body.String())
	}
	var directResult map[string]any
	if err := json.Unmarshal(direct.Body.Bytes(), &directResult); err != nil {
		t.Fatal(err)
	}
	if directResult["status"] != "approved" || directResult["applied_version"] != float64(1) {
		t.Fatalf("direct result=%#v", directResult)
	}

	registered := doReq(t, srv, http.MethodPost, "/v1/tools/hub_callsign_register", ownerToken, []byte(fmt.Sprintf(`{"project_id":%q,"callsign":"worker-agent","kind":"agent"}`, pid)), nil)
	if registered.Code != http.StatusOK {
		t.Fatalf("agent register status=%d body=%s", registered.Code, registered.Body.String())
	}
	var agent map[string]any
	if err := json.Unmarshal(registered.Body.Bytes(), &agent); err != nil {
		t.Fatal(err)
	}
	agentToken := agent["token"].(string)
	proposal := doReq(t, srv, http.MethodPost, "/api/projects/"+pid+"/guide", agentToken, []byte(`{"base_version":1,"body":"agent guide","note":"proposal"}`), map[string]string{"Content-Type": "application/json"})
	if proposal.Code != http.StatusOK {
		t.Fatalf("proposal status=%d body=%s", proposal.Code, proposal.Body.String())
	}
	var proposalResult map[string]any
	if err := json.Unmarshal(proposal.Body.Bytes(), &proposalResult); err != nil {
		t.Fatal(err)
	}
	if proposalResult["status"] != "open" || proposalResult["proposal_id"] != "GP-0002" {
		t.Fatalf("proposal result=%#v", proposalResult)
	}
	unauthorizedDecision := doReq(t, srv, http.MethodPost, "/api/projects/"+pid+"/guide/proposals/GP-0002", agentToken, []byte(`{"approve":true}`), map[string]string{"Content-Type": "application/json"})
	if unauthorizedDecision.Code != http.StatusForbidden {
		t.Fatalf("agent decision status=%d body=%s", unauthorizedDecision.Code, unauthorizedDecision.Body.String())
	}
	decision := doReq(t, srv, http.MethodPost, "/api/projects/"+pid+"/guide/proposals/GP-0002", ownerToken, []byte(`{"approve":true}`), map[string]string{"Content-Type": "application/json"})
	if decision.Code != http.StatusOK {
		t.Fatalf("decision status=%d body=%s", decision.Code, decision.Body.String())
	}
	var decisionResult map[string]any
	if err := json.Unmarshal(decision.Body.Bytes(), &decisionResult); err != nil {
		t.Fatal(err)
	}
	if decisionResult["status"] != "approved" || decisionResult["applied_version"] != float64(2) {
		t.Fatalf("decision result=%#v", decisionResult)
	}
	var versions int
	if err := st.DB().QueryRow("SELECT COUNT(*) FROM guide WHERE project_id=?", pid).Scan(&versions); err != nil {
		t.Fatal(err)
	}
	if versions != 2 {
		t.Fatalf("guide versions=%d, want 2", versions)
	}

	stale := doReq(t, srv, http.MethodPost, "/api/projects/"+pid+"/guide", agentToken, []byte(`{"base_version":1,"body":"stale guide"}`), map[string]string{"Content-Type": "application/json"})
	if stale.Code != http.StatusConflict {
		t.Fatalf("stale proposal status=%d body=%s", stale.Code, stale.Body.String())
	}
	floatVersion := doReq(t, srv, http.MethodPost, "/api/projects/"+pid+"/guide", agentToken, []byte(`{"base_version":2.0,"body":"float version"}`), map[string]string{"Content-Type": "application/json"})
	if floatVersion.Code != http.StatusBadRequest {
		t.Fatalf("float base_version status=%d body=%s", floatVersion.Code, floatVersion.Body.String())
	}
	trailingJSON := doReq(t, srv, http.MethodPost, "/api/projects/"+pid+"/guide", agentToken, []byte(`{"base_version":2,"body":"trailing"} {}`), map[string]string{"Content-Type": "application/json"})
	if trailingJSON.Code != http.StatusBadRequest {
		t.Fatalf("trailing JSON status=%d body=%s", trailingJSON.Code, trailingJSON.Body.String())
	}
	largeBody, _ := json.Marshal(map[string]any{"base_version": 2, "body": strings.Repeat("x", 7000)})
	tooLarge := doReq(t, srv, http.MethodPost, "/api/projects/"+pid+"/guide", agentToken, largeBody, map[string]string{"Content-Type": "application/json"})
	if tooLarge.Code != http.StatusUnprocessableEntity {
		t.Fatalf("over-budget proposal status=%d body=%s", tooLarge.Code, tooLarge.Body.String())
	}
}

func TestHTTPUIOrchestrationRoutes(t *testing.T) {
	srv, st := newTestServer(t)
	reg := doReq(t, srv, http.MethodPost, "/v1/tools/hub_project_register", "", []byte(`{"remote_url":"https://github.com/acme/ui-orchestration","display_name":"UI Orchestration","callsign":"owner-human","kind":"human"}`), nil)
	if reg.Code != http.StatusOK {
		t.Fatalf("register status=%d body=%s", reg.Code, reg.Body.String())
	}
	var project map[string]any
	if err := json.Unmarshal(reg.Body.Bytes(), &project); err != nil {
		t.Fatal(err)
	}
	token, pid := project["token"].(string), project["project_id"].(string)
	start := doReq(t, srv, http.MethodPost, "/v1/tools/hub_session_start", token, []byte(`{"session":{"harness":"codex"}}`), nil)
	if start.Code != http.StatusOK {
		t.Fatalf("session start status=%d body=%s", start.Code, start.Body.String())
	}
	var started map[string]any
	if err := json.Unmarshal(start.Body.Bytes(), &started); err != nil {
		t.Fatal(err)
	}
	sessionID := started["session"].(map[string]any)["id"].(string)
	start2 := doReq(t, srv, http.MethodPost, "/v1/tools/hub_session_start", token, []byte(`{"session":{"harness":"claude-code"}}`), nil)
	if start2.Code != http.StatusOK {
		t.Fatalf("second session start status=%d body=%s", start2.Code, start2.Body.String())
	}
	var started2 map[string]any
	if err := json.Unmarshal(start2.Body.Bytes(), &started2); err != nil {
		t.Fatal(err)
	}
	sessionID2 := started2["session"].(map[string]any)["id"].(string)
	base := "/api/projects/" + pid + "/orchestration"
	for _, body := range []string{`{"action":"declare","session":"` + sessionID + `"}`, `{"action":"transfer","session":"` + sessionID2 + `"}`, `{"action":"release"}`, `{"action":"declare","session":"` + sessionID + `"}`} {
		res := doReq(t, srv, http.MethodPost, base+"/lease", token, []byte(body), map[string]string{"Content-Type": "application/json"})
		if res.Code != http.StatusOK {
			t.Fatalf("lease %s status=%d body=%s", body, res.Code, res.Body.String())
		}
	}
	for _, on := range []bool{true, false} {
		body, _ := json.Marshal(map[string]bool{"on": on})
		res := doReq(t, srv, http.MethodPost, base+"/halt", token, body, map[string]string{"Content-Type": "application/json"})
		if res.Code != http.StatusOK {
			t.Fatalf("halt=%v status=%d body=%s", on, res.Code, res.Body.String())
		}
	}
	if _, err := st.DB().Exec("INSERT INTO relay_host(host_id,name,token_hash,owner_callsign,projects_json,harnesses_json) VALUES(?,?,?,?,?,?)", "H-ui", "test relay", store.HashToken("relay-token"), "owner-human", store.MustJSON([]string{pid}), store.MustJSON([]string{"codex"})); err != nil {
		t.Fatal(err)
	}
	agentRegistration := doReq(t, srv, http.MethodPost, "/v1/tools/hub_callsign_register", token, []byte(fmt.Sprintf(`{"project_id":%q,"callsign":"viewer-agent","kind":"agent"}`, pid)), nil)
	if agentRegistration.Code != http.StatusOK {
		t.Fatalf("agent registration status=%d body=%s", agentRegistration.Code, agentRegistration.Body.String())
	}
	var agentPayload map[string]any
	if err := json.Unmarshal(agentRegistration.Body.Bytes(), &agentPayload); err != nil {
		t.Fatal(err)
	}
	agentToken := agentPayload["token"].(string)
	agentHalt := doReq(t, srv, http.MethodPost, base+"/halt", agentToken, []byte(`{"on":true}`), map[string]string{"Content-Type": "application/json"})
	if agentHalt.Code != http.StatusForbidden {
		t.Fatalf("agent halt status=%d body=%s", agentHalt.Code, agentHalt.Body.String())
	}
	if _, err := st.DB().Exec("INSERT INTO session_request(project_id,id,kind,host_id,target_json,requested_by,state,created_at) VALUES(?,?, 'spawn', ?, ?, ?, 'pending_approval', ?)", pid, "SR-0001", "H-ui", `{"dir_alias":"repo","harness":"codex"}`, sessionID, "2026-11-22T12:00:00Z"); err != nil {
		t.Fatal(err)
	}
	decision := doReq(t, srv, http.MethodPost, base+"/approvals/SR-0001", token, []byte(`{"decision":"approve","note":"checked"}`), map[string]string{"Content-Type": "application/json"})
	if decision.Code != http.StatusOK {
		t.Fatalf("approval decision status=%d body=%s", decision.Code, decision.Body.String())
	}
	invite := doReq(t, srv, http.MethodPost, base+"/relays/invite", token, []byte(`{}`), map[string]string{"Content-Type": "application/json"})
	if invite.Code != http.StatusOK {
		t.Fatalf("relay invite status=%d body=%s", invite.Code, invite.Body.String())
	}
	var inviteResult map[string]any
	if err := json.Unmarshal(invite.Body.Bytes(), &inviteResult); err != nil {
		t.Fatal(err)
	}
	if _, ok := inviteResult["invite"].(string); !ok || !strings.Contains(inviteResult["command"].(string), "http://127.0.0.1:8770") {
		t.Fatalf("invite result=%#v", inviteResult)
	}
	view := doReq(t, srv, http.MethodGet, base, token, nil, nil)
	if view.Code != http.StatusOK {
		t.Fatalf("orchestration view status=%d body=%s", view.Code, view.Body.String())
	}
	var snapshot map[string]any
	if err := json.Unmarshal(view.Body.Bytes(), &snapshot); err != nil {
		t.Fatal(err)
	}
	if snapshot["principal"].(map[string]any)["can_manage"] != true || snapshot["orchestrator"].(map[string]any)["session"] != sessionID {
		t.Fatalf("orchestration snapshot=%#v", snapshot)
	}
	if len(snapshot["hosts"].([]any)) != 1 || len(snapshot["requests"].([]any)) != 1 {
		t.Fatalf("orchestration hosts/requests=%#v", snapshot)
	}
	revoke := doReq(t, srv, http.MethodPost, base+"/relays/H-ui/revoke", token, []byte(`{}`), map[string]string{"Content-Type": "application/json"})
	if revoke.Code != http.StatusOK {
		t.Fatalf("relay revoke status=%d body=%s", revoke.Code, revoke.Body.String())
	}
}

func TestHTTPRelayRegisterPollResult(t *testing.T) {
	srv, st := newTestServer(t)
	reg := doReq(t, srv, http.MethodPost, "/v1/tools/hub_project_register", "", []byte(`{"remote_url":"https://github.com/acme/relay-http","display_name":"Relay HTTP","callsign":"owner-human","kind":"human"}`), nil)
	if reg.Code != http.StatusOK {
		t.Fatalf("project register status=%d body=%s", reg.Code, reg.Body.String())
	}
	var project map[string]any
	if err := json.Unmarshal(reg.Body.Bytes(), &project); err != nil {
		t.Fatal(err)
	}
	ownerToken, pid := project["token"].(string), project["project_id"].(string)
	invitePath := "/api/projects/" + pid + "/orchestration/relays/invite"
	inviteResponse := doReq(t, srv, http.MethodPost, invitePath, ownerToken, []byte(`{}`), map[string]string{"Content-Type": "application/json"})
	if inviteResponse.Code != http.StatusOK {
		t.Fatalf("invite status=%d body=%s", inviteResponse.Code, inviteResponse.Body.String())
	}
	var invitePayload map[string]any
	if err := json.Unmarshal(inviteResponse.Body.Bytes(), &invitePayload); err != nil {
		t.Fatal(err)
	}
	inviteCode := invitePayload["invite"].(string)
	registerBody, _ := json.Marshal(map[string]any{"invite": inviteCode, "name": "Test PC", "harnesses": []string{"codex"}})
	registered := doReq(t, srv, http.MethodPost, "/v1/relay/register", "", registerBody, nil)
	if registered.Code != http.StatusOK {
		t.Fatalf("relay register status=%d body=%s", registered.Code, registered.Body.String())
	}
	var relay map[string]any
	if err := json.Unmarshal(registered.Body.Bytes(), &relay); err != nil {
		t.Fatal(err)
	}
	hostID, relayToken := relay["host_id"].(string), relay["token"].(string)
	if relay["project_id"] != pid || !strings.HasPrefix(hostID, "H-20261122-") {
		t.Fatalf("relay registration=%#v", relay)
	}
	var storedHash string
	if err := st.DB().QueryRow("SELECT token_hash FROM relay_host WHERE host_id=?", hostID).Scan(&storedHash); err != nil {
		t.Fatal(err)
	}
	if storedHash == relayToken || storedHash != store.HashToken(relayToken) {
		t.Fatal("relay token was not stored as a hash")
	}

	badAuth := doReq(t, srv, http.MethodPost, "/v1/relay/poll", "", []byte(`{"wait_s":0}`), nil)
	if badAuth.Code != http.StatusUnauthorized {
		t.Fatalf("missing relay auth status=%d", badAuth.Code)
	}
	callsignAuth := doReq(t, srv, http.MethodPost, "/v1/relay/poll", ownerToken, []byte(`{"wait_s":0}`), nil)
	if callsignAuth.Code != http.StatusUnauthorized {
		t.Fatalf("callsign token on relay route status=%d", callsignAuth.Code)
	}
	firstPoll := doReq(t, srv, http.MethodPost, "/v1/relay/poll", relayToken, []byte(`{"wait_s":0,"allow_digest":"allow-v1","sessions":[]}`), nil)
	if firstPoll.Code != http.StatusOK {
		t.Fatalf("poll status=%d body=%s", firstPoll.Code, firstPoll.Body.String())
	}
	var pollPayload map[string]any
	if err := json.Unmarshal(firstPoll.Body.Bytes(), &pollPayload); err != nil {
		t.Fatal(err)
	}
	if pollPayload["dispatch"] == nil || pollPayload["deliver"] == nil || pollPayload["halted"] == nil || pollPayload["sessions"] == nil || pollPayload["waited_s"] != float64(0) {
		t.Fatalf("poll response=%#v", pollPayload)
	}
	unknownPollField := doReq(t, srv, http.MethodPost, "/v1/relay/poll", relayToken, []byte(`{"wait_s":0,"unexpected":true}`), nil)
	if unknownPollField.Code != http.StatusBadRequest {
		t.Fatalf("unknown poll field status=%d body=%s", unknownPollField.Code, unknownPollField.Body.String())
	}
	floatWait := doReq(t, srv, http.MethodPost, "/v1/relay/poll", relayToken, []byte(`{"wait_s":1.0}`), nil)
	if floatWait.Code != http.StatusBadRequest {
		t.Fatalf("float wait_s status=%d body=%s", floatWait.Code, floatWait.Body.String())
	}
	if _, err := st.DB().Exec("INSERT INTO session_request(project_id,id,kind,host_id,target_json,requested_by,state,created_at) VALUES(?,?,?,?,?,?,?,?)", pid, "SR-0001", "spawn", hostID, `{"dir_alias":"repo","harness":"codex"}`, "owner-human", "approved", "2026-11-22T12:00:00Z"); err != nil {
		t.Fatal(err)
	}
	dispatch := doReq(t, srv, http.MethodPost, "/v1/relay/poll", relayToken, []byte(`{"wait_s":0}`), nil)
	if dispatch.Code != http.StatusOK {
		t.Fatalf("dispatch poll status=%d body=%s", dispatch.Code, dispatch.Body.String())
	}
	var dispatchPayload map[string]any
	if err := json.Unmarshal(dispatch.Body.Bytes(), &dispatchPayload); err != nil {
		t.Fatal(err)
	}
	if len(dispatchPayload["dispatch"].([]any)) != 1 {
		t.Fatalf("dispatch payload=%#v", dispatchPayload)
	}
	result := doReq(t, srv, http.MethodPost, "/v1/relay/result", relayToken, []byte(`{"project_id":"`+pid+`","request":"SR-0001","state":"done","result":{"session":"S-20261122-aabbccdd"}}`), nil)
	if result.Code != http.StatusOK {
		t.Fatalf("result status=%d body=%s", result.Code, result.Body.String())
	}
	var requestState string
	if err := st.DB().QueryRow("SELECT state FROM session_request WHERE project_id=? AND id=?", pid, "SR-0001").Scan(&requestState); err != nil {
		t.Fatal(err)
	}
	if requestState != "done" {
		t.Fatalf("request state=%q", requestState)
	}
	secondResult := doReq(t, srv, http.MethodPost, "/v1/relay/result", relayToken, []byte(`{"project_id":"`+pid+`","request":"SR-0001","state":"done"}`), nil)
	if secondResult.Code != http.StatusConflict {
		t.Fatalf("duplicate result status=%d body=%s", secondResult.Code, secondResult.Body.String())
	}
	replay := doReq(t, srv, http.MethodPost, "/v1/relay/register", "", registerBody, nil)
	if replay.Code != http.StatusForbidden {
		t.Fatalf("invite replay status=%d body=%s", replay.Code, replay.Body.String())
	}
	revoke := doReq(t, srv, http.MethodPost, "/api/projects/"+pid+"/orchestration/relays/"+hostID+"/revoke", ownerToken, []byte(`{}`), map[string]string{"Content-Type": "application/json"})
	if revoke.Code != http.StatusOK {
		t.Fatalf("revoke status=%d body=%s", revoke.Code, revoke.Body.String())
	}
	revoked := doReq(t, srv, http.MethodPost, "/v1/relay/poll", relayToken, []byte(`{"wait_s":0}`), nil)
	if revoked.Code != http.StatusUnauthorized {
		t.Fatalf("revoked relay token status=%d", revoked.Code)
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
