"""scope drift detection — 표준 §0.8 #3 (v0.15.26+)

seed/claim 시점에 적은 *다음에 할 일* (planned) 과 실제 한 일 (post-handoff 의
*최근 완료 작업* + git log) 의 TASK-ID 를 비교해 *범위 이탈* 을 검출한다.
병합 시점 (또는 handoff close 시점) 에 advisory 로 *판단* 만 한다 — 자동 block
하지 않는다 (§5D.4 정합).

3-way enum:
    - ``planned_done``     — pre 에 있고, post ∪ git_log 에도 있음 (정상)
    - ``planned_undone``   — pre 에 있고, post ∪ git_log 에 *없음* (놓친 일)
    - ``unplanned_done``   — pre 에 *없고*, post ∪ git_log 에 있음 (범위 creep)

drift score = ``(|unplanned| + |undone|) / max(|planned|, 1)`` — 0..∞. advisory:
    - 0      = clean
    - 0~0.3  = minor (small adjustments)
    - 0.3~0.7 = significant
    - 0.7+   = major (re-evaluate scope)

Title semantic drift (planned TASK-001: A → done TASK-001: B) 는 v2 (LLM-based).

Public API:
    extract_section(text, header) -> str
    extract_task_ids(text) -> set[str]
    detect_scope_drift(*, pre_text, post_text, git_log_text="", pre_section_header, post_section_header) -> dict
"""

from __future__ import annotations

import re
from typing import Any, Final


#: TASK-2026-08-08-main-014 형식. \d{4}-\d{2}-\d{2} + [\w-]+ + \d+ (3+ 자리).
#: branch name 은 [a-z0-9-]+ (대문자 X). 너무 strict 하면 false negative, 너무
#: loose 하면 false positive. *현실적* TASK-ID 만 매치.
TASK_ID_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"\bTASK-\d{4}-\d{2}-\d{2}-[a-z0-9][a-z0-9-]*-\d+\b"
)


#: 섹션 헤더 패턴. `## 5. 다음에 할 일 (순서)` / `## 4. 최근 완료 작업` 모두 매치.
#: 공백 / 괄호 / 숫자 prefix 모두 허용.
SECTION_HEADER_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"^(?P<hashes>#{1,6})\s+(?P<title>.+?)\s*$",
    re.MULTILINE,
)


def extract_task_ids(text: str | None) -> set[str]:
    """text 에서 TASK-xxx ID 들을 추출. 중복 제거, sort 된 set 반환.

    Returns:
        set[str] — 발견된 TASK-xxx ID 들. text 가 None / 빈 string 이면 *빈 set*.
    """
    if not text:
        return set()
    return set(TASK_ID_PATTERN.findall(text))


def extract_section(text: str | None, header_substring: str) -> str:
    """markdown text 에서 *header_substring* 을 *제목에 포함* 하는 섹션의 본문을 추출.

    예: ``extract_section(handoff, "다음에 할 일")`` → "## 5. 다음에 할 일 (순서)"
    부터 다음 ``## `` 까지의 본문. *없으면* 빈 string.

    Args:
        text: markdown 원문.
        header_substring: 매치할 header 부분 문자열 (case-sensitive).

    Returns:
        섹션 본문 (헤더 / 다음 헤더 제외). 발견 못 하면 "".
    """
    if not text:
        return ""
    lines = text.splitlines()
    start_idx = -1
    start_level = 0
    for i, line in enumerate(lines):
        m = SECTION_HEADER_PATTERN.match(line)
        if not m:
            continue
        title = m.group("title")
        if header_substring in title:
            start_idx = i + 1
            start_level = len(m.group("hashes"))
            break
    if start_idx == -1:
        return ""
    # 다음 동일/상위 레벨 헤더까지 본문
    end_idx = len(lines)
    for j in range(start_idx, len(lines)):
        m = SECTION_HEADER_PATTERN.match(lines[j])
        if not m:
            continue
        if len(m.group("hashes")) <= start_level:
            end_idx = j
            break
    return "\n".join(lines[start_idx:end_idx])


def _drift_score(*, planned: int, unplanned: int, undone: int) -> float:
    """drift score = (|unplanned| + |undone|) / max(|planned|, 1). 0..∞."""
    if planned <= 0:
        return float("inf") if (unplanned + undone) > 0 else 0.0
    return (unplanned + undone) / planned


def detect_scope_drift(
    *,
    pre_text: str | None,
    post_text: str | None,
    git_log_text: str = "",
    pre_section_header: str = "다음에 할 일",
    post_section_header: str = "최근 완료 작업",
) -> dict[str, Any]:
    """pre + post + git log 3-way 비교.

    Args:
        pre_text: 작업 시작 시점의 handoff 본문 (or None / 빈 string).
        post_text: 작업 종료 시점의 handoff 본문 (or None).
        git_log_text: ``git log <range>`` 의 stdout (commit messages).
        pre_section_header: pre 에서 *planned* 섹션을 가리키는 헤더 substring.
            (default "다음에 할 일" — `session_handoff.md` 의 §5 와 §1 둘 다 매치,
            먼저 발견된 섹션 사용.)
        post_section_header: post 에서 *done* 섹션 헤더 substring. (default
            "최근 완료 작업".)

    Returns:
        ``{"planned_done": [...], "planned_undone": [...], "unplanned_done": [...],
            "drift_score": float, "score_band": "clean"/"minor"/"significant"/"major",
            "warnings": [...], "counts": {...}}``
    """
    warnings: list[str] = []
    pre_section = extract_section(pre_text, pre_section_header) if pre_text else ""
    post_section = extract_section(post_text, post_section_header) if post_text else ""
    if not pre_section and pre_text:
        warnings.append(f"pre_section: '{pre_section_header}' not found in pre handoff")
    if not post_section and post_text:
        warnings.append(f"post_section: '{post_section_header}' not found in post handoff")
    if not pre_text:
        warnings.append("pre_text is None/empty — all done items treated as unplanned")
    if not post_text and not git_log_text:
        warnings.append("post_text and git_log_text both None/empty — nothing to compare")
    planned_ids = extract_task_ids(pre_section)
    post_done_ids = extract_task_ids(post_section) | extract_task_ids(git_log_text)
    planned_done = sorted(planned_ids & post_done_ids)
    planned_undone = sorted(planned_ids - post_done_ids)
    unplanned_done = sorted(post_done_ids - planned_ids)
    score = _drift_score(
        planned=len(planned_ids),
        unplanned=len(unplanned_done),
        undone=len(planned_undone),
    )
    if score == float("inf"):
        band = "major"  # no plan, but did something
    elif score == 0.0:
        band = "clean"
    elif score < 0.3:
        band = "minor"
    elif score < 0.7:
        band = "significant"
    else:
        band = "major"
    return {
        "planned_done": planned_done,
        "planned_undone": planned_undone,
        "unplanned_done": unplanned_done,
        "drift_score": score,
        "score_band": band,
        "warnings": warnings,
        "counts": {
            "planned": len(planned_ids),
            "done": len(post_done_ids),
            "planned_done": len(planned_done),
            "planned_undone": len(planned_undone),
            "unplanned_done": len(unplanned_done),
        },
    }
