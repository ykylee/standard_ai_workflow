#!/usr/bin/env python3
"""살아있는 문서가 주장하는 smoke 파일 수를 **전수** 대조한다.

TASK-2026-09-21-main-004.

## 왜 필요한가 (2026-09-21 실측)

`check_code_index` 와 `check_installation_usage` 는 이미 기대값을 **디스크에서**
센다 (`len(tests/check_*.py)`) — 파생은 이미 돼 있었다. 결함은 다른 층에 있었다:
그 두 검사는 각자 **자기 문서 하나씩만** 본다. 즉 판정 범위가 *포함 목록* 이었다.

목록 밖은 아무도 안 봐서 조용히 갈라졌다 (81차 실측, 실제 285):

| 문서 | 주장 | 게이트 |
|---|---|---|
| `docs/CODE_INDEX.md` · `docs/INSTALLATION_AND_USAGE.md` | 285 | 있음 |
| `README.md` (2곳) | **162** | 없음 |
| `core/workflow_kit_roadmap.md` (+ 미러) | **52** | 없음 |
| `.omo/plans/llm-wiki-convergence-design.md` | **52** | 없음 |

포함 목록은 사각지대를 못 본다 — 조용한 쪽이 틀린 쪽이었다.

## 무엇을 동결하는가 — 이름이 아니라 문맥으로

전역 금지는 위양성이 지배한다. `releases/Beta-v0.5.10.1.md` 의 '52개' 와
`wiki/topics/aidlc-benchmark-analysis-2026-06-12.md` 의 '52개' 는 **그 시점의
사실** 이므로 고치는 것이 오히려 날조다.

동결 판별에 디렉터리 이름 목록을 쓰지 않는다. 저장소가 **이미 가진 규약** 두 개를 읽는다:

1. 살아있는 문서는 문서 메타데이터 헤더(`- 상태:`)를 단다. 발행된 release note 와
   날짜가 박힌 분석 기록은 그 헤더가 없다.
2. 기록 계층(`ai-workflow/memory/`) 안은 그 시점의 기록이다. 경로는 문자열이 아니라
   `workflow_kit.common.paths.memory_dir_for_workspace` 에서 얻는다.

**1번만으로는 부족했다** (실측). 처음엔 헤더 신호 하나로 8건이 전부 갈린다고 봤는데,
전수로 훑자 `memory/release/v0.5.10/backlog/2026-06-09.md` 가 살아있는 문서로
분류됐다 — 기록 계층의 문서는 **생성기가 헤더를 달아 주기 때문**이다. 손 조사(8건)가
놓친 것을 전수가 잡은 자리이기도 하다. 그래서 2번을 더했다.

두 신호 다 파생이라 새 문서가 생겨도 손볼 목록이 없다.
"""
from __future__ import annotations

#: 전역 선언 (spec `core/test_impact_tiering_spec.md` §2). `WATCHES` 와 동시 선언은
#: 모순이라 meta-watch 가 red 로 잡는다 — 전역이면 근거만 남긴다.
WATCHES_ALL_REASON = (
    "git 이 추적하는 Markdown 전부(실측 1321건)를 훑는다 — 판정 범위가 포함 목록이 "
    "아니라 파생인 것이 이 검사의 요지다. 좁게 선언하면 그 선언이 다시 사각지대가 "
    "되어, 이 검사가 고치려는 결함을 이 검사가 재현한다."
)

#: 이 검사가 강제하는 정본 요구 (spec `core/test_impact_tiering_spec.md` §7).
ENFORCES = ("smoke-count-claims-are-verified-repo-wide",)

import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
TESTS_DIR = REPO_ROOT / "workflow-source" / "tests"

#: 'N개 <smoke 어휘>' 주장. 세 표기를 모두 잡는다 (`162개 smoke` / `285개 스모크` /
#: `285개 check_*.py`). 실측에서 이 셋 외의 표기는 없었다.
CLAIM_RE = re.compile(r"(?P<n>\d{2,4})\s*개\s*(?:`?check_\*\.py`?|smoke|스모크)")

#: 살아있는 문서의 표지 — 저장소의 문서 메타데이터 헤더. 목록이 아니라 규약이다.
LIVE_MARKER_RE = re.compile(r"^-\s*상태:", re.MULTILINE)


def memory_layer_root() -> Path:
    """기록 계층(`ai-workflow/memory/`)의 경로를 **kit 의 경로 해석기에서** 얻는다.

    여기를 문자열로 박으면 경로 규약의 약한 사본이 된다. 이 계층이 기록이라는 것은
    내 판단이 아니라 저장소의 선언이다 — CLAUDE.md: "`ai-workflow/` 는 세션 복원과
    workflow 상태 관리용 메타 레이어다 ... 프로젝트 문서를 탐색할 때는 이 경로를
    기본 탐색 범위에 넣지 말고".

    왜 필요한가 (2026-09-21 실측): 헤더 신호만으로는 부족했다. 기록 계층의
    `memory/release/v0.5.10/backlog/2026-06-09.md` 는 **생성기가 헤더를 달아 주므로**
    살아있는 문서로 잘못 분류됐다. 그 문서의 '52개' 는 v0.5.10 시점의 사실이다.
    """
    sys.path.insert(0, str(REPO_ROOT / "workflow-source"))
    from workflow_kit.common.paths import memory_dir_for_workspace

    return memory_dir_for_workspace(REPO_ROOT)


def is_record_layer(path: Path) -> bool:
    """기록 계층 안인가 — 그 안의 주장은 그 시점의 사실이다."""
    try:
        path.relative_to(memory_layer_root())
        return True
    except ValueError:
        return False


_failures: list[str] = []
_passes: list[str] = []


def _record(case: str, ok: bool, detail: str = "") -> None:
    (_passes if ok else _failures).append(case if ok else f"{case}: {detail}")
    print(f"  {case}: {'PASS' if ok else 'FAIL'}{(' — ' + detail) if detail else ''}")


def actual_smoke_count() -> int:
    """디스크가 정본이다. 문서를 읽어 기대값으로 삼으면 동어반복이 된다
    (`tests/_doc_stamp.py` 가 같은 이유로 git 에서 판정한다)."""
    return len(list(TESTS_DIR.glob("check_*.py")))


def tracked_markdown() -> list[Path]:
    """git 이 추적하는 `*.md` 전부. 워킹 트리 쓰레기를 판정 대상에 넣지 않는다."""
    out = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "ls-files", "*.md"],
        capture_output=True, text=True, check=True,
    ).stdout.splitlines()
    return [REPO_ROOT / line for line in out if line.strip()]


def classify() -> tuple[list[tuple[Path, int]], list[tuple[Path, int]]]:
    """(살아있는 문서의 주장, 동결 문서의 주장)."""
    live: list[tuple[Path, int]] = []
    frozen: list[tuple[Path, int]] = []
    for path in tracked_markdown():
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        claims = [int(m.group("n")) for m in CLAIM_RE.finditer(text)]
        if not claims:
            continue
        is_live = LIVE_MARKER_RE.search(text) is not None and not is_record_layer(path)
        bucket = live if is_live else frozen
        bucket.extend((path, n) for n in claims)
    return live, frozen


def case_1_live_claims_match_disk() -> None:
    """살아있는 문서의 모든 주장이 실제 파일 수와 일치한다."""
    actual = actual_smoke_count()
    live, _ = classify()
    bad = [f"{p.relative_to(REPO_ROOT)}: {n}" for p, n in live if n != actual]
    _record(
        "case 1 (살아있는 문서의 주장 == 디스크)",
        not bad,
        f"실제 {actual} 인데 — {', '.join(bad)}" if bad else f"주장 {len(live)}건 전부 {actual} 정합",
    )


def case_2_scope_is_not_empty() -> None:
    """훑은 문서가 0 이면 이 검사는 아무것도 보장하지 않는다.

    git 이 없거나 glob 이 빗나가면 case 1 은 빈 집합을 검사하며 **통과한다** —
    검사는 깨지지 않고 무력화된다. 범위 자체를 판정에 넣는다.
    """
    docs = tracked_markdown()
    actual = actual_smoke_count()
    ok = len(docs) > 50 and actual > 0
    _record(
        "case 2 (판정 범위가 비어 있지 않다)",
        ok,
        f"md {len(docs)}건 · check_*.py {actual}개"
        if ok
        else f"범위가 의심스럽다: md {len(docs)}건 / check_*.py {actual}개",
    )


def case_3_frozen_is_reported_not_silent() -> None:
    """동결로 건너뛴 주장을 **보고**한다.

    조용히 건너뛰면 '봤는데 맞았다' 와 '아예 안 봤다' 가 같은 모양이 된다.
    건너뛴 것이 실제로 동결 문맥인지 사람이 확인할 수 있게 목록을 찍는다.
    """
    _, frozen = classify()
    for path, n in frozen:
        why = "기록 계층" if is_record_layer(path) else "메타데이터 헤더 없음"
        print(f"    [frozen] {path.relative_to(REPO_ROOT)}: {n} — {why}(그 시점 기록)")
    # 동결이 전부를 먹으면 case 1 이 빈 집합을 본다.
    live, _ = classify()
    _record(
        "case 3 (동결 목록 보고 + 살아있는 주장 존재)",
        bool(live),
        f"동결 {len(frozen)}건 / 살아있는 {len(live)}건"
        if live
        else "살아있는 주장이 0 — case 1 이 아무것도 검사하지 않는다",
    )


def main() -> int:
    print("=== smoke 수 주장 전수 대조 (TASK-2026-09-21-main-004) ===")
    for fn in (case_1_live_claims_match_disk, case_2_scope_is_not_empty, case_3_frozen_is_reported_not_silent):
        fn()
    total = len(_passes) + len(_failures)
    print(f"\n{len(_passes)}/{total} passed")
    if _failures:
        for f in _failures:
            print(f"  ✗ {f}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
