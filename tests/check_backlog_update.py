#!/usr/bin/env python3
"""Smoke test the backlog-update prototype."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "skills" / "backlog-update" / "scripts" / "run_backlog_update.py"

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from workflow_kit.common.output_contracts import validate_output_payload


def run_backlog_update(*, expect_success: bool, args: list[str]) -> tuple[int, dict[str, object]]:
    completed = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if expect_success and completed.returncode != 0:
        raise AssertionError(f"Expected backlog-update success but got {completed.returncode}: {completed.stderr}")
    if not expect_success and completed.returncode == 0:
        raise AssertionError("Expected backlog-update failure path but command succeeded.")
    return completed.returncode, json.loads(completed.stdout)


def main() -> int:
    example_root = REPO_ROOT / "examples" / "acme_delivery_platform"
    backlog_path = sorted((example_root / "backlog").glob("*.md"))[-1]

    _, payload = run_backlog_update(
        expect_success=True,
        args=[
            "--project-profile-path",
            str(example_root / "project_workflow_profile.md"),
            "--daily-backlog-path",
            str(backlog_path),
            "--task-name",
            "배송 상태 동기화 실패 대응 절차 문서 정리",
            "--task-brief",
            "runbook 및 handoff 반영 상태를 점검했다.",
            "--task-id",
            "TASK-021",
            "--mode",
            "update",
        ],
    )
    output_errors = validate_output_payload(payload, family="backlog_update")
    if output_errors:
        raise AssertionError(f"Backlog-update success payload violated output contract: {output_errors}")
    if payload["operation_type"] != "update_entry":
        raise AssertionError("Expected update_entry operation type.")
    if payload["status_recommendation"]["value"] != "in_progress":
        raise AssertionError("Expected conservative in_progress status recommendation.")
    if not payload["draft_entry"]:
        raise AssertionError("Expected non-empty backlog draft entry.")

    failure_code, failure_payload = run_backlog_update(
        expect_success=False,
        args=[
            "--project-profile-path",
            "/tmp/missing-profile.md",
            "--task-name",
            "운영 허브 링크 무결성 재점검",
            "--task-brief",
            "새 runbook 링크 반영 여부를 확인한다.",
        ],
    )
    if failure_code == 0:
        raise AssertionError("Expected backlog-update failure for missing profile path.")
    output_errors = validate_output_payload(failure_payload, family="backlog_update")
    if output_errors:
        raise AssertionError(f"Backlog-update error payload violated output contract: {output_errors}")
    if failure_payload["error_code"] != "missing_required_document":
        raise AssertionError("Expected missing_required_document error code.")

    print("Backlog-update smoke check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
