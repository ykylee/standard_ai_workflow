"""Output-building helpers for session-oriented skills."""

from __future__ import annotations


def build_session_summary(
    handoff: dict[str, object], backlog: dict[str, object], profile: dict[str, object]
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


def make_session_recommended_action(
    warnings: list[str], backlog: dict[str, object], profile: dict[str, object]
) -> str:
    if warnings:
        return "handoff 와 최신 backlog 의 상태 불일치 여부를 먼저 확인한다."
    if backlog.get("blocked_items"):
        return "차단 작업의 해소 조건과 현재 접근 제약을 먼저 확인한다."
    if profile.get("quick_test"):
        return f"프로파일의 빠른 테스트 명령 `{profile['quick_test']}` 실행 필요 여부를 검토한다."
    return "handoff 와 최신 backlog 를 기준으로 현재 세션의 첫 작업을 확정한다."


def build_reconcile_notes(profile: dict[str, object], changed_files: list[str]) -> list[str]:
    notes: list[str] = []
    if profile.get("merge_rule"):
        notes.append(f"프로젝트 병합 규칙: {profile['merge_rule']}")
    notes.extend(
        [
            "병합 후 handoff 와 최신 backlog 의 상태값을 실제 저장소 기준으로 다시 맞춘다.",
            "허브 및 인덱스 문서가 최신 문서 경로와 설명을 반영하는지 확인한다.",
        ]
    )
    if changed_files:
        notes.append("병합에 포함된 변경 파일과 문서 설명이 어긋나지 않는지 다시 본다.")
    return notes
