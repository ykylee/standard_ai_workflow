"""Project workflow document parsers shared across skill prototypes."""

from __future__ import annotations

import re
from pathlib import Path

from workflow_kit.common.markdown import markdown_targets
from workflow_kit.common.text import (
    extract_list_after_label,
    extract_named_section_bullets,
    extract_section_value,
    iter_lines,
)


STATUS_RE = re.compile(r"- 상태:\s*(planned|in_progress|blocked|done)\s*$")
TASK_HEADER_RE = re.compile(r"^##\s+(TASK-[A-Z0-9-]+)\s+(.+)$")


def parse_project_profile_core(path: Path) -> dict[str, str | None]:
    lines = iter_lines(path)
    return {
        "project_name": extract_section_value(lines, "프로젝트명"),
        "document_home": extract_section_value(lines, "문서 위키 홈"),
        "operations_path": extract_section_value(lines, "운영 문서 위치"),
        "backlog_path": extract_section_value(lines, "백로그 위치"),
        "handoff_path": extract_section_value(lines, "세션 인계 문서 위치"),
        "environment_path": extract_section_value(lines, "환경 기록 위치"),
    }


def parse_project_profile_validation(path: Path) -> dict[str, str | list[str] | None]:
    lines = iter_lines(path)
    return {
        "project_name": extract_section_value(lines, "프로젝트명"),
        "quick_tests": extract_section_value(lines, "빠른 테스트"),
        "isolated_tests": extract_section_value(lines, "격리 테스트"),
        "runtime_checks": extract_section_value(lines, "UI/API 실행 확인"),
        "validation_points": extract_named_section_bullets(lines, "4. 프로젝트 특화 검증 포인트"),
        "exception_rules": extract_named_section_bullets(lines, "5. 프로젝트 특화 예외 규칙"),
    }


def parse_project_profile_session(path: Path) -> dict[str, str | None]:
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


def parse_handoff(path: Path) -> dict[str, object]:
    lines = iter_lines(path)
    return {
        "current_baseline": extract_section_value(lines, "현재 기준선"),
        "current_axis": extract_section_value(lines, "현재 주 작업 축"),
        "recent_core_docs": extract_list_after_label(lines, "최근 핵심 기준 문서"),
        "in_progress_items": extract_list_after_label(lines, "현재 `in_progress` 작업"),
        "blocked_items": extract_list_after_label(lines, "현재 `blocked` 작업"),
        "recent_done_items": extract_list_after_label(lines, "최근 완료 작업 목록"),
        "constraints": extract_section_value(lines, "주요 제약"),
        "next_documents": [(path.parent / target).resolve() for target in markdown_targets(path)],
    }


def parse_backlog(path: Path) -> dict[str, object]:
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

    return {
        "tasks": tasks,
        "in_progress_items": [f"{task['task_id']} {task['title']}" for task in tasks if task.get("status") == "in_progress"],
        "blocked_items": [f"{task['task_id']} {task['title']}" for task in tasks if task.get("status") == "blocked"],
        "done_items": [f"{task['task_id']} {task['title']}" for task in tasks if task.get("status") == "done"],
    }


def find_latest_backlog_path(index_path: Path) -> Path | None:
    linked_paths = [(index_path.parent / target).resolve() for target in markdown_targets(index_path)]
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

