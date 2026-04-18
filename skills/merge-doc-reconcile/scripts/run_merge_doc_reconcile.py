#!/usr/bin/env python3
"""Prototype runner for the merge-doc-reconcile skill."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


TASK_HEADER_RE = re.compile(r"^##\s+(TASK-[A-Z0-9-]+)\s+(.+)$")
DOC_LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def iter_lines(path: Path) -> list[str]:
    return read_text(path).splitlines()


def resolve_existing_path(raw: str) -> Path:
    path = Path(raw).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"path does not exist: {path}")
    return path


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
                results.append(normalize_inline_code(stripped[2:].strip()))
            elif stripped:
                break
    return results


def extract_markdown_links(path: Path) -> list[Path]:
    candidates: list[Path] = []
    for match in DOC_LINK_RE.finditer(read_text(path)):
        target = match.group(1).split("#", 1)[0].strip()
        if not target or "://" in target or target.startswith("#"):
            continue
        candidate = (path.parent / target).resolve()
        if candidate.exists():
            candidates.append(candidate)
    return candidates


def dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        normalized = " ".join(item.strip().split())
        if normalized and normalized not in seen:
            seen.add(normalized)
            result.append(normalized)
    return result


def parse_project_profile(path: Path) -> dict[str, Any]:
    lines = iter_lines(path)
    return {
        "project_name": extract_section_value(lines, "프로젝트명"),
        "document_home": extract_section_value(lines, "문서 위키 홈"),
        "operations_path": extract_section_value(lines, "운영 문서 위치"),
        "backlog_path": extract_section_value(lines, "백로그 위치"),
        "handoff_path": extract_section_value(lines, "세션 인계 문서 위치"),
        "constraints": extract_section_value(lines, "환경 제약"),
        "merge_rule": extract_section_value(lines, "병합 규칙"),
    }


def parse_handoff(path: Path) -> dict[str, Any]:
    lines = iter_lines(path)
    return {
        "current_axis": extract_section_value(lines, "현재 주 작업 축"),
        "in_progress_items": extract_list_after_label(lines, "현재 `in_progress` 작업"),
        "blocked_items": extract_list_after_label(lines, "현재 `blocked` 작업"),
        "recent_done_items": extract_list_after_label(lines, "최근 완료 작업 목록"),
        "next_documents": [str(p) for p in extract_markdown_links(path)],
    }


def parse_backlog(path: Path) -> dict[str, Any]:
    tasks: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    for line in iter_lines(path):
        header_match = TASK_HEADER_RE.match(line.strip())
        if header_match:
            if current:
                tasks.append(current)
            current = {"task_id": header_match.group(1), "title": header_match.group(2), "status": ""}
            continue
        if current is None:
            continue
        stripped = line.strip()
        if stripped.startswith("- 상태:"):
            current["status"] = stripped.split(":", 1)[1].strip()
    if current:
        tasks.append(current)
    return {
        "tasks": tasks,
        "in_progress_items": [f"{t['task_id']} {t['title']}" for t in tasks if t["status"] == "in_progress"],
        "blocked_items": [f"{t['task_id']} {t['title']}" for t in tasks if t["status"] == "blocked"],
        "done_items": [f"{t['task_id']} {t['title']}" for t in tasks if t["status"] == "done"],
    }


def compare_lists(label: str, handoff_items: list[str], backlog_items: list[str]) -> list[str]:
    handoff_set = set(dedupe(handoff_items))
    backlog_set = set(dedupe(backlog_items))
    conflicts: list[str] = []
    if handoff_set != backlog_set:
        handoff_view = ", ".join(sorted(handoff_set)) or "없음"
        backlog_view = ", ".join(sorted(backlog_set)) or "없음"
        conflicts.append(f"{label} 항목이 다르다. handoff: {handoff_view} / backlog: {backlog_view}")
    return conflicts


def classify_changed_file(path_str: str) -> str:
    lower = path_str.lower()
    if lower.endswith(".md"):
        if "readme" in lower:
            return "hub_doc"
        if "runbook" in lower:
            return "runbook_doc"
        if "handoff" in lower:
            return "handoff_doc"
        if "backlog" in lower:
            return "backlog_doc"
        return "doc"
    if any(lower.endswith(ext) for ext in [".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".rs", ".java"]):
        return "code"
    if any(lower.endswith(ext) for ext in [".yaml", ".yml", ".json", ".toml", ".ini"]):
        return "config"
    return "other"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the merge-doc-reconcile prototype.")
    parser.add_argument("--project-profile-path", required=True)
    parser.add_argument("--merge-result-summary", required=True)
    parser.add_argument("--session-handoff-path")
    parser.add_argument("--work-backlog-index-path")
    parser.add_argument("--latest-backlog-path")
    parser.add_argument("--changed-file", action="append", dest="changed_files", default=[])
    parser.add_argument("--validation-result")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    profile_path = resolve_existing_path(args.project_profile_path)
    profile = parse_project_profile(profile_path)
    base_dir = profile_path.parent

    warnings: list[str] = []
    state_conflicts: list[str] = []
    reconfirmation_points: list[str] = []
    reconcile_targets: list[str] = []
    draft_reconcile_notes: list[str] = []

    session_handoff_path = resolve_existing_path(args.session_handoff_path) if args.session_handoff_path else None
    work_backlog_index_path = resolve_existing_path(args.work_backlog_index_path) if args.work_backlog_index_path else None
    latest_backlog_path = resolve_existing_path(args.latest_backlog_path) if args.latest_backlog_path else None

    handoff: dict[str, Any] = {"in_progress_items": [], "blocked_items": [], "recent_done_items": [], "next_documents": []}
    backlog: dict[str, Any] = {"in_progress_items": [], "blocked_items": [], "done_items": []}

    if session_handoff_path:
        handoff = parse_handoff(session_handoff_path)
        reconcile_targets.append(str(session_handoff_path))
    else:
        warnings.append("handoff 경로가 없어 세션 요약 상태를 직접 비교하지 못했다.")

    if latest_backlog_path:
        backlog = parse_backlog(latest_backlog_path)
        reconcile_targets.append(str(latest_backlog_path))
    else:
        warnings.append("최신 backlog 경로가 없어 작업 단위 상태를 직접 비교하지 못했다.")

    if work_backlog_index_path:
        reconcile_targets.append(str(work_backlog_index_path))

    operations_doc = None
    if profile.get("operations_path"):
        operations_doc = (base_dir / profile["operations_path"]).resolve()
        if operations_doc.exists():
            reconcile_targets.append(str(operations_doc))

    state_conflicts.extend(compare_lists("in_progress", handoff.get("in_progress_items", []), backlog.get("in_progress_items", [])))
    state_conflicts.extend(compare_lists("blocked", handoff.get("blocked_items", []), backlog.get("blocked_items", [])))

    if backlog.get("done_items") and not args.validation_result:
        warnings.append("병합 후 검증 결과가 없어 done 상태를 재확정할 수 없다.")
        reconfirmation_points.append("병합 후 완료 처리된 작업의 검증 근거를 다시 확인한다.")

    for changed in args.changed_files:
        kind = classify_changed_file(changed)
        if kind in {"runbook_doc", "hub_doc"}:
            reconfirmation_points.append(f"{changed} 링크와 허브 반영 여부를 다시 확인한다.")
        if kind in {"code", "config"}:
            reconfirmation_points.append(f"{changed} 변경이 handoff/backlog 설명과 일치하는지 확인한다.")
        if kind in {"handoff_doc", "backlog_doc"}:
            reconfirmation_points.append(f"{changed} 의 병합 후 상태 요약을 재확정한다.")

    if profile.get("merge_rule"):
        draft_reconcile_notes.append(f"프로젝트 병합 규칙: {profile['merge_rule']}")

    draft_reconcile_notes.extend(
        [
            "병합 후 handoff 와 최신 backlog 의 상태값을 실제 저장소 기준으로 다시 맞춘다.",
            "허브 및 인덱스 문서가 최신 문서 경로와 설명을 반영하는지 확인한다.",
        ]
    )
    if args.changed_files:
        draft_reconcile_notes.append("병합에 포함된 변경 파일과 문서 설명이 어긋나지 않는지 다시 본다.")

    if state_conflicts:
        reconfirmation_points.append("handoff 와 backlog 의 충돌 항목을 우선 정리한다.")

    recommended_review_order = dedupe(
        [
            str(latest_backlog_path) if latest_backlog_path else "",
            str(session_handoff_path) if session_handoff_path else "",
            str(work_backlog_index_path) if work_backlog_index_path else "",
            str(operations_doc) if operations_doc and operations_doc.exists() else "",
        ]
    )
    reconcile_targets = dedupe(reconcile_targets)
    reconfirmation_points = dedupe(reconfirmation_points)
    draft_reconcile_notes = dedupe(draft_reconcile_notes)

    result = {
        "reconcile_targets": reconcile_targets,
        "state_conflicts": state_conflicts,
        "reconfirmation_points": reconfirmation_points,
        "draft_reconcile_notes": draft_reconcile_notes,
        "recommended_review_order": recommended_review_order,
        "warnings": warnings,
        "handoff_update_note": "handoff 의 현재 주 작업 축과 상태 요약을 병합 후 기준으로 재작성할지 확인한다." if session_handoff_path else None,
        "backlog_update_note": "최신 backlog 와 backlog index 의 정합성을 함께 확인한다." if latest_backlog_path or work_backlog_index_path else None,
        "hub_update_note": "허브 문서 링크와 설명이 병합 후 구조를 반영하는지 확인한다." if operations_doc and operations_doc.exists() else None,
        "validation_follow_up": args.validation_result or "병합 후 별도 검증 결과가 없으면 상태 재확정 전에 확인이 필요하다.",
        "source_context": {
            "project_profile_path": str(profile_path),
            "merge_result_summary": args.merge_result_summary,
            "changed_files": args.changed_files,
        },
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
