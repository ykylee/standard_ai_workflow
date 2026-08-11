"""workflow_kit.cli_registry - dispatcher command registry (v1.1.7+).

workflow_kit_cli.py 에서 verbatim 추출 (TASK-2026-08-11-main-011, dispatcher
2095-line 부분 분할). `COMMANDS` dict + `@register` decorator + flag helper 를
들고 있는 최하층 — workflow_kit_cli 및 cli_commands_* 모듈이 여기서 import 하고,
본 모듈은 workflow_kit 내부의 어느 모듈도 import 하지 않는다 (cycle 차단).
workflow_kit_cli 가 전부 재-export 하므로 기존 호출 경로는 그대로 동작한다.
"""

from __future__ import annotations

from typing import Callable

__all__ = [
    "COMMANDS",
    "register",
    "_print_usage",
    "_parse_flag",
    "_has_flag",
]


COMMANDS: dict[str, Callable[[list[str]], int]] = {}


def register(name: str) -> Callable[[Callable[[list[str]], int]], Callable[[list[str]], int]]:
    def decorator(fn: Callable[[list[str]], int]) -> Callable[[list[str]], int]:
        COMMANDS[name] = fn
        return fn
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
