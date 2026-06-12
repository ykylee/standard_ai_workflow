#!/usr/bin/env python3
"""Check V-R9: wiki-ingest source = archive/ only, NOT active/.

R9 (Raw Source of Truth) — wiki-ingest/memory-ingest must source from
archive/YYYY-MM-DD/, never from active/. This prevents the agent from
ingesting mutable/frozen-incomplete state into the wiki.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
WIKI_DIR = REPO_ROOT / "ai-workflow" / "wiki"
MEMORY_ACTIVE = REPO_ROOT / "ai-workflow" / "memory" / "active"
MEMORY_ARCHIVE = REPO_ROOT / "ai-workflow" / "memory" / "archive"


def check_wiki_specs_no_active_ref() -> list[str]:
    """Check that no wiki spec/docs reference active/ as ingest source."""
    errors: list[str] = []
    if not WIKI_DIR.is_dir():
        return errors
    for md_file in WIKI_DIR.rglob("*.md"):
        text = md_file.read_text(encoding="utf-8")
        # Look for patterns like "ingest from active/" or "source=active/"
        if re.search(r"ingest.*active[/\s]|active/.*ingest|source.*active/", text, re.IGNORECASE):
            rel = md_file.relative_to(REPO_ROOT)
            errors.append(f"[V-R9] {rel}: references active/ as ingest source (must use archive/ only)")
    return errors


def check_active_files_not_in_wiki() -> list[str]:
    """Check that no wiki page uses memory/active/ as an ingest source reference."""
    errors: list[str] = []
    if not WIKI_DIR.is_dir() or not MEMORY_ACTIVE.is_dir():
        return errors
    for wiki_file in WIKI_DIR.rglob("*.md"):
        text = wiki_file.read_text(encoding="utf-8")
        # Only flag when active/ appears in ingest or source context
        if re.search(r"ingest.*memory/active|memory/active.*ingest|source.*memory/active|memory/active.*source", text, re.IGNORECASE):
            rel = wiki_file.relative_to(REPO_ROOT)
            errors.append(f"[V-R9] {rel}: references memory/active/ as ingest source (must use archive/ only)")
    return errors


def main() -> int:
    errors: list[str] = []
    errors.extend(check_wiki_specs_no_active_ref())
    errors.extend(check_active_files_not_in_wiki())

    if errors:
        for e in errors:
            print(f"FAIL: {e}")
        raise AssertionError(f"V-R9 check failed with {len(errors)} violation(s).")
    print("V-R9 check passed: no active/ references as wiki-ingest source.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
