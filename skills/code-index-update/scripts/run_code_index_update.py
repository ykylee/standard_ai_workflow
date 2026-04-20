#!/usr/bin/env python3
"""Prototype runner for the code-index-update skill."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

TOOL_VERSION = "prototype-v1"


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
    while normalized.startswith("`"):
        normalized = normalized[1:].strip()
    while normalized.endswith("`"):
        normalized = normalized[:-1].strip()
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
    }


def path_exists_relative(base: Path, raw: str | None) -> Path | None:
    if not raw:
        return None
    candidate = (base / raw).resolve()
    if candidate.exists():
        return candidate
    return None


def declared_doc_path(base: Path, raw: str | None) -> str | None:
    if not raw:
        return None
    return str((base / raw).resolve())


def dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        normalized = item.strip()
        if normalized and normalized not in seen:
            seen.add(normalized)
            result.append(normalized)
    return result


def classify_changed_file(path_str: str) -> set[str]:
    lower = path_str.lower()
    kinds: set[str] = set()
    is_markdown = lower.endswith(".md")

    if lower.endswith("readme.md"):
        kinds.add("root_or_hub_readme")
    if is_markdown:
        kinds.add("doc")
    if is_markdown and any(
        token in lower
        for token in ["runbook", "/reports/", "release-report", "/dataset", "manifest", "/prompt", "/prompts/"]
    ):
        kinds.add("hub_child_doc")
    if "backlog" in lower:
        kinds.add("backlog_doc")
    if "handoff" in lower:
        kinds.add("handoff_doc")
    if any(lower.endswith(ext) for ext in [".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".rs", ".java"]):
        kinds.add("code")
    if any(lower.endswith(ext) for ext in [".yaml", ".yml", ".json", ".toml", ".ini"]):
        kinds.add("config")
    if lower.startswith("docs/") and is_markdown and lower.count("/") >= 2:
        kinds.add("nested_doc")

    if not kinds:
        kinds.add("other")
    return kinds


def infer_missing_index_targets(changed_files: list[str]) -> list[str]:
    targets: list[str] = []
    for changed in changed_files:
        lower = changed.lower()
        if lower.startswith("docs/operations/runbooks/"):
            targets.append("docs/operations/README.md")
        if "/reports/" in lower or "release-report" in lower:
            targets.append("docs/evals/README.md")
        if "/dataset" in lower or "manifest" in lower:
            targets.append("docs/evals/README.md")
        if lower.endswith("readme.md"):
            targets.append("README.md")
    return dedupe(targets)


def build_index_plan(
    *,
    base_dir: Path,
    repo_root: Path,
    profile: dict[str, Any],
    changed_files: list[str],
    work_backlog_index_path: Path | None,
    session_handoff_path: Path | None,
    change_summary: str | None,
) -> dict[str, Any]:
    index_candidates: list[str] = []
    priority_candidates: list[str] = []
    stale_warnings: list[str] = []
    reasoning_notes: list[str] = []
    suggested_actions: list[str] = []
    confidence_notes: list[str] = []
    structure_signals: list[str] = []
    missing_index_candidates: list[str] = []

    root_readme = repo_root / "README.md"
    if root_readme.exists():
        index_candidates.append(str(root_readme))

    declared_document_home = declared_doc_path(base_dir, profile.get("document_home"))
    document_home = path_exists_relative(base_dir, profile.get("document_home"))
    if declared_document_home:
        index_candidates.append(declared_document_home)
        if not document_home:
            missing_index_candidates.append(declared_document_home)

    declared_operations_root = declared_doc_path(base_dir, profile.get("operations_path"))
    operations_path = path_exists_relative(base_dir, profile.get("operations_path"))
    if declared_operations_root:
        index_candidates.append(declared_operations_root)
        if not operations_path:
            missing_index_candidates.append(declared_operations_root)
        operations_readme = str((Path(declared_operations_root) / "README.md").resolve())
        index_candidates.append(operations_readme)
        if not Path(operations_readme).exists():
            missing_index_candidates.append(operations_readme)

    if work_backlog_index_path and work_backlog_index_path.exists():
        index_candidates.append(str(work_backlog_index_path))
    if session_handoff_path and session_handoff_path.exists():
        index_candidates.append(str(session_handoff_path))

    doc_change_detected = False
    structure_change_detected = False
    code_change_detected = False

    for changed in changed_files:
        kinds = classify_changed_file(changed)
        reasoning_notes.append(f"`{changed}` 는 `{', '.join(sorted(kinds))}` 신호로 분류됐다.")

        if "doc" in kinds:
            doc_change_detected = True
        if "code" in kinds or "config" in kinds:
            code_change_detected = True
        if "nested_doc" in kinds or "root_or_hub_readme" in kinds:
            structure_change_detected = True

        if "root_or_hub_readme" in kinds:
            priority_candidates.append(changed)
            suggested_actions.append("README 또는 허브 문서 자체가 바뀌었으므로 링크와 문서 목록을 다시 확인한다.")

        if "hub_child_doc" in kinds:
            structure_signals.append(f"{changed} 변경은 상위 허브 문서 stale 가능성을 만든다.")
            if declared_operations_root:
                priority_candidates.append(str((Path(declared_operations_root) / "README.md").resolve()))
            elif declared_document_home:
                priority_candidates.append(declared_document_home)
            suggested_actions.append("하위 문서 변경이 허브 링크나 설명에 반영됐는지 확인한다.")

        if "backlog_doc" in kinds and work_backlog_index_path:
            priority_candidates.append(str(work_backlog_index_path))
            suggested_actions.append("날짜별 backlog 변경이 backlog index 설명과 최신 링크에 반영됐는지 확인한다.")

        if "handoff_doc" in kinds and session_handoff_path:
            priority_candidates.append(str(session_handoff_path))

        if "nested_doc" in kinds:
            structure_change_detected = True
            missing_index_candidates.extend(infer_missing_index_targets([changed]))

    summary_lower = (change_summary or "").lower()
    if any(token in summary_lower for token in ["new doc", "새 문서", "문서 추가", "rename", "move", "이동"]):
        structure_change_detected = True
        structure_signals.append("변경 요약에서 문서 구조 변경 신호가 감지됐다.")
    if any(token in summary_lower for token in ["runbook", "report", "dataset", "prompt", "허브"]):
        suggested_actions.append("변경 요약에 허브성 문서 신호가 있어 상위 index 문서를 우선 검토한다.")

    if code_change_detected:
        if declared_operations_root:
            index_candidates.append(str((Path(declared_operations_root) / "README.md").resolve()))
        if work_backlog_index_path:
            index_candidates.append(str(work_backlog_index_path))
        stale_warnings.append("코드/설정 변경이 문서 허브 설명과 최신 구조에 반영됐는지 확인이 필요하다.")

    if doc_change_detected and not any(path.endswith(".md") or path.endswith("README.md") for path in index_candidates):
        stale_warnings.append("문서 변경은 있었지만 재검토할 색인 문서 후보를 찾지 못했다.")

    if structure_change_detected:
        if declared_document_home:
            priority_candidates.append(declared_document_home)
        if root_readme.exists():
            priority_candidates.append(str(root_readme))
        suggested_actions.append("문서 구조 변경 가능성이 있어 루트 README 와 문서 홈을 함께 점검한다.")

    missing_index_candidates = [
        candidate
        for candidate in dedupe(missing_index_candidates)
        if not (repo_root / candidate).exists()
    ]
    if missing_index_candidates:
        stale_warnings.append("변경 경로 기준으로 추정한 색인 문서 일부가 현재 저장소에서 확인되지 않는다.")

    confidence_notes.append("현재 출력은 변경 경로와 프로젝트 프로파일만 사용한 보수적 추천이다.")
    if not structure_change_detected:
        confidence_notes.append("rename 또는 신규 문서 생성 여부는 git diff 없이 확정하지 않았다.")

    return {
        "index_update_candidates": dedupe(index_candidates),
        "priority_index_candidates": dedupe(priority_candidates),
        "stale_index_warnings": dedupe(stale_warnings),
        "warnings": dedupe(stale_warnings),
        "reasoning_notes": dedupe(reasoning_notes),
        "suggested_index_actions": dedupe(suggested_actions),
        "document_structure_signals": dedupe(structure_signals),
        "missing_index_candidates": missing_index_candidates,
        "confidence_notes": dedupe(confidence_notes),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the code-index-update prototype.")
    parser.add_argument("--project-profile-path", required=True)
    parser.add_argument("--changed-file", action="append", dest="changed_files", default=[])
    parser.add_argument("--work-backlog-index-path")
    parser.add_argument("--session-handoff-path")
    parser.add_argument("--change-summary")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.changed_files and not args.change_summary:
        raise SystemExit("at least one --changed-file or --change-summary is required")

    project_profile_path = resolve_existing_path(args.project_profile_path)
    profile = parse_project_profile(project_profile_path)
    base_dir = project_profile_path.parent
    repo_root = Path(__file__).resolve().parents[3]

    work_backlog_index_path = (
        resolve_existing_path(args.work_backlog_index_path) if args.work_backlog_index_path else None
    )
    session_handoff_path = resolve_existing_path(args.session_handoff_path) if args.session_handoff_path else None

    result = build_index_plan(
        base_dir=base_dir,
        repo_root=repo_root,
        profile=profile,
        changed_files=args.changed_files,
        work_backlog_index_path=work_backlog_index_path,
        session_handoff_path=session_handoff_path,
        change_summary=args.change_summary,
    )
    result["status"] = "ok"
    result["tool_version"] = TOOL_VERSION
    result["source_context"] = {
        "project_profile_path": str(project_profile_path),
        "project_name": profile.get("project_name"),
        "changed_files": args.changed_files,
        "change_summary": args.change_summary,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
