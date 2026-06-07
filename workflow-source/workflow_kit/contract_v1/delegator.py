"""§6.1 / §6.3 Delegator for Orchestrator ↔ Sub-agent Contract v1.

Decides role mapping per §6.1 (MUST delegate) and rejects §6.3 (MUST NOT
delegate) actions. Used by the orchestrator side to auto-enforce the contract
on every task it considers doing itself (P0 from v0.5.5 pilot findings).

Reference: workflow-source/core/orchestrator_subagent_contract_v1.md §6
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

# §3.1~§3.5 role names (must match contract v1 spec)
ALLOWED_ROLES = ("doc-worker", "code-worker", "validation-worker", "workflow-worker")
# §4 task_type enum
ALLOWED_TASK_TYPES = ("doc_draft", "code_change", "validation_run", "bounded_research")

# §6.1 mapping (deterministic): task_type → role
TASK_TYPE_TO_ROLE: dict[str, str] = {
    "doc_draft": "doc-worker",
    "code_change": "code-worker",
    "validation_run": "validation-worker",
    "bounded_research": "doc-worker",
}

# §6.3 MUST-NOT-delegate actions (7 explicit per the spec).
# Substring match against `task.brief` and `task.expected_outputs.primary_artifact`.
# Each entry is (marker, human-readable reason).
MUST_NOT_DELEGATE_MARKERS: tuple[tuple[str, str], ...] = (
    ("handoff", "handoff 갱신은 orchestrator 직접 처리 (contract v1 §6.3)"),
    ("backlog", "backlog 갱신은 orchestrator 직접 처리 (contract v1 §6.3)"),
    ("state.json", "state.json 갱신은 orchestrator 직접 처리 (contract v1 §6.3)"),
    ("ask_user", "ask_user 호출은 orchestrator 직접 처리 (contract v1 §6.3)"),
    ("우선순위", "우선순위 결정은 orchestrator 직접 처리 (contract v1 §6.3)"),
    ("통합/리뷰", "sub-agent 출력 통합/리뷰는 orchestrator 직접 처리 (contract v1 §6.3)"),
    ("PR 본문", "PR 본문 작성은 orchestrator 직접 처리 (contract v1 §6.3)"),
)


@dataclass
class DelegationDecision:
    """The orchestrator's delegation decision for a given task.

    `must_not_delegate` is True iff the task matches a §6.3 marker — in which
    case `rejected_reason` is set and `role` is None. Otherwise `role` is set
    per §6.1 and a fresh `delegation_id` is generated.
    """
    role: str | None
    must_not_delegate: bool
    rejected_reason: str | None
    warnings: list[str] = field(default_factory=list)
    delegation_id: str | None = None
    task_type: str | None = None


class DelegationRejected(ValueError):
    """Raised by strict-mode helpers when §6.3 is violated."""

    def __init__(self, decision: DelegationDecision) -> None:
        super().__init__(decision.rejected_reason or "delegation rejected")
        self.decision = decision


def _generate_delegation_id() -> str:
    """Generate a unique delegation_id per the §4 format `del-YYYY-MM-DD-NNN`."""
    # We keep a date prefix for human readability; the suffix is a short uuid4 hex.
    from datetime import date
    today = date.today().isoformat()
    suffix = uuid.uuid4().hex[:8]
    return f"del-{today}-{suffix}"


def _looks_like_must_not_delegate(task: dict[str, Any]) -> tuple[bool, str | None]:
    """Inspect task.brief and primary_artifact for §6.3 markers.

    Returns (matched, reason). The marker is substring-matched; matches are
    case-insensitive. We intentionally do NOT match "handoff" inside e.g.
    "handoff_path" — only the bare marker word to reduce false positives.
    """
    brief = str(task.get("brief", ""))
    primary = str(
        task.get("expected_outputs", {}).get("primary_artifact", "")
        if isinstance(task.get("expected_outputs"), dict)
        else ""
    )
    haystack = f"{brief}\n{primary}".lower()
    for marker, reason in MUST_NOT_DELEGATE_MARKERS:
        if marker.lower() in haystack:
            return True, reason
    return False, None


def choose_role(task: dict[str, Any], *, strict: bool = False) -> DelegationDecision:
    """Decide which role a task should be delegated to, per contract v1 §6.

    Args:
        task: A task dict matching contract v1 §4 input schema. Only `task_type`,
            `brief`, and `expected_outputs.primary_artifact` are inspected.
        strict: If True, raise DelegationRejected on §6.3 violation instead
            of returning a `must_not_delegate=True` decision. Default False
            (the orchestrator's normal-mode "warn, do not delegate" path).

    Returns:
        DelegationDecision. On §6.3 violation, `must_not_delegate=True` and
        `rejected_reason` is set; orchestrator should NOT call the worker in
        that case. On valid §6.1 task, `role` and `delegation_id` are set.

    Raises:
        DelegationRejected: only if `strict=True` and §6.3 is violated.
        ValueError: if `task.task_type` is not a known enum value.
    """
    if not isinstance(task, dict):
        raise ValueError(f"task must be a dict, got {type(task).__name__}")

    task_type = task.get("task_type")
    if task_type not in ALLOWED_TASK_TYPES:
        raise ValueError(
            f"task.task_type must be one of {ALLOWED_TASK_TYPES}, got {task_type!r}"
        )

    matched, reason = _looks_like_must_not_delegate(task)
    if matched:
        decision = DelegationDecision(
            role=None,
            must_not_delegate=True,
            rejected_reason=reason,
            warnings=[],
            delegation_id=None,
            task_type=task_type,
        )
        if strict:
            raise DelegationRejected(decision)
        return decision

    role = TASK_TYPE_TO_ROLE[task_type]
    warnings: list[str] = []
    # §3 model_tier hint (best-effort, not strict)
    if isinstance(task.get("constraints"), list):
        for c in task["constraints"]:
            if isinstance(c, str) and "main" in c.lower() and "model" in c.lower():
                warnings.append("task mentions 'main model' — orchestrator may promote model_tier")

    return DelegationDecision(
        role=role,
        must_not_delegate=False,
        rejected_reason=None,
        warnings=warnings,
        delegation_id=_generate_delegation_id(),
        task_type=task_type,
    )
