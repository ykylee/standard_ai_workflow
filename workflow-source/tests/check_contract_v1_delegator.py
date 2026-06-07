#!/usr/bin/env python3
"""Contract v1 §6.1 / §6.3 delegator regression check.

Verifies that workflow_kit.contract_v1.delegator.choose_role correctly:
- maps the 4 task_types to roles per §6.1
- rejects all 7 §6.3 MUST-NOT-delegate markers (handoff / backlog / state.json / ask_user / 우선순위 / 통합/리뷰 / PR 본문)
- raises on unknown task_type
- generates valid §4 delegation_id format

Reference: workflow-source/core/orchestrator_subagent_contract_v1.md §6
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SOURCE_ROOT))

from workflow_kit.contract_v1 import choose_role, DelegationRejected  # noqa: E402

DELEGATION_ID_RE = re.compile(r"^del-\d{4}-\d{2}-\d{2}-[0-9a-f]{8}$")


def _task(task_type: str, brief: str = "draft spec", primary_artifact: str = "spec.md") -> dict[str, object]:
    return {
        "task_type": task_type,
        "brief": brief,
        "expected_outputs": {"primary_artifact": primary_artifact},
    }


def check_task_type_to_role_mapping() -> None:
    """§6.1: each task_type maps to its expected role."""
    cases = [
        ("doc_draft", "doc-worker"),
        ("code_change", "code-worker"),
        ("validation_run", "validation-worker"),
        ("bounded_research", "doc-worker"),
    ]
    for task_type, expected_role in cases:
        decision = choose_role(_task(task_type))
        if decision.role != expected_role:
            raise AssertionError(
                f"task_type={task_type!r} should map to {expected_role!r}, got {decision.role!r}"
            )
        if decision.must_not_delegate:
            raise AssertionError(f"task_type={task_type!r} should NOT be §6.3 rejected")
        if not DELEGATION_ID_RE.match(decision.delegation_id or ""):
            raise AssertionError(
                f"delegation_id format wrong: {decision.delegation_id!r} (expected del-YYYY-MM-DD-xxxxxxxx)"
            )


def check_must_not_delegate_rejection() -> None:
    """§6.3: all 7 markers must be rejected with must_not_delegate=True."""
    cases = [
        ("handoff 갱신 및 정리", "handoff 갱신은 orchestrator 직접 처리 (contract v1 §6.3)"),
        ("backlog update", "backlog 갱신은 orchestrator 직접 처리 (contract v1 §6.3)"),
        ("state.json 동기화", "state.json 갱신은 orchestrator 직접 처리 (contract v1 §6.3)"),
        ("ask_user 호출", "ask_user 호출은 orchestrator 직접 처리 (contract v1 §6.3)"),
        ("우선순위 결정", "우선순위 결정은 orchestrator 직접 처리 (contract v1 §6.3)"),
        ("sub-agent 출력 통합/리뷰", "sub-agent 출력 통합/리뷰는 orchestrator 직접 처리 (contract v1 §6.3)"),
        ("PR 본문 작성", "PR 본문 작성은 orchestrator 직접 처리 (contract v1 §6.3)"),
    ]
    for brief, expected_reason in cases:
        decision = choose_role(_task("doc_draft", brief=brief))
        if not decision.must_not_delegate:
            raise AssertionError(f"brief={brief!r} should be §6.3 rejected, but was not")
        if decision.rejected_reason != expected_reason:
            raise AssertionError(
                f"brief={brief!r} reason mismatch:\n  expected: {expected_reason}\n  got: {decision.rejected_reason}"
            )
        if decision.role is not None:
            raise AssertionError(f"brief={brief!r} should have role=None, got {decision.role!r}")


def check_strict_mode_raises() -> None:
    """strict=True must raise DelegationRejected on §6.3 violation."""
    try:
        choose_role(_task("doc_draft", brief="handoff 갱신"), strict=True)
    except DelegationRejected as exc:
        if not exc.decision.must_not_delegate:
            raise AssertionError("DelegationRejected but decision.must_not_delegate is False")
        return
    raise AssertionError("strict=True on §6.3 should raise DelegationRejected")


def check_unknown_task_type_raises() -> None:
    """Unknown task_type must raise ValueError."""
    try:
        choose_role(_task("unknown_type_xyz"))
    except ValueError as exc:
        if "task_type" not in str(exc):
            raise AssertionError(f"ValueError should mention 'task_type', got: {exc}")
        return
    raise AssertionError("Unknown task_type should raise ValueError")


def check_marker_in_primary_artifact_also_rejected() -> None:
    """§6.3 markers in primary_artifact (not just brief) must also be rejected."""
    decision = choose_role(_task(
        "doc_draft",
        brief="draft something",
        primary_artifact="handoff-update.md",  # marker in path
    ))
    if not decision.must_not_delegate:
        raise AssertionError(
            "Marker in primary_artifact should also trigger §6.3 rejection"
        )


def check_non_must_not_delegate_brief_passes() -> None:
    """Brief that contains unrelated substring should NOT be rejected (regression
    against overly broad substring matching)."""
    # "비교" contains "교" which is in "통합/리뷰" — should NOT match
    decision = choose_role(_task(
        "doc_draft",
        brief="v0.5.3 release notes 와 비교하여 변경점 정리",
    ))
    if decision.must_not_delegate:
        raise AssertionError(
            f"비교 should NOT trigger §6.3 rejection, but got: {decision.rejected_reason}"
        )


def main() -> int:
    check_task_type_to_role_mapping()
    check_must_not_delegate_rejection()
    check_strict_mode_raises()
    check_unknown_task_type_raises()
    check_marker_in_primary_artifact_also_rejected()
    check_non_must_not_delegate_brief_passes()
    print(
        "Contract v1 §6.1/§6.3 delegator smoke check passed "
        "(4 task_type mappings, 7 must-not-delegate rejections, strict mode, "
        "unknown type, primary_artifact marker, non-match baseline)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
