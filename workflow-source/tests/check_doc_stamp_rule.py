#!/usr/bin/env python3
"""`_doc_stamp` 의 스탬프 판정 규칙을 **격리 git 저장소**에서 고정한다 (14 cases — 7~10 · 13 · 14 는 각 함수 docstring).

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
  11) 날짜 뒤 주석 달린 스탬프 → 형식 위반 (case 10 이 건너뛰지 않는다)
  12) 주석만 지운 변경 → 스탬프 전용 (정규화가 '오늘' 을 요구하지 않는다)
  13) 정본의 wiki status 현행/은퇴 분할 == wiki SCHEMA 의 어휘 합집합
  14) 살아있음 판정 경계 — wiki frontmatter · 굵은 헤더 · 스냅샷 · 은퇴 · 숫자 주장
"""

from __future__ import annotations

#: case 10 이 저장소 전수(210건)의 git 이력을 훑는다 — 실측 ~7s.
CHECK_TIMEOUT_S = 150

#: 전역 선언 (spec `core/test_impact_tiering_spec.md` §2).
#:
#: case 1~9 는 임시 저장소로 판정을 고정하므로 표면이 좁다. 그런데 **case 10 이
#: 저장소 전수를 훑는다** — meta-watch 실측(2026-09-22) 접근 1412건. 전수성이 곧
#: 그 case 의 계약이라(릴리스 파이프라인이 워킹 트리 변경분만 보게 된 대신 전수
#: 감시를 게이트가 한 번 맡는다) 좁힐 수 있는 표면이 아니다.
WATCHES_ALL_REASON = (
    "case 10 이 살아있는 문서 전수의 스탬프를 git 이력과 대조한다 — meta-watch "
    "실측(2026-09-22) 접근 1412건. 판정 정본은 "
    "`workflow_kit/common/doc_stamp.py` · 범위 정본은 "
    "`release_pipeline._iter_doc_markdown_files` 다"
)

import os
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

#: 저장소 루트 — case 10 이 실 저장소 전수를 훑는다.
REPO_ROOT = Path(__file__).resolve().parents[2]

from _doc_stamp import check_frontmatter_stamp, stamp_format_violation  # noqa: E402

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


def case_11_annotated_stamp_is_a_format_violation() -> None:
    """**날짜 뒤 주석은 판정 불가다** (TASK-2026-09-29-main-007).

    case 10 의 전수 판정은 날짜 뒤가 줄 끝인 줄만 읽는다. 주석 달린 스탬프를
    형식 위반으로 내지 않으면 그 문서는 판정 없이 통과한다 — 2026-09-29 실측
    살아있는 문서 5건, 그중 3건이 실제로 뒤처져 있었다. 반대쪽(날짜만 · 템플릿
    자리표시자 · 필드 없음)은 위반이 아니어야 한다.
    """
    table = (
        ("주석", "- 최종 수정일: 2026-07-16 (v0.14.0 신규 layout 정합)\n", True),
        ("두 날짜", "- 최종 수정일: 2026-04-30 (원본) / 2026-06-09 (배너)\n", True),
        ("빈 값", "- 최종 수정일:\n", True),
        ("날짜만", "- 최종 수정일: 2026-07-16\n", False),
        ("뒤 공백", "- 최종 수정일: 2026-07-16   \n", False),
        ("자리표시자", "- 최종 수정일: YYYY-MM-DD\n", False),
        ("필드 없음", "- 상태: beta\n", False),
    )
    wrong = [
        label for label, text, want in table
        if (stamp_format_violation(f"# 제목\n\n{text}") is not None) is not want
    ]
    _expect(
        "case_11_annotated_stamp_is_a_format_violation",
        not wrong, True,
        f"형식 판정 {len(table)}행 일치" if not wrong else f"어긋난 행: {wrong}",
    )


def case_12_dropping_annotation_is_stamp_only() -> None:
    """**주석만 지운 변경은 스탬프 전용이다** (main-007).

    case 11 이 주석을 위반으로 만들었으니 고치는 길이 있어야 한다. 주석 달린 줄을
    내용 줄로 세면, 주석을 지우는 정규화가 '지금 내용을 고치는 중' 이 되어 **오늘**
    스탬프를 요구한다 — 사실이 아닌 날짜를 찍어야 green 이 되는 판정이다.
    배치: 30일 전 커밋의 스탬프에 주석이 달렸고, 워킹 트리는 주석만 지웠다.
    """
    with tempfile.TemporaryDirectory(prefix="doc-stamp-annot-") as td:
        repo, doc = _make_repo(Path(td), stamp=f"{_shift(-30)} (옛 주석)", commit_days_ago=30)
        _write_doc(doc, _shift(-30))
        ok, detail = check_frontmatter_stamp(doc, repo_root=repo, actual=_shift(-30))
        _expect("case_12_dropping_annotation_is_stamp_only", ok, True, detail)


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


def case_10_repo_wide_stamps_are_current() -> None:
    """**저장소 전수**: 살아있는 문서의 스탬프가 뒤처지지 않았다 (main-006).

    이 case 가 없으면 전수 감시가 어디에도 없다. 릴리스 파이프라인의
    `doc-headers-update` auto-step 은 **워킹 트리 변경분만** 본다 — 전수를 훑게
    하면 `release --dry-run` 이 10s 예산 밖으로 나가고, 그 예산을 쓰는 검사가
    여럿이라 남의 검사를 깨뜨린다 (2026-09-22 실측). 그래서 비용을 **게이트에
    한 번** 으로 옮겼고, 그 한 번이 여기다.

    범위와 동결 판정은 도구와 **같은 정본**을 읽는다 — 사본을 두면 도구가 고치는
    집합과 게이트가 보는 집합이 갈린다.
    """
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "release_pipeline",
        REPO_ROOT / "workflow-source" / "workflow_kit" / "tools" / "release_pipeline.py",
    )
    assert spec and spec.loader, "release_pipeline 을 못 읽었다"
    rp = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(rp)

    docs = rp._iter_doc_markdown_files("all")
    assert len(docs) > 100, f"범위가 의심스럽다 ({len(docs)}건) — 전수가 아니면 이 case 는 무의미하다"

    sys.path.insert(0, str(REPO_ROOT / "workflow-source"))
    from workflow_kit.common.doc_stamp import dirty_paths

    dirty = dirty_paths(REPO_ROOT)
    stale: list[str] = []
    judged = 0
    for doc in docs:
        text = doc.read_text(encoding="utf-8")
        match = rp.DOC_HEADER_DATE_RE.search(text)
        if match is None:
            # 건너뜀은 통과가 아니다 (main-007) — 필드가 있는데 형식이 틀리면
            # 판정 불가를 loud 로 낸다. 필드 자체가 없는 문서만 조용히 넘긴다.
            violation = stamp_format_violation(text)
            if violation is not None:
                stale.append(f"{doc.relative_to(REPO_ROOT)}: {violation}")
            continue
        judged += 1
        ok, why = check_frontmatter_stamp(
            doc, repo_root=REPO_ROOT, actual=match.group(2), dirty=dirty
        )
        if not ok:
            stale.append(f"{doc.relative_to(REPO_ROOT)}: {why}")
    _expect(
        "case_10_repo_wide_stamps_are_current",
        not stale,
        True,
        f"살아있는 문서 {len(docs)}건 중 스탬프 판정 {judged}건 전부 정합 "
        f"(스탬프 필드 없음·자리표시자 {len(docs) - judged}건)"
        if not stale
        else f"{len(stale)}건 뒤처짐 — {'; '.join(stale[:3])}",
    )


def case_13_wiki_status_partition_matches_schema() -> None:
    """정본의 현행/은퇴 분할이 wiki `SCHEMA.md` 의 어휘와 **같은 집합**인가 (main-010).

    SCHEMA 에 어휘가 늘면(예: `archived`) 분할에 없는 값은 `is_live_marked` 가
    조용히 '동결' 로 읽는다 — 새 값을 단 페이지가 스탬프 감시에서 빠진다. 그래서
    분할을 손 목록으로 두되 SCHEMA 의 `status: a | b | c` 줄에서 파생한 합집합과
    대조한다.
    """
    import re

    sys.path.insert(0, str(REPO_ROOT / "workflow-source"))
    from workflow_kit.common.doc_layers import WIKI_LIVE_STATUSES, WIKI_RETIRED_STATUSES
    from workflow_kit.common.paths import wiki_dir_for_workspace

    schema = (wiki_dir_for_workspace(REPO_ROOT) / "SCHEMA.md").read_text(encoding="utf-8")
    declared: set[str] = set()
    for line in re.findall(r"^status:\s*(.+\|.+)$", schema, re.MULTILINE):
        declared.update(v.strip() for v in line.split("|"))
    assert declared, "SCHEMA 에서 status 어휘 줄을 하나도 못 읽었다 — 파생이 비면 대조는 무의미하다"
    ours = set(WIKI_LIVE_STATUSES) | set(WIKI_RETIRED_STATUSES)
    overlap = WIKI_LIVE_STATUSES & WIKI_RETIRED_STATUSES
    _expect(
        "case_13_wiki_status_partition_matches_schema",
        declared == ours and not overlap,
        True,
        f"SCHEMA {sorted(declared)} == 분할 {sorted(ours)}"
        if declared == ours and not overlap
        else f"SCHEMA 에만 {sorted(declared - ours)} · 정본에만 {sorted(ours - declared)} · 겹침 {sorted(overlap)}",
    )


def case_14_liveness_boundaries() -> None:
    """살아있음 판정의 경계를 한 줄씩 고정한다 (main-010).

    파일을 쓰지 않는다 — 판정은 (경로, 본문) 만 읽으므로 존재하지 않는 경로로 잰다.
    각 행은 '예전 판정이 틀렸던 자리' 또는 '넓히면 틀리게 될 자리' 다.
    """
    sys.path.insert(0, str(REPO_ROOT / "workflow-source"))
    from workflow_kit.common.doc_layers import is_frozen_claim_layer, is_frozen_document

    def fm(status: str) -> str:
        return f"---\ntype: concept\nstatus: {status}\n---\n\n# t\n\n- 최종 수정일: 2026-01-01\n"

    wiki = REPO_ROOT / "ai-workflow" / "wiki" / "concepts" / "_probe_main010.md"
    sample = REPO_ROOT / "docs" / "samples" / "_probe_main010" / "concepts" / "x.md"
    doc = REPO_ROOT / "docs" / "_probe_main010.md"
    note = REPO_ROOT / "workflow-source" / "releases" / "_probe_main010.md"
    bold = "# t\n\n- **상태**: accepted\n- 최종 수정일: 2026-01-01\n"
    rows = [
        # (이름, 판정 함수, 경로, 본문, 기대 동결)
        ("wiki active → 스탬프 살아있음", is_frozen_document, wiki, fm("active"), False),
        ("wiki accepted → 스탬프 살아있음", is_frozen_document, wiki, fm("accepted"), False),
        ("wiki deprecated → 동결", is_frozen_document, wiki, fm("deprecated"), True),
        ("wiki 루트 밖 스냅샷의 status active → 동결", is_frozen_document, sample, fm("active"), True),
        ("본문의 status: 줄은 frontmatter 가 아니다", is_frozen_document, wiki,
         "# t\n\nstatus: active\n", True),
        ("굵은 헤더 - **상태**: → 살아있음", is_frozen_document, doc, bold, False),
        ("wiki active 라도 숫자 주장은 동결", is_frozen_claim_layer, wiki, fm("active"), True),
        ("굵은 헤더 문서의 숫자 주장 → 살아있음", is_frozen_claim_layer, doc, bold, False),
        ("발행된 노트는 굵은 헤더여도 숫자 주장 동결", is_frozen_claim_layer, note, bold, True),
    ]
    wrong = [
        name for name, fn, path, text, want in rows
        if fn(path, text, repo_root=REPO_ROOT) is not want
    ]
    _expect(
        "case_14_liveness_boundaries",
        not wrong,
        True,
        f"경계 {len(rows)}행 일치" if not wrong else f"{len(wrong)}행 불일치 — {wrong}",
    )


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
        case_10_repo_wide_stamps_are_current,
        case_11_annotated_stamp_is_a_format_violation,
        case_12_dropping_annotation_is_stamp_only,
        case_13_wiki_status_partition_matches_schema,
        case_14_liveness_boundaries,
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
