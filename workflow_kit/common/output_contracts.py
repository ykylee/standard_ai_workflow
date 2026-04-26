"""Shared output contract helpers for samples, docs, and smoke tests."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

COMMON_REQUIRED_KEYS = frozenset({"status", "tool_version", "warnings"})

SUCCESS_PATH_CONTRACTS: dict[str, frozenset[str]] = {
    "session_start": frozenset({"summary", "recommended_next_action"}),
    "backlog_update": frozenset({"operation_type", "target_backlog_path", "source_context"}),
    "doc_sync": frozenset({"impacted_documents", "recommended_review_order", "source_context"}),
    "merge_doc_reconcile": frozenset({"reconcile_targets", "state_conflicts", "source_context"}),
    "validation_plan": frozenset({"recommended_validation_levels", "documentation_checks", "source_context"}),
    "code_index_update": frozenset({"index_update_candidates", "source_context"}),
    "latest_backlog": frozenset({"latest_backlog_path", "candidates"}),
    "check_doc_metadata": frozenset({"checked_files", "missing_metadata"}),
    "check_doc_links": frozenset({"checked_files", "broken_links"}),
    "check_quickstart_stale_links": frozenset(
        {"checked_files", "missing_expected_links", "stale_link_warnings", "reasoning_notes"}
    ),
    "create_backlog_entry": frozenset({"draft_entry"}),
    "create_session_handoff_draft": frozenset({"draft_handoff", "source_context"}),
    "create_environment_record_stub": frozenset({"draft_record", "source_context"}),
    "suggest_impacted_docs": frozenset({"impacted_documents", "reasoning_notes"}),
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
    "latest_backlog": frozenset({"error", "error_code", "source_context"}),
    "check_doc_metadata": frozenset({"error", "error_code", "source_context"}),
    "check_doc_links": frozenset({"error", "error_code", "source_context"}),
    "check_quickstart_stale_links": frozenset({"error", "error_code", "source_context"}),
    "create_backlog_entry": frozenset({"error", "error_code", "source_context"}),
    "create_session_handoff_draft": frozenset({"error", "error_code", "source_context"}),
    "create_environment_record_stub": frozenset({"error", "error_code", "source_context"}),
    "suggest_impacted_docs": frozenset({"error", "error_code", "source_context"}),
    "read_only_entrypoint": frozenset({"error", "error_code", "source_context"}),
    "demo_workflow": frozenset({"error", "error_code", "source_context"}),
    "existing_project_onboarding": frozenset({"error", "error_code", "source_context"}),
}


def required_output_keys(family: str, *, status: str) -> frozenset[str]:
    """Return required keys for a payload family and status."""

    if status == "error":
        return COMMON_REQUIRED_KEYS | ERROR_PATH_CONTRACTS.get(family, frozenset())
    return COMMON_REQUIRED_KEYS | SUCCESS_PATH_CONTRACTS.get(family, frozenset())


def validate_output_payload(payload: dict[str, object], *, family: str) -> list[str]:
    """Validate a payload against the shared output contracts."""

    errors: list[str] = []
    status = str(payload.get("status") or "")
    if status not in {"ok", "warning", "error"}:
        errors.append("`status` 는 `ok`, `warning`, `error` 중 하나여야 한다.")
        return errors

    required_keys = required_output_keys(family, status=status)
    for key in sorted(required_keys):
        if key not in payload:
            errors.append(f"`{family}` output 에 `{key}` 필드가 없다.")
    errors.extend(validate_output_payload_shape(payload, family=family, status=status))
    return errors


@dataclass(frozen=True)
class OutputFieldShape:
    kind: str
    item_kind: str | None = None
    required_keys: frozenset[str] = frozenset()
    allow_null: bool = False
    properties: dict[str, "OutputFieldShape"] = field(default_factory=dict)
    item_properties: dict[str, "OutputFieldShape"] = field(default_factory=dict)


READ_ONLY_OUTPUT_FIELD_SHAPES: dict[str, dict[str, OutputFieldShape]] = {
    "latest_backlog": {
        "latest_backlog_path": OutputFieldShape(kind="string", allow_null=True),
        "candidates": OutputFieldShape(kind="list", item_kind="string"),
        "warnings": OutputFieldShape(kind="list", item_kind="string"),
    },
    "check_doc_metadata": {
        "checked_files": OutputFieldShape(kind="list", item_kind="string"),
        "missing_metadata": OutputFieldShape(
            kind="list",
            item_kind="object",
            required_keys=frozenset({"path", "missing_fields"}),
        ),
        "warnings": OutputFieldShape(kind="list", item_kind="string"),
    },
    "check_doc_links": {
        "checked_files": OutputFieldShape(kind="list", item_kind="string"),
        "broken_links": OutputFieldShape(
            kind="list",
            item_kind="object",
            required_keys=frozenset({"path", "broken_links"}),
        ),
        "warnings": OutputFieldShape(kind="list", item_kind="string"),
    },
    "suggest_impacted_docs": {
        "impacted_documents": OutputFieldShape(kind="list", item_kind="string"),
        "reasoning_notes": OutputFieldShape(kind="list", item_kind="string"),
        "warnings": OutputFieldShape(kind="list", item_kind="string"),
    },
    "check_quickstart_stale_links": {
        "checked_files": OutputFieldShape(kind="list", item_kind="string"),
        "broken_links": OutputFieldShape(
            kind="list",
            item_kind="object",
            required_keys=frozenset({"path", "broken_links"}),
        ),
        "missing_expected_links": OutputFieldShape(
            kind="list",
            item_kind="object",
            required_keys=frozenset({"path", "missing_targets"}),
        ),
        "stale_link_warnings": OutputFieldShape(kind="list", item_kind="string"),
        "reasoning_notes": OutputFieldShape(kind="list", item_kind="string"),
        "warnings": OutputFieldShape(kind="list", item_kind="string"),
    },
    "create_session_handoff_draft": {
        "draft_handoff": OutputFieldShape(kind="list", item_kind="string"),
        "warnings": OutputFieldShape(kind="list", item_kind="string"),
        "source_context": OutputFieldShape(
            kind="object",
            required_keys=frozenset({"latest_backlog_path"}),
            properties={
                "latest_backlog_path": OutputFieldShape(kind="string", allow_null=True),
            },
        ),
    },
    "create_environment_record_stub": {
        "draft_record": OutputFieldShape(kind="list", item_kind="string"),
        "warnings": OutputFieldShape(kind="list", item_kind="string"),
        "source_context": OutputFieldShape(
            kind="object",
            required_keys=frozenset({"hostname", "os_type"}),
            properties={
                "hostname": OutputFieldShape(kind="string"),
                "os_type": OutputFieldShape(kind="string"),
            },
        ),
    },
}

HIGH_VALUE_OUTPUT_FIELD_SHAPES: dict[str, dict[str, OutputFieldShape]] = {
    "session_start": {
        "summary": OutputFieldShape(kind="list", item_kind="string"),
        "in_progress_items": OutputFieldShape(kind="list", item_kind="string"),
        "blocked_items": OutputFieldShape(kind="list", item_kind="string"),
        "latest_backlog_path": OutputFieldShape(kind="string", allow_null=True),
        "next_documents": OutputFieldShape(kind="list", item_kind="string"),
        "validation_notes": OutputFieldShape(kind="list", item_kind="string"),
        "environment_constraints": OutputFieldShape(kind="list", item_kind="string"),
        "source_documents": OutputFieldShape(
            kind="object",
            required_keys=frozenset({"session_handoff_path", "work_backlog_index_path", "project_profile_path"}),
            properties={
                "session_handoff_path": OutputFieldShape(kind="string"),
                "work_backlog_index_path": OutputFieldShape(kind="string"),
                "project_profile_path": OutputFieldShape(kind="string"),
            },
        ),
        "warnings": OutputFieldShape(kind="list", item_kind="string"),
    },
    "backlog_update": {
        "target_backlog_path": OutputFieldShape(kind="string"),
        "task_id": OutputFieldShape(kind="string"),
        "draft_entry": OutputFieldShape(kind="list", item_kind="string"),
        "status_recommendation": OutputFieldShape(
            kind="object",
            required_keys=frozenset({"value", "reason"}),
            properties={
                "value": OutputFieldShape(kind="string"),
                "reason": OutputFieldShape(kind="string"),
            },
        ),
        "fields_requiring_confirmation": OutputFieldShape(kind="list", item_kind="string"),
        "index_update_note": OutputFieldShape(kind="string", allow_null=True),
        "handoff_update_note": OutputFieldShape(kind="string", allow_null=True),
        "validation_note": OutputFieldShape(kind="string", allow_null=True),
        "source_context": OutputFieldShape(
            kind="object",
            required_keys=frozenset({"project_profile_path", "daily_backlog_exists", "existing_task_count"}),
            properties={
                "project_profile_path": OutputFieldShape(kind="string"),
                "daily_backlog_exists": OutputFieldShape(kind="boolean"),
                "existing_task_count": OutputFieldShape(kind="integer"),
            },
        ),
        "warnings": OutputFieldShape(kind="list", item_kind="string"),
    },
    "create_backlog_entry": {
        "draft_entry": OutputFieldShape(kind="list", item_kind="string"),
        "warnings": OutputFieldShape(kind="list", item_kind="string"),
    },
    "doc_sync": {
        "impacted_documents": OutputFieldShape(kind="list", item_kind="string"),
        "hub_update_candidates": OutputFieldShape(kind="list", item_kind="string"),
        "status_doc_candidates": OutputFieldShape(kind="list", item_kind="string"),
        "validation_doc_candidates": OutputFieldShape(kind="list", item_kind="string"),
        "stale_warnings": OutputFieldShape(kind="list", item_kind="string"),
        "warnings": OutputFieldShape(kind="list", item_kind="string"),
        "reasoning_notes": OutputFieldShape(kind="list", item_kind="string"),
        "recommended_review_order": OutputFieldShape(kind="list", item_kind="string"),
        "follow_up_actions": OutputFieldShape(kind="list", item_kind="string"),
        "confidence_notes": OutputFieldShape(kind="list", item_kind="string"),
        "source_context": OutputFieldShape(
            kind="object",
            required_keys=frozenset({"project_profile_path", "changed_files", "change_summary"}),
            properties={
                "project_profile_path": OutputFieldShape(kind="string"),
                "changed_files": OutputFieldShape(kind="list", item_kind="string"),
                "change_summary": OutputFieldShape(kind="string", allow_null=True),
            },
        ),
    },
    "merge_doc_reconcile": {
        "reconcile_targets": OutputFieldShape(kind="list", item_kind="string"),
        "state_conflicts": OutputFieldShape(kind="list", item_kind="string"),
        "reconfirmation_points": OutputFieldShape(kind="list", item_kind="string"),
        "draft_reconcile_notes": OutputFieldShape(kind="list", item_kind="string"),
        "recommended_review_order": OutputFieldShape(kind="list", item_kind="string"),
        "handoff_update_note": OutputFieldShape(kind="string", allow_null=True),
        "backlog_update_note": OutputFieldShape(kind="string", allow_null=True),
        "hub_update_note": OutputFieldShape(kind="string", allow_null=True),
        "validation_follow_up": OutputFieldShape(kind="string", allow_null=True),
        "warnings": OutputFieldShape(kind="list", item_kind="string"),
        "source_context": OutputFieldShape(
            kind="object",
            required_keys=frozenset({"project_profile_path", "merge_result_summary", "changed_files"}),
            properties={
                "project_profile_path": OutputFieldShape(kind="string"),
                "merge_result_summary": OutputFieldShape(kind="string"),
                "changed_files": OutputFieldShape(kind="list", item_kind="string"),
            },
        ),
    },
    "code_index_update": {
        "index_update_candidates": OutputFieldShape(kind="list", item_kind="string"),
        "priority_index_candidates": OutputFieldShape(kind="list", item_kind="string"),
        "stale_index_warnings": OutputFieldShape(kind="list", item_kind="string"),
        "document_structure_signals": OutputFieldShape(kind="list", item_kind="string"),
        "warnings": OutputFieldShape(kind="list", item_kind="string"),
        "source_context": OutputFieldShape(
            kind="object",
            required_keys=frozenset({"project_profile_path", "changed_files", "change_summary"}),
            properties={
                "project_profile_path": OutputFieldShape(kind="string"),
                "project_name": OutputFieldShape(kind="string", allow_null=True),
                "changed_files": OutputFieldShape(kind="list", item_kind="string"),
                "change_summary": OutputFieldShape(kind="string", allow_null=True),
                "work_backlog_index_path": OutputFieldShape(kind="string", allow_null=True),
                "session_handoff_path": OutputFieldShape(kind="string", allow_null=True),
            },
        ),
    },
    "validation_plan": {
        "detected_change_types": OutputFieldShape(kind="list", item_kind="string"),
        "recommended_validation_levels": OutputFieldShape(kind="list", item_kind="string"),
        "recommended_commands": OutputFieldShape(
            kind="list",
            item_kind="object",
            required_keys=frozenset({"command", "reason"}),
            item_properties={
                "command": OutputFieldShape(kind="string"),
                "reason": OutputFieldShape(kind="string"),
            },
        ),
        "commands_requiring_confirmation": OutputFieldShape(
            kind="list",
            item_kind="object",
            required_keys=frozenset({"command", "reason"}),
            item_properties={
                "command": OutputFieldShape(kind="string"),
                "reason": OutputFieldShape(kind="string"),
            },
        ),
        "documentation_checks": OutputFieldShape(kind="list", item_kind="string"),
        "deferred_validation_items": OutputFieldShape(
            kind="list",
            item_kind="object",
            required_keys=frozenset({"item", "suggested_record_path"}),
            item_properties={
                "item": OutputFieldShape(kind="string"),
                "suggested_record_path": OutputFieldShape(kind="string"),
            },
        ),
        "warnings": OutputFieldShape(kind="list", item_kind="string"),
        "confidence_notes": OutputFieldShape(kind="list", item_kind="string"),
        "source_context": OutputFieldShape(
            kind="object",
            required_keys=frozenset({"project_profile_path", "project_name", "changed_files", "change_summary"}),
            properties={
                "project_profile_path": OutputFieldShape(kind="string"),
                "project_name": OutputFieldShape(kind="string"),
                "changed_files": OutputFieldShape(kind="list", item_kind="string"),
                "change_summary": OutputFieldShape(kind="string"),
            },
        ),
    },
    "demo_workflow": {
        "orchestration_plan": OutputFieldShape(
            kind="object",
            required_keys=frozenset({"recommended_pattern", "model_split", "worker_assignments", "integration_notes"}),
            properties={
                "recommended_pattern": OutputFieldShape(kind="string"),
                "model_split": OutputFieldShape(
                    kind="object",
                    required_keys=frozenset({"orchestrator", "doc_worker", "validation_worker"}),
                    properties={
                        "orchestrator": OutputFieldShape(kind="string"),
                        "doc_worker": OutputFieldShape(kind="string"),
                        "code_worker": OutputFieldShape(kind="string"),
                        "validation_worker": OutputFieldShape(kind="string"),
                    },
                ),
                "worker_assignments": OutputFieldShape(
                    kind="list",
                    item_kind="object",
                    required_keys=frozenset({"worker", "model", "responsibilities", "backing_steps"}),
                    item_properties={
                        "worker": OutputFieldShape(kind="string"),
                        "model": OutputFieldShape(kind="string"),
                        "responsibilities": OutputFieldShape(kind="list", item_kind="string"),
                        "backing_steps": OutputFieldShape(kind="list", item_kind="string"),
                    },
                ),
                "integration_notes": OutputFieldShape(kind="list", item_kind="string"),
            },
        ),
        "workflow_summary": OutputFieldShape(
            kind="object",
            required_keys=frozenset(
                {
                    "current_baseline",
                    "target_backlog_path",
                    "primary_impacted_documents",
                    "recommended_validation_levels",
                    "priority_index_candidates",
                    "reconcile_targets",
                }
            ),
            properties={
                "current_baseline": OutputFieldShape(kind="list", item_kind="string"),
                "target_backlog_path": OutputFieldShape(kind="string"),
                "primary_impacted_documents": OutputFieldShape(kind="list", item_kind="string"),
                "recommended_validation_levels": OutputFieldShape(kind="list", item_kind="string"),
                "priority_index_candidates": OutputFieldShape(kind="list", item_kind="string"),
                "reconcile_targets": OutputFieldShape(kind="list", item_kind="string"),
            },
        ),
        "source_context": OutputFieldShape(
            kind="object",
            required_keys=frozenset(
                {
                    "example_project",
                    "project_profile_path",
                    "session_handoff_path",
                    "work_backlog_index_path",
                    "backlog_dir_path",
                    "latest_backlog_path",
                    "task_id",
                    "task_name",
                    "task_brief",
                    "task_status",
                    "changed_files",
                    "merge_result_summary",
                }
            ),
            properties={
                "example_project": OutputFieldShape(kind="string"),
                "project_profile_path": OutputFieldShape(kind="string"),
                "session_handoff_path": OutputFieldShape(kind="string"),
                "work_backlog_index_path": OutputFieldShape(kind="string"),
                "backlog_dir_path": OutputFieldShape(kind="string"),
                "latest_backlog_path": OutputFieldShape(kind="string", allow_null=True),
                "task_id": OutputFieldShape(kind="string"),
                "task_name": OutputFieldShape(kind="string"),
                "task_brief": OutputFieldShape(kind="string"),
                "task_status": OutputFieldShape(kind="string"),
                "changed_files": OutputFieldShape(kind="list", item_kind="string"),
                "merge_result_summary": OutputFieldShape(kind="string"),
            },
        ),
        "warnings": OutputFieldShape(kind="list", item_kind="string"),
    },
    "existing_project_onboarding": {
        "orchestration_plan": OutputFieldShape(
            kind="object",
            required_keys=frozenset({"recommended_pattern", "model_split", "worker_assignments", "integration_notes"}),
            properties={
                "recommended_pattern": OutputFieldShape(kind="string"),
                "model_split": OutputFieldShape(
                    kind="object",
                    required_keys=frozenset({"orchestrator", "doc_worker", "validation_worker"}),
                    properties={
                        "orchestrator": OutputFieldShape(kind="string"),
                        "doc_worker": OutputFieldShape(kind="string"),
                        "code_worker": OutputFieldShape(kind="string"),
                        "validation_worker": OutputFieldShape(kind="string"),
                    },
                ),
                "worker_assignments": OutputFieldShape(
                    kind="list",
                    item_kind="object",
                    required_keys=frozenset({"worker", "model", "responsibilities", "backing_steps"}),
                    item_properties={
                        "worker": OutputFieldShape(kind="string"),
                        "model": OutputFieldShape(kind="string"),
                        "responsibilities": OutputFieldShape(kind="list", item_kind="string"),
                        "backing_steps": OutputFieldShape(kind="list", item_kind="string"),
                    },
                ),
                "integration_notes": OutputFieldShape(kind="list", item_kind="string"),
            },
        ),
        "repository_assessment": OutputFieldShape(
            kind="object",
            required_keys=frozenset({"path", "summary"}),
            properties={
                "path": OutputFieldShape(kind="string", allow_null=True),
                "summary": OutputFieldShape(
                    kind="object",
                    allow_null=True,
                    required_keys=frozenset(
                        {
                            "project_name",
                            "analysis_mode",
                            "primary_stack",
                            "stack_labels",
                            "install_command",
                            "run_command",
                            "quick_test_command",
                            "isolated_test_command",
                            "smoke_check_command",
                            "top_level_entries",
                            "source_dirs",
                            "docs_dirs",
                            "test_dirs",
                            "sample_paths",
                        }
                    ),
                    properties={
                        "project_name": OutputFieldShape(kind="string", allow_null=True),
                        "analysis_mode": OutputFieldShape(kind="string", allow_null=True),
                        "primary_stack": OutputFieldShape(kind="string", allow_null=True),
                        "stack_labels": OutputFieldShape(kind="string", allow_null=True),
                        "install_command": OutputFieldShape(kind="string", allow_null=True),
                        "run_command": OutputFieldShape(kind="string", allow_null=True),
                        "quick_test_command": OutputFieldShape(kind="string", allow_null=True),
                        "isolated_test_command": OutputFieldShape(kind="string", allow_null=True),
                        "smoke_check_command": OutputFieldShape(kind="string", allow_null=True),
                        "top_level_entries": OutputFieldShape(kind="string", allow_null=True),
                        "source_dirs": OutputFieldShape(kind="string", allow_null=True),
                        "docs_dirs": OutputFieldShape(kind="string", allow_null=True),
                        "test_dirs": OutputFieldShape(kind="string", allow_null=True),
                        "sample_paths": OutputFieldShape(kind="list", item_kind="string"),
                    },
                ),
            },
        ),
        "onboarding_summary": OutputFieldShape(
            kind="object",
            required_keys=frozenset({"review_assessment_first", "primary_stack", "inferred_commands", "recommended_next_steps"}),
            properties={
                "review_assessment_first": OutputFieldShape(kind="boolean"),
                "primary_stack": OutputFieldShape(kind="string", allow_null=True),
                "inferred_commands": OutputFieldShape(
                    kind="object",
                    required_keys=frozenset({"install", "run", "quick_test", "isolated_test", "smoke_check"}),
                    properties={
                        "install": OutputFieldShape(kind="string", allow_null=True),
                        "run": OutputFieldShape(kind="string", allow_null=True),
                        "quick_test": OutputFieldShape(kind="string", allow_null=True),
                        "isolated_test": OutputFieldShape(kind="string", allow_null=True),
                        "smoke_check": OutputFieldShape(kind="string", allow_null=True),
                    },
                ),
                "recommended_next_steps": OutputFieldShape(kind="list", item_kind="string"),
            },
        ),
        "source_context": OutputFieldShape(
            kind="object",
            required_keys=frozenset(
                {
                    "project_profile_path",
                    "session_handoff_path",
                    "work_backlog_index_path",
                    "backlog_dir_path",
                    "repository_assessment_path",
                    "latest_backlog_path",
                    "changed_files",
                    "change_summary",
                }
            ),
            properties={
                "project_profile_path": OutputFieldShape(kind="string"),
                "session_handoff_path": OutputFieldShape(kind="string"),
                "work_backlog_index_path": OutputFieldShape(kind="string"),
                "backlog_dir_path": OutputFieldShape(kind="string"),
                "repository_assessment_path": OutputFieldShape(kind="string", allow_null=True),
                "latest_backlog_path": OutputFieldShape(kind="string", allow_null=True),
                "changed_files": OutputFieldShape(kind="list", item_kind="string"),
                "change_summary": OutputFieldShape(kind="string"),
            },
        ),
        "warnings": OutputFieldShape(kind="list", item_kind="string"),
    },
}

OUTPUT_FIELD_SHAPES: dict[str, dict[str, OutputFieldShape]] = {
    **READ_ONLY_OUTPUT_FIELD_SHAPES,
    **HIGH_VALUE_OUTPUT_FIELD_SHAPES,
}

ERROR_OUTPUT_FIELD_SHAPES: dict[str, dict[str, OutputFieldShape]] = {
    "session_start": {
        "source_context": OutputFieldShape(
            kind="object",
            required_keys=frozenset(
                {"session_handoff_path", "work_backlog_index_path", "project_profile_path", "latest_backlog_path"}
            ),
            properties={
                "session_handoff_path": OutputFieldShape(kind="string"),
                "work_backlog_index_path": OutputFieldShape(kind="string"),
                "project_profile_path": OutputFieldShape(kind="string"),
                "latest_backlog_path": OutputFieldShape(kind="string", allow_null=True),
                "missing_path_detail": OutputFieldShape(kind="string"),
                "exception_type": OutputFieldShape(kind="string"),
            },
        ),
    },
    "backlog_update": {
        "source_context": OutputFieldShape(
            kind="object",
            required_keys=frozenset(
                {"project_profile_path", "task_name", "task_brief", "daily_backlog_path", "target_date", "task_id", "mode"}
            ),
            properties={
                "project_profile_path": OutputFieldShape(kind="string"),
                "task_name": OutputFieldShape(kind="string"),
                "task_brief": OutputFieldShape(kind="string"),
                "daily_backlog_path": OutputFieldShape(kind="string", allow_null=True),
                "target_date": OutputFieldShape(kind="string", allow_null=True),
                "task_id": OutputFieldShape(kind="string", allow_null=True),
                "mode": OutputFieldShape(kind="string"),
                "missing_path_detail": OutputFieldShape(kind="string"),
                "exception_type": OutputFieldShape(kind="string"),
            },
        ),
    },
    "doc_sync": {
        "source_context": OutputFieldShape(
            kind="object",
            required_keys=frozenset(
                {
                    "project_profile_path",
                    "changed_files",
                    "change_summary",
                    "session_handoff_path",
                    "work_backlog_index_path",
                    "latest_backlog_path",
                }
            ),
            properties={
                "project_profile_path": OutputFieldShape(kind="string"),
                "changed_files": OutputFieldShape(kind="list", item_kind="string"),
                "change_summary": OutputFieldShape(kind="string", allow_null=True),
                "session_handoff_path": OutputFieldShape(kind="string", allow_null=True),
                "work_backlog_index_path": OutputFieldShape(kind="string", allow_null=True),
                "latest_backlog_path": OutputFieldShape(kind="string", allow_null=True),
                "missing_path_detail": OutputFieldShape(kind="string"),
                "exception_type": OutputFieldShape(kind="string"),
            },
        ),
    },
    "merge_doc_reconcile": {
        "source_context": OutputFieldShape(
            kind="object",
            required_keys=frozenset(
                {
                    "project_profile_path",
                    "merge_result_summary",
                    "session_handoff_path",
                    "work_backlog_index_path",
                    "latest_backlog_path",
                    "changed_files",
                }
            ),
            properties={
                "project_profile_path": OutputFieldShape(kind="string"),
                "merge_result_summary": OutputFieldShape(kind="string"),
                "session_handoff_path": OutputFieldShape(kind="string", allow_null=True),
                "work_backlog_index_path": OutputFieldShape(kind="string", allow_null=True),
                "latest_backlog_path": OutputFieldShape(kind="string", allow_null=True),
                "changed_files": OutputFieldShape(kind="list", item_kind="string"),
                "missing_path_detail": OutputFieldShape(kind="string"),
                "exception_type": OutputFieldShape(kind="string"),
            },
        ),
    },
    "validation_plan": {
        "source_context": OutputFieldShape(
            kind="object",
            required_keys=frozenset(
                {"project_profile_path", "changed_files", "change_summary", "session_handoff_path", "latest_backlog_path"}
            ),
            properties={
                "project_profile_path": OutputFieldShape(kind="string"),
                "changed_files": OutputFieldShape(kind="list", item_kind="string"),
                "change_summary": OutputFieldShape(kind="string", allow_null=True),
                "session_handoff_path": OutputFieldShape(kind="string", allow_null=True),
                "latest_backlog_path": OutputFieldShape(kind="string", allow_null=True),
                "missing_path_detail": OutputFieldShape(kind="string"),
                "exception_type": OutputFieldShape(kind="string"),
            },
        ),
    },
    "code_index_update": {
        "source_context": OutputFieldShape(
            kind="object",
            required_keys=frozenset(
                {"project_profile_path", "changed_files", "change_summary", "work_backlog_index_path", "session_handoff_path"}
            ),
            properties={
                "project_profile_path": OutputFieldShape(kind="string"),
                "changed_files": OutputFieldShape(kind="list", item_kind="string"),
                "change_summary": OutputFieldShape(kind="string", allow_null=True),
                "work_backlog_index_path": OutputFieldShape(kind="string", allow_null=True),
                "session_handoff_path": OutputFieldShape(kind="string", allow_null=True),
                "missing_path_detail": OutputFieldShape(kind="string"),
                "exception_type": OutputFieldShape(kind="string"),
            },
        ),
    },
    "demo_workflow": {
        "source_context": OutputFieldShape(
            kind="object",
            required_keys=frozenset(
                {
                    "example_project",
                    "project_profile_path",
                    "session_handoff_path",
                    "work_backlog_index_path",
                    "backlog_dir_path",
                    "latest_backlog_path",
                    "task_id",
                    "task_name",
                    "task_brief",
                    "task_status",
                    "changed_files",
                    "merge_result_summary",
                    "failed_step",
                    "failed_command",
                    "upstream_error_code",
                }
            ),
            properties={
                "example_project": OutputFieldShape(kind="string"),
                "project_profile_path": OutputFieldShape(kind="string"),
                "session_handoff_path": OutputFieldShape(kind="string"),
                "work_backlog_index_path": OutputFieldShape(kind="string"),
                "backlog_dir_path": OutputFieldShape(kind="string"),
                "latest_backlog_path": OutputFieldShape(kind="string", allow_null=True),
                "task_id": OutputFieldShape(kind="string"),
                "task_name": OutputFieldShape(kind="string"),
                "task_brief": OutputFieldShape(kind="string"),
                "task_status": OutputFieldShape(kind="string"),
                "changed_files": OutputFieldShape(kind="list", item_kind="string"),
                "merge_result_summary": OutputFieldShape(kind="string"),
                "failed_step": OutputFieldShape(kind="string"),
                "failed_command": OutputFieldShape(kind="list", item_kind="string"),
                "upstream_error_code": OutputFieldShape(kind="string"),
                "upstream_status": OutputFieldShape(kind="string"),
                "exception_type": OutputFieldShape(kind="string"),
            },
        ),
    },
    "existing_project_onboarding": {
        "source_context": OutputFieldShape(
            kind="object",
            required_keys=frozenset(
                {
                    "project_profile_path",
                    "session_handoff_path",
                    "work_backlog_index_path",
                    "backlog_dir_path",
                    "repository_assessment_path",
                    "latest_backlog_path",
                    "changed_files",
                    "change_summary",
                }
            ),
            properties={
                "project_profile_path": OutputFieldShape(kind="string"),
                "session_handoff_path": OutputFieldShape(kind="string"),
                "work_backlog_index_path": OutputFieldShape(kind="string"),
                "backlog_dir_path": OutputFieldShape(kind="string"),
                "repository_assessment_path": OutputFieldShape(kind="string", allow_null=True),
                "latest_backlog_path": OutputFieldShape(kind="string", allow_null=True),
                "changed_files": OutputFieldShape(kind="list", item_kind="string"),
                "change_summary": OutputFieldShape(kind="string"),
            },
        ),
    },
    "read_only_entrypoint": {
        "source_context": OutputFieldShape(
            kind="object",
            required_keys=frozenset({"action", "tool", "payload_json"}),
            properties={
                "action": OutputFieldShape(kind="string"),
                "tool": OutputFieldShape(kind="string", allow_null=True),
                "payload_json": OutputFieldShape(kind="string", allow_null=True),
                "allowed_fields": OutputFieldShape(kind="list", item_kind="string"),
                "missing_path": OutputFieldShape(kind="string"),
                "exception_type": OutputFieldShape(kind="string"),
                "exception": OutputFieldShape(kind="string"),
            },
        ),
    },
}


def output_field_shapes_schema() -> dict[str, dict[str, dict[str, object]]]:
    """Return a JSON-serializable view of the nested output field shapes."""

    return {
        family: {
            field_name: output_field_shape_to_schema(shape)
            for field_name, shape in field_shapes.items()
        }
        for family, field_shapes in OUTPUT_FIELD_SHAPES.items()
    }


def output_error_field_shapes_schema() -> dict[str, dict[str, dict[str, object]]]:
    """Return a JSON-serializable view of error-only output field shapes."""

    return {
        family: {
            field_name: output_field_shape_to_schema(shape)
            for field_name, shape in field_shapes.items()
        }
        for family, field_shapes in ERROR_OUTPUT_FIELD_SHAPES.items()
    }


def output_field_shape_to_schema(shape: OutputFieldShape) -> dict[str, object]:
    result: dict[str, object] = {
        "kind": shape.kind,
        "item_kind": shape.item_kind,
        "required_keys": sorted(shape.required_keys),
        "allow_null": shape.allow_null,
    }
    if shape.properties:
        result["properties"] = {
            key: output_field_shape_to_schema(value)
            for key, value in sorted(shape.properties.items())
        }
    if shape.item_properties:
        result["item_properties"] = {
            key: output_field_shape_to_schema(value)
            for key, value in sorted(shape.item_properties.items())
        }
    return result


def _json_schema_for_shape(shape: OutputFieldShape) -> dict[str, object]:
    if shape.kind == "string":
        type_value: object = ["string", "null"] if shape.allow_null else "string"
        return {"type": type_value}
    if shape.kind == "boolean":
        type_value = ["boolean", "null"] if shape.allow_null else "boolean"
        return {"type": type_value}
    if shape.kind == "integer":
        type_value = ["integer", "null"] if shape.allow_null else "integer"
        return {"type": type_value}
    if shape.kind == "list":
        item_schema: dict[str, object] = {}
        if shape.item_kind == "string":
            item_schema = {"type": "string"}
        elif shape.item_kind == "object":
            item_schema = {
                "type": "object",
                "required": sorted(shape.required_keys),
                "properties": {
                    key: _json_schema_for_shape(value)
                    for key, value in sorted(shape.item_properties.items())
                },
                "additionalProperties": True,
            }
        type_value: object = ["array", "null"] if shape.allow_null else "array"
        return {"type": type_value, "items": item_schema}
    if shape.kind == "object":
        type_value = ["object", "null"] if shape.allow_null else "object"
        return {
            "type": type_value,
            "required": sorted(shape.required_keys),
            "properties": {
                key: _json_schema_for_shape(value)
                for key, value in sorted(shape.properties.items())
            },
            "additionalProperties": True,
        }
    return {}


def _json_schema_properties_for_family(family: str) -> dict[str, dict[str, object]]:
    properties: dict[str, dict[str, object]] = {
        "status": {"type": "string"},
        "tool_version": {"type": "string"},
        "warnings": {"type": "array", "items": {"type": "string"}},
    }
    for field_name, shape in OUTPUT_FIELD_SHAPES.get(family, {}).items():
        properties[field_name] = _json_schema_for_shape(shape)
    return properties


def output_json_schema_for_family(family: str) -> dict[str, object]:
    """Build a permissive JSON Schema draft for a payload family."""

    success_required = sorted(required_output_keys(family, status="ok"))
    error_required = sorted(required_output_keys(family, status="error"))
    properties = _json_schema_properties_for_family(family)
    for key in success_required:
        properties.setdefault(key, {})
    for key in error_required:
        properties.setdefault(key, {})

    error_properties = {
        **properties,
        "status": {"const": "error"},
        "error": {"type": "string"},
        "error_code": {"type": "string"},
        "source_context": _json_schema_for_shape(
            ERROR_OUTPUT_FIELD_SHAPES.get(family, {}).get("source_context", OutputFieldShape(kind="object"))
        ),
    }
    success_properties = {
        **properties,
        "status": {"enum": ["ok", "warning"]},
    }

    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": f"{family} output",
        "oneOf": [
            {
                "type": "object",
                "required": success_required,
                "properties": success_properties,
                "additionalProperties": True,
            },
            {
                "type": "object",
                "required": error_required,
                "properties": error_properties,
                "additionalProperties": True,
            },
        ],
    }


def output_json_schema_bundle() -> dict[str, object]:
    """Build JSON Schema drafts for every known output family."""

    families = sorted(set(SUCCESS_PATH_CONTRACTS) | set(ERROR_PATH_CONTRACTS))
    return {
        "schema_version": "draft-2026-04-22",
        "json_schema_draft": "2020-12",
        "tool_version_source": "workflow_kit.__version__",
        "families": {family: output_json_schema_for_family(family) for family in families},
    }


def _validate_list_field(
    family: str,
    field_name: str,
    value: object,
    shape: OutputFieldShape,
) -> list[str]:
    errors: list[str] = []
    if not isinstance(value, list):
        return [f"`{family}` output 의 `{field_name}` 필드는 list 여야 한다."]

    if shape.item_kind == "string":
        if any(not isinstance(item, str) for item in value):
            errors.append(f"`{family}` output 의 `{field_name}` list 항목은 모두 string 이어야 한다.")
        return errors

    if shape.item_kind == "object":
        for index, item in enumerate(value):
            if not isinstance(item, dict):
                errors.append(f"`{family}` output 의 `{field_name}[{index}]` 항목은 object 여야 한다.")
                continue
            missing = sorted(shape.required_keys - set(item))
            for key in missing:
                errors.append(f"`{family}` output 의 `{field_name}[{index}]` 항목에 `{key}` 필드가 없다.")
            for key, item_shape in shape.item_properties.items():
                if key in item:
                    errors.extend(_validate_shape_value(family, f"{field_name}[{index}].{key}", item[key], item_shape))
        return errors

    return errors


def _validate_object_field(
    family: str,
    field_name: str,
    value: object,
    shape: OutputFieldShape,
) -> list[str]:
    if not isinstance(value, dict):
        return [f"`{family}` output 의 `{field_name}` 필드는 object 여야 한다."]

    errors: list[str] = []
    missing = sorted(shape.required_keys - set(value))
    for key in missing:
        errors.append(f"`{family}` output 의 `{field_name}` object 에 `{key}` 필드가 없다.")
    for key, item_shape in shape.properties.items():
        if key in value:
            errors.extend(_validate_shape_value(family, f"{field_name}.{key}", value[key], item_shape))
    return errors


def _validate_shape_value(family: str, field_name: str, value: object, shape: OutputFieldShape) -> list[str]:
    if value is None:
        if shape.allow_null:
            return []
        return [f"`{family}` output 의 `{field_name}` 필드는 null 이 될 수 없다."]
    if shape.kind == "string":
        return [] if isinstance(value, str) else [f"`{family}` output 의 `{field_name}` 필드는 string 이어야 한다."]
    if shape.kind == "boolean":
        return [] if isinstance(value, bool) else [f"`{family}` output 의 `{field_name}` 필드는 boolean 이어야 한다."]
    if shape.kind == "integer":
        return [] if isinstance(value, int) and not isinstance(value, bool) else [
            f"`{family}` output 의 `{field_name}` 필드는 integer 이어야 한다."
        ]
    if shape.kind == "list":
        return _validate_list_field(family, field_name, value, shape)
    if shape.kind == "object":
        return _validate_object_field(family, field_name, value, shape)
    return []


def validate_output_payload_shape(payload: dict[str, object], *, family: str, status: str) -> list[str]:
    if status == "error":
        field_shapes = ERROR_OUTPUT_FIELD_SHAPES.get(family, {})
    else:
        field_shapes = OUTPUT_FIELD_SHAPES.get(family, {})

    errors: list[str] = []
    for field_name, shape in field_shapes.items():
        if field_name not in payload:
            continue
        value = payload[field_name]
        errors.extend(_validate_shape_value(family, field_name, value, shape))
    return errors


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
