"""telemetry 윈도 지표 smoke (TASK-2026-08-09-main-011, Phase 13 AC2 후속)

전체 기간 `by_source` 는 **각 경로를 한 번씩만 돌려도** 4 source 가 찬다.
2026-08-09 P0-2 가 실제로 그렇게 충족됐고, 그래서 그 숫자는 *지속적 사용* 을
재지 못한다. 윈도 지표는 방치하면 값이 떨어지므로 "지금도 쓰이는가" 를 묻는다.

검증 케이스 (8):
    1. 전체 기간 필드는 그대로다 (기존 소비자 정합 — additive)
    2. 윈도 밖 event 는 `window_*` 에서 빠진다
    3. 윈도 안 event 만으로 `window_source_count` 가 계산된다
    4. **핵심**: 오래된 4 source + 최근 1 source → 전체는 4, 윈도는 1
       (= P0-2 acceptance 가 못 잡던 상황을 윈도는 잡는다)
    5. `window_days=0` → 윈도 집계 생략 (필드는 0)
    6. `window_hit_rate` 는 윈도 안에서만 계산된다
    7. naive timestamp 도 UTC 로 간주해 비교가 터지지 않는다
    8. event 부재 → 전부 0, 예외 없음

Stdlib only (+ 저장소 schema).
"""

from __future__ import annotations

import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from workflow_kit.common.schemas.memory_index import (  # noqa: E402
    MemoryIndexTelemetryEvent,
)
from workflow_kit.common.state.memory_index import (  # noqa: E402
    append_telemetry_event,
    summarize_telemetry,
)

NOW = datetime(2026, 8, 9, 12, 0, 0, tzinfo=timezone.utc)


def _event(source: str, *, days_ago: float, selected: int = 1) -> MemoryIndexTelemetryEvent:
    return MemoryIndexTelemetryEvent(
        timestamp=NOW - timedelta(days=days_ago),
        source=source,
        workspace_root="/tmp/ws",
        query_tokens_count=2,
        selected_count=selected,
    )


def main() -> int:
    failures: list[str] = []

    def check(label: str, cond: bool, detail: str = "") -> None:
        if cond:
            print(f"PASS: {label}")
        else:
            print(f"FAIL: {label} — {detail}")
            failures.append(label)

    with tempfile.TemporaryDirectory() as td:
        ws = Path(td)
        # 오래된 것 3 source (60일 전) + 최근 1 source (2일 전)
        for src in ("doc-sync", "backlog-update", "dispatcher"):
            append_telemetry_event(ws, _event(src, days_ago=60))
        append_telemetry_event(ws, _event("session-start", days_ago=2))

        s30 = summarize_telemetry(ws, window_days=30, now=NOW)

        # 1) 전체 기간 필드 불변
        check(
            "1) 전체 기간 필드는 그대로 (additive)",
            s30.total_calls == 4 and len(s30.by_source) == 4 and s30.hit_rate == 1.0,
            f"total={s30.total_calls} sources={sorted(s30.by_source)}",
        )

        # 2~4) 윈도가 오래된 것을 걸러낸다 — P0-2 가 못 잡던 상황
        check(
            "2) 윈도 밖 event 제외",
            s30.window_calls == 1,
            f"window_calls={s30.window_calls}",
        )
        check(
            "3) window_source_count 는 윈도 안 기준",
            s30.window_source_count == 1 and set(s30.window_by_source) == {"session-start"},
            f"count={s30.window_source_count} sources={sorted(s30.window_by_source)}",
        )
        check(
            "4) 전체 4 source 인데 윈도는 1 — acceptance 갭을 잡는다",
            len(s30.by_source) == 4 and s30.window_source_count == 1,
            f"total_sources={len(s30.by_source)} window={s30.window_source_count}",
        )

        # 5) window_days=0 → 생략
        s0 = summarize_telemetry(ws, window_days=0, now=NOW)
        check(
            "5) window_days=0 → 윈도 집계 생략",
            s0.window_days == 0 and s0.window_calls == 0 and s0.window_source_count == 0,
            f"{s0.window_days}/{s0.window_calls}/{s0.window_source_count}",
        )

        # 6) window_hit_rate 는 윈도 안에서만
        append_telemetry_event(ws, _event("doc-sync", days_ago=1, selected=0))  # miss
        s_hit = summarize_telemetry(ws, window_days=30, now=NOW)
        check(
            "6) window_hit_rate 는 윈도 안에서만 계산",
            s_hit.window_calls == 2 and s_hit.window_hits == 1 and s_hit.window_hit_rate == 0.5,
            f"calls={s_hit.window_calls} hits={s_hit.window_hits} rate={s_hit.window_hit_rate}",
        )

        # 90일 윈도면 전부 들어온다 — 경계가 실제로 동작하는지
        s90 = summarize_telemetry(ws, window_days=90, now=NOW)
        check(
            "6b) 윈도를 넓히면 오래된 것도 들어온다",
            s90.window_source_count == 4 and s90.window_calls == 5,
            f"count={s90.window_source_count} calls={s90.window_calls}",
        )

    # 7) naive timestamp 도 터지지 않는다
    with tempfile.TemporaryDirectory() as td:
        ws = Path(td)
        naive = MemoryIndexTelemetryEvent(
            timestamp=datetime(2026, 8, 8, 12, 0, 0),  # tz 없음
            source="session-start",
            workspace_root="/tmp/ws",
            query_tokens_count=1,
            selected_count=1,
        )
        append_telemetry_event(ws, naive)
        try:
            s = summarize_telemetry(ws, window_days=30, now=NOW)
            ok = s.window_calls in (0, 1)  # 해석은 UTC — 어느 쪽이든 예외만 아니면 된다
        except TypeError as e:
            ok = False
            print(f"       naive 비교에서 TypeError: {e}")
        check("7) naive timestamp 도 비교가 터지지 않는다", ok, "")

    # 8) event 부재
    with tempfile.TemporaryDirectory() as td:
        s = summarize_telemetry(Path(td), window_days=30, now=NOW)
        check(
            "8) event 부재 → 전부 0, 예외 없음",
            s.total_calls == 0 and s.window_calls == 0 and s.window_hit_rate == 0.0,
            f"{s.total_calls}/{s.window_calls}",
        )

    total = 8
    print()
    if failures:
        print(f"{total - len(failures)}/{total} PASS — FAILED: {failures}")
        return 1
    print(f"{total}/{total} PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
