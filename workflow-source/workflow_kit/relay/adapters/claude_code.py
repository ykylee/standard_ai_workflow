"""Claude Code 어댑터 — 상주 stream-json 프로세스 (실측 §1.2 S6, DO10).

``claude -p --input-format stream-json --output-format stream-json --verbose`` 한 프로세스가 턴 사이에 살아 있고, 다음 입력을
stdin 한 줄로 받는다. ``result`` 이벤트 = 턴 끝(idle). 턴 중에 넣으면 다음 턴으로 들어간다 (턴 중 끼우기는 미측정).
``--bg`` 는 쓰지 않는다 — 디렉터리 신뢰가 필요하다 (실측 S10).
"""

from __future__ import annotations

import json
import shutil
import subprocess
import threading
from pathlib import Path
from typing import Any

from workflow_kit.relay.adapters.base import Handle, terminate


class ClaudeCodeAdapter:
    harness = "claude-code"

    def probe(self) -> dict[str, Any]:
        exe = shutil.which("claude")
        if exe is None:
            return {"harness": self.harness, "available": False}
        out = subprocess.run([exe, "--version"], capture_output=True, text=True, timeout=30, encoding="utf-8",
                             errors="replace")
        return {"harness": self.harness, "available": True, "version": out.stdout.strip(),
                "actions": ["spawn", "deliver", "status", "stop"], "deliver_mid_turn": "unmeasured"}

    def spawn(self, cwd: Path, prompt: str, permission_mode: str) -> Handle:
        exe = shutil.which("claude") or "claude"
        proc: subprocess.Popen[str] = subprocess.Popen(
            [exe, "-p", "--input-format", "stream-json", "--output-format", "stream-json", "--verbose",
             "--permission-mode", permission_mode],
            cwd=str(cwd), stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
            encoding="utf-8")
        h = Handle(self.harness, proc, cwd)
        threading.Thread(target=self._read, args=(h,), daemon=True).start()
        self.deliver(h, prompt)
        return h

    @staticmethod
    def _read(h: Handle) -> None:
        assert h.proc.stdout is not None
        for line in h.proc.stdout:
            try:
                ev = json.loads(line)
            except ValueError:
                continue
            if ev.get("type") == "system" and ev.get("subtype") == "init" and ev.get("session_id"):
                h.harness_session_id = str(ev["session_id"])
            elif ev.get("type") == "result":
                h.status = "idle"
        h.status = "ended"

    def deliver(self, handle: Handle, text: str) -> str:
        assert handle.proc.stdin is not None
        with handle.lock:
            handle.proc.stdin.write(json.dumps({"type": "user", "message": {"role": "user", "content": text}}) + "\n")
            handle.proc.stdin.flush()
            was = handle.status
            handle.status = "busy"
        return "next_turn" if was == "busy" else "stdin"

    def status(self, handle: Handle) -> str:
        return handle.status if handle.alive() else "ended"

    def stop(self, handle: Handle) -> None:
        if handle.proc.stdin is not None:
            handle.proc.stdin.close()
        terminate(handle.proc)
        handle.status = "ended"
