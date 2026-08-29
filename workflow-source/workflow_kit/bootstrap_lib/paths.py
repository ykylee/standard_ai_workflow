"""Path dataclass and harness overlay path helpers.

The ``Paths`` dataclass captures every well-known file the bootstrap
script touches inside a generated kit. The harness-specific
``*_agents_path`` / ``*_config_path`` helpers turn those into the exact
path a given harness's overlay or MCP config should land at.

These helpers are intentionally self-contained: they take already-resolved
``Paths`` instances so the higher-level ``__main__`` can compose the
plan and the lower-level writers/renderers can stay focused on their
own jobs.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

#: Directories ignored when discovering project files via
#: :func:`bootstrap_lib.discovery.iter_repo_files`.
IGNORED_DIRS: frozenset[str] = frozenset(
    {
        ".git",
        ".hg",
        ".svn",
        ".idea",
        ".vscode",
        "node_modules",
        ".next",
        ".turbo",
        "dist",
        "build",
        "coverage",
        "__pycache__",
        ".venv",
        "venv",
    }
)


@dataclass(frozen=True)
class Paths:
    target_root: Path
    kit_root: Path
    core_dir: Path
    memory_dir: Path
    backlog_dir: Path
    readme_path: Path
    profile_path: Path
    state_path: Path
    handoff_path: Path
    backlog_index_path: Path
    daily_backlog_path: Path
    assessment_path: Path
    status_assessment_path: Path


@dataclass(frozen=True)
class HarnessDefinition:
    name: str
    description: str


def bootstrap_branch_slug(target_root: Path) -> str:
    """대상 저장소의 branch slug. git 저장소가 아니면 ``main``.

    v1.0.2 — `workflow_kit.common.paths.branch_for_workspace` 는 대상이 git 저장소가
    아닐 때 **이 kit 저장소의** branch 로 떨어진다 (sandbox caller 를 위한 의도된
    동작이다). 부트스트랩에서 그 동작을 그대로 쓰면 *내가 feature 브랜치에서 실행했다는
    이유로* 남의 새 프로젝트에 `active/feature-x/` 가 생긴다. 대상이 git 이 아니면
    ``main`` 이라는 고정 기본값을 쓴다.
    """
    from workflow_kit.common.paths import _git_branch_slug  # noqa: PLC0415 - 순환 import 회피

    return _git_branch_slug(target_root) or "main"


def make_paths(args: argparse.Namespace) -> Paths:
    target_root = Path(args.target_root).resolve()
    kit_root = target_root / args.kit_dir
    shared_dir = kit_root / "memory" / "active"

    # v1.0.2 — 세션 상태를 **브랜치별로** 둔다.
    #
    # 이전에는 평평한 `active/state.json` 하나였다. 그래서 두 사람이 각자 브랜치에서
    # 일하면 같은 파일에 쓰고 한쪽이 덮어썼다 — 정작 이 워크플로우가 "브랜치별로
    # 갈라 두면 서로 덮어쓰지 않는다" 고 주장하는 바로 그 지점이다. 런타임
    # (`state_path_for_workspace`)은 이미 branch-scoped 를 먼저 보고 legacy 로
    # fallback 하는데, 정작 **부트스트랩이 legacy 만 만들고 있었다**.
    #
    # 공유/브랜치 구분은 `tools/migrate_memory_to_branch_scoped.py` 의 규약과 같다:
    #   공유   — PROJECT_PROFILE.md / PURPOSE.md / *_assessment.md / memory_index/
    #   브랜치 — state.json / session_handoff.md / work_backlog.md / backlog/ / sessions/
    #
    # **기존 평면 layout 이 이미 있으면 그대로 쓴다.** 재실행이 병렬 상태를 만들어
    # "진짜 상태는 어느 쪽인가" 를 모호하게 만드는 것이 더 나쁘다. 옮기려면
    # 마이그레이션 도구를 명시적으로 돌린다.
    legacy_state = shared_dir / "state.json"
    if legacy_state.exists():
        memory_dir = shared_dir
    else:
        memory_dir = shared_dir / bootstrap_branch_slug(target_root)

    backlog_dir = memory_dir / "backlog"
    return Paths(
        target_root=target_root,
        kit_root=kit_root,
        core_dir=kit_root / "core",
        memory_dir=memory_dir,
        backlog_dir=backlog_dir,
        readme_path=kit_root / "README.md",
        profile_path=target_root / "docs" / "PROJECT_PROFILE.md",
        state_path=memory_dir / "state.json",
        handoff_path=memory_dir / "session_handoff.md",
        backlog_index_path=memory_dir / "work_backlog.md",
        daily_backlog_path=backlog_dir / f"{args.today}.md",
        # 평가 문서는 브랜치와 무관한 **프로젝트 정체성** 이라 공유 계층에 둔다.
        assessment_path=shared_dir / "repository_assessment.md",
        status_assessment_path=shared_dir / "project_status_assessment.md",
    )


# ---------------------------------------------------------------------------
# Harness overlay paths
# ---------------------------------------------------------------------------


def codex_agents_path(paths: Paths) -> Path:
    return paths.target_root / "AGENTS.md"


def codex_config_example_path(paths: Paths) -> Path:
    return paths.target_root / ".codex" / "config.toml.example"


def opencode_config_path(paths: Paths) -> Path:
    return paths.target_root / "opencode.json"


def opencode_skill_path(paths: Paths) -> Path:
    return paths.target_root / ".opencode" / "skills" / "standard-ai-workflow" / "SKILL.md"


def opencode_agent_path(paths: Paths) -> Path:
    return paths.target_root / ".opencode" / "agents" / "workflow-orchestrator.md"


def opencode_worker_agent_path(paths: Paths) -> Path:
    return paths.target_root / ".opencode" / "agents" / "workflow-worker.md"


def opencode_doc_worker_agent_path(paths: Paths) -> Path:
    return paths.target_root / ".opencode" / "agents" / "workflow-doc-worker.md"


def opencode_code_worker_agent_path(paths: Paths) -> Path:
    return paths.target_root / ".opencode" / "agents" / "workflow-code-worker.md"


def opencode_validation_worker_agent_path(paths: Paths) -> Path:
    return paths.target_root / ".opencode" / "agents" / "workflow-validation-worker.md"


def antigravity_agents_path(paths: Paths) -> Path:
    return paths.target_root / "ANTIGRAVITY.md"


def minimax_agents_path(paths: Paths) -> Path:
    """Path to the MiniMax Code harness entry file (project root ``MiniMax.md``)."""
    return paths.target_root / "MiniMax.md"


__all__ = [
    "HarnessDefinition",
    "IGNORED_DIRS",
    "Paths",
    "antigravity_agents_path",
    "codex_agents_path",
    "codex_config_example_path",
    "make_paths",
    "minimax_agents_path",
    "opencode_agent_path",
    "opencode_code_worker_agent_path",
    "opencode_config_path",
    "opencode_doc_worker_agent_path",
    "opencode_skill_path",
    "opencode_validation_worker_agent_path",
    "opencode_worker_agent_path",
]
