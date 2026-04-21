"""Shared output contract helpers for samples, docs, and smoke tests."""

from __future__ import annotations

from pathlib import Path

COMMON_REQUIRED_KEYS = frozenset({"status", "tool_version", "warnings"})

SUCCESS_PATH_CONTRACTS: dict[str, frozenset[str]] = {
    "session_start": frozenset({"summary", "recommended_next_action"}),
    "backlog_update": frozenset({"operation_type", "target_backlog_path", "source_context"}),
    "doc_sync": frozenset({"impacted_documents", "recommended_review_order", "source_context"}),
    "merge_doc_reconcile": frozenset({"reconcile_targets", "state_conflicts", "source_context"}),
    "validation_plan": frozenset({"recommended_validation_levels", "documentation_checks", "source_context"}),
    "code_index_update": frozenset({"index_update_candidates", "source_context"}),
    "latest_backlog": frozenset({"latest_backlog_path", "candidates"}),
    "demo_workflow": frozenset({"orchestration_plan", "workflow_summary", "source_context"}),
    "existing_project_onboarding": frozenset({"orchestration_plan", "onboarding_summary", "source_context"}),
}

ERROR_PATH_CONTRACTS: dict[str, frozenset[str]] = {
    "session_start": frozenset({"error", "error_code", "source_context"}),
    "backlog_update": frozenset({"error", "error_code", "source_context"}),
    "doc_sync": frozenset({"error", "error_code", "source_context"}),
    "merge_doc_reconcile": frozenset({"error", "error_code", "source_context"}),
    "validation_plan": frozenset({"error", "error_code", "source_context"}),
    "code_index_update": frozenset({"error", "error_code", "source_context"}),
    "demo_workflow": frozenset({"error", "error_code", "source_context"}),
    "existing_project_onboarding": frozenset({"error", "error_code", "source_context"}),
}


def detect_sample_family(path: Path) -> str | None:
    """Infer the sample family from a sample JSON filename."""

    name = path.name
    for family in sorted(
        set(SUCCESS_PATH_CONTRACTS) | set(ERROR_PATH_CONTRACTS),
        key=len,
        reverse=True,
    ):
        if name.startswith(family):
            return family
    return None
