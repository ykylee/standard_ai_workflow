"""어댑터 계약 (스펙 §9.4)."""

from __future__ import annotations

import subprocess
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol


@dataclass
class Handle:
    """띄운 세션 하나 — 프로세스 · 상태 · 하네스 세션 ID."""

    harness: str
    proc: subprocess.Popen[str]
    cwd: Path
    status: str = "busy"                      # idle · busy · ended · unknown
    harness_session_id: str = ""
    extra: dict[str, Any] = field(default_factory=dict)
    lock: threading.Lock = field(default_factory=threading.Lock)

    def alive(self) -> bool:
        return self.proc.poll() is None


class Adapter(Protocol):
    harness: str

    def probe(self) -> dict[str, Any]: ...
    def spawn(self, cwd: Path, prompt: str, permission_mode: str) -> Handle: ...
    def deliver(self, handle: Handle, text: str) -> str: ...
    def status(self, handle: Handle) -> str: ...
    def stop(self, handle: Handle) -> None: ...


def terminate(proc: subprocess.Popen[str], timeout: float = 10.0) -> None:
    if proc.poll() is not None:
        return
    proc.terminate()
    try:
        proc.wait(timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout)
