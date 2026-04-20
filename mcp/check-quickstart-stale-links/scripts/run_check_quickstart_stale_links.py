#!/usr/bin/env python3
"""Prototype runner for check_quickstart_stale_links MCP."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from workflow_kit.common.markdown import markdown_targets, rel_link_from_doc, resolve_relative_target
from workflow_kit.common.paths import resolve_existing_path

TOOL_VERSION = "prototype-v1"


def main() -> int:
    parser = argparse.ArgumentParser(description="Run check_quickstart_stale_links MCP prototype.")
    parser.add_argument("--quickstart-path", action="append", dest="quickstart_paths", required=True)
    parser.add_argument("--project-profile-path")
    parser.add_argument("--session-handoff-path")
    parser.add_argument("--work-backlog-index-path")
    parser.add_argument("--agents-path")
    args = parser.parse_args()

    checked_files: list[str] = []
    broken_links: list[dict[str, object]] = []
    missing_expected_links: list[dict[str, object]] = []
    stale_link_warnings: list[str] = []
    reasoning_notes: list[str] = []

    quickstart_paths = [resolve_existing_path(item) for item in args.quickstart_paths]

    expected_targets: list[Path] = []
    if args.project_profile_path:
        expected_targets.append(resolve_existing_path(args.project_profile_path))
    if args.session_handoff_path:
        expected_targets.append(resolve_existing_path(args.session_handoff_path))
    if args.work_backlog_index_path:
        expected_targets.append(resolve_existing_path(args.work_backlog_index_path))
    if args.agents_path:
        expected_targets.append(resolve_existing_path(args.agents_path))

    for quickstart_path in quickstart_paths:
        checked_files.append(str(quickstart_path))
        raw_targets = markdown_targets(quickstart_path)
        target_set = set(raw_targets)
        quickstart_text = quickstart_path.read_text(encoding="utf-8")

        broken: list[str] = []
        for raw_target in raw_targets:
            resolved = resolve_relative_target(quickstart_path, raw_target)
            if not resolved.exists():
                broken.append(raw_target)
        if broken:
            broken_links.append({"path": str(quickstart_path), "broken_links": sorted(set(broken))})
            stale_link_warnings.append(
                f"{quickstart_path.name} 문서에 존재하지 않는 상대 링크가 있어 quickstart 진입이 stale 되었을 가능성이 있다."
            )

        missing_for_doc: list[str] = []
        for expected in expected_targets:
            rel_target = rel_link_from_doc(quickstart_path, expected)
            if rel_target not in target_set and expected.name not in quickstart_text:
                missing_for_doc.append(rel_target)
        if missing_for_doc:
            missing_expected_links.append(
                {
                    "path": str(quickstart_path),
                    "missing_targets": missing_for_doc,
                }
            )
            stale_link_warnings.append(
                f"{quickstart_path.name} 문서가 현재 워크플로우 핵심 진입 문서 일부를 직접 가리키지 않아 onboarding 흐름이 약할 수 있다."
            )

        reasoning_notes.append(
            f"`{quickstart_path.name}` 문서에서 상대 링크 무결성과 핵심 진입 문서 링크 존재 여부를 함께 점검했다."
        )

    print(
        json.dumps(
            {
                "status": "ok",
                "tool_version": TOOL_VERSION,
                "checked_files": checked_files,
                "broken_links": broken_links,
                "missing_expected_links": missing_expected_links,
                "stale_link_warnings": stale_link_warnings,
                "reasoning_notes": reasoning_notes,
                "warnings": [],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
