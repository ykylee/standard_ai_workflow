#!/usr/bin/env python3
"""Smoke test the workflow-linter runner."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"


def _detect_branch_name() -> str:
    """Return the current git branch name with a safe fallback.

    Delegates to :func:`workflow_kit.common.paths.get_current_branch` so the
    test files and the linter look at the same ``ai-workflow/memory/<branch>/``
    directory. The function prefers CI-provided env vars, then falls back
    to ``git rev-parse`` anchored at the workflow kit repo, and finally
    defaults to ``main`` when nothing usable is available.
    """
    sys.path.insert(0, str(SOURCE_ROOT))
    from workflow_kit.common.paths import get_current_branch

    return get_current_branch()


BRANCH_NAME = _detect_branch_name()


def _memory_paths(project_root: Path) -> dict[str, Path]:
    """Return the standard memory paths under the current branch directory."""
    branch_root = project_root / "ai-workflow" / "memory" / BRANCH_NAME
    backlog_dir = branch_root / "backlog"
    backlog_dir.mkdir(parents=True, exist_ok=True)
    return {
        "state_json": project_root / "ai-workflow" / "memory" / "state.json",
        "handoff": branch_root / "session_handoff.md",
        "backlog": backlog_dir / "2026-04-26.md",
    }


def run_linter(project_root: Path, extra_args: list[str] = []) -> dict:
    project_profile_path = project_root / "docs" / "PROJECT_PROFILE.md"
    project_profile_path.parent.mkdir(parents=True, exist_ok=True)
    if not project_profile_path.exists():
        project_profile_path.write_text(
            "# Test Project Profile\n"
            "- 문서 목적: 테스트용 프로젝트 프로파일\n"
            "- 범위: 단위 테스트\n"
            "- 대상 독자: AI agent 테스트 러너\n"
            "- 상태: draft\n"
            "- 최종 수정일: 2026-01-01\n"
            "- 관련 문서: 없음\n"
        )

    cmd = [
        sys.executable,
        str(REPO_ROOT / "workflow-source/skills/workflow-linter/scripts/run_workflow_linter.py"),
        "--project-profile-path", str(project_profile_path),
    ] + extra_args
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(project_root))
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        print("STDOUT:", result.stdout)
        print("STDERR:", result.stderr)
        return {"status": "error", "error": "Failed to parse JSON output"}


def test_linter_pass():
    print("Testing linter pass case...")
    with tempfile.TemporaryDirectory() as tmp_dir:
        root = Path(tmp_dir)
        paths = _memory_paths(root)

        paths["state_json"].write_text(json.dumps({
            "source_of_truth": {"latest_backlog_path": str(paths["backlog"])},
            "session": {"in_progress_items": ["TASK-001 Test task"]},
            "project": {"project_name": "Test"}
        }))
        paths["handoff"].write_text(
            "## 1. 현재 작업 요약\n"
            "- 현재 기준선: Test\n"
            "- 현재 주 작업 축: Test\n\n"
            "## 2. 진행 중 작업\n"
            "- 현재 `in_progress` 작업:\n"
            "  - TASK-001 Test task"
        )
        paths["backlog"].write_text("## TASK-001 Test task\n- 상태: in_progress")

        # handoff 에서 프로젝트 루트로 올라가는 **유효한** 링크를 붙여, 린터가 이것을
        # broken 으로 오인하지 않는지 본다.
        #
        # 깊이를 상수로 박으면 안 된다. `<branch>` 가 `feature/x` 처럼 슬래시를 가지면
        # handoff 는 `ai-workflow/memory/feature/x/` 로 **한 단계 더 깊어**지고, 고정
        # 3 dot 은 루트에 못 닿아 `file_not_found` 위양성이 난다(슬래시 브랜치에서
        # 이 검사가 red 였던 이유). v0.11.20 이 4 dot → 3 dot 으로 고친 것도 같은
        # 부류의 상수 문제였다 — 상수를 바꾸는 대신 **실제 깊이에서 계산**한다.
        readme = root / "README.md"
        readme.write_text("Hello")
        depth = len(paths["handoff"].parent.relative_to(root).parts)
        up = "../" * depth
        paths["handoff"].write_text(
            paths["handoff"].read_text() + f"\n\n[README]({up}README.md)"
        )

        result = run_linter(root)
        if result["status"] != "ok":
            print(f"FAILED. Result: {json.dumps(result, indent=2, ensure_ascii=False)}")
        assert result["status"] == "ok", f"Expected ok, got {result['status']}"
        assert not result["issues"], f"Expected no issues, but found: {result['issues']}"
        print("✅ Pass case successful.")


def test_linter_fail_task_mismatch():
    print("Testing linter task mismatch case...")
    with tempfile.TemporaryDirectory() as tmp_dir:
        root = Path(tmp_dir)
        paths = _memory_paths(root)

        paths["state_json"].write_text(json.dumps({
            "source_of_truth": {"latest_backlog_path": str(paths["backlog"])},
            "session": {"in_progress_items": ["TASK-001 Test task"]},
            "project": {"project_name": "Test"}
        }))
        paths["handoff"].write_text(
            "## 1. 현재 작업 요약\n"
            "- 현재 기준선: Test\n"
            "- 현재 주 작업 축: Test\n\n"
            "## 2. 진행 중 작업\n"
            "- 현재 `in_progress` 작업:\n"
            "  - (Empty)"
        )
        paths["backlog"].write_text("## TASK-001 Test task\n- 상태: in_progress")

        result = run_linter(root)
        linter_status = "issues_found" if result.get("issues") else "ok"
        assert linter_status == "issues_found", f"Expected issues_found, got {linter_status}"
        task_issues = [i for i in result["issues"] if i["code"] == "task_status_mismatch"]
        assert task_issues, "Expected task status mismatch issue"
        print("✅ Task mismatch detection successful.")


def test_linter_fail_broken_link():
    print("Testing linter broken link case...")
    with tempfile.TemporaryDirectory() as tmp_dir:
        root = Path(tmp_dir)
        paths = _memory_paths(root)

        paths["state_json"].write_text(json.dumps({
            "source_of_truth": {"latest_backlog_path": str(paths["backlog"])},
            "session": {"in_progress_items": []},
            "project": {"project_name": "Test"}
        }))
        paths["handoff"].write_text(
            "## 1. 현재 작업 요약\n"
            "- 현재 기준선: Test\n"
            "- 현재 주 작업 축: Test\n\n"
            "[Non-existent File](../../missing.md)"
        )
        paths["backlog"].write_text("Nothing here")

        result = run_linter(root)
        linter_status = "issues_found" if result.get("issues") else "ok"
        assert linter_status == "issues_found", f"Expected issues_found, got {linter_status}"
        link_issues = [i for i in result["issues"] if i["code"] == "file_not_found"]
        assert link_issues, "Expected broken link issue"
        print("✅ Broken link detection successful.")


def test_missing_handoff_is_issue_not_warning() -> None:
    """handoff 부재는 warning 이 아니라 issue 다 (v1.0.2).

    이전에는 handoff 가 없어도 `status: ok / total_issues: 0` 이었다. 정합 검사가
    빈 dict 로 계속 돌아 *비교할 것이 없으니 통과* 했기 때문이다. 실제로 이
    저장소가 그 상태였고, 그 사이 session-start 는 아예 실행되지 못했다.
    """
    print("Testing missing-handoff case...")
    with tempfile.TemporaryDirectory() as tmp_dir:
        root = Path(tmp_dir)
        paths = _memory_paths(root)
        paths["state_json"].write_text(json.dumps({
            "source_of_truth": {"latest_backlog_path": str(paths["backlog"])},
            "session": {"in_progress_items": []},
            "project": {"project_name": "Test"},
        }))
        paths["backlog"].write_text("## TASK-001 Test task\n- 상태: done")
        # handoff 를 **만들지 않는다** — 그것이 이 test 의 조건이다.

        result = run_linter(root)
        missing = [i for i in result.get("issues", []) if i["code"] == "missing_required_document"]
        assert missing, f"handoff 부재가 issue 로 보고되지 않았다: {result.get('issues')}"
        assert result["status"] != "ok", f"문서가 없는데 status 가 ok 다: {result['status']}"
        assert result["summary"]["missing_documents"] >= 1, result["summary"]
        assert "session_handoff" in missing[0]["description"], missing[0]
        print("✅ Missing handoff reported as issue.")


def test_unreadable_handoff_is_issue() -> None:
    """읽히지 않는 handoff 도 issue 다 — 부재와 원인이 다르니 code 를 나눈다."""
    print("Testing unreadable-handoff case...")
    with tempfile.TemporaryDirectory() as tmp_dir:
        root = Path(tmp_dir)
        paths = _memory_paths(root)
        paths["state_json"].write_text(json.dumps({
            "source_of_truth": {"latest_backlog_path": str(paths["backlog"])},
            "session": {"in_progress_items": []},
            "project": {"project_name": "Test"},
        }))
        paths["backlog"].write_text("## TASK-001 Test task\n- 상태: done")
        # 디렉터리를 파일 자리에 둬서 파서가 읽지 못하게 한다.
        paths["handoff"].mkdir(parents=True, exist_ok=True)

        result = run_linter(root)
        codes = {i["code"] for i in result.get("issues", [])}
        assert codes & {"document_parse_failure", "missing_required_document"}, result.get("issues")
        assert result["status"] != "ok", result["status"]
        print("✅ Unreadable handoff reported as issue.")


if __name__ == "__main__":
    try:
        test_linter_pass()
        test_linter_fail_task_mismatch()
        test_linter_fail_broken_link()
        test_missing_handoff_is_issue_not_warning()
        test_unreadable_handoff_is_issue()
        print("\n🎉 All workflow-linter smoke tests passed!")
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)
