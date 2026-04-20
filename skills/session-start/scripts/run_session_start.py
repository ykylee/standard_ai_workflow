#!/usr/bin/env python3
"""Prototype runner for the session-start skill."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from workflow_kit.common.paths import resolve_existing_path
from workflow_kit.common.project_docs import (
    find_latest_backlog_path,
    parse_backlog,
    parse_handoff,
    parse_project_profile_session,
)

TOOL_VERSION = "prototype-v1"


STATUS_RE = re.compile(r"- 상태:\s*(planned|in_progress|blocked|done)\s*$")
TASK_HEADER_RE = re.compile(r"^##\s+(TASK-[A-Z0-9-]+)\s+(.+)$")
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
    profile = parse_project_profile_session(project_profile_path)

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
        "status": "ok",
        "tool_version": TOOL_VERSION,
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
