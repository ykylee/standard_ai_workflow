#!/usr/bin/env python3
"""워크벤치 화면 자동 새로고침 (`core/plan_workbench_spec.md` §4.5, TASK-2026-11-16-main-006).

1. 진척 · 계획 화면에 `<body data-refresh="N">` · 스크립트 · `<main data-version>` 이 있고, CSP 에 `connect-src 'self'` 가 있다
2. 지문 — 같은 상태 두 번 GET 의 `data-version` 이 같고, task 파일이 바뀌면(결정 상태) 달라진다
3. `refresh=0` 이면 `data-refresh` 가 없고 진척 화면에 스크립트도 없다
4. CLI — 기본 5초, 범위 밖(-1 · 3601)은 rc 2, `--autostart on` 이 기본이 아닌 `--refresh` 를 저장한다
5. 스크립트 — 지문이 같으면 갈아 끼우지 않고, 답을 쓰는 중(dirty)이면 알림만 낸다는 분기가 파일에 있다
   (실제 브라우저 동작은 헤드리스 Chrome CDP 로 task Proof 에 잰다 — 게이트는 브라우저를 띄우지 않는다)
"""

from __future__ import annotations

#: 이 검사의 입력 표면 (spec `core/test_impact_tiering_spec.md` §2).
WATCHES = (
    "workflow-source/pyproject.toml",
    "workflow-source/workflow_kit/*",
    "workflow-source/tests/_workbench_fixture.py",
)

import json
import re
import subprocess
import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _workbench_fixture as fx  # noqa: E402

FAILURES: list[str] = []
JS = fx.SOURCE_ROOT / "workflow_kit" / "workbench" / "static" / "workbench.js"
VERSION_RE = re.compile(r'<main data-version="([0-9a-f]{16})">')


def _record(name: str, problems: list[str]) -> None:
    if problems:
        FAILURES.append(name)
        print(f"  FAIL  {name}")
        for problem in problems[:12]:
            print(f"        - {problem}")
    else:
        print(f"  PASS  {name}")


def _version(html_text: str) -> str | None:
    match = VERSION_RE.search(html_text)
    return match.group(1) if match else None


def _wb(ws: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "workflow_kit", "workbench", "--project-profile-path", str(fx.profile(ws)), *args],
        capture_output=True, encoding="utf-8", errors="replace", check=False, env=fx.env(), cwd=str(ws), timeout=60)


def case_markup() -> list[str]:
    problems: list[str] = []
    with fx.temp_workspace("wb-refresh-1-") as td:
        ws = fx.make_workspace(td)
        task_id = fx.create_task(ws)
        with fx.running(ws, tokens=(), open_name="owner") as srv:
            srv.app.refresh_seconds = 5
            for path in ("/", f"/task/{task_id}"):
                reply = fx.request(srv.port, "GET", path)
                if '<body data-refresh="5">' not in reply.text:
                    problems.append(f"{path}: data-refresh 가 없다")
                if not re.search(r'static/workbench\.js\?v=[0-9a-f]+" defer></script>', reply.text):
                    problems.append(f"{path}: 스크립트가 없다")
                if _version(reply.text) is None:
                    problems.append(f"{path}: main 의 data-version 이 없다")
                if "connect-src 'self'" not in (reply.header("Content-Security-Policy") or ""):
                    problems.append(f"{path}: CSP 에 connect-src 'self' 가 없다 — 스크립트가 다시 받지 못한다")
    return problems


def case_fingerprint() -> list[str]:
    problems: list[str] = []
    with fx.temp_workspace("wb-refresh-2-") as td:
        ws = fx.make_workspace(td)
        task_id = fx.create_task(ws)
        with fx.running(ws, tokens=(), open_name="owner") as srv:
            srv.app.refresh_seconds = 5
            browser = fx.Browser(srv.port)
            for path in ("/", f"/task/{task_id}"):
                first, second = _version(browser.get(path).text), _version(browser.get(path).text)
                if first is None or first != second:
                    problems.append(f"{path}: 같은 상태인데 지문이 다르다 ({first} · {second}) — 화면이 매번 갈아 끼워진다")
            before = {path: _version(browser.get(path).text) for path in ("/", f"/task/{task_id}")}
            fx.backlog(ws, "--mode", "update", "--task-id", task_id, "--task-name", "x", "--decision-state", "D1=answered:warn")
            after = {path: _version(browser.get(path).text) for path in ("/", f"/task/{task_id}")}
            for path in before:
                if before[path] == after[path]:
                    problems.append(f"{path}: task 파일이 바뀌었는데 지문이 그대로다 — 새로고침이 일어나지 않는다")
    return problems


def case_disabled() -> list[str]:
    problems: list[str] = []
    with fx.temp_workspace("wb-refresh-3-") as td:
        ws = fx.make_workspace(td)
        fx.create_task(ws)
        with fx.running(ws, tokens=(), open_name="owner") as srv:
            text = fx.request(srv.port, "GET", "/").text
        if "data-refresh" in text or "workbench.js" in text:
            problems.append("refresh=0 인데 진척 화면에 data-refresh · 스크립트가 있다")
    return problems


def case_cli() -> list[str]:
    problems: list[str] = []
    from workflow_kit.tools import workbench as wb_cli
    if wb_cli.build_parser().parse_args([]).refresh != 5:
        problems.append("--refresh 기본값이 5 가 아니다")
    with fx.temp_workspace("wb-refresh-4-") as td:
        ws = fx.make_workspace(td)
        for bad in ("-1", "3601"):
            proc = _wb(ws, "--open", "owner", "--port", "0", "--refresh", bad)
            if proc.returncode != 2 or "--refresh" not in proc.stderr:
                problems.append(f"--refresh {bad}: rc {proc.returncode} {proc.stderr[-120:]}")
        if _wb(ws, "--autostart", "on", "--open", "owner", "--refresh", "2").returncode != 0:
            return problems + ["--autostart on --refresh 2 가 실패했다"]
        argv = json.loads((ws / ".workbench" / "autostart.json").read_text(encoding="utf-8"))["argv"]
        saved = argv[argv.index("--refresh") + 1] if "--refresh" in argv[:-1] else None
        if saved != "2":
            problems.append(f"자동 기동 설정에 --refresh 2 가 저장되지 않았다: {argv}")
    return problems


def case_script() -> list[str]:
    problems: list[str] = []
    js = JS.read_text(encoding="utf-8")
    for needle, label in (('getAttribute("data-version") === main.getAttribute("data-version")', "지문 비교"),
                          ("if (dirty) { notify(); return; }", "답 쓰는 중이면 알림만"),
                          ("document.hidden", "숨은 탭은 쉰다"),
                          ('redirect: "manual"', "세션이 끝나면 로그인 화면으로 갈아 끼우지 않는다")):
        if needle not in js:
            problems.append(f"workbench.js 에 {label} 분기가 없다")
    return problems


CASES = (
    ("1 data-refresh · 스크립트 · data-version · CSP connect-src", case_markup),
    ("2 지문 — 같은 상태는 같고 바뀌면 다르다", case_fingerprint),
    ("3 refresh=0 이면 끈다", case_disabled),
    ("4 CLI --refresh 기본 · 범위 · 자동 기동 저장", case_cli),
    ("5 스크립트 분기 — 지문 비교 · 쓰는 중 알림", case_script),
)


def main() -> int:
    print("check_workbench_refresh — 워크벤치 자동 새로고침 (plan_workbench_spec §4.5)")
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
