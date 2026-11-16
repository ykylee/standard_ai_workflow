#!/usr/bin/env python3
"""워크벤치 개방 모드 `--open NAME` — 토큰 · 로그인 없이 IP 로 보고 답한다 (`core/plan_workbench_spec.md` §5.6).

1. 시작 — `--open` 은 loopback 밖 bind 를 TLS · `--allow-plain-http` 없이 받고 경고는 한 줄이다;
   `--open` + `--token` · 이름 문법 위반은 rc 2; CLI 로 띄우면 URL 을 내고 `--status` 가 running
2. 쿠키 없는 GET — 진척 · 계획 화면 · api 가 200 이고 세션 쿠키를 준다; 계획 화면에 응답 폼, 로그아웃 폼은 없다;
   `login` · `logout` 은 303 `./`
3. 제출 — 브라우저가 연 주소(Host)의 Origin 은 통과해 받은편지함에 `responder: NAME` · `client: <접속 주소>` 응답을 쓰고,
   `plan-import --apply` 가 반영한다; 다른 Origin 은 403 · 받은편지함 무변경
4. 토큰 모드는 그대로 — Host 기준 Origin 은 403, 세션 없는 화면은 303 ./login, 응답 파일에 `client` 줄이 없다
5. 접속 주소 정리 — 신뢰 프록시의 `X-Forwarded-For` 가 주소 문자 밖이면 `client: unknown`
6. DNS rebinding — `Host` 와 `Origin` 이 같은 다른 이름(`attacker.example`)이면 403 · 받은편지함 무변경;
   `localhost` 와 `public_url` 의 호스트 이름은 통과
7. 세션 상한 — 쿠키 없는 GET 을 상한보다 많이 보내도 세션 표가 상한을 넘지 않고, 살아 있는 세션은 남는다
8. `Origin: null` — 개방 · 토큰 모드 모두 403 · 받은편지함 무변경; 화면의 `Referrer-Policy` 는 `no-referrer` 가 아니다
   (`no-referrer` 면 브라우저가 폼 POST 에 Origin null 을 실어 정상 제출이 막힌다 — TASK-2026-11-16-main-007)
"""

from __future__ import annotations

#: 서버 subprocess 와 `plan-import` subprocess 를 돈다.
CHECK_TIMEOUT_S = 180

#: 이 검사의 입력 표면 (spec `core/test_impact_tiering_spec.md` §2).
WATCHES = (
    "workflow-source/pyproject.toml",
    "workflow-source/workflow_kit/*",
    "workflow-source/tests/_workbench_fixture.py",
)

import argparse
import json
import signal
import subprocess
import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _workbench_fixture as fx  # noqa: E402
from workflow_kit.common import plan_claims as pc  # noqa: E402
from workflow_kit.common import plan_responses as pr  # noqa: E402
from workflow_kit.common import plan_tasks  # noqa: E402
from workflow_kit.tools import workbench as wb_cli  # noqa: E402
from workflow_kit.workbench import auth  # noqa: E402

FAILURES: list[str] = []
OPEN_NAME = "owner"


def _record(name: str, problems: list[str]) -> None:
    if problems:
        FAILURES.append(name)
        print(f"  FAIL  {name}")
        for problem in problems[:12]:
            print(f"        - {problem}")
    else:
        print(f"  PASS  {name}")


def _args(*argv: str) -> argparse.Namespace:
    return wb_cli.build_parser().parse_args(list(argv))


def _wb(ws: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "workflow_kit", "workbench", "--project-profile-path", str(fx.profile(ws)), *args],
        capture_output=True, encoding="utf-8", errors="replace", check=False, env=fx.env(), cwd=str(ws), timeout=60)


def _task(ws: Path, task_id: str) -> plan_tasks.TaskPlan:
    task = plan_tasks.read_task_plan(fx.branch_dir(ws) / "backlog" / "tasks" / f"{task_id}.md")
    assert task is not None
    return task


def _inbox_text(ws: Path) -> list[str]:
    inbox = pr.inbox_dir(fx.branch_dir(ws))
    return [(inbox / name).read_text(encoding="utf-8") for name in fx.inbox_snapshot(ws)]


def case_start() -> list[str]:
    problems: list[str] = []
    with fx.temp_workspace("wb-open-1-") as td:
        ws = fx.make_workspace(td)
        # 판정만 잰다 — 이 검사가 네트워크에 포트를 열지 않게 loopback 밖 bind 는 실제로 하지 않는다.
        try:
            tokens, url = wb_cli.validate_start(_args("--open", OPEN_NAME, "--bind", "0.0.0.0", "--port", "8799"), ws)
            if tokens:
                problems.append(f"개방 모드에 토큰이 실렸다: {tokens}")
            if not url.startswith("http://") or not url.endswith(":8799/"):
                problems.append(f"개방 모드 기본 public_url 이 http://<주소>:8799/ 가 아니다: {url}")
        except wb_cli.StartRefused as exc:
            problems.append(f"--open --bind 0.0.0.0 을 거절했다: {exc}")
        try:
            _, url = wb_cli.validate_start(_args("--open", OPEN_NAME, "--bind", "10.1.2.3", "--port", "8799"), ws)
            if url != "http://10.1.2.3:8799/":
                problems.append(f"특정 주소 bind 의 기본 public_url 이 그 주소가 아니다: {url}")
        except wb_cli.StartRefused as exc:
            problems.append(f"--open --bind 10.1.2.3 을 거절했다: {exc}")
        for label, argv, needle in (
            ("--open + --token", ("--open", OPEN_NAME, "--token", "approver:a=env:X"), "같이"),
            ("이름 문법", ("--open", "a b"), "이름은"),
            ("토큰 모드 비 loopback 평문", ("--token", "approver:a=env:WB_NONE", "--bind", "0.0.0.0"), ""),
        ):
            try:
                wb_cli.validate_start(_args(*argv), ws)
                problems.append(f"{label}: 거절하지 않았다")
            except wb_cli.StartRefused as exc:
                if needle not in str(exc):
                    problems.append(f"{label}: 이유에 `{needle}` 이 없다: {exc}")
        notes = wb_cli.startup_warnings("0.0.0.0", open_name=OPEN_NAME)
        if len(notes) != 1 or "인증 없이" not in notes[0] or "0.0.0.0" not in notes[0]:
            problems.append(f"개방 모드 비 loopback 경고가 한 줄이 아니다: {notes}")
        if len(wb_cli.startup_warnings("127.0.0.1", open_name=OPEN_NAME)) != 1:
            problems.append("loopback 개방 모드에도 인증 없음 경고 한 줄이 있어야 한다")
        # CLI 경로 — loopback 에 띄워 URL · 경고 · --status 를 잰다.
        proc = subprocess.Popen(
            [sys.executable, "-m", "workflow_kit", "workbench", "--project-profile-path", str(fx.profile(ws)),
             "--open", OPEN_NAME, "--port", "0"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding="utf-8", env=fx.env(), cwd=str(ws))
        try:
            assert proc.stdout is not None and proc.stderr is not None
            url = proc.stdout.readline().strip()
            warning = proc.stderr.readline().strip()
            if not url.startswith("http://127.0.0.1:"):
                problems.append(f"CLI 개방 모드가 URL 을 내지 않았다: {url!r}")
            if "인증 없이" not in warning:
                problems.append(f"CLI 개방 모드 경고가 없다: {warning!r}")
            status = json.loads(_wb(ws, "--status").stdout)
            if status.get("running") is not True or status.get("public_url") != url:
                problems.append(f"--status 가 개방 모드 서버를 보이지 않는다: {status}")
            port = int(status["port"])
            home = fx.request(port, "GET", "/")
            if home.status != 200:
                problems.append(f"CLI 개방 모드 서버의 GET / 가 {home.status} 다")
        finally:
            proc.send_signal(signal.SIGTERM)
            try:
                proc.wait(timeout=15)
            except subprocess.TimeoutExpired:
                proc.kill()
                problems.append("SIGTERM 에 끝나지 않았다")
    return problems


def case_no_login() -> list[str]:
    problems: list[str] = []
    with fx.temp_workspace("wb-open-2-") as td:
        ws = fx.make_workspace(td)
        task_id = fx.create_task(ws)
        with fx.running(ws, tokens=(), open_name=OPEN_NAME) as srv:
            for path in ("/", f"/task/{task_id}", "/api/state"):
                reply = fx.request(srv.port, "GET", path)
                if reply.status != 200:
                    problems.append(f"쿠키 없는 GET {path} 가 {reply.status} 다")
                elif "wb_session=" not in (reply.header("Set-Cookie") or ""):
                    problems.append(f"쿠키 없는 GET {path} 가 세션 쿠키를 주지 않았다")
            page = fx.request(srv.port, "GET", f"/task/{task_id}")
            if fx.respond_form(page.text) is None:
                problems.append("개방 모드 계획 화면에 응답 폼이 없다")
            if 'action="../logout"' in page.text or "로그아웃" in page.text:
                problems.append("개방 모드 화면에 로그아웃 폼이 있다")
            if OPEN_NAME not in page.text:
                problems.append("개방 모드 화면 머리에 응답자 이름이 없다")
            for method, path in (("GET", "/login"), ("POST", "/login"), ("POST", "/logout")):
                reply = fx.request(srv.port, method, path, body=b"" if method == "POST" else None,
                                   headers={"Content-Length": "0"} if method == "POST" else None)
                if reply.status != 303 or reply.header("Location") != "./":
                    problems.append(f"개방 모드 {method} {path}: {reply.status} {reply.header('Location')} (기대 303 ./)")
    return problems


def case_submit() -> list[str]:
    problems: list[str] = []
    with fx.temp_workspace("wb-open-3-") as td:
        ws = fx.make_workspace(td)
        task_id = fx.create_task(ws)
        with fx.running(ws, tokens=(), open_name=OPEN_NAME) as srv:
            # 다른 기기가 IP 로 연 모양 — Host 와 Origin 이 public_url(127.0.0.1) 과 다르다.
            lan = f"192.168.77.9:{srv.port}"
            evil = fx.Browser(srv.port, origin="http://evil.example")
            evil.get(f"/task/{task_id}")
            reply, _ = fx.submit(evil, f"/task/{task_id}", overrides={"value_D1": "warn"})
            if reply.status != 403 or fx.inbox_snapshot(ws):
                problems.append(f"다른 Origin 의 제출: {reply.status} · 받은편지함 {list(fx.inbox_snapshot(ws))}")
            browser = fx.Browser(srv.port, origin=f"http://{lan}")
            page = browser.get(f"/task/{task_id}")
            form = fx.respond_form(page.text)
            if form is None:
                return problems + ["계획 화면에 응답 폼이 없다"]
            fields = [(k, v) for k, v in form["fields"] if k != "value_D1"] + [("value_D1", "warn")]
            reply = browser.post(fx.resolve(f"/task/{task_id}", form["action"]), fields, extra={"Host": lan})
            if reply.status != 303:
                problems.append(f"Host 기준 Origin 의 제출이 303 이 아니다: {reply.status} {reply.text[:200]}")
        texts = _inbox_text(ws)
        if len(texts) != 1:
            return problems + [f"받은편지함에 응답이 1건이 아니다: {len(texts)}"]
        if f"\nresponder: {OPEN_NAME}\n" not in texts[0] or "\nclient: 127.0.0.1\n" not in texts[0]:
            problems.append(f"응답 머리에 responder · client 가 없다: {texts[0][:300]!r}")
        rc, out = fx.plan_import(ws, "--task", task_id, "--apply")
        verdicts = out.get("responses") or out.get("inbox") or []
        if rc != 0 or not any(v.get("eligible") for v in verdicts):
            problems.append(f"plan-import 가 개방 모드 응답을 자격 있게 보지 않았다: rc {rc} {str(out)[:300]}")
        states = plan_tasks.computed_states(_task(ws, task_id)).states
        if states.get("D1") != f"{pc.STATE_CHANGED}:warn":
            problems.append(f"결정 상태가 응답을 반영하지 않았다: {states}")
    return problems


def case_token_mode_unchanged() -> list[str]:
    problems: list[str] = []
    with fx.temp_workspace("wb-open-4-") as td:
        ws = fx.make_workspace(td)
        task_id = fx.create_task(ws)
        with fx.running(ws) as srv:
            reply = fx.request(srv.port, "GET", "/")
            if reply.status != 303 or reply.header("Location") != "./login":
                problems.append(f"토큰 모드 세션 없는 GET / 가 303 login 이 아니다: {reply.status} {reply.header('Location')}")
            lan = f"192.168.77.9:{srv.port}"
            browser = fx.Browser(srv.port, origin=f"http://{lan}")
            login = fx.Browser(srv.port)
            login.login(fx.APPROVER)
            browser.cookies = login.cookies
            page = browser.get(f"/task/{task_id}")
            form = fx.respond_form(page.text)
            if form is None:
                return problems + ["토큰 모드 계획 화면에 응답 폼이 없다"]
            reply = browser.post(fx.resolve(f"/task/{task_id}", form["action"]), form["fields"], extra={"Host": lan})
            if reply.status != 403 or fx.inbox_snapshot(ws):
                problems.append(f"토큰 모드가 Host 기준 Origin 을 받았다: {reply.status}")
            reply, _ = fx.submit(login, f"/task/{task_id}")
            if reply.status != 303:
                problems.append(f"토큰 모드 정상 제출이 {reply.status} 다")
        texts = _inbox_text(ws)
        if len(texts) != 1 or "\nclient:" in texts[0] or f"\nresponder: {fx.APPROVER.name}\n" not in texts[0]:
            problems.append(f"토큰 모드 응답 머리가 바뀌었다: {[t[:200] for t in texts]}")
    return problems


def case_client_sanitized() -> list[str]:
    problems: list[str] = []
    with fx.temp_workspace("wb-open-5-") as td:
        ws = fx.make_workspace(td)
        task_id = fx.create_task(ws)
        with fx.running(ws, tokens=(), open_name=OPEN_NAME, trusted_proxies=frozenset({"127.0.0.1"})) as srv:
            browser = fx.Browser(srv.port)
            page = browser.get(f"/task/{task_id}")
            form = fx.respond_form(page.text)
            if form is None:
                return ["계획 화면에 응답 폼이 없다"]
            reply = browser.post(fx.resolve(f"/task/{task_id}", form["action"]), form["fields"],
                                 extra={"X-Forwarded-For": "1.2.3.4 <script>"})
            if reply.status != 303:
                problems.append(f"제출이 {reply.status} 다")
        texts = _inbox_text(ws)
        if len(texts) != 1 or "\nclient: unknown\n" not in texts[0]:
            problems.append(f"주소 문자 밖 X-Forwarded-For 가 정리되지 않았다: {[t[:300] for t in texts]}")
    return problems


def _submit_as(srv: fx.Running, task_id: str, host: str) -> int:
    browser = fx.Browser(srv.port, origin=f"http://{host}")
    page = browser.get(f"/task/{task_id}")
    form = fx.respond_form(page.text)
    if form is None:
        raise AssertionError("계획 화면에 응답 폼이 없다")
    return browser.post(fx.resolve(f"/task/{task_id}", form["action"]), form["fields"], extra={"Host": host}).status


def case_dns_rebinding() -> list[str]:
    problems: list[str] = []
    with fx.temp_workspace("wb-open-6-") as td:
        ws = fx.make_workspace(td)
        task_id = fx.create_task(ws)
        with fx.running(ws, tokens=(), open_name=OPEN_NAME, public_url="http://wb.lan:9/") as srv:
            status = _submit_as(srv, task_id, f"attacker.example:{srv.port}")
            if status != 403 or fx.inbox_snapshot(ws):
                problems.append(f"다른 이름의 Host+Origin 제출이 {status} 다 — DNS rebinding 이 통과한다")
            for host in (f"localhost:{srv.port}", f"wb.lan:{srv.port}", f"[::1]:{srv.port}"):
                before = len(fx.inbox_snapshot(ws))
                status = _submit_as(srv, task_id, host)
                if status != 303 or len(fx.inbox_snapshot(ws)) != before + 1:
                    problems.append(f"Host {host} 의 제출이 {status} 다 (기대 303)")
    return problems


def case_session_cap() -> list[str]:
    problems: list[str] = []
    clock = [0.0]
    table = auth.Sessions(ttl_s=100, clock=lambda: clock[0], max_sessions=8)
    keep = table.create(auth.Token(auth.ROLE_APPROVER, OPEN_NAME, ""))
    clock[0] = 50.0
    for _ in range(30):
        table.create(auth.Token(auth.ROLE_APPROVER, OPEN_NAME, ""))
    if len(table) > 8:
        problems.append(f"세션 표가 상한 8 을 넘었다: {len(table)}")
    if table.get(keep.sid) is not None:
        problems.append("상한을 넘겼는데 만료가 가장 이른 세션을 버리지 않았다")
    with fx.temp_workspace("wb-open-7-") as td:
        ws = fx.make_workspace(td)
        with fx.running(ws, tokens=(), open_name=OPEN_NAME) as srv:
            for _ in range(auth.MAX_SESSIONS + 50):
                srv.app.sessions.create(auth.Token(auth.ROLE_APPROVER, OPEN_NAME, ""))
            fx.request(srv.port, "GET", "/")
            if len(srv.app.sessions) > auth.MAX_SESSIONS:
                problems.append(f"서버 세션 표가 상한 {auth.MAX_SESSIONS} 를 넘었다: {len(srv.app.sessions)}")
    return problems


def case_null_origin() -> list[str]:
    problems: list[str] = []
    for label, kwargs in (("개방", {"tokens": (), "open_name": OPEN_NAME}), ("토큰", {})):
        with fx.temp_workspace("wb-open-8-") as td:
            ws = fx.make_workspace(td)
            task_id = fx.create_task(ws)
            with fx.running(ws, **kwargs) as srv:  # type: ignore[arg-type]
                browser = fx.Browser(srv.port, origin="null")
                if label == "토큰":
                    login = fx.Browser(srv.port)
                    login.login(fx.APPROVER)
                    browser.cookies = login.cookies
                page = browser.get(f"/task/{task_id}")
                policy = page.header("Referrer-Policy") or ""
                if policy == "no-referrer" or not policy:
                    problems.append(f"{label}: Referrer-Policy 가 {policy!r} — 브라우저가 폼 POST 에 Origin null 을 싣는다")
                reply, _ = fx.submit(browser, f"/task/{task_id}")
                if reply.status != 403 or fx.inbox_snapshot(ws):
                    problems.append(f"{label}: Origin null 제출이 {reply.status} · 받은편지함 {list(fx.inbox_snapshot(ws))}")
    return problems


CASES = (
    ("1 시작 — 비 loopback 평문 허용 · 경고 한 줄 · 거절 · CLI", case_start),
    ("2 쿠키 없는 GET 200 · 응답 폼 · 로그아웃 없음 · login 303", case_no_login),
    ("3 Host 기준 Origin 제출 · responder/client · plan-import 반영 · 다른 Origin 403", case_submit),
    ("4 토큰 모드 그대로", case_token_mode_unchanged),
    ("5 접속 주소 정리", case_client_sanitized),
    ("6 DNS rebinding — 다른 이름의 Host 403", case_dns_rebinding),
    ("7 세션 표 상한", case_session_cap),
    ("8 Origin null 403 · Referrer-Policy 는 no-referrer 가 아니다", case_null_origin),
)


def main() -> int:
    print("check_workbench_open — 워크벤치 개방 모드 (plan_workbench_spec §5.6)")
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
