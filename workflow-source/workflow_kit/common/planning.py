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


#: 강등이 **이미 기록된 완료를 취소**했을 때 붙는 표식. 호출자는 이 문자열로
#: 그 사건을 구별해 최상위 status 를 `ok` 가 아니게 만든다 (조용한 취소 금지).
DEMOTION_REVERTS_DONE = "demotion_reverts_recorded_done"


def determine_conservative_task_status(
    requested_status: str | None,
    validation_result: str | None,
    operation_type: str,
    current_status: str | None = None,
    *,
    recorded_validation: str | None = None,
) -> tuple[str, list[str]]:
    """보수적 상태 판정.

    v1.1.8 (TASK-2026-08-12-main-008, TASK-023 후속): update 에서 `--status` 미지정이면
    **기존 task 의 상태를 보존**한다. 이전에는 무조건 `in_progress` 로 떨어져서,
    planned task 에 메모만 다는 호출이 상태를 승격시키고 done task 를 되돌렸다 —
    미지정은 "바꾸지 말라" 지 "진행 중으로 하라" 가 아니다.

    done 강등 규칙은 **명시 요청에만** 적용한다: `--status done` 인데 검증 결과가
    없으면 낮춘다. 기존 done 의 보존은 강등하지 않는다 — 그 done 은 이미 검증과
    함께 기록된 상태다.

    ## v1.8.2 (TASK-2026-09-01-main-003) — 그 원칙이 절반만 지켜지고 있었다

    바로 윗 문단은 "이미 검증과 함께 기록된 done 은 강등하지 않는다" 고 **선언**했지만,
    코드는 그것을 `--status` 를 **생략했을 때만** 지켰다. `--status done` 을 명시하면
    파일에 이미 기록된 검증 결과를 **보지 않고** 무조건 낮췄다.

    그 차이가 실제로 물었다 (2026-09-01, 72차): 이미 close 한 task 에 진행 메모만
    덧붙이려고 `--status done --progress-note` 로 재호출했는데 `--validation-result` 를
    안 실어서, 도구가 done → in_progress 로 낮추고 **handoff §4(최근 완료)에 있던
    항목을 §2(진행 중)로 되돌렸다.** 최상위 `status` 는 `ok` 였고 근거는 warnings 한
    줄뿐이라 그대로 커밋·push 됐다.

    그래서 판정을 두 갈래로 나눈다 — **성격이 다른 두 경우이기 때문이다**:

    - `recorded_validation` 이 있으면 → **보존**. 검증은 이미 파일에 있고, 이 호출은
      *새로운* 미검증 done 을 주장하는 것이 아니다. 막을 것이 없다.
    - 어디에도 검증이 없으면 → **강등 유지**(규칙은 옳다). 다만 그것이 *이미 기록된*
      done 을 취소하는 경우라면 `DEMOTION_REVERTS_DONE` 표식을 warning 에 실어,
      호출자가 최상위 status 를 `ok` 가 아니게 만들 수 있게 한다.

    Args:
        recorded_validation: task SSOT 파일에 **이미 기록된** 검증 결과. 인자로 새로
            넘어온 `validation_result` 와 구별한다.
    """
    warnings: list[str] = []
    valid = {"planned", "in_progress", "blocked", "done"}
    if requested_status:
        status = requested_status
        if status not in valid:
            warnings.append(f"알 수 없는 상태 `{status}` 는 사용할 수 없어 `planned` 로 대체한다.")
            status = "planned"
        if status == "done" and not validation_result:
            if recorded_validation:
                warnings.append(
                    "이번 호출에는 검증 결과가 없지만 task 파일에 이미 기록돼 있어 "
                    "`done` 을 보존한다 (새 검증을 남기려면 `--validation-result` 를 준다)."
                )
            else:
                status = "in_progress"
                if current_status == "done":
                    warnings.append(
                        f"[{DEMOTION_REVERTS_DONE}] 검증 결과가 없어 `done` 을 "
                        "`in_progress` 로 낮춘다 — 이 task 는 **이미 done 으로 기록돼 "
                        "있었으므로 그 완료 기록이 취소된다** (handoff 의 최근 완료 목록 "
                        "포함). 되돌릴 뜻이 아니었다면 `--validation-result` 를 주거나 "
                        "`--status` 를 빼고 다시 부른다."
                    )
                else:
                    warnings.append(
                        "검증 결과가 없으므로 `done` 상태는 초안에서 `in_progress` 로 낮춘다."
                    )
        return status, warnings
    if operation_type == "create_entry":
        return "planned", warnings
    if current_status in valid:
        return str(current_status), warnings
    return "in_progress", warnings

