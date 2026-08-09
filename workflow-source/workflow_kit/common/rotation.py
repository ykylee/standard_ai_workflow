"""Logic for preventing document bloat by rotating old tasks.

## v1.1.2 에서 고친 것 — 이 도구는 한 번도 동작한 적이 없었다

`handoff_bloat` 경고를 해소하라고 있는 도구인데 `status: error` 만 냈다. 원인이
둘이었고, 두 번째가 더 위험했다:

1. **섹션 이름을 고정 문자열로 찾았다** — `## 5. 최근 완료 작업` / `## 6. 잔여 작업`
   을 찾는데 실제 문서는 `## 4. 최근 완료 작업` / `## 5. 다음 세션 시작 포인트` 다.
   번호는 문서마다 다르고 다음 섹션 제목은 더 다르다. 이제 **번호 무관 제목 매칭 +
   다음 `## ` 헤더까지**로 찾는다.
2. **정렬 방향이 문서와 반대였다** — `items[-max:]` 로 *뒤* 를 남겼다. §4 는
   **앞이 최신** 인데 (사람과 에이전트가 줄곧 앞에 붙여 왔고, state.json 의
   `recent_done_items` 계약도 최신순이다 — `check_recent_done_items_order` 계약 1)
   그대로 돌았다면 **최신 항목을 지우고 오래된 것을 남겼다.** 1번만 고쳤다면
   도구가 "동작하면서" 조용히 최신을 버렸을 것이다.

`workflow_writes.py` 의 writer 도 같은 커밋에서 `insert(0)` 으로 맞췄다 — 두 경로가
반대로 쌓으면 어느 쪽을 고쳐도 다른 쪽이 깨진다.

## baseline 을 건드리지 않는다

예전 구현은 잘라낸 항목을 `- 현재 기준선:` 줄에 이어붙였다. 그 줄은 *어느 커밋
기준인지* 를 적는 자리지 완료 목록이 아니다. 잘라낸 것은 반환값으로만 알린다 —
정보는 `backlog/tasks/` 에 SSOT 로 남아 있어 손실이 아니다.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List

#: `## 4. 최근 완료 작업` / `## 최근 완료 작업` 둘 다. 번호는 문서마다 다르다.
DONE_SECTION_PATTERN = re.compile(r"^##\s+(?:\d+\.\s*)?최근 완료 작업\s*$")

#: 섹션의 끝 = 다음 `## ` 헤더. 제목을 특정하지 않는다 — 예전엔 `## 6. 잔여 작업` 을
#: 기다렸는데 그런 섹션은 이 저장소에 없다.
NEXT_SECTION_PATTERN = re.compile(r"^##\s+")

#: 항목 줄. `- TASK-...` 만 센다 (`- 최근 완료 작업 목록:` 같은 라벨 줄은 제외).
ITEM_PREFIX = "- TASK-"


def _locate_done_section(lines: List[str]) -> tuple[int, int]:
    """(start, end) — start 는 헤더 줄 index, end 는 다음 섹션 헤더 index (없으면 len)."""
    start = -1
    for i, line in enumerate(lines):
        if DONE_SECTION_PATTERN.match(line):
            start = i
            break
    if start == -1:
        return -1, -1
    for j in range(start + 1, len(lines)):
        if NEXT_SECTION_PATTERN.match(lines[j]):
            return start, j
    return start, len(lines)


def rotate_handoff_tasks(
    handoff_path: Path,
    max_done_items: int = 10,
    *,
    newest_first: bool = True,
) -> Dict[str, Any]:
    """handoff §4 를 상한까지 줄인다.

    Args:
        handoff_path: `session_handoff.md`.
        max_done_items: 남길 개수.
        newest_first: 목록의 **앞** 이 최신인가. 기본 True (이 저장소 규약).
            False 면 뒤가 최신이라고 보고 앞에서 버린다.

    Returns:
        ``{"status", "rotated", "rotated_count", "remaining_count", "rotated_items"}``
    """
    if not handoff_path.exists():
        return {"status": "skipped", "reason": "handoff file not found"}

    content = handoff_path.read_text(encoding="utf-8")
    lines = content.splitlines()

    start, end = _locate_done_section(lines)
    if start == -1:
        return {
            "status": "error",
            "message": "Could not locate '최근 완료 작업' section",
            "rotated": False,
        }

    # 항목의 *원래 위치* 를 들고 있어야 라벨 줄과 빈 줄을 보존한 채 지울 수 있다.
    item_indices = [
        i for i in range(start + 1, end) if lines[i].strip().startswith(ITEM_PREFIX)
    ]
    items = [lines[i] for i in item_indices]

    if len(items) <= max_done_items:
        return {
            "status": "ok",
            "message": f"Done items ({len(items)}) within limit ({max_done_items})",
            "rotated": False,
            "rotated_count": 0,
            "remaining_count": len(items),
            "rotated_items": [],
        }

    if newest_first:
        keep_indices = set(item_indices[:max_done_items])
    else:
        keep_indices = set(item_indices[-max_done_items:])

    drop_indices = [i for i in item_indices if i not in keep_indices]
    rotated_items = [lines[i].strip() for i in drop_indices]

    drop_set = set(drop_indices)
    new_lines = [line for i, line in enumerate(lines) if i not in drop_set]

    # 원본이 개행으로 끝났으면 그대로 유지한다 — 끝 개행이 사라지면 diff 가 마지막
    # 줄까지 통째로 바뀐 것처럼 보인다.
    trailing = "\n" if content.endswith("\n") else ""
    handoff_path.write_text("\n".join(new_lines) + trailing, encoding="utf-8")

    return {
        "status": "ok",
        "rotated": True,
        "rotated_count": len(rotated_items),
        "remaining_count": len(items) - len(rotated_items),
        "rotated_items": rotated_items,
    }
