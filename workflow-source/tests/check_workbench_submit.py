#!/usr/bin/env python3
"""워크벤치 쓰기 폼 제출 경로 (TASK-2026-11-17-claude-remote-sync-check-234c32-004).

iOS Chrome(CriOS 156 · iPadOS 27)이 워크벤치의 폼 제출 페이지 이동을 서버에 보내지 않고 버렸다 — submit 은
일어나는데 접속이 0 이었고, 같은 화면의 fetch POST 는 닿았다(실측). 진단 중 서버 결함 둘이 더 드러났다.

1. 스크립트 — POST 폼의 submit 을 가로채 fetch POST(같은 출처 쿠키 · urlencoded)로 보내고, 리다이렉트면 그 주소로
   가고, 오류 화면은 main 에 그린다. fetch 가 없으면 가로채지 않는다 (폼이 원래대로 간다)
2. 쓰기 요청은 응답 뒤 연결을 닫는다 — 본문을 읽지 않고 답하는 경로(경로 표 밖 404 · 개방 모드 로그인 · 로그아웃)가
   남긴 본문이 같은 연결의 다음 요청을 'probe=1GET …' 로 깨뜨리지 않는다
3. ``--stop`` 의 healthz 탐침이 비 loopback 바인드 주소로 간다 — 기록의 ``bind``, 없으면 ``public_url`` 의 호스트
4. 실행 기록이 수동 기동에도 ``bind`` 를 싣고, 자동 기동 표식은 붙이지 않는다

실제 iPad 동작은 게이트가 잴 수 없다 — task Proof 에 소유자 확인으로 남긴다.
"""

from __future__ import annotations

#: 이 검사의 입력 표면 (spec `core/test_impact_tiering_spec.md` §2).
WATCHES = (
    "workflow-source/pyproject.toml",
    "workflow-source/workflow_kit/*",
    "workflow-source/tests/_workbench_fixture.py",
)

import http.client
import json
import socket
import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _workbench_fixture as fx  # noqa: E402

from workflow_kit.tools import workbench as wb_tool  # noqa: E402

FAILURES: list[str] = []
JS = fx.SOURCE_ROOT / "workflow_kit" / "workbench" / "static" / "workbench.js"


def _record(name: str, problems: list[str]) -> None:
    if problems:
        FAILURES.append(name)
        print(f"  FAIL  {name}")
        for problem in problems[:12]:
            print(f"        - {problem}")
    else:
        print(f"  PASS  {name}")


def case_script() -> list[str]:
    problems: list[str] = []
    js = JS.read_text(encoding="utf-8")
    for needle, label in (
        ('document.addEventListener("submit"', "submit 가로채기"),
        ('!== "post"', "POST 폼만"),
        ("event.preventDefault();", "폼 이동을 막고"),
        ("if (!window.fetch || !window.FormData || !window.URLSearchParams) { return; }", "fetch 없으면 원래 폼대로"),
        ('new URL(form.getAttribute("action") || "", location.href).href', "주소는 action 속성에서"),
        ('method: "POST"', "fetch POST"),
        ('credentials: "same-origin"', "같은 출처 쿠키"),
        ('"Content-Type": "application/x-www-form-urlencoded"', "urlencoded 본문"),
        ("if (resp.redirected) { location.assign(resp.url);", "리다이렉트면 그 주소로"),
        ('main.innerHTML = next.innerHTML;\n          main.removeAttribute("data-version");', "오류 화면을 main 에"),
    ):
        if needle not in js:
            problems.append(f"workbench.js 에 {label} 이 없다 (`{needle[:50]}`)")
    # todo 폼의 <input name="action"> 이 form.action 을 가린다 — 주소로 쓰면 POST /task/[object HTMLInputElement] (실측)
    if "form.action" in js:
        problems.append("workbench.js 가 form.action 을 쓴다 — name=\"action\" 입력이 있는 폼에서 주소가 아니다")
    return problems


def _post_then_get(port: int, path: str, body: bytes) -> tuple[bytes, bytes | None]:
    """같은 연결로 POST(본문) 뒤 GET /healthz — (첫 응답, 두 번째 응답 또는 연결이 닫혀 None)."""
    sock = socket.create_connection(("127.0.0.1", port), timeout=10)
    try:
        host = f"127.0.0.1:{port}"
        sock.sendall(f"POST {path} HTTP/1.1\r\nHost: {host}\r\nOrigin: http://{host}\r\n"
                     f"Content-Type: application/x-www-form-urlencoded\r\nContent-Length: {len(body)}\r\n\r\n".encode()
                     + body)
        first = http.client.HTTPResponse(sock)
        first.begin()
        head = f"{first.status} connection={first.getheader('Connection')}".encode()
        first.read()
        try:
            sock.sendall(f"GET /healthz HTTP/1.1\r\nHost: {host}\r\n\r\n".encode())
            data = sock.recv(4096)
        except OSError:
            return head, None
        return head, (data or None)
    finally:
        sock.close()


def case_post_closes() -> list[str]:
    problems: list[str] = []
    with fx.temp_workspace("wb-submit-2-") as td:
        ws = fx.make_workspace(td)
        with fx.running(ws, open_name="owner") as srv:
            for path in ("/diagpost", "/login", "/logout"):
                head, second = _post_then_get(srv.port, path, b"probe=1")
                if b"connection=close" not in head:
                    problems.append(f"POST {path} 응답에 Connection: close 가 없다 ({head.decode()})")
                if second is not None:
                    problems.append(f"POST {path} 뒤 같은 연결의 다음 요청이 처리됐다: {second[:60]!r}")
            corrupted = [line for line in srv.logs if "probe=1" in line]
            if corrupted:
                problems.append(f"본문이 다음 요청 머리에 붙었다: {corrupted[:2]}")
    return problems


class _Recorder:
    hosts: list[str] = []

    def __init__(self, host: str, port: int, timeout: float = 0, **_: object) -> None:
        _Recorder.hosts.append(host)

    def request(self, *_: object, **__: object) -> None:
        raise OSError("탐침 기록용 — 접속하지 않는다")

    def close(self) -> None:
        return None


def case_stop_probe_hosts() -> list[str]:
    problems: list[str] = []
    original = wb_tool.http.client.HTTPConnection
    wb_tool.http.client.HTTPConnection = _Recorder  # type: ignore[misc,assignment]
    try:
        for record, expected in (
            ({"port": 1, "bind": "100.64.0.9", "public_url": "http://100.64.0.9:1/"}, ["100.64.0.9", "127.0.0.1"]),
            ({"port": 1, "public_url": "http://100.64.0.9:1/"}, ["100.64.0.9", "127.0.0.1"]),  # 1.26.0 이하 수동 기록
            ({"port": 1, "bind": "0.0.0.0", "public_url": "http://127.0.0.1:1/"}, ["127.0.0.1"]),
            ({"port": 1, "bind": "127.0.0.1", "public_url": "http://localhost:1/"}, ["127.0.0.1"]),
        ):
            _Recorder.hosts = []
            answers, _ = wb_tool._probe_healthz(record)
            if answers or _Recorder.hosts != expected:
                problems.append(f"{json.dumps(record)} → 탐침 {_Recorder.hosts} (기대 {expected})")
    finally:
        wb_tool.http.client.HTTPConnection = original  # type: ignore[misc]
    return problems


def case_record_bind() -> list[str]:
    problems: list[str] = []
    with fx.temp_workspace("wb-submit-4-") as td:
        ws = Path(td)
        path = wb_tool.write_record(ws, port=8767, public_url="http://100.64.0.9:8767/", bind="100.64.0.9",
                                    instance="x")
        record = json.loads(path.read_text(encoding="utf-8"))
        if record.get("bind") != "100.64.0.9":
            problems.append(f"수동 기동 기록에 bind 가 없다: {record}")
        if "autostarted" in record:
            problems.append(f"수동 기동 기록에 autostarted 가 붙었다: {record}")
        path = wb_tool.write_record(ws, port=8767, public_url="http://100.64.0.9:8767/", bind="100.64.0.9",
                                    autostarted_bind="100.64.0.9", instance="x")
        record = json.loads(path.read_text(encoding="utf-8"))
        if record.get("autostarted") is not True or record.get("bind") != "100.64.0.9":
            problems.append(f"자동 기동 기록이 바뀌었다: {record}")
    return problems


CASES = (
    ("1 스크립트 — POST 폼을 fetch 로 보낸다 · fetch 없으면 원래대로", case_script),
    ("2 쓰기 요청은 응답 뒤 연결을 닫는다 — 남은 본문이 다음 요청을 깨지 않는다", case_post_closes),
    ("3 --stop 탐침이 비 loopback 바인드 · public_url 호스트로 간다", case_stop_probe_hosts),
    ("4 실행 기록이 수동 기동에도 bind 를 싣는다", case_record_bind),
)


def main() -> int:
    print("check_workbench_submit — 워크벤치 쓰기 폼 제출 경로 (iPad Chrome 결함)")
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
