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
    files = [path for path in backlog_dir.glob("*.md") if DATE_NAME_RE.search(path.name)]
    return sorted(files, key=lambda path: path.name)


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


def create_backlog_entry_payload(
    *,
    task_id: str,
    task_name: str,
    request_date: str,
    status: str | None,
    priority: str | None,
    tool_version: str,
) -> dict[str, Any]:
    draft_entry = [
        f"## {task_id} {task_name}",
        "",
        f"- 상태: {status or 'planned'}",
        f"- 우선순위: {priority or 'high'}",
        f"- 요청일: {request_date}",
        "- 완료일:",
        "- 담당:",
        "- 호스트명:",
        "- 호스트 IP:",
        "- 영향 문서:",
        "- 작업 내용:",
        "- 진행 현황:",
        "- 완료 기준:",
        "- 작업 결과:",
        "- 다음 세션 시작 포인트:",
        "- 남은 리스크:",
        "- 후속 작업:",
    ]
    return {
        "status": "ok",
        "tool_version": tool_version,
        "draft_entry": draft_entry,
        "warnings": [],
    }


def create_session_handoff_draft_payload(
    *,
    latest_backlog_path: str | None,
    tool_version: str,
) -> dict[str, Any]:
    warnings: list[str] = []
    done_items: list[str] = []
    in_progress_items: list[str] = []

    if latest_backlog_path:
        path = resolve_existing_path(latest_backlog_path)
        content = path.read_text(encoding="utf-8")
        # Simple markdown section extractor
        current_section = ""
        for line in content.splitlines():
            if line.startswith("## "):
                current_section = line[3:].strip()
            elif "- 상태: done" in line:
                if current_section:
                    done_items.append(current_section)
            elif "- 상태: in_progress" in line:
                if current_section:
                    in_progress_items.append(current_section)

    if not done_items and not in_progress_items:
        warnings.append("최신 백로그에서 진행 중이거나 완료된 작업을 찾지 못했다.")

    draft_handoff = [
        "# 세션 인계 문서 (초안)",
        "",
        "- 상태: draft",
        f"- 생성일: {Path(latest_backlog_path).stem if latest_backlog_path else 'N/A'}",
        "",
        "## 1. 현재 작업 요약",
        "",
        "- 현재 기준선: N/A",
        "- 현재 주 작업 축: N/A",
        "",
        "## 2. 진행 중 작업",
        "",
    ]
    for item in in_progress_items:
        draft_handoff.append(f"- {item}")
    if not in_progress_items:
        draft_handoff.append("- N/A")

    draft_handoff.extend([
        "",
        "## 3. 차단 작업",
        "",
        "- N/A",
        "",
        "## 4. 최근 완료 작업",
        "",
    ])
    for item in done_items:
        draft_handoff.append(f"- {item}")
    if not done_items:
        draft_handoff.append("- N/A")

    draft_handoff.extend([
        "",
        "## 5. 잔여 작업 우선순위",
        "",
        "### 우선순위 1",
        "",
        "- [ ] 다음 단계 작업 명시",
        "",
        "## 6. 환경별 검증 현황",
        "",
        "- 검증 완료 호스트: local",
    ])

    return {
        "status": "ok",
        "tool_version": tool_version,
        "draft_handoff": draft_handoff,
        "source_context": {"latest_backlog_path": latest_backlog_path},
        "warnings": warnings,
    }


def create_environment_record_stub_payload(
    *,
    hostname: str,
    os_type: str,
    tool_version: str,
) -> dict[str, Any]:
    draft_record = [
        "## 환경 및 호스트 정보",
        "",
        f"- 호스트명: {hostname}",
        f"- OS 유형: {os_type}",
        "- Python 버전: N/A",
        "- 주요 가상환경: .venv",
        "- 프로젝트 루트: N/A",
        "",
        "### 검증 도구 상태",
        "",
        "- [ ] git",
        "- [ ] python3",
        "- [ ] pip",
        "",
        "### 특이 사항",
        "",
        "- N/A",
    ]
    return {
        "status": "ok",
        "tool_version": tool_version,
        "draft_record": draft_record,
        "source_context": {"hostname": hostname, "os_type": os_type},
        "warnings": [],
    }
