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
    for fn in (
        case_1_stamp_equals_commit_date,
        case_2_stamp_one_day_before_commit,
        case_3_stamp_far_behind_commit,
        case_4_dirty_tree_has_no_grace,
        case_5_dirty_tree_with_today_stamp,
        case_6_untracked_is_loud_failure,
    ):
        try:
            fn()
        except Exception as exc:  # noqa: BLE001
            FAILURES.append(fn.__name__)
            print(f"  FAIL  {fn.__name__} — 예외 {type(exc).__name__}: {exc}")
    if FAILURES:
        print(f"\n{len(FAILURES)} fail: {FAILURES}")
        return 1
    print("\n6/6 PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
