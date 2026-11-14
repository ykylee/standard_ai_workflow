#!/usr/bin/env python3
"""워크벤치 — 접두사를 벗기는 리버스 프록시 뒤 (`core/plan_workbench_spec.md` §4.3 · §9 · §11).

검사 안의 작은 프록시가 ``/wb/…`` 만 받아 접두사를 벗겨 서버로 넘긴다. 실물 nginx · Caddy 처럼 `Location` 과
`Set-Cookie` 를 고치지 않는다 (requirements §1.4 의 측정 구성). 판정은 **도착 경로**다 — 브라우저가 따라간
경로가 전부 접두사 안이고, 프록시가 접두사 밖 요청을 한 번도 받지 않았다.

1. 로그인 → 진척 → 계획 → 제출 → 도착 → 정적 자원 → 로그아웃이 전부 접두사 안이고 쿠키 `Path` 가 접두사다
2. `X-Forwarded-For` 는 신뢰 프록시에서 온 요청만 쓴다 — 실패 제한이 프록시 뒤 클라이언트 주소별로 걸린다
"""

from __future__ import annotations

#: 이 검사의 입력 표면 (spec `core/test_impact_tiering_spec.md` §2).
WATCHES = (
    "workflow-source/pyproject.toml",
    "workflow-source/workflow_kit/*",
    "workflow-source/tests/_workbench_fixture.py",
)

import http.client
import sys
import threading
import traceback
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Iterator

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _workbench_fixture as fx  # noqa: E402

FAILURES: list[str] = []
PREFIX = "/wb/"


def _record(name: str, problems: list[str]) -> None:
    if problems:
        FAILURES.append(name)
        print(f"  FAIL  {name}")
        for problem in problems[:12]:
            print(f"        - {problem}")
    else:
        print(f"  PASS  {name}")


@contextmanager
def prefix_proxy(backend_port: int, *, client_ip: str = "") -> Iterator[tuple[int, list[str]]]:
    """``/wb/<rest>`` → 서버 ``/<rest>``. 접두사 밖은 404 로 끝내고 기록한다. 머리는 그대로 넘긴다."""
    outside: list[str] = []

    class Proxy(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, format: str, *args: object) -> None:  # noqa: A002
            return

        def _forward(self) -> None:
            if not self.path.startswith(PREFIX):
                outside.append(f"{self.command} {self.path}")
                self.send_response(404)
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            length = int(self.headers.get("Content-Length") or 0)
            body = self.rfile.read(length) if length else None
            headers = {k: v for k, v in self.headers.items() if k.lower() not in ("host", "connection")}
            if client_ip:
                headers["X-Forwarded-For"] = client_ip
            conn = http.client.HTTPConnection("127.0.0.1", backend_port, timeout=30)
            conn.request(self.command, "/" + self.path[len(PREFIX):], body=body, headers=headers)
            resp = conn.getresponse()
            data = resp.read()
            self.send_response(resp.status)
            for key, value in resp.getheaders():
                if key.lower() not in ("connection", "transfer-encoding", "content-length"):
                    self.send_header(key, value)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            conn.close()

        do_GET = _forward  # noqa: N815
        do_POST = _forward  # noqa: N815

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Proxy)
    thread = threading.Thread(target=httpd.serve_forever, kwargs={"poll_interval": 0.1}, daemon=True)
    thread.start()
    try:
        yield httpd.server_address[1], outside
    finally:
        httpd.shutdown()
        httpd.server_close()


def case_prefix_flow() -> list[str]:
    problems: list[str] = []
    with fx.temp_workspace("wb-proxy-1-") as td:
        ws = fx.make_workspace(td)
        task_id = fx.create_task(ws)
        with fx.running(ws) as srv, prefix_proxy(srv.port) as (proxy_port, outside):
            srv.app.public_url = f"http://127.0.0.1:{proxy_port}{PREFIX}"
            browser = fx.Browser(proxy_port)
            arrived: list[str] = []

            def follow(current: str, reply: fx.Reply) -> str:
                location = reply.header("location") or ""
                if not location or location.startswith(("http:", "https:", "/")):
                    problems.append(f"{current}: Location 이 상대 경로가 아니다: {location!r}")
                target = fx.resolve(current, location)
                arrived.append(target)
                return target

            reply = browser.get(PREFIX)
            login = follow(PREFIX, reply)
            reply = browser.get(login)
            if reply.status != 200:
                problems.append(f"로그인 화면 {login}: {reply.status}")
            reply = browser.post(login, {"token": fx.APPROVER.value})
            cookie_path = browser.cookies.get("wb_session", ("", ""))[1]
            if cookie_path != PREFIX:
                problems.append(f"쿠키 Path 가 접두사가 아니다: {cookie_path!r}")
            home = follow(login, reply)
            page = browser.get(home)
            if page.status != 200 or f'href="./task/{task_id}"' not in page.text:
                problems.append(f"진척 화면 {home}: {page.status} — 계획 링크가 상대 경로가 아니다")
            task_path = fx.resolve(home, f"./task/{task_id}")
            arrived.append(task_path)
            reply, action = fx.submit(browser, task_path, overrides={"value_D1": "warn"})
            arrived.append(action)
            if reply.status != 303:
                problems.append(f"제출 {action}: {reply.status} {reply.text[:200]}")
            landing = follow(action, reply)
            page = browser.get(landing)
            if page.status != 200 or "의 응답을" not in page.text:
                problems.append(f"도착 {landing}: {page.status} — 받았다는 줄이 없다")
            css = fx.resolve(landing, "../static/workbench.css")
            arrived.append(css)
            if 'href="../static/workbench.css"' not in page.text or browser.get(css).status != 200:
                problems.append(f"정적 자원이 접두사 안에서 열리지 않는다: {css}")
            reply = browser.post(fx.resolve(landing, "../logout"), {"csrf": fx.csrf_of(page.text)})
            follow(fx.resolve(landing, "../logout"), reply)
            outside_paths = [p for p in arrived + browser.seen if not p.startswith(PREFIX)]
            if outside_paths:
                problems.append(f"접두사 밖으로 나간 경로: {sorted(set(outside_paths))}")
            if outside:
                problems.append(f"프록시가 접두사 밖 요청을 받았다: {outside}")
            if len(fx.inbox_snapshot(ws)) != 1:
                problems.append("프록시 뒤 제출이 받은편지함에 닿지 않았다")
    return problems


def case_forwarded_for() -> list[str]:
    problems: list[str] = []
    with fx.temp_workspace("wb-proxy-2-") as td:
        ws = fx.make_workspace(td)
        # 신뢰 프록시 — 클라이언트 주소별로 센다: A 가 5회 실패해도 B 는 막히지 않는다.
        with fx.running(ws, trusted_proxies=frozenset({"127.0.0.1"})) as srv:
            with prefix_proxy(srv.port, client_ip="198.51.100.7") as (port_a, _):
                srv.app.public_url = f"http://127.0.0.1:{port_a}{PREFIX}"
                a = fx.Browser(port_a)
                for _ in range(5):
                    a.post(PREFIX + "login", {"token": "w" * 40})
                if a.post(PREFIX + "login", {"token": fx.APPROVER.value}).status != 429:
                    problems.append("신뢰 프록시 뒤 클라이언트 A 의 실패 제한이 걸리지 않았다")
            with prefix_proxy(srv.port, client_ip="198.51.100.8") as (port_b, _):
                srv.app.public_url = f"http://127.0.0.1:{port_b}{PREFIX}"
                b = fx.Browser(port_b)
                if b.post(PREFIX + "login", {"token": fx.APPROVER.value}).status != 303:
                    problems.append("다른 클라이언트 B 까지 막혔다 — X-Forwarded-For 를 쓰지 않았다")
    return problems


CASES = (
    ("1 접두사 프록시 뒤 로그인 → 계획 → 제출 → 도착이 전부 접두사 안 · 쿠키 Path = 접두사", case_prefix_flow),
    ("2 X-Forwarded-For 는 신뢰 프록시에서만 — 클라이언트별 실패 제한", case_forwarded_for),
)


def main() -> int:
    print("check_workbench_proxy — 접두사 프록시 뒤 경로 · 쿠키 (plan_workbench_spec §4.3 · §9)")
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
