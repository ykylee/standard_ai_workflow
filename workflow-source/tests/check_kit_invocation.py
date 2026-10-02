#!/usr/bin/env python3
"""하네스가 kit 를 ``wk`` 실행 파일 없이 ``python -m workflow_kit`` 으로 부르는지 잰다.

TASK-2026-10-02-main-007. 소유자 보고: Windows 에서 AhnLab V3 가 ``wk.exe`` 를 평판
기반으로 차단했다. ``wk.exe`` 는 pip 가 설치마다 새로 만드는 서명 없는 console-script
런처라 평판이 쌓이지 않는다. 해석기(``python.exe``)는 막히지 않으니 하네스가 보는
모든 호출을 모듈 실행으로 옮겼다. 정본은 ``workflow_kit/common/kit_invocation.py`` 다.

1. ``python -m workflow_kit`` 이 실제로 dispatcher 를 탄다 (``__main__.py``).
2. 정본 §11.1 명령이 전부 :data:`KIT_INVOCATION` 형태이고, 하위 명령이 dispatcher 에 실재한다.
3. 에이전트가 읽고 그대로 실행하는 표면에 ``wk <명령>`` 이 없다. 표면은 플러그인 payload ·
   이 저장소 진입점 · kit 런타임 문자열(docstring 제외)이다.
4. hook 해석기 탐침이 import 에 실패하는 첫 후보를 건너뛴다. Windows 의 ``python3`` 는
   대개 Store 별칭이라 이 경우가 실제로 생긴다.
"""
from __future__ import annotations

WATCHES = (
    "workflow-source/workflow_kit/*",
    "workflow-source/core/global_workflow_standard.md",
    "workflow-source/pyproject.toml",
    "plugin/*",
    "CLAUDE.md",
    "AGENTS.md",
)

import ast
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from workflow_kit.common.kit_invocation import (  # noqa: E402
    KIT_INVOCATION,
    kit_subcommand,
    posix_interpreter_probe,
    posix_kit_found,
)
from workflow_kit.common.standard_rules import load_standard_rules  # noqa: E402

#: ``wk <하위명령>`` 호출 형태. "`wk` executable" 처럼 이름만 말하는 문장은 안 걸린다.
WK_CALL = re.compile(r"(?<![\w-])wk [a-z][a-z-]+")

_failures: list[str] = []
_passes: list[str] = []


def _record(case: str, ok: bool, detail: str = "") -> None:
    (_passes if ok else _failures).append(case if ok else f"{case}: {detail}")
    print(f"  {case}: {'PASS' if ok else 'FAIL'}{(' — ' + detail) if detail else ''}")


def _env() -> dict[str, str]:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(SOURCE_ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    return env


def case_1_module_execution_dispatches() -> None:
    """``python -m workflow_kit --help`` 가 dispatcher 의 명령 목록을 낸다."""
    proc = subprocess.run(
        [sys.executable, "-m", "workflow_kit", "--help"], capture_output=True,
        encoding="utf-8", errors="replace", env=_env(), timeout=60, check=False,
    )
    ok = proc.returncode == 0 and "session-start" in proc.stdout and "refresh-state" in proc.stdout
    _record(
        "case 1 (python -m workflow_kit 이 dispatcher 를 탄다)", ok,
        f"rc={proc.returncode} stdout={proc.stdout[:80]!r} stderr={proc.stderr[-160:]!r}",
    )


def case_2_standard_commands_are_module_calls() -> None:
    """§11.1 명령이 전부 모듈 실행 형태이고 하위 명령이 dispatcher 에 있다."""
    from workflow_kit.workflow_kit_cli import COMMANDS

    rules = load_standard_rules(SOURCE_ROOT)
    problems: list[str] = []
    for purpose, command in rules.memory_commands:
        try:
            sub = kit_subcommand(command).split()[0]
        except ValueError as exc:
            problems.append(str(exc))
            continue
        if sub not in COMMANDS:
            problems.append(f"{purpose}: 하위 명령 {sub!r} 가 dispatcher 에 없다")
    _record(
        f"case 2 (§11.1 명령 {len(rules.memory_commands)}개 = {KIT_INVOCATION} + 실재 하위 명령)",
        not problems and len(rules.memory_commands) > 0, "; ".join(problems[:4]),
    )


def _runtime_string_hits() -> tuple[list[str], int]:
    """kit 런타임 문자열(docstring 제외) 속 ``wk <명령>`` — 출력 · 템플릿으로 에이전트에게 간다."""
    hits: list[str] = []
    sources = sorted((SOURCE_ROOT / "workflow_kit").rglob("*.py"))
    for path in sources:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        docstrings: set[int] = set()
        for node in ast.walk(tree):
            if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                first = node.body[0] if node.body else None
                if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant):
                    docstrings.add(id(first.value))
        for node in ast.walk(tree):
            if (isinstance(node, ast.Constant) and isinstance(node.value, str)
                    and id(node) not in docstrings and (m := WK_CALL.search(node.value))):
                hits.append(f"{path.relative_to(SOURCE_ROOT).as_posix()}:{node.lineno} {m.group(0)}")
    return hits, len(sources)


def case_3_agent_surfaces_never_call_wk() -> None:
    """에이전트가 읽는 표면에 ``wk <명령>`` 0건 — payload · 진입점 · 런타임 문자열."""
    hits: list[str] = []
    payload_files = sorted(p for p in (REPO_ROOT / "plugin").rglob("*") if p.is_file()
                           and p.suffix in {".md", ".json", ".yaml", ".yml", ".toml"})
    for path in [*payload_files, REPO_ROOT / "CLAUDE.md", REPO_ROOT / "AGENTS.md"]:
        if not path.is_file():
            continue
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if m := WK_CALL.search(line):
                hits.append(f"{path.relative_to(REPO_ROOT).as_posix()}:{lineno} {m.group(0)}")
    # CLAUDE.md · AGENTS.md 는 이 저장소의 손 문안도 담는다 — 생성 블록만 재야 하지만 지금은
    # 전체가 0건이라 전체를 잰다. 손 문안에 `wk …` 를 써야 하면 여기를 생성 블록으로 좁힌다.
    runtime_hits, n_sources = _runtime_string_hits()
    hits.extend(runtime_hits)
    ok = not hits and len(payload_files) >= 5 and n_sources >= 100
    _record(
        "case 3 (에이전트 표면에 wk <명령> 0건)", ok,
        f"payload {len(payload_files)} · 소스 {n_sources} 훑음"
        + (f" · {len(hits)}건: {hits[:6]}" if hits else ""),
    )


def case_4_probe_skips_interpreter_without_kit() -> None:
    """첫 후보(``python3``)가 import 에 실패하면 ``python`` 으로 넘어가고, 둘 다 없으면 빈 값."""
    script = f"{posix_interpreter_probe()} {posix_kit_found()} && echo \"PICK=$py\" || echo PICK="
    results: dict[str, str] = {}
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        layouts = {
            "store-alias": {"python3": "exit 9009", "python": "exit 0"},
            "posix": {"python3": "exit 0", "python": "exit 0"},
            "absent": {"python3": "exit 1", "python": "exit 1"},
        }
        for name, bodies in layouts.items():
            bindir = root / name
            bindir.mkdir()
            for exe, body in bodies.items():
                (bindir / exe).write_text(f"#!/bin/sh\n{body}\n", encoding="utf-8")
                (bindir / exe).chmod(0o755)
            env = dict(os.environ)
            # fake 만 보이게 — 실제 해석기가 PATH 에 남으면 판정이 이 호스트에 달린다
            env["PATH"] = f"{bindir}{os.pathsep}/usr/bin{os.pathsep}/bin"
            proc = subprocess.run(["sh", "-c", script], capture_output=True, encoding="utf-8",
                                  errors="replace", env=env, timeout=30, check=False)
            results[name] = proc.stdout.strip()
    expected = {"store-alias": "PICK=python", "posix": "PICK=python3", "absent": "PICK="}
    _record("case 4 (hook 탐침이 kit 없는 해석기를 건너뛴다)", results == expected,
            f"{results} (기대 {expected})")


def main() -> int:
    print("=== kit 호출 = python -m workflow_kit (TASK-2026-10-02-main-007) ===")
    for fn in (case_1_module_execution_dispatches,
               case_2_standard_commands_are_module_calls,
               case_3_agent_surfaces_never_call_wk,
               case_4_probe_skips_interpreter_without_kit):
        fn()
    total = len(_passes) + len(_failures)
    print(f"\n{len(_passes)}/{total} passed")
    if _failures:
        for f in _failures:
            print(f"  ✗ {f}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
