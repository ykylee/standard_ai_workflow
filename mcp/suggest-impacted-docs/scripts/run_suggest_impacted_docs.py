#!/usr/bin/env python3
"""Prototype runner for suggest_impacted_docs MCP."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from workflow_kit import __version__ as TOOL_VERSION
from workflow_kit.common.change_types import classify_impacted_doc_file
from workflow_kit.common.paths import resolve_existing_path


def dedupe(items: list[str]) -> list[str]:
    seen = set()
    result = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            result.append(item)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Run suggest_impacted_docs MCP prototype.")
    parser.add_argument("--changed-file", action="append", dest="changed_files", default=[])
    parser.add_argument("--session-handoff-path")
    parser.add_argument("--latest-backlog-path")
    parser.add_argument("--work-backlog-index-path")
    args = parser.parse_args()

    if not args.changed_files:
        raise SystemExit("at least one --changed-file is required")

    impacted_documents = []
    reasoning_notes = []
    warnings = []

    if args.session_handoff_path:
        impacted_documents.append(str(resolve_existing_path(args.session_handoff_path)))
    if args.latest_backlog_path:
        impacted_documents.append(str(resolve_existing_path(args.latest_backlog_path)))
    if args.work_backlog_index_path:
        impacted_documents.append(str(resolve_existing_path(args.work_backlog_index_path)))

    for changed in args.changed_files:
        kind = classify_impacted_doc_file(changed)
        reasoning_notes.append(f"`{changed}` 는 `{kind}` 유형 변경으로 해석했다.")
        if kind in {"code", "config"} and not any(
            [args.session_handoff_path, args.latest_backlog_path, args.work_backlog_index_path]
        ):
            warnings.append("코드/설정 변경이지만 상태 문서 후보 경로가 제공되지 않았다.")
        if kind == "doc":
            impacted_documents.append(changed)

    print(
        json.dumps(
            {
                "status": "ok",
                "tool_version": TOOL_VERSION,
                "impacted_documents": dedupe(impacted_documents),
                "reasoning_notes": reasoning_notes,
                "warnings": dedupe(warnings),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
