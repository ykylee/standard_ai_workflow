"""title semantic drift v2 smoke (TASK-2026-08-09-main-005, §7.5 v2)

v1 (TASK-018) 은 TASK-ID *집합* 만 비교했다. "TASK-001 을 계획했고 TASK-001 을
했다" 면 그 사이에서 내용이 통째로 바뀌었어도 언제나 clean 이었다. v2 는 같은 ID 의
**제목** 을 비교해 후보를 고르고, 판정은 LLM prompt 로 넘긴다 (advisory).

검증 케이스 (9):
    1. extract_task_titles — handoff 형식 (`- TASK-xxx 제목 — 상세`)
    2. extract_task_titles — backlog 형식 (`- **TASK-xxx** [tag] 제목`)
    3. markdown 껍데기(백틱/`**`/`[tag]`) 제거
    4. 같은 ID 중복 시 첫 줄 채택
    5. 동일 제목 → similarity 1.0, suspect=False
    6. 완전히 다른 제목 → suspect=True
    7. 표현만 다듬은 제목 → suspect=False (임계 위)
    8. detect_scope_drift 가 title_drift 를 additive 로 싣는다 (v1 필드 불변)
    9. prompt 생성 — 후보 없으면 빈 string, 있으면 3 분류 요청 포함

Stdlib only.
"""

from __future__ import annotations

#: 이 검사의 입력 표면 (spec `core/test_impact_tiering_spec.md` §2).
#: 게이트 채취 실측에서 뽑아 넓은 쪽으로 올렸다 — 좁으면 meta-watch 가 red 로 잡는다.
WATCHES = (
    "workflow-source/pyproject.toml",
    "workflow-source/workflow_kit/*",
)

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from workflow_kit.common.drift_detection import (  # noqa: E402
    detect_scope_drift,
    detect_title_drift,
    extract_task_titles,
    generate_title_drift_prompt,
    title_similarity,
)

HANDOFF_LINE = (
    "- TASK-2026-08-08-main-020 `[project.scripts]` entry points (CLI 化 A안) — "
    "29 entry point + venv e2e 검증. v1.1.1-beta release.\n"
)
BACKLOG_LINE = (
    "- **TASK-2026-08-08-main-019** [safety] `--force` server-side 이중화 (pre-push hook)\n"
)


def main() -> int:
    failures: list[str] = []

    def check(label: str, cond: bool, detail: str = "") -> None:
        if cond:
            print(f"PASS: {label}")
        else:
            print(f"FAIL: {label} — {detail}")
            failures.append(label)

    # 1) handoff 형식
    titles = extract_task_titles(HANDOFF_LINE)
    check(
        "1) handoff 형식 제목 추출",
        titles.get("TASK-2026-08-08-main-020") == "[project.scripts] entry points (CLI 化 A안)",
        f"{titles}",
    )

    # 2) backlog 형식
    titles = extract_task_titles(BACKLOG_LINE)
    check(
        "2) backlog 형식 제목 추출 ([tag] 제거)",
        titles.get("TASK-2026-08-08-main-019")
        == "--force server-side 이중화 (pre-push hook)",
        f"{titles}",
    )

    # 3) markdown 껍데기 제거 — 표기 차이로 유사도가 깎이면 진짜 교체와 구분이 안 된다
    a = extract_task_titles("- TASK-2026-01-01-main-001 `foo` **bar** baz\n")
    b = extract_task_titles("- TASK-2026-01-01-main-001 foo bar baz\n")
    check(
        "3) 백틱/** 제거 후 동일",
        a["TASK-2026-01-01-main-001"] == b["TASK-2026-01-01-main-001"] == "foo bar baz",
        f"a={a} b={b}",
    )

    # 3b) ID 가 줄 *뒤* 에 오는 형식 (handoff §5). 실측 회귀 —
    #     처음 구현은 ID 뒤만 봐서 `", 본 세션). 4-level enum + Panel 5"` 를 집었다.
    tail_form = extract_task_titles(
        "- **§0.8 #2 in-flight 신뢰도** — ✅ **닫힘** "
        "(TASK-2026-08-08-main-014, 본 세션). 4-level enum + Panel 5 inline badge.\n"
    )
    check(
        "3b) ID 가 뒤에 오는 형식 → 앞쪽 항목명을 집는다",
        tail_form.get("TASK-2026-08-08-main-014") == "§0.8 #2 in-flight 신뢰도",
        f"{tail_form}",
    )

    # 4) 중복 ID → 첫 줄
    dup = extract_task_titles(
        "- TASK-2026-01-01-main-001 진짜 제목 — 상세\n"
        "  본문에서 TASK-2026-01-01-main-001 을 다시 언급한다\n"
    )
    check(
        "4) 같은 ID 중복 시 첫 줄 채택",
        dup["TASK-2026-01-01-main-001"] == "진짜 제목",
        f"{dup}",
    )

    # 5) 동일 제목
    same = detect_title_drift(
        "- TASK-2026-01-01-main-001 registry federation 정공법\n",
        "- TASK-2026-01-01-main-001 registry federation 정공법\n",
    )
    check(
        "5) 동일 제목 → similarity 1.0, suspect 없음",
        same["compared"] == 1
        and same["pairs"][0]["similarity"] == 1.0
        and same["suspect_count"] == 0,
        f"{same}",
    )

    # 6) 완전히 다른 제목
    diff = detect_title_drift(
        "- TASK-2026-01-01-main-001 registry federation 정공법\n",
        "- TASK-2026-01-01-main-001 학습회 발표자료 슬라이드 레이아웃 개편\n",
    )
    check(
        "6) 다른 제목 → suspect=True",
        diff["suspect_count"] == 1 and diff["pairs"][0]["suspect"] is True,
        f"{diff}",
    )

    # 7) 표현만 다듬음
    refined = detect_title_drift(
        "- TASK-2026-01-01-main-001 registry federation 정공법 (다중 호스트)\n",
        "- TASK-2026-01-01-main-001 registry federation 정공법 — 다중 호스트\n",
    )
    check(
        "7) 표현만 다듬음 → suspect=False",
        refined["suspect_count"] == 0,
        f"similarity={refined['pairs'][0]['similarity'] if refined['pairs'] else None}",
    )

    # 8) detect_scope_drift 에 additive — v1 필드가 그대로다
    pre = "## 5. 다음에 할 일\n\n- TASK-2026-01-01-main-001 원래 계획한 일\n"
    post = "## 4. 최근 완료 작업\n\n- TASK-2026-01-01-main-001 전혀 다른 무언가를 했다\n"
    payload = detect_scope_drift(pre_text=pre, post_text=post)
    v1_intact = (
        payload["planned_done"] == ["TASK-2026-01-01-main-001"]
        and payload["planned_undone"] == []
        and payload["unplanned_done"] == []
        and payload["score_band"] == "clean"
    )
    check(
        "8) v1 은 clean 인데 v2 가 후보를 잡는다 (additive)",
        v1_intact and payload["title_drift"]["suspect_count"] == 1,
        f"v1_intact={v1_intact} title_drift={payload.get('title_drift')}",
    )

    # 9) prompt
    empty_prompt = generate_title_drift_prompt(same)
    real_prompt = generate_title_drift_prompt(diff)
    check(
        "9) prompt — 후보 없으면 빈 string, 있으면 3 분류 요청",
        empty_prompt == ""
        and "same_work" in real_prompt
        and "different_work" in real_prompt
        and "advisory" in real_prompt,
        f"empty={empty_prompt!r} real_len={len(real_prompt)}",
    )

    # sanity: title_similarity 범위
    check(
        "sanity) similarity 는 0..1",
        0.0 <= title_similarity("a", "b") <= 1.0 and title_similarity("x", "x") == 1.0,
        "",
    )

    total = 11
    print()
    if failures:
        print(f"{total - len(failures)}/{total} PASS — FAILED: {failures}")
        return 1
    print(f"{total}/{total} PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
