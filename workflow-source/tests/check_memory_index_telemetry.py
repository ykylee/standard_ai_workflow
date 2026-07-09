"""workflow_kit memory_index telemetry sidecar smoke test (v0.13.1+).

Phase 13 AC2 (memory_index 활용도 측정) 의 telemetry 인프라가 spec 그대로 동작하는지 검증한다.

Test list (6 case):
1. test_emit_one_event_returns_summary_with_one_call
2. test_two_hits_one_miss_hit_rate_two_thirds
3. test_by_source_breakdown_distinguishes_skills
4. test_malformed_jsonl_line_is_skipped
5. test_workspace_root_absent_returns_empty_summary
6. test_concurrent_append_preserves_all_lines

Cross-ref: docs/architecture/phase-13-definition-north-star.md §2.4 + dashboard panel 3.
"""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
import threading
from datetime import datetime, timezone
from pathlib import Path

# site-packages 의 stale workflow_kit 이 source tree 를 shadowing 하는 v0.11.18 패턴 회피.
SOURCE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SOURCE_ROOT))

from workflow_kit.common.schemas.memory_index import (  # noqa: E402
    MemoryIndexTelemetryEvent,
)
from workflow_kit.common.state.memory_index import (  # noqa: E402
    MemoryIndexTelemetrySummary,
    append_telemetry_event,
    read_telemetry_events,
    summarize_telemetry,
    telemetry_path,
)


def _make_event(*, source: str, selected_count: int = 0, error: bool = False,
                cue_hits: int = 0, bm25_hits: int = 0, expansion_hits: int = 0,
                query_tokens_count: int = 1) -> MemoryIndexTelemetryEvent:
    return MemoryIndexTelemetryEvent(
        timestamp=datetime.now(timezone.utc),
        source=source,
        workspace_root="/tmp/test-ws",
        query_tokens_count=query_tokens_count,
        selected_count=selected_count,
        cue_hits=cue_hits,
        bm25_hits=bm25_hits,
        expansion_hits=expansion_hits,
        error=error,
    )


# --- Tests ---


def test_emit_one_event_returns_summary_with_one_call() -> None:
    """1 개 emit 후 summary.total_calls=1, selected_count=0 이면 miss (hit=False)."""
    with tempfile.TemporaryDirectory() as td:
        ws = Path(td)
        append_telemetry_event(ws, _make_event(source="session-start", selected_count=0))
        summary = summarize_telemetry(ws)
        assert summary.total_calls == 1, f"got {summary.total_calls}"
        assert summary.total_hits == 0, "miss event 는 hit 으로 카운트 ❌"
        assert summary.hit_rate == 0.0, "miss 1 건이므로 hit_rate=0.0"
        assert "session-start" in summary.by_source
        assert summary.by_source["session-start"] == {"calls": 1, "hits": 0}
        assert summary.events_parsed == 1
        assert summary.events_skipped == 0
        assert summary.first_event_at != ""
        assert summary.last_event_at != ""


def test_two_hits_one_miss_hit_rate_two_thirds() -> None:
    """2 hit + 1 miss → total=3, hits=2, hit_rate=2/3 (error flag 는 hit 카운트 제외)."""
    with tempfile.TemporaryDirectory() as td:
        ws = Path(td)
        append_telemetry_event(ws, _make_event(source="session-start", selected_count=2))  # hit
        append_telemetry_event(ws, _make_event(source="session-start", selected_count=0))  # miss
        append_telemetry_event(ws, _make_event(source="doc-sync", selected_count=1, error=True))  # error: not hit
        summary = summarize_telemetry(ws)
        assert summary.total_calls == 3, f"got {summary.total_calls}"
        # error=True event 는 selected_count 와 무관하게 hit 카운트 ❌ (정공법: error 는 negative example)
        assert summary.total_hits == 1, f"got {summary.total_hits}"
        # 1/3 정확도 (오차 < 1e-9)
        assert abs(summary.hit_rate - (1 / 3)) < 1e-9, f"got {summary.hit_rate}"


def test_by_source_breakdown_distinguishes_skills() -> None:
    """session-start 2 calls (1 hit) + doc-sync 1 call (1 hit) → by_source 분해 정확."""
    with tempfile.TemporaryDirectory() as td:
        ws = Path(td)
        append_telemetry_event(ws, _make_event(source="session-start", selected_count=1))
        append_telemetry_event(ws, _make_event(source="session-start", selected_count=0))
        append_telemetry_event(ws, _make_event(source="doc-sync", selected_count=3))
        summary = summarize_telemetry(ws)
        assert summary.by_source == {
            "session-start": {"calls": 2, "hits": 1},
            "doc-sync": {"calls": 1, "hits": 1},
        }, f"got {summary.by_source}"


def test_malformed_jsonl_line_is_skipped() -> None:
    """기존 telemetry file 에 malformed line 직접 추가 시 skip + events_skipped 증가."""
    with tempfile.TemporaryDirectory() as td:
        ws = Path(td)
        append_telemetry_event(ws, _make_event(source="session-start", selected_count=1))
        # malformed line 2 개 삽입
        tp = telemetry_path(ws)
        with tp.open("a", encoding="utf-8") as fp:
            fp.write('{"this is not valid json\n')
            fp.write('not-json-at-all\n')
        summary = summarize_telemetry(ws)
        assert summary.events_parsed == 1, f"valid line 1개만 parse: got {summary.events_parsed}"
        assert summary.events_skipped == 2, f"malformed 2개 skip: got {summary.events_skipped}"
        assert summary.total_calls == 1
        # read_telemetry_events 도 동일하게 skip
        events = read_telemetry_events(ws)
        assert len(events) == 1


def test_workspace_root_absent_returns_empty_summary() -> None:
    """telemetry dir 부재 시 graceful zero summary (no raise)."""
    with tempfile.TemporaryDirectory() as td:
        ws = Path(td) / "non_existent"
        summary = summarize_telemetry(ws)
        assert summary.total_calls == 0
        assert summary.total_hits == 0
        assert summary.hit_rate == 0.0
        assert summary.by_source == {}
        assert summary.first_event_at == ""
        assert summary.last_event_at == ""
        assert summary.events_skipped == 0
        assert summary.events_parsed == 0


def test_concurrent_append_preserves_all_lines() -> None:
    """2 thread 동시 emit → 2 line 모두 보존 (in-process lock 정합).

    cross-process 동시성은 best-effort (open("a") + write + flush 의 OS-level
    atomicity 가정, consumer_metrics.py 의 JSONL append 와 동일 정공법).
    """
    with tempfile.TemporaryDirectory() as td:
        ws = Path(td)

        def worker(source: str) -> None:
            for _ in range(5):
                append_telemetry_event(ws, _make_event(source=source, selected_count=1))

        t1 = threading.Thread(target=worker, args=("session-start",))
        t2 = threading.Thread(target=worker, args=("doc-sync",))
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        # 10 events total (5 + 5)
        events = read_telemetry_events(ws)
        assert len(events) == 10, f"expected 10 events, got {len(events)}"
        summary = summarize_telemetry(ws)
        assert summary.total_calls == 10
        assert summary.total_hits == 10  # all hits
        assert summary.by_source == {
            "session-start": {"calls": 5, "hits": 5},
            "doc-sync": {"calls": 5, "hits": 5},
        }


# --- 메인 실행 ---


def main() -> int:
    test_funcs = [
        test_emit_one_event_returns_summary_with_one_call,
        test_two_hits_one_miss_hit_rate_two_thirds,
        test_by_source_breakdown_distinguishes_skills,
        test_malformed_jsonl_line_is_skipped,
        test_workspace_root_absent_returns_empty_summary,
        test_concurrent_append_preserves_all_lines,
    ]
    failures: list[tuple[str, str]] = []
    for func in test_funcs:
        try:
            func()
            print(f"  PASS: {func.__name__}")
        except AssertionError as e:
            failures.append((func.__name__, f"AssertionError: {e}"))
            print(f"  FAIL: {func.__name__} — {e}")
        except Exception as e:
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
