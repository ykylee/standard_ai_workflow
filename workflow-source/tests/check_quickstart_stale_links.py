#!/usr/bin/env python3
"""Smoke test the check_quickstart_stale_links MCP prototype."""

from __future__ import annotations

#: 이 검사의 입력 표면 (spec `core/test_impact_tiering_spec.md` §2).
#: 게이트 채취 실측에서 뽑아 넓은 쪽으로 올렸다 — 좁으면 meta-watch 가 red 로 잡는다.
WATCHES = (
    "workflow-source/examples/*",
    "workflow-source/mcp_servers/check-quickstart-stale-links/scripts/*",
    "workflow-source/mcp_servers/lib/*",
    "workflow-source/pyproject.toml",
    "workflow-source/workflow_kit/*",
)

import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
SCRIPT_PATH = SOURCE_ROOT / "mcp_servers" / "check-quickstart-stale-links" / "scripts" / "run_check_quickstart_stale_links.py"


def main() -> int:
    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT_PATH),
            "--quickstart-path",
            str(SOURCE_ROOT / "examples" / "bootstrap_output_samples.md"),
            "--project-profile-path",
            str(SOURCE_ROOT / "templates" / "project_workflow_profile_template.md"),
            "--session-handoff-path",
            str(SOURCE_ROOT / "examples" / "README.md"),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    payload = json.loads(completed.stdout)
    if not payload["checked_files"]:
        raise AssertionError("Expected checked quickstart files.")
    if payload["broken_links"]:
        raise AssertionError("Expected no broken links in bootstrap_output_samples.md.")
    if not payload["missing_expected_links"]:
        raise AssertionError("Expected at least one missing expected link warning.")
    if not payload["stale_link_warnings"]:
        raise AssertionError("Expected stale link warnings.")
    print("Quickstart stale link smoke check passed.")
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
