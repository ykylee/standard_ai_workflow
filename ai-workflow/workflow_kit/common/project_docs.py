"""Project workflow document parsers shared across skill prototypes."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Iterable

from workflow_kit.common.markdown import markdown_targets
from workflow_kit.common.text import (
    extract_list_after_label,
    extract_named_section_bullets,
    extract_section_value,
    iter_lines,
    normalize_inline_code,
)


STATUS_RE = re.compile(r"- 상태:\s*(planned|in_progress|blocked|done)\s*$")
TASK_HEADER_RE = re.compile(r"^##\s+(TASK-[A-Z0-9-]+)\s+(.+)$")


class WorkflowDocParser:
    def __init__(self, path: Path):
        self.path = path
        self.lines = iter_lines(path)
        self.warnings: list[str] = []

    def get_value(self, label: str, required: bool = False) -> str | None:
        val = extract_section_value(self.lines, label)
        if val is None and required:
            self.warnings.append(f"필수 섹션 누락: `{label}` ({self.path.name})")
        return val

    def get_list(self, label: str) -> list[str]:
        return extract_list_after_label(self.lines, label)

    def get_named_bullets(self, title: str) -> list[str]:
        return extract_named_section_bullets(self.lines, title)


def parse_project_profile_core(path: Path) -> dict[str, Any]:
    parser = WorkflowDocParser(path)
    data = {
        "project_name": parser.get_value("프로젝트명", required=True),
        "document_home": parser.get_value("문서 위키 홈"),
        "operations_path": parser.get_value("운영 문서 위치"),
        "backlog_path": parser.get_value("백로그 위치"),
        "handoff_path": parser.get_value("세션 인계 문서 위치"),
        "environment_path": parser.get_value("환경 기록 위치"),
    }
    return {**data, "warnings": parser.warnings}


def parse_project_profile_validation(path: Path) -> dict[str, Any]:
    parser = WorkflowDocParser(path)
    data = {
        "project_name": parser.get_value("프로젝트명"),
        "quick_tests": parser.get_value("빠른 테스트"),
        "isolated_tests": parser.get_value("격리 테스트"),
        "runtime_checks": parser.get_value("UI/API 실행 확인"),
        "validation_points": parser.get_named_bullets("4. 프로젝트 특화 검증 포인트"),
        "exception_rules": parser.get_named_bullets("5. 프로젝트 특화 예외 규칙"),
    }
    return {**data, "warnings": parser.warnings}


def parse_project_profile_session(path: Path) -> dict[str, Any]:
    parser = WorkflowDocParser(path)
    data = {
        "project_name": parser.get_value("프로젝트명", required=True),
        "document_home": parser.get_value("문서 위키 홈"),
        "operations_path": parser.get_value("운영 문서 위치"),
        "backlog_path": parser.get_value("백로그 위치"),
        "handoff_path": parser.get_value("세션 인계 문서 위치"),
        "environment_path": parser.get_value("환경 기록 위치"),
        "quick_test": parser.get_value("빠른 테스트"),
        "constraints": parser.get_value("환경 제약"),
    }
    return {**data, "warnings": parser.warnings}


def parse_project_profile_merge(path: Path) -> dict[str, Any]:
    parser = WorkflowDocParser(path)
    data = {
        "project_name": parser.get_value("프로젝트명"),
        "document_home": parser.get_value("문서 위키 홈"),
        "operations_path": parser.get_value("운영 문서 위치"),
        "backlog_path": parser.get_value("백로그 위치"),
        "handoff_path": parser.get_value("세션 인계 문서 위치"),
        "constraints": parser.get_value("환경 제약"),
        "merge_rule": parser.get_value("병합 규칙"),
    }
    return {**data, "warnings": parser.warnings}


def parse_project_profile_backlog(path: Path) -> dict[str, Any]:
    parser = WorkflowDocParser(path)
    data = {
        "project_name": parser.get_value("프로젝트명"),
        "backlog_path": parser.get_value("백로그 위치"),
        "handoff_path": parser.get_value("세션 인계 문서 위치"),
        "constraints": parser.get_value("환경 제약"),
    }
    return {**data, "warnings": parser.warnings}


def parse_handoff(path: Path) -> dict[str, object]:
    parser = WorkflowDocParser(path)
    data = {
        "current_baseline": parser.get_value("현재 기준선", required=True),
        "current_axis": parser.get_value("현재 주 작업 축", required=True),
        "recent_core_docs": parser.get_list("최근 핵심 기준 문서"),
        "in_progress_items": parser.get_list("현재 `in_progress` 작업"),
        "blocked_items": parser.get_list("현재 `blocked` 작업"),
        "recent_done_items": parser.get_list("최근 완료 작업 목록"),
        "constraints": parser.get_value("주요 제약"),
        "next_documents": [path.parent / target for target in markdown_targets(path)],
    }
    return {**data, "warnings": parser.warnings}


def parse_backlog(path: Path) -> dict[str, object]:
    lines: Iterable[str]
    if not path.exists():
        # Try branch-specific tasks dir first, then fall back to original location
        from workflow_kit.common.paths import workflow_branch_dir
        branch_dir = workflow_branch_dir(path.parent.parent) # Assuming path is ai-workflow/memory/backlog/YYYY-MM-DD.md
        tasks_dir = branch_dir / "backlog" / "tasks"
        if not tasks_dir.exists():
            tasks_dir = path.parent / "tasks"

        task_files = sorted(tasks_dir.glob(f"{path.stem}_*.md")) if tasks_dir.exists() else []
        if not task_files:
            return {
                "tasks": [],
                "in_progress_items": [],
                "blocked_items": [],
                "done_items": [],
                "warnings": [f"백로그 파일({path.name}) 및 태스크 파일을 찾을 수 없습니다."],
            }
        lines = []
        for tf in task_files:
            lines.extend(tf.read_text(encoding="utf-8").splitlines())
            lines.append("")
        parser = WorkflowDocParser(path)
        parser.lines = iter(lines)
    else:
        parser = WorkflowDocParser(path)

    tasks: list[dict[str, str]] = []
    current_task: dict[str, str] | None = None

    for idx, line in enumerate(parser.lines):
        stripped = line.strip()
        header_match = TASK_HEADER_RE.match(stripped)
        if header_match:
            if current_task:
                tasks.append(current_task)
            current_task = {"task_id": header_match.group(1), "title": header_match.group(2)}
            continue

        if current_task is None:
            continue

        status_match = STATUS_RE.match(stripped)
        if status_match:
            current_task["status"] = status_match.group(1)
        elif stripped.startswith("- 상태:") and not STATUS_RE.match(stripped):
            parser.warnings.append(f"잘못된 상태 형식 (L{idx+1}): `{stripped}`")

    if current_task:
        tasks.append(current_task)

    return {
        "tasks": tasks,
        "in_progress_items": [f"{task['task_id']} {task['title']}" for task in tasks if task.get("status") == "in_progress"],
        "blocked_items": [f"{task['task_id']} {task['title']}" for task in tasks if task.get("status") == "blocked"],
        "done_items": [f"{task['task_id']} {task['title']}" for task in tasks if task.get("status") == "done"],
        "warnings": parser.warnings,
    }


def parse_backlog_task_entries(path: Path) -> list[dict[str, str | None]]:
    lines: Iterable[str]
    if not path.exists():
        # Try branch-specific tasks dir first, then fall back to original location
        from workflow_kit.common.paths import workflow_branch_dir
        branch_dir = workflow_branch_dir(path.parent.parent)
        tasks_dir = branch_dir / "backlog" / "tasks"
        if not tasks_dir.exists():
            tasks_dir = path.parent / "tasks"

        task_files = sorted(tasks_dir.glob(f"{path.stem}_*.md")) if tasks_dir.exists() else []
        if not task_files:
            return []
        lines = []
        for tf in task_files:
            lines.extend(tf.read_text(encoding="utf-8").splitlines())
            lines.append("")
        parser = WorkflowDocParser(path)
        parser.lines = iter(lines)
    else:
        parser = WorkflowDocParser(path)

    tasks: list[dict[str, str | None]] = []
    current_task: dict[str, str | None] | None = None
    for idx, line in enumerate(parser.lines):
        stripped = line.strip()
        header_match = TASK_HEADER_RE.match(stripped)
        if header_match:
            if current_task:
                tasks.append(current_task)
            current_task = {"task_id": header_match.group(1), "title": header_match.group(2), "status": None}
            continue
        if current_task is None:
            continue
        status_match = STATUS_RE.match(stripped)
        if status_match:
            current_task["status"] = status_match.group(1)
        elif stripped.startswith("- 상태:") and not STATUS_RE.match(stripped):
            parser.warnings.append(f"잘못된 상태 형식 (L{idx+1}): `{stripped}`")
    if current_task:
        tasks.append(current_task)
    return tasks


def find_latest_backlog_path(index_path: Path) -> Path | None:
    linked_paths = [index_path.parent / target for target in markdown_targets(index_path)]
    if linked_paths:
        return linked_paths[-1]
    lines = iter_lines(index_path)
    date_candidates: list[Path] = []
    for line in lines:
        stripped = line.strip()
        if re.search(r"\d{4}-\d{2}-\d{2}\.md", stripped):
            match = re.search(r"(\.?\.?/.*\d{4}-\d{2}-\d{2}\.md)", stripped)
            if match:
                date_candidates.append(index_path.parent / match.group(1))
    return date_candidates[-1] if date_candidates else None
