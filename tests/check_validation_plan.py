#!/usr/bin/env python3
"""Smoke test the validation-plan prototype."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "skills" / "validation-plan" / "scripts" / "run_validation_plan.py"


def run_validation(example_name: str, changed_files: list[str], change_summary: str) -> dict[str, object]:
    example_root = REPO_ROOT / "examples" / example_name
    latest_backlog = sorted((example_root / "backlog").glob("*.md"))[-1]
    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT_PATH),
            "--project-profile-path",
            str(example_root / "project_workflow_profile.md"),
            "--session-handoff-path",
            str(example_root / "session_handoff.md"),
            "--latest-backlog-path",
            str(latest_backlog),
            *sum([["--changed-file", item] for item in changed_files], []),
            "--change-summary",
            change_summary,
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(completed.stdout)


def main() -> int:
    acme_payload = run_validation(
        "acme_delivery_platform",
        [
            "app/jobs/delivery_sync.py",
            "docs/operations/runbooks/delivery-sync.md",
        ],
        "delivery sync 재시도 로직과 운영 runbook 동시 수정",
    )
    detected = set(acme_payload["detected_change_types"])
    if not {"code", "docs", "ops"}.issubset(detected):
        raise AssertionError("Acme example should classify code/docs/ops changes.")
    levels = set(acme_payload["recommended_validation_levels"])
    if not {"standard", "release_sensitive"}.issubset(levels):
        raise AssertionError("Acme example should recommend standard and release-sensitive validation.")
    if not acme_payload["recommended_commands"]:
        raise AssertionError("Acme example should recommend at least one validation command.")

    research_payload = run_validation(
        "research_eval_hub",
        [
            "evals/pipelines/report_builder.py",
            "docs/evals/reports/release-report-v2.md",
        ],
        "evaluation report builder 로직과 release report 동시 수정",
    )
    research_detected = set(research_payload["detected_change_types"])
    if not {"code", "docs", "prompt_or_eval"}.issubset(research_detected):
        raise AssertionError("Research example should classify code/docs/prompt_or_eval changes.")
    if "artifact_sensitive" not in research_payload["recommended_validation_levels"]:
        raise AssertionError("Research example should recommend artifact-sensitive validation.")
    if not research_payload["documentation_checks"]:
        raise AssertionError("Research example should include documentation checks.")

    print("Validation-plan smoke check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
