#!/usr/bin/env python3
"""`_doc_stamp` 의 스탬프 판정 규칙을 **격리 git 저장소**에서 고정한다 (6 cases).

## 왜 이 검사가 있나 (TASK-2026-09-01-main-002)

`check_code_index_v0_15_17` · `check_document_index_v0_15_16` 의 기대 스탬프가
리터럴에서 git 파생으로 바뀌었다. 그 판정에는 **틀리기 쉬운 자리가 둘** 있고,
2026-09-01 에 두 자리를 다 한 번씩 틀렸다:

1. **타임존.** `--date=format-local:` 은 실행 환경의 TZ 를 쓴다. UTC 를 자칭하며
   로컬(KST) 날짜를 읽어, 커밋 `236a6aa9`(2026-09-01T00:12+09:00 = 08-31 UTC)를
   하루 뒤로 보고 없는 어긋남을 만들었다.
2. **유예의 적용 범위.** 커밋된 경우의 자정 경계를 흡수하려고 둔 1일 유예를
   워킹 트리가 더러운 경우에도 똑같이 적용했더니, "어제 스탬프를 단 채 오늘
   내용을 고치는 것" 이 통과했다 — 이 판정이 잡으려는 바로 그 경우다.

둘 다 **red 가 아니라 green** 으로 새는 결함이라 본 저장소 검사로는 안 보인다
(실제 문서의 스탬프가 우연히 맞으면 그만이다). 그래서 날짜를 **우리가 정하는**
격리 저장소에서 규칙 자체를 잰다.

6 cases:
  1) 커밋일과 같은 스탬프 → PASS
  2) 커밋일보다 **하루 앞선** 스탬프 → PASS (자정 경계 유예)
  3) 커밋일보다 **한참 뒤처진** 스탬프 → FAIL
  4) 워킹 트리가 더러우면 유예 0 — 어제 스탬프 → FAIL
  5) 워킹 트리가 더러워도 오늘 스탬프면 → PASS
  6) git 이 모르는 파일 → 판정 불가로 **loud FAIL** (조용한 통과 금지)
"""

from __future__ import annotations

#: 이 검사의 입력 표면 (spec `core/test_impact_tiering_spec.md` §2).
WATCHES = (
    # 스탬프 판정 정본 (TASK-2026-09-22-main-002 에서 kit 으로 승격).
    "workflow-source/workflow_kit/common/doc_stamp.py",
    "workflow-source/tests/_doc_stamp.py",
)

import os
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _doc_stamp import check_frontmatter_stamp  # noqa: E402

FAILURES: list[str] = []


def _shift(days: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(days=days)).strftime("%Y-%m-%d")


def _git(repo: Path, *args: str, env_extra: dict[str, str] | None = None) -> None:
    env = {**os.environ, **(env_extra or {})}
    completed = subprocess.run(
        ["git", *args], cwd=str(repo), capture_output=True, text=True, env=env
    )
    if completed.returncode != 0:
        raise AssertionError(f"git {' '.join(args)} 실패: {completed.stderr.strip()}")


def _write_doc(path: Path, stamp: str, body: str = "본문") -> None:
    path.write_text(f"# 제목\n\n- 최종 수정일: {stamp}\n\n{body}\n", encoding="utf-8")


def _make_repo(tmp: Path, *, stamp: str, commit_days_ago: int) -> tuple[Path, Path]:
    """`docs/X.md` 하나를 담은 저장소. 커밋 시각을 UTC 로 못박는다."""
    repo = tmp / "repo"
    (repo / "docs").mkdir(parents=True)
    _git(repo.parent, "init", "-q", str(repo))
    _git(repo, "config", "user.email", "check@example.invalid")
    _git(repo, "config", "user.name", "check")

    doc = repo / "docs" / "X.md"
    _write_doc(doc, stamp)
    _git(repo, "add", "docs/X.md")
    # 커밋 시각을 **UTC 자정 직전**으로 고정한다. 정오로 두면 어느 TZ 에서 읽어도
    # 같은 날짜라 타임존 결함이 통과한다 — 경계에 세워야 case_2 가 그것을 문다
    # (KST=+9 에서 이 시각은 이튿날 08:30 이다).
    when = f"{_shift(-commit_days_ago)}T23:30:00+00:00"
    _git(
        repo,
        "commit",
        "-q",
        "-m",
        "doc",
        env_extra={"GIT_AUTHOR_DATE": when, "GIT_COMMITTER_DATE": when},
    )
    return repo, doc


def _expect(name: str, ok: bool, want_ok: bool, detail: str) -> None:
    if ok is want_ok:
        print(f"  PASS  {name} — {detail}")
        return
    FAILURES.append(name)
    print(f"  FAIL  {name} — ok={ok} (기대 {want_ok}): {detail}")


def _run_case(name: str, *, stamp: str, commit_days_ago: int, dirty: bool, want_ok: bool) -> None:
    with tempfile.TemporaryDirectory(prefix="doc-stamp-") as td:
        repo, doc = _make_repo(Path(td), stamp=stamp, commit_days_ago=commit_days_ago)
        if dirty:
            _write_doc(doc, stamp, body="본문 — 내용을 고쳤다")
        ok, detail = check_frontmatter_stamp(doc, repo_root=repo, actual=stamp)
        _expect(name, ok, want_ok, detail)


def case_1_stamp_equals_commit_date() -> None:
    _run_case(
        "case_1_stamp_equals_commit_date",
        stamp=_shift(-3), commit_days_ago=3, dirty=False, want_ok=True,
    )


def case_2_stamp_one_day_before_commit() -> None:
    """스탬프를 찍은 날과 커밋이 착지한 날이 UTC 자정을 사이에 두고 갈린 경우."""
    _run_case(
        "case_2_stamp_one_day_before_commit",
        stamp=_shift(-4), commit_days_ago=3, dirty=False, want_ok=True,
    )


def case_3_stamp_far_behind_commit() -> None:
    _run_case(
        "case_3_stamp_far_behind_commit",
        stamp=_shift(-30), commit_days_ago=3, dirty=False, want_ok=False,
    )


def case_4_dirty_tree_has_no_grace() -> None:
    """더러운 트리에 어제 스탬프 — 유예를 여기까지 주면 이 검사는 무의미해진다."""
    _run_case(
        "case_4_dirty_tree_has_no_grace",
        stamp=_shift(-1), commit_days_ago=1, dirty=True, want_ok=False,
    )


def case_5_dirty_tree_with_today_stamp() -> None:
    _run_case(
        "case_5_dirty_tree_with_today_stamp",
        stamp=_shift(0), commit_days_ago=1, dirty=True, want_ok=True,
    )


def case_7_stamp_only_commit_is_not_a_content_change() -> None:
    """**스탬프만 바꾼 커밋은 내용 변경이 아니다** (TASK-2026-09-22-main-004).

    이 구분이 없으면 이 판정은 이름과 docstring 이 말하는 '마지막 **내용** 변경'
    이 아니라 '마지막 커밋' 을 잰다. 릴리스의 `doc-headers-update` 가 스탬프만
    바꾼 커밋을 만들고, 그것이 기준선을 앞으로 밀어 **스탬프가 내용보다 최대
    126일 앞선 문서 97개**가 통과하고 있었다 (2026-09-22 전수 실측).

    배치: 내용은 30일 전에 고쳤고, 그 뒤 스탬프만 바꾼 커밋이 하나 있다.
    옛 판정은 그 커밋을 기준으로 삼아 **오래된 스탬프를 red 로** 만들고,
    새 판정은 내용 변경일을 기준으로 삼아 green 이다 — 두 답이 갈린다.
    """
    with tempfile.TemporaryDirectory(prefix="doc-stamp-only-") as td:
        repo, doc = _make_repo(Path(td), stamp=_shift(-30), commit_days_ago=30)
        # 스탬프만 바꾸는 커밋 (내용은 그대로).
        _write_doc(doc, _shift(-2))
        _git(repo, "add", "docs/X.md")
        when = f"{_shift(-2)}T23:30:00+00:00"
        _git(repo, "commit", "-q", "-m", "stamp only",
             env_extra={"GIT_AUTHOR_DATE": when, "GIT_COMMITTER_DATE": when})

        # 스탬프를 **내용 변경일** 로 되돌린다 — 소급 교정이 하는 일이다.
        _write_doc(doc, _shift(-30))
        _git(repo, "add", "docs/X.md")
        when = f"{_shift(-1)}T23:30:00+00:00"
        _git(repo, "commit", "-q", "-m", "backfill stamp",
             env_extra={"GIT_AUTHOR_DATE": when, "GIT_COMMITTER_DATE": when})

        ok, detail = check_frontmatter_stamp(doc, repo_root=repo, actual=_shift(-30))
        _expect("case_7_stamp_only_commit_is_not_a_content_change", ok, True, detail)


def case_8_stamp_only_worktree_change_keeps_history_baseline() -> None:
    """**스탬프만 고친 미커밋 변경도 내용 변경이 아니다** (main-004).

    더러운 트리 분기는 유예 0 으로 '오늘' 을 요구한다 — 지금 고치는 중이니
    맞는 규율이다. 그런데 그 분기가 *무엇을* 고치는 중인지 보지 않으면,
    **스탬프를 교정하는 행위 자체가 위반**이 된다. 2026-09-22 소급 교정에서
    `check_document_index` 가 정확히 그 이유로 red 였다.

    배치: 내용은 30일 전에 고쳤고, 워킹 트리에 스탬프 줄만 바뀐 상태다.
    내용 변경일 기준이면 green 이어야 한다.
    """
    with tempfile.TemporaryDirectory(prefix="doc-stamp-wt-") as td:
        repo, doc = _make_repo(Path(td), stamp=_shift(-2), commit_days_ago=30)
        _write_doc(doc, _shift(-30))  # 스탬프만 되돌린다 (커밋하지 않는다)
        ok, detail = check_frontmatter_stamp(doc, repo_root=repo, actual=_shift(-30))
        _expect(
            "case_8_stamp_only_worktree_change_keeps_history_baseline",
            ok, True, detail,
        )


def case_9_dirty_content_still_demands_today() -> None:
    """위 둘이 유예 0 규율을 **풀지 않았는지** 반대쪽에서 확인한다.

    case 8 과 같은 배치인데 워킹 트리 변경에 **본문**이 섞여 있다. 그러면
    '지금 고치는 중' 이므로 오늘 스탬프를 요구해야 한다 — 안 그러면 스탬프
    전용 판정이 더러운 트리 규율 전체를 무력화한 것이다.
    """
    with tempfile.TemporaryDirectory(prefix="doc-stamp-wt2-") as td:
        repo, doc = _make_repo(Path(td), stamp=_shift(-2), commit_days_ago=30)
        _write_doc(doc, _shift(-30), body="본문 — 내용도 같이 고쳤다")
        ok, detail = check_frontmatter_stamp(doc, repo_root=repo, actual=_shift(-30))
        _expect("case_9_dirty_content_still_demands_today", ok, False, detail)


def case_6_untracked_is_loud_failure() -> None:
    with tempfile.TemporaryDirectory(prefix="doc-stamp-") as td:
        repo, _doc = _make_repo(Path(td), stamp=_shift(0), commit_days_ago=0)
        stray = repo / "docs" / "Y.md"
        _write_doc(stray, _shift(0))
        _git(repo, "add", "-A")
        _git(repo, "reset", "-q", "--", "docs/Y.md")
        _git(repo, "rm", "-q", "--cached", "--ignore-unmatch", "docs/Y.md")
        # 미추적 + 미커밋 → git status 가 잡으므로 dirty 로 읽힌다. 이력 자체가 없는
        # 상태를 만들려면 status 를 통과해야 하므로 .gitignore 로 감춘다.
        (repo / ".gitignore").write_text("docs/Y.md\n", encoding="utf-8")
        _git(repo, "add", ".gitignore")
        _git(repo, "commit", "-q", "-m", "ignore")
        ok, detail = check_frontmatter_stamp(stray, repo_root=repo, actual=_shift(0))
        _expect("case_6_untracked_is_loud_failure", ok, False, detail)


def main() -> int:
    print("=== 문서 스탬프 판정 규칙 (_doc_stamp) ===")
    cases = (
        case_1_stamp_equals_commit_date,
        case_2_stamp_one_day_before_commit,
        case_3_stamp_far_behind_commit,
        case_4_dirty_tree_has_no_grace,
        case_5_dirty_tree_with_today_stamp,
        case_6_untracked_is_loud_failure,
        case_7_stamp_only_commit_is_not_a_content_change,
        case_8_stamp_only_worktree_change_keeps_history_baseline,
        case_9_dirty_content_still_demands_today,
    )
    for fn in cases:
        try:
            fn()
        except Exception as exc:  # noqa: BLE001
            FAILURES.append(fn.__name__)
            print(f"  FAIL  {fn.__name__} — 예외 {type(exc).__name__}: {exc}")
    if FAILURES:
        print(f"\n{len(FAILURES)} fail: {FAILURES}")
        return 1
    # 합계는 **등록된 case 수에서 파생**한다 (TASK-2026-09-22-main-004).
    # 리터럴 `6/6` 이었을 때 case 를 9개로 늘려도 요약은 `6/6` 을 찍었다 —
    # 새 case 가 돌았는지 요약만 보고는 알 수 없었다 (같은 세션에
    # `check_drift_prevention_helpers` 에서도 같은 자리를 고쳤다).
    print(f"\n{len(cases)}/{len(cases)} PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
