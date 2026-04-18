#!/usr/bin/env python3
"""Prototype runner for check_doc_links MCP."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


def resolve_existing_path(raw: str) -> Path:
    path = Path(raw).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"path does not exist: {path}")
    return path


def find_broken_links(path: Path) -> list[str]:
    broken = []
    for match in LINK_RE.finditer(path.read_text(encoding="utf-8")):
        target = match.group(1).split("#", 1)[0].strip()
        if not target or "://" in target or target.startswith("#"):
            continue
        resolved = (path.parent / target).resolve()
        if not resolved.exists():
            broken.append(target)
    return broken


def main() -> int:
    parser = argparse.ArgumentParser(description="Run check_doc_links MCP prototype.")
    parser.add_argument("--doc-dir-path", required=True)
    args = parser.parse_args()

    doc_dir = resolve_existing_path(args.doc_dir_path)
    checked_files = []
    broken_links = []
    for path in sorted(doc_dir.rglob("*.md")):
        checked_files.append(str(path))
        broken = find_broken_links(path)
        if broken:
            broken_links.append({"path": str(path), "broken_links": broken})

    print(
        json.dumps(
            {
                "checked_files": checked_files,
                "broken_links": broken_links,
                "warnings": [],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
