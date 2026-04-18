#!/usr/bin/env python3
"""Prototype runner for the doc-sync skill."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


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


def parse_project_profile(path: Path) -> dict[str, Any]:
    lines = iter_lines(path)
    return {
        "project_name": extract_section_value(lines, "프로젝트명"),
        "document_home": extract_section_value(lines, "문서 위키 홈"),
        "operations_path": extract_section_value(lines, "운영 문서 위치"),
        "backlog_path": extract_section_value(lines, "백로그 위치"),
        "handoff_path": extract_section_value(lines, "세션 인계 문서 위치"),
        "environment_path": extract_section_value(lines, "환경 기록 위치"),
    }


def path_exists_relative(base: Path, raw: str | None) -> Path | None:
    if not raw:
        return None
    candidate = (base / raw).resolve()
    if candidate.exists():
        return candidate
    return None


def dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        normalized = item.strip()
        if normalized and normalized not in seen:
            seen.add(normalized)
            result.append(normalized)
    return result


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


def build_candidates(
    *,
    base_dir: Path,
    profile: dict[str, Any],
    changed_files: list[str],
    session_handoff_path: Path | None,
    work_backlog_index_path: Path | None,
    latest_backlog_path: Path | None,
    change_summary: str | None,
) -> dict[str, Any]:
    operations_doc = path_exists_relative(base_dir, profile.get("operations_path"))
    doc_home = path_exists_relative(base_dir, profile.get("document_home"))
    impacted: list[str] = []
    hub_candidates: list[str] = []
    status_doc_candidates: list[str] = []
    stale_warnings: list[str] = []
    reasoning_notes: list[str] = []
    follow_up_actions: list[str] = []
    validation_doc_candidates: list[str] = []

    if session_handoff_path and session_handoff_path.exists():
        status_doc_candidates.append(str(session_handoff_path))
    if latest_backlog_path and latest_backlog_path.exists():
        status_doc_candidates.append(str(latest_backlog_path))
    if work_backlog_index_path and work_backlog_index_path.exists():
        hub_candidates.append(str(work_backlog_index_path))
    if operations_doc and operations_doc.exists():
        hub_candidates.append(str(operations_doc))
    if doc_home and doc_home.exists():
        hub_candidates.append(str(doc_home))

    for changed in changed_files:
        kind = classify_changed_file(changed)
        reasoning_notes.append(f"`{changed}` 는 `{kind}` 유형 변경으로 분류됐다.")
        if kind in {"handoff_doc", "backlog_doc", "doc"}:
            impacted.append(changed)
            if "handoff" in changed.lower() and session_handoff_path:
                status_doc_candidates.append(str(session_handoff_path))
            if "backlog" in changed.lower():
                if latest_backlog_path:
                    status_doc_candidates.append(str(latest_backlog_path))
                if work_backlog_index_path:
                    hub_candidates.append(str(work_backlog_index_path))
        if kind == "hub_doc":
            hub_candidates.append(changed)
            impacted.append(changed)
        if kind == "runbook_doc":
            impacted.append(changed)
            if operations_doc:
                hub_candidates.append(str(operations_doc))
            follow_up_actions.append("runbook 링크가 운영 허브에 반영됐는지 확인한다.")
        if kind in {"code", "config"}:
            if session_handoff_path:
                status_doc_candidates.append(str(session_handoff_path))
            if latest_backlog_path:
                status_doc_candidates.append(str(latest_backlog_path))
            if operations_doc:
                hub_candidates.append(str(operations_doc))
            stale_warnings.append(
                f"{changed} 변경이 운영 문서에 반영됐는지 아직 확인되지 않았다."
            )
            follow_up_actions.append("코드/설정 변경이 관련 운영 문서에 반영됐는지 확인한다.")

    summary_lower = (change_summary or "").lower()
    if "runbook" in summary_lower:
        follow_up_actions.append("runbook 내용과 허브 링크 최신성을 함께 점검한다.")
        if operations_doc:
            hub_candidates.append(str(operations_doc))
    if "handoff" in summary_lower and session_handoff_path:
        status_doc_candidates.append(str(session_handoff_path))
    if "backlog" in summary_lower and latest_backlog_path:
        status_doc_candidates.append(str(latest_backlog_path))

    if any(classify_changed_file(item) in {"code", "config"} for item in changed_files):
        validation_doc_candidates.extend(dedupe(status_doc_candidates))
        if not status_doc_candidates:
            stale_warnings.append("코드 변경은 있었지만 상태 문서 후보를 찾지 못했다.")

    impacted_documents = dedupe(impacted + status_doc_candidates)
    hub_update_candidates = dedupe(hub_candidates)
    status_doc_candidates = dedupe(status_doc_candidates)
    follow_up_actions = dedupe(follow_up_actions)

    recommended_review_order = dedupe(
        [*impacted_documents, *status_doc_candidates, *hub_update_candidates]
    )
    confidence_notes = []
    if stale_warnings:
        confidence_notes.append("현재 출력에는 추정 기반 후보가 포함되어 있어 수동 검토가 필요하다.")
    else:
        confidence_notes.append("입력된 변경 파일 기준으로 직접 영향 문서를 우선 정리했다.")

    return {
        "impacted_documents": impacted_documents,
        "hub_update_candidates": hub_update_candidates,
        "status_doc_candidates": status_doc_candidates,
        "validation_doc_candidates": dedupe(validation_doc_candidates),
        "stale_warnings": dedupe(stale_warnings),
        "reasoning_notes": dedupe(reasoning_notes),
        "recommended_review_order": recommended_review_order,
        "follow_up_actions": follow_up_actions,
        "confidence_notes": confidence_notes,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the doc-sync prototype.")
    parser.add_argument("--project-profile-path", required=True)
    parser.add_argument("--changed-file", action="append", dest="changed_files", default=[])
    parser.add_argument("--session-handoff-path")
    parser.add_argument("--work-backlog-index-path")
    parser.add_argument("--latest-backlog-path")
    parser.add_argument("--change-summary")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.changed_files and not args.change_summary:
        raise SystemExit("at least one --changed-file or --change-summary is required")

    project_profile_path = resolve_existing_path(args.project_profile_path)
    profile = parse_project_profile(project_profile_path)
    base_dir = project_profile_path.parent

    session_handoff_path = resolve_existing_path(args.session_handoff_path) if args.session_handoff_path else None
    work_backlog_index_path = (
        resolve_existing_path(args.work_backlog_index_path) if args.work_backlog_index_path else None
    )
    latest_backlog_path = resolve_existing_path(args.latest_backlog_path) if args.latest_backlog_path else None

    result = build_candidates(
        base_dir=base_dir,
        profile=profile,
        changed_files=args.changed_files,
        session_handoff_path=session_handoff_path,
        work_backlog_index_path=work_backlog_index_path,
        latest_backlog_path=latest_backlog_path,
        change_summary=args.change_summary,
    )
    result["source_context"] = {
        "project_profile_path": str(project_profile_path),
        "changed_files": args.changed_files,
        "change_summary": args.change_summary,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
