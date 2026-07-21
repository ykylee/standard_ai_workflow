"""Phase 13 AC2 — telemetry source 다양성 ≥ 4 self-contained guard (v0.15.21+).

roadmap P0-2 (AC2 수렴) 의 CI 강제. 기존 `check_telemetry_cross_v0_15_6.py` 는 live
`events.jsonl` (gitignore 런타임 데이터) 를 읽어 ≥ 1 만 확인하므로 clean checkout 에서
≥ 4 를 durable 하게 보장하지 못한다. 본 smoke 는 live-file 의존 없이 temp workspace 에
4-source fixture 를 직접 seed 하여 `summarize_telemetry` 의 `by_source` 가 4 canonical
source (dispatcher / session-start / doc-sync / backlog-update) 를 모두 집계하는지 검증한다.

배경: 3 skill (session-start / doc-sync / backlog-update) 의 memory_index retrieval 게이트가
v0.15.21 에서 opt-in → workspace memory_index 존재 시 자동 활성 으로 전환되어, dispatcher
1 source 만 있던 상태에서 4 source 로 수렴한다.

Test list (5 case):
1. test_four_canonical_sources_meet_diversity_threshold
2. test_all_four_canonical_source_names_present
3. test_hit_rate_sanity_all_hits
4. test_under_diversity_is_detectable
5. test_schema_roundtrip_for_every_canonical_source

Cross-ref: docs/architecture/phase-13-definition-north-star.md §2.2 (AC2) +
core/phase_13_followup.md §2.2 + dashboard Panel 8 (memory_index_utilization_v2).
"""

from __future__ import annotations

import json
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

# site-packages 의 stale workflow_kit shadowing 회피 (check_memory_index_telemetry.py 와 동일 패턴).
SOURCE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SOURCE_ROOT))

from workflow_kit.common.schemas.memory_index import (  # noqa: E402
    MemoryIndexTelemetryEvent,
)
from workflow_kit.common.state.memory_index import (  # noqa: E402
    append_telemetry_event,
    summarize_telemetry,
)

# AC2 수렴 목표 (roadmap P0-2 / phase_13_followup §2.2). 지금까지 code 상수로
# 존재하지 않던 threshold 를 명시화한다 (dispatcher 1 → 4 source 수렴).
AC2_MIN_SOURCE_DIVERSITY = 4
AC2_MIN_HIT_RATE = 0.9

# v0.15.21 자동 활성으로 emit 되는 4 canonical source
# (dispatcher + 3 skill: session-start / doc-sync / backlog-update).
CANONICAL_SOURCES = ("dispatcher", "session-start", "doc-sync", "backlog-update")


def _make_event(*, source: str, selected_count: int = 1, error: bool = False,
                query_tokens_count: int = 3) -> MemoryIndexTelemetryEvent:
    return MemoryIndexTelemetryEvent(
        timestamp=datetime.now(timezone.utc),
        source=source,
        workspace_root="/tmp/test-ws",
        query_tokens_count=query_tokens_count,
        selected_count=selected_count,
        cue_hits=selected_count,
        bm25_hits=0,
        expansion_hits=0,
        error=error,
    )


def _seed(ws: Path, sources) -> None:
    """각 source 당 1 hit event 를 seed."""
    for src in sources:
        append_telemetry_event(ws, _make_event(source=src, selected_count=1))


# --- Tests ---


def test_four_canonical_sources_meet_diversity_threshold() -> None:
    """4 canonical source seed → by_source 다양성 ≥ AC2_MIN_SOURCE_DIVERSITY."""
    with tempfile.TemporaryDirectory() as td:
        ws = Path(td)
        _seed(ws, CANONICAL_SOURCES)
        summary = summarize_telemetry(ws)
        diversity = len(summary.by_source)
        assert diversity >= AC2_MIN_SOURCE_DIVERSITY, (
            f"source 다양성 {diversity} < AC2 목표 {AC2_MIN_SOURCE_DIVERSITY} "
            f"(by_source={summary.by_source})"
        )
        assert summary.total_calls == len(CANONICAL_SOURCES), f"got {summary.total_calls}"


def test_all_four_canonical_source_names_present() -> None:
    """by_source 의 key set 이 4 canonical source 를 정확히 포함."""
    with tempfile.TemporaryDirectory() as td:
        ws = Path(td)
        _seed(ws, CANONICAL_SOURCES)
        summary = summarize_telemetry(ws)
        missing = set(CANONICAL_SOURCES) - set(summary.by_source.keys())
        assert not missing, f"누락된 canonical source: {missing}"


def test_hit_rate_sanity_all_hits() -> None:
    """4 source 모두 hit → hit_rate=1.0 (≥ AC2_MIN_HIT_RATE) + 0..1 범위."""
    with tempfile.TemporaryDirectory() as td:
        ws = Path(td)
        _seed(ws, CANONICAL_SOURCES)
        summary = summarize_telemetry(ws)
        assert 0.0 <= summary.hit_rate <= 1.0, f"hit_rate 범위 이탈: {summary.hit_rate}"
        assert summary.hit_rate >= AC2_MIN_HIT_RATE, (
            f"hit_rate {summary.hit_rate} < AC2 목표 {AC2_MIN_HIT_RATE}"
        )
        assert summary.total_hits == len(CANONICAL_SOURCES)
        for src, agg in summary.by_source.items():
            assert agg["hits"] <= agg["calls"], f"{src}: hits > calls ❌"


def test_under_diversity_is_detectable() -> None:
    """3 source 만 seed → 다양성 3 < 4. threshold 가 실제로 under-diversity 를 잡는지 (guard 의 guard)."""
    with tempfile.TemporaryDirectory() as td:
        ws = Path(td)
        _seed(ws, CANONICAL_SOURCES[:3])  # dispatcher / session-start / doc-sync
        summary = summarize_telemetry(ws)
        assert len(summary.by_source) < AC2_MIN_SOURCE_DIVERSITY, (
            "3 source 인데 threshold 검사가 통과하면 안 됨 (threshold 무의미)"
        )


def test_schema_roundtrip_for_every_canonical_source() -> None:
    """4 canonical source 각각 MemoryIndexTelemetryEvent JSON round-trip 정합."""
    for src in CANONICAL_SOURCES:
        ev = _make_event(source=src, selected_count=1)
        raw = ev.model_dump_json()
        obj = json.loads(raw)
        assert obj["source"] == src, f"round-trip source mismatch: {obj.get('source')} != {src}"
        # 재파싱도 정합
        ev2 = MemoryIndexTelemetryEvent.model_validate(obj)
        assert ev2.source == src


# --- 메인 실행 ---


def main() -> int:
    test_funcs = [
        test_four_canonical_sources_meet_diversity_threshold,
        test_all_four_canonical_source_names_present,
        test_hit_rate_sanity_all_hits,
        test_under_diversity_is_detectable,
        test_schema_roundtrip_for_every_canonical_source,
    ]
    failures: list[tuple[str, str]] = []
    for func in test_funcs:
        try:
            func()
            print(f"  PASS: {func.__name__}")
        except AssertionError as e:
            failures.append((func.__name__, f"AssertionError: {e}"))
            print(f"  FAIL: {func.__name__} — {e}")
        except Exception as e:  # noqa: BLE001
            failures.append((func.__name__, f"{type(e).__name__}: {e}"))
            print(f"  FAIL: {func.__name__} — {type(e).__name__}: {e}")

    total = len(test_funcs)
    passed = total - len(failures)
    print(f"\n{passed}/{total} PASS")
    if failures:
        for name, err in failures:
            print(f"  - {name}: {err}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
