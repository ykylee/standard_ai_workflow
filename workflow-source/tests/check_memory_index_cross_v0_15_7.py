#!/usr/bin/env python3
"""Smoke test — Panel 3 (memory_index_utilization) cross-validation (v0.15.7+).

Panel 3 의 entries / cue_anchors / timeline / retrieval_hit_rate metric 들을
실제 file system + telemetry 와 cross-check.

5 cases:
  1) **entries_total 정합**: `entries/` 디렉토리 의 실제 .json file 갯수 ==
     Panel 3 entries_total. 각 entry 는 valid JSON + required field 정합.
  2) **entries_by_merge_state 정합**: Panel 3 entries_by_merge_state 의
     value 합 == entries_total + 각 merge_state 의 file 갯수와 정합.
  3) **cue_anchors_unique 정합**: Panel 3 cue_anchors_top 의 unique count ==
     cue_anchors_unique (file 의 cue_anchors 직접 집계).
  4) **timeline + retrieval_hit_rate 정합**: first_entry_date <= last_entry_date +
     cumulative_timeline 의 date 가 first ~ last 사이 + retrieval_hit_rate (Panel 3)
     == telemetry_hit_rate (Panel 8) cross-panel.
  5) **한 대시보드 = 한 telemetry 스냅샷** (TASK-2026-09-28-main-005): 두 읽기
     사이에 이벤트가 붙는 상황을 결정적으로 주입해도 Panel 3 == Panel 8 이고,
     스냅샷은 1회만 뜬다. case 4 는 실저장소를 재므로 그 경합을 **가끔만** 본다 —
     91차 push 게이트에서 1/5 로 red 였다.
"""

from __future__ import annotations

#: 이 검사의 입력 표면 (spec `core/test_impact_tiering_spec.md` §2).
#: 게이트 채취 실측에서 뽑아 넓은 쪽으로 올렸다 — 좁으면 meta-watch 가 red 로 잡는다.
WATCHES = (
    # case 4·5 가 대시보드 전체를 조립한다 — 입력 표면이 대시보드의 표면이다
    # (main-005 채취: memory/active 640건 · release ledger · core · releases · kit).
    # 예전 선언은 entries/* 하나라 dashboard_data 를 고쳐도 --changed 가 안 골랐다.
    "ai-workflow/memory/*",
    "workflow-source/workflow_kit/*",
    "workflow-source/core/*",
    "workflow-source/releases/*",
    "workflow-source/pyproject.toml",
)

import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
MEMORY_INDEX_DIR = REPO_ROOT / "ai-workflow" / "memory" / "active" / "memory_index"
ENTRIES_DIR = MEMORY_INDEX_DIR / "entries"

REQUIRED_ENTRY_FIELDS = {"id", "cue_anchors", "merge_state"}


def _collect_dashboard() -> dict:
    """workflow_kit_cli dashboard --format=json subprocess 호출 → 전체 dashboard dict."""
    proc = subprocess.run(
        [sys.executable, "-m", "workflow_kit.workflow_kit_cli",
         "--command=dashboard", "--format=json"],
        cwd=str(REPO_ROOT),
        env={"PYTHONPATH": str(SOURCE_ROOT), "PATH": __import__("os").environ.get("PATH", "")},
        capture_output=True, text=True, timeout=60,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"dashboard --format=json failed: {proc.stderr[:300]}")
    return json.loads(proc.stdout)


def _load_entries() -> list[dict]:
    """entries/ 디렉토리 의 모든 .json file 을 valid dict list 로 반환.

    malformed file 0개 정합 (entry 는 critical data source). 단, schema mismatch
    (필수 field 부재) 는 fail ❌.
    """
    if not ENTRIES_DIR.is_dir():
        return []
    entries: list[dict] = []
    for f in sorted(ENTRIES_DIR.glob("*.json")):
        try:
            obj = json.loads(f.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            raise AssertionError(f"entry {f.name} parse 실패: {e}")
        if not isinstance(obj, dict):
            raise AssertionError(f"entry {f.name} not dict: {type(obj)}")
        if not REQUIRED_ENTRY_FIELDS.issubset(obj.keys()):
            missing = REQUIRED_ENTRY_FIELDS - set(obj.keys())
            raise AssertionError(f"entry {f.name} missing fields: {missing}")
        entries.append(obj)
    return entries


def case_1_entries_total() -> bool:
    """1) entries_total 정합: entries/ 실제 file 갯수 == Panel 3 entries_total."""
    d = _collect_dashboard()
    panel_3 = d["panels"]["memory_index_utilization"]
    panel_total = int(panel_3.get("entries_total", 0))
    actual_files = sum(1 for _ in ENTRIES_DIR.glob("*.json")) if ENTRIES_DIR.is_dir() else 0
    if panel_total != actual_files:
        print(f"  FAIL: panel entries_total={panel_total} != actual files={actual_files}")
        return False
    # valid entries 정합 (load 시 raise 가능)
    try:
        entries = _load_entries()
    except AssertionError as e:
        print(f"  FAIL: {e}")
        return False
    if len(entries) != panel_total:
        print(f"  FAIL: loaded entries={len(entries)} != panel entries_total={panel_total}")
        return False
    print(f"  [info] entries_total={panel_total}, actual files={actual_files}, loaded={len(entries)}")
    return True


def case_2_entries_by_merge_state() -> bool:
    """2) entries_by_merge_state 정합: 분해 합 == entries_total + 각 state 의 file 갯수 정합."""
    d = _collect_dashboard()
    panel_3 = d["panels"]["memory_index_utilization"]
    by_state = panel_3.get("entries_by_merge_state", {})
    panel_total = int(panel_3.get("entries_total", 0))
    if not isinstance(by_state, dict) or not by_state:
        print(f"  FAIL: entries_by_merge_state 부재 또는 empty: {by_state}")
        return False
    # 분해 합 == entries_total
    state_sum = sum(by_state.values())
    if state_sum != panel_total:
        print(f"  FAIL: by_state sum={state_sum} != entries_total={panel_total}")
        return False
    # 실제 entry file 의 merge_state 카운트
    try:
        entries = _load_entries()
    except AssertionError as e:
        print(f"  FAIL: {e}")
        return False
    actual_counter = Counter(e.get("merge_state", "") for e in entries)
    for state, count in by_state.items():
        if actual_counter.get(state, 0) != count:
            print(f"  FAIL: by_state[{state!r}]={count} != actual count={actual_counter.get(state, 0)}")
            return False
    print(f"  [info] by_state={dict(by_state)}, sum={state_sum}")
    return True


def case_3_cue_anchors_unique() -> bool:
    """3) cue_anchors_unique 정합: cue_anchors_top 의 unique count == cue_anchors_unique (file 집계)."""
    d = _collect_dashboard()
    panel_3 = d["panels"]["memory_index_utilization"]
    cue_unique = int(panel_3.get("cue_anchors_unique", 0))
    cue_top = panel_3.get("cue_anchors_top", [])
    # cue_anchors_top 의 unique
    panel_unique = len(set(c.get("anchor", "") for c in cue_top if isinstance(c, dict) and c.get("anchor")))
    # 실제 file 의 cue_anchors 직접 집계
    try:
        entries = _load_entries()
    except AssertionError as e:
        print(f"  FAIL: {e}")
        return False
    all_anchors = []
    for e in entries:
        anchors = e.get("cue_anchors", [])
        if not isinstance(anchors, list):
            print(f"  FAIL: entry {e.get('id')!r} cue_anchors not list: {anchors!r}")
            return False
        all_anchors.extend(anchors)
    actual_unique = len(set(all_anchors))
    if cue_unique != actual_unique:
        print(f"  FAIL: cue_anchors_unique={cue_unique} != actual={actual_unique}")
        return False
    if panel_unique != actual_unique:
        # panel top 의 unique 가 actual 과 다르면, panel top 자체 가 truncated 됨
        # (cue_anchors_top 은 top N 만 emit 가능, 그러나 unique 는 전체 집계)
        # 단, panel_unique >= cue_unique 면 정상 (top N 이 unique 의 부분집합)
        if panel_unique > actual_unique:
            print(f"  FAIL: cue_anchors_top unique={panel_unique} > actual={actual_unique}")
            return False
    print(f"  [info] cue_unique={cue_unique}, actual unique={actual_unique}, top entries={len(cue_top)}")
    return True


def case_4_timeline_and_retrieval_hit_rate() -> bool:
    """4) timeline + retrieval_hit_rate 정합: first <= last + timeline in range + Panel 3 = Panel 8."""
    d = _collect_dashboard()
    panel_3 = d["panels"]["memory_index_utilization"]
    panel_8 = d["panels"]["memory_index_utilization_v2"]
    first = str(panel_3.get("first_entry_date", ""))
    last = str(panel_3.get("last_entry_date", ""))
    timeline = panel_3.get("cumulative_timeline", [])
    # first <= last
    if not first or not last:
        print(f"  FAIL: first/last_entry_date 부재: first={first!r}, last={last!r}")
        return False
    if first > last:
        print(f"  FAIL: first_entry_date={first} > last_entry_date={last}")
        return False
    # cumulative_timeline 의 date 가 first ~ last 사이
    for entry in timeline:
        date = str(entry.get("date", ""))
        if not (first <= date <= last):
            print(f"  FAIL: timeline date={date} out of range [{first}, {last}]")
            return False
    # cumulative_timeline 의 마지막 entry 의 count == entries_total
    if timeline:
        last_count = int(timeline[-1].get("count", 0))
        panel_total = int(panel_3.get("entries_total", 0))
        if last_count != panel_total:
            print(f"  FAIL: timeline last count={last_count} != entries_total={panel_total}")
            return False
    # Panel 3 retrieval_hit_rate == Panel 8 telemetry_hit_rate
    p3_rate = float(panel_3.get("retrieval_hit_rate", -1.0))
    p8_rate = float(panel_8.get("telemetry_hit_rate", -2.0))
    if abs(p3_rate - p8_rate) > 1e-9:
        print(f"  FAIL: retrieval_hit_rate Panel 3={p3_rate} != Panel 8={p8_rate}")
        return False
    print(f"  [info] first={first}, last={last}, timeline_entries={len(timeline)}, hit_rate={p3_rate} (Panel 3 == Panel 8)")
    return True


def case_5_one_snapshot_per_dashboard() -> bool:
    """5) 읽을 때마다 값이 달라지는 telemetry 에서도 두 패널이 같은 순간을 잰다."""
    if str(SOURCE_ROOT) not in sys.path:
        sys.path.insert(0, str(SOURCE_ROOT))
    from workflow_kit.common import dashboard_data
    from workflow_kit.common.state import memory_index

    real = memory_index.summarize_telemetry
    calls = {"n": 0}

    def drifting(workspace_root, **kw):  # noqa: ANN001, ANN003
        # 호출마다 1건씩 늘어난 로그 — 병렬 검사가 session-start 로 붙이는 모양.
        calls["n"] += 1
        base = real(workspace_root, **kw)
        total = base.total_calls + calls["n"]
        return base.model_copy(update={
            "total_calls": total,
            "hit_rate": round(base.total_hits / total, 4),
        })

    memory_index.summarize_telemetry = drifting
    try:
        # 실제 조립 경로 — collector 단위가 아니라 배선(스냅샷을 넘기는가)을 잰다.
        dash = dashboard_data.collect_dashboard_snapshot(REPO_ROOT, inline_guard=False)
        p3 = dash["panels"]["memory_index_utilization"]
        p8 = dash["panels"]["memory_index_utilization_v2"]
        shared_calls = calls["n"]
        # 대조군: 스냅샷을 안 넘기면(각자 읽으면) 실제로 갈리는가 — 주입이 살아 있다는 증거
        p3_solo = dashboard_data.collect_memory_index_utilization(REPO_ROOT)
        p8_solo = dashboard_data.collect_memory_index_utilization_v2(REPO_ROOT)
    finally:
        memory_index.summarize_telemetry = real

    if p3_solo["retrieval_hit_rate"] == p8_solo["telemetry_hit_rate"]:
        print("  FAIL: 주입이 죽었다 — 각자 읽어도 값이 같다 (이 case 가 아무것도 못 잰다)")
        return False
    if shared_calls != 1:
        print(f"  FAIL: 대시보드 한 번에 telemetry 를 {shared_calls}회 읽었다 — 스냅샷이 1개가 아니다")
        return False
    if p3["retrieval_hit_rate"] != p8["telemetry_hit_rate"]:
        print(f"  FAIL: 같은 스냅샷인데 Panel 3={p3['retrieval_hit_rate']} != "
              f"Panel 8={p8['telemetry_hit_rate']}")
        return False
    print(f"  [info] 스냅샷 공유 시 Panel 3 == Panel 8 == {p3['retrieval_hit_rate']} · "
          f"각자 읽으면 {p3_solo['retrieval_hit_rate']} vs {p8_solo['telemetry_hit_rate']}")
    return True


def main() -> int:
    cases = [
        ("case_1_entries_total", case_1_entries_total),
        ("case_2_entries_by_merge_state", case_2_entries_by_merge_state),
        ("case_3_cue_anchors_unique", case_3_cue_anchors_unique),
        ("case_4_timeline_and_retrieval_hit_rate", case_4_timeline_and_retrieval_hit_rate),
        ("case_5_one_snapshot_per_dashboard", case_5_one_snapshot_per_dashboard),
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


def test_case_1_entries_total() -> None:
    assert case_1_entries_total(), "case_1_entries_total FAIL"


def test_case_2_entries_by_merge_state() -> None:
    assert case_2_entries_by_merge_state(), "case_2_entries_by_merge_state FAIL"


def test_case_3_cue_anchors_unique() -> None:
    assert case_3_cue_anchors_unique(), "case_3_cue_anchors_unique FAIL"


def test_case_4_timeline_and_retrieval_hit_rate() -> None:
    assert case_4_timeline_and_retrieval_hit_rate(), "case_4_timeline_and_retrieval_hit_rate FAIL"


def test_case_5_one_snapshot_per_dashboard() -> None:
    assert case_5_one_snapshot_per_dashboard(), "case_5_one_snapshot_per_dashboard FAIL"


if __name__ == "__main__":
    raise SystemExit(main())
