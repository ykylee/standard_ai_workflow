"""워크벤치 검사 넷이 같이 쓰는 fixture (`core/plan_workbench_spec.md` §11).

- 작업 공간은 실물과 같은 배치(`ai-workflow/memory/active/<branch>/`)이고 task 는 ``backlog-update`` 로 만든다 —
  손으로 쓴 task 파일은 게이트가 만든 것과 갈라진다.
- 서버는 같은 프로세스의 스레드로 포트 0 에 띄운다. 위치는 브랜치 env 가 아니라 작업 공간에서 직접 만든다.
- HTTP 는 ``http.client`` 로 하나씩 보낸다 — 리다이렉트를 따라가지 않고 쿠키는 ``Path`` 를 지키는 작은 단지로 다룬다.
"""

from __future__ import annotations

import hashlib
import http.client
import itertools
import json
import os
import re
import subprocess
import sys
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Iterator
from urllib.parse import urlencode, urljoin, urlsplit

SOURCE_ROOT = Path(__file__).resolve().parents[1]
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from workflow_kit.common import plan_responses as pr  # noqa: E402
from workflow_kit.workbench import auth, server, state_view  # noqa: E402

BRANCH = "workbench"
BACKLOG_UPDATE = SOURCE_ROOT / "workflow_kit" / "tools" / "backlog_update.py"
APPROVER = auth.Token("approver", "alice", "a" * 40)
VIEWER = auth.Token("viewer", "bob", "b" * 40)
D1 = "D1 [C1] 막는가? | default: block | options: block = 거부한다; warn = 경고만 낸다"
D2 = "D2 [C2] 어느 쪽인가? | default: a | options: a = 가; b = 나"


def env() -> dict[str, str]:
    out = dict(os.environ)
    out["PYTHONPATH"] = str(SOURCE_ROOT)
    out["CODEX_WORKFLOW_BRANCH"] = BRANCH
    out["PYTHONIOENCODING"] = "utf-8"
    return out


def branch_dir(ws: Path) -> Path:
    return ws / "ai-workflow" / "memory" / "active" / BRANCH


def profile(ws: Path) -> Path:
    return ws / "docs" / "PROJECT_PROFILE.md"


def make_workspace(td: str) -> Path:
    ws = Path(td)
    (ws / "docs").mkdir(parents=True, exist_ok=True)
    profile(ws).write_text("# Profile\n", encoding="utf-8")
    (branch_dir(ws) / "backlog" / "tasks").mkdir(parents=True, exist_ok=True)
    (branch_dir(ws) / "sessions").mkdir(parents=True, exist_ok=True)
    return ws


def cli(ws: Path, argv: list[str], *, timeout: float = 60) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, *argv], capture_output=True, encoding="utf-8", errors="replace",
                          check=False, env=env(), cwd=str(ws), timeout=timeout)


def backlog(ws: Path, *args: str) -> dict[str, Any]:
    proc = cli(ws, [str(BACKLOG_UPDATE), "--project-profile-path", str(profile(ws)), "--target-date", "2026-11-14",
                    "--apply", *args])
    try:
        out: dict[str, Any] = json.loads(proc.stdout)
    except json.JSONDecodeError:
        raise AssertionError(f"backlog-update 출력이 JSON 이 아니다: {proc.stdout[-300:]} {proc.stderr[-300:]}") from None
    if proc.returncode != 0:
        raise AssertionError(f"backlog-update rc {proc.returncode}: {out.get('error') or out}")
    return out


def create_task(ws: Path, *decisions: str, name: str = "응답을 받는 task", claims: tuple[str, ...] = (),
                criteria: tuple[str, ...] = ()) -> str:
    out = backlog(
        ws, "--mode", "create", "--status", "planned", "--task-name", name, "--task-brief", "b",
        *itertools.chain.from_iterable(("--done-criteria", c) for c in (criteria or ("[C1] 닫히지 않는다", "[C2] 그대로다"))),
        *itertools.chain.from_iterable(("--plan-claim", c) for c in (claims or (
            "C1 열린 결정이 남으면 닫히지 않는다", "C2 옛 task 는 그대로 읽힌다"))),
        *itertools.chain.from_iterable(("--plan-decision", d) for d in (decisions if decisions else (D1, D2))))
    return str(out["task_id"])


def plan_import(ws: Path, *args: str) -> tuple[int, dict[str, Any]]:
    proc = cli(ws, ["-m", "workflow_kit", "plan-import", "--project-profile-path", str(profile(ws)), *args])
    try:
        return proc.returncode, json.loads(proc.stdout)
    except json.JSONDecodeError:
        return proc.returncode, {"_raw": proc.stdout[-300:], "_err": proc.stderr[-300:]}


def inbox_snapshot(ws: Path) -> dict[str, str]:
    """받은편지함의 이름 → 내용 지문 (`.gitignore` · 잠금 제외)."""
    inbox = pr.inbox_dir(branch_dir(ws))
    if not inbox.is_dir():
        return {}
    return {
        entry.name: hashlib.sha256(entry.read_bytes()).hexdigest()
        for entry in sorted(inbox.iterdir())
        if entry.is_file() and entry.name not in (".gitignore", pr.LOCK_FILENAME)
    }


def tree_snapshot(ws: Path, *, skip: tuple[str, ...] = ()) -> dict[str, str]:
    out: dict[str, str] = {}
    for path in sorted(ws.rglob("*")):
        rel = path.relative_to(ws).as_posix()
        if path.is_file() and not any(rel.startswith(prefix) for prefix in skip) and "telemetry" not in path.parts:
            out[rel] = hashlib.sha256(path.read_bytes()).hexdigest()
    return out


# --------------------------------------------------------------------------- 서버


@dataclass
class Running:
    app: server.App
    httpd: Any
    port: int
    logs: list[str] = field(default_factory=list)

    @property
    def host(self) -> str:
        return f"127.0.0.1:{self.port}"


def locate_for(ws: Path) -> Any:
    def locate() -> state_view.Where:
        return state_view.Where(workspace_root=ws, branch=BRANCH, branch_dir=branch_dir(ws))
    return locate


@contextmanager
def running(ws: Path, *, public_url: str | None = None, tokens: tuple[auth.Token, ...] = (APPROVER, VIEWER),
            trusted_proxies: frozenset[str] = frozenset()) -> Iterator[Running]:
    logs: list[str] = []
    app = server.App(public_url="http://127.0.0.1:0/", tokens=tokens, locate=locate_for(ws),
                     trusted_proxies=trusted_proxies, log=logs.append)
    httpd = server.make_server(app, "127.0.0.1", 0)
    port = httpd.server_address[1]
    app.public_url = server.normalize_public_url(public_url or f"http://127.0.0.1:{port}/")
    server.serve_in_thread(httpd)
    try:
        yield Running(app=app, httpd=httpd, port=port, logs=logs)
    finally:
        httpd.shutdown()
        httpd.server_close()


@dataclass
class Reply:
    status: int
    headers: dict[str, list[str]]
    body: bytes

    def header(self, name: str) -> str | None:
        values = self.headers.get(name.lower())
        return values[-1] if values else None

    @property
    def text(self) -> str:
        return self.body.decode("utf-8", errors="replace")


def request(port: int, method: str, path: str, *, body: bytes | None = None,
            headers: dict[str, str] | None = None) -> Reply:
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=30)
    try:
        conn.request(method, path, body=body, headers=headers or {})
        resp = conn.getresponse()
        data = resp.read()
        collected: dict[str, list[str]] = {}
        for key, value in resp.getheaders():
            collected.setdefault(key.lower(), []).append(value)
        return Reply(resp.status, collected, data)
    finally:
        conn.close()


class Browser:
    """쿠키 ``Path`` 를 지키고 상대 경로를 현재 URL 기준으로 푸는 작은 클라이언트 (리다이렉트는 따라가지 않는다)."""

    def __init__(self, port: int, *, origin: str | None = None) -> None:
        self.port = port
        self.origin = origin or f"http://127.0.0.1:{port}"
        self.cookies: dict[str, tuple[str, str]] = {}  # name → (value, path)
        self.seen: list[str] = []

    def _cookie_header(self, path: str) -> dict[str, str]:
        pairs = [f"{name}={value}" for name, (value, cpath) in self.cookies.items()
                 if value and path.startswith(cpath)]
        return {"Cookie": "; ".join(pairs)} if pairs else {}

    def _store(self, reply: Reply) -> None:
        for raw in reply.headers.get("set-cookie", []):
            parts = [p.strip() for p in raw.split(";")]
            name, _, value = parts[0].partition("=")
            path = next((p.split("=", 1)[1] for p in parts[1:] if p.lower().startswith("path=")), "/")
            self.cookies[name] = (value, path)

    def get(self, path: str) -> Reply:
        self.seen.append(path)
        reply = request(self.port, "GET", path, headers=self._cookie_header(path))
        self._store(reply)
        return reply

    def post(self, path: str, form: dict[str, str] | list[tuple[str, str]], *, origin: str | None = "default",
             extra: dict[str, str] | None = None) -> Reply:
        self.seen.append(path)
        data = urlencode(form).encode("utf-8")
        headers = {"Content-Type": "application/x-www-form-urlencoded", **self._cookie_header(path), **(extra or {})}
        if origin == "default":
            headers["Origin"] = self.origin
        elif origin is not None:
            headers["Origin"] = origin
        reply = request(self.port, "POST", path, body=data, headers=headers)
        self._store(reply)
        return reply

    def login(self, token: auth.Token, *, login_path: str = "/login") -> Reply:
        return self.post(login_path, {"token": token.value})


def resolve(current: str, location: str) -> str:
    """브라우저처럼 상대 경로를 푼다 — 경로만 돌려준다."""
    return urlsplit(urljoin("http://x" + current, location)).path


class FormParser(HTMLParser):
    """페이지의 첫 ``respond`` 폼 — action 과 기본 제출값(hidden · checked radio · textarea 이름)."""

    def __init__(self) -> None:
        super().__init__()
        self.forms: list[dict[str, Any]] = []
        self._current: dict[str, Any] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = {k: v or "" for k, v in attrs}
        if tag == "form":
            self._current = {"action": a.get("action", ""), "fields": [], "textareas": []}
            self.forms.append(self._current)
        elif self._current is not None and tag == "input":
            kind = a.get("type", "text")
            if kind == "hidden" or (kind == "radio" and "checked" in a):
                self._current["fields"].append((a.get("name", ""), a.get("value", "")))
        elif self._current is not None and tag == "textarea":
            self._current["textareas"].append(a.get("name", ""))

    def handle_endtag(self, tag: str) -> None:
        if tag == "form":
            self._current = None


def respond_form(html_text: str) -> dict[str, Any] | None:
    parser = FormParser()
    parser.feed(html_text)
    return next((f for f in parser.forms if f["action"].endswith("/respond")), None)


def csrf_of(html_text: str) -> str:
    match = re.search(r'name="csrf" value="([^"]+)"', html_text)
    if not match:
        raise AssertionError("페이지에 csrf 값이 없다")
    return match.group(1)


def submit(browser: Browser, task_path: str, *, overrides: dict[str, str] | None = None,
           drop: tuple[str, ...] = (), extra_fields: list[tuple[str, str]] | None = None) -> tuple[Reply, str]:
    """계획 화면을 열어 폼을 그대로(또는 바꿔) 제출한다 — (응답, 제출 경로)."""
    page = browser.get(task_path)
    if page.status != 200:
        raise AssertionError(f"계획 화면이 {page.status} 다: {task_path}")
    form = respond_form(page.text)
    if form is None:
        raise AssertionError("계획 화면에 respond 폼이 없다")
    fields = [(k, v) for k, v in form["fields"] if k not in drop and k not in (overrides or {})]
    fields.extend((overrides or {}).items())
    fields.extend(extra_fields or [])
    action = resolve(task_path, form["action"])
    return browser.post(action, fields), action


def temp_workspace(prefix: str) -> tempfile.TemporaryDirectory[str]:
    return tempfile.TemporaryDirectory(prefix=prefix)
