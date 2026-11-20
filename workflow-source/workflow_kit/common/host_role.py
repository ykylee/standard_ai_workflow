"""이 클론의 역할 — 개발 참여자 / 읽기 전용 소비자 (`docs/HOST_ROLES.md` §2).

역할은 클론마다 git **로컬** 설정 `workflow.role` 에 둔다. 전역(`~/.gitconfig`) 값은 읽지 않는다 —
한 호스트의 모든 저장소가 소비자로 바뀌면 안 된다. 읽는 곳은 둘이고 이 함수 하나를 쓴다:

- push: `.githooks/pre-push` → :mod:`workflow_kit.common.gate_evidence` — 소비자 클론의 push 를 막는다.
- 세션 시작: :mod:`workflow_kit.tools.session_start` — 소비자 클론에서는 저장소에 쓰지 않는다
  (TASK-2026-11-20-claude-consumer-readonly-session-start-002).
"""

from __future__ import annotations

import subprocess
from pathlib import Path

#: 이 클론의 역할을 담는 git 로컬 설정 키.
ROLE_CONFIG_KEY = "workflow.role"
CONSUMER_ROLE = "consumer"
CONTRIBUTOR_ROLE = "contributor"


def host_role(repo_root: Path) -> str | None:
    """`git config --local --get workflow.role` (소문자) — 미선언 · git 아님 · git 실패면 None."""
    try:
        proc = subprocess.run(["git", "-C", str(repo_root), "config", "--local", "--get", ROLE_CONFIG_KEY],
                              capture_output=True, text=True, timeout=30, encoding="utf-8", errors="replace")
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    value = proc.stdout.strip() if proc.returncode == 0 else ""
    return value.lower() or None


def is_consumer(repo_root: Path) -> bool:
    """이 클론이 읽기 전용 소비자로 선언됐는가."""
    return host_role(repo_root) == CONSUMER_ROLE
