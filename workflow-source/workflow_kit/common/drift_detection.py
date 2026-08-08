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
    result: dict[str, Any] = {
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
    # v2 (TASK-023): 같은 TASK-ID 인데 *제목이 달라진* 경우. v1 은 ID 집합만 봐서
    # "TASK-001 을 계획했고 TASK-001 을 했다" 면 항상 clean 이었다 — 그 사이에서
    # 내용이 통째로 바뀌었어도 보이지 않았다.
    result["title_drift"] = detect_title_drift(pre_section, post_section)
    return result


# ---------------------------------------------------------------------------
# v2 — title semantic drift (TASK-2026-08-09-main-005)
# ---------------------------------------------------------------------------

#: 제목 유사도가 이 아래면 *의심* 으로 표시한다. `difflib` 비율이라 문자 단위다.
#:
#: 0.6 은 실측으로 고른 값이 아니라 출발점이다. 낮추면 표기 차이(백틱, 괄호)까지
#: 걸리고, 높이면 진짜 교체를 놓친다. **판정이 아니라 후보 선별** 이므로 느슨한
#: 쪽에 둔다 — 최종 판단은 LLM(또는 사람)이 prompt 를 보고 한다.
TITLE_SIMILARITY_THRESHOLD: Final[float] = 0.6

#: TASK-ID 뒤에 붙는 제목의 끝을 알리는 구분자. handoff 는 `— 상세` 로,
#: backlog 는 줄바꿈으로 끊는다.
_TITLE_STOP: Final[re.Pattern[str]] = re.compile(r"\s+[—–]\s+|\s+\|\s+|$")


def extract_task_titles(text: str | None) -> dict[str, str]:
    """TASK-ID → 그 줄에 적힌 제목.

    세 형식을 같이 받는다 — **ID 가 줄의 어디에 오는지가 형식마다 다르다**:

        - `- TASK-xxx 제목 — 상세…`              (handoff §4: ID 가 앞)
        - `- **TASK-xxx** [tag] 제목`             (backlog: ID 가 앞)
        - `- **항목명** — ✅ 닫힘 (TASK-xxx, …)`  (handoff §5: ID 가 **뒤**)

    ID 뒤쪽만 제목으로 삼으면 세 번째 형식에서 설명의 꼬리를 집는다 (실측으로
    걸렸다: `", 본 세션). 4-level enum + Panel 5"`). 그래서 ID *앞* 에 텍스트가
    있으면 그쪽을, 없으면 뒤쪽을 제목으로 본다.

    같은 ID 가 여러 번 나오면 *처음* 것을 쓴다 — 뒤쪽은 보통 상세 설명 안의 참조다.

    Returns:
        dict[str, str] — 제목이 비어 있으면 그 ID 는 넣지 않는다.
    """
    if not text:
        return {}
    titles: dict[str, str] = {}
    for line in text.splitlines():
        match = TASK_ID_PATTERN.search(line)
        if not match:
            continue
        task_id = match.group(0)
        if task_id in titles:
            continue

        head = _strip_markdown(line[:match.start()].lstrip("-*# \t"))
        if head:
            # ID 가 뒤에 오는 형식. 앞쪽에서 첫 구분자까지가 항목명이다.
            title = _TITLE_STOP.split(head, maxsplit=1)[0]
        else:
            tail = line[match.end():].lstrip("*: \t")
            tail = re.sub(r"^\[[^\]]*\]\s*", "", tail)  # `[tag]` 제거
            title = _TITLE_STOP.split(_strip_markdown(tail), maxsplit=1)[0]

        title = title.strip(" .*—–(,")
        if title:
            titles[task_id] = title
    return titles


def _strip_markdown(text: str) -> str:
    """백틱과 `**` 를 벗긴다.

    표기 차이(`` `foo` `` vs `foo`)로 유사도가 깎이면 *진짜 교체* 와 구분이 안 된다.
    """
    return text.replace("`", "").replace("**", "").strip()


def title_similarity(a: str, b: str) -> float:
    """두 제목의 유사도 0.0~1.0 (`difflib`).

    토큰 자카드 대신 문자 기반을 쓴다 — 이 저장소의 제목은 한국어와 영어 식별자가
    섞여 있어서 (`§0.8 #3 scope drift detection`) 공백 토큰화가 잘 안 맞는다.
    """
    from difflib import SequenceMatcher

    return SequenceMatcher(None, a.strip(), b.strip()).ratio()


def detect_title_drift(
    pre_text: str | None,
    post_text: str | None,
    *,
    threshold: float = TITLE_SIMILARITY_THRESHOLD,
) -> dict[str, Any]:
    """같은 TASK-ID 의 제목이 pre ↔ post 사이에서 얼마나 바뀌었는지.

    **advisory 다.** 낮은 유사도가 곧 잘못이 아니다 — 제목을 다듬었을 수도, 작업이
    실제로 바뀌었을 수도 있다. 여기서는 *어디를 봐야 하는지* 만 고른다.

    Returns:
        ``{"pairs": [...], "suspect_count": int, "compared": int, "threshold": float}``
        각 pair: ``{"task_id", "pre_title", "post_title", "similarity", "suspect"}``
    """
    pre_titles = extract_task_titles(pre_text)
    post_titles = extract_task_titles(post_text)
    shared = sorted(set(pre_titles) & set(post_titles))

    pairs: list[dict[str, Any]] = []
    for task_id in shared:
        pre_title = pre_titles[task_id]
        post_title = post_titles[task_id]
        ratio = title_similarity(pre_title, post_title)
        pairs.append({
            "task_id": task_id,
            "pre_title": pre_title,
            "post_title": post_title,
            "similarity": round(ratio, 4),
            "suspect": ratio < threshold,
        })

    return {
        "pairs": pairs,
        "compared": len(pairs),
        "suspect_count": sum(1 for p in pairs if p["suspect"]),
        "threshold": threshold,
    }


def generate_title_drift_prompt(title_drift: dict[str, Any], *, only_suspect: bool = True) -> str:
    """LLM 이 판정할 수 있게 prompt 를 만든다 (advisory).

    이 저장소는 LLM API 를 직접 부르지 않는다 (`purpose_refresh` 와 같은 모델) —
    prompt 를 만들어 놓으면 하네스의 에이전트가 그걸 읽고 판단한다. 자동 적용은
    하지 않는다: 제목이 바뀐 이유를 아는 건 결국 사람이다.

    Returns:
        markdown prompt. 볼 것이 없으면 빈 string.
    """
    pairs = title_drift.get("pairs", [])
    if only_suspect:
        pairs = [p for p in pairs if p.get("suspect")]
    if not pairs:
        return ""

    lines = [
        "# Title Semantic Drift — LLM 판정 요청 (advisory)\n",
        "> ⚠️ 이 판정의 결과는 *advisory* 다. 자동 적용하지 않는다.\n",
        "\n같은 TASK-ID 인데 계획 시점과 완료 시점의 **제목이 달라진** 항목이다.",
        " 문자 유사도로 고른 후보일 뿐이므로, 실제로 *다른 일* 을 한 것인지",
        " 표현만 다듬은 것인지 판단해 달라.\n\n",
        f"임계값: similarity < {title_drift.get('threshold')}"
        f" (비교 {title_drift.get('compared')}건 중 {len(pairs)}건 후보)\n\n",
    ]
    for pair in pairs:
        lines.append(f"## {pair['task_id']} (similarity {pair['similarity']})\n\n")
        lines.append(f"- 계획: {pair['pre_title']}\n")
        lines.append(f"- 완료: {pair['post_title']}\n\n")
    lines.append(
        "## 요청\n\n"
        "각 항목을 `same_work` / `refined_wording` / `different_work` 중 하나로 분류하고,"
        " `different_work` 면 무엇이 어떻게 달라졌는지 한 줄로 적어 달라.\n"
    )
    return "".join(lines)
