#!/usr/bin/env python3
"""**관찰 전용** session-start 호출 — 검사가 저장소를 바꾸지 않는 한 곳.

`check_roadmap_wiring` 과 `check_state_reconcile` 이 자기 적용을 확인하려고
session-start 를 **실제 저장소**에 돌린다. 그 도구는 기본 브랜치 체크아웃에서
dry-run 을 `--apply` 로 올려 버려, 관찰이 조용히 갱신이 되었다
(TASK-2026-10-02-feat-auto-20261002-4a5d394c-002 — 두 검사에서 각각 발동해
브랜치 메모리를 `archived/` 로 옮기고 `active/main/` 을 오염시켰다).

세는 가지가 방어선을 세웠고, 그 수명은 코드가 아니라 **작성자**에 달려 있었다:
플래그를 까먹은 검사는 조용히 저장소를 바꾼다. 그래서 방어선을 함수 하나로
꺼내 검사가 **관찰만** 할 수 있게 한다. 플래그를 여기서만 준다 — 호출부가 그
위험을 알 필요가 없도록.

두 축을 함께 닫는다. **의도**(`--no-reflect`)는 승격을 막고, **환경**(실제
checkout 브랜치)은 "자기 브랜치가 병합된 것으로 보인다" 는 오판을 막는다. 두
둘만으로는 부족하다 — main 체크아웃 + 죽은 브랜치 메모리는 환경 축이 못 막고
(사라지는 대상이 checkout 브랜치가 아니므로), 의도 축은 브랜치 오판을 못 막는다.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
SESSION_START_TOOL = SOURCE_ROOT / "workflow_kit" / "tools" / "session_start.py"

#: 네임스페이스가 없는 브랜치(로컬 detached HEAD · CI)에 넘길 이름. 이 이름을
#: 넘기는 이유가 반대도 아니다 — **알 수 없는 브랜치 이름을 넘기면 session-start 가
#: 그 이름의 메모리 네임스페이스를 새로 seed 해서 쓴다.** 관찰이 그만큼 위험해진다.
#: 그래서 "실제 checkout 브랜치, 단 네임스페이스가 있을 때만" 이 규칙이 필요하다.
FALLBACK_BRANCH = "main"


def resolve_observation_branch(repo_root: Path) -> str:
    """관찰에 넘길 브랜치 — 실제 checkout 브랜치, 네임스페이스가 없으면 fallback.

    `main` 을 무조건 강제하면 worktree 에서 현재 브랜치가 "HEAD 에 병합된
    브랜치" 로 보여 합류 반영이 열린다 (115차 실측). 그러니 실제 이름을 쓰되,
    그 브랜치의 메모리 디렉터리가 **있을 때만** 쓴다.
    """
    proc = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        cwd=str(repo_root), capture_output=True, text=True, encoding="utf-8",
    )
    name = proc.stdout.strip()
    if (
        proc.returncode == 0
        and name
        and name != "HEAD"
        and (repo_root / "ai-workflow" / "memory" / "active" / name / "session_handoff.md").is_file()
    ):
        return name
    return FALLBACK_BRANCH


def _project_root_of(profile: Path) -> Path:
    """``<프로젝트 루트>/docs/PROJECT_PROFILE.md`` → ``<프로젝트 루트>``."""
    # 프로필이 두 단계 nested 라는 관례는 저장소뿐 아니다 — 격리 픽스처도 같은
    # `docs/PROJECT_PROFILE.md` 레이아웃을 쓴다. 그래서 **관찰 대상**의 루트를
    # 여기서 유도해야 한다. 이 헬퍼가 사는 저장소(``REPO_ROOT``)로 고정하면 격리
    # 픽스처를 볼 때 엉뚱한 브랜치(그리고 그 네임스페이스)가 넘어간다 — 실제로
    # 첫 배치가 그렇게 깨졌고, 존재하지 않는 `active/<다른 브랜치>/` 를 찾는
    # session-start 가 `missing_required_document` 로 죽었다. 관찰 대상과
    # 관찰 도구는 다른 저장소일 수 있다.
    return profile.resolve().parents[1] if profile.name == "PROJECT_PROFILE.md" else profile.resolve().parent


def observe_session_start(
    profile: Path,
    *,
    repo_root: Path | None = None,
    branch: str | None = None,
    timeout: int = 180,
) -> tuple[int, dict]:
    """session-start 를 **관찰 전용**으로 돌린다 — 절대 저장소를 바꾸지 않는다.

    ``profile`` 은 세션 시작이 읽을 프로젝트 프로필 경로다. 검사가 자기 저장소를
    관찰하려고 실제 ``docs/PROJECT_PROFILE.md`` 를 넘길 수 있고, 격리 픽스처를
    관찰하려고 임시 프로필을 넘길 수도 있다. **분기 해석은 이 프로필의 프로젝트
    루트 기준**으로 한다 — 명시적 ``repo_root`` 를 주면 그쪽을 쓴다.

    반환은 ``(returncode, payload)`` 다. ``payload`` 는 도구 stdout 을 그대로
    파싱한 것이므로 호출자가 보던 그대로 본다 — 감싸지 않는다.
    """
    root = repo_root or _project_root_of(profile)
    resolved_branch = branch or resolve_observation_branch(root)
    env = dict(os.environ)
    env["CODEX_WORKFLOW_BRANCH"] = resolved_branch
    env["PYTHONPATH"] = str(SOURCE_ROOT)
    # `--no-reflect` 는 이 함수의 존재 이유다. 호출부가 이 목록을 늘리면 안 된다 —
    # 관찰 경로에 쓰기 권한이 들어오는 순간 이 모듈의 계약이 끝난다.
    proc = subprocess.run(
        [
            sys.executable,
            str(SESSION_START_TOOL),
            "--project-profile-path",
            str(profile),
            "--no-reflect",
        ],
        # cwd 를 **관찰 대상 프로젝트**로 둔다. 안 두면 툴이 자기 프로세스의 cwd
        # (검사라면 저장소 루트)를 본다 — 격리 픽스처를 관찰하러 갔는데 실제로는
        # 저장소를 보는 셈이고, 그 저장소엔 아카이브할 게 없어서 "안전" 이라는
        # **빈 증명** 이 나온다. 이 버그를 음성 대조군이 실제로 잡았다.
        cwd=str(root),
        capture_output=True, text=True, timeout=timeout, env=env,
    )
    try:
        payload = json.loads(proc.stdout) if proc.stdout.strip() else {}
    except json.JSONDecodeError:
        raise AssertionError(
            f"session-start 출력이 JSON 이 아니다:\n{proc.stdout[:500]}\n{proc.stderr[:500]}"
        ) from None
    return proc.returncode, payload
