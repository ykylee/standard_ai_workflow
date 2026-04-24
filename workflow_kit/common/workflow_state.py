"""Helpers for building a compact workflow state cache from markdown source docs."""

from __future__ import annotations

import json
from pathlib import Path

from workflow_kit.common.normalize import dedupe_normalized_backticked, dedupe_strings
from workflow_kit.common.paths import workflow_project_dir
from workflow_kit.common.project_docs import (
    find_latest_backlog_path,
    parse_backlog,
    parse_handoff,
    parse_project_profile_core,
    parse_project_profile_validation,
)


def is_meaningful_text(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip()) and not value.strip().startswith("TODO:")


def build_workflow_state_payload(
    *,
    project_profile_path: Path,
    session_handoff_path: Path,
    work_backlog_index_path: Path,
    latest_backlog_path: Path | None = None,
    repository_assessment_path: Path | None = None,
    generated_at: str,
) -> dict[str, object]:
    resolved_latest_backlog_path = latest_backlog_path or find_latest_backlog_path(work_backlog_index_path)
    if resolved_latest_backlog_path is not None and not resolved_latest_backlog_path.exists():
        resolved_latest_backlog_path = None

    profile_core = parse_project_profile_core(project_profile_path)
    profile_validation = parse_project_profile_validation(project_profile_path)
    handoff = parse_handoff(session_handoff_path)
    backlog = parse_backlog(resolved_latest_backlog_path) if resolved_latest_backlog_path else {
        "tasks": [],
        "in_progress_items": [],
        "blocked_items": [],
        "done_items": [],
    }

    in_progress_items = dedupe_normalized_backticked(
        [item for item in list(handoff.get("in_progress_items", [])) if is_meaningful_text(item)]
        + list(backlog.get("in_progress_items", []))
    )
    blocked_items = dedupe_normalized_backticked(
        [item for item in list(handoff.get("blocked_items", [])) if is_meaningful_text(item)]
        + list(backlog.get("blocked_items", []))
    )
    recent_done_items = dedupe_normalized_backticked(
        [item for item in list(handoff.get("recent_done_items", [])) if is_meaningful_text(item)]
        + list(backlog.get("done_items", []))
    )
    next_documents = dedupe_strings(
        [
            str(project_profile_path),
            str(session_handoff_path),
            str(work_backlog_index_path),
            str(resolved_latest_backlog_path) if resolved_latest_backlog_path else "",
            *[str(path) for path in handoff.get("next_documents", []) if isinstance(path, Path) and path.exists()],
            *[str(path) for path in backlog.get("linked_documents", []) if isinstance(path, Path) and path.exists()],
        ]
    )

    current_focus = in_progress_items[0] if in_progress_items else (blocked_items[0] if blocked_items else None)
    if current_focus is None:
        tasks = list(backlog.get("tasks", []))
        if tasks:
            first_task = tasks[0]
            current_focus = f"{first_task['task_id']} {first_task['title']}"

    return {
        "schema_version": "1",
        "generated_at": generated_at,
        "source_of_truth": {
            "project_profile_path": str(project_profile_path),
            "session_handoff_path": str(session_handoff_path),
            "work_backlog_index_path": str(work_backlog_index_path),
            "latest_backlog_path": str(resolved_latest_backlog_path) if resolved_latest_backlog_path else None,
            "repository_assessment_path": str(repository_assessment_path) if repository_assessment_path else None,
        },
        "project": {
            "project_name": profile_core.get("project_name"),
            "document_home": profile_core.get("document_home"),
            "operations_path": profile_core.get("operations_path"),
            "backlog_path": profile_core.get("backlog_path"),
            "handoff_path": profile_core.get("handoff_path"),
            "environment_path": profile_core.get("environment_path"),
        },
        "commands": {
            "quick_tests": profile_validation.get("quick_tests"),
            "isolated_tests": profile_validation.get("isolated_tests"),
            "runtime_checks": profile_validation.get("runtime_checks"),
        },
        "session": {
            "current_baseline": handoff.get("current_baseline"),
            "current_axis": handoff.get("current_axis"),
            "current_focus": current_focus,
            "in_progress_items": in_progress_items,
            "blocked_items": blocked_items,
            "recent_done_items": recent_done_items,
            "environment_constraints": dedupe_normalized_backticked(
                [item for item in [handoff.get("constraints")] if is_meaningful_text(item)]
            ),
        },
        "backlog": {
            "latest_backlog_path": str(resolved_latest_backlog_path) if resolved_latest_backlog_path else None,
            "task_count": len(list(backlog.get("tasks", []))),
            "in_progress_items": list(backlog.get("in_progress_items", [])),
            "blocked_items": list(backlog.get("blocked_items", [])),
            "done_items": list(backlog.get("done_items", [])),
        },
        "next_documents": next_documents,
        "repository_assessment": {
            "path": str(repository_assessment_path) if repository_assessment_path else None,
            "present": bool(repository_assessment_path and repository_assessment_path.exists()),
        },
    }


def build_state_cache_refresh_hint(
    *,
    project_profile_path: Path,
    latest_backlog_path: Path | None = None,
    repository_assessment_path: Path | None = None,
) -> dict[str, str]:
    state_path = project_profile_path.parent / "state.json"
    workflow_dir = workflow_project_dir(project_profile_path)
    command_parts = [
        "python3 scripts/generate_workflow_state.py",
        f"--project-profile-path {project_profile_path}",
        f"--session-handoff-path {workflow_dir / 'session_handoff.md'}",
        f"--work-backlog-index-path {workflow_dir / 'work_backlog.md'}",
        f"--output-path {state_path}",
    ]
    if latest_backlog_path:
        command_parts.append(f"--latest-backlog-path {latest_backlog_path}")
    if repository_assessment_path:
        command_parts.append(f"--repository-assessment-path {repository_assessment_path}")
    return {
        "state_path": str(state_path),
        "refresh_command": " ".join(str(part) for part in command_parts),
    }


def refresh_workflow_state_cache(
    *,
    project_profile_path: Path,
    session_handoff_path: Path | None = None,
    work_backlog_index_path: Path | None = None,
    latest_backlog_path: Path | None = None,
    repository_assessment_path: Path | None = None,
    output_path: Path | None = None,
    generated_at: str,
) -> dict[str, object]:
    resolved_project_profile_path = project_profile_path.resolve()
    project_dir = workflow_project_dir(resolved_project_profile_path)
    resolved_session_handoff_path = (session_handoff_path or (project_dir / "session_handoff.md")).resolve()
    resolved_work_backlog_index_path = (work_backlog_index_path or (project_dir / "work_backlog.md")).resolve()
    resolved_latest_backlog_path = latest_backlog_path.resolve() if latest_backlog_path else None
    resolved_repository_assessment_path = repository_assessment_path.resolve() if repository_assessment_path else None

    missing_paths: list[str] = []
    for required_path in (
        resolved_project_profile_path,
        resolved_session_handoff_path,
        resolved_work_backlog_index_path,
    ):
        if not required_path.exists():
            missing_paths.append(str(required_path))

    state_path = (output_path or (project_dir / "state.json")).resolve()
    refresh_hint = build_state_cache_refresh_hint(
        project_profile_path=resolved_project_profile_path,
        latest_backlog_path=resolved_latest_backlog_path,
        repository_assessment_path=resolved_repository_assessment_path,
    )
    if missing_paths:
        return {
            "status": "skipped",
            "state_path": str(state_path),
            "refresh_command": refresh_hint["refresh_command"],
            "missing_paths": missing_paths,
        }

    payload = build_workflow_state_payload(
        project_profile_path=resolved_project_profile_path,
        session_handoff_path=resolved_session_handoff_path,
        work_backlog_index_path=resolved_work_backlog_index_path,
        latest_backlog_path=resolved_latest_backlog_path,
        repository_assessment_path=resolved_repository_assessment_path,
        generated_at=generated_at,
    )
    state_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {
        "status": "refreshed",
        "state_path": str(state_path),
        "refresh_command": refresh_hint["refresh_command"],
        "missing_paths": [],
    }
