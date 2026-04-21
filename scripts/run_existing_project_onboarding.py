#!/usr/bin/env python3
"""Run the post-bootstrap onboarding flow for an existing project adoption."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

TOOL_VERSION = "prototype-v1"

REPO_ROOT = Path(__file__).resolve().parents[1]

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from workflow_kit.common.paths import resolve_existing_path
from workflow_kit.common.runner import current_python_executable, repeated_flag_args, run_json_command
from workflow_kit.common.text import (
    extract_list_after_label,
    extract_section_value,
    iter_lines,
)
def repo_path(*parts: str) -> Path:
    return REPO_ROOT.joinpath(*parts).resolve()


def parse_repository_assessment(path: Path) -> dict[str, Any]:
    lines = iter_lines(path)
    return {
        "project_name": extract_section_value(lines, "분석 대상 프로젝트"),
        "analysis_mode": extract_section_value(lines, "분석 모드"),
        "primary_stack": extract_section_value(lines, "추정 기본 스택"),
        "stack_labels": extract_section_value(lines, "감지된 스택 라벨"),
        "install_command": extract_section_value(lines, "설치"),
        "run_command": extract_section_value(lines, "로컬 실행"),
        "quick_test_command": extract_section_value(lines, "빠른 테스트"),
        "isolated_test_command": extract_section_value(lines, "격리 테스트"),
        "smoke_check_command": extract_section_value(lines, "실행 확인"),
        "top_level_entries": extract_section_value(lines, "상위 디렉터리 항목"),
        "source_dirs": extract_section_value(lines, "소스 디렉터리 후보"),
        "docs_dirs": extract_section_value(lines, "문서 디렉터리 후보"),
        "test_dirs": extract_section_value(lines, "테스트 디렉터리 후보"),
        "sample_paths": extract_list_after_label(lines, "분석 중 확인한 경로 샘플"),
    }
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the existing-project onboarding flow after bootstrap generation."
    )
    parser.add_argument("--project-profile-path", required=True)
    parser.add_argument("--session-handoff-path", required=True)
    parser.add_argument("--work-backlog-index-path", required=True)
    parser.add_argument("--backlog-dir-path", required=True)
    parser.add_argument("--repository-assessment-path")
    parser.add_argument("--latest-backlog-path")
    parser.add_argument("--changed-file", action="append", dest="changed_files", default=[])
    parser.add_argument(
        "--change-summary",
        default="기존 프로젝트 도입 초안과 추정 명령/문서 구조를 실제 저장소 기준으로 정렬한다.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    python = current_python_executable()

    project_profile_path = resolve_existing_path(args.project_profile_path)
    session_handoff_path = resolve_existing_path(args.session_handoff_path)
    work_backlog_index_path = resolve_existing_path(args.work_backlog_index_path)
    backlog_dir_path = resolve_existing_path(args.backlog_dir_path)
    repository_assessment_path = (
        resolve_existing_path(args.repository_assessment_path) if args.repository_assessment_path else None
    )

    assessment: dict[str, Any] | None = None
    if repository_assessment_path:
        assessment = parse_repository_assessment(repository_assessment_path)

    latest_backlog_data: dict[str, Any]
    if args.latest_backlog_path:
        latest_backlog_path = resolve_existing_path(args.latest_backlog_path)
        latest_backlog_data = {
            "status": "ok",
            "tool_version": TOOL_VERSION,
            "latest_backlog_path": str(latest_backlog_path),
            "candidates": [str(latest_backlog_path)],
            "warnings": [],
        }
    else:
        latest_backlog_data = run_json_command(
            [
                python,
                str(repo_path("mcp", "latest-backlog", "scripts", "run_latest_backlog.py")),
                "--work-backlog-index-path",
                str(work_backlog_index_path),
                "--backlog-dir-path",
                str(backlog_dir_path),
            ],
            REPO_ROOT,
        )
        latest_backlog_path = Path(latest_backlog_data["latest_backlog_path"]).resolve()

    session_start = run_json_command(
        [
            python,
            str(repo_path("skills", "session-start", "scripts", "run_session_start.py")),
            "--session-handoff-path",
            str(session_handoff_path),
            "--work-backlog-index-path",
            str(work_backlog_index_path),
            "--project-profile-path",
            str(project_profile_path),
            "--latest-backlog-path",
            str(latest_backlog_path),
        ],
        REPO_ROOT,
    )

    validation_plan = run_json_command(
        [
            python,
            str(repo_path("skills", "validation-plan", "scripts", "run_validation_plan.py")),
            "--project-profile-path",
            str(project_profile_path),
            "--session-handoff-path",
            str(session_handoff_path),
            "--latest-backlog-path",
            str(latest_backlog_path),
            *repeated_flag_args("--changed-file", args.changed_files),
            "--change-summary",
            args.change_summary,
        ],
        REPO_ROOT,
    )

    code_index_update = run_json_command(
        [
            python,
            str(repo_path("skills", "code-index-update", "scripts", "run_code_index_update.py")),
            "--project-profile-path",
            str(project_profile_path),
            "--work-backlog-index-path",
            str(work_backlog_index_path),
            "--session-handoff-path",
            str(session_handoff_path),
            *repeated_flag_args("--changed-file", args.changed_files),
            "--change-summary",
            args.change_summary,
        ],
        REPO_ROOT,
    )

    onboarding_summary = {
        "review_assessment_first": repository_assessment_path is not None,
        "primary_stack": assessment.get("primary_stack") if assessment else None,
        "inferred_commands": {
            "install": assessment.get("install_command") if assessment else None,
            "run": assessment.get("run_command") if assessment else None,
            "quick_test": assessment.get("quick_test_command") if assessment else None,
            "isolated_test": assessment.get("isolated_test_command") if assessment else None,
            "smoke_check": assessment.get("smoke_check_command") if assessment else None,
        },
        "recommended_next_steps": [
            "repository assessment 의 추정 명령과 문서 경로를 실제 저장소 기준으로 먼저 확정한다.",
            "session-start 결과를 기준으로 handoff 와 최신 backlog 의 현재 상태를 맞춘다.",
            "validation-plan 에서 제안한 검증 수준과 미실행 항목 기록 위치를 검토한다.",
            "code-index-update 가 추천한 README/허브/index 후보를 우선순위 순서대로 재확인한다.",
        ],
    }

    result = {
        "status": "ok",
        "tool_version": TOOL_VERSION,
        "onboarding_mode": "existing_project_followup",
        "repository_assessment": {
            "path": str(repository_assessment_path) if repository_assessment_path else None,
            "summary": assessment,
        },
        "latest_backlog": latest_backlog_data,
        "session_start": session_start,
        "validation_plan": validation_plan,
        "code_index_update": code_index_update,
        "onboarding_summary": onboarding_summary,
        "source_context": {
            "project_profile_path": str(project_profile_path),
            "session_handoff_path": str(session_handoff_path),
            "work_backlog_index_path": str(work_backlog_index_path),
            "backlog_dir_path": str(backlog_dir_path),
            "changed_files": args.changed_files,
            "change_summary": args.change_summary,
        },
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
