#!/usr/bin/env python3
"""release validate 의 source 목록 사본이 정본을 따라가는지 고정한다 (6 cases).

## 왜

`cmd_validate` 의 source 목록을 손으로 다시 적은 곳이 여럿이었고 전부 **따로
낡았다** (TASK-2026-09-28-main-009). v0.11.12 에 mypy, P4 에 plugin_payload 가 붙을
때마다 일부만 따라갔다 — '전부 skip' 이라면서 mypy 를 실제로 돌리는 test 가 셋,
mypy 를 끌 수 없는 `release-doctor`, 개별 skip 이 mypy 하나뿐인 `release-create`.

정본은 `release_pipeline.VALIDATE_SOURCES` + `VALIDATE_UNSKIPPABLE`. argparse 와
'전부 skip' test 는 정본에서 **파생**한다. 공개 함수 시그니처와 손 파싱 dispatcher 는
리터럴이 필요해 파생할 수 없으므로 **여기서 대조**한다. 정본 자체가 `cmd_validate`
본문과 같은지도 잰다 — 정본이 코드와 갈라지면 파생도 대조도 틀린 것을 따른다.

`known_flags_for` 는 docstring 에 적힌 플래그도 '안다' 로 치므로 **전달**의 증거가
못 된다. 그래서 dispatcher 는 본문이 `_has_flag` 로 **읽는** 리터럴과, 호출에 **넘기는**
`skip_*` 키워드를 AST 로 본다.

6 cases:
  1) `cmd_validate` 가 결과에 쓰는 source (순서 포함) == `VALIDATE_SOURCES`
  2) `cmd_validate` 의 skip 판정이 `_skipped(args, "<source>")` 한 모양뿐이고, 그 집합이
     skip 가능 source 와 같다 (skip 불가 source 에는 탈출구가 없다)
  3) `VALIDATE_UNSKIPPABLE` 은 정본의 부분집합이고 이유가 적혀 있다
  4) argparse `validate` · `release` 가 skip 가능 source 전부의 플래그를 열고, skip 불가
     source 의 플래그는 열지 않는다 (실제 `--help` 로 잰다)
  5) lib `cmd_validate` · `cmd_release` 가 `skip_<source>` 를 받고 `_make_args` 로 넘긴다
  6) dispatcher `release-doctor` · `release-create` 가 `--skip-<source>` 를 읽어
     `skip_<source>` 로 넘긴다
"""

from __future__ import annotations

#: 이 검사의 입력 표면 (spec `core/test_impact_tiering_spec.md` §2). `release_pipeline`
#: import 가 kit 모듈 대부분을 끌어온다 (meta-watch 실측 75건) — 대조 대상 네 파일로
#: 좁히면 사각지대다. 같은 모듈을 import 하는 `check_release_gate_evidence` 와 같은 선언.
WATCHES = (
    "workflow-source/pyproject.toml",
    "workflow-source/workflow_kit/*",
)

import ast
import inspect
import os
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
KIT = SOURCE_ROOT / "workflow_kit"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from workflow_kit.tools import release_pipeline as rp  # noqa: E402
from workflow_kit.tools import release_pipeline_lib as lib  # noqa: E402

PIPELINE_SRC = KIT / "tools" / "release_pipeline.py"
LIB_SRC = KIT / "tools" / "release_pipeline_lib.py"
DISPATCHERS = (
    (KIT / "cli_commands_release.py", "cmd_release_doctor"),
    (KIT / "workflow_kit_cli.py", "cmd_release_create"),
)

FAILURES: list[str] = []


def _flag(source: str) -> str:
    return f"--skip-{source.replace('_', '-')}"


def _func(path: Path, name: str) -> ast.FunctionDef:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError(f"{path.name} 에 {name} 가 없다")


def _check(name: str, problems: list[str]) -> None:
    if problems:
        FAILURES.append(name)
        print(f"  FAIL  {name}")
        for p in problems:
            print(f"        - {p}")
    else:
        print(f"  PASS  {name}")


def _skippable() -> tuple[str, ...]:
    return rp.validate_skippable_sources()


def case_1_result_keys_match_canonical() -> None:
    fn = _func(PIPELINE_SRC, "cmd_validate")
    seen: list[tuple[int, str]] = []
    for node in ast.walk(fn):
        if (isinstance(node, ast.Subscript) and isinstance(node.ctx, ast.Store)
                and isinstance(node.value, ast.Name) and node.value.id == "results"
                and isinstance(node.slice, ast.Constant)):
            seen.append((node.lineno, str(node.slice.value)))
    order: list[str] = []
    for _, key in sorted(seen):
        if key not in order:
            order.append(key)
    problems = []
    if not order:
        problems.append("cmd_validate 에서 results[...] 대입을 하나도 못 찾았다 — 판정이 아무것도 안 잰다")
    if tuple(order) != tuple(rp.VALIDATE_SOURCES):
        problems.append(f"cmd_validate 가 쓰는 source {order} != 정본 {list(rp.VALIDATE_SOURCES)}")
    _check("case 1 cmd_validate 결과 source == VALIDATE_SOURCES (순서 포함)", problems)


def case_2_single_skip_shape() -> None:
    fn = _func(PIPELINE_SRC, "cmd_validate")
    via_helper: list[str] = []
    other_shapes: list[str] = []
    for node in ast.walk(fn):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id == "_skipped" and len(node.args) == 2
                and isinstance(node.args[1], ast.Constant)):
            via_helper.append(str(node.args[1].value))
        if isinstance(node, ast.Attribute) and node.attr.startswith("skip_") \
                and isinstance(node.value, ast.Name) and node.value.id == "args":
            other_shapes.append(f"L{node.lineno} args.{node.attr}")
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id == "getattr" and len(node.args) >= 2
                and isinstance(node.args[1], ast.Constant)
                and str(node.args[1].value).startswith("skip_")):
            other_shapes.append(f"L{node.lineno} getattr(args, {node.args[1].value!r})")
    problems = []
    if other_shapes:
        problems.append(f"_skipped 밖의 skip 판정: {other_shapes}")
    if sorted(via_helper) != sorted(_skippable()):
        problems.append(f"_skipped 로 읽는 source {sorted(via_helper)} != skip 가능 {sorted(_skippable())}")
    _check("case 2 skip 판정은 _skipped 한 모양 · 집합 == skip 가능 source", problems)


def case_3_unskippable_declared() -> None:
    problems = []
    for src, reason in rp.VALIDATE_UNSKIPPABLE.items():
        if src not in rp.VALIDATE_SOURCES:
            problems.append(f"skip 불가로 선언된 {src} 가 정본에 없다")
        if not str(reason).strip():
            problems.append(f"{src} 를 skip 불가로 둔 이유가 비었다")
    _check("case 3 VALIDATE_UNSKIPPABLE ⊂ 정본 + 이유 명시", problems)


def _help_flags(subcommand: str) -> set[str]:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(SOURCE_ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    proc = subprocess.run(
        [sys.executable, "-m", "workflow_kit.tools.release_pipeline", subcommand, "--help"],
        capture_output=True, text=True, timeout=60, env=env, cwd=str(REPO_ROOT),
    )
    if proc.returncode != 0:
        raise AssertionError(f"{subcommand} --help exit {proc.returncode}: {proc.stderr[-300:]}")
    return set(re.findall(r"--skip-[a-z-]+", proc.stdout))


def case_4_argparse_exposes_canonical() -> None:
    problems = []
    for sub in ("validate", "release"):
        flags = _help_flags(sub)
        missing = [_flag(s) for s in _skippable() if _flag(s) not in flags]
        leaked = [_flag(s) for s in rp.VALIDATE_UNSKIPPABLE if _flag(s) in flags]
        if missing:
            problems.append(f"{sub}: 없는 플래그 {missing}")
        if leaked:
            problems.append(f"{sub}: skip 불가 source 의 플래그가 열렸다 {leaked}")
    _check("case 4 argparse validate · release 의 skip 플래그 == 정본", problems)


def _call_keywords(fn: ast.FunctionDef) -> set[str]:
    return {kw.arg for n in ast.walk(fn) if isinstance(n, ast.Call)
            for kw in n.keywords if kw.arg}


def case_5_lib_signatures() -> None:
    problems = []
    for name in ("cmd_validate", "cmd_release"):
        params = set(inspect.signature(getattr(lib, name)).parameters)
        passed = _call_keywords(_func(LIB_SRC, name))
        for s in _skippable():
            if f"skip_{s}" not in params:
                problems.append(f"lib.{name} 가 skip_{s} 를 받지 않는다")
            elif f"skip_{s}" not in passed:
                problems.append(f"lib.{name} 가 skip_{s} 를 받고도 넘기지 않는다")
        for s in rp.VALIDATE_UNSKIPPABLE:
            if f"skip_{s}" in params:
                problems.append(f"lib.{name} 가 skip 불가 source 의 skip_{s} 를 받는다")
    _check("case 5 lib cmd_validate · cmd_release 가 skip_<source> 를 받아 넘긴다", problems)


def _read_flags(fn: ast.FunctionDef) -> set[str]:
    return {str(n.args[1].value) for n in ast.walk(fn)
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
            and n.func.id in ("_has_flag", "_parse_flag") and len(n.args) >= 2
            and isinstance(n.args[1], ast.Constant)}


def case_6_dispatchers_forward() -> None:
    problems = []
    for path, name in DISPATCHERS:
        fn = _func(path, name)
        read = _read_flags(fn)
        passed = _call_keywords(fn)
        for s in _skippable():
            if _flag(s) not in read:
                problems.append(f"{name} 가 {_flag(s)} 를 읽지 않는다")
            if f"skip_{s}" not in passed:
                problems.append(f"{name} 가 skip_{s} 를 넘기지 않는다")
        for s in rp.VALIDATE_UNSKIPPABLE:
            if _flag(s) in read or f"skip_{s}" in passed:
                problems.append(f"{name} 가 skip 불가 source {s} 의 탈출구를 연다")
    _check("case 6 dispatcher release-doctor · release-create 가 --skip-<source> 를 읽어 넘긴다", problems)


CASES = (
    case_1_result_keys_match_canonical,
    case_2_single_skip_shape,
    case_3_unskippable_declared,
    case_4_argparse_exposes_canonical,
    case_5_lib_signatures,
    case_6_dispatchers_forward,
)


def main() -> int:
    print("=== release validate source 정본 ↔ 사본 ===")
    for fn in CASES:
        try:
            fn()
        except Exception as exc:  # noqa: BLE001
            FAILURES.append(fn.__name__)
            print(f"  FAIL  {fn.__name__} — 예외 {type(exc).__name__}: {exc}")
    if FAILURES:
        print(f"\n{len(FAILURES)} fail: {FAILURES}")
        return 1
    print(f"\n{len(CASES)}/{len(CASES)} PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
