#!/usr/bin/env python3
"""Prototype runner for check_doc_metadata MCP."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from workflow_kit import __version__ as TOOL_VERSION
from workflow_kit.common.docs import missing_metadata_fields
from workflow_kit.common.paths import resolve_existing_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Run check_doc_metadata MCP prototype.")
    parser.add_argument("--doc-dir-path", required=True)
    args = parser.parse_args()

    doc_dir = resolve_existing_path(args.doc_dir_path)
    checked_files = []
    missing_metadata = []
    for path in sorted(doc_dir.rglob("*.md")):
        checked_files.append(str(path))
        missing = missing_metadata_fields(path)
        if missing:
            missing_metadata.append({"path": str(path), "missing_fields": missing})

    print(
        json.dumps(
            {
                "status": "ok",
                "tool_version": TOOL_VERSION,
                "checked_files": checked_files,
                "missing_metadata": missing_metadata,
                "warnings": [],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
