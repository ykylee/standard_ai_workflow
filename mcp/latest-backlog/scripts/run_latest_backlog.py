#!/usr/bin/env python3
"""Prototype runner for latest_backlog MCP."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from workflow_kit.common.markdown import markdown_targets
from workflow_kit.common.paths import resolve_existing_path

TOOL_VERSION = "prototype-v1"


DATE_NAME_RE = re.compile(r"(\d{4}-\d{2}-\d{2})\.md$")


def extract_index_candidates(index_path: Path) -> list[Path]:
    candidates: list[Path] = []
    for target in markdown_targets(index_path):
        candidate = (index_path.parent / target).resolve()
        if candidate.exists() and candidate.suffix == ".md":
            candidates.append(candidate)
    return candidates


def discover_backlog_files(backlog_dir: Path) -> list[Path]:
    files = [p for p in backlog_dir.glob("*.md") if DATE_NAME_RE.search(p.name)]
    return sorted(files, key=lambda p: p.name)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run latest_backlog MCP prototype.")
    parser.add_argument("--backlog-dir-path")
    parser.add_argument("--work-backlog-index-path")
    args = parser.parse_args()

    warnings: list[str] = []
    candidates: list[Path] = []

    if args.work_backlog_index_path:
        index_path = resolve_existing_path(args.work_backlog_index_path)
        candidates = extract_index_candidates(index_path)
        if not candidates:
            warnings.append("backlog index 에서 링크된 backlog 후보를 찾지 못했다.")

    if not candidates and args.backlog_dir_path:
        backlog_dir = resolve_existing_path(args.backlog_dir_path)
        candidates = discover_backlog_files(backlog_dir)
        if not candidates:
            warnings.append("backlog 디렉터리에서 날짜형 markdown 파일을 찾지 못했다.")

    latest = str(candidates[-1]) if candidates else None
    print(
        json.dumps(
            {
                "status": "ok",
                "tool_version": TOOL_VERSION,
                "latest_backlog_path": latest,
                "candidates": [str(path) for path in candidates],
                "warnings": warnings,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
