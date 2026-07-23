#!/usr/bin/env python3
"""Smoke test — Panel 6/8 telemetry + events.jsonl cross-validation (v0.15.6+).

v0.13.1+ telemetry sidecar 인프라 + Panel 8 (memory_index_utilization_v2) +
Panel 6 (multi_agent_concurrent_write_conflict) 의 cross-check discipline anchor.

## v1.0.1+ 자립형 전환 — 왜 바꿨나

이 check 는 **실저장소의 `events.jsonl` 을 읽었다.** 그 파일은 gitignore 된 런타임
데이터라 fresh clone 에는 없다. 그래서 작성자의 워킹카피에서만 green 이었고, CI 는
이것 때문에 계속 red 였다 (2026-07-23 조사: smoke workflow 최근 40회 전량 failure).
"전량 209/209 PASS" 라는 선언이 **재현 불가능한 환경에서만 성립**하고 있었다.

> 없는 파일을 요구하는 대신 **skip** 하는 방식도 있다. 그러나 CI 에서 항상 skip 되면
> 그 check 는 도는 척만 하는 것이고, red 보다 나쁘다 — 초록으로 보이기 때문이다.
> 그래서 skip 이 아니라 **fixture 를 실제로 만들어 매번 돌린다.**

fixture 는 손으로 쓰지 않는다. `append_telemetry_event` / `save_memory_entry` 라는
**프로덕션 writer 를 호출**해서 만든다 (§2.22 왕복 계약과 같은 이유 — 손으로 쓴
fixture 는 reader 기대에 맞춰져 있어 writer 가 딴 데 쓰고 있어도 통과한다).

`telemetry_events_total >= 1` 을 실저장소에 대해 단언하던 부분은 뺐다. 그건 코드의
성질이 아니라 **운영 실적**이고, 운영 실적을 smoke 로 강제하면 데이터가 없는 환경에서
영구 red 가 된다. 대신 데이터가 없을 때 panel 이 어떻게 행동하는지를 case 5 로 새로
검사한다 — 이전에는 그 분기가 아예 테스트되지 않았다.

5 cases:
  1) **events.jsonl parse**: 프로덕션 writer 가 쓴 events.jsonl JSON parse 가능
     + schema 정합. malformed line 은 warn only.
  2) **Panel 8 source 다양성**: telemetry `by_source` 가 실제 event source 집합과
     일치 + 합계 == `telemetry_events_total`.
  3) **Panel 8 hit_rate sanity**: `telemetry_hit_rate` 0.0~1.0 +
     `hit_count <= total_queries` + `rate == hit_count / total_queries`.
  4) **Panel 6 conflict 정합** (실저장소): `working + git_log == conflict` +
     `threshold >= 0` + status logic.
  5) **telemetry 부재 분기**: 데이터가 없는 workspace 에서 panel 이 죽지 않고
     0 / 빈 dict 를 낸다.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
sys.path.insert(0, str(SOURCE_ROOT))

from workflow_kit.common.schemas.memory_index import (  # noqa: E402
    MemoryEntry,
    MemoryIndexTelemetryEvent,
)
from workflow_kit.common.state.memory_index import (  # noqa: E402
    append_telemetry_event,
    save_memory_entry,
)

# fixture 가 만들어 낼 값 — 아래 case 들이 이 숫자를 그대로 대조한다.
FIXTURE_SOURCES: dict[str, int] = {"dispatcher": 2, "session-start": 1, "doc-sync": 1}
FIXTURE_EVENTS_TOTAL = sum(FIXTURE_SOURCES.values())
FIXTURE_HIT_EVENTS = 3  # cue_hits 를 1 이상으로 준 event 갯수


def _build_fixture_workspace(ws: Path) -> Path:
    """프로덕션 writer 로 telemetry + memory entry 를 갖춘 workspace 를 만든다.

    손으로 JSON 을 쓰지 않는 것이 핵심이다 — writer 가 경로/포맷을 바꾸면 이 fixture 도
    같이 따라가야 하고, 따라가지 못하면 그 자체가 결함 신호다.
    """
    now = datetime.now(timezone.utc)
    save_memory_entry(ws, MemoryEntry(
        id="MEM-2026-07-23-001",
        primary_abstraction="telemetry cross-validation fixture",
        cue_anchors=["telemetry", "fixture"],
        created_at=now,
        updated_at=now,
    ))
    emitted = 0
    for source, count in FIXTURE_SOURCES.items():
        for i in range(count):
            # 앞의 FIXTURE_HIT_EVENTS 개만 hit 를 준다 (hit_rate 가 0/1 양극단이 아니게).
            hit = 1 if emitted < FIXTURE_HIT_EVENTS else 0
            append_telemetry_event(ws, MemoryIndexTelemetryEvent(
                timestamp=now + timedelta(seconds=emitted),
                source=source,
                workspace_root=str(ws),
                query_tokens_count=2,
                selected_count=hit,
                cue_hits=hit,
            ))
            emitted += 1
    return ws


def _collect_dashboard(workspace_root: Path | None = None) -> dict:
    """workflow_kit_cli dashboard --format=json subprocess 호출 → 전체 dashboard dict."""
    cmd = [sys.executable, "-m", "workflow_kit.workflow_kit_cli",
           "--command=dashboard", "--format=json"]
    if workspace_root is not None:
        cmd.append(f"--workspace-root={workspace_root}")
    proc = subprocess.run(
        cmd,
        cwd=str(REPO_ROOT),
        env={"PYTHONPATH": str(SOURCE_ROOT), "PATH": __import__("os").environ.get("PATH", "")},
        capture_output=True, text=True, timeout=60,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"dashboard --format=json failed: {proc.stderr[:300]}")
    return json.loads(proc.stdout)


def _telemetry_file(ws: Path) -> Path:
    """fixture workspace 의 events.jsonl 경로 (writer 가 쓰는 자리와 같아야 한다)."""
    return ws / "ai-workflow" / "memory" / "active" / "memory_index" / "telemetry" / "events.jsonl"


def _parse_telemetry_events(ws: Path) -> tuple[list[dict], list[tuple[int, str]]]:
    """telemetry/events.jsonl file parse → (valid_events, malformed_lines).

    valid_events: dict list (각 event). Pydantic schema validate 는 정밀도 위해
    수동 check (각 field 의 type / value range).
    malformed_lines: (line_number, raw_line) list.
    """
    telemetry_file = _telemetry_file(ws)
    if not telemetry_file.is_file():
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
    for ln, raw in enumerate(telemetry_file.read_text(encoding="utf-8").splitlines(), start=1):
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
    """1) 프로덕션 writer 가 쓴 events.jsonl 이 parse 가능 + schema 정합."""
    with tempfile.TemporaryDirectory() as td:
        ws = _build_fixture_workspace(Path(td))
        telemetry_file = _telemetry_file(ws)
        if not telemetry_file.is_file():
            print(f"  FAIL: writer 가 events.jsonl 을 만들지 않았다: {telemetry_file}")
            return False
        return _assert_events_parse(ws)


def _assert_events_parse(ws: Path) -> bool:
    valid, malformed = _parse_telemetry_events(ws)
    if len(valid) != FIXTURE_EVENTS_TOTAL:
        print(f"  FAIL: valid event {len(valid)}개 (writer 로 {FIXTURE_EVENTS_TOTAL}건 기록했다)")
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
    with tempfile.TemporaryDirectory() as td:
        ws = _build_fixture_workspace(Path(td))
        d = _collect_dashboard(ws)
        panel_8 = d["panels"]["memory_index_utilization_v2"]
        by_source = panel_8.get("telemetry_by_source", {})
        if not isinstance(by_source, dict) or not by_source:
            print(f"  FAIL: telemetry_by_source 부재 또는 empty: {by_source}")
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
        # writer 로 기록한 것과 panel 이 읽은 것이 정확히 같아야 한다 (warn 이 아니라 fail).
        if by_source != FIXTURE_SOURCES:
            print(f"  FAIL: panel by_source={dict(sorted(by_source.items()))} != writer={FIXTURE_SOURCES}")
            return False
        valid, _ = _parse_telemetry_events(ws)
        event_sources = {e["source"] for e in valid}
        if event_sources != set(by_source.keys()):
            print(f"  FAIL: source 불일치 — event={event_sources}, panel={set(by_source.keys())}")
            return False
        print(f"  [info] sources ({len(by_source)}): {dict(sorted(by_source.items()))}, total={events_total}")
        return True


def case_3_panel_8_hit_rate_sanity() -> bool:
    """3) Panel 8 hit_rate sanity: 0.0~1.0 + hit ≤ total + rate = hit/total."""
    with tempfile.TemporaryDirectory() as td:
        ws = _build_fixture_workspace(Path(td))
        d = _collect_dashboard(ws)
        panel_8 = d["panels"]["memory_index_utilization_v2"]
        rate = float(panel_8.get("telemetry_hit_rate", -1.0))
        if not (0.0 <= rate <= 1.0):
            print(f"  FAIL: hit_rate={rate} (expected 0.0 ~ 1.0)")
            return False
        total_queries = int(panel_8.get("telemetry_total_queries", 0))
        hit_count = int(panel_8.get("telemetry_hit_count", 0))
        events_total = int(panel_8.get("telemetry_events_total", 0))
        if events_total != FIXTURE_EVENTS_TOTAL:
            print(f"  FAIL: events_total={events_total} != writer 기록 {FIXTURE_EVENTS_TOTAL}")
            return False
        if hit_count != FIXTURE_HIT_EVENTS:
            print(f"  FAIL: hit_count={hit_count} != writer 가 hit 를 준 {FIXTURE_HIT_EVENTS}건")
            return False
        if hit_count > total_queries:
            print(f"  FAIL: hit_count={hit_count} > total_queries={total_queries}")
            return False
        # rate == hit_count / total_queries (if total_queries > 0)
        if total_queries > 0 and abs(rate - hit_count / total_queries) > 1e-9:
            print(f"  FAIL: rate={rate} != hit_count/total_queries={hit_count}/{total_queries}")
            return False
        print(f"  [info] rate={rate}, events={events_total}, queries={total_queries}, hits={hit_count}")
        return True


def case_5_panel_8_absent_telemetry() -> bool:
    """5) telemetry 가 없는 workspace 에서 panel 이 죽지 않고 0 / 빈 dict 를 낸다.

    이전에는 이 분기가 아예 테스트되지 않았다 — 실저장소에는 항상 데이터가 있었기
    때문이다. 그리고 데이터가 없는 환경(fresh clone / CI)에서는 check 가 통째로 red 였다.
    """
    with tempfile.TemporaryDirectory() as td:
        ws = Path(td)  # 아무것도 쓰지 않는다
        d = _collect_dashboard(ws)
        panel_8 = d["panels"]["memory_index_utilization_v2"]
        events_total = panel_8.get("telemetry_events_total")
        by_source = panel_8.get("telemetry_by_source")
        rate = panel_8.get("telemetry_hit_rate")
        if events_total != 0:
            print(f"  FAIL: telemetry 부재인데 events_total={events_total!r} (expected 0)")
            return False
        if by_source != {}:
            print(f"  FAIL: telemetry 부재인데 by_source={by_source!r} (expected {{}})")
            return False
        if not isinstance(rate, (int, float)) or not (0.0 <= float(rate) <= 1.0):
            print(f"  FAIL: telemetry 부재인데 hit_rate={rate!r} (0.0~1.0 이어야 한다)")
            return False
        print(f"  [info] 부재 분기 정합: events_total=0, by_source={{}}, hit_rate={rate}")
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
        ("case_5_panel_8_absent_telemetry", case_5_panel_8_absent_telemetry),
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


def test_case_1_events_jsonl_parse() -> None:
    assert case_1_events_jsonl_parse(), "case_1_events_jsonl_parse FAIL"


def test_case_2_panel_8_source_diversity() -> None:
    assert case_2_panel_8_source_diversity(), "case_2_panel_8_source_diversity FAIL"


def test_case_3_panel_8_hit_rate_sanity() -> None:
    assert case_3_panel_8_hit_rate_sanity(), "case_3_panel_8_hit_rate_sanity FAIL"


def test_case_4_panel_6_conflict_consistency() -> None:
    assert case_4_panel_6_conflict_consistency(), "case_4_panel_6_conflict_consistency FAIL"


def test_case_5_panel_8_absent_telemetry() -> None:
    # v1.0.1+: 자리를 채우던 `assert True` dummy 를 실제 검사로 교체.
    assert case_5_panel_8_absent_telemetry(), "case_5_panel_8_absent_telemetry FAIL"



if __name__ == "__main__":
    raise SystemExit(main())
