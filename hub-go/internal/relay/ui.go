package relay

import (
	"encoding/json"
	"errors"
	"fmt"
	"html"
	"io"
	"net"
	"net/http"
	"sort"
	"strings"
)

const uiHost = "127.0.0.1"
const relayCSP = "frame-ancestors 'self' vscode-webview: vscode-file://vscode-app"

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
			"harnesses":        e.Harnesses,
			"permission_modes": e.PermissionModes,
			"max_sessions":     e.MaxSessions,
		})
	}
	paused, _ := st["paused"].(bool)

	return map[string]any{
		"hub":          cfg["hub"],
		"host_id":      cfg["host_id"],
		"project_id":   cfg["project_id"],
		"name":         cfg["name"],
		"paused":       paused,
		"sessions":     live,
		"max_sessions": MaxSessions,
		"allow":        allowOut,
		"last_poll": map[string]any{
			"dispatch": dispatchLen,
			"deliver":  deliverLen,
			"halted":   halted,
		},
		"log": logSlice,
	}
}

func joinAnyStrings(v any) string {
	switch arr := v.(type) {
	case []string:
		return strings.Join(arr, ", ")
	case []any:
		parts := make([]string, 0, len(arr))
		for _, item := range arr {
			parts = append(parts, fmt.Sprint(item))
		}
		return strings.Join(parts, ", ")
	default:
		return ""
	}
}

func renderPage(s map[string]any) string {
	e := html.EscapeString
	sessions, _ := s["sessions"].([]map[string]any)
	var rows strings.Builder
	if len(sessions) == 0 {
		rows.WriteString("<tr><td colspan=6>띄운 세션 없음</td></tr>")
	} else {
		for _, x := range sessions {
			alias := fmt.Sprint(x["alias"])
			if x["alias"] == nil {
				alias = "None"
			}
			sess := "—"
			if x["session"] != nil && fmt.Sprint(x["session"]) != "" {
				sess = fmt.Sprint(x["session"])
			}
			fmt.Fprintf(
				&rows,
				"<tr><td>%s</td><td>%s</td><td>%s</td><td>%v</td><td>%s</td><td>%s</td></tr>",
				e(fmt.Sprint(x["request"])),
				e(alias),
				e(fmt.Sprint(x["harness"])),
				x["pid"],
				e(fmt.Sprint(x["status"])),
				e(sess),
			)
		}
	}

	allowItems, _ := s["allow"].([]map[string]any)
	var allow strings.Builder
	if len(allowItems) == 0 {
		allow.WriteString("<li>없음</li>")
	} else {
		for _, a := range allowItems {
			fmt.Fprintf(
				&allow,
				"<li><code>%s</code> — %s · %s · 최대 %v</li>",
				e(fmt.Sprint(a["alias"])),
				e(joinAnyStrings(a["harnesses"])),
				e(joinAnyStrings(a["permission_modes"])),
				a["max_sessions"],
			)
		}
	}

	logs, _ := s["log"].([]string)
	logStr := "—"
	if len(logs) > 0 {
		logStr = e(strings.Join(logs, "\n"))
	}

	paused, _ := s["paused"].(bool)
	action := "pause"
	statusLabel := "돌고 있음"
	btnLabel := "일시정지"
	if paused {
		action = "resume"
		statusLabel = "일시정지"
		btnLabel = "재개"
	}
	lp, _ := s["last_poll"].(map[string]any)

	return fmt.Sprintf(`<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>PC 중계</title><meta http-equiv="refresh" content="5">
<style>
:root{--bg:#fff;--fg:#1d1d1f;--mute:#6e6e73;--line:#e5e5ea;--accent:#0a66c2}
@media (prefers-color-scheme:dark){:root{--bg:#111;--fg:#eee;--mute:#999;--line:#333;--accent:#5aa9ff}}
body{margin:0;padding:16px;background:var(--bg);color:var(--fg);font:14px/1.5 system-ui,sans-serif;max-width:960px}
table{border-collapse:collapse;width:100%%}td,th{border-bottom:1px solid var(--line);padding:6px;text-align:left}
.mute{color:var(--mute)}pre{white-space:pre-wrap;background:var(--line);padding:8px;max-height:240px;overflow:auto}
button{background:var(--accent);color:#fff;border:0;padding:6px 14px;border-radius:6px;cursor:pointer}
</style></head><body>
<h1>PC 중계 — %s</h1>
<p class="mute">host %s · 프로젝트 %s · 허브 %s</p>
<p>상태: <b>%s</b>
<button onclick="fetch('/api/%s',{method:'POST',headers:{'X-Relay-UI':'1'}}).then(()=>location.reload())">%s</button></p>
<h2>띄운 세션 (%d / %v)</h2>
<table><tr><th>요청</th><th>별칭</th><th>하네스</th><th>pid</th><th>상태</th><th>허브 세션</th></tr>%s</table>
<h2>허용 목록</h2><ul>%s</ul>
<p class="mute">승인은 중앙 허브 화면에서 owner 가 한다 · 마지막 폴링: 내줌 %v · 전달 %v</p>
<h2>로그</h2><pre>%s</pre></body></html>`,
		e(fmt.Sprint(s["name"])),
		e(fmt.Sprint(s["host_id"])),
		e(fmt.Sprint(s["project_id"])),
		e(fmt.Sprint(s["hub"])),
		statusLabel,
		action,
		btnLabel,
		len(sessions),
		s["max_sessions"],
		rows.String(),
		allow.String(),
		lp["dispatch"],
		lp["deliver"],
		logStr,
	)
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
			case "/", "/index.html":
				htmlDoc := renderPage(State(r))
				sendResponse(w, http.StatusOK, "text/html; charset=utf-8", []byte(htmlDoc))
			default:
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
						"message":    "JSON 객체가 필요하다",
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
