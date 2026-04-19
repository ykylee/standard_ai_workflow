#!/usr/bin/env python3
"""Smoke test the code-index-update prototype."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "skills" / "code-index-update" / "scripts" / "run_code_index_update.py"


def run_index_update(example_name: str, changed_files: list[str], change_summary: str) -> dict[str, object]:
    example_root = REPO_ROOT / "examples" / example_name
    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT_PATH),
            "--project-profile-path",
            str(example_root / "project_workflow_profile.md"),
            "--work-backlog-index-path",
            str(example_root / "work_backlog.md"),
            "--session-handoff-path",
            str(example_root / "session_handoff.md"),
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
    acme_payload = run_index_update(
        "acme_delivery_platform",
        [
            "app/jobs/delivery_sync.py",
            "docs/operations/runbooks/delivery-sync.md",
        ],
        "delivery sync 재시도 로직과 운영 runbook 동시 수정",
    )
    acme_priorities = set(acme_payload["priority_index_candidates"])
    if not any(item.endswith("docs/README.md") for item in acme_priorities):
        raise AssertionError("Acme example should elevate the declared document home as a priority index candidate.")
    if not any(item.endswith("docs/operations/README.md") for item in acme_priorities):
        raise AssertionError("Acme example should elevate the operations README candidate.")
    if not acme_payload["stale_index_warnings"]:
        raise AssertionError("Acme example should produce at least one stale index warning.")

    research_payload = run_index_update(
        "research_eval_hub",
        [
            "evals/pipelines/report_builder.py",
            "docs/evals/reports/release-report-v2.md",
        ],
        "evaluation report builder 로직과 release report 동시 수정",
    )
    research_candidates = set(research_payload["index_update_candidates"])
    if not any(item.endswith("docs/evals/README.md") for item in research_candidates):
        raise AssertionError("Research example should include the evals README candidate.")
    if not research_payload["document_structure_signals"]:
        raise AssertionError("Research example should include document structure signals.")

    print("Code-index-update smoke check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
