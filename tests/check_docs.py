#!/usr/bin/env python3
"""Smoke checks for markdown docs in the standard AI workflow repository."""

from __future__ import annotations

import re
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
REQUIRED_METADATA = [
    "문서 목적",
    "범위",
    "대상 독자",
    "상태",
    "최종 수정일",
    "관련 문서",
]
LINK_PATTERN = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
SKIP_PREFIXES = ("http://", "https://", "mailto:", "#")
IGNORED_PARTS = {
    ".git",
    ".venv",
    "venv",
    "env",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "dist",
    "build",
}


def iter_markdown_files() -> list[Path]:
    return sorted(path for path in REPO_ROOT.rglob("*.md") if not set(path.parts).intersection(IGNORED_PARTS))


def normalize_link_target(raw_target: str) -> str:
    target = raw_target.strip()
    if target.startswith("<") and target.endswith(">"):
        target = target[1:-1].strip()
    if "#" in target:
        target = target.split("#", 1)[0]
    return target


def check_metadata(path: Path) -> list[str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    header_lines = lines[:20]
    missing = []
    for field in REQUIRED_METADATA:
        prefix = f"- {field}:"
        if not any(line.startswith(prefix) for line in header_lines):
            missing.append(field)
    if not lines or not lines[0].startswith("# "):
        missing.append("제목 헤더")
    return missing


def check_links(path: Path) -> list[str]:
    errors: list[str] = []
    text = path.read_text(encoding="utf-8")
    for match in LINK_PATTERN.finditer(text):
        raw_target = normalize_link_target(match.group(1))
        if not raw_target or raw_target.startswith(SKIP_PREFIXES):
            continue
        if "://" in raw_target:
            continue
        target_path = (path.parent / raw_target).resolve()
        if not target_path.exists():
            errors.append(f"broken link `{raw_target}`")
    return errors


def main() -> int:
    failures: list[str] = []
    for path in iter_markdown_files():
        rel_path = path.relative_to(REPO_ROOT)
        missing_metadata = check_metadata(path)
        if missing_metadata:
            failures.append(
                f"{rel_path}: missing metadata fields: {', '.join(missing_metadata)}"
            )
        link_errors = check_links(path)
        for error in link_errors:
            failures.append(f"{rel_path}: {error}")

    if failures:
        print("Document smoke check failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print(f"Document smoke check passed for {len(iter_markdown_files())} markdown files.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
