"""Normalization helpers shared across workflow kit scripts."""

from __future__ import annotations

import re

from workflow_kit.common.project_docs import WORK_ITEM_ID_PATTERN

# v1.0.2: 정본(`project_docs.WORK_ITEM_ID_PATTERN`)에서 조립한다.
#
# 이전 값 `r"^((?:TASK|WF)-[A-Z0-9-]+)\b"` 는 정본의 **사본**이었고, 문자 클래스가
# 대문자 전용이라 branch-scoped ID 의 소문자 브랜치 segment 에서 매치가 끊겼다:
#
#   TASK-2026-07-27-main-001  →  key 'TASK-2026-07-27-'
#   TASK-2026-07-27-main-002  →  key 'TASK-2026-07-27-'   ← 충돌
#
# `dedupe_work_items` 가 이 key 로 중복을 지우므로 **같은 날짜의 task 가 전부 하나로
# 뭉개져 첫 개만 살아남았다**. state.json 은 자기 내용이 다시 입력으로 돌아오는
# 구조라, 한 번 지워진 항목은 영구 소실된다 (실측: recent_done_items 10건 → 8건,
# 새 항목은 추가되지도 않음).
#
# §2.35 (3) 에서 `WORK_STATUS_RE` 의 같은 결함을 고치며 정본을 세웠는데, 이 사본이
# 남아 있었다 — "규약을 두 곳에 두면 갈라지는 게 아니라 같이 틀린다" 의 세 번째 사례.
WORK_ITEM_ID_RE = re.compile(rf"^({WORK_ITEM_ID_PATTERN})\b")


def normalize_whitespace(value: str) -> str:
    return " ".join(value.strip().split())


def normalize_backticked(value: str) -> str:
    normalized = value.strip()
    if normalized.startswith("`") and normalized.endswith("`"):
        normalized = normalized[1:-1].strip()
    return normalize_whitespace(normalized)


def dedupe_strings(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        normalized = normalize_whitespace(item)
        if normalized and normalized not in seen:
            seen.add(normalized)
            result.append(normalized)
    return result


def is_meaningful_text(value: object) -> bool:
    """빈 문자열과 `TODO:` 플레이스홀더를 걸러낸다.

    `state/builder.py` 에 있던 것을 옮겼다 — `normalize_constraint_values` 가
    같은 술어를 쓰는데, 거기서 복제하면 두 자리가 갈라진다 (본 파일 상단
    `WORK_ITEM_ID_RE` 주석의 "규약을 두 곳에 두면 같이 틀린다" 와 같은 축).
    """
    return isinstance(value, str) and bool(value.strip()) and not value.strip().startswith("TODO:")


def normalize_constraint_values(*values: object) -> list[str]:
    """`주요 제약` / `환경 제약` 값을 state 계약의 **목록**으로 정규화한다.

    **왜 정본이 필요한가 (TASK-2026-09-07-main-002).** 문서 파서의 이 필드는
    `WorkflowDocParser.get_value()` 반환이라 `str | None` 인데, state.json 의
    `session.environment_constraints` 는 목록이다. 그 변환을 소비자마다 따로
    했고 **둘이 서로 달랐다**:

    - `tools/session_start.py` — `[handoff.get(...), profile.get(...)]` 로
      감싸서 넘겼다. 맞다.
    - `state/builder.py` — `cast(list[str], handoff.get("constraints") or [])`.
      `cast` 는 **아무것도 변환하지 않는다**; 타입 검사기의 입을 막을 뿐이다.
      그 뒤 문자열을 iterate 하니 결과가 **한 글자씩** 쪼개졌다:

          'VPN 미연결 상태에서는 staging API 및 운영 콘솔 접근 불가'
            → ['V','P','N','미','연','결', ... ]   (dedupe 후 28개)

    같은 입력에 대해 session-start 와 state.json 이 다른 답을 냈고, `cast` 가
    mypy strict 를 통과시켜 타입 축은 이것을 볼 수 없었다. 이 저장소에서 그동안
    안 보인 이유는 별개다 — main 의 handoff 에는 `주요 제약` 줄이 없어 값이 늘
    비어 있었다. 그 줄을 가진 유일한 코퍼스가 `examples/` 였고, 체크인된 예제
    산출물을 생성기와 대조하는 검사가 없었다 (main-003).

    문자열은 **한 항목**이고, 목록은 펼친다. 둘 다 받는 이유는 프로파일 쪽
    파서가 장차 목록을 낼 수 있어서다 — 그때 이 함수만 이미 맞다.
    """
    items: list[str] = []
    for value in values:
        if isinstance(value, str):
            items.append(value)
        elif isinstance(value, (list, tuple)):
            items.extend(item for item in value if isinstance(item, str))
    return dedupe_normalized_backticked([item for item in items if is_meaningful_text(item)])


def dedupe_normalized_backticked(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        normalized = normalize_backticked(item)
        if normalized and normalized not in seen:
            seen.add(normalized)
            result.append(normalized)
    return result


def dedupe_work_items(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        normalized = normalize_backticked(item)
        match = WORK_ITEM_ID_RE.match(normalized)
        key = match.group(1) if match else normalized
        if normalized and key not in seen:
            seen.add(key)
            result.append(normalized)
    return result
