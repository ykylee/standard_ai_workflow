#!/usr/bin/env python3
"""Prototype runner for check_quickstart_stale_links MCP."""

from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path


LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


def resolve_existing_path(raw: str) -> Path:
    path = Path(raw).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"path does not exist: {path}")
    return path


def normalize_target(raw: str) -> str:
    target = raw.strip()
    if target.startswith("<") and target.endswith(">"):
        target = target[1:-1].strip()
    if "#" in target:
        target = target.split("#", 1)[0]
    return target


def markdown_targets(path: Path) -> list[str]:
    targets: list[str] = []
    for match in LINK_RE.finditer(path.read_text(encoding="utf-8")):
        target = normalize_target(match.group(1))
        if not target or "://" in target or target.startswith("#"):
            continue
        targets.append(target)
    return targets


def resolve_relative_target(base: Path, raw_target: str) -> Path:
    return (base.parent / raw_target).resolve()


def rel_link_from_doc(doc_path: Path, target_path: Path) -> str:
    return os.path.relpath(target_path, start=doc_path.parent).replace(os.sep, "/")


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
            if rel_target not in target_set and expected.name not in quickstart_path.read_text(encoding="utf-8"):
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
