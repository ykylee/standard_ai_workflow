"""Shared callable implementations for the first read-only MCP bundle."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from workflow_kit.common.change_types import classify_impacted_doc_file
from workflow_kit.common.docs import missing_metadata_fields
from workflow_kit.common.markdown import (
    find_broken_links,
    markdown_targets,
    rel_link_from_doc,
    resolve_relative_target,
)
from workflow_kit.common.paths import resolve_existing_path


DATE_NAME_RE = re.compile(r"(\d{4}-\d{2}-\d{2})\.md$")


def dedupe_strings(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        normalized = item.strip()
        if normalized and normalized not in seen:
            seen.add(normalized)
            result.append(normalized)
    return result


def extract_index_candidates(index_path: Path) -> list[Path]:
    candidates: list[Path] = []
    for target in markdown_targets(index_path):
        candidate = (index_path.parent / target).resolve()
        if candidate.exists() and candidate.suffix == ".md":
            candidates.append(candidate)
    return candidates


def discover_backlog_files(backlog_dir: Path) -> list[Path]:
    files = [path for path in backlog_dir.rglob("*.md") if DATE_NAME_RE.search(path.name)]
    return sorted(files, key=lambda path: (path.name, path.as_posix()))


def latest_backlog_payload(*, backlog_dir_path: str | None, work_backlog_index_path: str | None, tool_version: str) -> dict[str, Any]:
    warnings: list[str] = []
    candidates: list[Path] = []

    if work_backlog_index_path:
        index_path = resolve_existing_path(work_backlog_index_path)
        candidates = extract_index_candidates(index_path)
        if not candidates:
            warnings.append("backlog index 에서 링크된 backlog 후보를 찾지 못했다.")

    if not candidates and backlog_dir_path:
        backlog_dir = resolve_existing_path(backlog_dir_path)
        candidates = discover_backlog_files(backlog_dir)
        if not candidates:
            warnings.append("backlog 디렉터리에서 날짜형 markdown 파일을 찾지 못했다.")

    latest = str(candidates[-1]) if candidates else None
    return {
        "status": "ok",
        "tool_version": tool_version,
        "latest_backlog_path": latest,
        "candidates": [str(path) for path in candidates],
        "warnings": warnings,
    }


def check_doc_metadata_payload(*, doc_dir_path: str, tool_version: str) -> dict[str, Any]:
    doc_dir = resolve_existing_path(doc_dir_path)
    checked_files: list[str] = []
    missing_metadata: list[dict[str, Any]] = []

    for path in sorted(doc_dir.rglob("*.md")):
        checked_files.append(str(path))
        missing = missing_metadata_fields(path)
        if missing:
            missing_metadata.append({"path": str(path), "missing_fields": missing})

    return {
        "status": "ok",
        "tool_version": tool_version,
        "checked_files": checked_files,
        "missing_metadata": missing_metadata,
        "warnings": [],
    }


def check_doc_links_payload(*, doc_dir_path: str, tool_version: str) -> dict[str, Any]:
    doc_dir = resolve_existing_path(doc_dir_path)
    checked_files: list[str] = []
    broken_links: list[dict[str, Any]] = []

    for path in sorted(doc_dir.rglob("*.md")):
        checked_files.append(str(path))
        broken = find_broken_links(path)
        if broken:
            broken_links.append({"path": str(path), "broken_links": broken})

    return {
        "status": "ok",
        "tool_version": tool_version,
        "checked_files": checked_files,
        "broken_links": broken_links,
        "warnings": [],
    }


def suggest_impacted_docs_payload(
    *,
    changed_files: list[str],
    session_handoff_path: str | None,
    latest_backlog_path: str | None,
    work_backlog_index_path: str | None,
    tool_version: str,
) -> dict[str, Any]:
    impacted_documents: list[str] = []
    reasoning_notes: list[str] = []
    warnings: list[str] = []

    if session_handoff_path:
        impacted_documents.append(str(resolve_existing_path(session_handoff_path)))
    if latest_backlog_path:
        impacted_documents.append(str(resolve_existing_path(latest_backlog_path)))
    if work_backlog_index_path:
        impacted_documents.append(str(resolve_existing_path(work_backlog_index_path)))

    for changed in changed_files:
        kind = classify_impacted_doc_file(changed)
        reasoning_notes.append(f"`{changed}` 는 `{kind}` 유형 변경으로 해석했다.")
        if kind in {"code", "config"} and not any([session_handoff_path, latest_backlog_path, work_backlog_index_path]):
            warnings.append("코드/설정 변경이지만 상태 문서 후보 경로가 제공되지 않았다.")
        if kind == "doc":
            impacted_documents.append(changed)

    return {
        "status": "ok",
        "tool_version": tool_version,
        "impacted_documents": dedupe_strings(impacted_documents),
        "reasoning_notes": reasoning_notes,
        "warnings": dedupe_strings(warnings),
    }


def check_quickstart_stale_links_payload(
    *,
    quickstart_paths: list[str],
    project_profile_path: str | None,
    session_handoff_path: str | None,
    work_backlog_index_path: str | None,
    agents_path: str | None,
    tool_version: str,
) -> dict[str, Any]:
    checked_files: list[str] = []
    broken_links: list[dict[str, Any]] = []
    missing_expected_links: list[dict[str, Any]] = []
    stale_link_warnings: list[str] = []
    reasoning_notes: list[str] = []

    resolved_quickstart_paths = [resolve_existing_path(item) for item in quickstart_paths]

    expected_targets: list[Path] = []
    for raw in (project_profile_path, session_handoff_path, work_backlog_index_path, agents_path):
        if raw:
            expected_targets.append(resolve_existing_path(raw))

    for quickstart_path in resolved_quickstart_paths:
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
            missing_expected_links.append({"path": str(quickstart_path), "missing_targets": missing_for_doc})
            stale_link_warnings.append(
                f"{quickstart_path.name} 문서가 현재 워크플로우 핵심 진입 문서 일부를 직접 가리키지 않아 onboarding 흐름이 약할 수 있다."
            )

        reasoning_notes.append(
            f"`{quickstart_path.name}` 문서에서 상대 링크 무결성과 핵심 진입 문서 링크 존재 여부를 함께 점검했다."
        )

    return {
        "status": "ok",
        "tool_version": tool_version,
        "checked_files": checked_files,
        "broken_links": broken_links,
        "missing_expected_links": missing_expected_links,
        "stale_link_warnings": stale_link_warnings,
        "reasoning_notes": reasoning_notes,
        "warnings": [],
    }
