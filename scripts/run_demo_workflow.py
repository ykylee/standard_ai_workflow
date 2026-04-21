#!/usr/bin/env python3
"""Run the end-to-end workflow demo against the example project."""

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

from workflow_kit.common.runner import current_python_executable, repeated_flag_args, run_json_command
def repo_path(*parts: str) -> Path:
    return REPO_ROOT.joinpath(*parts).resolve()


EXAMPLE_PRESETS = {
    "acme_delivery_platform": {
        "project_profile_path": repo_path("examples", "acme_delivery_platform", "project_workflow_profile.md"),
        "session_handoff_path": repo_path("examples", "acme_delivery_platform", "session_handoff.md"),
        "work_backlog_index_path": repo_path("examples", "acme_delivery_platform", "work_backlog.md"),
        "backlog_dir_path": repo_path("examples", "acme_delivery_platform", "backlog"),
        "task_id": "TASK-021",
        "task_name": "배송 상태 동기화 실패 대응 절차 문서 정리",
        "task_brief": "runbook 및 handoff 반영 상태를 점검했다.",
        "task_status": "in_progress",
        "changed_files": [
            "app/jobs/delivery_sync.py",
            "docs/operations/runbooks/delivery-sync.md",
        ],
        "merge_result_summary": "runbook 링크와 상태 문서가 함께 수정된 브랜치 병합 후 재정리",
    },
    "research_eval_hub": {
        "project_profile_path": repo_path("examples", "research_eval_hub", "project_workflow_profile.md"),
        "session_handoff_path": repo_path("examples", "research_eval_hub", "session_handoff.md"),
        "work_backlog_index_path": repo_path("examples", "research_eval_hub", "work_backlog.md"),
        "backlog_dir_path": repo_path("examples", "research_eval_hub", "backlog"),
        "task_id": "TASK-044",
        "task_name": "평가 리포트 패키지와 실험 메타데이터 정합성 점검",
        "task_brief": "release report 와 manifest 기준선을 재확인했다.",
        "task_status": "in_progress",
        "changed_files": [
            "evals/pipelines/report_builder.py",
            "docs/evals/reports/release-report-v2.md",
        ],
        "merge_result_summary": "평가 리포트와 실험 메타데이터 문서가 함께 갱신된 브랜치 병합 후 재정리",
    },
}
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the workflow kit end-to-end demo.")
    parser.add_argument(
        "--example-project",
        choices=sorted(EXAMPLE_PRESETS),
        default="acme_delivery_platform",
        help="Use one of the bundled example projects as the default input set.",
    )
    parser.add_argument(
        "--project-profile-path",
        default=None,
    )
    parser.add_argument(
        "--session-handoff-path",
        default=None,
    )
    parser.add_argument(
        "--work-backlog-index-path",
        default=None,
    )
    parser.add_argument(
        "--backlog-dir-path",
        default=None,
    )
    parser.add_argument("--latest-backlog-path")
    parser.add_argument(
        "--task-id",
        default=None,
    )
    parser.add_argument(
        "--task-name",
        default=None,
    )
    parser.add_argument(
        "--task-brief",
        default=None,
    )
    parser.add_argument(
        "--task-status",
        default=None,
    )
    parser.add_argument(
        "--changed-file",
        action="append",
        dest="changed_files",
        default=None,
    )
    parser.add_argument(
        "--merge-result-summary",
        default=None,
    )
    args = parser.parse_args()
    preset = EXAMPLE_PRESETS[args.example_project]
    args.project_profile_path = args.project_profile_path or str(preset["project_profile_path"])
    args.session_handoff_path = args.session_handoff_path or str(preset["session_handoff_path"])
    args.work_backlog_index_path = args.work_backlog_index_path or str(preset["work_backlog_index_path"])
    args.backlog_dir_path = args.backlog_dir_path or str(preset["backlog_dir_path"])
    args.task_id = args.task_id or str(preset["task_id"])
    args.task_name = args.task_name or str(preset["task_name"])
    args.task_brief = args.task_brief or str(preset["task_brief"])
    args.task_status = args.task_status or str(preset["task_status"])
    args.changed_files = list(args.changed_files or preset["changed_files"])
    args.merge_result_summary = args.merge_result_summary or str(preset["merge_result_summary"])
    return args


def main() -> int:
    args = parse_args()
    python = current_python_executable()

    latest_backlog_data: dict[str, Any]
    if args.latest_backlog_path:
        latest_backlog_path = Path(args.latest_backlog_path).resolve()
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
                args.work_backlog_index_path,
                "--backlog-dir-path",
                args.backlog_dir_path,
            ],
            REPO_ROOT,
        )
    latest_backlog_path = latest_backlog_data.get("latest_backlog_path")

    session_start = run_json_command(
        [
            python,
            str(repo_path("skills", "session-start", "scripts", "run_session_start.py")),
            "--session-handoff-path",
            args.session_handoff_path,
            "--work-backlog-index-path",
            args.work_backlog_index_path,
            "--project-profile-path",
            args.project_profile_path,
            *(["--latest-backlog-path", latest_backlog_path] if latest_backlog_path else []),
        ],
        REPO_ROOT,
    )

    backlog_update = run_json_command(
        [
            python,
            str(repo_path("skills", "backlog-update", "scripts", "run_backlog_update.py")),
            "--project-profile-path",
            args.project_profile_path,
            "--daily-backlog-path",
            latest_backlog_path or "",
            "--mode",
            "update",
            "--task-id",
            args.task_id,
            "--task-name",
            args.task_name,
            "--task-brief",
            args.task_brief,
            "--status",
            args.task_status,
        ],
        REPO_ROOT,
    )

    doc_sync = run_json_command(
        [
            python,
            str(repo_path("skills", "doc-sync", "scripts", "run_doc_sync.py")),
            "--project-profile-path",
            args.project_profile_path,
            "--session-handoff-path",
            args.session_handoff_path,
            "--work-backlog-index-path",
            args.work_backlog_index_path,
            *(["--latest-backlog-path", latest_backlog_path] if latest_backlog_path else []),
            *repeated_flag_args("--changed-file", args.changed_files),
            "--change-summary",
            " / ".join(args.changed_files),
        ],
        REPO_ROOT,
    )

    validation_plan = run_json_command(
        [
            python,
            str(repo_path("skills", "validation-plan", "scripts", "run_validation_plan.py")),
            "--project-profile-path",
            args.project_profile_path,
            "--session-handoff-path",
            args.session_handoff_path,
            *(["--latest-backlog-path", latest_backlog_path] if latest_backlog_path else []),
            *repeated_flag_args("--changed-file", args.changed_files),
            "--change-summary",
            " / ".join(args.changed_files),
        ],
        REPO_ROOT,
    )

    code_index_update = run_json_command(
        [
            python,
            str(repo_path("skills", "code-index-update", "scripts", "run_code_index_update.py")),
            "--project-profile-path",
            args.project_profile_path,
            "--work-backlog-index-path",
            args.work_backlog_index_path,
            "--session-handoff-path",
            args.session_handoff_path,
            *repeated_flag_args("--changed-file", args.changed_files),
            "--change-summary",
            " / ".join(args.changed_files),
        ],
        REPO_ROOT,
    )

    suggest_impacted_docs = run_json_command(
        [
            python,
            str(repo_path("mcp", "suggest-impacted-docs", "scripts", "run_suggest_impacted_docs.py")),
            *repeated_flag_args("--changed-file", args.changed_files),
            "--session-handoff-path",
            args.session_handoff_path,
            *(["--latest-backlog-path", latest_backlog_path] if latest_backlog_path else []),
            "--work-backlog-index-path",
            args.work_backlog_index_path,
        ],
        REPO_ROOT,
    )

    merge_doc_reconcile = run_json_command(
        [
            python,
            str(repo_path("skills", "merge-doc-reconcile", "scripts", "run_merge_doc_reconcile.py")),
            "--project-profile-path",
            args.project_profile_path,
            "--session-handoff-path",
            args.session_handoff_path,
            "--work-backlog-index-path",
            args.work_backlog_index_path,
            *(["--latest-backlog-path", latest_backlog_path] if latest_backlog_path else []),
            "--merge-result-summary",
            args.merge_result_summary,
            *repeated_flag_args("--changed-file", args.changed_files),
        ],
        REPO_ROOT,
    )

    result = {
        "status": "ok",
        "tool_version": TOOL_VERSION,
        "example_project": args.example_project,
        "project_profile_path": str(Path(args.project_profile_path).resolve()),
        "latest_backlog": latest_backlog_data,
        "session_start": session_start,
        "backlog_update": backlog_update,
        "doc_sync": doc_sync,
        "validation_plan": validation_plan,
        "code_index_update": code_index_update,
        "suggest_impacted_docs": suggest_impacted_docs,
        "merge_doc_reconcile": merge_doc_reconcile,
        "workflow_summary": {
            "current_baseline": session_start.get("summary", []),
            "target_backlog_path": backlog_update.get("target_backlog_path"),
            "primary_impacted_documents": doc_sync.get("impacted_documents", []),
            "recommended_validation_levels": validation_plan.get("recommended_validation_levels", []),
            "priority_index_candidates": code_index_update.get("priority_index_candidates", []),
            "reconcile_targets": merge_doc_reconcile.get("reconcile_targets", []),
        },
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
