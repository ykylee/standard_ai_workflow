package relay

import (
	"embed"
	"encoding/json"
	"errors"
	"fmt"
	"github.com/ykylee/standard_ai_workflow/hub-go/internal/pytext"
	"io"
	"net"
	"net/http"
	"net/url"
	"sort"
	"strings"
)

const uiHost = "127.0.0.1"
const relayCSP = "frame-ancestors 'self' vscode-webview: vscode-file://vscode-app"

func hubDeepLinks(hub any, pid any) (string, string) {
	base := strings.TrimRight(pytext.Strip(fmt.Sprint(hub)), "/")
	proj := pytext.Strip(fmt.Sprint(pid))
	if hub == nil || pid == nil || base == "" || proj == "" {
		return "", ""
	}
	if !strings.HasPrefix(base, "http://") && !strings.HasPrefix(base, "https://") {
		return "", ""
	}
	projURL := base + "/ui/#/p/" + url.PathEscape(proj)
	return projURL, projURL + "/orch"
}

func State(r *Relay) map[string]any {
	cfg, _ := ReadJSON("relay.json")
	st, _ := ReadJSON("relay-state.json")
	entries, _ := LoadAllow()

	r.Mu.Lock()
	sessionsMap := make(map[string]string, len(r.SessionOf))
	for sid, rid := range r.SessionOf {
		sessionsMap[rid] = sid
	}
	reqIDs := make([]string, 0, len(r.Handles))
	for rid := range r.Handles {
		reqIDs = append(reqIDs, rid)
	}
	sort.Strings(reqIDs)

	live := make([]map[string]any, 0, len(reqIDs))
	byAlias := map[string]int{}
	for _, rid := range reqIDs {
		h := r.Handles[rid]
		ad, _ := GetAdapter(h.Harness)
		status := "unknown"
		if ad != nil {
			status = ad.Status(h)
		}
		var sidVal any
		if sid, ok := sessionsMap[rid]; ok && sid != "" {
			sidVal = sid
		}
		h.Mu.Lock()
		hsid := h.HarnessSessionID
		h.Mu.Unlock()
		var hsidVal any
		if hsid != "" {
			hsidVal = hsid
		}
		var aliasVal any
		if a, ok := r.AliasOf[rid]; ok && a != "" {
			aliasVal = a
			if status != "ended" {
				byAlias[a]++
			}
		}
		live = append(live, map[string]any{
			"request":            rid,
			"alias":              aliasVal,
			"harness":            h.Harness,
			"pid":                h.PID(),
			"status":             status,
			"session":            sidVal,
			"harness_session_id": hsidVal,
		})
	}

	dispatchLen := 0
	if d, ok := r.Last["dispatch"].([]any); ok {
		dispatchLen = len(d)
	}
	deliverLen := 0
	if d, ok := r.Last["deliver"].([]any); ok {
		deliverLen = len(d)
	}
	halted := []any{}
	if h, ok := r.Last["halted"].([]any); ok && h != nil {
		halted = h
	}
	logSlice := make([]string, 0)
	if len(r.Recent) > 30 {
		logSlice = append(logSlice, r.Recent[len(r.Recent)-30:]...)
	} else {
		logSlice = append(logSlice, r.Recent...)
	}
	r.Mu.Unlock()

	allowOut := make([]map[string]any, 0, len(entries))
	for _, e := range entries {
		allowOut = append(allowOut, map[string]any{
			"alias":            e.Alias,
			"path":             e.Path,
			"harnesses":        e.Harnesses,
			"permission_modes": e.PermissionModes,
			"max_sessions":     e.MaxSessions,
			"active_sessions":  byAlias[e.Alias],
		})
	}
	paused, _ := st["paused"].(bool)
	harnesses := cfg["harnesses"]
	if harnesses == nil {
		harnesses = []any{}
	}
	active := 0
	for _, x := range live {
		if x["status"] != "ended" {
			active++
		}
	}
	var hubLinks any
	if projURL, orchURL := hubDeepLinks(cfg["hub"], cfg["project_id"]); orchURL != "" {
		hubLinks = map[string]any{"project": projURL, "orch": orchURL}
	}

	return map[string]any{
		"hub":             cfg["hub"],
		"host_id":         cfg["host_id"],
		"project_id":      cfg["project_id"],
		"name":            cfg["name"],
		"harnesses":       harnesses,
		"paused":          paused,
		"sessions":        live,
		"max_sessions":    MaxSessions,
		"active_sessions": active,
		"hub_links":       hubLinks,
		"allow":           allowOut,
		"last_poll": map[string]any{
			"dispatch": dispatchLen,
			"deliver":  deliverLen,
			"halted":   halted,
		},
		"log": logSlice,
	}
}

// 화면은 정적 파일 세 개(relay.html · relay.css · relay.js)가 정본이다 — Python 중계
// (workflow-source/workflow_kit/relay/static/)와 같은 바이트(check_go_assets_sync). 서버는 상태를 /api/state 로만 낸다.
//
//go:embed static/relay.html static/relay.css static/relay.js
var staticFS embed.FS

var staticFiles = map[string][2]string{
	"/":           {"static/relay.html", "text/html; charset=utf-8"},
	"/index.html": {"static/relay.html", "text/html; charset=utf-8"},
	"/relay.css":  {"static/relay.css", "text/css; charset=utf-8"},
	"/relay.js":   {"static/relay.js", "text/javascript; charset=utf-8"},
}

func sendResponse(w http.ResponseWriter, code int, ctype string, body []byte) {
	w.Header().Set("Content-Type", ctype)
	w.Header().Set("Content-Length", fmt.Sprint(len(body)))
	w.Header().Set("Content-Security-Policy", relayCSP)
	w.Header().Set("Cache-Control", "no-store")
	w.WriteHeader(code)
	_, _ = w.Write(body)
}

func sendJSON(w http.ResponseWriter, code int, v any) {
	raw, err := compactJSON(v)
	if err != nil {
		raw = []byte("{}")
	}
	sendResponse(w, code, "application/json", raw)
}

func validUIOrigin(req *http.Request, port int) bool {
	if req.Header.Get("X-Relay-UI") != "1" {
		return false
	}
	origin := req.Header.Get("Origin")
	if origin == "" {
		return true
	}
	return origin == fmt.Sprintf("http://%s:%d", uiHost, port) ||
		origin == fmt.Sprintf("http://localhost:%d", port)
}

func StartUI(r *Relay, port int) (*http.Server, int, error) {
	ln, err := net.Listen("tcp", fmt.Sprintf("%s:%d", uiHost, port))
	if err != nil {
		return nil, 0, err
	}
	actualPort := ln.Addr().(*net.TCPAddr).Port

	mux := http.NewServeMux()
	mux.HandleFunc("/", func(w http.ResponseWriter, req *http.Request) {
		switch req.Method {
		case http.MethodGet:
			switch req.URL.Path {
			case "/api/state":
				sendJSON(w, http.StatusOK, State(r))
			default:
				if f, ok := staticFiles[req.URL.Path]; ok {
					raw, err := staticFS.ReadFile(f[0])
					if err == nil {
						sendResponse(w, http.StatusOK, f[1], raw)
						return
					}
				}
				sendResponse(w, http.StatusNotFound, "application/json", []byte("{}"))
			}
		case http.MethodPost:
			if !validUIOrigin(req, actualPort) {
				sendJSON(w, http.StatusForbidden, map[string]any{
					"error_code": "forbidden",
					"message":    "중계 화면에서만",
				})
				return
			}
			if strings.HasPrefix(req.URL.Path, "/api/sessions/") && strings.HasSuffix(req.URL.Path, "/stop") {
				reqID := pytext.Strip(strings.TrimSuffix(strings.TrimPrefix(req.URL.Path, "/api/sessions/"), "/stop"))
				var h *Handle
				if reqID != "" && !strings.Contains(reqID, "/") {
					r.Mu.Lock()
					h = r.Handles[reqID]
					r.Mu.Unlock()
				}
				if h == nil || !h.Alive() {
					sendJSON(w, http.StatusNotFound, map[string]any{
						"error_code": "not_found",
						"message":    "실행 중인 세션이 없어요",
					})
					return
				}
				if ad, err := GetAdapter(h.Harness); err == nil {
					_ = ad.Stop(h)
				}
				r.Log("로컬 종료 " + reqID)
				sendJSON(w, http.StatusOK, map[string]any{
					"stopped": reqID,
					"state":   State(r),
				})
				return
			}
			switch req.URL.Path {
			case "/api/pause", "/api/resume":
				st, err := ReadJSON("relay-state.json")
				if err != nil {
					sendJSON(w, http.StatusInternalServerError, map[string]any{
						"error_code": "io_error",
						"message":    err.Error(),
					})
					return
				}
				paused := req.URL.Path == "/api/pause"
				st["paused"] = paused
				if err := WriteJSON("relay-state.json", st); err != nil {
					sendJSON(w, http.StatusInternalServerError, map[string]any{
						"error_code": "io_error",
						"message":    err.Error(),
					})
					return
				}
				if paused {
					r.Log("화면에서 일시정지")
				} else {
					r.Log("화면에서 재개")
				}
				sendJSON(w, http.StatusOK, map[string]any{"paused": paused})
			case "/api/poll":
				var body struct {
					WaitS int `json:"wait_s"`
				}
				if req.Body != nil {
					raw, _ := io.ReadAll(io.LimitReader(req.Body, 1<<20))
					if len(raw) > 0 {
						_ = json.Unmarshal(raw, &body)
					}
				}
				got, err := r.Once(body.WaitS)
				if err != nil {
					var hubErr *HubError
					if errors.As(err, &hubErr) {
						sendJSON(w, hubErr.Status, hubErr.Payload)
						return
					}
					sendJSON(w, http.StatusBadGateway, map[string]any{
						"error_code": "hub_unreachable",
						"message":    err.Error(),
					})
					return
				}
				sendJSON(w, http.StatusOK, got)
			case "/api/deliver":
				var s map[string]any
				raw, _ := io.ReadAll(io.LimitReader(req.Body, 1<<20))
				if err := json.Unmarshal(raw, &s); err != nil || s == nil {
					sendJSON(w, http.StatusBadRequest, map[string]any{
						"error_code": "invalid_json",
						"message":    "JSON 객체가 필요해요",
					})
					return
				}
				r.DeliverSession(s)
				sendJSON(w, http.StatusOK, map[string]any{"status": "ok"})
			default:
				sendResponse(w, http.StatusNotFound, "application/json", []byte("{}"))
			}
		default:
			sendResponse(w, http.StatusMethodNotAllowed, "application/json", []byte("{}"))
		}
	})

	srv := &http.Server{Handler: mux}
	go func() {
		_ = srv.Serve(ln)
	}()
	return srv, actualPort, nil
}
