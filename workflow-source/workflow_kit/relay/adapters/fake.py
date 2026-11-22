"""가짜 어댑터 — 게이트 검사용 (계정 · 모델 없이 계약만 잰다).

띄운 프로세스는 stdin 의 줄을 작업 디렉터리 ``.relay-fake.log`` 에 적고, 첫 줄(첫 프롬프트)을 받으면 준비 신호를 낸다.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any

from workflow_kit.relay.adapters.base import Handle, terminate

_SCRIPT = (
    "import sys, pathlib\n"
    "log = pathlib.Path('.relay-fake.log')\n"
    "for line in sys.stdin:\n"
    "    with log.open('a', encoding='utf-8') as f:\n"
    "        f.write(line)\n"
    "    print('ok', flush=True)\n"
)


class FakeAdapter:
    harness = "fake"

    def probe(self) -> dict[str, Any]:
        return {"harness": "fake", "version": "0", "actions": ["spawn", "deliver", "status", "stop"]}

    def spawn(self, cwd: Path, prompt: str, permission_mode: str) -> Handle:
        proc: subprocess.Popen[str] = subprocess.Popen(
            [sys.executable, "-u", "-c", _SCRIPT], cwd=str(cwd), stdin=subprocess.PIPE, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL, text=True, encoding="utf-8")
        h = Handle("fake", proc, cwd, status="idle", extra={"permission_mode": permission_mode})
        self.deliver(h, prompt)
        return h

    def deliver(self, handle: Handle, text: str) -> str:
        assert handle.proc.stdin is not None
        handle.proc.stdin.write(text.replace("\n", " ") + "\n")
        handle.proc.stdin.flush()
        return "stdin"

    def status(self, handle: Handle) -> str:
        return "idle" if handle.alive() else "ended"

    def stop(self, handle: Handle) -> None:
        if handle.proc.stdin is not None:
            handle.proc.stdin.close()
        terminate(handle.proc)
        handle.status = "ended"
