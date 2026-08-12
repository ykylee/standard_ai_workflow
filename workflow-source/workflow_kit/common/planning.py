"""Planning helpers shared across workflow kit skills."""

from __future__ import annotations

from workflow_kit.common.normalize import dedupe_strings


def collect_validation_levels(change_types: list[str]) -> list[str]:
    levels: list[str] = []
    if change_types == ["docs"]:
        levels.append("documentation")
    if any(item in change_types for item in ["code", "config"]):
        levels.append("standard")
    if "ui" in change_types:
        levels.append("ui_extended")
    if "ops" in change_types:
        levels.append("release_sensitive")
    if "prompt_or_eval" in change_types:
        levels.append("artifact_sensitive")
    if not levels:
        levels.append("light_review")
    return dedupe_strings(levels)


def determine_conservative_task_status(
    requested_status: str | None,
    validation_result: str | None,
    operation_type: str,
    current_status: str | None = None,
) -> tuple[str, list[str]]:
    """보수적 상태 판정.

    v1.1.8 (TASK-2026-08-12-main-008, TASK-023 후속): update 에서 `--status` 미지정이면
    **기존 task 의 상태를 보존**한다. 이전에는 무조건 `in_progress` 로 떨어져서,
    planned task 에 메모만 다는 호출이 상태를 승격시키고 done task 를 되돌렸다 —
    미지정은 "바꾸지 말라" 지 "진행 중으로 하라" 가 아니다.

    done 강등 규칙은 **명시 요청에만** 적용한다: `--status done` 인데 검증 결과가
    없으면 낮춘다. 기존 done 의 보존은 강등하지 않는다 — 그 done 은 이미 검증과
    함께 기록된 상태다.
    """
    warnings: list[str] = []
    valid = {"planned", "in_progress", "blocked", "done"}
    if requested_status:
        status = requested_status
        if status not in valid:
            warnings.append(f"알 수 없는 상태 `{status}` 는 사용할 수 없어 `planned` 로 대체한다.")
            status = "planned"
        if status == "done" and not validation_result:
            warnings.append("검증 결과가 없으므로 `done` 상태는 초안에서 `in_progress` 로 낮춘다.")
            status = "in_progress"
        return status, warnings
    if operation_type == "create_entry":
        return "planned", warnings
    if current_status in valid:
        return str(current_status), warnings
    return "in_progress", warnings

