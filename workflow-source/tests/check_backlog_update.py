#!/usr/bin/env python3
"""Smoke test the backlog-update prototype."""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
SCRIPT_PATH = SOURCE_ROOT / "skills" / "backlog-update" / "scripts" / "run_backlog_update.py"

if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from workflow_kit.common.output_contracts import validate_output_payload
from workflow_kit.common.paths import get_current_branch


def run_backlog_update(*, expect_success: bool, args: list[str]) -> tuple[int, dict[str, object]]:
    completed = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if expect_success and completed.returncode != 0:
        raise AssertionError(f"Expected backlog-update success but got {completed.returncode}: {completed.stderr}")
    if not expect_success and completed.returncode == 0:
        raise AssertionError("Expected backlog-update failure path but command succeeded.")
    return completed.returncode, json.loads(completed.stdout)


def main() -> int:
    example_root = SOURCE_ROOT / "examples" / "acme_delivery_platform"
    backlog_path = sorted((example_root / "backlog").glob("*.md"))[-1]

    # Case 1: Standard update without --apply
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_root = Path(temp_dir).resolve()
        temp_project_root = (temp_root / "project").resolve()
        temp_project_root.mkdir()

        current_branch = get_current_branch()
        temp_branch_root = (temp_project_root / current_branch).resolve()
        temp_branch_root.mkdir(parents=True)

        for relative_path in ("PROJECT_PROFILE.md", "work_backlog.md"):
            source_path = example_root / relative_path
            target_path = temp_project_root / relative_path
            target_path.write_text(source_path.read_text(encoding="utf-8"), encoding="utf-8")

        source_path = example_root / "session_handoff.md"
        target_path = temp_branch_root / "session_handoff.md"
        target_path.write_text(source_path.read_text(encoding="utf-8"), encoding="utf-8")

        temp_backlog_dir = (temp_branch_root / "backlog").resolve()
        temp_backlog_dir.mkdir()
        temp_backlog_path = (temp_backlog_dir / backlog_path.name).resolve()
        temp_backlog_path.write_text(backlog_path.read_text(encoding="utf-8"), encoding="utf-8")

        _, payload = run_backlog_update(
            expect_success=True,
            args=[
                "--project-profile-path",
                str(temp_project_root / "PROJECT_PROFILE.md"),
                "--daily-backlog-path",
                str(temp_backlog_path),
                "--task-name",
                "배송 상태 동기화 실패 대응 절차 문서 정리",
                "--task-brief",
                "runbook 및 handoff 반영 상태를 점검했다.",
                "--task-id",
                "TASK-021",
                "--mode",
                "update",
            ],
        )

        output_errors = validate_output_payload(payload, family="backlog_update")
        if output_errors:
            raise AssertionError(f"Backlog-update success payload violated output contract: {output_errors}")
        if payload["operation_type"] != "update_entry":
            raise AssertionError("Expected update_entry operation type.")
        if payload["status_recommendation"]["value"] != "in_progress":
            raise AssertionError("Expected conservative in_progress status recommendation.")
        if not payload["draft_entry"]:
            raise AssertionError("Expected non-empty backlog draft entry.")

        if "state.json" not in payload["state_cache_update_note"]:
            raise AssertionError("Expected backlog-update to include a state cache refresh note.")
        if "generate_workflow_state.py" not in payload["state_cache_refresh_command"]:
            raise AssertionError("Expected backlog-update to include a state cache refresh command.")
        # v1.0.1: draft 모드는 **쓰지 않는다**. 이전 버전의 본 case 는 정반대를
        # 단언하고 있었다 — 초안만 달라는 호출이 state.json 을 만드는 dry-run 오염을
        # 테스트가 규약으로 굳혀 놓은 셈이었다. hint 는 그대로 내되 write 는 안 한다.
        if payload["state_cache_status"] != "skipped":
            raise AssertionError(f"Expected draft mode to skip the state.json write. Got: {payload['state_cache_status']}")

        for candidate in (
            (temp_project_root / "state.json").resolve(),
            (temp_branch_root / "state.json").resolve(),
        ):
            if candidate.exists():
                raise AssertionError(f"draft 모드가 state.json 을 만들었다: {candidate}")

    # Case 2: Update with --apply
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_root = Path(temp_dir).resolve()
        temp_project_root = (temp_root / "project").resolve()
        temp_project_root.mkdir()

        current_branch = get_current_branch()
        temp_branch_root = (temp_project_root / current_branch).resolve()
        temp_branch_root.mkdir(parents=True)

        for relative_path in ("PROJECT_PROFILE.md", "work_backlog.md"):
            source_path = example_root / relative_path
            target_path = temp_project_root / relative_path
            target_path.write_text(source_path.read_text(encoding="utf-8"), encoding="utf-8")

        source_path = example_root / "session_handoff.md"
        target_path = temp_branch_root / "session_handoff.md"
        target_path.write_text(source_path.read_text(encoding="utf-8"), encoding="utf-8")

        temp_backlog_dir = (temp_branch_root / "backlog").resolve()
        temp_backlog_dir.mkdir()
        temp_backlog_path = (temp_backlog_dir / backlog_path.name).resolve()
        temp_backlog_path.write_text(backlog_path.read_text(encoding="utf-8"), encoding="utf-8")

        _, apply_payload = run_backlog_update(
            expect_success=True,
            args=[
                "--project-profile-path",
                str(temp_project_root / "PROJECT_PROFILE.md"),
                "--daily-backlog-path",
                str(temp_backlog_path),
                "--work-backlog-index-path",
                str(temp_project_root / "work_backlog.md"),
                "--session-handoff-path",
                str(temp_project_root / "session_handoff.md"),
                "--task-name",
                "배송 상태 동기화 실패 대응 절차 문서 정리",
                "--task-brief",
                "검증 대기 상태라 차단으로 되돌렸다.",
                "--task-id",
                "TASK-021",
                "--mode",
                "update",
                "--status",
                "blocked",
                "--apply",
            ],
        )
        if apply_payload["apply_status"] != "applied":
            raise AssertionError("Expected backlog-update apply mode to report applied status.")

        # v1.0.1: write 는 apply 모드에서만. 그리고 branch-scoped 경로로 간다
        # (v1.0.0 에서 hint 만 옮겨지고 writer 는 legacy 에 남아 있던 결함의 회귀 방지).
        if apply_payload["state_cache_status"] != "refreshed":
            raise AssertionError(f"Expected apply mode to refresh state.json. Got: {apply_payload['state_cache_status']}")
        branch_state_path = (temp_branch_root / "state.json").resolve()
        if not branch_state_path.exists():
            raise AssertionError(f"Expected branch-scoped state.json at {branch_state_path}.")
        state_payload = json.loads(branch_state_path.read_text(encoding="utf-8"))
        expected_profile_path = str((temp_project_root / "PROJECT_PROFILE.md").resolve())
        actual_profile_rel = state_payload["source_of_truth"]["project_profile_path"]
        actual_profile_path = str((temp_project_root / actual_profile_rel).resolve())
        if actual_profile_path != expected_profile_path:
            raise AssertionError(f"Expected state.json to be refreshed from {expected_profile_path}, but got {actual_profile_path} (rel: {actual_profile_rel})")
        backlog_text = temp_backlog_path.read_text(encoding="utf-8")
        if "- 상태: blocked" not in backlog_text:
            raise AssertionError("Expected apply mode to update the backlog task status in the target file.")
        handoff_text = (temp_branch_root / "session_handoff.md").read_text(encoding="utf-8")
        if "TASK-021 배송 상태 동기화 실패 대응 절차 문서 정리" not in handoff_text:
            raise AssertionError("Expected apply mode to keep the task visible in handoff.")
        blocked_section = handoff_text.split("- 현재 `blocked` 작업:", 1)[1]
        if "TASK-021 배송 상태 동기화 실패 대응 절차 문서 정리" not in blocked_section:
            raise AssertionError("Expected apply mode to move the task into the blocked handoff section.")

        resolved_written_paths = [str(Path(p).resolve()) for p in apply_payload["written_paths"]]
        if str(temp_backlog_path.resolve()) not in resolved_written_paths:
            raise AssertionError(f"Expected apply mode to report the written backlog path. Got: {resolved_written_paths}")

        work_backlog_text = (temp_project_root / "work_backlog.md").read_text(encoding="utf-8")
        backlog_link_count = sum(
            1
            for line in work_backlog_text.splitlines()
            if line.strip() == f"- [{backlog_path.stem} 작업 백로그](./backlog/{backlog_path.name})"
        )
        if backlog_link_count != 1:
            raise AssertionError("Expected apply mode to keep only one backlog index link per daily backlog file.")

    # Case 3: Duplicate link cleanup with --apply
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_root = Path(temp_dir).resolve()
        temp_project_root = (temp_root / "project").resolve()
        temp_project_root.mkdir()

        current_branch = get_current_branch()
        temp_branch_root = (temp_project_root / current_branch).resolve()
        temp_branch_root.mkdir(parents=True)

        for relative_path in ("PROJECT_PROFILE.md", "work_backlog.md"):
            source_path = example_root / relative_path
            target_path = temp_project_root / relative_path
            target_path.write_text(source_path.read_text(encoding="utf-8"), encoding="utf-8")

        source_path = example_root / "session_handoff.md"
        target_path = temp_branch_root / "session_handoff.md"
        target_path.write_text(source_path.read_text(encoding="utf-8"), encoding="utf-8")

        temp_backlog_dir = (temp_branch_root / "backlog").resolve()
        temp_backlog_dir.mkdir()
        temp_backlog_path = (temp_backlog_dir / backlog_path.name).resolve()
        temp_backlog_path.write_text(backlog_path.read_text(encoding="utf-8"), encoding="utf-8")
        index_path = (temp_project_root / "work_backlog.md").resolve()
        current_branch = get_current_branch()
        canonical_rel_path = f"./{current_branch}/backlog/{backlog_path.name}"
        index_path = (temp_project_root / "work_backlog.md").resolve()
        index_text = index_path.read_text(encoding="utf-8")

        # Replace the existing link (which might be in the old format) with a duplicate in the new format
        # First, find what's actually in the index
        old_link_pattern = rf"- \[{backlog_path.stem} 작업 백로그\]\(\.\/backlog\/{backlog_path.name}\)"
        new_link = f"- [{backlog_path.stem} 작업 백로그]({canonical_rel_path})"

        index_text = re.sub(old_link_pattern, f"{new_link}\n{new_link}", index_text)
        index_path.write_text(index_text, encoding="utf-8")

        _, apply_payload = run_backlog_update(
            expect_success=True,
            args=[
                "--project-profile-path",
                str(temp_project_root / "PROJECT_PROFILE.md"),
                "--daily-backlog-path",
                str(temp_backlog_path),
                "--work-backlog-index-path",
                str(index_path),
                "--session-handoff-path",
                str(temp_branch_root / "session_handoff.md"),
                "--task-name",
                "배송 상태 동기화 실패 대응 절차 문서 정리",
                "--task-brief",
                "중복 링크를 자동 정리하는지 확인한다.",
                "--task-id",
                "TASK-021",
                "--mode",
                "update",
                "--apply",
            ],
        )
        if apply_payload["apply_status"] != "applied":
            raise AssertionError("Expected apply mode to succeed while cleaning duplicate backlog links.")
        normalized_lines = [
            line.strip()
            for line in index_path.read_text(encoding="utf-8").splitlines()
            if line.strip().startswith("- [") and backlog_path.name in line
        ]
        if len(normalized_lines) != 1:
            raise AssertionError("Expected duplicate backlog links to be collapsed to one canonical entry.")

    # Case 4: Failure path (missing profile)
    failure_code, failure_payload = run_backlog_update(
        expect_success=False,
        args=[
            "--project-profile-path",
            "/tmp/missing-profile.md",
            "--task-name",
            "운영 허브 링크 무결성 재점검",
            "--task-brief",
            "새 runbook 링크 반영 여부를 확인한다.",
        ],
    )
    if failure_code == 0:
        raise AssertionError("Expected backlog-update failure for missing profile path.")
    output_errors = validate_output_payload(failure_payload, family="backlog_update")
    if output_errors:
        raise AssertionError(f"Backlog-update error payload violated output contract: {output_errors}")
    if failure_payload["error_code"] != "missing_required_document":
        raise AssertionError("Expected missing_required_document error code.")

    _check_auto_mode_creates_unknown_id()

    print("Backlog-update smoke check passed.")
    return 0


def _check_auto_mode_creates_unknown_id() -> None:
    """`--mode auto` + 아직 없는 `--task-id` → **create** (v1.0.2).

    이전에는 `--task-id` 가 있으면 무조건 update 로 잡혀서, 새 작업을 등록하려 하면
    `cannot_determine` 이 되어 **아무것도 쓰지 않은 채 `status: ok`** 를 냈다. 세션
    종료 절차대로 작업을 등록하려던 호출이 조용히 무시된 것이다 (실제로 이 저장소의
    close-out 에서 겪었다). auto 의 뜻은 "있으면 갱신, 없으면 생성" 이므로 존재
    여부를 실제로 보고 정해야 한다.
    """
    example_root = SOURCE_ROOT / "examples" / "acme_delivery_platform"
    backlog_path = sorted((example_root / "backlog").glob("*.md"))[-1]

    with tempfile.TemporaryDirectory() as temp_dir:
        project_root = (Path(temp_dir) / "project").resolve()
        branch_root = (project_root / get_current_branch()).resolve()
        branch_root.mkdir(parents=True)
        for relative_path in ("PROJECT_PROFILE.md", "work_backlog.md"):
            (project_root / relative_path).write_text(
                (example_root / relative_path).read_text(encoding="utf-8"), encoding="utf-8"
            )
        (branch_root / "session_handoff.md").write_text(
            (example_root / "session_handoff.md").read_text(encoding="utf-8"), encoding="utf-8"
        )
        backlog_dir = branch_root / "backlog"
        backlog_dir.mkdir()
        daily = backlog_dir / backlog_path.name
        daily.write_text(backlog_path.read_text(encoding="utf-8"), encoding="utf-8")

        base_args = [
            "--project-profile-path", str(project_root / "PROJECT_PROFILE.md"),
            "--daily-backlog-path", str(daily),
        ]

        # 없는 ID → create
        _, payload = run_backlog_update(expect_success=True, args=[
            *base_args,
            "--task-id", "TASK-2026-07-27-auto-901",
            "--task-name", "auto 모드 신규 등록",
            "--task-brief", "존재하지 않는 ID 를 auto 로 등록한다.",
        ])
        if payload["operation_type"] not in ("create_entry", "create_daily_backlog"):
            raise AssertionError(
                "auto 모드가 없는 ID 를 create 로 잡지 않았다: "
                f"operation_type={payload['operation_type']!r}, warnings={payload.get('warnings')}"
            )

        # 있는 ID → update (반대 방향으로 넓히지 않았는지)
        _, payload2 = run_backlog_update(expect_success=True, args=[
            *base_args,
            "--task-id", "TASK-021",
            "--task-name", "배송 상태 동기화 실패 대응 절차 문서 정리",
            "--task-brief", "이미 있는 ID 는 갱신이어야 한다.",
        ])
        if payload2["operation_type"] != "update_entry":
            raise AssertionError(
                f"auto 모드가 있는 ID 를 update 로 잡지 않았다: {payload2['operation_type']!r}"
            )


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
