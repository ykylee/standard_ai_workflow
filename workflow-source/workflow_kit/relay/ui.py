"""중계 로컬 화면 (스펙 §10, 요구 R22.1 · M-053 WBS-53.2) — ``127.0.0.1`` 만, 표준 라이브러리 ``http.server``.

화면 정본은 ``relay/static/relay.{html,css,js}`` (Go 는 같은 바이트 내장). 보여 주는 것: 등록 정보 · 일시정지 · 하네스 · 띄운 세션(요청 · 별칭 · 하네스 · pid · 상태 · 세션 ID · 로컬 종료) ·
허용 목록(이 PC 로컬 경로 · 현재/최대 세션) · 중앙 허브 딥링크 · 최근 로그 (`fetch('/api/state')` 무깜빡임 부분 갱신).
승인 대기는 보이지 않는다 — 승인은 owner 권한이라 중앙 허브 화면에서 한다 (중계는 owner 토큰을 갖지 않는다).
토큰은 어떤 응답에도 싣지 않는다. 쓰기(POST)는 출처 대조 + ``X-Relay-UI`` 머리 — 다른 사이트의 폼이 누르지 못하게.
프레임은 ``frame-ancestors 'self' vscode-webview: vscode-file://vscode-app`` — VS Code 확장 껍데기(``editors/vscode/``)만 띄울 수 있다.
frame-ancestors 는 조상 **전부**를 대조한다 — webview(``vscode-webview:``) 위의 VS Code 데스크톱 작업대(``vscode-file://vscode-app``)가
빠지면 실제 VS Code 에서 ``ERR_BLOCKED_BY_RESPONSE`` 로 빈 화면이 된다 (TASK-2026-11-22-main-016 실측).
"""

from __future__ import annotations

import json
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
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
    proj_url, orch_url = _hub_deep_links(cfg.get("hub"), cfg.get("project_id"))
    return {
        "hub": cfg.get("hub"), "host_id": cfg.get("host_id"), "project_id": cfg.get("project_id"), "name": cfg.get("name"),
        "harnesses": cfg.get("harnesses") or [],
        "paused": bool(config.read_json("relay-state.json", {}).get("paused")),
        "sessions": live, "max_sessions": config.MAX_SESSIONS,
        "active_sessions": sum(1 for x in live if x["status"] != "ended"),
        "hub_links": {"project": proj_url, "orch": orch_url} if orch_url else None,
        "allow": [{"alias": e.get("alias"), "path": e.get("path"), "harnesses": e.get("harnesses"),
                   "permission_modes": e.get("permission_modes"), "max_sessions": e.get("max_sessions"),
                   "active_sessions": by_alias.get(str(e.get("alias") or ""), 0)} for e in config.load_allow()],
        "last_poll": {k: len(relay.last.get(k, [])) for k in ("dispatch", "deliver")} | {"halted": relay.last.get("halted", [])},
        "log": list(relay.recent)[-30:],
    }


_STATIC = Path(__file__).resolve().parent / "static"
# 화면은 정적 파일 세 개(relay.html · relay.css · relay.js)가 정본이다 — Go 중계는 같은 바이트를 내장한다(check_go_assets_sync).
# 서버는 상태를 /api/state 로만 내고, 그리기는 relay.js 한 벌이 한다 (TASK-2026-11-26-claude-plex-010).
STATIC_FILES = {
    "/": ("relay.html", "text/html; charset=utf-8"),
    "/index.html": ("relay.html", "text/html; charset=utf-8"),
    "/relay.css": ("relay.css", "text/css; charset=utf-8"),
    "/relay.js": ("relay.js", "text/javascript; charset=utf-8"),
}


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
            path = urllib.parse.urlsplit(self.path).path  # 확장이 ?theme= 를 싣는다 — 화면은 relay.js 가 읽는다
            if path == "/api/state":
                self._send(200, json.dumps(state(relay), ensure_ascii=False), "application/json")
            elif path in STATIC_FILES:
                name, ctype = STATIC_FILES[path]
                self._send(200, (_STATIC / name).read_text(encoding="utf-8"), ctype)
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
