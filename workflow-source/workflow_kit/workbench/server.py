"""라우팅 · 응답 머리 · 쓰기 요청의 대조 순서 (워크벤치 스펙 §4 · §5 · §6).

표준 ``http.server`` 위에 선다 (스펙 §1-1). 경로는 요청이 받은 그대로(프록시가 접두사를 벗긴 뒤) 보고,
링크 · ``Location`` 은 전부 상대 경로로 낸다 — 절대 URL 은 시작 때 출력하는 ``public_url`` 하나다 (§4.3).
"""

from __future__ import annotations

import hmac
import ipaddress
import json
import re
import sys
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from http import HTTPStatus
from http.cookies import CookieError, SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib import resources
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlsplit

from workflow_kit.common import plan_tasks
from workflow_kit.common.project_docs import WORK_ITEM_ID_PATTERN
from workflow_kit.workbench import auth, respond, state_view, views

COOKIE_NAME = "wb_session"
LOGIN_BODY_LIMIT = 4_096
WRITE_BODY_LIMIT = 262_144
CSP = ("default-src 'none'; style-src 'self'; script-src 'self'; form-action 'self'; base-uri 'none'; "
       "frame-ancestors 'none'")
STATIC_FILES: dict[str, str] = {
    "workbench.css": "text/css; charset=utf-8",
    "workbench.js": "text/javascript; charset=utf-8",
}
_TASK_RE = re.compile(rf"^/task/({WORK_ITEM_ID_PATTERN})$")
_RESPOND_RE = re.compile(rf"^/task/({WORK_ITEM_ID_PATTERN})/respond$")


def normalize_public_url(url: str) -> str:
    return url if url.endswith("/") else url + "/"


def origin_of(url: str) -> str:
    parts = urlsplit(url)
    return f"{parts.scheme.lower()}://{parts.netloc.lower()}"


def is_loopback(host: str) -> bool:
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


@dataclass
class App:
    """서버 한 개의 상태 — 설정과 메모리 표. 위치(브랜치)는 요청마다 ``locate`` 로 다시 읽는다 (스펙 §3)."""

    public_url: str
    tokens: tuple[auth.Token, ...]
    locate: Callable[[], state_view.Where]
    trusted_proxies: frozenset[str] = frozenset()
    sessions: auth.Sessions = field(default_factory=auth.Sessions)
    limiter: auth.LoginLimiter = field(default_factory=auth.LoginLimiter)
    log: Callable[[str], None] = field(default=lambda line: print(line, file=sys.stderr, flush=True))

    @property
    def https(self) -> bool:
        return self.public_url.lower().startswith("https://")

    @property
    def cookie_path(self) -> str:
        return urlsplit(self.public_url).path or "/"

    @property
    def origin(self) -> str:
        return origin_of(self.public_url)


class _Reject(Exception):
    def __init__(self, status: int, message: str, *, close: bool = False) -> None:
        super().__init__(message)
        self.status = status
        self.message = message
        self.close = close


class Handler(BaseHTTPRequestHandler):
    server_version = "workbench"
    sys_version = ""
    protocol_version = "HTTP/1.1"
    app: App  # make_server 가 서브클래스에 붙인다

    # ------------------------------------------------------------------ 공통

    def _path(self) -> str:
        return urlsplit(getattr(self, "path", "") or "").path

    def _rel(self) -> str:
        return views.relative_base(self._path())

    def _query(self) -> dict[str, list[str]]:
        return parse_qs(urlsplit(self.path).query, keep_blank_values=True)

    def _client(self) -> str:
        peer = self.client_address[0]
        if peer in self.app.trusted_proxies:
            forwarded = self.headers.get("X-Forwarded-For")
            if forwarded:
                return forwarded.split(",")[-1].strip()
        return peer

    def _session(self) -> auth.Session | None:
        raw = self.headers.get("Cookie")
        if not raw:
            return None
        try:
            jar: SimpleCookie = SimpleCookie(raw)
        except CookieError:
            return None
        morsel = jar.get(COOKIE_NAME)
        return self.app.sessions.get(morsel.value if morsel is not None else None)

    def _send(self, status: int, body: bytes | str, *, content_type: str = "text/html; charset=utf-8",
              headers: dict[str, str] | None = None, cache: str = "no-store") -> None:
        data = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(status)
        self.send_header("Content-Security-Policy", CSP)
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Cache-Control", cache)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        for key, value in (headers or {}).items():
            self.send_header(key, value)
        if self.close_connection:
            self.send_header("Connection", "close")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(data)

    def _redirect(self, location: str, *, headers: dict[str, str] | None = None) -> None:
        self._send(HTTPStatus.SEE_OTHER, b"", content_type="text/plain; charset=utf-8",
                   headers={"Location": location, **(headers or {})})

    def _message(self, status: int, message: str) -> None:
        where = self._where_or_none()
        self._send(status, views.message_page(rel=self._rel(), branch=where.branch if where else None,
                                              title=f"{status} {HTTPStatus(status).phrase}", message=message,
                                              back=self._rel()))

    def _where_or_none(self) -> state_view.Where | None:
        try:
            return self.app.locate()
        except Exception:  # noqa: BLE001 — 오류 화면은 위치 없이도 그린다
            return None

    def send_error(self, code: int, message: str | None = None, explain: str | None = None) -> None:
        """표준 처리기가 내는 오류(잘못된 요청 · 모르는 메서드)도 같은 머리를 갖는다 (스펙 §4.2)."""
        self.close_connection = True
        try:
            phrase = HTTPStatus(code).phrase
        except ValueError:
            phrase = "Error"
        self._send(code, f"{code} {phrase}\n", content_type="text/plain; charset=utf-8")

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002 — 표준 서명
        return  # 접근 기록은 _log 한 곳 (스펙 §5.5)

    def log_request(self, code: int | str = "-", size: int | str = "-") -> None:
        session = getattr(self, "_logged_user", None)
        stamp = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        status = code.value if isinstance(code, HTTPStatus) else code
        self.app.log(f"{stamp} {self.command or '-'} {self._path()} {status} {session or '-'}")

    def _content_length(self, limit: int) -> int:
        raw = self.headers.get("Content-Length")
        if raw is None:
            raise _Reject(HTTPStatus.LENGTH_REQUIRED, "Content-Length 가 필요하다", close=True)
        try:
            length = int(raw)
        except ValueError:
            raise _Reject(HTTPStatus.BAD_REQUEST, "Content-Length 를 읽지 못했다", close=True) from None
        if length < 0:
            raise _Reject(HTTPStatus.BAD_REQUEST, "Content-Length 를 읽지 못했다", close=True)
        if length > limit:
            raise _Reject(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, f"본문이 {limit:,} 바이트를 넘는다", close=True)
        return length

    def _form(self, length: int) -> dict[str, list[str]]:
        raw = self.rfile.read(length)
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            raise _Reject(HTTPStatus.BAD_REQUEST, "본문이 UTF-8 이 아니다") from None
        return parse_qs(text, keep_blank_values=True)

    def _check_origin(self) -> None:
        origin = self.headers.get("Origin")
        if origin is None or origin.lower() != self.app.origin:
            raise _Reject(HTTPStatus.FORBIDDEN, f"요청 출처가 {self.app.origin} 가 아니다")

    def _check_csrf(self, session: auth.Session, form: dict[str, list[str]]) -> None:
        given = (form.get("csrf") or [""])[0]
        if not hmac.compare_digest(given.encode("utf-8"), session.csrf.encode("utf-8")):
            raise _Reject(HTTPStatus.FORBIDDEN, "CSRF 값이 세션과 다르다")

    def _cookie(self, value: str, *, expire: bool = False) -> str:
        parts = [f"{COOKIE_NAME}={value}", "HttpOnly", "SameSite=Lax", f"Path={self.app.cookie_path}"]
        if self.app.https:
            parts.append("Secure")
        if expire:
            parts.append("Max-Age=0")
        return "; ".join(parts)

    def _task(self, where: state_view.Where, task_id: str) -> plan_tasks.TaskPlan | None:
        path = where.tasks_dir / f"{task_id}.md"
        if not path.is_file():
            return None
        task = plan_tasks.read_task_plan(path)
        return task if task is not None and task.task_id == task_id else None

    # ------------------------------------------------------------------ 진입

    def do_GET(self) -> None:  # noqa: N802 — 표준 서명
        self._dispatch(get=True)

    def do_POST(self) -> None:  # noqa: N802 — 표준 서명
        self._dispatch(get=False)

    def _not_found(self) -> None:
        """경로 표(§4.1) 밖의 메서드도 404 — 표준 처리기의 501 이 아니다."""
        self.close_connection = True
        self._send(HTTPStatus.NOT_FOUND, "404 Not Found\n", content_type="text/plain; charset=utf-8")

    do_HEAD = do_PUT = do_DELETE = do_PATCH = do_OPTIONS = _not_found  # noqa: N815

    def _dispatch(self, *, get: bool) -> None:
        try:
            self._route(get=get)
        except _Reject as reject:
            # 쓰기 요청을 거절하면 본문을 다 읽지 않았을 수 있다 — 연결을 닫는다.
            if reject.close or not get:
                self.close_connection = True
            self._message(reject.status, reject.message)
        except BrokenPipeError:
            self.close_connection = True

    def _route(self, *, get: bool) -> None:
        path = self._path()
        if get and path == "/healthz":
            self._send(HTTPStatus.OK, "ok\n", content_type="text/plain; charset=utf-8")
            return
        if get and path.startswith("/static/"):
            self._static(path[len("/static/"):])
            return
        if path == "/login":
            if "token" in self._query():
                raise _Reject(HTTPStatus.BAD_REQUEST, "토큰은 질의 문자열로 받지 않는다 — 로그인 폼을 쓴다")
            if get:
                self._send(HTTPStatus.OK, views.login_page(rel=self._rel()))
            else:
                self._login()
            return
        if path == "/logout" and not get:
            self._logout()
            return
        if get and path in ("/", "/api/state"):
            self._progress(api=path == "/api/state")
            return
        match = _TASK_RE.match(path)
        if get and match:
            self._plan(match.group(1))
            return
        match = _RESPOND_RE.match(path)
        if not get and match:
            self._respond(match.group(1))
            return
        self._send(HTTPStatus.NOT_FOUND, "404 Not Found\n", content_type="text/plain; charset=utf-8")

    def _static(self, name: str) -> None:
        content_type = STATIC_FILES.get(name)
        if content_type is None:
            self._send(HTTPStatus.NOT_FOUND, "404 Not Found\n", content_type="text/plain; charset=utf-8")
            return
        data = resources.files("workflow_kit.workbench").joinpath("static").joinpath(name).read_bytes()
        self._send(HTTPStatus.OK, data, content_type=content_type, cache="max-age=3600")

    # ------------------------------------------------------------------ 로그인

    def _login(self) -> None:
        length = self._content_length(LOGIN_BODY_LIMIT)
        self._check_origin()
        client = self._client()
        if self.app.limiter.blocked(client):
            self.rfile.read(length)
            raise _Reject(HTTPStatus.TOO_MANY_REQUESTS, "로그인 실패가 많다 — 60초 뒤에 다시 한다")
        form = self._form(length)
        token = auth.match_token(self.app.tokens, (form.get("token") or [""])[0])
        if token is None:
            self.app.limiter.fail(client)
            self._send(HTTPStatus.UNAUTHORIZED, views.login_page(rel=self._rel(), error="토큰이 맞지 않는다"))
            return
        session = self.app.sessions.create(token)
        self._logged_user = token.name
        self._redirect("./", headers={"Set-Cookie": self._cookie(session.sid)})

    def _logout(self) -> None:
        length = self._content_length(LOGIN_BODY_LIMIT)
        session = self._session()
        if session is None:
            raise _Reject(HTTPStatus.UNAUTHORIZED, "세션이 없다")
        self._check_origin()
        form = self._form(length)
        self._check_csrf(session, form)
        self.app.sessions.drop(session.sid)
        self._redirect("./login", headers={"Set-Cookie": self._cookie("", expire=True)})

    # ------------------------------------------------------------------ 화면

    def _need_session(self, *, api: bool) -> auth.Session | None:
        session = self._session()
        if session is None:
            if api:
                self._send(HTTPStatus.UNAUTHORIZED, '{"error": "unauthorized"}\n',
                           content_type="application/json; charset=utf-8")
            else:
                self._redirect(self._rel() + "login")
            return None
        self._logged_user = session.name
        return session

    def _progress(self, *, api: bool) -> None:
        session = self._need_session(api=api)
        if session is None:
            return
        state = state_view.build_state(self.app.locate())
        if api:
            self._send(HTTPStatus.OK, json.dumps(state, ensure_ascii=False, indent=2) + "\n",
                       content_type="application/json; charset=utf-8")
            return
        self._send(HTTPStatus.OK, views.progress_page(state=state, rel=self._rel(), user=session.name,
                                                      csrf=session.csrf))

    def _plan(self, task_id: str, *, error: str | None = None, status: int = HTTPStatus.OK) -> None:
        session = self._need_session(api=False)
        if session is None:
            return
        where = self.app.locate()
        task = self._task(where, task_id)
        if task is None:
            self._send(HTTPStatus.NOT_FOUND, views.message_page(
                rel=self._rel(), branch=where.branch, title="404 Not Found",
                message=f"이 브랜치에 task 가 없다: {task_id}", back=self._rel()))
            return
        flash, session.flash = session.flash, None
        self._send(status, views.plan_page(
            view=state_view.build_plan(where, task), rel=self._rel(), branch=where.branch, user=session.name,
            csrf=session.csrf, role=session.role, flash=flash, error=error))

    # ------------------------------------------------------------------ 쓰기 (§5.4 → §6)

    def _respond(self, task_id: str) -> None:
        # §5.4 — 순서대로, 하나라도 어긋나면 아무것도 쓰지 않는다.
        length = self._content_length(WRITE_BODY_LIMIT)
        session = self._session()
        if session is None:
            raise _Reject(HTTPStatus.UNAUTHORIZED, "세션이 없다", close=True)
        self._logged_user = session.name
        if session.role != auth.ROLE_APPROVER:
            raise _Reject(HTTPStatus.FORBIDDEN, "approver 만 응답할 수 있다", close=True)
        self._check_origin()
        form = self._form(length)
        self._check_csrf(session, form)
        where = self.app.locate()
        task = self._task(where, task_id)
        if task is None:
            raise _Reject(HTTPStatus.NOT_FOUND, f"이 브랜치에 task 가 없다: {task_id}")
        outcome = respond.build_and_publish(branch_dir=where.branch_dir, task=task, form=form,
                                            responder=session.name)
        if not outcome.ok:
            self._send(outcome.status, views.message_page(
                rel=self._rel(), branch=where.branch, title=f"{outcome.status} {HTTPStatus(outcome.status).phrase}",
                message=outcome.message, back=f"../{task_id}"))
            return
        session.flash = outcome.message
        self._redirect(f"../{task_id}")


def make_server(app: App, host: str, port: int) -> ThreadingHTTPServer:
    handler = type("BoundHandler", (Handler,), {"app": app})
    server = ThreadingHTTPServer((host, port), handler)
    server.daemon_threads = True
    return server


def serve_in_thread(server: ThreadingHTTPServer) -> threading.Thread:
    thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.1}, daemon=True)
    thread.start()
    return thread


def where_for(profile_path: Path) -> Callable[[], state_view.Where]:
    """프로필 기준 위치를 **요청마다** 다시 계산하는 함수 — 브랜치가 바뀌면 따라간다."""
    from workflow_kit.common.paths import branch_for_workspace, project_workspace_root, workflow_branch_dir

    def locate() -> state_view.Where:
        workspace = project_workspace_root(profile_path)
        return state_view.Where(workspace_root=workspace, branch=branch_for_workspace(workspace),
                                branch_dir=workflow_branch_dir(profile_path))

    return locate
