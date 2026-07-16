"""Logic for managing the workflow state JSON cache."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from workflow_kit.common.paths import (
    project_workspace_root,
    workflow_backlog_dir,
    workflow_branch_dir,
    workflow_memory_dir,
    workflow_sessions_dir,
    workflow_tasks_dir,
)
from workflow_kit.common.state.builder import build_workflow_state_payload
from workflow_kit.common.state.memory_index import (
    load_memory_index,
    load_memory_index_at,
    memory_index_root,
)

def build_state_cache_refresh_hint(
    *,
    project_profile_path: Path,
    latest_backlog_path: Path | None = None,
    repository_assessment_path: Path | None = None,
    memory_index_dir: Path | None = None,
    daily_backlog_dir: Path | None = None,
    tasks_dir: Path | None = None,
    sessions_dir: Path | None = None,
) -> dict[str, str]:
    workspace_root = project_workspace_root(project_profile_path)
    # v0.11.20 fix: workflow_memory_dir(...) 이 이미 `ai-workflow/memory/active/` (or
    # `<workspace>/ai-workflow/memory/` when PROJECT_PROFILE.md is in docs/) 을 반환.
    # v0.6.0.1 의 `/ "active"` 후속 fix 가 누락되어 state.json 이 `<branch>/active/state.json`
    # 으로 잘못 쓰여졌었음 (테스트 fixture 의 path 기대와 production 양쪽 어긋남).
    memory_dir = workflow_memory_dir(project_profile_path)
    branch_dir = workflow_branch_dir(project_profile_path)
    generator_path = workspace_root / "workflow-source" / "scripts" / "generate_workflow_state.py"
    # state.json 은 memory_dir (active/) 에서 공유 — workflow-linter 의
    # `workflow_memory_dir(...) / "state.json"` 패턴과 정합.
    state_path = memory_dir / "state.json"
    # v0.14.0+ 신규 layout (append-only) dir 자동 resolve.
    # 명시되지 않으면 memory_dir 하위 신규 layout 디렉토리로 default.
    resolved_daily_backlog_dir = daily_backlog_dir or workflow_backlog_dir(project_profile_path)
    resolved_tasks_dir = tasks_dir or workflow_tasks_dir(project_profile_path)
    resolved_sessions_dir = sessions_dir or workflow_sessions_dir(project_profile_path)
    # legacy path (1st deprecation cycle fallback) — branch_dir/session_handoff.md 및
    # memory_dir/work_backlog.md 가 모두 부재할 때만 hint 에서 제외.
    legacy_handoff_path = branch_dir / "session_handoff.md"
    legacy_index_path = memory_dir / "work_backlog.md"
    command_parts = [
        f"python3 {generator_path}",
        f"--project-profile-path {project_profile_path}",
        f"--daily-backlog-dir {resolved_daily_backlog_dir}",
        f"--tasks-dir {resolved_tasks_dir}",
        f"--sessions-dir {resolved_sessions_dir}",
    ]
    if legacy_handoff_path.exists():
        command_parts.append(f"--session-handoff-path {legacy_handoff_path}")
    if legacy_index_path.exists():
        command_parts.append(f"--work-backlog-index-path {legacy_index_path}")
    command_parts.append(f"--output-path {state_path}")
    if latest_backlog_path:
        command_parts.append(f"--latest-backlog-path {latest_backlog_path}")
    if repository_assessment_path:
        command_parts.append(f"--repository-assessment-path {repository_assessment_path}")
    # v0.11.22+ Phase 1.5: memory_index_dir 가 명시되면 refresh hint command 에 포함.
    if memory_index_dir:
        command_parts.append(f"--memory-index-dir {memory_index_dir}")
    return {
        "state_path": str(state_path),
        "refresh_command": " ".join(str(part) for part in command_parts),
    }

def refresh_workflow_state_cache(
    *,
    project_profile_path: Path,
    session_handoff_path: Path | None = None,
    work_backlog_index_path: Path | None = None,
    daily_backlog_dir: Path | None = None,
    tasks_dir: Path | None = None,
    sessions_dir: Path | None = None,
    latest_backlog_path: Path | None = None,
    repository_assessment_path: Path | None = None,
    output_path: Path | None = None,
    generated_at: str,
    workspace_root: Path | None = None,
    memory_index_dir: Path | None = None,
) -> dict[str, Any]:
    resolved_project_profile_path = project_profile_path.resolve()
    # v0.11.20 fix: build_state_cache_refresh_hint 와 정합 — memory_dir / branch_dir 모두
    # `/ "active"` suffix 제거. PROJECT_PROFILE.md 가 이미 `<memory>/active/` 에 있으므로
    # `workflow_memory_dir(...)` 가 active/ 까지 포함한 path 를 반환.
    memory_dir = workflow_memory_dir(resolved_project_profile_path)
    branch_dir = workflow_branch_dir(resolved_project_profile_path)
    actual_root = workspace_root or project_workspace_root(resolved_project_profile_path)
    # legacy path 자동 resolve (1st deprecation cycle fallback)
    resolved_session_handoff_path = (
        (session_handoff_path or (branch_dir / "session_handoff.md")).resolve()
        if (session_handoff_path or (branch_dir / "session_handoff.md")).exists()
        else None
    )
    resolved_work_backlog_index_path = (
        (work_backlog_index_path or (memory_dir / "work_backlog.md")).resolve()
        if (work_backlog_index_path or (memory_dir / "work_backlog.md")).exists()
        else None
    )
    # v0.14.0+ 신규 layout dir 자동 resolve
    resolved_daily_backlog_dir = daily_backlog_dir or workflow_backlog_dir(resolved_project_profile_path)
    resolved_tasks_dir = tasks_dir or workflow_tasks_dir(resolved_project_profile_path)
    resolved_sessions_dir = sessions_dir or workflow_sessions_dir(resolved_project_profile_path)
    resolved_latest_backlog_path = latest_backlog_path.resolve() if latest_backlog_path else None
    resolved_repository_assessment_path = repository_assessment_path.resolve() if repository_assessment_path else None

    # v0.14.0+ 신규 layout 의 dir 은 부재해도 OK (aggregate 가 빈 dict 반환).
    # legacy path 만 required check 대상.
    missing_paths: list[str] = []
    for required_path in (
        resolved_project_profile_path,
    ):
        if not required_path.exists():
            missing_paths.append(str(required_path))
    # legacy required (둘 다 부재 시 warning 만, skip ❌)
    if resolved_session_handoff_path is None and resolved_work_backlog_index_path is None:
        if not resolved_daily_backlog_dir.exists():
            missing_paths.append(str(resolved_daily_backlog_dir))

    state_path = (output_path or (memory_dir / "state.json")).resolve()
    refresh_hint = build_state_cache_refresh_hint(
        project_profile_path=resolved_project_profile_path,
        latest_backlog_path=resolved_latest_backlog_path,
        repository_assessment_path=resolved_repository_assessment_path,
        memory_index_dir=memory_index_dir,
        daily_backlog_dir=resolved_daily_backlog_dir,
        tasks_dir=resolved_tasks_dir,
        sessions_dir=resolved_sessions_dir,
    )
    if missing_paths and not resolved_daily_backlog_dir.exists():
        return {
            "status": "skipped",
            "state_path": str(state_path),
            "refresh_command": refresh_hint["refresh_command"],
            "missing_paths": missing_paths,
        }

    # v0.11.22+ Phase 1.5: ADR-005 memory_entries optional merge.
    # None 이면 zero-risk (key 미포함). 명시되면 load 후 dict 로 변환.
    memory_entries_payload: list[dict[str, Any]] = []
    if memory_index_dir is not None:
        loaded_entries = load_memory_index_at(memory_index_dir)
    elif actual_root is not None:
        loaded_entries = load_memory_index(actual_root)
    else:
        loaded_entries = []
    memory_entries_payload = [e.model_dump(mode="json") for e in loaded_entries]

    payload = build_workflow_state_payload(
        project_profile_path=resolved_project_profile_path,
        session_handoff_path=resolved_session_handoff_path,
        work_backlog_index_path=resolved_work_backlog_index_path,
        daily_backlog_dir=resolved_daily_backlog_dir,
        tasks_dir=resolved_tasks_dir,
        sessions_dir=resolved_sessions_dir,
        latest_backlog_path=resolved_latest_backlog_path,
        repository_assessment_path=resolved_repository_assessment_path,
        generated_at=generated_at,
        workspace_root=actual_root,
        memory_entries=memory_entries_payload,
    )
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {
        "status": "refreshed",
        "state_path": str(state_path),
        "refresh_command": refresh_hint["refresh_command"],
        "missing_paths": [],
    }
