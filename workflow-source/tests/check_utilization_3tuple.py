"""memory_index 지표 재정의 3-tuple smoke (ADR-006 W-4, TASK-2026-08-10-main-014).

hit_rate 단독 지표는 33일간 1.0 으로 고정돼 정보가 없었고 소비자 결함(패널
반올림 불일치)까지 숨겼다. W-4 는 north-star 를 **(질의 다양성 / 30일 신규
entry / 조회된 distinct entry)** 3-tuple 로 교체하고 hit_rate 는 보조로
강등한다. 측정 불가(구 라인)는 `*_measurable` 분모로 0 과 구분한다.

검증 케이스 (9):
    1. telemetry selected_ids roundtrip — 필드 존재가 read 후에도 보존
    2. 구 라인 (필드 부재) → measurable 0 (미측정이 0 으로 위장하지 않는다)
    3. **miss 도 측정이다** — 명시적 `selected_ids: []` → measurable 1 / distinct 0
       (되주입 겸용: measurable 판정을 값-비어있음으로 되돌리면 여기서 잡힌다)
    4. query_diversity — distinct 질의 내용 수 (중복 질의는 1 로)
    5. distinct_entries_retrieved — event 간 selected_ids 합집합
    6. Panel 8 — utilization_3tuple 필드 + summarize 값 정합
    7. entries_new_30d — 30일 경계 (오래된 entry 제외)
    8. north-star 교체 — phase_15_north_star 가 3-tuple 을 가리키고 hit_rate 는
       보조로 명시 (항상 1.0 이던 지표의 강등을 문자열로 고정)
    9. hit_rate 는 유지된다 (은퇴가 아니라 강등 — 기존 소비자 하위호환)

Stdlib only.
"""

from __future__ import annotations

#: 이 검사의 입력 표면 (spec `core/test_impact_tiering_spec.md` §2).
#: 게이트 채취 실측에서 뽑아 넓은 쪽으로 올렸다 — 좁으면 meta-watch 가 red 로 잡는다.
WATCHES = (
    "workflow-source/pyproject.toml",
    "workflow-source/workflow_kit/*",
)

import json
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from workflow_kit.common.dashboard_data import (  # noqa: E402
    collect_memory_index_utilization_v2,
)
from workflow_kit.common.schemas.memory_index import (  # noqa: E402
    MemoryIndexTelemetryEvent,
)
from workflow_kit.common.state.memory_index import (  # noqa: E402
    append_telemetry_event,
    read_telemetry_events,
    summarize_telemetry,
    telemetry_path,
)

NOW = datetime.now(timezone.utc)


def _raw_line(ws: Path, payload: dict[str, object]) -> None:
    """구 형식 라인을 raw 로 append (신규 필드 key 자체가 없는 상태 재현)."""
    tp = telemetry_path(ws)
    tp.parent.mkdir(parents=True, exist_ok=True)
    with tp.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload) + "\n")


def _write_entry(ws: Path, entry_id: str, created_at: str) -> None:
    ed = ws / "ai-workflow" / "memory" / "active" / "memory_index" / "entries"
    ed.mkdir(parents=True, exist_ok=True)
    (ed / f"{entry_id}.json").write_text(json.dumps({
        "id": entry_id, "primary_abstraction": f"abstraction {entry_id}",
        "created_at": created_at, "updated_at": created_at,
    }), encoding="utf-8")


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

        # 구 라인 2개 (query_tokens / selected_ids key 부재)
        _raw_line(ws, {"timestamp": "2026-07-09T00:00:00Z", "source": "session-start",
                       "query_tokens_count": 3, "selected_count": 1, "cue_hits": 1})
        _raw_line(ws, {"timestamp": "2026-07-10T00:00:00Z", "source": "backlog-update",
                       "query_tokens_count": 3, "selected_count": 1, "cue_hits": 1})

        # 신 라인 3개 — miss 1 (selected_ids=[] 명시) + hit 2 (중복 질의 1쌍)
        append_telemetry_event(ws, MemoryIndexTelemetryEvent(
            timestamp=NOW, source="session-start",
            query_tokens_count=2, query_tokens=["alpha", "beta"],
            query_source="context", selected_count=0, selected_ids=[],
        ))
        append_telemetry_event(ws, MemoryIndexTelemetryEvent(
            timestamp=NOW, source="doc-sync",
            query_tokens_count=2, query_tokens=["alpha", "beta"],
            query_source="context", selected_count=2,
            selected_ids=["MEM-2026-01-01-001", "MEM-2026-01-01-002"], cue_hits=2,
        ))
        append_telemetry_event(ws, MemoryIndexTelemetryEvent(
            timestamp=NOW, source="dispatcher",
            query_tokens_count=1, query_tokens=["gamma"],
            query_source="explicit", selected_count=2,
            selected_ids=["MEM-2026-01-01-002", "MEM-2026-01-01-003"], cue_hits=1,
        ))

        events = read_telemetry_events(ws)
        summary = summarize_telemetry(ws)

        # 1) roundtrip — read 후에도 필드 존재/값 보존
        new_events = [e for e in events if "selected_ids" in e.model_fields_set]
        check(
            "1) selected_ids roundtrip (필드 존재 보존)",
            len(events) == 5 and len(new_events) == 3
            and new_events[1].selected_ids == ["MEM-2026-01-01-001", "MEM-2026-01-01-002"],
            f"events={len(events)} new={len(new_events)}",
        )

        # 2) 구 라인 → measurable 분모에서 제외
        check(
            "2) 구 라인은 measurable 에 안 잡힌다",
            summary.query_diversity_measurable == 3 and summary.selected_ids_measurable == 3,
            f"q_meas={summary.query_diversity_measurable} s_meas={summary.selected_ids_measurable}",
        )

        # 3) miss 도 측정 — selected_ids=[] 명시 라인이 measurable 에 포함
        #    (되주입 검출: 판정을 `if e.selected_ids` 로 되돌리면 measurable 2 가 된다)
        miss_line_counted = summary.selected_ids_measurable == 3
        check(
            "3) miss (selected_ids=[]) 도 측정으로 센다",
            miss_line_counted,
            f"selected_ids_measurable={summary.selected_ids_measurable} (기대 3 = hit 2 + miss 1)",
        )

        # 4) query_diversity — [alpha,beta] 중복 1쌍 + [gamma] → 2
        check(
            "4) query_diversity (중복 질의는 1)",
            summary.query_diversity == 2,
            f"diversity={summary.query_diversity}",
        )

        # 5) distinct union — {001, 002, 003} = 3
        check(
            "5) distinct_entries_retrieved (합집합)",
            summary.distinct_entries_retrieved == 3,
            f"distinct={summary.distinct_entries_retrieved}",
        )

        # 6~9) Panel 8
        _write_entry(ws, "MEM-2026-01-01-001", "2026-01-01T00:00:00Z")  # 오래됨
        recent = (NOW - timedelta(days=3)).strftime("%Y-%m-%dT%H:%M:%SZ")
        _write_entry(ws, "MEM-2026-08-08-001", recent)                   # 최근
        p8 = collect_memory_index_utilization_v2(ws)
        t3 = p8.get("utilization_3tuple", {})

        check(
            "6) Panel 8 — 3-tuple 이 summarize 값과 정합",
            t3.get("query_diversity") == summary.query_diversity
            and t3.get("distinct_entries_retrieved") == summary.distinct_entries_retrieved
            and t3.get("selected_ids_measurable") == summary.selected_ids_measurable,
            f"t3={t3}",
        )

        check(
            "7) entries_new_30d — 30일 경계 (2 중 1)",
            t3.get("entries_new_30d") == 1 and p8.get("entries_total") == 2,
            f"new_30d={t3.get('entries_new_30d')} total={p8.get('entries_total')}",
        )

        north = str(p8.get("phase_15_north_star", ""))
        check(
            "8) north-star 교체 — 3-tuple 명시 + hit_rate 보조 강등",
            "utilization_3tuple" in north and "hit_rate" in north and "보조" in north,
            f"north={north!r}",
        )

        check(
            "9) hit_rate 필드는 유지 (기존 소비자 하위호환)",
            isinstance(p8.get("telemetry_hit_rate"), float)
            and 0.0 <= p8["telemetry_hit_rate"] <= 1.0,
            f"hit_rate={p8.get('telemetry_hit_rate')!r}",
        )

    total = 9
    print()
    if failures:
        print(f"{total - len(failures)}/{total} PASS — FAILED: {failures}")
        return 1
    print(f"{total}/{total} PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
