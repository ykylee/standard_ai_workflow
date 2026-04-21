#!/usr/bin/env python3
"""Run the post-bootstrap onboarding flow for an existing project adoption."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from workflow_kit import __version__ as TOOL_VERSION
from workflow_kit.common.errors import build_error_result
from workflow_kit.common.paths import resolve_existing_path
from workflow_kit.common.runner import (
    build_orchestration_plan,
    build_step_error_context,
    build_worker_assignment,
    collect_step_warnings,
    current_python_executable,
    repeated_flag_args,
    run_json_command,
    WorkflowStepError,
)
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
    source_context = {
        "project_profile_path": str(Path(args.project_profile_path).resolve()),
        "session_handoff_path": str(Path(args.session_handoff_path).resolve()),
        "work_backlog_index_path": str(Path(args.work_backlog_index_path).resolve()),
        "backlog_dir_path": str(Path(args.backlog_dir_path).resolve()),
        "repository_assessment_path": (
            str(Path(args.repository_assessment_path).resolve()) if args.repository_assessment_path else None
        ),
        "latest_backlog_path": str(Path(args.latest_backlog_path).resolve()) if args.latest_backlog_path else None,
        "changed_files": args.changed_files,
        "change_summary": args.change_summary,
    }

    try:
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
                step_name="latest_backlog",
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
            step_name="session_start",
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
            step_name="validation_plan",
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
            step_name="code_index_update",
        )
    except WorkflowStepError as exc:
        result = build_error_result(
            tool_version=TOOL_VERSION,
            error=exc.error,
            error_code="workflow_step_failed",
            warnings=list(exc.payload.get("warnings", [])) if exc.payload else [],
            source_context=build_step_error_context(step_error=exc, source_context=source_context),
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1
    except FileNotFoundError as exc:
        result = build_error_result(
            tool_version=TOOL_VERSION,
            error=str(exc),
            error_code="missing_required_document",
            warnings=[],
            source_context=source_context,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1
    except Exception as exc:
        result = build_error_result(
            tool_version=TOOL_VERSION,
            error=str(exc),
            error_code="existing_project_onboarding_runtime_error",
            warnings=[],
            source_context=source_context,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1

    orchestration_plan = build_orchestration_plan(
        model_split={
            "orchestrator": "main",
            "doc_worker": "small",
            "validation_worker": "small",
        },
        worker_assignments=[
            build_worker_assignment(
                worker="doc-worker",
                model="small",
                responsibilities=[
                    "repository assessment 와 workflow 문서 비교",
                    "handoff 와 latest backlog 기준선 차이 확인",
                    "허브 문서와 index 후보 요약",
                ],
                backing_steps=["session_start", "code_index_update"],
            ),
            build_worker_assignment(
                worker="validation-worker",
                model="small",
                responsibilities=[
                    "초기 검증 수준과 미실행 항목 정리",
                    "추정 명령 검토",
                    "증빙 기록 위치 제안",
                ],
                backing_steps=["validation_plan"],
            ),
        ],
        integration_notes=[
            "메인 오케스트레이터는 assessment, session-start, validation, index 결과를 합쳐 첫 후속 작업 순서를 결정한다.",
            "기존 프로젝트 온보딩 초기에는 bounded 탐색과 문서 정렬을 small worker 에 맡기고, 최종 판단은 main 에 남기는 편이 안전하다.",
        ],
    )

    warnings = collect_step_warnings(
        latest_backlog_data,
        session_start,
        validation_plan,
        code_index_update,
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
        "warnings": warnings,
        "onboarding_mode": "existing_project_followup",
        "orchestration_plan": orchestration_plan,
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
