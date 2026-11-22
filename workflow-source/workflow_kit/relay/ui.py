"""중계 로컬 화면 (스펙 §10, 요구 R22.1) — ``127.0.0.1`` 만, 표준 라이브러리 ``http.server``.

보여 주는 것: 등록 정보 · 일시정지 · 띄운 세션(요청 · 하네스 · pid · 상태 · 세션 ID) · 허용 목록 별칭 · 최근 로그.
하는 것: 일시정지 · 재개뿐 — 승인은 owner 권한이라 중앙 허브 화면에서 한다 (중계는 owner 토큰을 갖지 않는다).
토큰은 어떤 응답에도 싣지 않는다. 쓰기(POST)는 출처 대조 + ``X-Relay-UI`` 머리 — 다른 사이트의 폼이 누르지 못하게.
프레임은 ``frame-ancestors 'self' vscode-webview:`` — VS Code 확장 껍데기(``editors/vscode/``)만 띄울 수 있다.
"""

from __future__ import annotations

import html
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import TYPE_CHECKING, Any

from workflow_kit.relay import adapters, config

if TYPE_CHECKING:
    from workflow_kit.relay.runner import Relay

HOST = "127.0.0.1"


def state(relay: Relay) -> dict[str, Any]:
    cfg = config.read_json("relay.json", {})
    sessions = {rid: sid for sid, rid in relay.session_of.items()}
    live = []
    for rid, h in relay.handles.items():
        live.append({"request": rid, "alias": relay.alias_of.get(rid), "harness": h.harness, "pid": h.proc.pid,
                     "status": adapters.get(h.harness).status(h), "session": sessions.get(rid),
                     "harness_session_id": h.harness_session_id or None})
    return {
        "hub": cfg.get("hub"), "host_id": cfg.get("host_id"), "project_id": cfg.get("project_id"), "name": cfg.get("name"),
        "paused": bool(config.read_json("relay-state.json", {}).get("paused")),
        "sessions": live, "max_sessions": config.MAX_SESSIONS,
        "allow": [{"alias": e.get("alias"), "harnesses": e.get("harnesses"), "permission_modes": e.get("permission_modes"),
                   "max_sessions": e.get("max_sessions")} for e in config.load_allow()],
        "last_poll": {k: len(relay.last.get(k, [])) for k in ("dispatch", "deliver")} | {"halted": relay.last.get("halted", [])},
        "log": list(relay.recent)[-30:],
    }


def _page(s: dict[str, Any]) -> str:
    e = html.escape
    rows = "".join(
        f"<tr><td>{e(str(x['request']))}</td><td>{e(str(x['alias']))}</td><td>{e(x['harness'])}</td><td>{x['pid']}</td>"
        f"<td>{e(x['status'])}</td><td>{e(str(x['session'] or '—'))}</td></tr>" for x in s["sessions"]) \
        or "<tr><td colspan=6>띄운 세션 없음</td></tr>"
    allow = "".join(f"<li><code>{e(str(a['alias']))}</code> — {e(', '.join(a['harnesses'] or []))} · "
                    f"{e(', '.join(a['permission_modes'] or []))} · 최대 {a['max_sessions']}</li>" for a in s["allow"]) or "<li>없음</li>"
    log = e("\n".join(s["log"])) or "—"
    action = "resume" if s["paused"] else "pause"
    return f"""<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>PC 중계</title><meta http-equiv="refresh" content="5">
<style>
:root{{--bg:#fff;--fg:#1d1d1f;--mute:#6e6e73;--line:#e5e5ea;--accent:#0a66c2}}
@media (prefers-color-scheme:dark){{:root{{--bg:#111;--fg:#eee;--mute:#999;--line:#333;--accent:#5aa9ff}}}}
body{{margin:0;padding:16px;background:var(--bg);color:var(--fg);font:14px/1.5 system-ui,sans-serif;max-width:960px}}
table{{border-collapse:collapse;width:100%}}td,th{{border-bottom:1px solid var(--line);padding:6px;text-align:left}}
.mute{{color:var(--mute)}}pre{{white-space:pre-wrap;background:var(--line);padding:8px;max-height:240px;overflow:auto}}
button{{background:var(--accent);color:#fff;border:0;padding:6px 14px;border-radius:6px;cursor:pointer}}
</style></head><body>
<h1>PC 중계 — {e(str(s['name']))}</h1>
<p class="mute">host {e(str(s['host_id']))} · 프로젝트 {e(str(s['project_id']))} · 허브 {e(str(s['hub']))}</p>
<p>상태: <b>{'일시정지' if s['paused'] else '돌고 있음'}</b>
<button onclick="fetch('/api/{action}',{{method:'POST',headers:{{'X-Relay-UI':'1'}}}}).then(()=>location.reload())">{'재개' if s['paused'] else '일시정지'}</button></p>
<h2>띄운 세션 ({len(s['sessions'])} / {s['max_sessions']})</h2>
<table><tr><th>요청</th><th>별칭</th><th>하네스</th><th>pid</th><th>상태</th><th>허브 세션</th></tr>{rows}</table>
<h2>허용 목록</h2><ul>{allow}</ul>
<p class="mute">승인은 중앙 허브 화면에서 owner 가 한다 · 마지막 폴링: 내줌 {s['last_poll']['dispatch']} · 전달 {s['last_poll']['deliver']}</p>
<h2>로그</h2><pre>{log}</pre></body></html>"""


def serve(relay: Relay, port: int) -> ThreadingHTTPServer:
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_a: Any) -> None:  # 표준 오류를 시끄럽게 하지 않는다
            return

        def _send(self, code: int, body: str, ctype: str) -> None:
            raw = body.encode("utf-8")
            self.send_response(code)
            self.send_header("content-type", ctype)
            self.send_header("content-length", str(len(raw)))
            # 프레임은 이 화면 자신과 VS Code webview 만 (M-047 — 확장 껍데기가 iframe 으로 띄운다). 다른 사이트가 이 화면을
            # 프레임에 넣어 일시정지 버튼을 누르게 하는 클릭재킹은 계속 막는다 (POST 는 X-Relay-UI + 같은 출처도 요구).
            self.send_header("content-security-policy", "frame-ancestors 'self' vscode-webview:")
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
