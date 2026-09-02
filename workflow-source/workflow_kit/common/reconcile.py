"""Shared state comparison helpers for workflow kit skills.

## 무엇을 재는가 (TASK-2026-09-02-main-002)

handoff 의 열린 작업 목록과 **backlog SSOT** 를 대조한다. 두 가지가 이 모듈의
계약이다:

1. **키는 task ID 다.** handoff 는 `TASK-… <제목>` 으로 적고 task corpus 는
   `TASK-…` 만 낸다. 문자열 집합으로 비교하면 *같은 항목이 늘 다르게* 보인다.
   같은 저장소의 `dedupe_work_items` 는 이미 `WORK_ITEM_ID_RE` 로 ID 를 키로
   쓴다 — state.json 생성기는 ID 로 볼 줄 알았고 이 경고 경로만 몰랐다.
2. **다르면 무엇이 다른지 말한다.** 예전 문안은 "다를 수 있으므로 수동
   재확인이 필요하다" 였다. 사람이 매번 두 문서를 손으로 대조해야 했고, 그
   대조는 도구가 이미 들고 있는 두 목록의 차집합이다.

ID 가 없는 항목(산문)은 정규화된 본문 자체가 키다 — 추적되지 않는 작업이
handoff 에만 있다는 것은 **진짜 발견**이라 조용히 넘기지 않는다.
"""

from __future__ import annotations

from workflow_kit.common.normalize import WORK_ITEM_ID_RE, normalize_backticked

# 충돌 문안의 고정 조각. 소비자(검사·하네스)가 경고 목록에서 이 줄을 골라낼 때
# 리터럴을 사본으로 들고 가면 문안이 바뀌는 순간 조용히 아무것도 안 고른다.
STATE_CONFLICT_MARKER = "항목이 handoff 와 backlog 사이에서 다르다"


def _keyed_items(items: list[str]) -> dict[str, str]:
    """work item 목록을 task ID 를 키로 색인한다 (ID 가 없으면 정규화 본문).

    같은 ID 가 두 번 오면 **먼저 온 표기**를 남긴다 — 비교 결과가 아니라 사람에게
    보여줄 문자열을 고르는 자리라, 어느 쪽이든 판정은 같다.
    """
    keyed: dict[str, str] = {}
    for item in items:
        normalized = normalize_backticked(item)
        if not normalized:
            continue
        # ID 매칭 전에 backtick 을 걷는다. `normalize_backticked` 는 **문자열
        # 전체**가 감싸였을 때만 벗기므로, handoff 에 흔한 `` `TASK-x` 제목 ``
        # 표기에서는 선두 backtick 이 남아 ID 정규식이 첫 글자에서 끊긴다.
        candidate = normalized.replace("`", "")
        match = WORK_ITEM_ID_RE.match(candidate)
        key = match.group(1) if match else candidate
        keyed.setdefault(key, normalized)
    return keyed


def diff_state_lists(
    handoff_items: list[str], backlog_items: list[str]
) -> tuple[list[str], list[str]]:
    """(handoff 에만 있는 항목, backlog 에만 있는 항목). 둘 다 비면 정합이다."""
    handoff_keyed = _keyed_items(handoff_items)
    backlog_keyed = _keyed_items(backlog_items)
    only_handoff = sorted(
        display for key, display in handoff_keyed.items() if key not in backlog_keyed
    )
    only_backlog = sorted(
        display for key, display in backlog_keyed.items() if key not in handoff_keyed
    )
    return only_handoff, only_backlog


def _conflict_sentence(label: str, only_handoff: list[str], only_backlog: list[str]) -> str:
    parts: list[str] = []
    if only_handoff:
        parts.append(f"handoff 에만: {', '.join(only_handoff)}")
    if only_backlog:
        parts.append(f"backlog 에만: {', '.join(only_backlog)}")
    return f"{label} {STATE_CONFLICT_MARKER} — " + " / ".join(parts)


def compare_state_lists(handoff_items: list[str], backlog_items: list[str], label: str) -> list[str]:
    only_handoff, only_backlog = diff_state_lists(handoff_items, backlog_items)
    if not only_handoff and not only_backlog:
        return []
    return [_conflict_sentence(label, only_handoff, only_backlog)]


def explain_state_conflicts(handoff_items: list[str], backlog_items: list[str], label: str) -> list[str]:
    return compare_state_lists(handoff_items, backlog_items, label)
