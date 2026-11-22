package relay

import (
	"encoding/json"
	"errors"
	"fmt"
	"html"
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
	base := strings.TrimRight(strings.TrimSpace(fmt.Sprint(hub)), "/")
	proj := strings.TrimSpace(fmt.Sprint(pid))
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

	return map[string]any{
		"hub":          cfg["hub"],
		"host_id":      cfg["host_id"],
		"project_id":   cfg["project_id"],
		"name":         cfg["name"],
		"harnesses":    harnesses,
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
		rows.WriteString("<tr><td colspan=7>띄운 세션 없음</td></tr>")
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
			st := fmt.Sprint(x["status"])
			req := fmt.Sprint(x["request"])
			stopBtn := ""
			if st != "ended" {
				stopBtn = fmt.Sprintf(`<button type="button" class="ghost stop-btn" data-req="%s">종료</button>`, e(req))
			}
			fmt.Fprintf(
				&rows,
				`<tr><td>%s</td><td>%s</td><td>%s</td><td>%v</td><td><span class="chip">%s</span></td><td>%s</td><td>%s</td></tr>`,
				e(req),
				e(alias),
				e(fmt.Sprint(x["harness"])),
				x["pid"],
				e(st),
				e(sess),
				stopBtn,
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
				`<li><code>%s</code> <span class="mono mute">%s</span> — %s · %s · %v/%v</li>`,
				e(fmt.Sprint(a["alias"])),
				e(fmt.Sprint(a["path"])),
				e(joinAnyStrings(a["harnesses"])),
				e(joinAnyStrings(a["permission_modes"])),
				a["active_sessions"],
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
	harnesses := joinAnyStrings(s["harnesses"])
	if harnesses == "" {
		harnesses = "—"
	}
	projURL, orchURL := hubDeepLinks(s["hub"], s["project_id"])
	hubLinks := ""
	if orchURL != "" {
		hubLinks = fmt.Sprintf(
			`<a class="link-btn" href="%s" target="_blank" rel="noopener">중앙 허브 오케스트레이션</a> <a class="link-btn" href="%s" target="_blank" rel="noopener">프로젝트 화면</a>`,
			e(orchURL),
			e(projURL),
		)
	}

	return fmt.Sprintf(`<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>PC 중계</title>
<style>
:root{--bg:#f4f6fa;--card:#fff;--fg:#161a23;--mute:#677085;--line:#e2e6ef;--accent:#4f5bd5;--soft:#eef0f5;--bad:#c2283c;--bad-soft:#fde6e9}
@media (prefers-color-scheme:dark){:root{--bg:#0f1218;--card:#171b24;--fg:#e7eaf2;--mute:#9aa3b8;--line:#2a3140;--accent:#8b95ff;--soft:#232936;--bad:#ff7a8c;--bad-soft:#3d1a21}}
*{box-sizing:border-box}
body{margin:0;padding:16px;background:var(--bg);color:var(--fg);font:14px/1.5 system-ui,sans-serif;max-width:980px;overflow-wrap:anywhere}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px 16px;margin-bottom:12px}
.row{display:flex;gap:8px;flex-wrap:wrap;align-items:center}
table{border-collapse:collapse;width:100%%}td,th{border-bottom:1px solid var(--line);padding:6px;text-align:left}
.mute{color:var(--mute)}.mono{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-size:.85em}
.chip{display:inline-block;padding:1px 8px;border-radius:999px;background:var(--soft);font-size:.85em}
pre{white-space:pre-wrap;background:var(--soft);padding:10px;border-radius:8px;max-height:260px;overflow:auto;margin:0}
button,.link-btn{background:var(--accent);color:#fff;border:0;padding:6px 12px;border-radius:8px;cursor:pointer;text-decoration:none;font:inherit;display:inline-block}
button.ghost{background:var(--bad-soft);color:var(--bad)}
.link-btn{background:var(--soft);color:var(--fg)}
</style></head><body>
<div class="card">
<h1>PC 중계 — <span id="r-name">%s</span></h1>
<p class="mute" id="r-meta">host %s · 프로젝트 %s · 허브 %s · 하네스 %s</p>
<div class="row">상태: <b id="r-status">%s</b>
<button type="button" id="toggle-btn" data-action="%s">%s</button>
%s</div>
<div id="r-msg" class="mute"></div>
</div>
<div class="card">
<h2 id="sess-title">띄운 세션 (%d / %v)</h2>
<table><thead><tr><th>요청</th><th>별칭</th><th>하네스</th><th>pid</th><th>상태</th><th>허브 세션</th><th>동작</th></tr></thead>
<tbody id="sess-body">%s</tbody></table>
</div>
<div class="card">
<h2>허용 목록 (이 PC 경로)</h2><ul id="allow-list">%s</ul>
<p class="mute" id="poll-line">승인은 중앙 허브 화면에서 owner 가 한다 · 마지막 폴링: 내줌 %v · 전달 %v</p>
</div>
<div class="card"><h2>로그</h2><pre id="log-box">%s</pre></div>
<script>
(function () {
  const headers = { "X-Relay-UI": "1" };
  const toggleBtn = document.getElementById("toggle-btn");
  const msgEl = document.getElementById("r-msg");
  function mk(tag, text, cls) {
    const el = document.createElement(tag);
    if (cls) el.className = cls;
    if (text !== undefined && text !== null) el.textContent = String(text);
    return el;
  }
  function renderState(s) {
    document.getElementById("r-status").textContent = s.paused ? "일시정지" : "돌고 있음";
    toggleBtn.dataset.action = s.paused ? "resume" : "pause";
    toggleBtn.textContent = s.paused ? "재개" : "일시정지";
    document.getElementById("sess-title").textContent = "띄운 세션 (" + s.sessions.length + " / " + s.max_sessions + ")";
    const tb = document.getElementById("sess-body");
    tb.replaceChildren();
    if (!s.sessions.length) {
      const td = mk("td", "띄운 세션 없음"); td.colSpan = 7;
      const tr = mk("tr"); tr.appendChild(td); tb.appendChild(tr);
    } else {
      for (const x of s.sessions) {
        const tr = mk("tr");
        tr.append(mk("td", x.request), mk("td", x.alias), mk("td", x.harness), mk("td", x.pid));
        const stTd = mk("td"); stTd.appendChild(mk("span", x.status, "chip")); tr.appendChild(stTd);
        tr.append(mk("td", x.session || "—"));
        const actTd = mk("td");
        if (x.status !== "ended") {
          const b = mk("button", "종료", "ghost stop-btn");
          b.type = "button"; b.dataset.req = x.request;
          actTd.appendChild(b);
        }
        tr.appendChild(actTd);
        tb.appendChild(tr);
      }
    }
    const ul = document.getElementById("allow-list");
    ul.replaceChildren();
    if (!s.allow.length) { ul.appendChild(mk("li", "없음")); }
    else {
      for (const a of s.allow) {
        const li = mk("li");
        li.append(mk("code", a.alias), " ", mk("span", a.path || "", "mono mute"),
          " — " + (a.harnesses || []).join(", ") + " · " + (a.permission_modes || []).join(", ") +
          " · " + (a.active_sessions || 0) + "/" + a.max_sessions);
        ul.appendChild(li);
      }
    }
    const lp = s.last_poll || {};
    document.getElementById("poll-line").textContent =
      "승인은 중앙 허브 화면에서 owner 가 한다 · 마지막 폴링: 내줌 " + (lp.dispatch || 0) + " · 전달 " + (lp.deliver || 0);
    const logEl = document.getElementById("log-box");
    const nextLog = (s.log || []).join("\n") || "—";
    const sel = window.getSelection ? String(window.getSelection()) : "";
    if (!sel && logEl.textContent !== nextLog) {
      const atBottom = logEl.scrollTop + logEl.clientHeight >= logEl.scrollHeight - 8;
      logEl.textContent = nextLog;
      if (atBottom) logEl.scrollTop = logEl.scrollHeight;
    }
  }
  async function refresh() {
    try {
      const r = await fetch("/api/state", { cache: "no-store" });
      if (r.ok) renderState(await r.json());
    } catch (e) {}
  }
  toggleBtn.addEventListener("click", async () => {
    const r = await fetch("/api/" + toggleBtn.dataset.action, { method: "POST", headers });
    if (r.ok) await refresh();
  });
  document.getElementById("sess-body").addEventListener("click", async (ev) => {
    const btn = ev.target && ev.target.closest ? ev.target.closest(".stop-btn") : null;
    if (!btn) return;
    const reqId = btn.dataset.req;
    if (!confirm(reqId + " 세션을 이 PC 에서 강제 종료할까?")) return;
    const r = await fetch("/api/sessions/" + encodeURIComponent(reqId) + "/stop", { method: "POST", headers });
    msgEl.textContent = r.ok ? (reqId + " 세션을 로컬에서 종료했다.") : ("종료 실패 (" + r.status + ")");
    await refresh();
  });
  setInterval(refresh, 3000);
})();
</script></body></html>`,
		e(fmt.Sprint(s["name"])),
		e(fmt.Sprint(s["host_id"])),
		e(fmt.Sprint(s["project_id"])),
		e(fmt.Sprint(s["hub"])),
		e(harnesses),
		statusLabel,
		action,
		btnLabel,
		hubLinks,
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
			if strings.HasPrefix(req.URL.Path, "/api/sessions/") && strings.HasSuffix(req.URL.Path, "/stop") {
				reqID := strings.TrimSpace(strings.TrimSuffix(strings.TrimPrefix(req.URL.Path, "/api/sessions/"), "/stop"))
				var h *Handle
				if reqID != "" && !strings.Contains(reqID, "/") {
					r.Mu.Lock()
					h = r.Handles[reqID]
					r.Mu.Unlock()
				}
				if h == nil || !h.Alive() {
					sendJSON(w, http.StatusNotFound, map[string]any{
						"error_code": "not_found",
						"message":    "실행 중인 세션이 없다",
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
