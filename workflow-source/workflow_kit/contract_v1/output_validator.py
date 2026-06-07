"""§5 Output schema validator for Orchestrator ↔ Sub-agent Contract v1.

Validates a sub-agent output payload against contract v1 §5 schema. Used by the
orchestrator to auto-enforce the contract on every sub-agent response (P0 from
v0.5.5 pilot findings).

Reference: workflow-source/core/orchestrator_subagent_contract_v1.md §5
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# Constants pulled from the contract spec. Keep in sync with §5 of
# workflow-source/core/orchestrator_subagent_contract_v1.md.
CONTRACT_VERSION = "1.0"
ALLOWED_STATUS = ("ok", "partial", "failed")
ALLOWED_ROLES = ("doc-worker", "code-worker", "validation-worker", "workflow-worker")
ALLOWED_MODEL_TIERS = ("small", "main")
ALLOWED_ARTIFACT_KINDS = ("markdown", "python", "json", "toml", "text", "code", "other")

REQUIRED_TOP_FIELDS = ("contract_version", "delegation_id", "completed_at", "worker", "result")
REQUIRED_WORKER_FIELDS = ("session_id", "role", "model_tier")
REQUIRED_RESULT_FIELDS = ("status", "summary", "artifacts", "written_paths", "next_step")


@dataclass
class OutputValidationError:
    """A single field-level validation error."""
    field: str
    reason: str

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"{self.field}: {self.reason}"


@dataclass
class OutputValidationResult:
    """Result of validating a sub-agent output payload.

    `is_valid` is True iff `errors` is empty. `warnings` are non-fatal hints
    (e.g., `result.summary` is short, `artifacts` list is empty).
    """
    is_valid: bool
    errors: list[OutputValidationError] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def raise_if_invalid(self) -> None:
        if not self.is_valid:
            joined = "; ".join(str(err) for err in self.errors)
            raise ValueError(f"Contract v1 §5 output schema violation: {joined}")


def _ensure_dict(payload: Any, field: str) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError(f"{field} must be a dict, got {type(payload).__name__}")
    return payload


def validate_output(
    payload: Any,
    expected_delegation_id: str | None = None,
) -> OutputValidationResult:
    """Validate a sub-agent output payload against contract v1 §5.

    Args:
        payload: The deserialized JSON object a sub-agent produced.
        expected_delegation_id: If provided, the validator also asserts the
            payload's `delegation_id` matches this expected value. This is
            what orchestrators should pass to detect cross-delegation leaks.

    Returns:
        OutputValidationResult with `is_valid`, `errors`, `warnings`. Does not
        raise on validation failure — callers decide policy (reject, retry,
        escalate) per contract v1 §7.4.
    """
    errors: list[OutputValidationError] = []
    warnings: list[str] = []

    # Top-level shape
    if not isinstance(payload, dict):
        errors.append(OutputValidationError("payload", f"must be a dict, got {type(payload).__name__}"))
        return OutputValidationResult(is_valid=False, errors=errors)

    for field_name in REQUIRED_TOP_FIELDS:
        if field_name not in payload:
            errors.append(OutputValidationError(field_name, "missing required field"))

    if errors:
        return OutputValidationResult(is_valid=False, errors=errors)

    # contract_version
    version = payload["contract_version"]
    if version != CONTRACT_VERSION:
        errors.append(OutputValidationError(
            "contract_version", f"must be {CONTRACT_VERSION!r}, got {version!r}"
        ))

    # delegation_id match
    delegation_id = payload.get("delegation_id")
    if expected_delegation_id is not None and delegation_id != expected_delegation_id:
        errors.append(OutputValidationError(
            "delegation_id",
            f"expected {expected_delegation_id!r}, got {delegation_id!r}",
        ))

    # worker
    worker = _ensure_dict(payload["worker"], "worker")
    for field_name in REQUIRED_WORKER_FIELDS:
        if field_name not in worker:
            errors.append(OutputValidationError(f"worker.{field_name}", "missing required field"))
    if "role" in worker and worker["role"] not in ALLOWED_ROLES:
        errors.append(OutputValidationError(
            "worker.role", f"must be one of {ALLOWED_ROLES}, got {worker['role']!r}"
        ))
    if "model_tier" in worker and worker["model_tier"] not in ALLOWED_MODEL_TIERS:
        errors.append(OutputValidationError(
            "worker.model_tier", f"must be one of {ALLOWED_MODEL_TIERS}, got {worker['model_tier']!r}"
        ))

    # result
    result = _ensure_dict(payload["result"], "result")
    for field_name in REQUIRED_RESULT_FIELDS:
        if field_name not in result:
            errors.append(OutputValidationError(f"result.{field_name}", "missing required field"))
    if "status" in result and result["status"] not in ALLOWED_STATUS:
        errors.append(OutputValidationError(
            "result.status", f"must be one of {ALLOWED_STATUS}, got {result['status']!r}"
        ))
    if "summary" in result and not isinstance(result["summary"], str):
        errors.append(OutputValidationError("result.summary", "must be a string"))
    if "summary" in result and isinstance(result["summary"], str) and len(result["summary"]) < 3:
        warnings.append("result.summary is very short (< 3 chars); may be insufficient for orchestrator review")
    if "artifacts" in result and not isinstance(result["artifacts"], list):
        errors.append(OutputValidationError("result.artifacts", "must be a list"))
    if "artifacts" in result and isinstance(result["artifacts"], list):
        for idx, artifact in enumerate(result["artifacts"]):
            if not isinstance(artifact, dict):
                errors.append(OutputValidationError(
                    f"result.artifacts[{idx}]", f"must be a dict, got {type(artifact).__name__}"
                ))
                continue
            if "path" not in artifact or "kind" not in artifact:
                errors.append(OutputValidationError(
                    f"result.artifacts[{idx}]", "missing required 'path' or 'kind'"
                ))
            elif artifact["kind"] not in ALLOWED_ARTIFACT_KINDS:
                errors.append(OutputValidationError(
                    f"result.artifacts[{idx}].kind",
                    f"must be one of {ALLOWED_ARTIFACT_KINDS}, got {artifact['kind']!r}",
                ))
    if "written_paths" in result and not isinstance(result["written_paths"], list):
        errors.append(OutputValidationError("result.written_paths", "must be a list"))
    if "next_step" in result:
        if not isinstance(result["next_step"], str):
            errors.append(OutputValidationError("result.next_step", "must be a string"))
        elif not result["next_step"].strip():
            errors.append(OutputValidationError("result.next_step", "must be non-empty"))

    # Optional but validated when present
    if "validation_result" in result:
        vr = result["validation_result"]
        if not isinstance(vr, dict):
            errors.append(OutputValidationError("result.validation_result", "must be a dict"))
        else:
            if "ran" in vr and not isinstance(vr["ran"], bool):
                errors.append(OutputValidationError("result.validation_result.ran", "must be a bool"))
            if vr.get("ran") is True:
                if "status" not in vr:
                    errors.append(OutputValidationError(
                        "result.validation_result.status", "required when ran=true"
                    ))
                elif vr["status"] not in ("pass", "fail", "skipped"):
                    errors.append(OutputValidationError(
                        "result.validation_result.status",
                        f"must be one of ('pass', 'fail', 'skipped'), got {vr['status']!r}",
                    ))

    return OutputValidationResult(
        is_valid=not errors,
        errors=errors,
        warnings=warnings,
    )
