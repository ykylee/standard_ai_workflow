"""Output-building helpers for session-oriented skills."""

from __future__ import annotations


def build_session_summary(
    handoff: dict[str, object], backlog: dict[str, object], profile: dict[str, object]
) -> list[str]:
    summary: list[str] = []
    
    # Extract current task mode if available
    current_mode = None
    tasks = backlog.get("tasks", [])
    if isinstance(tasks, list):
        for task in tasks:
            if isinstance(task, dict) and task.get("status") == "in_progress":
                current_mode = task.get("mode")
                break
    
    if current_mode:
        summary.append(f"현재 작업 모드: **{current_mode}**")
        summary.extend(build_mode_guidelines(current_mode))
    else:
        # Try to recommend a mode based on task titles
        in_progress_tasks = [t for t in tasks if isinstance(t, dict) and t.get("status") == "in_progress"]
        if in_progress_tasks:
            recommended = recommend_task_mode(in_progress_tasks[0].get("title", ""))
            if recommended:
                summary.append(f"추천 작업 모드: **{recommended}** (자동 감지)")
                summary.extend(build_mode_guidelines(recommended))
                summary.append("참고: 백로그에 `- 모드: {recommended}`를 명시하여 고정할 수 있습니다.")

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
    return summary[:8]


def build_mode_guidelines(mode: str) -> list[str]:
    guidelines = {
        "Analysis": [
            "가이드: 구조 분석 및 탐색 중심. `doc-worker`를 활용하여 병렬 탐색하고 `code_index`를 갱신한다.",
        ],
        "Requirements": [
            "가이드: 니즈 수집 및 명세화 중심. 사용자 질문을 통해 제약 사항을 명확히 하고 `requirements.md`를 작성한다.",
        ],
        "Design": [
            "가이드: 아키텍처 및 상세 설계 중심. `main`급 모델을 사용하여 `technical_spec.md`를 설계한다.",
        ],
        "Planning": [
            "가이드: 태스크 분해 및 일정 계획 중심. 목표를 최소 단위 작업으로 쪼개어 백로그에 등록한다.",
        ],
        "Implementation": [
            "가이드: 코드 작성 및 단위 검증 중심. `code-worker`와 `validation-worker` 루프를 통해 즉시 검증한다.",
        ],
        "Refactoring": [
            "가이드: 코드 개선 및 회귀 테스트 중심. 기능 변경 없이 품질을 높이고 `validation-worker`로 무결성을 확인한다.",
        ],
    }
    return guidelines.get(mode, [])


def recommend_task_mode(title: str) -> str | None:
    t = title.lower()
    if any(k in t for k in ["analysis", "분석", "조사", "탐색", "investigate"]):
        return "Analysis"
    if any(k in t for k in ["requirement", "요구", "명세", "needs"]):
        return "Requirements"
    if any(k in t for k in ["design", "설계", "architecture", "아키텍처"]):
        return "Design"
    if any(k in t for k in ["plan", "계획", "roadmap", "일정"]):
        return "Planning"
    if any(k in t for k in ["refactor", "리팩터", "개선", "cleanup", "정리"]):
        return "Refactoring"
    if any(k in t for k in ["implement", "구현", "feat", "add", "fix", "버그", "수정", "작업"]):
        return "Implementation"
    return None


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
