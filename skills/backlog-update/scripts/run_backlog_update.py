#!/usr/bin/env python3
"""Prototype runner for the backlog-update skill."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

TOOL_VERSION = "prototype-v1"


TASK_HEADER_RE = re.compile(r"^##\s+(TASK-[A-Z0-9-]+)\s+(.+)$")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def iter_lines(path: Path) -> list[str]:
    return read_text(path).splitlines()


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


def normalize_inline_code(value: str) -> str:
    normalized = value.strip()
    if normalized.startswith("`") and normalized.endswith("`"):
        normalized = normalized[1:-1].strip()
    return normalized


def extract_section_value(lines: list[str], label: str) -> str | None:
    prefix = f"- {label}:"
    for idx, line in enumerate(lines):
        if line.strip() == prefix and idx + 1 < len(lines):
            value = lines[idx + 1].strip()
            if value.startswith("- "):
                value = value[2:].strip()
            return normalize_inline_code(value)
    return None


def parse_project_profile(path: Path) -> dict[str, Any]:
    lines = iter_lines(path)
    return {
        "project_name": extract_section_value(lines, "프로젝트명"),
        "backlog_path": extract_section_value(lines, "백로그 위치"),
        "handoff_path": extract_section_value(lines, "세션 인계 문서 위치"),
        "constraints": extract_section_value(lines, "환경 제약"),
    }


def parse_backlog_tasks(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    tasks: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    for line in iter_lines(path):
        stripped = line.rstrip()
        header_match = TASK_HEADER_RE.match(stripped.strip())
        if header_match:
            if current:
                tasks.append(current)
            current = {
                "task_id": header_match.group(1),
                "title": header_match.group(2),
                "status": None,
            }
            continue
        if current is None:
            continue
        if stripped.strip().startswith("- 상태:"):
            current["status"] = stripped.split(":", 1)[1].strip()
    if current:
        tasks.append(current)
    return tasks


def infer_backlog_path(project_profile_path: Path, backlog_dir: str | None, target_date: str) -> Path:
    base_dir = project_profile_path.parent
    if backlog_dir:
        return (base_dir / backlog_dir / f"{target_date}.md").resolve()
    return (base_dir / "backlog" / f"{target_date}.md").resolve()


def suggest_next_task_id(tasks: list[dict[str, Any]]) -> str:
    max_num = 0
    for task in tasks:
        match = re.match(r"TASK-(\d+)", task["task_id"])
        if match:
            max_num = max(max_num, int(match.group(1)))
    return f"TASK-{max_num + 1:03d}"


def determine_status(
    requested_status: str | None,
    validation_result: str | None,
    operation_type: str,
) -> tuple[str, list[str]]:
    warnings: list[str] = []
    status = requested_status or ("planned" if operation_type == "create_entry" else "in_progress")
    if status not in {"planned", "in_progress", "blocked", "done"}:
        warnings.append(f"알 수 없는 상태 `{status}` 는 사용할 수 없어 `planned` 로 대체한다.")
        status = "planned"
    if status == "done" and not validation_result:
        warnings.append("검증 결과가 없으므로 `done` 상태는 초안에서 `in_progress` 로 낮춘다.")
        status = "in_progress"
    return status, warnings


def build_draft_entry(
    *,
    task_id: str,
    task_name: str,
    status: str,
    priority: str,
    request_date: str,
    owner: str | None,
    host_name: str | None,
    host_ip: str | None,
    affected_documents: list[str],
    task_summary: str | None,
    progress_note: str | None,
    done_criteria: str | None,
    result_note: str | None,
    next_step: str | None,
    risks: str | None,
    follow_up: str | None,
) -> list[str]:
    lines = [
        f"## {task_id} {task_name}",
        "",
        f"- 상태: {status}",
        f"- 우선순위: {priority}",
        f"- 요청일: {request_date}",
        "- 완료일:",
        "- 담당:",
        f"- {owner}" if owner else "- ",
        "- 호스트명:",
        f"- {host_name}" if host_name else "- ",
        "- 호스트 IP:",
        f"- {host_ip}" if host_ip else "- ",
        "- 영향 문서:",
    ]
    if affected_documents:
        lines.extend([f"- `{doc}`" for doc in affected_documents])
    else:
        lines.append("- ")
    lines.extend(
        [
            "- 작업 내용:",
            f"- {task_summary}" if task_summary else "- ",
            "- 진행 현황:",
            f"- {progress_note}" if progress_note else "- ",
            "- 완료 기준:",
            f"- {done_criteria}" if done_criteria else "- ",
            "- 작업 결과:",
            f"- {result_note}" if result_note else "- ",
            "- 다음 세션 시작 포인트:",
            f"- {next_step}" if next_step else "- ",
            "- 남은 리스크:",
            f"- {risks}" if risks else "- ",
            "- 후속 작업:",
            f"- {follow_up}" if follow_up else "- ",
        ]
    )
    return lines


def detect_confirmation_fields(data: dict[str, Any]) -> list[str]:
    mapping = {
        "owner": "담당",
        "host_name": "호스트명",
        "host_ip": "호스트 IP",
        "affected_documents": "영향 문서",
        "done_criteria": "완료 기준",
        "result_note": "작업 결과",
        "next_step": "다음 세션 시작 포인트",
        "risks": "남은 리스크",
        "follow_up": "후속 작업",
    }
    missing: list[str] = []
    for key, label in mapping.items():
        value = data.get(key)
        if value is None or value == "" or value == []:
            missing.append(label)
    return missing


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the backlog-update prototype.")
    parser.add_argument("--project-profile-path", required=True)
    parser.add_argument("--task-name", required=True)
    parser.add_argument("--task-brief", required=True)
    parser.add_argument("--daily-backlog-path")
    parser.add_argument("--target-date")
    parser.add_argument("--task-id")
    parser.add_argument("--mode", choices=["create", "update", "auto"], default="auto")
    parser.add_argument("--status")
    parser.add_argument("--priority", default="high")
    parser.add_argument("--owner")
    parser.add_argument("--host-name")
    parser.add_argument("--host-ip")
    parser.add_argument("--affected-document", action="append", dest="affected_documents", default=[])
    parser.add_argument("--progress-note")
    parser.add_argument("--done-criteria")
    parser.add_argument("--result-note")
    parser.add_argument("--next-step")
    parser.add_argument("--risks")
    parser.add_argument("--follow-up")
    parser.add_argument("--validation-result")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    project_profile_path = resolve_existing_path(args.project_profile_path)
    profile = parse_project_profile(project_profile_path)

    warnings: list[str] = []
    request_date = args.target_date or datetime.now().strftime("%Y-%m-%d")

    daily_backlog_path: Path
    if args.daily_backlog_path:
        daily_backlog_path = Path(args.daily_backlog_path).expanduser().resolve()
    else:
        daily_backlog_path = infer_backlog_path(project_profile_path, profile.get("backlog_path"), request_date)

    existing_tasks = parse_backlog_tasks(daily_backlog_path) if daily_backlog_path.exists() else []

    requested_mode = args.mode
    if requested_mode == "auto":
        requested_mode = "update" if args.task_id else "create"

    operation_type = "create_entry"
    if not daily_backlog_path.exists():
        operation_type = "create_daily_backlog"
    if requested_mode == "update":
        operation_type = "update_entry"

    matched_task: dict[str, Any] | None = None
    if requested_mode == "update":
        if not args.task_id:
            operation_type = "cannot_determine"
            warnings.append("기존 항목 갱신에는 `task_id` 가 필요하다.")
        else:
            for task in existing_tasks:
                if task["task_id"] == args.task_id:
                    matched_task = task
                    break
            if matched_task is None and daily_backlog_path.exists():
                operation_type = "cannot_determine"
                warnings.append(f"`{args.task_id}` 항목을 대상 backlog 에서 찾지 못했다.")

    task_id = args.task_id or suggest_next_task_id(existing_tasks)
    status, status_warnings = determine_status(args.status, args.validation_result, operation_type)
    warnings.extend(status_warnings)

    progress_note = args.progress_note
    if not progress_note:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        progress_note = f"`{timestamp}` 기준 {args.task_brief}"

    result_note = args.result_note
    if args.validation_result and not result_note:
        result_note = args.validation_result

    fields_data = {
        "owner": args.owner,
        "host_name": args.host_name,
        "host_ip": args.host_ip,
        "affected_documents": args.affected_documents,
        "done_criteria": args.done_criteria,
        "result_note": result_note,
        "next_step": args.next_step,
        "risks": args.risks,
        "follow_up": args.follow_up,
    }
    fields_requiring_confirmation = detect_confirmation_fields(fields_data)

    draft_entry = build_draft_entry(
        task_id=task_id,
        task_name=args.task_name,
        status=status,
        priority=args.priority,
        request_date=request_date,
        owner=args.owner,
        host_name=args.host_name,
        host_ip=args.host_ip,
        affected_documents=args.affected_documents,
        task_summary=args.task_brief,
        progress_note=progress_note,
        done_criteria=args.done_criteria,
        result_note=result_note,
        next_step=args.next_step,
        risks=args.risks,
        follow_up=args.follow_up,
    )

    if operation_type == "create_daily_backlog":
        warnings.append("대상 날짜 backlog 파일이 없어 새 파일 초안 생성이 필요하다.")

    index_update_note = None
    if operation_type == "create_daily_backlog":
        index_update_note = "새 날짜 backlog 파일이 생성되면 backlog index 에 링크를 추가해야 한다."

    handoff_update_note = None
    if status in {"in_progress", "blocked", "done"}:
        handoff_update_note = "상태 변화가 handoff 에 반영되어야 하는지 확인한다."

    result = {
        "status": "ok",
        "tool_version": TOOL_VERSION,
        "operation_type": operation_type,
        "target_backlog_path": str(daily_backlog_path),
        "task_id": task_id,
        "task_found": bool(matched_task),
        "draft_entry": draft_entry,
        "status_recommendation": {
            "value": status,
            "reason": (
                "검증 결과가 없으므로 완료 확정 대신 보수적인 상태를 유지한다."
                if status != "done" and args.status == "done"
                else "입력된 상태와 현재 작업 브리핑 기준으로 가장 보수적인 상태를 제안한다."
            ),
        },
        "fields_requiring_confirmation": fields_requiring_confirmation,
        "warnings": warnings,
        "index_update_note": index_update_note,
        "handoff_update_note": handoff_update_note,
        "validation_note": args.validation_result,
        "source_context": {
            "project_profile_path": str(project_profile_path),
            "daily_backlog_exists": daily_backlog_path.exists(),
            "existing_task_count": len(existing_tasks),
        },
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
