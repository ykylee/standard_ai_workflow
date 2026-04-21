#!/usr/bin/env python3
"""Prototype runner for the validation-plan skill."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from workflow_kit.common.change_types import detect_validation_change_types
from workflow_kit.common.normalize import dedupe_strings
from workflow_kit.common.paths import resolve_existing_path
from workflow_kit.common.planning import collect_validation_levels
from workflow_kit.common.project_docs import parse_project_profile_validation
from workflow_kit.common.text import normalize_inline_code

TOOL_VERSION = "prototype-v1"

def split_commands(raw: str | None) -> list[str]:
    if not raw:
        return []
    return [normalize_inline_code(item.strip()) for item in raw.split(",") if item.strip()]


def build_validation_plan(
    *,
    profile: dict[str, Any],
    change_types: list[str],
    changed_files: list[str],
    session_handoff_path: Path | None,
    latest_backlog_path: Path | None,
) -> dict[str, Any]:
    recommended_commands: list[dict[str, str]] = []
    confirmation_commands: list[dict[str, str]] = []
    documentation_checks: list[str] = []
    evidence_expectations: list[str] = []
    deferred_validation_items: list[dict[str, str]] = []
    warnings: list[str] = []
    confidence_notes: list[str] = []

    quick_tests = split_commands(profile.get("quick_tests"))
    isolated_tests = split_commands(profile.get("isolated_tests"))
    runtime_checks = split_commands(profile.get("runtime_checks"))

    if any(item in change_types for item in ["code", "config"]):
        for command in quick_tests:
            recommended_commands.append({"command": command, "reason": "기본 빠른 테스트"})
        for command in isolated_tests:
            recommended_commands.append({"command": command, "reason": "격리 검증 또는 추가 회귀 확인"})

    if "ui" in change_types:
        for command in runtime_checks:
            recommended_commands.append({"command": command, "reason": "화면 또는 사용자 흐름 smoke 확인"})
        evidence_expectations.append("UI 변경은 스크린샷, smoke 결과, 또는 동등한 시각 증빙을 남긴다.")

    if "ops" in change_types:
        for command in runtime_checks:
            confirmation_commands.append({"command": command, "reason": "배포/운영 변경과 연계된 실행 확인"})
        documentation_checks.append("헬스체크 확인 결과와 롤백 절차 검토 여부를 남긴다.")
        documentation_checks.append("운영팀 공지 또는 승인 필요 여부를 확인한다.")

    if "docs" in change_types:
        documentation_checks.append("허브 문서, 메타데이터, 관련 링크 무결성을 함께 점검한다.")
        evidence_expectations.append("문서 변경은 관련 허브 또는 상태 문서 동기화 여부를 기록한다.")

    if "prompt_or_eval" in change_types:
        documentation_checks.append("기준 실험 ID, fixture, 또는 산출물 버전 정합성을 확인한다.")
        evidence_expectations.append("프롬프트/평가 자산 변경은 비교 기준과 결과 요약을 backlog 또는 handoff 에 남긴다.")

    for point in profile.get("validation_points", []):
        lower = point.lower()
        if "코드 변경 시" in point or "문서 변경 시" in point or "ui 변경 시" in point or "배포/운영 변경 시" in point:
            continue
        if ("code" in change_types or "config" in change_types) and any(token in lower for token in ["테스트", "lint", "스키마", "fixture", "golden"]):
            documentation_checks.append(point)
        if "docs" in change_types and any(token in lower for token in ["링크", "메타데이터", "버전", "runbook"]):
            documentation_checks.append(point)
        if "ui" in change_types and any(token in lower for token in ["스크린샷", "smoke", "화면"]):
            documentation_checks.append(point)
        if "ops" in change_types and any(token in lower for token in ["헬스체크", "롤백", "공지"]):
            documentation_checks.append(point)
        if "prompt_or_eval" in change_types and any(token in lower for token in ["실험", "dataset", "report", "manifest"]):
            documentation_checks.append(point)

    for rule in profile.get("exception_rules", []):
        lowered = rule.lower()
        if any(token in lowered for token in ["vpn", "secure runner", "승인", "review", "검토", "로컬"]):
            warnings.append(rule)

    if session_handoff_path:
        deferred_validation_items.append(
            {
                "item": "검증 결과와 미실행 사유를 handoff 에 남길지 확인",
                "suggested_record_path": str(session_handoff_path),
            }
        )
    if latest_backlog_path:
        deferred_validation_items.append(
            {
                "item": "오늘 세션에서 생략한 검증 항목을 backlog 에 후속 작업으로 남길지 확인",
                "suggested_record_path": str(latest_backlog_path),
            }
        )

    if not recommended_commands and not confirmation_commands:
        warnings.append("프로젝트 프로파일에서 실행 가능한 검증 명령을 충분히 찾지 못했다.")
        confidence_notes.append("명령 추천보다 문서 기반 체크리스트 비중이 높다.")
    else:
        confidence_notes.append("프로젝트 프로파일의 기본 명령을 우선 사용해 검증 계획을 구성했다.")

    if changed_files and all(item == "docs" for item in change_types):
        confidence_notes.append("현재 변경은 문서 중심으로 보여 실행 검증은 최소화했다.")

    return {
        "recommended_validation_levels": collect_validation_levels(change_types),
        "recommended_commands": recommended_commands,
        "commands_requiring_confirmation": confirmation_commands,
        "documentation_checks": dedupe_strings(documentation_checks),
        "evidence_expectations": dedupe_strings(evidence_expectations),
        "deferred_validation_items": deferred_validation_items,
        "warnings": dedupe_strings(warnings),
        "confidence_notes": dedupe_strings(confidence_notes),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the validation-plan prototype.")
    parser.add_argument("--project-profile-path", required=True)
    parser.add_argument("--changed-file", action="append", dest="changed_files", default=[])
    parser.add_argument("--change-summary")
    parser.add_argument("--session-handoff-path")
    parser.add_argument("--latest-backlog-path")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.changed_files and not args.change_summary:
        raise SystemExit("at least one --changed-file or --change-summary is required")

    project_profile_path = resolve_existing_path(args.project_profile_path)
    profile = parse_project_profile_validation(project_profile_path)
    session_handoff_path = resolve_existing_path(args.session_handoff_path) if args.session_handoff_path else None
    latest_backlog_path = resolve_existing_path(args.latest_backlog_path) if args.latest_backlog_path else None
    change_types = detect_validation_change_types(args.changed_files, args.change_summary)

    result = {
        "status": "ok",
        "tool_version": TOOL_VERSION,
        "detected_change_types": change_types,
        **build_validation_plan(
            profile=profile,
            change_types=change_types,
            changed_files=args.changed_files,
            session_handoff_path=session_handoff_path,
            latest_backlog_path=latest_backlog_path,
        ),
        "source_context": {
            "project_profile_path": str(project_profile_path),
            "project_name": profile.get("project_name"),
            "changed_files": args.changed_files,
            "change_summary": args.change_summary,
        },
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
