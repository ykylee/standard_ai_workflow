#!/usr/bin/env python3
import os
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT / "ai-workflow") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "ai-workflow"))

from workflow_kit.common.workflow_state import build_state_cache_refresh_hint


def main() -> int:
    original_branch = os.environ.get("CODEX_WORKFLOW_BRANCH")
    os.environ["CODEX_WORKFLOW_BRANCH"] = "codex/phase6"
    try:
        hint = build_state_cache_refresh_hint(
            project_profile_path=(REPO_ROOT / "docs" / "PROJECT_PROFILE.md").resolve(),
            latest_backlog_path=(
                REPO_ROOT / "ai-workflow" / "memory" / "codex" / "phase6" / "backlog" / "2026-05-01.md"
            ).resolve(),
            repository_assessment_path=(REPO_ROOT / "ai-workflow" / "memory" / "repository_assessment.md").resolve(),
        )
    finally:
        if original_branch is None:
            os.environ.pop("CODEX_WORKFLOW_BRANCH", None)
        else:
            os.environ["CODEX_WORKFLOW_BRANCH"] = original_branch

    command = hint["refresh_command"]
    expected_parts = [
        "python3 " + str(REPO_ROOT / "ai-workflow" / "scripts" / "generate_workflow_state.py"),
        "--project-profile-path " + str(REPO_ROOT / "docs" / "PROJECT_PROFILE.md"),
        "--session-handoff-path " + str(REPO_ROOT / "ai-workflow" / "memory" / "codex" / "phase6" / "session_handoff.md"),
        "--work-backlog-index-path " + str(REPO_ROOT / "ai-workflow" / "memory" / "work_backlog.md"),
        "--output-path " + str(REPO_ROOT / "ai-workflow" / "memory" / "codex" / "phase6" / "state.json"),
        "--latest-backlog-path " + str(REPO_ROOT / "ai-workflow" / "memory" / "codex" / "phase6" / "backlog" / "2026-05-01.md"),
        "--repository-assessment-path " + str(REPO_ROOT / "ai-workflow" / "memory" / "repository_assessment.md"),
    ]
    for expected in expected_parts:
        if expected not in command:
            raise AssertionError(f"missing refresh command part: {expected}\nactual: {command}")

    stale_parts = [
        "python3 scripts/generate_workflow_state.py",
        "--work-backlog-index-path " + str(REPO_ROOT / "docs" / "work_backlog.md"),
    ]
    for stale in stale_parts:
        if stale in command:
            raise AssertionError(f"stale refresh command part remained: {stale}\nactual: {command}")

    if hint["state_path"] != str(REPO_ROOT / "ai-workflow" / "memory" / "codex" / "phase6" / "state.json"):
        raise AssertionError(f"unexpected state path: {hint['state_path']}")

    print("workflow state refresh hint check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
