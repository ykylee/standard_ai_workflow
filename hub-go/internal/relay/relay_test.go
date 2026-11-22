package relay

import (
	"bytes"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/http/httptest"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"
	"sync"
	"testing"
	"time"
)

func TestMain(m *testing.M) {
	if len(os.Args) > 1 && os.Args[1] == "__fake-worker" {
		os.Exit(RunFakeWorker())
	}
	os.Exit(m.Run())
}

func TestAllowDigestAndValidation(t *testing.T) {
	work := t.TempDir()
	entry := AllowEntry{
		Alias:           "w",
		Path:            work,
		Project:         "P-1",
		Harnesses:       []string{"fake"},
		PermissionModes: []string{"default"},
		MaxSessions:     2,
	}
	if errMsg := ValidateEntry(entry); errMsg != "" {
		t.Fatalf("unexpected validation error: %s", errMsg)
	}

	// Python: json.dumps([entry], ensure_ascii=False, sort_keys=True, separators=(",", ":"))
	wantRaw := fmt.Sprintf(`[{"alias":"w","harnesses":["fake"],"max_sessions":2,"path":%q,"permission_modes":["default"],"project":"P-1"}]`, work)
	wantSum := sha256.Sum256([]byte(wantRaw))
	wantDigest := "sha256:" + hex.EncodeToString(wantSum[:])
	if got := AllowDigest([]AllowEntry{entry}); got != wantDigest {
		t.Fatalf("AllowDigest mismatch:\n got: %s\nwant: %s\n raw: %s", got, wantDigest, wantRaw)
	}

	badBypass := entry
	badBypass.PermissionModes = []string{"bypassPermissions"}
	if msg := ValidateEntry(badBypass); !strings.Contains(msg, "bypass") {
		t.Fatalf("expected bypass rejection, got %q", msg)
	}

	badDir := entry
	badDir.Path = filepath.Join(work, "nope")
	if msg := ValidateEntry(badDir); !strings.Contains(msg, "디렉터리가 없다") {
		t.Fatalf("expected missing dir rejection, got %q", msg)
	}

	gotEntry, why := CheckRequest([]AllowEntry{entry}, "P-1", map[string]any{
		"dir_alias": "nope",
		"harness":   "fake",
	}, map[string]int{})
	if gotEntry != nil || !strings.Contains(why, "허용 목록에 없는 별칭") {
		t.Fatalf("unexpected CheckRequest result: entry=%v why=%q", gotEntry, why)
	}

	gotEntry, why = CheckRequest([]AllowEntry{entry}, "P-1", map[string]any{
		"dir_alias": "w",
		"harness":   "fake",
	}, map[string]int{"w": 2})
	if gotEntry != nil || !strings.Contains(why, "동시 세션 상한") {
		t.Fatalf("expected max sessions refusal, got entry=%v why=%q", gotEntry, why)
	}
}

func TestCLIInitAllowPauseStatus(t *testing.T) {
	home := t.TempDir()
	t.Setenv(HomeEnv, home)
	work := t.TempDir()

	usedInvite := false
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		var body map[string]any
		_ = json.NewDecoder(r.Body).Decode(&body)
		w.Header().Set("Content-Type", "application/json")
		if r.URL.Path != "/v1/relay/register" {
			w.WriteHeader(404)
			return
		}
		if usedInvite || body["invite"] != "wri_test" {
			w.WriteHeader(403)
			_ = json.NewEncoder(w).Encode(map[string]any{
				"error_code": "invite_invalid",
				"message":    "초대 코드가 없거나 · 썼거나 · 만료됐다",
			})
			return
		}
		usedInvite = true
		_ = json.NewEncoder(w).Encode(map[string]any{
			"host_id":    "H-20261122-abcd",
			"token":      "secret-relay-tok-1",
			"project_id": "P-1",
		})
	}))
	defer srv.Close()

	var out, errBuf bytes.Buffer
	rc := Main([]string{"init", "--hub", srv.URL, "--invite", "wri_test", "--name", "pc-1", "--harness", "fake"}, &out, &errBuf)
	if rc != 0 {
		t.Fatalf("init rc=%d stderr=%s", rc, errBuf.String())
	}
	if strings.Contains(out.String(), "secret-relay-tok-1") {
		t.Fatalf("token leaked to stdout")
	}
	tokBytes, err := os.ReadFile(filepath.Join(home, "relay.token"))
	if err != nil || strings.TrimSpace(string(tokBytes)) != "secret-relay-tok-1" {
		t.Fatalf("token file mismatch: %v %q", err, string(tokBytes))
	}
	if runtime.GOOS != "windows" {
		info, _ := os.Stat(filepath.Join(home, "relay.token"))
		if info.Mode().Perm() != 0o600 {
			t.Fatalf("token mode=%o, want 0600", info.Mode().Perm())
		}
	}
	cfgRaw, _ := os.ReadFile(filepath.Join(home, "relay.json"))
	if strings.Contains(string(cfgRaw), "secret-relay-tok-1") {
		t.Fatalf("token leaked to relay.json")
	}

	out.Reset()
	errBuf.Reset()
	rc2 := Main([]string{"init", "--hub", srv.URL, "--invite", "wri_test", "--name", "pc-2", "--harness", "fake"}, &out, &errBuf)
	if rc2 != 1 || !strings.Contains(errBuf.String(), "invite_invalid") {
		t.Fatalf("expected reuse invite error, rc=%d stderr=%q", rc2, errBuf.String())
	}

	out.Reset()
	errBuf.Reset()
	if rc := Main([]string{"allow", "add", "--alias", "w", "--path", work, "--harness", "fake", "--permission-mode", "bypassPermissions"}, &out, &errBuf); rc != 2 || !strings.Contains(errBuf.String(), "bypass") {
		t.Fatalf("expected bypass fail, rc=%d stderr=%q", rc, errBuf.String())
	}

	out.Reset()
	errBuf.Reset()
	if rc := Main([]string{"allow", "add", "--alias", "w", "--path", work, "--harness", "fake", "--max-sessions", "2"}, &out, &errBuf); rc != 0 {
		t.Fatalf("allow add failed: rc=%d stderr=%q", rc, errBuf.String())
	}

	out.Reset()
	errBuf.Reset()
	if rc := Main([]string{"pause"}, &out, &errBuf); rc != 0 || !strings.Contains(out.String(), `"paused": true`) {
		t.Fatalf("pause failed: rc=%d out=%q", rc, out.String())
	}
	out.Reset()
	if rc := Main([]string{"status"}, &out, &errBuf); rc != 0 || !strings.Contains(out.String(), `"paused": true`) || !strings.Contains(out.String(), `"registered": true`) {
		t.Fatalf("status failed: rc=%d out=%q", rc, out.String())
	}
	out.Reset()
	if rc := Main([]string{"resume"}, &out, &errBuf); rc != 0 || !strings.Contains(out.String(), `"paused": false`) {
		t.Fatalf("resume failed: rc=%d out=%q", rc, out.String())
	}
}

func TestRunnerAndUI(t *testing.T) {
	home := t.TempDir()
	t.Setenv(HomeEnv, home)
	work := t.TempDir()

	if err := WriteToken("tok-runner"); err != nil {
		t.Fatal(err)
	}
	if err := WriteJSON("relay.json", map[string]any{
		"hub":        "http://placeholder",
		"host_id":    "H-1",
		"project_id": "P-1",
		"name":       "pc-1",
		"harnesses":  []string{"fake"},
	}); err != nil {
		t.Fatal(err)
	}
	if err := SaveAllow([]AllowEntry{{
		Alias:           "w",
		Path:            work,
		Project:         "P-1",
		Harnesses:       []string{"fake"},
		PermissionModes: []string{"default"},
		MaxSessions:     2,
	}}); err != nil {
		t.Fatal(err)
	}

	var mu sync.Mutex
	results := []map[string]any{}
	reportedStates := []string{}
	pollStep := 0

	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		var body map[string]any
		_ = json.NewDecoder(r.Body).Decode(&body)
		w.Header().Set("Content-Type", "application/json")
		mu.Lock()
		defer mu.Unlock()
		switch r.URL.Path {
		case "/v1/relay/result":
			results = append(results, body)
			_ = json.NewEncoder(w).Encode(map[string]any{"request": body["request"], "state": body["state"]})
		case "/v1/relay/poll":
			if sessList, ok := body["sessions"].([]any); ok {
				for _, item := range sessList {
					if m, ok := item.(map[string]any); ok {
						reportedStates = append(reportedStates, fmt.Sprint(m["status"]))
					}
				}
			}
			pollStep++
			switch pollStep {
			case 1:
				_ = json.NewEncoder(w).Encode(map[string]any{
					"dispatch": []any{
						map[string]any{
							"project_id": "P-1",
							"request":    "SR-0001",
							"kind":       "spawn",
							"target": map[string]any{
								"dir_alias": "w",
								"harness":   "fake",
								"prompt":    "지시-P1",
							},
						},
						map[string]any{
							"project_id": "P-1",
							"request":    "SR-0002",
							"kind":       "spawn",
							"target": map[string]any{
								"dir_alias": "nope",
								"harness":   "fake",
							},
						},
					},
					"deliver":  []any{},
					"halted":   []any{},
					"sessions": []any{},
				})
			case 2:
				_ = json.NewEncoder(w).Encode(map[string]any{
					"dispatch": []any{},
					"deliver": []any{
						map[string]any{
							"session":    "S-0001",
							"project_id": "P-1",
							"messages": []any{
								map[string]any{
									"id":   "M-0001",
									"kind": "note",
									"from": map[string]any{"callsign": "agent-o", "orchestrator": true},
									"body": "중계로-M1",
								},
							},
						},
					},
					"halted": []any{},
					"sessions": []any{
						map[string]any{"session": "S-0001", "request": "SR-0001", "project_id": "P-1"},
					},
				})
			case 3:
				_ = json.NewEncoder(w).Encode(map[string]any{
					"dispatch": []any{
						map[string]any{
							"project_id": "P-1",
							"request":    "SR-0003",
							"kind":       "stop",
							"target":     map[string]any{"session": "S-0001"},
						},
					},
					"deliver":  []any{},
					"halted":   []any{},
					"sessions": []any{},
				})
			default:
				_ = json.NewEncoder(w).Encode(map[string]any{
					"dispatch": []any{},
					"deliver":  []any{},
					"halted":   []any{},
					"sessions": []any{},
				})
			}
		}
	}))
	defer srv.Close()

	cfg, _ := ReadJSON("relay.json")
	cfg["hub"] = srv.URL
	_ = WriteJSON("relay.json", cfg)

	relay, err := NewRelay(nil)
	if err != nil {
		t.Fatal(err)
	}
	defer relay.StopAll()

	if _, err := relay.Once(0); err != nil {
		t.Fatal(err)
	}
	// Fake worker 가 첫 프롬프트를 기록할 짧은 여유
	logPath := filepath.Join(work, ".relay-fake.log")
	deadline := time.Now().Add(3 * time.Second)
	for time.Now().Before(deadline) {
		if b, err := os.ReadFile(logPath); err == nil && strings.Contains(string(b), "지시-P1") {
			break
		}
		time.Sleep(50 * time.Millisecond)
	}
	logBytes, err := os.ReadFile(logPath)
	if err != nil || !strings.Contains(string(logBytes), "SR-0001") || !strings.Contains(string(logBytes), "지시-P1") {
		t.Fatalf("fake log missing first prompt: err=%v content=%q", err, string(logBytes))
	}

	mu.Lock()
	if len(results) != 2 || results[0]["state"] != "done" || results[1]["state"] != "refused_by_host" {
		t.Fatalf("unexpected dispatch results: %+v", results)
	}
	mu.Unlock()

	polled2, err := relay.Once(0)
	if err != nil {
		t.Fatal(err)
	}
	// 재전달 중복 제거 검증: 같은 전달 페이로드를 한 번 더 넘겨도 로그에는 1줄만
	if delivs, ok := polled2["deliver"].([]any); ok {
		for _, item := range delivs {
			if m, ok := item.(map[string]any); ok {
				relay.DeliverSession(m)
			}
		}
	}
	deadline = time.Now().Add(3 * time.Second)
	for time.Now().Before(deadline) {
		if b, err := os.ReadFile(logPath); err == nil && strings.Contains(string(b), "중계로-M1") {
			break
		}
		time.Sleep(50 * time.Millisecond)
	}
	time.Sleep(100 * time.Millisecond)
	logBytes, _ = os.ReadFile(logPath)
	if count := strings.Count(string(logBytes), "note M-0001"); count != 1 {
		t.Fatalf("expected M-0001 delivered once, got count=%d log=%q", count, string(logBytes))
	}

	// UI 검증 (port 0 으로 OS 자유 포트)
	uiSrv, uport, err := StartUI(relay, 0)
	if err != nil {
		t.Fatal(err)
	}
	defer uiSrv.Close()
	ubase := fmt.Sprintf("http://127.0.0.1:%d", uport)

	resp, err := http.Get(ubase + "/")
	if err != nil {
		t.Fatal(err)
	}
	pageBytes, _ := io.ReadAll(resp.Body)
	resp.Body.Close()
	csp := resp.Header.Get("Content-Security-Policy")
	if csp != relayCSP || resp.Header.Get("X-Frame-Options") != "" {
		t.Fatalf("unexpected security headers: csp=%q xfo=%q", csp, resp.Header.Get("X-Frame-Options"))
	}
	if !strings.Contains(string(pageBytes), "pc-1") || !strings.Contains(string(pageBytes), "<table>") || strings.Contains(string(pageBytes), "tok-runner") {
		t.Fatalf("unexpected UI HTML")
	}

	reqBad, _ := http.NewRequest(http.MethodPost, ubase+"/api/pause", nil)
	rBad, err := http.DefaultClient.Do(reqBad)
	if err != nil || rBad.StatusCode != 403 {
		t.Fatalf("expected 403 without header, got err=%v code=%v", err, rBad)
	}
	rBad.Body.Close()

	reqForeign, _ := http.NewRequest(http.MethodPost, ubase+"/api/pause", nil)
	reqForeign.Header.Set("X-Relay-UI", "1")
	reqForeign.Header.Set("Origin", "https://evil.example")
	rForeign, err := http.DefaultClient.Do(reqForeign)
	if err != nil || rForeign.StatusCode != 403 {
		t.Fatalf("expected 403 on foreign origin")
	}
	rForeign.Body.Close()

	reqPause, _ := http.NewRequest(http.MethodPost, ubase+"/api/pause", nil)
	reqPause.Header.Set("X-Relay-UI", "1")
	reqPause.Header.Set("Origin", ubase)
	rPause, err := http.DefaultClient.Do(reqPause)
	if err != nil || rPause.StatusCode != 200 {
		t.Fatalf("expected 200 on valid pause, got err=%v code=%v", err, rPause)
	}
	rPause.Body.Close()

	pausedPoll, err := relay.Once(0)
	if err != nil || pausedPoll["paused"] != true {
		t.Fatalf("expected paused poll, got %v err=%v", pausedPoll, err)
	}

	reqResume, _ := http.NewRequest(http.MethodPost, ubase+"/api/resume", nil)
	reqResume.Header.Set("X-Relay-UI", "1")
	rResume, err := http.DefaultClient.Do(reqResume)
	if err != nil || rResume.StatusCode != 200 {
		t.Fatalf("expected 200 on resume")
	}
	rResume.Body.Close()

	// stop 요청 처리 및 ended 보고
	if _, err := relay.Once(0); err != nil {
		t.Fatal(err)
	}
	relay.Mu.Lock()
	h := relay.Handles["SR-0001"]
	relay.Mu.Unlock()
	if h == nil || h.Alive() {
		t.Fatalf("expected SR-0001 stopped")
	}
	if _, err := relay.Once(0); err != nil {
		t.Fatal(err)
	}
	mu.Lock()
	hasEnded := false
	for _, st := range reportedStates {
		if st == "ended" {
			hasEnded = true
		}
	}
	mu.Unlock()
	if !hasEnded {
		t.Fatalf("expected ended reported in poll, got %v", reportedStates)
	}
}

func TestCodexSandboxPolicy(t *testing.T) {
	if _, err := exec.LookPath("git"); err != nil {
		t.Skip("git not installed")
	}
	tmp := t.TempDir()
	repo := filepath.Join(tmp, "cx-repo")
	if err := os.MkdirAll(repo, 0o755); err != nil {
		t.Fatal(err)
	}
	runGit := func(dir string, args ...string) {
		full := append([]string{"-c", "user.name=t", "-c", "user.email=t@example.invalid", "-C", dir}, args...)
		out, err := exec.Command("git", full...).CombinedOutput()
		if err != nil {
			t.Fatalf("git %v failed: %v (%s)", args, err, string(out))
		}
	}
	runGit(repo, "init", "-q")
	runGit(repo, "commit", "-q", "--allow-empty", "-m", "init")
	wt := filepath.Join(tmp, "cx-wt")
	runGit(repo, "worktree", "add", "-q", "-b", "wt", wt)
	plain := filepath.Join(tmp, "cx-plain")
	if err := os.MkdirAll(plain, 0o755); err != nil {
		t.Fatal(err)
	}

	realPath := func(p string) string {
		r, err := filepath.EvalSymlinks(p)
		if err != nil {
			return p
		}
		return r
	}

	pol := SandboxPolicy("workspace-write", repo)
	if pol == nil || pol["type"] != "workspaceWrite" {
		t.Fatalf("unexpected policy: %+v", pol)
	}
	roots := pol["writableRoots"].([]string)
	if len(roots) != 2 || realPath(roots[0]) != realPath(repo) || realPath(roots[1]) != realPath(filepath.Join(repo, ".git")) {
		t.Fatalf("unexpected repo roots: %v", roots)
	}

	wtPol := SandboxPolicy("workspace-write", wt)
	wtRoots := wtPol["writableRoots"].([]string)
	if len(wtRoots) != 3 {
		t.Fatalf("expected 3 roots for worktree (wt, git-dir, common-dir), got %v", wtRoots)
	}

	plainPol := SandboxPolicy("workspace-write", plain)
	plainRoots := plainPol["writableRoots"].([]string)
	if len(plainRoots) != 1 || plainRoots[0] != plain {
		t.Fatalf("unexpected plain roots: %v", plainRoots)
	}

	if planPol := SandboxPolicy("read-only", repo); planPol != nil {
		t.Fatalf("expected nil policy for read-only, got %+v", planPol)
	}
}
