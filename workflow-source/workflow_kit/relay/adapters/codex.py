"""Codex 어댑터 — ``codex app-server`` (stdio JSON-RPC, 실측 §1.2 S6 · S7, DO10).

``thread/start`` → ``turn/start``, 턴 중에는 ``turn/steer`` (``expectedTurnId``) 로 끼운다. 서버가 보내는 승인 요청은 거절한다 —
사람 없는 세션이다 (권한 모드가 허용하는 범위는 sandbox 로 준다). hook 신뢰 · remote-control 은 쓰지 않는다.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import threading
import time
from pathlib import Path
from typing import Any

from workflow_kit.relay.adapters.base import Handle, terminate

#: 권한 모드 → Codex sandbox (승인 정책은 늘 never — 승인할 사람이 없다)
_SANDBOX = {"default": "workspace-write", "acceptEdits": "workspace-write", "plan": "read-only"}


class CodexAdapter:
    harness = "codex"

    def probe(self) -> dict[str, Any]:
        exe = shutil.which("codex")
        if exe is None:
            return {"harness": self.harness, "available": False}
        out = subprocess.run([exe, "--version"], capture_output=True, text=True, timeout=30, encoding="utf-8",
                             errors="replace")
        return {"harness": self.harness, "available": True, "version": out.stdout.strip(),
                "actions": ["spawn", "deliver", "deliver_mid_turn", "status", "stop"]}

    def spawn(self, cwd: Path, prompt: str, permission_mode: str) -> Handle:
        exe = shutil.which("codex") or "codex"
        proc: subprocess.Popen[str] = subprocess.Popen(
            [exe, "app-server"], cwd=str(cwd), stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            text=True, encoding="utf-8")
        h = Handle(self.harness, proc, cwd, status="busy",
                   extra={"next_id": 0, "waiting": {}, "turn": None, "sandbox": _SANDBOX.get(permission_mode, "read-only")})
        threading.Thread(target=self._read, args=(h,), daemon=True).start()
        self._request(h, "initialize", {"clientInfo": {"name": "workflow-hub-relay", "version": "1"}})
        self._send(h, {"method": "initialized"})
        r = self._request(h, "thread/start", {"cwd": str(cwd), "sandbox": h.extra["sandbox"], "approvalPolicy": "never"})
        h.harness_session_id = str(((r or {}).get("result") or {}).get("thread", {}).get("id", ""))
        self.deliver(h, prompt)
        return h

    @staticmethod
    def _send(h: Handle, msg: dict[str, Any]) -> None:
        assert h.proc.stdin is not None
        with h.lock:
            h.proc.stdin.write(json.dumps(msg) + "\n")
            h.proc.stdin.flush()

    def _request(self, h: Handle, method: str, params: dict[str, Any], timeout: float = 60.0) -> dict[str, Any] | None:
        h.extra["next_id"] += 1
        rid = h.extra["next_id"]
        ev = threading.Event()
        h.extra["waiting"][rid] = [ev, None]
        self._send(h, {"id": rid, "method": method, "params": params})
        ev.wait(timeout)
        got = h.extra["waiting"].pop(rid, [None, None])[1]
        return got if isinstance(got, dict) else None

    def _read(self, h: Handle) -> None:
        assert h.proc.stdout is not None
        for line in h.proc.stdout:
            try:
                m = json.loads(line)
            except ValueError:
                continue
            if "id" in m and "method" in m:   # 서버 → 클라이언트 요청 (승인 등) — 사람이 없으니 거절
                self._send(h, {"id": m["id"], "error": {"code": -32000, "message": "relay declines — no human"}})
                continue
            if "id" in m:
                slot = h.extra["waiting"].get(m["id"])
                if slot is not None:
                    slot[1] = m
                    slot[0].set()
                continue
            method = m.get("method")
            if method == "turn/started":
                h.extra["turn"] = ((m.get("params") or {}).get("turn") or {}).get("id")
                h.status = "busy"
            elif method == "turn/completed":
                h.extra["turn"] = None
                h.status = "idle"
        h.status = "ended"

    def deliver(self, handle: Handle, text: str) -> str:
        items = [{"type": "text", "text": text}]
        turn = handle.extra.get("turn")
        if turn:
            r = self._request(handle, "turn/steer", {"threadId": handle.harness_session_id, "expectedTurnId": turn,
                                                     "input": items})
            if r is not None and "result" in r:
                return "steer"
        handle.status = "busy"
        r = self._request(handle, "turn/start", {"threadId": handle.harness_session_id, "input": items})
        if r is not None:
            handle.extra["turn"] = ((r.get("result") or {}).get("turn") or {}).get("id") or handle.extra.get("turn")
        return "turn"

    def status(self, handle: Handle) -> str:
        return handle.status if handle.alive() else "ended"

    def stop(self, handle: Handle) -> None:
        turn = handle.extra.get("turn")
        if turn and handle.alive():
            self._request(handle, "turn/interrupt", {"threadId": handle.harness_session_id, "turnId": turn}, timeout=10)
            time.sleep(0.5)
        if handle.proc.stdin is not None:
            handle.proc.stdin.close()
        terminate(handle.proc)
        handle.status = "ended"
