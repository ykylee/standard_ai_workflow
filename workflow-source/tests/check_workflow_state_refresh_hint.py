#!/usr/bin/env python3
"""build_state_cache_refresh_hint 의 refresh command 조립 검증.

v1.0.0: **temp fixture 로 격리**한다. 이전 구현은 실제 저장소의
`ai-workflow/memory/codex/phase6/session_handoff.md` 가 *존재하는 것* 에 의존했는데,
`build_state_cache_refresh_hint` 는 legacy path 를 `.exists()` 로 분기하므로
그 디렉터리가 정리되거나 아카이브되는 순간 조용히 red 가 됐다(실제 발생).
저장소 상태와 무관하게 동작을 검증하도록 fixture 를 직접 만든다.
"""
import os
import sys
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from workflow_kit.common.workflow_state import build_state_cache_refresh_hint

BRANCH = "codex/phase6"


def _build_fixture(root: Path) -> tuple[Path, Path, Path, Path]:
    """temp 저장소에 profile + branch 메모리 세트를 만든다.

    Returns: (profile_path, memory_root, branch_dir, latest_backlog_path)
    """
    (root / "docs").mkdir(parents=True, exist_ok=True)
    profile = root / "docs" / "PROJECT_PROFILE.md"
    profile.write_text("# profile\n", encoding="utf-8")

    memory_root = root / "ai-workflow" / "memory"
    branch_dir = memory_root / BRANCH
    (branch_dir / "backlog" / "tasks").mkdir(parents=True, exist_ok=True)
    (branch_dir / "sessions").mkdir(parents=True, exist_ok=True)
    # legacy path 는 존재할 때만 hint 에 포함된다 → 존재시켜 그 분기를 검증한다.
    (branch_dir / "session_handoff.md").write_text("# handoff\n", encoding="utf-8")
    (memory_root / "work_backlog.md").write_text("# index\n", encoding="utf-8")
    (memory_root / "repository_assessment.md").write_text("# assess\n", encoding="utf-8")
    latest = branch_dir / "backlog" / "2026-05-01.md"
    latest.write_text("# backlog\n", encoding="utf-8")
    return profile, memory_root, branch_dir, latest


def main() -> int:
    original_branch = os.environ.get("CODEX_WORKFLOW_BRANCH")
    os.environ["CODEX_WORKFLOW_BRANCH"] = BRANCH
    try:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            profile, memory_root, branch_dir, latest = _build_fixture(root)
            hint = build_state_cache_refresh_hint(
                project_profile_path=profile.resolve(),
                latest_backlog_path=latest.resolve(),
                repository_assessment_path=(memory_root / "repository_assessment.md").resolve(),
            )
            command = hint["refresh_command"]

            expected_parts = [
                # generator 경로도 workspace 기준으로 계산된다 (fixture 안이면 fixture 기준).
                "python3 " + str(root / "workflow-source" / "scripts" / "generate_workflow_state.py"),
                "--project-profile-path " + str(profile),
                # v0.14.0+ 신규 layout 인자 (branch-scoped)
                "--daily-backlog-dir " + str(branch_dir / "backlog"),
                "--tasks-dir " + str(branch_dir / "backlog" / "tasks"),
                "--sessions-dir " + str(branch_dir / "sessions"),
                # legacy 인자 — 파일이 존재하므로 포함되어야 한다
                "--session-handoff-path " + str(branch_dir / "session_handoff.md"),
                "--work-backlog-index-path " + str(memory_root / "work_backlog.md"),
                "--output-path " + str(branch_dir / "state.json"),
                "--latest-backlog-path " + str(latest),
                "--repository-assessment-path " + str(memory_root / "repository_assessment.md"),
            ]
            for expected in expected_parts:
                if expected not in command:
                    raise AssertionError(
                        f"missing refresh command part: {expected}\nactual: {command}")

            stale_parts = [
                "python3 scripts/generate_workflow_state.py",   # 상대경로 잔재
                "--work-backlog-index-path " + str(root / "docs" / "work_backlog.md"),
            ]
            for stale in stale_parts:
                if stale in command:
                    raise AssertionError(
                        f"stale refresh command part remained: {stale}\nactual: {command}")

            if hint["state_path"] != str(branch_dir / "state.json"):
                raise AssertionError(f"unexpected state path: {hint['state_path']}")
    finally:
        if original_branch is None:
            os.environ.pop("CODEX_WORKFLOW_BRANCH", None)
        else:
            os.environ["CODEX_WORKFLOW_BRANCH"] = original_branch

    print("workflow state refresh hint check passed")
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
