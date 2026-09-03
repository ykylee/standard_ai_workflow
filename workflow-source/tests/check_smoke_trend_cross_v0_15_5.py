#!/usr/bin/env python3
"""Smoke test — Panel 4 cross-validation (v0.15.5+).

Panel 4 의 두 metric (`cumulative_total` / `smoke_files_count`) cross-check +
sanity + recent releases 정합 검증.

Panel 4 metrics 의미 (v0.13.0+):
  - cumulative_total / cumulative_pass: 가장 최근 release note 의 누적 smoke
    total / pass (release note 본문 `누적 smoke **N+ PASS**` / `**N/N PASS**` parse)
  - smoke_files_count: workflow-source/tests/check_*.py 의 file 갯수 (실제 data 기반)
  - cumulative_pass_rate: pass / total (0.0 ~ 1.0)
  - recent_releases: [{version, pass, total, release_note_path}, ...] (newest first)

6 cases:
  1) sanity: cumulative_total > 0, smoke_files_count > 0, cumulative_pass <= total,
     0.0 <= cumulative_pass_rate <= 1.0
  2) 최신 release note 의 누적 수치가 **그 노트의 시점** 과 정합한가.
     발행된 노트(태그가 있다)는 *그 태그 시점의* check 파일 수와, 아직 발행되지
     않은 노트는 *현재* 파일 수와 대조한다 (v1.9.2 — case 2 주석 참조)
  3) recent releases consistency: recent_releases[0] (가장 최근) 의 pass/total
     == panel top 의 cumulative_pass / cumulative_total
  4) delta vs v0.15.0 baseline: smoke_files_count >= v0.15.0 baseline (179).
     v0.15.0 → v0.15.4 까지 3 신규 smoke 추가 → expected 182 (179 + 3)
  5) pass_rate = 1.0: v0.15.4 시점 모든 smoke PASS 정합 (회귀 ❌)
  6) 최신 release note 가 누적 수치 줄을 **실제로 들고 있는가** — 표기가 빠지면
     파서가 그 노트를 건너뛰고 *이전* 노트를 최신으로 읽는다 (v1.1.0 / v1.1.1
     회귀의 모양). case 2 가 그 상황에서 엉뚱한 노트를 재지 않도록 여기서 막는다.
"""

from __future__ import annotations

import json
import sys
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"

if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))


def _collect_panel_4() -> dict:
    """workflow_kit_cli dashboard --format=json subprocess 호출 → Panel 4 dict 반환."""
    proc = subprocess.run(
        [sys.executable, "-m", "workflow_kit.workflow_kit_cli",
         "--command=dashboard", "--format=json"],
        cwd=str(REPO_ROOT),
        env={"PYTHONPATH": str(SOURCE_ROOT), "PATH": __import__("os").environ.get("PATH", "")},
        capture_output=True, text=True, timeout=60,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"dashboard --format=json failed: {proc.stderr[:300]}")
    return json.loads(proc.stdout)["panels"]["smoke_trend"]


def _actual_smoke_files_count() -> int:
    """workflow-source/tests/check_*.py 의 실제 file 갯수 (cross-check source)."""
    tests_dir = SOURCE_ROOT / "tests"
    return sum(1 for _ in tests_dir.glob("check_*.py"))


def _git(args: list[str]) -> tuple[int, str]:
    proc = subprocess.run(
        ["git", *args], cwd=str(REPO_ROOT),
        capture_output=True, text=True, timeout=20, check=False,
    )
    return proc.returncode, proc.stdout.strip()


def _is_git_repo() -> bool:
    return _git(["rev-parse", "--git-dir"])[0] == 0


def _release_tag_for(note_stem: str) -> str | None:
    """`'Beta-v1.9.1'` → 실재하는 태그 이름. 아직 발행 전이면 ``None``.

    구 포맷(`v0.9.0-beta`)도 함께 찾는다 — v1.2.1 부터 접미사가 없다.
    """
    version = note_stem[len("Beta-"):] if note_stem.startswith("Beta-") else note_stem
    for candidate in (version, f"{version}-beta"):
        if _git(["rev-parse", "--verify", "--quiet", f"refs/tags/{candidate}"])[0] == 0:
            return candidate
    return None


def _smoke_files_at_tag(tag: str) -> int | None:
    """그 태그 시점의 `workflow-source/tests/check_*.py` 갯수. 못 재면 ``None``."""
    rc, out = _git(["ls-tree", "-r", "--name-only", tag, "--", "workflow-source/tests"])
    if rc != 0:
        return None
    return sum(
        1 for line in out.splitlines()
        if line.endswith(".py") and Path(line).name.startswith("check_")
    )


def _newest_release_note_stem() -> str | None:
    """`releases/Beta-v*.md` 중 semver 최신 파일의 stem (본문 파싱과 무관)."""
    releases_dir = SOURCE_ROOT / "releases"
    if not releases_dir.is_dir():
        return None
    def _key(path: Path) -> tuple[int, ...]:
        digits = path.stem[len("Beta-v"):] if path.stem.startswith("Beta-v") else "0"
        parts: list[int] = []
        for chunk in digits.split("-")[0].split("."):
            parts.append(int(chunk) if chunk.isdigit() else 0)
        return tuple(parts)
    notes = sorted(releases_dir.glob("Beta-v*.md"), key=_key)
    return notes[-1].stem if notes else None


def case_1_sanity() -> bool:
    """1) sanity: cumulative_total > 0, smoke_files_count > 0, pass <= total, rate 0~1."""
    p4 = _collect_panel_4()
    cum_total = int(p4.get("cumulative_total", 0))
    cum_pass = int(p4.get("cumulative_pass", 0))
    smoke_files = int(p4.get("smoke_files_count", 0))
    rate = float(p4.get("cumulative_pass_rate", 0.0))
    if cum_total <= 0:
        print(f"  FAIL: cumulative_total={cum_total} (expected > 0)")
        return False
    if smoke_files <= 0:
        print(f"  FAIL: smoke_files_count={smoke_files} (expected > 0)")
        return False
    if cum_pass > cum_total:
        print(f"  FAIL: cum_pass={cum_pass} > cum_total={cum_total}")
        return False
    if not (0.0 <= rate <= 1.0):
        print(f"  FAIL: rate={rate} (expected 0.0 ~ 1.0)")
        return False
    print(f"  [info] cum_total={cum_total}, cum_pass={cum_pass}, smoke_files={smoke_files}, rate={rate}")
    return True


def case_2_note_matches_its_own_moment() -> bool:
    """2) 최신 release note 의 누적 수치가 **그 노트의 시점** 과 정합한가.

    ## 왜 기준이 '현재 파일 수' 가 아닌가 (v1.9.2, TASK-2026-09-03-main-003)

    이 case 는 오래 `cumulative_total >= smoke_files_count` 를 요구했다. 그러면
    사이클 중에 검사가 하나라도 늘 때마다 **이미 발행된 노트** 를 고쳐야 red 가
    꺼진다. 그리고 다음 발행 준비에서 그 노트를 발행 시점 값으로 되돌린다 —
    `Beta-v1.9.0.md` 의 `279 → 280 → 279` 왕복이 git 이력에 그대로 남아 있고,
    71·72·73·74차 **네 사이클 연속** 같은 자리를 손으로 오갔다.

    뿌리는 판정 기준이 아니라 **분모** 였다. 릴리스 노트의 수치는 *그 릴리스가
    나가던 순간의 주장* 이다. 발행된 뒤에도 그것을 현재와 맞추라고 요구하면
    역사 기록이 가변이 되고, 그 편집은 "전량을 돌렸다" 는 주장을 돌리지 않은
    사람이 쓰게 만든다 — 검사가 거짓 주장을 유도한다.

    그래서 노트마다 자기 시점과 대조한다:

    - **발행된 노트** (같은 이름의 태그가 있다) → 그 태그 시점의 `check_*.py`
      갯수와 **정확히** 같아야 한다. 값이 얼어붙으므로 왕복이 사라지고,
      과거 노트를 몰래 고치면 오히려 red 가 난다.
    - **아직 발행 전인 노트** (태그 없음 — 발행 준비 커밋과 태그 push 사이) →
      **현재** 갯수와 같아야 한다. 발행 게이트의
      `verify_release_note_smoke_count` 와 같은 규칙이라, 그 창에서도 빈틈이 없다.

    v1.1.0 / v1.1.1 처럼 수치 표기를 통째로 빠뜨리는 회귀는 case 6 이 막는다 —
    그때는 파서가 *이전* 노트를 최신으로 읽어 이 case 가 엉뚱한 것을 잰다.
    """
    if not _is_git_repo():
        print("  FAIL: git 저장소가 아니라 릴리스 시점을 잴 수 없다 "
              "(모름을 통과로 세지 않는다 — `_doc_stamp.py` 와 같은 규약)")
        return False

    p4 = _collect_panel_4()
    recent = p4.get("recent_releases", [])
    if not recent:
        print("  FAIL: release note 에서 누적 수치를 하나도 못 읽었다")
        return False
    stem = str(recent[0].get("version", ""))
    claimed = int(p4.get("cumulative_total", 0))

    tag = _release_tag_for(stem)
    if tag is None:
        expected = _actual_smoke_files_count()
        basis = f"{stem} 은 아직 발행 전(태그 없음) — 현재 파일 수"
    else:
        at_tag = _smoke_files_at_tag(tag)
        if at_tag is None:
            print(f"  FAIL: 태그 {tag} 의 트리를 읽지 못했다 (얕은 clone 인가)")
            return False
        expected = at_tag
        basis = f"태그 {tag} 시점의 파일 수"

    if claimed != expected:
        print(f"  FAIL: {stem} 의 누적 수치 {claimed} != {expected} ({basis})")
        if tag is None:
            print(f"        전량 PASS 를 확인한 뒤 노트를 {expected}/{expected} 로 적을 것.")
        else:
            print(f"        발행된 노트의 수치는 그 시점의 사실이다 — 현재 값에 맞추지 "
                  f"말고 {expected} 로 되돌릴 것.")
        return False
    print(f"  [info] {stem}: 누적 {claimed} == {expected} ({basis}); "
          f"현재 파일 수 {_actual_smoke_files_count()}")
    return True


def case_3_recent_releases_consistency() -> bool:
    """3) recent_releases[0] (가장 최근) 의 pass/total == panel top 의 cumulative."""
    p4 = _collect_panel_4()
    recent = p4.get("recent_releases", [])
    if not recent:
        print(f"  FAIL: recent_releases 부재")
        return False
    latest = recent[0]
    if int(latest.get("pass", 0)) != int(p4.get("cumulative_pass", -1)):
        print(f"  FAIL: recent[0].pass={latest.get('pass')} != cum_pass={p4.get('cumulative_pass')}")
        return False
    if int(latest.get("total", 0)) != int(p4.get("cumulative_total", -1)):
        print(f"  FAIL: recent[0].total={latest.get('total')} != cum_total={p4.get('cumulative_total')}")
        return False
    print(f"  [info] recent[0] = {latest.get('version')}: pass={latest.get('pass')}, total={latest.get('total')}")
    return True


def case_4_delta_vs_v0_15_0_baseline() -> bool:
    """4) delta vs v0.15.0 baseline: smoke_files_count >= 179 + 신규 smoke count."""
    p4 = _collect_panel_4()
    actual_count = int(p4.get("smoke_files_count", 0))
    file_count_actual = _actual_smoke_files_count()
    # v0.15.0 시점 baseline: 179 (cumulative_total=260 release note 기준).
    # v0.15.1~v0.15.4 까지 추가된 신규 smoke:
    #   - check_refresh_maturity_v0_15_2.py (v0.15.2)
    #   - check_refresh_maturity_v0_15_3.py (v0.15.3)
    #   - check_deprecation_3rd_cycle_v0_15_4.py (v0.15.4)
    # = 3 file 추가 → expected 182
    V0_15_0_BASELINE = 179
    NEW_SMOKE_V0_15_1_TO_V0_15_4 = 3
    expected_min = V0_15_0_BASELINE + NEW_SMOKE_V0_15_1_TO_V0_15_4
    if actual_count < expected_min:
        print(f"  FAIL: smoke_files_count={actual_count} < expected_min={expected_min} (v0.15.0 baseline {V0_15_0_BASELINE} + {NEW_SMOKE_V0_15_1_TO_V0_15_4} 신규)")
        return False
    # panel smoke_files_count == actual file count (file-based, real-time)
    if actual_count != file_count_actual:
        print(f"  FAIL: panel smoke_files_count={actual_count} != actual file count={file_count_actual}")
        return False
    print(f"  [info] smoke_files_count={actual_count} (expected ≥ {expected_min}), actual file count={file_count_actual}")
    return True


def case_5_pass_rate_full() -> bool:
    """5) pass_rate = 1.0: v0.15.4 시점 모든 smoke PASS 정합."""
    p4 = _collect_panel_4()
    # **실효 지표**로 판정한다. 본 case 자신과 quality_dashboard Panel 4 도 전량에
    # 포함되므로, 원 수치(cumulative_*)로 rate=1.0 을 요구하면 "둘이 green 이어야
    # green 이 된다"는 순환이 된다. release note 에 제외 대상을 명시하고 그 실효
    # 지표를 보는 것이 자기참조를 제거하는 정공법이다.
    rate = float(p4.get("effective_pass_rate", 0.0))
    if rate != 1.0:
        print(f"  FAIL: effective_pass_rate={rate} (expected 1.0 — 자기참조 게이트 제외 후 full pass)")
        return False
    eff_total = int(p4.get("effective_total", 0))
    eff_pass = int(p4.get("effective_pass", 0))
    if eff_pass != eff_total:
        print(f"  FAIL: eff_pass={eff_pass} != eff_total={eff_total}")
        return False
    excluded = int(p4.get("self_referential_excluded", 0))
    print(f"  [info] full pass 정합: {eff_pass}/{eff_total} = 1.0 "
          f"(원 수치 {p4.get('cumulative_pass')}/{p4.get('cumulative_total')}, 자기참조 {excluded} 제외)")
    return True


def case_6_newest_note_carries_the_line() -> bool:
    """6) 가장 최신 release note 가 누적 수치 줄을 실제로 들고 있는가.

    파서(`collect_smoke_trend`)는 수치 줄이 없는 노트를 **조용히 건너뛴다**.
    그래서 v1.1.0 / v1.1.1 에서 표기가 빠졌을 때 dashboard 는 옛 노트(v1.0.0 의
    234)를 최신으로 읽었고, 그 상태로 검사가 계속 red 였는데 원인은 엉뚱한
    자리에서 찾아졌다. 여기서 **파일 기준 최신** 과 **파싱 기준 최신** 이 같은지
    직접 대조한다 — 다르면 그 사이의 노트가 수치 줄을 빠뜨린 것이다.
    """
    newest = _newest_release_note_stem()
    if newest is None:
        print("  FAIL: workflow-source/releases/Beta-v*.md 가 없다")
        return False
    p4 = _collect_panel_4()
    recent = p4.get("recent_releases", [])
    if not recent:
        print("  FAIL: release note 에서 누적 수치를 하나도 못 읽었다")
        return False
    parsed_newest = str(recent[0].get("version", ""))
    if parsed_newest != newest:
        print(f"  FAIL: 파일 기준 최신 노트는 {newest} 인데 파싱된 최신은 "
              f"{parsed_newest} 다 — {newest} 에 `누적 smoke **N/N PASS**` 줄이 빠졌다.")
        return False
    print(f"  [info] 최신 노트 {newest} 가 누적 수치 줄을 들고 있다")
    return True


def main() -> int:
    cases = [
        ("case_1_sanity", case_1_sanity),
        ("case_2_note_matches_its_own_moment", case_2_note_matches_its_own_moment),
        ("case_3_recent_releases_consistency", case_3_recent_releases_consistency),
        ("case_4_delta_vs_v0_15_0_baseline", case_4_delta_vs_v0_15_0_baseline),
        ("case_5_pass_rate_full", case_5_pass_rate_full),
        ("case_6_newest_note_carries_the_line", case_6_newest_note_carries_the_line),
    ]
    results: list[tuple[str, bool]] = []
    for name, fn in cases:
        results.append((name, fn()))
    passed = sum(1 for _, ok in results if ok)
    for name, ok in results:
        marker = "PASS" if ok else "FAIL"
        print(f"  [{marker}] {name}")
    print(f"\n=== {passed}/{len(cases)} PASS ===")
    if passed != len(cases):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
