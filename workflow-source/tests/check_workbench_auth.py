#!/usr/bin/env python3
"""워크벤치 — 명령 · 수명 · 인증 · 응답 머리 (`core/plan_workbench_spec.md` §2 · §3 · §4 · §5 · §11).

1. 시작 거절 — 토큰 없음 · 32자 미만 · 파일 모드 넓음 · 이름 문법 · 이름 겹침 · 비 loopback 평문 · TLS+http ·
   포트 사용 중 · 살아 있는 서버: 전부 rc 2 · 이유 한 줄 · 실행 기록 무변경
2. 수명 — 기록(`.workbench/server.json`)과 자기 무시 `.gitignore`, `--status`, 죽은 pid 기록 덮기 ·
   죽은 pid 임시 파일 청소, `session-start` 의 `public_url` 줄(살아 있을 때만), SIGTERM 에 기록 삭제
3. `--new-token` — `0600` 파일 · 값은 출력에 없음 · 있는 파일은 덮지 않음
4. 경로 표 밖은 404, 모든 응답에 §4.2 머리 (`static/` 만 `max-age=3600`)
5. 세션 없는 요청 — 화면은 303 `login` (상대), `api/state` 는 401
6. 질의 문자열의 토큰은 400 · 로그인 실패 5회면 429 (맞는 토큰도)
7. viewer — 폼이 없고 POST 는 403 · 받은편지함 무변경
8. §5.4 네 단계 — Content-Length 없음 411 · 한도 413 · 세션 없음 401 · Origin 403 · CSRF 403, 전부 받은편지함 무변경
9. 쿠키 — `HttpOnly` · `SameSite=Lax` · `Path` = `public_url` 경로 · `https` 면 `Secure`; 로그아웃은 CSRF 를 대조한다
10. 접근 기록 — 토큰 · 쿠키 · CSRF · 폼 본문이 없다
11. 시간 — 세션 12시간 만료 · 실패 60초 창 · 차단 60초 · 로그아웃도 Origin 대조
12. §5.4 순서 — 길이 → 세션 · 역할 → Origin → CSRF
"""

from __future__ import annotations

#: 서버 subprocess 를 여러 번 띄운다.
CHECK_TIMEOUT_S = 180

#: 이 검사의 입력 표면 (spec `core/test_impact_tiering_spec.md` §2).
WATCHES = (
    "workflow-source/pyproject.toml",
    "workflow-source/workflow_kit/*",
    "workflow-source/tests/_workbench_fixture.py",
)

import json
import os
import signal
import socket
import subprocess
import sys
import time
import traceback
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _workbench_fixture as fx  # noqa: E402
from workflow_kit.common import plan_responses as pr  # noqa: E402
from workflow_kit.tools import workbench as wb_cli  # noqa: E402
from workflow_kit.workbench import server  # noqa: E402

FAILURES: list[str] = []
GOOD = "g" * 40
HEADERS = {
    # 스펙 §4.2 문면 그대로 — 서버 모듈의 상수를 빌리면 그 상수를 바꾼 결함이 함께 바뀐다.
    "content-security-policy": ("default-src 'none'; style-src 'self'; script-src 'self'; form-action 'self'; "
                                "base-uri 'none'; frame-ancestors 'none'"),
    "x-content-type-options": "nosniff",
    "referrer-policy": "no-referrer",
}


def _record(name: str, problems: list[str]) -> None:
    if problems:
        FAILURES.append(name)
        print(f"  FAIL  {name}")
        for problem in problems[:12]:
            print(f"        - {problem}")
    else:
        print(f"  PASS  {name}")


def _wb(ws: Path, *args: str, extra_env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    env = fx.env()
    env.update(extra_env or {})
    return subprocess.run(
        [sys.executable, "-m", "workflow_kit", "workbench", "--project-profile-path", str(fx.profile(ws)), *args],
        capture_output=True, encoding="utf-8", errors="replace", check=False, env=env, cwd=str(ws), timeout=60)


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def case_start_refusals() -> list[str]:
    problems: list[str] = []
    with fx.temp_workspace("wb-auth-1-") as td:
        ws = fx.make_workspace(td)
        wide = ws / "wide.token"
        wide.write_text(GOOD, encoding="utf-8")
        os.chmod(wide, 0o644)
        busy = socket.socket()
        busy.bind(("127.0.0.1", 0))
        busy.listen(1)
        busy_port = busy.getsockname()[1]
        token = ["--token", "approver:alice=env:WB_T", "--port", "0"]
        env = {"WB_T": GOOD, "WB_SHORT": "s" * 31}
        refusals = [
            ("토큰 없음", ["--port", "0"], "토큰이 없다"),
            ("32자 미만", ["--token", "approver:alice=env:WB_SHORT", "--port", "0"], "32자 미만"),
            ("파일 모드", ["--token", f"approver:alice=file:{wide}", "--port", "0"], "0600"),
            ("이름 문법", ["--token", "approver:al ice=env:WB_T", "--port", "0"], "이름은"),
            ("역할", ["--token", "admin:alice=env:WB_T", "--port", "0"], "역할은"),
            ("이름 겹침", [*token, "--token", "viewer:alice=env:WB_T"], "겹친다"),
            ("비 loopback 평문", [*token, "--bind", "0.0.0.0"], "loopback"),
            ("TLS+http", [*token, "--tls-cert", "c.pem", "--tls-key", "k.pem"], "http"),
            ("포트 사용 중", ["--token", "approver:alice=env:WB_T", "--port", str(busy_port)], "bind"),
            ("모르는 인자", [*token, "--nope"], ""),
            ("접두 축약", ["--stat"], ""),
        ]
        try:
            for label, args, needle in refusals:
                proc = _wb(ws, *args, extra_env=env)
                lines = [ln for ln in proc.stderr.splitlines() if ln.strip()]
                if proc.returncode != 2:
                    problems.append(f"{label}: rc {proc.returncode} (기대 2) {proc.stderr[-200:]}")
                elif needle and (len(lines) != 1 or needle not in lines[0]):
                    problems.append(f"{label}: 이유 한 줄에 `{needle}` 이 없다: {lines}")
                if (ws / ".workbench" / "server.json").exists():
                    problems.append(f"{label}: 거절했는데 실행 기록이 생겼다")
        finally:
            busy.close()
        # 살아 있는 서버 — 기록의 pid 가 살아 있으면 그 public_url 을 알린다.
        record = ws / ".workbench"
        record.mkdir()
        (record / "server.json").write_text(json.dumps(
            {"pid": os.getpid(), "port": 1, "public_url": "http://127.0.0.1:1/", "started_at": "x"}), encoding="utf-8")
        proc = _wb(ws, *token, extra_env=env)
        if proc.returncode != 2 or "http://127.0.0.1:1/" not in proc.stderr:
            problems.append(f"살아 있는 서버: rc {proc.returncode} {proc.stderr[-200:]}")
    return problems


def _start(ws: Path, *args: str) -> tuple[subprocess.Popen[str], str]:
    env = fx.env()
    env["WB_T"] = GOOD
    proc = subprocess.Popen(
        [sys.executable, "-m", "workflow_kit", "workbench", "--project-profile-path", str(fx.profile(ws)),
         "--token", "approver:alice=env:WB_T", "--port", "0", *args],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding="utf-8", env=env, cwd=str(ws))
    assert proc.stdout is not None
    line = proc.stdout.readline().strip()
    return proc, line


def _session_start_summary(ws: Path) -> list[str]:
    handoff = fx.branch_dir(ws) / "session_handoff.md"
    if not handoff.is_file():  # session-start 는 handoff 가 없으면 오류로 끝난다
        handoff.write_text("# Session Handoff\n", encoding="utf-8")
    proc = fx.cli(ws, ["-m", "workflow_kit", "session-start", "--project-profile-path", str(fx.profile(ws))],
                  timeout=120)
    try:
        return list(json.loads(proc.stdout).get("summary") or [])
    except json.JSONDecodeError:
        return [f"(session-start 출력이 JSON 이 아니다: {proc.stderr[-200:]})"]


def case_lifecycle() -> list[str]:
    problems: list[str] = []
    with fx.temp_workspace("wb-auth-2-") as td:
        ws = fx.make_workspace(td)
        record_dir = ws / ".workbench"
        record_dir.mkdir()
        (record_dir / ".gitignore").write_text("!keep\r\n", encoding="utf-8")
        (record_dir / "server.json").write_text(json.dumps({"pid": 2 ** 22 + 12345, "port": 9, "public_url": "x"}),
                                                encoding="utf-8")
        inbox = pr.ensure_inbox(fx.branch_dir(ws))
        dead_tmp = inbox / ".tmp-4194303-0123456789abcdef"
        live_tmp = inbox / f".tmp-{os.getpid()}-0123456789abcdef"
        dead_tmp.write_bytes(b"x")
        live_tmp.write_bytes(b"x")
        inbox_rel = inbox.relative_to(ws).as_posix() + "/"
        quiet = (".workbench/", inbox_rel)
        before_tree = fx.tree_snapshot(ws, skip=quiet)
        proc, url = _start(ws, "--public-url", "http://127.0.0.1:9/wb")
        try:
            if url != "http://127.0.0.1:9/wb/":
                problems.append(f"public_url 에 끝 슬래시를 붙이지 않았다: {url!r}")
            data = json.loads((record_dir / "server.json").read_text(encoding="utf-8"))
            if data.get("pid") != proc.pid or data.get("public_url") != url or not data.get("started_at"):
                problems.append(f"실행 기록이 맞지 않다 (죽은 pid 기록을 덮지 않았다?): {data}")
            if set(data) != {"pid", "port", "public_url", "started_at"}:
                problems.append(f"실행 기록에 다른 것이 실렸다: {sorted(data)}")
            if (record_dir / ".gitignore").read_bytes() != b"*\n":
                problems.append("시작할 때 .workbench/.gitignore 를 *\\n 으로 되돌리지 않았다")
            if dead_tmp.exists() or not live_tmp.exists():
                problems.append(f"임시 파일 청소가 틀렸다: 죽은 pid {dead_tmp.exists()} · 산 pid {live_tmp.exists()}")
            port = json.loads((record_dir / "server.json").read_text(encoding="utf-8"))["port"]
            client = fx.Browser(port, origin="http://127.0.0.1:9")
            client.login(auth_token := wb_cli.auth.Token("approver", "alice", GOOD))
            for path in ("/", "/api/state", "/healthz", "/nope"):
                client.get(path)
            del auth_token
            changed = sorted(k for k, v in fx.tree_snapshot(ws, skip=quiet).items() if before_tree.get(k) != v)
            changed += sorted(set(before_tree) - set(fx.tree_snapshot(ws, skip=quiet)))
            if changed:
                problems.append(f"CLI 서버가 .workbench/ · 받은편지함 밖에 썼다: {changed}")
            status = json.loads(_wb(ws, "--status").stdout)
            if status.get("running") is not True or status.get("public_url") != url:
                problems.append(f"--status 가 실행 중을 보이지 않는다: {status}")
            if f"워크벤치 실행 중: {url}" not in _session_start_summary(ws):
                problems.append("session-start 보고에 살아 있는 서버의 public_url 줄이 없다")
            health = fx.request(port, "GET", "/healthz")
            if health.status != 200 or health.text.strip() != "ok":
                problems.append(f"healthz: {health.status}")
        finally:
            proc.send_signal(signal.SIGTERM)
            try:
                proc.wait(timeout=15)
            except subprocess.TimeoutExpired:
                proc.kill()
                problems.append("SIGTERM 에 끝나지 않았다")
        if (record_dir / "server.json").exists():
            problems.append("정상 종료 뒤 실행 기록이 남았다")
        # 기록이 남았어도 pid 가 죽었으면 싣지 않는다 (비정상 종료 뒤의 모양).
        (record_dir / "server.json").write_text(json.dumps(
            {"pid": 2 ** 22 + 12345, "port": 1, "public_url": "http://127.0.0.1:1/", "started_at": "x"}), encoding="utf-8")
        if any("워크벤치" in line for line in _session_start_summary(ws)):
            problems.append("서버가 죽었는데 session-start 가 워크벤치 줄을 싣는다")
        (record_dir / "server.json").unlink()
        status = json.loads(_wb(ws, "--status").stdout)
        if status.get("running") is not False:
            problems.append(f"종료 뒤 --status 가 running 이다: {status}")
    return problems


def case_new_token() -> list[str]:
    problems: list[str] = []
    with fx.temp_workspace("wb-auth-3-") as td:
        ws = fx.make_workspace(td)
        out = ws / "alice.token"
        proc = _wb(ws, "--new-token", "approver:alice", "--out", str(out))
        if proc.returncode != 0 or not out.is_file():
            return [f"--new-token 실패: rc {proc.returncode} {proc.stderr[-200:]}"]
        value = out.read_text(encoding="utf-8").strip()
        if len(value) < 32:
            problems.append(f"토큰 값이 32자 미만: {len(value)}")
        if os.name == "posix" and (out.stat().st_mode & 0o777) != 0o600:
            problems.append(f"토큰 파일 모드가 0600 이 아니다: {oct(out.stat().st_mode & 0o777)}")
        if value in proc.stdout or value in proc.stderr:
            problems.append("토큰 값이 출력에 실렸다")
        again = _wb(ws, "--new-token", "approver:alice", "--out", str(out))
        if again.returncode != 2 or out.read_text(encoding="utf-8").strip() != value:
            problems.append("있는 토큰 파일을 덮었다")
        # `~` 와 없는 디렉터리 — 스킬이 안내하는 꼴 그대로 (셸은 `=file:~/…` 의 `~` 를 펼치지 않는다).
        nested = _wb(ws, "--new-token", "viewer:bob", "--out", "~/.config/wb/bob.token", extra_env={"HOME": str(ws)})
        made = ws / ".config" / "wb" / "bob.token"
        if nested.returncode != 0 or not made.is_file():
            problems.append(f"--out 의 ~ · 없는 디렉터리: rc {nested.returncode} {nested.stderr[-200:]}")
        elif os.name == "posix" and (made.parent.stat().st_mode & 0o077):
            problems.append(f"새로 만든 토큰 디렉터리가 0700 이 아니다: {oct(made.parent.stat().st_mode & 0o777)}")
        else:
            with mock.patch.dict(os.environ, {"HOME": str(ws)}):
                try:
                    wb_cli.auth.load_tokens(["viewer:bob=file:~/.config/wb/bob.token"])
                except wb_cli.auth.TokenError as exc:
                    problems.append(f"=file:~/… 를 읽지 못한다: {exc}")
        # 만든 파일이 그대로 시작에 쓰인다 (모드 검사를 통과한다).
        tokens = wb_cli.auth.load_tokens([f"approver:alice=file:{out}"])
        if tokens[0].value != value:
            problems.append("만든 토큰 파일을 시작이 읽지 못한다")
    return problems


def _check_headers(label: str, reply: fx.Reply, problems: list[str], *, cache: str = "no-store") -> None:
    for key, value in HEADERS.items():
        if reply.header(key) != value:
            problems.append(f"{label}: {key} = {reply.header(key)!r}")
    if reply.header("cache-control") != cache:
        problems.append(f"{label}: cache-control = {reply.header('cache-control')!r} (기대 {cache})")


def case_routes_and_headers() -> list[str]:
    problems: list[str] = []
    with fx.temp_workspace("wb-auth-4-") as td:
        ws = fx.make_workspace(td)
        task_id = fx.create_task(ws)
        with fx.running(ws) as srv:
            browser = fx.Browser(srv.port)
            browser.login(fx.APPROVER)
            for method, path in (("GET", "/nope"), ("GET", "/task/NOT-A-TASK"), ("GET", "/static/evil.js"),
                                 ("GET", "/static/../server.py"), ("GET", f"/task/{task_id}/respond"),
                                 ("POST", "/"), ("POST", "/api/state"), ("GET", "/logout"),
                                 ("GET", "/task/TASK-2026-01-01-workbench-999")):
                reply = browser.get(path) if method == "GET" else browser.post(path, {})
                if reply.status != 404:
                    problems.append(f"{method} {path}: {reply.status} (기대 404)")
                _check_headers(f"{method} {path}", reply, problems)
            for path in ("/", f"/task/{task_id}", "/api/state", "/login", "/healthz"):
                _check_headers(f"GET {path}", browser.get(path), problems)
            _check_headers("GET 세션 없음", fx.request(srv.port, "GET", "/"), problems)
            for method in ("HEAD", "PUT", "DELETE", "OPTIONS", "PATCH"):
                reply = fx.request(srv.port, method, "/", body=b"" if method in ("PUT", "PATCH") else None)
                if reply.status != 404:
                    problems.append(f"{method} /: {reply.status} (기대 404 — 경로 표 밖)")
                _check_headers(method, reply, problems)
            for name in server.STATIC_FILES:
                reply = fx.request(srv.port, "GET", f"/static/{name}")
                if reply.status != 200 or not reply.body:
                    problems.append(f"static/{name}: {reply.status}")
                _check_headers(f"static/{name}", reply, problems, cache="max-age=3600")
            text = browser.get(f"/task/{task_id}").text
            if "<script>" in text or "style=" in text:
                problems.append("인라인 스크립트 · 스타일이 있다 (CSP)")
    return problems


def case_no_session() -> list[str]:
    problems: list[str] = []
    with fx.temp_workspace("wb-auth-5-") as td:
        ws = fx.make_workspace(td)
        task_id = fx.create_task(ws)
        with fx.running(ws) as srv:
            for path, location in (("/", "./login"), (f"/task/{task_id}", "../login")):
                reply = fx.request(srv.port, "GET", path)
                if reply.status != 303 or reply.header("location") != location:
                    problems.append(f"GET {path}: {reply.status} {reply.header('location')} (기대 303 {location})")
            reply = fx.request(srv.port, "GET", "/api/state")
            if reply.status != 401 or "branch" in reply.text:
                problems.append(f"api/state 세션 없음: {reply.status}")
            fx.Browser(srv.port).login(fx.APPROVER)  # 표에 진짜 세션이 있어도
            reply = fx.request(srv.port, "GET", "/", headers={"Cookie": "wb_session=forged"})
            if reply.status != 303:
                problems.append(f"위조 쿠키가 통했다: {reply.status}")
    return problems


def case_login_limits() -> list[str]:
    problems: list[str] = []
    with fx.temp_workspace("wb-auth-6-") as td:
        ws = fx.make_workspace(td)
        with fx.running(ws) as srv:
            reply = fx.request(srv.port, "GET", f"/login?token={fx.APPROVER.value}")
            if reply.status != 400:
                problems.append(f"질의 토큰 GET: {reply.status} (기대 400)")
            browser = fx.Browser(srv.port)
            reply = browser.post(f"/login?token={fx.APPROVER.value}", {"token": fx.APPROVER.value})
            if reply.status != 400 or browser.cookies:
                problems.append(f"질의 토큰 POST: {reply.status} · 쿠키 {bool(browser.cookies)}")
            statuses = [browser.post("/login", {"token": "w" * 40}).status for _ in range(5)]
            if statuses != [401] * 5:
                problems.append(f"틀린 토큰 5회: {statuses}")
            reply = browser.login(fx.APPROVER)
            if reply.status != 429 or browser.cookies:
                problems.append(f"5회 실패 뒤 맞는 토큰: {reply.status} (기대 429)")
            reply = browser.post("/login", {"token": fx.APPROVER.value}, origin="http://evil.example")
            if reply.status != 403:
                problems.append(f"로그인 Origin 다름: {reply.status}")
            reply = fx.request(srv.port, "POST", "/login", body=b"token=" + b"x" * 4_100,
                               headers={"Origin": browser.origin, "Content-Type": "application/x-www-form-urlencoded"})
            if reply.status != 413:
                problems.append(f"로그인 본문 4,096 초과: {reply.status}")
        # 신뢰 프록시가 아닌 곳의 X-Forwarded-For 는 무시한다 — 머리를 바꿔도 같은 주소로 센다.
        with fx.running(ws) as srv:
            for i in range(5):
                fx.request(srv.port, "POST", "/login", body=b"token=" + b"w" * 40,
                           headers={"Origin": f"http://127.0.0.1:{srv.port}", "X-Forwarded-For": f"10.0.0.{i}",
                                    "Content-Type": "application/x-www-form-urlencoded"})
            reply = fx.Browser(srv.port).login(fx.APPROVER)
            if reply.status != 429:
                problems.append(f"신뢰하지 않는 X-Forwarded-For 로 실패 제한을 피했다: {reply.status}")
    return problems


def case_viewer() -> list[str]:
    problems: list[str] = []
    with fx.temp_workspace("wb-auth-7-") as td:
        ws = fx.make_workspace(td)
        task_id = fx.create_task(ws)
        with fx.running(ws) as srv:
            approver = fx.Browser(srv.port)
            approver.login(fx.APPROVER)
            form = fx.respond_form(approver.get(f"/task/{task_id}").text)
            assert form is not None
            viewer = fx.Browser(srv.port)
            viewer.login(fx.VIEWER)
            page = viewer.get(f"/task/{task_id}")
            if page.status != 200 or fx.respond_form(page.text) is not None or 'type="radio"' in page.text:
                problems.append("viewer 화면에 응답 폼이 있다")
            fields = [(k, v) for k, v in form["fields"] if k != "csrf"]
            fields.append(("csrf", fx.csrf_of(page.text)))
            before = fx.inbox_snapshot(ws)
            reply = viewer.post(f"/task/{task_id}/respond", fields)
            if reply.status != 403:
                problems.append(f"viewer POST: {reply.status} (기대 403)")
            if fx.inbox_snapshot(ws) != before:
                problems.append("viewer POST 가 받은편지함을 바꿨다")
    return problems


def case_write_checks() -> list[str]:
    problems: list[str] = []
    with fx.temp_workspace("wb-auth-8-") as td:
        ws = fx.make_workspace(td)
        task_id = fx.create_task(ws)
        with fx.running(ws) as srv:
            browser = fx.Browser(srv.port)
            browser.login(fx.APPROVER)
            form = fx.respond_form(browser.get(f"/task/{task_id}").text)
            assert form is not None
            action = f"/task/{task_id}/respond"
            good = form["fields"]
            before = fx.inbox_snapshot(ws)
            cookie = browser._cookie_header(action)
            body = "&".join(f"{k}={v}" for k, v in good).encode()
            attempts = [
                ("Content-Length 없음", 411, lambda: _raw_post(srv.port, action, body, {**cookie, "Origin": browser.origin},
                                                             length=False)),
                ("본문 한도", 413, lambda: _raw_post(srv.port, action, b"x", {**cookie, "Origin": browser.origin},
                                                  length=262_145)),
                ("세션 없음", 401, lambda: fx.Browser(srv.port).post(action, good)),
                ("Origin 없음", 403, lambda: browser.post(action, good, origin=None)),
                ("Origin 다름", 403, lambda: browser.post(action, good, origin="http://127.0.0.1:1")),
                ("CSRF 다름", 403, lambda: browser.post(action, [(k, "x" if k == "csrf" else v) for k, v in good])),
                ("CSRF 없음", 403, lambda: browser.post(action, [(k, v) for k, v in good if k != "csrf"])),
            ]
            for label, status, attempt in attempts:
                reply = attempt()
                if reply.status != status:
                    problems.append(f"{label}: {reply.status} (기대 {status})")
                if fx.inbox_snapshot(ws) != before:
                    problems.append(f"{label}: 받은편지함이 바뀌었다")
            reply = browser.post(action, good, origin="http://127.0.0.1:1")
            if browser.origin not in reply.text:
                problems.append("Origin 403 화면에 기대하는 출처가 없다")
            reply = browser.post(action, good)
            if reply.status != 303 or len(fx.inbox_snapshot(ws)) != 1:
                problems.append(f"맞는 요청이 통하지 않는다: {reply.status}")
    return problems


def _raw_post(port: int, path: str, body: bytes, headers: dict[str, str], *, length: int | bool = True) -> fx.Reply:
    """``http.client`` 는 Content-Length 를 스스로 붙인다 — 머리를 손으로 쓴다."""
    lines = [f"POST {path} HTTP/1.1", f"Host: 127.0.0.1:{port}", "Content-Type: application/x-www-form-urlencoded",
             *(f"{k}: {v}" for k, v in headers.items())]
    if length is True:
        lines.append(f"Content-Length: {len(body)}")
    elif length is not False:
        lines.append(f"Content-Length: {length}")
    raw = ("\r\n".join(lines) + "\r\n\r\n").encode() + (body if length is True else b"")
    with socket.create_connection(("127.0.0.1", port), timeout=10) as sock:
        sock.sendall(raw)
        if length is False:
            sock.shutdown(socket.SHUT_WR)
        data = b""
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            chunk = sock.recv(65536)
            if not chunk:
                break
            data += chunk
    head, _, rest = data.partition(b"\r\n\r\n")
    status = int(head.split(b" ", 2)[1]) if head else 0
    headers_out: dict[str, list[str]] = {}
    for line in head.split(b"\r\n")[1:]:
        key, _, value = line.decode("latin-1").partition(":")
        headers_out.setdefault(key.strip().lower(), []).append(value.strip())
    return fx.Reply(status, headers_out, rest)


def _cookie_attrs(reply: fx.Reply) -> dict[str, str]:
    raw = reply.header("set-cookie") or ""
    parts = [p.strip() for p in raw.split(";")]
    attrs = {p.split("=", 1)[0].lower(): (p.split("=", 1)[1] if "=" in p else "") for p in parts[1:]}
    return attrs


def case_cookies() -> list[str]:
    problems: list[str] = []
    with fx.temp_workspace("wb-auth-9-") as td:
        ws = fx.make_workspace(td)
        for public, path, secure in ((None, "/", False), ("http://127.0.0.1:{port}/wb/", "/wb/", False),
                                     ("https://example.test/pre/fix/", "/pre/fix/", True)):
            with fx.running(ws) as srv:
                if public:
                    srv.app.public_url = public.format(port=srv.port)
                origin = server.origin_of(srv.app.public_url)
                browser = fx.Browser(srv.port, origin=origin)
                reply = browser.login(fx.APPROVER)
                attrs = _cookie_attrs(reply)
                want = {"httponly": "", "samesite": "Lax", "path": path}
                for key, value in want.items():
                    if attrs.get(key) != value:
                        problems.append(f"{public or '기본'}: 쿠키 {key} = {attrs.get(key)!r} (기대 {value!r})")
                if ("secure" in attrs) != secure:
                    problems.append(f"{public or '기본'}: Secure 가 {'없다' if secure else '붙었다'}")
                if reply.header("location") != "./":
                    problems.append(f"{public or '기본'}: 로그인 뒤 Location {reply.header('location')!r}")
        # 로그아웃 — CSRF 를 대조하고, 나간 세션은 다시 쓰이지 않는다.
        with fx.running(ws) as srv:
            browser = fx.Browser(srv.port)
            browser.login(fx.APPROVER)
            csrf = fx.csrf_of(browser.get("/").text)
            if browser.post("/logout", {"csrf": "x"}).status != 403:
                problems.append("로그아웃이 CSRF 를 대조하지 않는다")
            sid = browser.cookies["wb_session"][0]
            reply = browser.post("/logout", {"csrf": csrf})
            if reply.status != 303 or reply.header("location") != "./login":
                problems.append(f"로그아웃: {reply.status} {reply.header('location')}")
            again = fx.request(srv.port, "GET", "/", headers={"Cookie": f"wb_session={sid}"})
            if again.status != 303:
                problems.append("로그아웃한 세션이 아직 통한다")
    return problems


def case_access_log() -> list[str]:
    problems: list[str] = []
    with fx.temp_workspace("wb-auth-10-") as td:
        ws = fx.make_workspace(td)
        task_id = fx.create_task(ws)
        with fx.running(ws) as srv:
            browser = fx.Browser(srv.port)
            browser.login(fx.APPROVER)
            fx.submit(browser, f"/task/{task_id}", extra_fields=[("comment_-", "비밀주석문장")])
            logs = "\n".join(srv.logs)
            sid = browser.cookies["wb_session"][0]
            csrf = fx.csrf_of(browser.get("/").text)
            for label, secret in (("토큰", fx.APPROVER.value), ("쿠키", sid), ("CSRF", csrf), ("폼 본문", "비밀주석문장")):
                if secret in logs:
                    problems.append(f"접근 기록에 {label} 가 있다")
            if f"POST /task/{task_id}/respond 303 alice" not in logs:
                problems.append(f"접근 기록에 메서드 · 경로 · 상태 · 사용자가 없다: {srv.logs[-3:]}")
    return problems


def case_clocks() -> list[str]:
    """시간이 지나면 풀리는 것들 — 세션 12시간 · 실패 창 60초 · 차단 60초 (시계를 바꿔 끼운다)."""
    problems: list[str] = []
    with fx.temp_workspace("wb-auth-11-") as td:
        ws = fx.make_workspace(td)
        now = [1000.0]
        clock = lambda: now[0]  # noqa: E731
        with fx.running(ws) as srv:
            srv.app.sessions = wb_cli.auth.Sessions(clock=clock)
            srv.app.limiter = wb_cli.auth.LoginLimiter(clock=clock)
            browser = fx.Browser(srv.port)
            browser.login(fx.APPROVER)
            now[0] += 12 * 3600 - 1
            if browser.get("/").status != 200:
                problems.append("세션이 12시간 전에 끝났다")
            now[0] += 2
            if browser.get("/").status != 303:
                problems.append("세션이 12시간 뒤에도 살아 있다")
            other = fx.Browser(srv.port)
            for _ in range(5):
                other.post("/login", {"token": "w" * 40})
            if other.login(fx.APPROVER).status != 429:
                problems.append("5회 실패 뒤 막히지 않았다")
            now[0] += 59
            if other.login(fx.APPROVER).status != 429:
                problems.append("차단이 60초 전에 풀렸다")
            now[0] += 2
            if other.login(fx.APPROVER).status != 303:
                problems.append("차단이 60초 뒤에도 풀리지 않았다")
            third = fx.Browser(srv.port)
            for _ in range(4):
                third.post("/login", {"token": "w" * 40})
            now[0] += 61  # 창 밖으로 — 앞의 4회는 세지 않는다
            third.post("/login", {"token": "w" * 40})
            if third.login(fx.APPROVER).status != 303:
                problems.append("60초 창 밖의 실패까지 세어 막았다")
            # 로그아웃도 Origin 을 대조한다 — 다른 출처면 세션이 그대로다.
            csrf = fx.csrf_of(third.get("/").text)
            if third.post("/logout", {"csrf": csrf}, origin="http://other.example").status != 403:
                problems.append("로그아웃이 Origin 을 대조하지 않는다")
            if third.get("/").status != 200:
                problems.append("다른 출처의 로그아웃이 세션을 끝냈다")
    return problems


def case_write_order() -> list[str]:
    """§5.4 의 순서 — 앞 단계의 실패가 뒤 단계보다 먼저 보고된다."""
    problems: list[str] = []
    with fx.temp_workspace("wb-auth-12-") as td:
        ws = fx.make_workspace(td)
        task_id = fx.create_task(ws)
        action = f"/task/{task_id}/respond"
        with fx.running(ws) as srv:
            origin = f"http://127.0.0.1:{srv.port}"
            reply = _raw_post(srv.port, action, b"x", {"Origin": "http://evil.example"}, length=262_145)
            if reply.status != 413:
                problems.append(f"세션 없음 + 본문 한도 초과: {reply.status} (기대 413 — 길이가 먼저)")
            reply = fx.Browser(srv.port).post(action, {"csrf": "x"}, origin="http://evil.example")
            if reply.status != 401:
                problems.append(f"세션 없음 + 다른 Origin: {reply.status} (기대 401 — 세션이 Origin 보다 먼저)")
            viewer = fx.Browser(srv.port)
            viewer.login(fx.VIEWER)
            reply = viewer.post(action, {"csrf": "x"}, origin="http://evil.example")
            if reply.status != 403 or "approver" not in reply.text:
                problems.append(f"viewer + 다른 Origin: {reply.status} — 역할 거절이 먼저여야 한다")
            approver = fx.Browser(srv.port)
            approver.login(fx.APPROVER)
            reply = approver.post(action, {"csrf": "x"}, origin="http://evil.example")
            if reply.status != 403 or origin not in reply.text:
                problems.append(f"approver + 다른 Origin + 틀린 CSRF: {reply.status} — Origin 거절이 CSRF 보다 먼저여야 한다")
            # 인증 전에는 본문을 읽지 않는다 — 머리만 보낸 세션 없는 요청에 곧바로 401 이 와야 한다.
            with socket.create_connection(("127.0.0.1", srv.port), timeout=5) as sock:
                sock.sendall((f"POST {action} HTTP/1.1\r\nHost: x\r\nOrigin: {origin}\r\n"
                              "Content-Type: application/x-www-form-urlencoded\r\nContent-Length: 1000\r\n\r\n").encode())
                try:
                    head = sock.recv(64)
                except socket.timeout:
                    head = b""
            if not head.startswith(b"HTTP/1.1 401"):
                problems.append(f"세션 없는 요청의 본문을 기다렸다 (인증 전에 본문을 읽는다): {head[:30]!r}")
            if fx.inbox_snapshot(ws):
                problems.append("거절된 요청이 받은편지함에 썼다")
            notes = wb_cli.startup_warnings("0.0.0.0")
            if len(notes) != 1 or "loopback" not in notes[0] or wb_cli.startup_warnings("127.0.0.1"):
                problems.append(f"비 loopback bind 경고가 한 줄이 아니다: {notes}")
    return problems


CASES = (
    ("1 시작 거절 — rc 2 · 이유 한 줄 · 기록 무변경", case_start_refusals),
    ("2 수명 — 실행 기록 · 자기 무시 .gitignore · --status · 임시 파일 청소 · 종료", case_lifecycle),
    ("3 --new-token — 0600 · 값 비출력 · 덮지 않음", case_new_token),
    ("4 경로 표 밖 404 · 모든 응답의 §4.2 머리", case_routes_and_headers),
    ("5 세션 없는 요청 — 303 login (상대) · api 401", case_no_session),
    ("6 질의 토큰 400 · 로그인 실패 제한 429", case_login_limits),
    ("7 viewer — 폼 없음 · POST 403 · 받은편지함 무변경", case_viewer),
    ("8 §5.4 네 단계 — 어긋난 요청은 받은편지함을 바꾸지 않는다", case_write_checks),
    ("9 쿠키 속성 · 로그아웃", case_cookies),
    ("10 접근 기록에 비밀이 없다", case_access_log),
    ("11 시간 — 세션 12시간 · 실패 창 · 차단 60초 · 로그아웃 Origin", case_clocks),
    ("12 §5.4 순서 — 길이 → 세션 · 역할 → Origin → CSRF", case_write_order),
)


def main() -> int:
    print("check_workbench_auth — 워크벤치 명령 · 인증 · 머리 (plan_workbench_spec §2~§5)")
    for name, case in CASES:
        try:
            _record(name, case())
        except Exception:  # noqa: BLE001 — case 하나의 예외는 그 case 의 FAIL 이다
            _record(name, ["예외: " + traceback.format_exc().strip().splitlines()[-1]])
            traceback.print_exc()
    print(f"\n{len(CASES) - len(FAILURES)}/{len(CASES)} PASS")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
