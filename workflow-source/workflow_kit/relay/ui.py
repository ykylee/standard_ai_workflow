"""중계 로컬 화면 (스펙 §10, 요구 R22.1 · M-053 WBS-53.2) — ``127.0.0.1`` 만, 표준 라이브러리 ``http.server``.

보여 주는 것: 등록 정보 · 일시정지 · 하네스 · 띄운 세션(요청 · 별칭 · 하네스 · pid · 상태 · 세션 ID · 로컬 종료) ·
허용 목록(이 PC 로컬 경로 · 현재/최대 세션) · 중앙 허브 딥링크 · 최근 로그 (`fetch('/api/state')` 무깜빡임 부분 갱신).
승인 대기는 보이지 않는다 — 승인은 owner 권한이라 중앙 허브 화면에서 한다 (중계는 owner 토큰을 갖지 않는다).
토큰은 어떤 응답에도 싣지 않는다. 쓰기(POST)는 출처 대조 + ``X-Relay-UI`` 머리 — 다른 사이트의 폼이 누르지 못하게.
프레임은 ``frame-ancestors 'self' vscode-webview: vscode-file://vscode-app`` — VS Code 확장 껍데기(``editors/vscode/``)만 띄울 수 있다.
frame-ancestors 는 조상 **전부**를 대조한다 — webview(``vscode-webview:``) 위의 VS Code 데스크톱 작업대(``vscode-file://vscode-app``)가
빠지면 실제 VS Code 에서 ``ERR_BLOCKED_BY_RESPONSE`` 로 빈 화면이 된다 (TASK-2026-11-22-main-016 실측).
"""

from __future__ import annotations

import html
import json
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import TYPE_CHECKING, Any

from workflow_kit.relay import adapters, config

if TYPE_CHECKING:
    from workflow_kit.relay.runner import Relay

HOST = "127.0.0.1"


def _hub_deep_links(hub: Any, pid: Any) -> tuple[str, str]:
    base = str(hub or "").strip().rstrip("/")
    proj = str(pid or "").strip()
    if not base or not proj or not (base.startswith("http://") or base.startswith("https://")):
        return "", ""
    enc = urllib.parse.quote(proj, safe="")
    proj_url = f"{base}/ui/#/p/{enc}"
    return proj_url, f"{proj_url}/orch"


def state(relay: Relay) -> dict[str, Any]:
    cfg = config.read_json("relay.json", {})
    sessions = {rid: sid for sid, rid in relay.session_of.items()}
    live = []
    by_alias: dict[str, int] = {}
    for rid, h in relay.handles.items():
        st = adapters.get(h.harness).status(h)
        alias = relay.alias_of.get(rid)
        if st != "ended" and alias:
            by_alias[alias] = by_alias.get(alias, 0) + 1
        live.append({"request": rid, "alias": alias, "harness": h.harness, "pid": h.proc.pid,
                     "status": st, "session": sessions.get(rid),
                     "harness_session_id": h.harness_session_id or None})
    return {
        "hub": cfg.get("hub"), "host_id": cfg.get("host_id"), "project_id": cfg.get("project_id"), "name": cfg.get("name"),
        "harnesses": cfg.get("harnesses") or [],
        "paused": bool(config.read_json("relay-state.json", {}).get("paused")),
        "sessions": live, "max_sessions": config.MAX_SESSIONS,
        "allow": [{"alias": e.get("alias"), "path": e.get("path"), "harnesses": e.get("harnesses"),
                   "permission_modes": e.get("permission_modes"), "max_sessions": e.get("max_sessions"),
                   "active_sessions": by_alias.get(str(e.get("alias") or ""), 0)} for e in config.load_allow()],
        "last_poll": {k: len(relay.last.get(k, [])) for k in ("dispatch", "deliver")} | {"halted": relay.last.get("halted", [])},
        "log": list(relay.recent)[-30:],
    }


def _row_html(x: dict[str, Any]) -> str:
    e = html.escape
    req = e(str(x["request"]))
    stop_btn = "" if x["status"] == "ended" else f'<button type="button" class="ghost stop-btn" data-req="{req}">종료</button>'
    return (
        f"<tr><td>{req}</td><td>{e(str(x['alias']))}</td><td>{e(x['harness'])}</td><td>{x['pid']}</td>"
        f'<td><span class="chip">{e(x["status"])}</span></td><td>{e(str(x["session"] or "—"))}</td>'
        f"<td>{stop_btn}</td></tr>"
    )


def _page(s: dict[str, Any]) -> str:
    e = html.escape
    rows = "".join(_row_html(x) for x in s["sessions"]) or "<tr><td colspan=7>띄운 세션 없음</td></tr>"
    allow = "".join(
        f"<li><code>{e(str(a['alias']))}</code> <span class=\"mono mute\">{e(str(a.get('path') or ''))}</span> — "
        f"{e(', '.join(a['harnesses'] or []))} · {e(', '.join(a['permission_modes'] or []))} · "
        f"{a.get('active_sessions', 0)}/{a['max_sessions']}</li>"
        for a in s["allow"]
    ) or "<li>없음</li>"
    log = e("\n".join(s["log"])) or "—"
    action = "resume" if s["paused"] else "pause"
    harnesses = ", ".join(s.get("harnesses") or []) or "—"
    proj_url, orch_url = _hub_deep_links(s.get("hub"), s.get("project_id"))
    hub_links = (
        f'<a class="link-btn" href="{e(orch_url)}" target="_blank" rel="noopener">중앙 허브 오케스트레이션</a> '
        f'<a class="link-btn" href="{e(proj_url)}" target="_blank" rel="noopener">프로젝트 화면</a>'
        if orch_url else ""
    )
    return f"""<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>PC 중계</title>
<style>
:root{{--bg:#f4f6fa;--card:#fff;--fg:#161a23;--mute:#677085;--line:#e2e6ef;--accent:#4f5bd5;--soft:#eef0f5;--bad:#c2283c;--bad-soft:#fde6e9}}
@media (prefers-color-scheme:dark){{:root{{--bg:#0f1218;--card:#171b24;--fg:#e7eaf2;--mute:#9aa3b8;--line:#2a3140;--accent:#8b95ff;--soft:#232936;--bad:#ff7a8c;--bad-soft:#3d1a21}}}}
*{{box-sizing:border-box}}
body{{margin:0;padding:16px;background:var(--bg);color:var(--fg);font:14px/1.5 system-ui,sans-serif;max-width:980px;overflow-wrap:anywhere}}
.card{{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px 16px;margin-bottom:12px}}
.row{{display:flex;gap:8px;flex-wrap:wrap;align-items:center}}
table{{border-collapse:collapse;width:100%}}td,th{{border-bottom:1px solid var(--line);padding:6px;text-align:left}}
.mute{{color:var(--mute)}}.mono{{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-size:.85em}}
.chip{{display:inline-block;padding:1px 8px;border-radius:999px;background:var(--soft);font-size:.85em}}
pre{{white-space:pre-wrap;background:var(--soft);padding:10px;border-radius:8px;max-height:260px;overflow:auto;margin:0}}
button,.link-btn{{background:var(--accent);color:#fff;border:0;padding:6px 12px;border-radius:8px;cursor:pointer;text-decoration:none;font:inherit;display:inline-block}}
button.ghost{{background:var(--bad-soft);color:var(--bad)}}
.link-btn{{background:var(--soft);color:var(--fg)}}
</style></head><body>
<div class="card">
<h1>PC 중계 — <span id="r-name">{e(str(s['name']))}</span></h1>
<p class="mute" id="r-meta">host {e(str(s['host_id']))} · 프로젝트 {e(str(s['project_id']))} · 허브 {e(str(s['hub']))} · 하네스 {e(harnesses)}</p>
<div class="row">상태: <b id="r-status">{'일시정지' if s['paused'] else '돌고 있음'}</b>
<button type="button" id="toggle-btn" data-action="{action}">{'재개' if s['paused'] else '일시정지'}</button>
{hub_links}</div>
<div id="r-msg" class="mute"></div>
</div>
<div class="card">
<h2 id="sess-title">띄운 세션 ({len(s['sessions'])} / {s['max_sessions']})</h2>
<table><thead><tr><th>요청</th><th>별칭</th><th>하네스</th><th>pid</th><th>상태</th><th>허브 세션</th><th>동작</th></tr></thead>
<tbody id="sess-body">{rows}</tbody></table>
</div>
<div class="card">
<h2>허용 목록 (이 PC 경로)</h2><ul id="allow-list">{allow}</ul>
<p class="mute" id="poll-line">승인은 중앙 허브 화면에서 owner 가 한다 · 마지막 폴링: 내줌 {s['last_poll']['dispatch']} · 전달 {s['last_poll']['deliver']}</p>
</div>
<div class="card"><h2>로그</h2><pre id="log-box">{log}</pre></div>
<script>
(function () {{
  const headers = {{ "X-Relay-UI": "1" }};
  const toggleBtn = document.getElementById("toggle-btn");
  const msgEl = document.getElementById("r-msg");
  function mk(tag, text, cls) {{
    const el = document.createElement(tag);
    if (cls) el.className = cls;
    if (text !== undefined && text !== null) el.textContent = String(text);
    return el;
  }}
  function renderState(s) {{
    document.getElementById("r-status").textContent = s.paused ? "일시정지" : "돌고 있음";
    toggleBtn.dataset.action = s.paused ? "resume" : "pause";
    toggleBtn.textContent = s.paused ? "재개" : "일시정지";
    document.getElementById("sess-title").textContent = "띄운 세션 (" + s.sessions.length + " / " + s.max_sessions + ")";
    const tb = document.getElementById("sess-body");
    tb.replaceChildren();
    if (!s.sessions.length) {{
      const td = mk("td", "띄운 세션 없음"); td.colSpan = 7;
      const tr = mk("tr"); tr.appendChild(td); tb.appendChild(tr);
    }} else {{
      for (const x of s.sessions) {{
        const tr = mk("tr");
        tr.append(mk("td", x.request), mk("td", x.alias), mk("td", x.harness), mk("td", x.pid));
        const stTd = mk("td"); stTd.appendChild(mk("span", x.status, "chip")); tr.appendChild(stTd);
        tr.append(mk("td", x.session || "—"));
        const actTd = mk("td");
        if (x.status !== "ended") {{
          const b = mk("button", "종료", "ghost stop-btn");
          b.type = "button"; b.dataset.req = x.request;
          actTd.appendChild(b);
        }}
        tr.appendChild(actTd);
        tb.appendChild(tr);
      }}
    }}
    const ul = document.getElementById("allow-list");
    ul.replaceChildren();
    if (!s.allow.length) {{ ul.appendChild(mk("li", "없음")); }}
    else {{
      for (const a of s.allow) {{
        const li = mk("li");
        li.append(mk("code", a.alias), " ", mk("span", a.path || "", "mono mute"),
          " — " + (a.harnesses || []).join(", ") + " · " + (a.permission_modes || []).join(", ") +
          " · " + (a.active_sessions || 0) + "/" + a.max_sessions);
        ul.appendChild(li);
      }}
    }}
    const lp = s.last_poll || {{}};
    document.getElementById("poll-line").textContent =
      "승인은 중앙 허브 화면에서 owner 가 한다 · 마지막 폴링: 내줌 " + (lp.dispatch || 0) + " · 전달 " + (lp.deliver || 0);
    const logEl = document.getElementById("log-box");
    const nextLog = (s.log || []).join("\\n") || "—";
    const sel = window.getSelection ? String(window.getSelection()) : "";
    if (!sel && logEl.textContent !== nextLog) {{
      const atBottom = logEl.scrollTop + logEl.clientHeight >= logEl.scrollHeight - 8;
      logEl.textContent = nextLog;
      if (atBottom) logEl.scrollTop = logEl.scrollHeight;
    }}
  }}
  async function refresh() {{
    try {{
      const r = await fetch("/api/state", {{ cache: "no-store" }});
      if (r.ok) renderState(await r.json());
    }} catch (e) {{}}
  }}
  toggleBtn.addEventListener("click", async () => {{
    const r = await fetch("/api/" + toggleBtn.dataset.action, {{ method: "POST", headers }});
    if (r.ok) await refresh();
  }});
  document.getElementById("sess-body").addEventListener("click", async (ev) => {{
    const btn = ev.target && ev.target.closest ? ev.target.closest(".stop-btn") : null;
    if (!btn) return;
    const reqId = btn.dataset.req;
    if (!confirm(reqId + " 세션을 이 PC 에서 강제 종료할까?")) return;
    const r = await fetch("/api/sessions/" + encodeURIComponent(reqId) + "/stop", {{ method: "POST", headers }});
    msgEl.textContent = r.ok ? (reqId + " 세션을 로컬에서 종료했다.") : ("종료 실패 (" + r.status + ")");
    await refresh();
  }});
  setInterval(refresh, 3000);
}})();
</script></body></html>"""


def serve(relay: Relay, port: int) -> ThreadingHTTPServer:
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_a: Any) -> None:  # 표준 오류를 시끄럽게 하지 않는다
            return

        def _send(self, code: int, body: str, ctype: str) -> None:
            raw = body.encode("utf-8")
            self.send_response(code)
            self.send_header("content-type", ctype)
            self.send_header("content-length", str(len(raw)))
            # 프레임은 이 화면 자신과 VS Code 데스크톱 webview 만 (M-047 — 확장 껍데기가 iframe 으로 띄운다). 다른 사이트가 이 화면을
            # 프레임에 넣어 일시정지 버튼을 누르게 하는 클릭재킹은 계속 막는다 (POST 는 X-Relay-UI + 같은 출처도 요구).
            self.send_header("content-security-policy", "frame-ancestors 'self' vscode-webview: vscode-file://vscode-app")
            self.send_header("cache-control", "no-store")
            self.end_headers()
            self.wfile.write(raw)

        def do_GET(self) -> None:
            if self.path == "/api/state":
                self._send(200, json.dumps(state(relay), ensure_ascii=False), "application/json")
            elif self.path in ("/", "/index.html"):
                self._send(200, _page(state(relay)), "text/html; charset=utf-8")
            else:
                self._send(404, "{}", "application/json")

        def do_POST(self) -> None:
            origin = self.headers.get("origin")
            same = origin is None or origin in (f"http://{HOST}:{port}", f"http://localhost:{port}")
            if self.headers.get("x-relay-ui") != "1" or not same:
                self._send(403, json.dumps({"error_code": "forbidden", "message": "중계 화면에서만"}), "application/json")
                return
            length = int(self.headers.get("content-length") or 0)
            raw = self.rfile.read(length) if length > 0 else b""
            if self.path == "/api/poll":
                from workflow_kit.relay.conn import HubError

                try:
                    req_body = json.loads(raw.decode("utf-8")) if raw.strip() else {}
                except ValueError:
                    req_body = {}
                wait_s = int(req_body.get("wait_s", 0)) if isinstance(req_body, dict) else 0
                try:
                    got = relay.once(wait_s=wait_s)
                    self._send(200, json.dumps(got, ensure_ascii=False), "application/json")
                except HubError as e:
                    self._send(e.status, json.dumps(e.payload, ensure_ascii=False), "application/json")
                return
            if self.path == "/api/deliver":
                try:
                    req_body = json.loads(raw.decode("utf-8")) if raw.strip() else None
                except ValueError:
                    req_body = None
                if not isinstance(req_body, dict):
                    self._send(400, json.dumps({"error_code": "invalid_json", "message": "JSON 객체가 필요하다"}),
                               "application/json")
                    return
                relay._deliver(req_body)
                self._send(200, json.dumps({"status": "ok"}), "application/json")
                return
            if self.path.startswith("/api/sessions/") and self.path.endswith("/stop"):
                req_id = urllib.parse.unquote(self.path[len("/api/sessions/") : -len("/stop")]).strip()
                h = relay.handles.get(req_id) if req_id and "/" not in req_id else None
                if h is None or not h.alive():
                    self._send(404, json.dumps({"error_code": "not_found", "message": "실행 중인 세션이 없다"}),
                               "application/json")
                    return
                adapters.get(h.harness).stop(h)
                relay.log(f"로컬 종료 {req_id}")
                self._send(200, json.dumps({"stopped": req_id, "state": state(relay)}, ensure_ascii=False),
                           "application/json")
                return
            if self.path not in ("/api/pause", "/api/resume"):
                self._send(404, "{}", "application/json")
                return
            st = config.read_json("relay-state.json", {})
            st["paused"] = self.path == "/api/pause"
            config.write_json("relay-state.json", st)
            relay.log(f"화면에서 {'일시정지' if st['paused'] else '재개'}")
            self._send(200, json.dumps({"paused": st["paused"]}), "application/json")

    server = ThreadingHTTPServer((HOST, port), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server
