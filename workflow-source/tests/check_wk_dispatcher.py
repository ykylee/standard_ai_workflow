"""`wk` dispatcher smoke (TASK-2026-08-09-main-002, CLI 化 B안)

A안(v1.1.1) 은 29개 `workflow-*` binary 를 만들었고, B안(v1.1.2) 은 그걸 단일
`wk <name>` 으로 묶는다. **두 표면이 같은 29개를 가리킨다** 는 것이 유일한 약속이라,
한쪽만 늘어나는 사고를 검사가 막는다 (drift prevention 정신, v0.11.23 과 동일).

검증 케이스 (8):
    1. TOOL_MODULES ↔ pyproject `[project.scripts]` 이름 집합 일치 (양방향)
    2. TOOL_MODULES 의 모든 module 이 실제 import 되고 `main` 을 갖는다
    3. `wk` entry point 가 pyproject 에 등록돼 있다
    4. tools 가 COMMANDS 에 실렸고, 기존 38 subcommand 를 *덮지 않았다*
    5. positional 형식과 `--command=` 형식이 같은 커맨드를 부른다
    6. `--list-commands` 가 COMMANDS 전체를 한 줄씩 흘린다 (completion 이 먹는 계약)
    7. unknown command → rc 2, usage 출력
    8. `main()` / `main(argv)` 두 시그니처 모두 argv 가 전달된다

Stdlib only. subprocess + json + tomllib + importlib.
"""

from __future__ import annotations

import importlib
import subprocess
import sys
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from workflow_kit.common.tool_dispatch import (  # noqa: E402
    ALREADY_REGISTERED,
    TOOL_MODULES,
    run_tool,
)
from workflow_kit.workflow_kit_cli import COMMANDS, run_workflow_kit_cli  # noqa: E402

PYPROJECT = SOURCE_ROOT / "pyproject.toml"
ENTRY_PREFIX = "workflow-"


def _entry_point_names() -> dict[str, str]:
    """pyproject `[project.scripts]` 중 `workflow-*` 만 → {name: target}."""
    data = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    scripts = data["project"]["scripts"]
    return {
        name[len(ENTRY_PREFIX):]: target
        for name, target in scripts.items()
        if name.startswith(ENTRY_PREFIX)
    }


def _run_module(*args: str) -> subprocess.CompletedProcess[str]:
    """dispatcher 를 subprocess 로 돌린다 (설치 없이 `wk` 와 같은 경로)."""
    return subprocess.run(
        [sys.executable, "-m", "workflow_kit.workflow_kit_cli", *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=60,
        env={**__import__("os").environ, "PYTHONPATH": str(SOURCE_ROOT)},
    )


def main() -> int:
    failures: list[str] = []

    def check(label: str, cond: bool, detail: str = "") -> None:
        if cond:
            print(f"PASS: {label}")
        else:
            print(f"FAIL: {label} — {detail}")
            failures.append(label)

    # 1) TOOL_MODULES ↔ pyproject entry points — 양방향 집합 일치
    entry_points = _entry_point_names()
    only_dispatch = sorted(set(TOOL_MODULES) - set(entry_points))
    only_entry = sorted(set(entry_points) - set(TOOL_MODULES))
    check(
        "1) TOOL_MODULES ↔ [project.scripts] 이름 집합 일치",
        not only_dispatch and not only_entry,
        f"dispatcher-only={only_dispatch} entry-only={only_entry}",
    )

    # target module 까지 같은 곳을 가리키는지 — 이름만 맞고 대상이 갈리면 더 나쁘다
    mismatched = [
        name
        for name, module in TOOL_MODULES.items()
        if name in entry_points
        and entry_points[name].split(":", 1)[0] != module
    ]
    check(
        "1b) 같은 이름이 같은 module 을 가리킨다",
        not mismatched,
        f"mismatched={mismatched}",
    )

    # 2) 전부 import 되고 main 을 갖는다
    broken: list[str] = []
    for name, module_path in sorted(TOOL_MODULES.items()):
        try:
            mod = importlib.import_module(module_path)
        except Exception as e:  # noqa: BLE001 — 어떤 import 실패든 red
            broken.append(f"{name}: import {type(e).__name__}")
            continue
        if not callable(getattr(mod, "main", None)):
            broken.append(f"{name}: no callable main")
    check("2) 29개 module import + main() 존재", not broken, f"broken={broken}")

    # 3) `wk` entry point 등록
    data = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    wk_target = data["project"]["scripts"].get("wk")
    check(
        "3) `wk` entry point 등록",
        wk_target == "workflow_kit.workflow_kit_cli:wk_main",
        f"wk={wk_target!r}",
    )

    # 4) COMMANDS 에 실렸고 기존 subcommand 를 덮지 않았다
    missing = sorted(set(TOOL_MODULES) - set(COMMANDS))
    check("4) tools 가 COMMANDS 에 등록됨", not missing, f"missing={missing}")

    # ALREADY_REGISTERED 는 손으로 쓴 wrapper 가 남아 있어야 한다 — lazy runner 로
    # 덮였다면 docstring 의 arg surface 가 사라진 것이다.
    overwritten = [
        name
        for name in ALREADY_REGISTERED
        if COMMANDS.get(name, None) is not None
        and COMMANDS[name].__name__.startswith("cmd_tool_")
    ]
    check(
        "4b) 기존 wrapper 2건을 덮지 않음",
        not overwritten,
        f"overwritten={overwritten}",
    )

    # 5) positional ↔ --command= 동치
    pos = _run_module("detect-scope-drift", "--help")
    flag = _run_module("--command=detect-scope-drift", "--help")
    check(
        "5) positional 형식과 --command= 형식이 같은 결과",
        pos.returncode == flag.returncode and pos.stdout == flag.stdout,
        f"rc={pos.returncode}/{flag.returncode} stdout_equal={pos.stdout == flag.stdout}",
    )

    # 6) --list-commands 계약 — completion script 가 이 형식을 먹는다
    listed = _run_module("--list-commands")
    names = [line for line in listed.stdout.splitlines() if line.strip()]
    check(
        "6) --list-commands 가 COMMANDS 전체를 한 줄씩 출력",
        listed.returncode == 0 and names == sorted(COMMANDS),
        f"rc={listed.returncode} n={len(names)} expected={len(COMMANDS)}",
    )

    # 7) unknown command → rc 2
    unknown = _run_module("no-such-command-xyz")
    check(
        "7) unknown command → rc 2 + usage",
        unknown.returncode == 2 and "Commands:" in unknown.stdout,
        f"rc={unknown.returncode}",
    )

    # 8) 두 시그니처 모두 argv 전달
    #    `main(argv)` 형: detect_scope_drift / `main()` 형: survey_remote_workspaces.
    #    잘못된 flag 를 주면 argparse 가 rc 2 로 죽는다 — argv 가 *도달했다* 는 증거.
    #    argv 가 안 갔다면 인자 없는 기본 실행이 되어 rc 가 0 이거나 다른 값이 된다.
    rc_argv_style = run_tool("detect-scope-drift", ["--definitely-not-a-flag"])
    rc_bare_style = run_tool("survey-remote-workspaces", ["--definitely-not-a-flag"])
    check(
        "8) main(argv) / main() 두 시그니처 모두 argv 전달",
        rc_argv_style == 2 and rc_bare_style == 2,
        f"argv_style={rc_argv_style} bare_style={rc_bare_style}",
    )

    # sanity: dispatcher 가 여전히 기존 subcommand 를 안다
    check(
        "sanity) 기존 38 subcommand 보존",
        "dashboard" in COMMANDS and "release-doctor" in COMMANDS,
        "dashboard/release-doctor missing",
    )

    total = 10
    print()
    if failures:
        print(f"{total - len(failures)}/{total} PASS — FAILED: {failures}")
        return 1
    print(f"{total}/{total} PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
