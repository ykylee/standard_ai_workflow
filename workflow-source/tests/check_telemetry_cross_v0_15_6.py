#!/usr/bin/env python3
"""Smoke test — Panel 6/8 telemetry + events.jsonl cross-validation (v0.15.6+).

v0.13.1+ telemetry sidecar 인프라 + Panel 8 (memory_index_utilization_v2) +
Panel 6 (multi_agent_concurrent_write_conflict) 의 cross-check discipline anchor.

4 cases:
  1) **events.jsonl parse**: `telemetry/events.jsonl` file 존재 + JSON parse 가능
     + MemoryIndexTelemetryEvent schema 정합. malformed line 0개 이상 허용
     (warn only), 단 valid event 1개 이상 정합 (north-star "1 release ≥ 1 query + hit").
  2) **Panel 8 source 다양성**: telemetry `by_source` dict 가 ≥ 1 source 정합
     (현 시점 dispatcher 1 source, 미래 ≥ 1). 각 source 의 {calls, hits} dict 정합.
  3) **Panel 8 hit_rate sanity**: `telemetry_hit_rate` 0.0 ~ 1.0 정합 +
     `telemetry_hit_count <= telemetry_total_queries` + `telemetry_events_total >= 1`
     (north-star 정합) + `by_source[*].hits <= by_source[*].calls`.
  4) **Panel 6 conflict 정합**: `working_tree_conflict_count + git_log_conflict_count
     == conflict_count` 정합 + `threshold >= 0` + `status = pass if conflict_count <= threshold
     else fail` 정합.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
TELEMETRY_FILE = REPO_ROOT / "ai-workflow" / "memory" / "active" / "memory_index" / "telemetry" / "events.jsonl"


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


def _parse_telemetry_events() -> tuple[list[dict], list[tuple[int, str]]]:
    """telemetry/events.jsonl file parse → (valid_events, malformed_lines).

    valid_events: dict list (각 event). Pydantic schema validate 는 정밀도 위해
    수동 check (각 field 의 type / value range).
    malformed_lines: (line_number, raw_line) list.
    """
    if not TELEMETRY_FILE.is_file():
        return [], []
    valid: list[dict] = []
    malformed: list[tuple[int, str]] = []
    required_fields = {
        "timestamp", "source", "query_tokens_count", "selected_count",
        "cue_hits", "bm25_hits", "expansion_hits", "error",
    }
    int_fields = {"query_tokens_count", "selected_count", "cue_hits", "bm25_hits", "expansion_hits"}
    bool_fields = {"error"}
    str_fields = {"timestamp", "source"}
    for ln, raw in enumerate(TELEMETRY_FILE.read_text(encoding="utf-8").splitlines(), start=1):
        if not raw.strip():
            continue
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError:
            malformed.append((ln, raw[:80]))
            continue
        if not isinstance(obj, dict):
            malformed.append((ln, f"non-dict: {raw[:60]}"))
            continue
        if not required_fields.issubset(obj.keys()):
            missing = required_fields - set(obj.keys())
            malformed.append((ln, f"missing fields: {missing}"))
            continue
        # type check
        ok = True
        for f in int_fields:
            if not isinstance(obj[f], int) or obj[f] < 0:
                malformed.append((ln, f"field {f!r} not non-negative int: {obj[f]!r}"))
                ok = False
                break
        if not ok:
            continue
        for f in bool_fields:
            if not isinstance(obj[f], bool):
                malformed.append((ln, f"field {f!r} not bool: {obj[f]!r}"))
                ok = False
                break
        if not ok:
            continue
        for f in str_fields:
            if not isinstance(obj[f], str) or not obj[f]:
                malformed.append((ln, f"field {f!r} not non-empty str: {obj[f]!r}"))
                ok = False
                break
        if not ok:
            continue
        valid.append(obj)
    return valid, malformed


def case_1_events_jsonl_parse() -> bool:
    """1) events.jsonl file 존재 + parse 가능 + valid event 1개 이상 정합."""
    if not TELEMETRY_FILE.is_file():
        print(f"  FAIL: telemetry file 부재: {TELEMETRY_FILE}")
        return False
    valid, malformed = _parse_telemetry_events()
    if not valid:
        print(f"  FAIL: valid event 0개 (north-star '1 release ≥ 1 query + hit' 위반)")
        return False
    if malformed:
        # warn only — malformed line 0개 이상 허용
        print(f"  [warn] malformed lines: {len(malformed)} (file integrity 시그널, fail ❌ 아님)")
        for ln, raw in malformed[:3]:
            print(f"    line {ln}: {raw}")
    print(f"  [info] valid events: {len(valid)}, malformed: {len(malformed)}")
    return True


def case_2_panel_8_source_diversity() -> bool:
    """2) Panel 8 telemetry `by_source` (dict[str, int]) 에 ≥ 1 source 정합.

    Panel 8 telemetry_by_source shape: source -> event_count (int).
    (Panel 3 telemetry.by_source shape 과 다름 — Panel 3 는 {calls, hits} dict).
    """
    d = _collect_dashboard()
    panel_8 = d["panels"]["memory_index_utilization_v2"]
    by_source = panel_8.get("telemetry_by_source", {})
    if not isinstance(by_source, dict) or not by_source:
        print(f"  FAIL: telemetry_by_source 부재 또는 empty: {by_source}")
        return False
    if len(by_source) < 1:
        print(f"  FAIL: source 다양성 부족: {len(by_source)} source (expected ≥ 1)")
        return False
    # 각 source 의 int 정합 + ≥ 0
    for source, count in by_source.items():
        if not isinstance(count, int) or count < 0:
            print(f"  FAIL: by_source[{source!r}] = {count!r} (expected non-negative int)")
            return False
    # by_source 총합 == events_total
    total_from_source = sum(by_source.values())
    events_total = int(panel_8.get("telemetry_events_total", 0))
    if total_from_source != events_total:
        print(f"  FAIL: by_source sum={total_from_source} != events_total={events_total}")
        return False
    # 실제 event source 와 panel by_source 일치
    valid, _ = _parse_telemetry_events()
    event_sources = {e["source"] for e in valid}
    panel_sources = set(by_source.keys())
    if event_sources != panel_sources:
        print(f"  [warn] source 불일치 — event={event_sources}, panel={panel_sources}")
    print(f"  [info] sources ({len(by_source)}): {dict(sorted(by_source.items()))}, total={events_total}")
    return True


def case_3_panel_8_hit_rate_sanity() -> bool:
    """3) Panel 8 hit_rate sanity: 0.0~1.0 + hit ≤ total + events ≥ 1."""
    d = _collect_dashboard()
    panel_8 = d["panels"]["memory_index_utilization_v2"]
    rate = float(panel_8.get("telemetry_hit_rate", -1.0))
    if not (0.0 <= rate <= 1.0):
        print(f"  FAIL: hit_rate={rate} (expected 0.0 ~ 1.0)")
        return False
    total_queries = int(panel_8.get("telemetry_total_queries", 0))
    hit_count = int(panel_8.get("telemetry_hit_count", 0))
    events_total = int(panel_8.get("telemetry_events_total", 0))
    if events_total < 1:
        print(f"  FAIL: telemetry_events_total={events_total} < 1 (north-star 위반)")
        return False
    if hit_count > total_queries:
        print(f"  FAIL: hit_count={hit_count} > total_queries={total_queries}")
        return False
    # rate == hit_count / total_queries (if total_queries > 0)
    if total_queries > 0 and abs(rate - hit_count / total_queries) > 1e-9:
        print(f"  FAIL: rate={rate} != hit_count/total_queries={hit_count}/{total_queries}={hit_count/total_queries}")
        return False
    print(f"  [info] rate={rate}, events={events_total}, queries={total_queries}, hits={hit_count}")
    return True


def case_4_panel_6_conflict_consistency() -> bool:
    """4) Panel 6 conflict 정합: working + git_log = conflict + threshold ≥ 0 + status logic."""
    d = _collect_dashboard()
    panel_6 = d["panels"]["multi_agent_concurrent_write_conflict"]
    working = int(panel_6.get("working_tree_conflict_count", -1))
    git_log = int(panel_6.get("git_log_conflict_count", -1))
    conflict = int(panel_6.get("conflict_count", -1))
    threshold = int(panel_6.get("threshold", -1))
    status = str(panel_6.get("status", ""))
    if working < 0 or git_log < 0 or conflict < 0:
        print(f"  FAIL: count field 음수: working={working}, git_log={git_log}, conflict={conflict}")
        return False
    if working + git_log != conflict:
        print(f"  FAIL: working + git_log = {working + git_log} != conflict = {conflict}")
        return False
    if threshold < 0:
        print(f"  FAIL: threshold={threshold} < 0")
        return False
    if status not in ("pass", "fail", "error"):
        print(f"  FAIL: status invalid: {status!r}")
        return False
    # status logic: pass if conflict <= threshold else fail (단, threshold=0 일 때 conflict>0 면 fail)
    if status == "pass" and conflict > threshold:
        print(f"  FAIL: status='pass' but conflict={conflict} > threshold={threshold}")
        return False
    if status == "fail" and conflict <= threshold:
        print(f"  FAIL: status='fail' but conflict={conflict} <= threshold={threshold}")
        return False
    print(f"  [info] working={working}, git_log={git_log}, conflict={conflict}, threshold={threshold}, status={status}")
    return True


def main() -> int:
    cases = [
        ("case_1_events_jsonl_parse", case_1_events_jsonl_parse),
        ("case_2_panel_8_source_diversity", case_2_panel_8_source_diversity),
        ("case_3_panel_8_hit_rate_sanity", case_3_panel_8_hit_rate_sanity),
        ("case_4_panel_6_conflict_consistency", case_4_panel_6_conflict_consistency),
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
