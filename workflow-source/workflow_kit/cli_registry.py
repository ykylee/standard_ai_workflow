"""workflow_kit.cli_registry - dispatcher command registry (v1.1.7+).

workflow_kit_cli.py 에서 verbatim 추출 (TASK-2026-08-11-main-011, dispatcher
2095-line 부분 분할). `COMMANDS` dict + `@register` decorator + flag helper 를
들고 있는 최하층 — workflow_kit_cli 및 cli_commands_* 모듈이 여기서 import 하고,
본 모듈은 workflow_kit 내부의 어느 모듈도 import 하지 않는다 (cycle 차단).
workflow_kit_cli 가 전부 재-export 하므로 기존 호출 경로는 그대로 동작한다.
"""

from __future__ import annotations

import ast
import inspect
import re
import sys
from typing import Callable

__all__ = [
    "COMMANDS",
    "register",
    "_print_usage",
    "_parse_flag",
    "_has_flag",
    "known_flags_for",
]


COMMANDS: dict[str, Callable[[list[str]], int]] = {}


#: 이 정규식이 docstring 과 소스에서 플래그를 뽑는 정본이다.
_FLAG_RE = re.compile(r"--[a-z0-9][a-z0-9-]*")


def _flag_literals(node: ast.AST) -> set[str]:
    """`_parse_flag(argv, "--x")` / `_has_flag(argv, "--x")` 의 리터럴을 모은다."""
    out: set[str] = set()
    for n in ast.walk(node):
        if isinstance(n, ast.Call) and getattr(n.func, "id", "") in ("_parse_flag", "_has_flag"):
            for a in n.args:
                if isinstance(a, ast.Constant) and isinstance(a.value, str) and a.value.startswith("--"):
                    out.add(a.value)
    return out


def known_flags_for(fn: Callable[[list[str]], int]) -> frozenset[str]:
    """이 커맨드가 **실제로 읽는** 플래그 집합 — 손 목록이 아니라 소스에서 파생한다.

    셋의 합집합이다:
      1. 자기 docstring 의 `--flag` 표기 (사람이 선언한 것)
      2. 자기 본문이 `_parse_flag`/`_has_flag` 로 읽는 리터럴
      3. **같은 모듈의 `_` 헬퍼**가 읽는 리터럴 (`--json` 같은 공통 배선)

    3을 *호출한 헬퍼만* 으로 좁히지 않는다 — 함수를 인자로 받는 래퍼가 하나만
    끼어도 호출그래프 파생이 조용히 풀리는 것을 이미 겪었다. 여기서는 모듈
    단위로 느슨하게 잡되, 실측 허용집합 중앙값이 4개라 충분히 좁다.
    """
    try:
        src = inspect.getsource(fn)
        node: ast.AST = ast.parse(src.lstrip())
    except (OSError, TypeError, SyntaxError, IndentationError):
        return frozenset()
    known = set(_FLAG_RE.findall(fn.__doc__ or "")) | _flag_literals(node)
    mod = sys.modules.get(getattr(fn, "__module__", ""))
    mod_file = getattr(mod, "__file__", None)
    if mod_file:
        try:
            tree = ast.parse(open(mod_file, encoding="utf-8").read())
        except (OSError, SyntaxError):
            return frozenset(known)
        for n in tree.body:
            if isinstance(n, ast.FunctionDef) and n.name.startswith("_"):
                known |= _flag_literals(n)
    return frozenset(known)


def register(name: str) -> Callable[[Callable[[list[str]], int]], Callable[[list[str]], int]]:
    def decorator(fn: Callable[[list[str]], int]) -> Callable[[list[str]], int]:
        def guarded(argv: list[str]) -> int:
            # **모르는 플래그는 거절한다.** 예전에는 조용히 버렸고, 그래서
            # `wk release-bump --version 1.11.0 --apply` 가 요청한 버전을 무시한 채
            # patch 자동 증가를 하고 **직전 커밋을 amend** 했다 (2026-09-23 실측,
            # 실제 플래그는 `--to`). 인자를 버리는 CLI 는 사용자가 요청한 것과
            # 다른 일을 하면서 성공을 보고한다.
            known = known_flags_for(fn)
            if not known:
                # 허용집합이 비면 이 커맨드는 손 파싱을 안 쓴다 — argparse 기반이라
                # **자기 파서가 이미 모르는 인자를 거절하고 자기 `--help` 를 낸다.**
                # 여기서 가로채면 그 풍부한 도움말을 빈약한 docstring 으로 덮는다.
                return fn(argv)
            if "--help" in argv or "-h" in argv:
                print(inspect.getdoc(fn) or f"{name}: (도움말 없음)")
                return 0
            if known:
                unknown = [
                    a for a in argv
                    if a.startswith("--") and a.split("=", 1)[0] not in known
                ]
                if unknown:
                    print(
                        f"ERROR: {name}: 모르는 인자 {unknown} — 받는 것은 "
                        f"{sorted(known)}",
                        file=sys.stderr,
                    )
                    return 2
            return fn(argv)

        guarded.__name__ = fn.__name__
        guarded.__doc__ = fn.__doc__
        guarded.__module__ = fn.__module__
        guarded.__wrapped__ = fn          # type: ignore[attr-defined]
        COMMANDS[name] = guarded
        return fn                          # 원본을 돌려준다 — 모듈 내부 직접 호출 보존

    return decorator


def _print_usage() -> None:
    print("Usage: wk <name> [args...]   |   workflow_kit_cli --command=<name> [args...]")
    print("Commands:")
    for name in sorted(COMMANDS):
        print(f"  {name}")


def _parse_flag(argv: list[str], flag: str) -> str | None:
    for arg in argv:
        if arg.startswith(flag + "="):
            return arg.split("=", 1)[1]
    return None


def _has_flag(argv: list[str], flag: str) -> bool:
    return flag in argv
