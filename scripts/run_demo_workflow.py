#!/usr/bin/env python3
"""Run the end-to-end workflow demo against the example project."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]


def repo_path(*parts: str) -> Path:
    return REPO_ROOT.joinpath(*parts).resolve()


def run_json(cmd: list[str]) -> dict[str, Any]:
    completed = subprocess.run(
        cmd,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(completed.stdout)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the workflow kit end-to-end demo.")
    parser.add_argument(
        "--project-profile-path",
        default=str(repo_path("examples", "acme_delivery_platform", "project_workflow_profile.md")),
    )
    parser.add_argument(
        "--session-handoff-path",
        default=str(repo_path("examples", "acme_delivery_platform", "session_handoff.md")),
    )
    parser.add_argument(
        "--work-backlog-index-path",
        default=str(repo_path("examples", "acme_delivery_platform", "work_backlog.md")),
    )
    parser.add_argument(
        "--backlog-dir-path",
        default=str(repo_path("examples", "acme_delivery_platform", "backlog")),
    )
    parser.add_argument("--latest-backlog-path")
    parser.add_argument(
        "--task-id",
        default="TASK-021",
    )
    parser.add_argument(
        "--task-name",
        default="배송 상태 동기화 실패 대응 절차 문서 정리",
    )
    parser.add_argument(
        "--task-brief",
        default="runbook 및 handoff 반영 상태를 점검했다.",
    )
    parser.add_argument(
        "--task-status",
        default="in_progress",
    )
    parser.add_argument(
        "--changed-file",
        action="append",
        dest="changed_files",
        default=["app/jobs/delivery_sync.py", "docs/operations/runbooks/delivery-sync.md"],
    )
    parser.add_argument(
        "--merge-result-summary",
        default="runbook 링크와 상태 문서가 함께 수정된 브랜치 병합 후 재정리",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    python = sys.executable

    latest_backlog_data: dict[str, Any]
    if args.latest_backlog_path:
        latest_backlog_path = Path(args.latest_backlog_path).resolve()
        latest_backlog_data = {
            "latest_backlog_path": str(latest_backlog_path),
            "candidates": [str(latest_backlog_path)],
            "warnings": [],
        }
    else:
        latest_backlog_data = run_json(
            [
                python,
                str(repo_path("mcp", "latest-backlog", "scripts", "run_latest_backlog.py")),
                "--work-backlog-index-path",
                args.work_backlog_index_path,
                "--backlog-dir-path",
                args.backlog_dir_path,
            ]
        )
    latest_backlog_path = latest_backlog_data.get("latest_backlog_path")

    session_start = run_json(
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
        ]
    )

    backlog_update = run_json(
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
        ]
    )

    doc_sync = run_json(
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
            *sum([["--changed-file", item] for item in args.changed_files], []),
            "--change-summary",
            " / ".join(args.changed_files),
        ]
    )

    suggest_impacted_docs = run_json(
        [
            python,
            str(repo_path("mcp", "suggest-impacted-docs", "scripts", "run_suggest_impacted_docs.py")),
            *sum([["--changed-file", item] for item in args.changed_files], []),
            "--session-handoff-path",
            args.session_handoff_path,
            *(["--latest-backlog-path", latest_backlog_path] if latest_backlog_path else []),
            "--work-backlog-index-path",
            args.work_backlog_index_path,
        ]
    )

    merge_doc_reconcile = run_json(
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
            *sum([["--changed-file", item] for item in args.changed_files], []),
        ]
    )

    result = {
        "project_profile_path": str(Path(args.project_profile_path).resolve()),
        "latest_backlog": latest_backlog_data,
        "session_start": session_start,
        "backlog_update": backlog_update,
        "doc_sync": doc_sync,
        "suggest_impacted_docs": suggest_impacted_docs,
        "merge_doc_reconcile": merge_doc_reconcile,
        "workflow_summary": {
            "current_baseline": session_start.get("summary", []),
            "target_backlog_path": backlog_update.get("target_backlog_path"),
            "primary_impacted_documents": doc_sync.get("impacted_documents", []),
            "reconcile_targets": merge_doc_reconcile.get("reconcile_targets", []),
        },
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
