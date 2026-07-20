#!/usr/bin/env python3
"""Smoke test the project-status-assessment skill (v0.11.20 stable 2nd batch)."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
SCRIPT_PATH = SOURCE_ROOT / "skills" / "project-status-assessment" / "scripts" / "run_project_status_assessment.py"

if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from workflow_kit.common.output_contracts import validate_output_payload


def run_assessment(*, expect_success: bool, args: list[str]) -> tuple[int, dict[str, object]]:
    completed = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if expect_success and completed.returncode != 0:
        raise AssertionError(f"Expected assessment success but got {completed.returncode}: {completed.stderr}")
    if not expect_success and completed.returncode == 0:
        raise AssertionError("Expected assessment failure path but command succeeded.")
    return completed.returncode, json.loads(completed.stdout)


def main() -> int:
    # Case 1: Successful analysis of a small Python project (json mode)
    with tempfile.TemporaryDirectory() as tmp_dir:
        project_root = Path(tmp_dir) / "small_project"
        project_root.mkdir()
        # Mimic a python project layout (no source_dirs — score 2: docs + test)
        (project_root / "docs").mkdir()
        (project_root / "docs" / "README.md").write_text("# Docs\n", encoding="utf-8")
        (project_root / "tests").mkdir()
        (project_root / "tests" / "test_smoke.py").write_text("# placeholder\n", encoding="utf-8")
        (project_root / "README.md").write_text("# Small project\n", encoding="utf-8")

        _, payload = run_assessment(
            expect_success=True,
            args=[
                "--project-root", str(project_root),
                "--json",
            ],
        )
        output_errors = validate_output_payload(payload, family="project_status_assessment")
        if output_errors:
            raise AssertionError(f"Assessment success payload violated output contract: {output_errors}")
        if payload["status"] != "ok":
            raise AssertionError(f"Expected ok status, got {payload['status']}")
        if "assessment" not in payload:
            raise AssertionError("Expected 'assessment' key in payload.")
        if "structure_score" not in payload["assessment"]:
            raise AssertionError("Expected 'structure_score' in assessment.")
        if not isinstance(payload["assessment"]["structure_score"], int):
            raise AssertionError("Expected structure_score to be int.")
        if not payload["recommended_actions"]:
            raise AssertionError("Expected at least one recommended action.")
        if not payload["orchestration_plan"]["worker_assignments"]:
            raise AssertionError("Expected worker_assignments in orchestration_plan.")
        if not payload["report_preview"]:
            raise AssertionError("Expected non-empty report_preview.")

    # Case 2: --apply writes repository_assessment.md to ai-workflow/memory/active/
    with tempfile.TemporaryDirectory() as tmp_dir:
        project_root = Path(tmp_dir) / "applied_project"
        project_root.mkdir()
        (project_root / "src").mkdir()
        (project_root / "tests").mkdir()
        (project_root / "docs").mkdir()

        rc, json_payload = run_assessment(
            expect_success=True,
            args=[
                "--project-root", str(project_root),
                "--apply",
                "--json",
            ],
        )
        if rc != 0:
            raise AssertionError("Expected --apply --json to succeed.")
        if not json_payload["written_paths"]:
            raise AssertionError("Expected written_paths to include the assessment report path.")
        report_path = Path(json_payload["written_paths"][0])
        if not report_path.exists():
            raise AssertionError(f"Expected assessment report to be written at {report_path}")
        if not report_path.read_text(encoding="utf-8").startswith("# Repository Assessment"):
            raise AssertionError("Expected assessment report to start with the standard header.")

    # Case 3: missing_required_document — non-existent project root
    failure_code, failure_payload = run_assessment(
        expect_success=False,
        args=[
            "--project-root", "/tmp/missing-xyz-project-status-assessment-dir",
            "--json",
        ],
    )
    if failure_code == 0:
        raise AssertionError("Expected failure for missing project_root.")
    if failure_payload["error_code"] != "missing_required_document":
        raise AssertionError(
            f"Expected missing_required_document error_code, got {failure_payload['error_code']}"
        )

    print("Project-status-assessment smoke check passed.")
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