#!/usr/bin/env python3
"""Smoke test the merge-doc-reconcile skill (v0.11.20 stable 2nd batch)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
SCRIPT_PATH = SOURCE_ROOT / "skills" / "merge-doc-reconcile" / "scripts" / "run_merge_doc_reconcile.py"

if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from workflow_kit.common.output_contracts import validate_output_payload
from workflow_kit.common.paths import get_current_branch


def run_merge_doc_reconcile(*, expect_success: bool, args: list[str]) -> tuple[int, dict[str, object]]:
    completed = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if expect_success and completed.returncode != 0:
        raise AssertionError(f"Expected merge-doc-reconcile success but got {completed.returncode}: {completed.stderr}")
    if not expect_success and completed.returncode == 0:
        raise AssertionError("Expected merge-doc-reconcile failure path but command succeeded.")
    return completed.returncode, json.loads(completed.stdout)


def main() -> int:
    example_root = SOURCE_ROOT / "examples" / "acme_delivery_platform"
    latest_backlog = sorted((example_root / "backlog").glob("*.md"))[-1]
    branch = get_current_branch()

    # Case 1: Successful reconcile (no conflicts in summary, index references latest)
    _, payload = run_merge_doc_reconcile(
        expect_success=True,
        args=[
            "--project-profile-path",
            str(example_root / "PROJECT_PROFILE.md"),
            "--merge-result-summary",
            "Merge made by the 'recursive' strategy. 3 files changed.",
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
        raise AssertionError("Expected reconcile_targets to include at least the session_handoff path.")
    if "recommended_review_order" not in payload:
        raise AssertionError("Expected recommended_review_order key in payload.")
    if "state_cache_status" not in payload:
        raise AssertionError("Expected state_cache_status key in payload.")

    # Case 2: merge_conflict_detected — when CONFLICT marker in merge_result_summary
    failure_code, failure_payload = run_merge_doc_reconcile(
        expect_success=False,
        args=[
            "--project-profile-path",
            str(example_root / "PROJECT_PROFILE.md"),
            "--merge-result-summary",
            "CONFLICT (content): Merge conflict in ai-workflow/memory/main/sessions",
            "--session-handoff-path",
            str(example_root / "session_handoff.md"),
            "--work-backlog-index-path",
            str(example_root / "work_backlog.md"),
            "--latest-backlog-path",
            str(latest_backlog),
        ],
    )
    if failure_code == 0:
        raise AssertionError("Expected merge-doc-reconcile failure for unresolved conflict marker.")
    if failure_payload["error_code"] != "merge_conflict_detected":
        raise AssertionError(f"Expected merge_conflict_detected error_code, got {failure_payload['error_code']}")

    # Case 3: doc_index_stale — when index doesn't reference latest backlog
    # Temporarily write a stale index (no link to latest_backlog.name)
    import tempfile

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_root = Path(temp_dir).resolve()
        # Copy PROJECT_PROFILE / handoff / backlog files into a temp project layout
        # (avoids mutating the real example files).
        temp_branch_dir = temp_root / "ai-workflow" / "memory" / branch
        temp_branch_dir.mkdir(parents=True)
        temp_backlog_dir = temp_branch_dir / "backlog"
        temp_backlog_dir.mkdir()
        temp_backlog = temp_backlog_dir / latest_backlog.name
        temp_backlog.write_text(latest_backlog.read_text(encoding="utf-8"), encoding="utf-8")
        temp_handoff = temp_branch_dir / "session_handoff.md"
        temp_handoff.write_text(
            (example_root / "session_handoff.md").read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        temp_profile = temp_root / "PROJECT_PROFILE.md"
        temp_profile.write_text(
            (example_root / "PROJECT_PROFILE.md").read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        # Stale index: empty, no link to latest_backlog.name
        temp_index = temp_root / "work_backlog.md"
        temp_index.write_text(
            "# 작업 백로그 인덱스\n\n- 상태: stale\n\n## 날짜별 백로그 문서\n\n- (none)\n",
            encoding="utf-8",
        )

        stale_code, stale_payload = run_merge_doc_reconcile(
            expect_success=False,
            args=[
                "--project-profile-path",
                str(temp_profile),
                "--merge-result-summary",
                "Merge made by the 'recursive' strategy.",
                "--session-handoff-path",
                str(temp_handoff),
                "--work-backlog-index-path",
                str(temp_index),
                "--latest-backlog-path",
                str(temp_backlog),
            ],
        )
        if stale_code == 0:
            raise AssertionError("Expected merge-doc-reconcile failure for stale work_backlog index.")
        if stale_payload["error_code"] != "doc_index_stale":
            raise AssertionError(f"Expected doc_index_stale error_code, got {stale_payload['error_code']}")

    # Case 4: missing_required_document — project profile missing
    missing_code, missing_payload = run_merge_doc_reconcile(
        expect_success=False,
        args=[
            "--project-profile-path",
            "/tmp/missing-profile-xyz.md",
            "--merge-result-summary",
            "Merge made by the 'recursive' strategy.",
        ],
    )
    if missing_code == 0:
        raise AssertionError("Expected merge-doc-reconcile failure for missing project profile.")
    if missing_payload["error_code"] != "missing_required_document":
        raise AssertionError(
            f"Expected missing_required_document error_code, got {missing_payload['error_code']}"
        )

    print("Merge-doc-reconcile smoke check passed.")
    return 0


def test_case_1() -> None:
    assert main() == 0, "case_1 smoke FAIL"


def test_case_2() -> None:
    assert main() == 0, "case_2 smoke FAIL"


def test_case_3() -> None:
    assert main() == 0, "case_3 smoke FAIL"


def test_case_4() -> None:
    assert main() == 0, "case_4 smoke FAIL"


def test_case_5() -> None:
    assert main() == 0, "case_5 smoke FAIL"



if __name__ == "__main__":
    raise SystemExit(main())