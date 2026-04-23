#!/usr/bin/env python3
"""Smoke test the demo workflow runner success and failure paths."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

if str(Path(__file__).resolve().parents[1]) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from workflow_kit.common.output_contracts import validate_output_payload


REPO_ROOT = Path(__file__).resolve().parents[1]
DEMO_SCRIPT = REPO_ROOT / "scripts" / "run_demo_workflow.py"


def run_json(cmd: list[str], *, expect_success: bool) -> tuple[int, dict[str, object]]:
    completed = subprocess.run(
        [sys.executable, *cmd],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if expect_success and completed.returncode != 0:
        raise AssertionError(f"Expected success but got exit code {completed.returncode}: {completed.stderr}")
    if not expect_success and completed.returncode == 0:
        raise AssertionError("Expected failure path but command succeeded.")
    return completed.returncode, json.loads(completed.stdout)


def check_success_path() -> None:
    _, payload = run_json([str(DEMO_SCRIPT), "--example-project", "acme_delivery_platform"], expect_success=True)
    if payload["status"] != "ok":
        raise AssertionError("Demo workflow success payload should have ok status.")
    output_errors = validate_output_payload(payload, family="demo_workflow")
    if output_errors:
        raise AssertionError(f"Demo workflow success payload violated output contract: {output_errors}")
    if payload["orchestration_plan"]["model_split"]["orchestrator"] != "main":
        raise AssertionError("Expected main orchestrator model split.")
    if len(payload["orchestration_plan"]["worker_assignments"]) < 3:
        raise AssertionError("Expected specialized worker assignments in orchestration plan.")
    if payload["runner_inputs"]["task"]["task_id"] != "TASK-021":
        raise AssertionError("Expected runner_inputs to preserve task metadata.")
    if len(payload["execution_trace"]) != 8:
        raise AssertionError("Expected execution_trace to record all eight orchestration steps.")
    if payload["execution_trace"][0]["step"] != "latest_backlog":
        raise AssertionError("Expected latest_backlog to appear first in execution_trace.")
    if "recommended_validation_levels" not in payload["execution_trace"][4]["produced_keys"]:
        raise AssertionError("Expected validation_plan trace to expose produced keys.")
    if not payload["workflow_summary"]["recommended_validation_levels"]:
        raise AssertionError("Expected workflow summary validation levels.")
    if payload["source_context"]["example_project"] != "acme_delivery_platform":
        raise AssertionError("Expected source_context example_project to be preserved.")
    if not payload["merge_doc_reconcile"]["reconcile_targets"]:
        raise AssertionError("Expected merge_doc_reconcile targets in success payload.")


def check_failure_path() -> None:
    _, payload = run_json(
        [str(DEMO_SCRIPT), "--project-profile-path", "/tmp/missing-profile.md"],
        expect_success=False,
    )
    if payload["status"] != "error":
        raise AssertionError("Demo workflow failure payload should have error status.")
    if payload["error_code"] != "workflow_step_failed":
        raise AssertionError("Expected workflow_step_failed error code.")
    if payload["source_context"]["failed_step"] != "session_start":
        raise AssertionError("Expected session_start to be reported as failed_step.")
    if payload["source_context"]["upstream_error_code"] != "missing_required_document":
        raise AssertionError("Expected upstream missing_required_document error code.")
    if "failed_command" not in payload["source_context"]:
        raise AssertionError("Expected failed command metadata in runner failure source_context.")
    if not payload["warnings"]:
        raise AssertionError("Expected propagated warnings from the failing child step.")


def main() -> int:
    check_success_path()
    check_failure_path()
    print("Demo workflow smoke check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
