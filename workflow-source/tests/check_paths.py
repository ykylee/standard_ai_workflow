#!/usr/bin/env python3
"""Smoke test workflow path helpers."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from workflow_kit.common.paths import get_current_branch, workflow_branch_dir


BRANCH_ENV_KEYS = (
    "CODEX_WORKFLOW_BRANCH",
    "GITHUB_HEAD_REF",
    "GITHUB_REF_NAME",
    "CI_COMMIT_REF_NAME",
    "BRANCH_NAME",
)


def clean_branch_env() -> dict[str, str]:
    saved = {key: value for key, value in os.environ.items() if key in BRANCH_ENV_KEYS}
    for key in BRANCH_ENV_KEYS:
        os.environ.pop(key, None)
    return saved


def restore_branch_env(saved: dict[str, str]) -> None:
    for key in BRANCH_ENV_KEYS:
        os.environ.pop(key, None)
    os.environ.update(saved)


def main() -> int:
    saved_env = clean_branch_env()
    try:
        os.environ["CODEX_WORKFLOW_BRANCH"] = "codex/test-paths"
        with patch("subprocess.check_output", return_value="HEAD\n"):
            if get_current_branch() != "codex/test-paths":
                raise AssertionError("Expected CODEX_WORKFLOW_BRANCH to override detached git HEAD.")

        os.environ.pop("CODEX_WORKFLOW_BRANCH", None)
        os.environ["GITHUB_HEAD_REF"] = "feature/from-pr"
        with patch("subprocess.check_output", return_value="HEAD\n"):
            if get_current_branch() != "feature/from-pr":
                raise AssertionError("Expected GITHUB_HEAD_REF to be used for detached PR checkouts.")

        os.environ.pop("GITHUB_HEAD_REF", None)
        os.environ["GITHUB_REF_NAME"] = "refs/heads/release/beta-0.4.0"
        with patch("subprocess.check_output", return_value="HEAD\n"):
            if get_current_branch() != "release/beta-0.4.0":
                raise AssertionError("Expected refs/heads/ prefix to be normalized.")

        os.environ["CODEX_WORKFLOW_BRANCH"] = "../bad"
        os.environ.pop("GITHUB_REF_NAME", None)
        with patch("subprocess.check_output", return_value="HEAD\n"):
            if get_current_branch() != "main":
                raise AssertionError("Expected unsafe env branch and detached HEAD to fall back to main.")

        os.environ.pop("CODEX_WORKFLOW_BRANCH", None)
        with patch("subprocess.check_output", side_effect=subprocess.CalledProcessError(1, ["git"])):
            if get_current_branch() != "main":
                raise AssertionError("Expected git failures to fall back to main.")

        profile = REPO_ROOT / "docs" / "PROJECT_PROFILE.md"
        os.environ["CODEX_WORKFLOW_BRANCH"] = "codex/test-paths"
        branch_dir = workflow_branch_dir(profile)
        # `docs/PROJECT_PROFILE.md` 기준 branch dir 은 `memory/active/<branch>` 다.
        # 이전 기대값에는 `active/` 가 빠져 있었는데, 이는 workflow_memory_dir 의
        # docs/ 분기 버그(정식 bootstrap layout 과 한 단계 어긋남)를 그대로 굳힌
        # 것이었다. bootstrap 이 실제로 만드는 위치가 정답이다.
        expected = REPO_ROOT / "ai-workflow" / "memory" / "active" / "codex" / "test-paths"
        if branch_dir != expected.resolve():
            raise AssertionError(f"Expected branch dir {expected}, got {branch_dir}")
    finally:
        restore_branch_env(saved_env)

    print("Path helper checks passed.")
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
