#!/usr/bin/env python3
"""Prototype runner for check_doc_metadata MCP."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


REQUIRED_METADATA = [
    "문서 목적",
    "범위",
    "대상 독자",
    "상태",
    "최종 수정일",
    "관련 문서",
]


def resolve_existing_path(raw: str) -> Path:
    path = Path(raw).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"path does not exist: {path}")
    return path


def check_file(path: Path) -> list[str]:
    lines = path.read_text(encoding="utf-8").splitlines()[:20]
    missing = []
    for field in REQUIRED_METADATA:
        prefix = f"- {field}:"
        if not any(line.startswith(prefix) for line in lines):
            missing.append(field)
    if not lines or not lines[0].startswith("# "):
        missing.append("제목 헤더")
    return missing


def main() -> int:
    parser = argparse.ArgumentParser(description="Run check_doc_metadata MCP prototype.")
    parser.add_argument("--doc-dir-path", required=True)
    args = parser.parse_args()

    doc_dir = resolve_existing_path(args.doc_dir_path)
    checked_files = []
    missing_metadata = []
    for path in sorted(doc_dir.rglob("*.md")):
        checked_files.append(str(path))
        missing = check_file(path)
        if missing:
            missing_metadata.append({"path": str(path), "missing_fields": missing})

    print(
        json.dumps(
            {
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
