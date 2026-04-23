#!/usr/bin/env python3
"""Smoke test the merge-doc-reconcile prototype."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "skills" / "merge-doc-reconcile" / "scripts" / "run_merge_doc_reconcile.py"

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from workflow_kit.common.output_contracts import validate_output_payload


def run_merge_doc_reconcile(*, expect_success: bool, args: list[str]) -> tuple[int, dict[str, object]]:
    completed = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if expect_success and completed.returncode != 0:
        raise AssertionError(
            f"Expected merge-doc-reconcile success but got {completed.returncode}: {completed.stderr}"
        )
    if not expect_success and completed.returncode == 0:
        raise AssertionError("Expected merge-doc-reconcile failure path but command succeeded.")
    return completed.returncode, json.loads(completed.stdout)


def main() -> int:
    example_root = REPO_ROOT / "examples" / "acme_delivery_platform"
    latest_backlog = sorted((example_root / "backlog").glob("*.md"))[-1]

    _, payload = run_merge_doc_reconcile(
        expect_success=True,
        args=[
            "--project-profile-path",
            str(example_root / "project_workflow_profile.md"),
            "--merge-result-summary",
            "delivery sync 관련 문서와 코드 변경이 병합됐다.",
            "--session-handoff-path",
            str(example_root / "session_handoff.md"),
            "--work-backlog-index-path",
            str(example_root / "work_backlog.md"),
            "--latest-backlog-path",
            str(latest_backlog),
            "--changed-file",
            "docs/operations/runbooks/delivery-sync.md",
            "--changed-file",
            "app/jobs/delivery_sync.py",
        ],
    )
    output_errors = validate_output_payload(payload, family="merge_doc_reconcile")
    if output_errors:
        raise AssertionError(f"Merge-doc-reconcile success payload violated output contract: {output_errors}")
    if payload["status"] != "ok":
        raise AssertionError("Expected ok status for merge-doc-reconcile success path.")
    if not payload["reconcile_targets"]:
        raise AssertionError("Expected reconcile targets.")
    if not payload["reconfirmation_points"]:
        raise AssertionError("Expected reconfirmation points.")
    if not payload["draft_reconcile_notes"]:
        raise AssertionError("Expected draft reconcile notes.")
    if not payload["validation_follow_up"]:
        raise AssertionError("Expected validation follow-up note.")

    failure_code, failure_payload = run_merge_doc_reconcile(
        expect_success=False,
        args=[
            "--project-profile-path",
            "/tmp/missing-project-profile.md",
            "--merge-result-summary",
            "병합 후 문서 상태를 재정리한다.",
        ],
    )
    if failure_code == 0:
        raise AssertionError("Expected merge-doc-reconcile failure for missing required document.")
    output_errors = validate_output_payload(failure_payload, family="merge_doc_reconcile")
    if output_errors:
        raise AssertionError(f"Merge-doc-reconcile error payload violated output contract: {output_errors}")
    if failure_payload["error_code"] != "missing_required_document":
        raise AssertionError("Expected missing_required_document error code.")

    print("Merge-doc-reconcile smoke check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
