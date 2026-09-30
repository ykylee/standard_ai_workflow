#!/usr/bin/env python3
"""
v0.7.26: F-7 (check_workflow_linter branch detection fix) smoke test (6/6 PASS)

Test cases:
1. test_detached_head_short_sha_fallback — CI 의 detached HEAD → 7-char commit SHA (not "main")
2. test_normal_branch_unchanged — main / feat/* 정상
3. test_env_override_still_works — CODEX_WORKFLOW_BRANCH / GITHUB_HEAD_REF / GITHUB_REF_NAME
4. test_unsafe_env_falls_back — CODEX_WORKFLOW_BRANCH="../bad" + detached → main
5. test_git_failure_falls_back — git 명령 fail → "main"
6. test_local_detached_head_uses_default_branch — CI 밖 detached HEAD → 기본 브랜치
   (TASK-2026-09-30-claude-session-start-e6eb83-002: Codex worktree 는 detached HEAD 라 sha slug 가 커밋마다
   바뀌어 메모리 네임스페이스가 고아가 됐다)
"""
from __future__ import annotations

#: 이 검사의 입력 표면 (spec `core/test_impact_tiering_spec.md` §2).
#: 게이트 채취 실측에서 뽑아 넓은 쪽으로 올렸다 — 좁으면 meta-watch 가 red 로 잡는다.
WATCHES = (
    "workflow-source/pyproject.toml",
    "workflow-source/workflow_kit/*",
)

import json
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from workflow_kit.common.paths import get_current_branch, _usable_branch_name, BRANCH_ENV_KEYS, CI_ENV_KEYS

#: 브랜치 env 와 CI env 를 함께 비운다 — detached HEAD 의 답이 CI 여부에 달려서
#: (TASK-2026-09-30-claude-session-start-e6eb83-002), 러너의 env 가 판정에 새면 호스트마다 결과가 갈린다.
_ENV_KEYS = (*BRANCH_ENV_KEYS, *CI_ENV_KEYS)


def _clean_branch_env() -> dict[str, str]:
    saved = {k: v for k, v in os.environ.items() if k in _ENV_KEYS}
    for k in _ENV_KEYS:
        os.environ.pop(k, None)
    return saved


def _restore_branch_env(saved: dict[str, str]) -> None:
    for k in _ENV_KEYS:
        os.environ.pop(k, None)
    os.environ.update(saved)


# === Test 1: detached HEAD → short SHA ===
def test_detached_head_short_sha_fallback() -> bool:
    """CI 의 detached HEAD ('HEAD') → 7-char commit SHA (not 'main')."""
    saved = _clean_branch_env()
    try:
        os.environ["CI"] = "true"
        # mock: abbrev-ref returns "HEAD", rev-parse --short=7 returns "abc1234"
        with patch("subprocess.check_output") as mock_check:
            mock_check.side_effect = [
                "HEAD\n",  # abbrev-ref
                "abc1234\n",  # short SHA
            ]
            result = get_current_branch()
            if result != "abc1234":
                print(f"  FAIL: expected 'abc1234' (short SHA), got {result!r}")
                return False
            if mock_check.call_count != 2:
                print(f"  FAIL: expected 2 git calls (abbrev-ref + short SHA), got {mock_check.call_count}")
                return False
        print("  PASS: detached HEAD → 7-char commit SHA")
        return True
    finally:
        _restore_branch_env(saved)


# === Test 2: normal branch unchanged ===
def test_normal_branch_unchanged() -> bool:
    """main / feat/* 정상 — detached HEAD 의 fix 가 *normal* branch 에 영향 없음."""
    saved = _clean_branch_env()
    try:
        with patch("subprocess.check_output", return_value="main\n"):
            result = get_current_branch()
            if result != "main":
                print(f"  FAIL: expected 'main', got {result!r}")
                return False
        with patch("subprocess.check_output", return_value="feat/foo\n"):
            result = get_current_branch()
            if result != "feat/foo":
                print(f"  FAIL: expected 'feat/foo', got {result!r}")
                return False
        with patch("subprocess.check_output", return_value="release/v0.7.25\n"):
            result = get_current_branch()
            if result != "release/v0.7.25":
                print(f"  FAIL: expected 'release/v0.7.25', got {result!r}")
                return False
        print("  PASS: normal branches (main / feat/* / release/*) unchanged")
        return True
    finally:
        _restore_branch_env(saved)


# === Test 3: env override still works ===
def test_env_override_still_works() -> bool:
    """env key (CODEX_WORKFLOW_BRANCH, GITHUB_HEAD_REF, GITHUB_REF_NAME) 가 여전히 우선."""
    saved = _clean_branch_env()
    try:
        # 1. CODEX_WORKFLOW_BRANCH
        os.environ["CODEX_WORKFLOW_BRANCH"] = "codex/test-f7"
        with patch("subprocess.check_output", return_value="HEAD\n"):
            result = get_current_branch()
            if result != "codex/test-f7":
                print(f"  FAIL: CODEX_WORKFLOW_BRANCH not respected: {result!r}")
                return False
        os.environ.pop("CODEX_WORKFLOW_BRANCH", None)
        # 2. GITHUB_HEAD_REF
        os.environ["GITHUB_HEAD_REF"] = "feature/from-pr"
        with patch("subprocess.check_output", return_value="HEAD\n"):
            result = get_current_branch()
            if result != "feature/from-pr":
                print(f"  FAIL: GITHUB_HEAD_REF not respected: {result!r}")
                return False
        os.environ.pop("GITHUB_HEAD_REF", None)
        # 3. GITHUB_REF_NAME (with refs/heads/ prefix)
        os.environ["GITHUB_REF_NAME"] = "refs/heads/release/v0.7.26"
        with patch("subprocess.check_output", return_value="HEAD\n"):
            result = get_current_branch()
            if result != "release/v0.7.26":
                print(f"  FAIL: GITHUB_REF_NAME (with prefix) not respected: {result!r}")
                return False
        os.environ.pop("GITHUB_REF_NAME", None)
        print("  PASS: env override (3 keys) respected")
        return True
    finally:
        _restore_branch_env(saved)


# === Test 4: unsafe env + detached → main ===
def test_unsafe_env_falls_back() -> bool:
    """unsafe env (e.g. '../bad') + detached HEAD ('HEAD') + short SHA fail → 'main'."""
    saved = _clean_branch_env()
    try:
        os.environ["CI"] = "true"
        os.environ["CODEX_WORKFLOW_BRANCH"] = "../bad"
        with patch("subprocess.check_output", side_effect=[
            "HEAD\n",  # abbrev-ref returns HEAD
            subprocess.CalledProcessError(1, ["git", "rev-parse"]),  # short SHA fail
        ]):
            result = get_current_branch()
            if result != "main":
                print(f"  FAIL: expected 'main' fallback, got {result!r}")
                return False
        print("  PASS: unsafe env + detached HEAD + short SHA fail → 'main'")
        return True
    finally:
        _restore_branch_env(saved)


# === Test 5: git command failure → main ===
def test_git_failure_falls_back() -> bool:
    """git 명령 fail (FileNotFoundError / CalledProcessError) → 'main'."""
    saved = _clean_branch_env()
    try:
        # 1. abbrev-ref raises CalledProcessError
        with patch("subprocess.check_output", side_effect=subprocess.CalledProcessError(1, ["git"])):
            result = get_current_branch()
            if result != "main":
                print(f"  FAIL: expected 'main' fallback on CalledProcessError, got {result!r}")
                return False
        # 2. abbrev-ref raises FileNotFoundError (git not installed)
        with patch("subprocess.check_output", side_effect=FileNotFoundError):
            result = get_current_branch()
            if result != "main":
                print(f"  FAIL: expected 'main' fallback on FileNotFoundError, got {result!r}")
                return False
        print("  PASS: git failure (CalledProcessError / FileNotFoundError) → 'main'")
        return True
    finally:
        _restore_branch_env(saved)


# === Test 6: CI 밖 detached HEAD → 기본 브랜치 ===
def test_local_detached_head_uses_default_branch() -> bool:
    """CI env 가 없으면 detached HEAD 는 sha 가 아니라 기본 브랜치다.

    sha 로 돌아가면(되주입) 커밋마다 `active/<sha>/` 가 새로 생긴다 — 110차 실측의
    `active/6545f13/state.json` 이 그 모양이다.
    """
    saved = _clean_branch_env()
    try:
        with patch("subprocess.check_output", side_effect=["HEAD\n", "abc1234\n"]), \
                patch("workflow_kit.path_resolver._detect_default_branch", return_value="trunk"):
            result = get_current_branch()
        if result != "trunk":
            print(f"  FAIL: expected default branch 'trunk', got {result!r} (sha 면 커밋마다 네임스페이스가 바뀐다)")
            return False
        os.environ["CI"] = "false"  # 값이 false 면 CI 가 아니다
        with patch("subprocess.check_output", side_effect=["HEAD\n", "abc1234\n"]), \
                patch("workflow_kit.path_resolver._detect_default_branch", return_value="trunk"):
            result = get_current_branch()
        if result != "trunk":
            print(f"  FAIL: CI=false 인데 CI 로 판정했다: {result!r}")
            return False
        print("  PASS: 로컬 detached HEAD → 기본 브랜치")
        return True
    finally:
        _restore_branch_env(saved)


# === Main ===
def main() -> int:
    print("=" * 60)
    print("F-7 (branch detection fix) smoke test (v0.7.26)")
    print("=" * 60)

    tests = [
        test_detached_head_short_sha_fallback,
        test_normal_branch_unchanged,
        test_env_override_still_works,
        test_unsafe_env_falls_back,
        test_git_failure_falls_back,
        test_local_detached_head_uses_default_branch,
    ]
    passed = 0
    for test in tests:
        print(f"\n{test.__name__}:")
        if test():
            passed += 1

    print()
    print("=" * 60)
    print(f"Result: {passed}/{len(tests)} PASS")
    print("=" * 60)
    return 0 if passed == len(tests) else 1


if __name__ == "__main__":
    sys.exit(main())
