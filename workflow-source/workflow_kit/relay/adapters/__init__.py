"""하네스 어댑터 — 하네스의 정식 제어면을 감싸는 얇은 층 (스펙 §9.4, DO10).

PTY 로 대화형 화면을 흉내 내지 않는다. 신뢰가 필요한 수단(Claude ``--bg`` · Codex hook 신뢰 · remote-control)은 쓰지 않는다.
"""

from __future__ import annotations

from workflow_kit.relay.adapters.base import Adapter, Handle

ADAPTERS = ("claude-code", "codex", "fake")


def get(name: str) -> Adapter:
    if name == "claude-code":
        from workflow_kit.relay.adapters.claude_code import ClaudeCodeAdapter

        return ClaudeCodeAdapter()
    if name == "codex":
        from workflow_kit.relay.adapters.codex import CodexAdapter

        return CodexAdapter()
    if name == "fake":
        from workflow_kit.relay.adapters.fake import FakeAdapter

        return FakeAdapter()
    raise KeyError(f"모르는 어댑터: {name}")


__all__ = ["ADAPTERS", "Adapter", "Handle", "get"]
