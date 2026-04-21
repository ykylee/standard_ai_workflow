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

from workflow_kit.common.doc_sync import build_doc_sync_candidates
from workflow_kit.common.paths import resolve_existing_path
from workflow_kit.common.project_docs import parse_project_profile_core

TOOL_VERSION = "prototype-v1"
def build_candidates(
    *,
    base_dir: Path,
    profile: dict[str, Any],
    changed_files: list[str],
    session_handoff_path: Path | None,
    work_backlog_index_path: Path | None,
    latest_backlog_path: Path | None,
    change_summary: str | None,
) -> dict[str, Any]:
    return build_doc_sync_candidates(
        base_dir=base_dir,
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
    if not args.changed_files and not args.change_summary:
        raise SystemExit("at least one --changed-file or --change-summary is required")

    project_profile_path = resolve_existing_path(args.project_profile_path)
    profile = parse_project_profile_core(project_profile_path)
    base_dir = project_profile_path.parent

    session_handoff_path = resolve_existing_path(args.session_handoff_path) if args.session_handoff_path else None
    work_backlog_index_path = (
        resolve_existing_path(args.work_backlog_index_path) if args.work_backlog_index_path else None
    )
    latest_backlog_path = resolve_existing_path(args.latest_backlog_path) if args.latest_backlog_path else None

    result = build_candidates(
        base_dir=base_dir,
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
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
