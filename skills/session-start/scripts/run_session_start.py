#!/usr/bin/env python3
"""Prototype runner for the session-start skill."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


STATUS_RE = re.compile(r"- 상태:\s*(planned|in_progress|blocked|done)\s*$")
TASK_HEADER_RE = re.compile(r"^##\s+(TASK-[A-Z0-9-]+)\s+(.+)$")
DOC_LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def iter_lines(path: Path) -> list[str]:
    return read_text(path).splitlines()


def extract_section_value(lines: list[str], label: str) -> str | None:
    prefix = f"- {label}:"
    for idx, line in enumerate(lines):
        if line.strip() == prefix and idx + 1 < len(lines):
            value = lines[idx + 1].strip()
            if value.startswith("- "):
                return value[2:].strip()
            return value
    return None


def extract_list_after_label(lines: list[str], label: str) -> list[str]:
    prefix = f"- {label}:"
    results: list[str] = []
    capture = False
    for line in lines:
        stripped = line.strip()
        if stripped == prefix:
            capture = True
            continue
        if capture:
            if stripped.startswith("## "):
                break
            if stripped.startswith("- "):
                results.append(stripped[2:].strip())
            elif stripped:
                break
    return results


def extract_markdown_links(path: Path) -> list[Path]:
    text = read_text(path)
    candidates: list[Path] = []
    for match in DOC_LINK_RE.finditer(text):
        target = match.group(1).split("#", 1)[0].strip()
        if not target or "://" in target or target.startswith("#"):
            continue
        candidates.append((path.parent / target).resolve())
    return candidates


def parse_handoff(path: Path) -> dict[str, Any]:
    lines = iter_lines(path)
    return {
        "current_baseline": extract_section_value(lines, "현재 기준선"),
        "current_axis": extract_section_value(lines, "현재 주 작업 축"),
        "recent_core_docs": extract_list_after_label(lines, "최근 핵심 기준 문서"),
        "in_progress_items": extract_list_after_label(lines, "현재 `in_progress` 작업"),
        "blocked_items": extract_list_after_label(lines, "현재 `blocked` 작업"),
        "recent_done_items": extract_list_after_label(lines, "최근 완료 작업 목록"),
        "constraints": extract_section_value(lines, "주요 제약"),
        "next_documents": extract_markdown_links(path),
    }


def find_latest_backlog_path(index_path: Path) -> Path | None:
    linked_paths = extract_markdown_links(index_path)
    if linked_paths:
        return linked_paths[-1]
    lines = iter_lines(index_path)
    date_candidates: list[Path] = []
    for line in lines:
        stripped = line.strip()
        if re.search(r"\d{4}-\d{2}-\d{2}\.md", stripped):
            match = re.search(r"(\.?\.?/.*\d{4}-\d{2}-\d{2}\.md)", stripped)
            if match:
                date_candidates.append((index_path.parent / match.group(1)).resolve())
    return date_candidates[-1] if date_candidates else None


def parse_backlog(path: Path) -> dict[str, Any]:
    lines = iter_lines(path)
    tasks: list[dict[str, str]] = []
    current_task: dict[str, str] | None = None

    for line in lines:
        header_match = TASK_HEADER_RE.match(line.strip())
        if header_match:
            if current_task:
                tasks.append(current_task)
            current_task = {"task_id": header_match.group(1), "title": header_match.group(2)}
            continue
        if current_task is None:
            continue
        status_match = STATUS_RE.match(line.strip())
        if status_match:
            current_task["status"] = status_match.group(1)

    if current_task:
        tasks.append(current_task)

    in_progress = [f"{task['task_id']} {task['title']}" for task in tasks if task.get("status") == "in_progress"]
    blocked = [f"{task['task_id']} {task['title']}" for task in tasks if task.get("status") == "blocked"]
    done = [f"{task['task_id']} {task['title']}" for task in tasks if task.get("status") == "done"]

    return {
        "tasks": tasks,
        "in_progress_items": in_progress,
        "blocked_items": blocked,
        "done_items": done,
    }


def parse_project_profile(path: Path) -> dict[str, Any]:
    lines = iter_lines(path)
    return {
        "project_name": extract_section_value(lines, "프로젝트명"),
        "document_home": extract_section_value(lines, "문서 위키 홈"),
        "operations_path": extract_section_value(lines, "운영 문서 위치"),
        "backlog_path": extract_section_value(lines, "백로그 위치"),
        "handoff_path": extract_section_value(lines, "세션 인계 문서 위치"),
        "environment_path": extract_section_value(lines, "환경 기록 위치"),
        "quick_test": extract_section_value(lines, "빠른 테스트"),
        "constraints": extract_section_value(lines, "환경 제약"),
    }


def build_summary(
    handoff: dict[str, Any], backlog: dict[str, Any], profile: dict[str, Any]
) -> list[str]:
    summary: list[str] = []
    if handoff.get("current_baseline"):
        summary.append(f"현재 기준선: {handoff['current_baseline']}")
    if handoff.get("current_axis"):
        summary.append(f"주 작업 축: {handoff['current_axis']}")
    if backlog.get("in_progress_items"):
        summary.append(f"진행 중 작업 {len(backlog['in_progress_items'])}건 확인")
    elif handoff.get("in_progress_items"):
        summary.append(f"handoff 기준 진행 중 작업 {len(handoff['in_progress_items'])}건 확인")
    if handoff.get("constraints"):
        summary.append(f"주요 제약: {handoff['constraints']}")
    elif profile.get("constraints"):
        summary.append(f"프로파일 제약: {profile['constraints']}")
    return summary[:6]


def dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        normalized = normalize_item(item)
        if normalized and normalized not in seen:
            seen.add(normalized)
            result.append(normalized)
    return result


def compare_state_sources(handoff_items: list[str], backlog_items: list[str], label: str) -> list[str]:
    warnings: list[str] = []
    handoff_set = {normalize_item(item) for item in handoff_items if normalize_item(item)}
    backlog_set = {normalize_item(item) for item in backlog_items if normalize_item(item)}
    if handoff_set != backlog_set:
        warnings.append(
            f"{label} 항목이 handoff 와 backlog 사이에서 다를 수 있으므로 수동 재확인이 필요하다."
        )
    return warnings


def make_recommended_action(
    warnings: list[str], backlog: dict[str, Any], profile: dict[str, Any]
) -> str:
    if warnings:
        return "handoff 와 최신 backlog 의 상태 불일치 여부를 먼저 확인한다."
    if backlog.get("blocked_items"):
        return "차단 작업의 해소 조건과 현재 접근 제약을 먼저 확인한다."
    if profile.get("quick_test"):
        return f"프로파일의 빠른 테스트 명령 `{profile['quick_test']}` 실행 필요 여부를 검토한다."
    return "handoff 와 최신 backlog 를 기준으로 현재 세션의 첫 작업을 확정한다."


def resolve_existing_path(raw: str) -> Path:
    path = Path(raw).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"path does not exist: {path}")
    return path


def normalize_item(value: str) -> str:
    normalized = value.strip()
    if normalized.startswith("`") and normalized.endswith("`"):
        normalized = normalized[1:-1].strip()
    return " ".join(normalized.split())


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the session-start prototype.")
    parser.add_argument("--session-handoff-path", required=True)
    parser.add_argument("--work-backlog-index-path", required=True)
    parser.add_argument("--project-profile-path", required=True)
    parser.add_argument("--latest-backlog-path")
    args = parser.parse_args()

    session_handoff_path = resolve_existing_path(args.session_handoff_path)
    work_backlog_index_path = resolve_existing_path(args.work_backlog_index_path)
    project_profile_path = resolve_existing_path(args.project_profile_path)

    warnings: list[str] = []
    handoff = parse_handoff(session_handoff_path)
    profile = parse_project_profile(project_profile_path)

    latest_backlog_path: Path | None
    if args.latest_backlog_path:
        latest_backlog_path = resolve_existing_path(args.latest_backlog_path)
    else:
        latest_backlog_path = find_latest_backlog_path(work_backlog_index_path)
        if latest_backlog_path is None or not latest_backlog_path.exists():
            latest_backlog_path = None
            warnings.append("최신 backlog 경로를 backlog index 에서 확인하지 못했다.")

    backlog: dict[str, Any] = {"tasks": [], "in_progress_items": [], "blocked_items": [], "done_items": []}
    if latest_backlog_path is not None:
        backlog = parse_backlog(latest_backlog_path)

    warnings.extend(compare_state_sources(handoff.get("in_progress_items", []), backlog.get("in_progress_items", []), "in_progress"))
    warnings.extend(compare_state_sources(handoff.get("blocked_items", []), backlog.get("blocked_items", []), "blocked"))

    next_documents = dedupe(
        [
            str(session_handoff_path),
            str(latest_backlog_path) if latest_backlog_path else "",
            str(project_profile_path),
            *[str(path) for path in handoff.get("next_documents", []) if path.exists()],
        ]
    )

    result = {
        "summary": build_summary(handoff, backlog, profile),
        "in_progress_items": dedupe(
            handoff.get("in_progress_items", []) + backlog.get("in_progress_items", [])
        ),
        "blocked_items": dedupe(handoff.get("blocked_items", []) + backlog.get("blocked_items", [])),
        "latest_backlog_path": str(latest_backlog_path) if latest_backlog_path else None,
        "next_documents": next_documents,
        "recommended_next_action": make_recommended_action(warnings, backlog, profile),
        "warnings": warnings,
        "validation_notes": [],
        "environment_constraints": dedupe(
            [item for item in [handoff.get("constraints"), profile.get("constraints")] if item]
        ),
        "source_documents": {
            "session_handoff_path": str(session_handoff_path),
            "work_backlog_index_path": str(work_backlog_index_path),
            "project_profile_path": str(project_profile_path),
        },
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
