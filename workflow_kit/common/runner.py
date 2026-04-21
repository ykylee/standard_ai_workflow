"""Shared subprocess runner helpers for workflow kit orchestration scripts."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any


def run_json_command(cmd: list[str], cwd: Path) -> dict[str, Any]:
    completed = subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(completed.stdout)


def current_python_executable() -> str:
    return sys.executable


def repeated_flag_args(flag: str, values: list[str]) -> list[str]:
    return [item for value in values for item in [flag, value]]
