#!/usr/bin/env python3
"""Prototype runner for the doc-sync skill."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from workflow_kit import __version__ as TOOL_VERSION
from workflow_kit.common.doc_sync import build_doc_sync_candidates
from workflow_kit.common.errors import build_error_result
from workflow_kit.common.paths import project_workspace_root, resolve_existing_path
from workflow_kit.common.project_docs import parse_project_profile_core


def build_candidates(
    *,
    project_root: Path,
    profile: dict[str, Any],
    changed_files: list[str],
    session_handoff_path: Path | None,
    work_backlog_index_path: Path | None,
    latest_backlog_path: Path | None,
    change_summary: str | None,
) -> dict[str, Any]:
    return build_doc_sync_candidates(
        project_root=project_root,
        profile=profile,
        changed_files=changed_files,
        session_handoff_path=session_handoff_path,
        work_backlog_index_path=work_backlog_index_path,
        latest_backlog_path=latest_backlog_path,
        change_summary=change_summary,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the doc-sync prototype.")
    parser.add_argument("--project-profile-path", required=True)
    parser.add_argument("--changed-file", action="append", dest="changed_files", default=[])
    parser.add_argument("--session-handoff-path")
    parser.add_argument("--work-backlog-index-path")
    parser.add_argument("--latest-backlog-path")
    parser.add_argument("--change-summary")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source_context = {
        "project_profile_path": args.project_profile_path,
        "changed_files": args.changed_files,
        "change_summary": args.change_summary,
        "session_handoff_path": args.session_handoff_path,
        "work_backlog_index_path": args.work_backlog_index_path,
        "latest_backlog_path": args.latest_backlog_path,
    }

    if not args.changed_files and not args.change_summary:
        result = build_error_result(
            tool_version=TOOL_VERSION,
            error="변경 입력이 없어 doc-sync 후보를 구성할 수 없다.",
            error_code="missing_change_input",
            warnings=["최소 하나의 changed file 또는 change summary 가 필요하다."],
            source_context=source_context,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1

    try:
        project_profile_path = resolve_existing_path(args.project_profile_path)
        profile = parse_project_profile_core(project_profile_path)
        project_root = project_workspace_root(project_profile_path)

        session_handoff_path = resolve_existing_path(args.session_handoff_path) if args.session_handoff_path else None
        work_backlog_index_path = (
            resolve_existing_path(args.work_backlog_index_path) if args.work_backlog_index_path else None
        )
        latest_backlog_path = resolve_existing_path(args.latest_backlog_path) if args.latest_backlog_path else None

        result = build_candidates(
            project_root=project_root,
            profile=profile,
            changed_files=args.changed_files,
            session_handoff_path=session_handoff_path,
            work_backlog_index_path=work_backlog_index_path,
            latest_backlog_path=latest_backlog_path,
            change_summary=args.change_summary,
        )
        result["status"] = "ok"
        result["tool_version"] = TOOL_VERSION
        result["source_context"] = {
            "project_profile_path": str(project_profile_path),
            "changed_files": args.changed_files,
            "change_summary": args.change_summary,
        }
    except FileNotFoundError as exc:
        result = build_error_result(
            tool_version=TOOL_VERSION,
            error="doc-sync 에 필요한 입력 문서를 읽을 수 없다.",
            error_code="missing_required_document",
            warnings=["프로젝트 프로파일 또는 선택 입력 경로를 다시 확인해야 한다."],
            source_context=source_context | {"missing_path_detail": str(exc)},
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1
    except Exception as exc:
        result = build_error_result(
            tool_version=TOOL_VERSION,
            error="doc-sync 실행 중 예기치 않은 오류가 발생했다.",
            error_code="doc_sync_runtime_error",
            warnings=["입력 값과 문서 후보 추천 로직을 점검한 뒤 다시 실행해야 한다."],
            source_context=source_context | {"exception_type": type(exc).__name__},
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
