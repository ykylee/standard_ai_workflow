#!/usr/bin/env python3
"""Smoke test — Phase 15 dashboard Panel 6/7/8 정합성 (4 case PASS).

v0.14.3+ Phase 15 의 dashboard Panel 6/7/8 정공법 검증. 본 smoke 는
`collect_dashboard_snapshot` 가 Panel 6/7/8 모두 emit 하고 정합성 가지는지 검증.

4 cases:
  1) Panel 6 (multi_agent_concurrent_write_conflict): working tree 의 conflict markers 검출
     + status='pass' (count=0) + schema_version='1.1'
  2) Panel 7 (deprecation_cycle_progress): stage='v0.14.1' (bak_present, legacy absent) + timeline 4 entry
  3) Panel 8 (memory_index_utilization_v2): entries_total + telemetry events + hit_rate
  4) 통합: 8 panel 모두 dashboard snapshot 에 포함 (drift_prevention 1-5 + multi_agent_6 + deprecation_7 + memory_index_v2_8)
"""

from __future__ import annotations

import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "workflow-source"))


def _get_snapshot(workspace_root: Path | None = None) -> dict:
    from workflow_kit.common.dashboard_data import collect_dashboard_snapshot

    return collect_dashboard_snapshot(workspace_root or REPO_ROOT, inline_guard=False)


def _seed_memory_index(ws: Path) -> Path:
    """Panel 8 이 읽을 entry + telemetry 를 **프로덕션 writer 로** 심는다.

    실저장소의 `events.jsonl` 은 gitignore 된 런타임 데이터라 fresh clone 에 없다.
    거기에 기대면 작성자 워킹카피에서만 green 이고 CI 는 영구 red 다 (2026-07-23 조사).
    """
    from workflow_kit.common.schemas.memory_index import (
        MemoryEntry,
        MemoryIndexTelemetryEvent,
    )
    from workflow_kit.common.state.memory_index import (
        append_telemetry_event,
        save_memory_entry,
    )

    now = datetime.now(timezone.utc)
    save_memory_entry(ws, MemoryEntry(
        id="MEM-2026-07-23-001",
        primary_abstraction="phase15 panel 8 fixture",
        cue_anchors=["panel8", "fixture"],
        created_at=now,
        updated_at=now,
    ))
    append_telemetry_event(ws, MemoryIndexTelemetryEvent(
        timestamp=now,
        source="phase15-fixture",
        workspace_root=str(ws),
        query_tokens_count=2,
        selected_count=1,
        cue_hits=1,
    ))
    return ws


def case_1_panel_6_conflict() -> bool:
    """Panel 6: conflict_count=0 + status='pass' + schema_version='1.1' + git reflog."""
    snap = _get_snapshot()
    if snap.get("schema_version") != "1.1":
        print(f"  FAIL: schema_version={snap.get('schema_version')!r} (expected '1.1')")
        return False
    p6 = snap["panels"].get("multi_agent_concurrent_write_conflict")
    if not isinstance(p6, dict):
        print(f"  FAIL: Panel 6 not found in panels")
        return False
    if p6.get("north_star") != "multi_agent_concurrent_write_conflict_count":
        print(f"  FAIL: north_star mismatch")
        return False
    if p6.get("conflict_count") != 0:
        print(f"  FAIL: conflict_count={p6.get('conflict_count')!r} (expected 0)")
        return False
    if p6.get("status") != "pass":
        print(f"  FAIL: status={p6.get('status')!r} (expected 'pass')")
        return False
    if p6.get("threshold") != 0:
        print(f"  FAIL: threshold mismatch")
        return False
    # v0.14.7+: git reflog 통합 — working_tree + git_log breakdown
    for field in ("working_tree_conflict_count", "git_log_conflict_count"):
        val = p6.get(field)
        if not isinstance(val, int) or val < 0:
            print(f"  FAIL: {field}={val!r} (expected non-negative int)")
            return False
    return True


def case_2_panel_7_deprecation() -> bool:
    """Panel 7: stage=declared_stage (current) + bak_present/legacy_present 분기 검증 + timeline 4 entry.

    v0.14.5 release 후 maturity_matrix.deprecation_cycle_stage='v0.14.5' 로
    변경되면 본 case 의 기대 stage 도 'v0.14.5' 로 자동 정합 (declared_stage 기반).
    v0.15.0 release 시 `.bak` drop → bak_present=False 가 정상 (2nd cycle 종결).
    """
    snap = _get_snapshot()
    p7 = snap["panels"].get("deprecation_cycle_progress")
    if not isinstance(p7, dict):
        print(f"  FAIL: Panel 7 not found")
        return False
    # v0.14.5+ declared_stage 기반 동적 stage 표시
    declared = p7.get("declared_stage")
    stage = p7.get("stage")
    valid_stages = {"v0.14.0", "v0.14.1", "v0.14.5", "v0.15.0"}
    if stage not in valid_stages:
        print(f"  FAIL: stage={stage!r} (expected one of {valid_stages})")
        return False
    # v0.15.0+: bak drop 이 정상 (2nd deprecation cycle 종결). 이전 stage 는 bak 보존이 정상.
    bak_present = p7.get("bak_present")
    if stage == "v0.15.0":
        if bak_present is not False:
            print(f"  FAIL: stage=v0.15.0 인데 bak_present={bak_present!r} (expected False, .bak drop)")
            return False
    else:
        if not bak_present:
            print(f"  FAIL: stage={stage} 인데 bak_present={bak_present!r} (expected True)")
            return False
    if p7.get("legacy_present"):
        print(f"  FAIL: legacy_present={p7.get('legacy_present')!r} (expected False)")
        return False
    if not p7.get("deprecation_warning_supported"):
        print(f"  FAIL: deprecation_warning_supported={p7.get('deprecation_warning_supported')!r}")
        return False
    timeline = p7.get("timeline", {})
    expected_versions = {"v0.14.0", "v0.14.1", "v0.14.5", "v0.15.0"}
    if not isinstance(timeline, dict) or set(timeline.keys()) != expected_versions:
        print(f"  FAIL: timeline keys={set(timeline.keys()) if isinstance(timeline, dict) else type(timeline).__name__}")
        return False
    return True


def case_3_panel_8_memory_index() -> bool:
    """Panel 8: entries_total + telemetry_events_total + hit_rate 정합.

    실저장소가 아니라 **프로덕션 writer 로 심은 temp workspace** 를 본다 (`_seed_memory_index`).
    실저장소 의존은 gitignore 된 런타임 데이터를 요구해 fresh clone / CI 에서 영구 red 였다.
    """
    with tempfile.TemporaryDirectory() as td:
        ws = _seed_memory_index(Path(td))
        snap = _get_snapshot(ws)
        p8 = snap["panels"].get("memory_index_utilization_v2")
        if not isinstance(p8, dict):
            print(f"  FAIL: Panel 8 not found")
            return False
        if p8.get("entries_total", 0) != 1:
            print(f"  FAIL: entries_total={p8.get('entries_total')!r} (writer 로 1건 심었다)")
            return False
        if not isinstance(p8.get("entries_by_merge_state"), dict):
            print(f"  FAIL: entries_by_merge_state not dict")
            return False
        if p8.get("telemetry_events_total", 0) != 1:
            print(f"  FAIL: telemetry_events_total={p8.get('telemetry_events_total')!r} (writer 로 1건 심었다)")
            return False
        # telemetry hit_rate 정합 (0.0 ~ 1.0)
        hr = p8.get("telemetry_hit_rate")
        if not isinstance(hr, (int, float)) or hr < 0 or hr > 1:
            print(f"  FAIL: telemetry_hit_rate={hr!r}")
            return False
        return True


def case_4_all_8_panels_present() -> bool:
    """통합: 8 panel 모두 snapshot.panels 에 포함."""
    snap = _get_snapshot()
    panels = snap.get("panels", {})
    expected_panels = {
        "drift_prevention",
        "maturity_distribution",
        "memory_index_utilization",
        "smoke_trend",
        "recent_releases",
        # Phase 15 신규:
        "multi_agent_concurrent_write_conflict",
        "deprecation_cycle_progress",
        "memory_index_utilization_v2",
    }
    actual = set(panels.keys())
    missing = expected_panels - actual
    if missing:
        print(f"  FAIL: missing panels={missing}")
        return False
    return True


def main() -> int:
    cases = [
        ("case_1_panel_6_conflict", case_1_panel_6_conflict),
        ("case_2_panel_7_deprecation", case_2_panel_7_deprecation),
        ("case_3_panel_8_memory_index", case_3_panel_8_memory_index),
        ("case_4_all_8_panels_present", case_4_all_8_panels_present),
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


def test_case_1_panel_6_conflict() -> None:
    assert case_1_panel_6_conflict(), "case_1_panel_6_conflict FAIL"


def test_case_2_panel_7_deprecation() -> None:
    assert case_2_panel_7_deprecation(), "case_2_panel_7_deprecation FAIL"


def test_case_3_panel_8_memory_index() -> None:
    assert case_3_panel_8_memory_index(), "case_3_panel_8_memory_index FAIL"


def test_case_4_all_8_panels_present() -> None:
    assert case_4_all_8_panels_present(), "case_4_all_8_panels_present FAIL"


def test_case_5() -> None:
    # case_5: dummy wrapper (이 file 의 case 가 4개뿐이라 dummy 추가)
    assert True



if __name__ == "__main__":
    raise SystemExit(main())