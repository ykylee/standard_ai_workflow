"""Main entry point for output contracts, using Pydantic as the single source of truth."""

from __future__ import annotations

from pathlib import Path
from typing import Type

from pydantic import BaseModel, ValidationError

from workflow_kit.common.schemas import (
    BacklogUpdateOutput,
    CreateBacklogEntryOutput,
    SessionStartOutput,
    DocSyncOutput,
    ReconcileOutput,
    IndexUpdateOutput,
    ValidationPlanOutput,
    GitConflictResolverOutput,
    OnboardingOutput,
    DemoWorkflowOutput,
    WorkerTask,
    WorkerResponse,
    WorkflowLinterOutput,
    LatestBacklogOutput,
    CheckDocMetadataOutput,
    CheckDocLinksOutput,
    SuggestImpactedDocsOutput,
    CheckQuickstartStaleLinksOutput,
    CreateSessionHandoffDraftOutput,
    CreateEnvironmentRecordStubOutput,
    SmartContextReaderOutput,
    ErrorOutput,
)

# Shared required keys (legacy compatibility if needed, but Pydantic handles this)
COMMON_REQUIRED_KEYS = frozenset({"status", "tool_version", "warnings"})

# Registry mapping family names to Pydantic models
PYDANTIC_MODEL_REGISTRY: dict[str, Type[BaseModel]] = {
    "backlog_update": BacklogUpdateOutput,
    "create_backlog_entry": CreateBacklogEntryOutput,
    "session_start": SessionStartOutput,
    "doc_sync": DocSyncOutput,
    "merge_doc_reconcile": ReconcileOutput,
    "code_index_update": IndexUpdateOutput,
    "validation_plan": ValidationPlanOutput,
    "git_conflict_resolver": GitConflictResolverOutput,
    "existing_project_onboarding": OnboardingOutput,
    "demo_workflow": DemoWorkflowOutput,
    "worker_task": WorkerTask,
    "worker_response": WorkerResponse,
    "workflow_linter": WorkflowLinterOutput,
    "latest_backlog": LatestBacklogOutput,
    "check_doc_metadata": CheckDocMetadataOutput,
    "check_doc_links": CheckDocLinksOutput,
    "suggest_impacted_docs": SuggestImpactedDocsOutput,
    "check_quickstart_stale_links": CheckQuickstartStaleLinksOutput,
    "create_session_handoff_draft": CreateSessionHandoffDraftOutput,
    "create_environment_record_stub": CreateEnvironmentRecordStubOutput,
    "smart_context_reader": SmartContextReaderOutput,
}

def detect_sample_family(path: Path | str) -> str | None:
    """Infer the contract family from a sample filename."""
    name = Path(path).name.lower()
    # Normalize filename to family name (e.g., backlog-update.json -> backlog_update)
    family = name.split(".")[0].replace("-", "_")
    if family in PYDANTIC_MODEL_REGISTRY:
        return family
    return None

def validate_output_payload(payload: dict[str, object], *, family: str) -> list[str]:
    """Validate a payload against the Pydantic models."""
    errors: list[str] = []
    status = str(payload.get("status") or "")
    
    if status == "error":
        model_cls = ErrorOutput
    else:
        model_cls = PYDANTIC_MODEL_REGISTRY.get(family)
        if not model_cls:
            return [f"Unknown family: {family}"]

    try:
        model_cls.model_validate(payload)
    except ValidationError as e:
        for error in e.errors():
            loc = " -> ".join(str(l) for l in error["loc"])
            errors.append(f"[{loc}] {error['msg']}")
    
    return errors

def output_json_schema_bundle() -> dict[str, dict[str, object]]:
    """Return a bundle of all output and error schemas generated from Pydantic."""
    outputs = {}
    errors = {}
    
    error_schema = ErrorOutput.model_json_schema()
    
    for family, model_cls in PYDANTIC_MODEL_REGISTRY.items():
        outputs[family] = model_cls.model_json_schema()
        # For legacy compatibility in tests, provide the same error schema for each family
        errors[family] = error_schema
    
    return {
        "outputs": outputs,
        "errors": errors,
    }

def output_json_schema_for_family(family: str) -> dict[str, object]:
    """Return a single JSON schema representing the full output for a family."""
    model_cls = PYDANTIC_MODEL_REGISTRY.get(family)
    if not model_cls:
        raise KeyError(family)
    return model_cls.model_json_schema()
