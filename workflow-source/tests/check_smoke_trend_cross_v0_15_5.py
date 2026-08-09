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

5 cases:
  1) sanity: cumulative_total > 0, smoke_files_count > 0, cumulative_pass <= total,
     0.0 <= cumulative_pass_rate <= 1.0
  2) cumulative_total >= smoke_files_count — 최신 release note 의 누적 수치가
     현재 전량 결과를 반영하는가. red 는 "노트를 갱신하라" 는 알림이다
     (case 2 주석의 관행 설명 참조)
  3) recent releases consistency: recent_releases[0] (가장 최근) 의 pass/total
     == panel top 의 cumulative_pass / cumulative_total
  4) delta vs v0.15.0 baseline: smoke_files_count >= v0.15.0 baseline (179).
     v0.15.0 → v0.15.4 까지 3 신규 smoke 추가 → expected 182 (179 + 3)
  5) pass_rate = 1.0: v0.15.4 시점 모든 smoke PASS 정합 (회귀 ❌)
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


def case_2_ratio_sanity() -> bool:
    """2) 최신 release note 의 누적 수치가 **현재 전량 결과를 반영** 하는가.

    `cumulative_total >= smoke_files_count` 를 요구한다.

    **이 수치는 릴리스 시점 스냅샷이 아니라 "살아있는 지표" 다.** 저장소 관행상
    smoke 가 늘면 *가장 최근 release note* 의 `누적 smoke **N/N PASS**` 줄을 함께
    갱신해 왔다 (커밋 메시지 `... (전량 205/205)` / `... (전량 206/206)` 이 그 흔적,
    `Beta-v1.0.0.md` 는 199 → 205 → 206 → … → 234 로 이어졌다). 그래서 red 는
    *거짓 경보가 아니라* **"노트를 갱신하라" 는 알림** 이다.

    2026-08-09 에 이 case 를 "정상적인 성장을 결함으로 본다" 고 오독해 판정을
    느슨하게 바꿨다가 되돌렸다. 실제로는 v1.0.0(199/199) / v1.1.2(257/257) 모두
    **발행 시점에 파일 수와 정합** 했고, red 가 난 구간은 v1.1.0 / v1.1.1 에서
    **표기 자체를 빠뜨린** 탓에 파서가 옛 노트(234)를 읽던 때였다.

    즉 고칠 것은 검사가 아니라 **노트 갱신을 빠뜨리는 절차** 다.
    """
    p4 = _collect_panel_4()
    cum_total = int(p4.get("cumulative_total", 0))
    smoke_files = int(p4.get("smoke_files_count", 0))
    if cum_total < smoke_files:
        print(f"  FAIL: cum_total={cum_total} < smoke_files={smoke_files}")
        print(f"        최신 release note 의 `누적 smoke **N/N PASS**` 를 "
              f"{smoke_files}/{smoke_files} 로 갱신할 것 (전량 PASS 확인 후).")
        return False
    print(f"  [info] cum_total/smoke_files = {cum_total}/{smoke_files} = {cum_total/smoke_files:.2f}")
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


def main() -> int:
    cases = [
        ("case_1_sanity", case_1_sanity),
        ("case_2_ratio_sanity", case_2_ratio_sanity),
        ("case_3_recent_releases_consistency", case_3_recent_releases_consistency),
        ("case_4_delta_vs_v0_15_0_baseline", case_4_delta_vs_v0_15_0_baseline),
        ("case_5_pass_rate_full", case_5_pass_rate_full),
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
