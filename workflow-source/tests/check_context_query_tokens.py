"""memory_index 컨텍스트 유래 질의 token smoke (ADR-006 W-2, TASK-2026-08-10-main-012).

회고 실측: 3 skill 의 질의는 각자 고정 trio 였고 공통 token "workflow" 가
항상 같은 entry 를 집어 33일간 질의 다양성이 1 이었다. W-2 는 (1) state.json
의 current_axis + 최근 done 제목에서 질의 token 을 유도하고 (실패 시 기존
default 로 떨어지되 출처 보고), (2) telemetry 에 질의 *내용*(`query_tokens`)
과 출처(`query_source`)를 additive 로 남겨 다양성을 측정 가능하게 한다.

검증 케이스 (8):
    1. axis + done_items → context token 유도, source="context"
    2. state 부재 → base default + source="default"
    3. state JSON 깨짐 → default (조용히, 그러나 출처는 보고)
    4. 위생 — stopword("task"/"main")·숫자 제거, dedupe, cap 8
    5. 유의미 token 없음 (빈 axis/done) → default
    6. telemetry 하위호환 — 구 라인 (신규 2 필드 없음) parse → 기본값
    7. telemetry roundtrip — 신규 필드 append → read back 일치
    8. 되주입 — state 내용을 바꾸면 token 이 따라 바뀐다 (실제로 state 를
       읽는다는 증명)

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
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from workflow_kit.common.schemas.memory_index import (  # noqa: E402
    MemoryIndexTelemetryEvent,
)
from workflow_kit.common.state.memory_index import (  # noqa: E402
    QUERY_SOURCE_CONTEXT,
    QUERY_SOURCE_DEFAULT,
    append_telemetry_event,
    derive_context_query_tokens,
    read_telemetry_events,
)

BASE = ["session", "handoff", "workflow"]


def _write_state(path: Path, axis: object, done_items: object) -> None:
    path.write_text(json.dumps({
        "session": {"current_axis": axis},
        "backlog": {"done_items": done_items},
    }, ensure_ascii=False), encoding="utf-8")


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
        state = ws / "state.json"

        # 1) 정상 유도
        _write_state(state, "registry federation 정공법 사이클", [
            "TASK-2026-01-05-main-001 — telemetry 윈도 재설계",
        ])
        tokens, source = derive_context_query_tokens(state, base_tokens=BASE)
        check(
            "1) axis + done → context 유도",
            source == QUERY_SOURCE_CONTEXT
            and "registry" in tokens and "federation" in tokens and "telemetry" in tokens,
            f"source={source} tokens={tokens}",
        )

        # 2) state 부재 → default
        tokens2, source2 = derive_context_query_tokens(ws / "no-such.json", base_tokens=BASE)
        check(
            "2) state 부재 → base + default",
            tokens2 == BASE and source2 == QUERY_SOURCE_DEFAULT,
            f"source={source2} tokens={tokens2}",
        )

        # 3) JSON 깨짐 → default
        broken = ws / "broken.json"
        broken.write_text("{not json", encoding="utf-8")
        tokens3, source3 = derive_context_query_tokens(broken, base_tokens=BASE)
        check(
            "3) state 깨짐 → base + default",
            tokens3 == BASE and source3 == QUERY_SOURCE_DEFAULT,
            f"source={source3} tokens={tokens3}",
        )

        # 4) 위생 — stopword/숫자 제거, dedupe, cap
        _write_state(state, "task main 2026 08 alpha alpha beta gamma delta epsilon zeta eta theta", [])
        tokens4, source4 = derive_context_query_tokens(state, base_tokens=BASE)
        check(
            "4) 위생 — stopword·숫자 제거 + dedupe + cap 8",
            source4 == QUERY_SOURCE_CONTEXT
            and "task" not in tokens4 and "main" not in tokens4 and "2026" not in tokens4
            and tokens4.count("alpha") == 1 and len(tokens4) <= 8,
            f"tokens={tokens4}",
        )

        # 5) 유의미 token 없음 → default
        _write_state(state, "", [])
        tokens5, source5 = derive_context_query_tokens(state, base_tokens=BASE)
        check(
            "5) 유의미 token 없음 → base + default",
            tokens5 == BASE and source5 == QUERY_SOURCE_DEFAULT,
            f"source={source5} tokens={tokens5}",
        )

        # 6) telemetry 하위호환 — 구 라인 (신규 필드 없음)
        legacy = MemoryIndexTelemetryEvent.model_validate({
            "timestamp": "2026-07-09T00:00:00Z",
            "source": "session-start",
            "query_tokens_count": 3,
        })
        check(
            "6) telemetry 구 라인 → query_tokens=[] / query_source=\"\"",
            legacy.query_tokens == [] and legacy.query_source == "",
            f"tokens={legacy.query_tokens!r} source={legacy.query_source!r}",
        )

        # 7) telemetry roundtrip
        append_telemetry_event(ws, MemoryIndexTelemetryEvent(
            timestamp=datetime(2026, 1, 5, tzinfo=timezone.utc),
            source="session-start",
            query_tokens_count=2,
            query_tokens=["registry", "federation"],
            query_source=QUERY_SOURCE_CONTEXT,
        ))
        events = read_telemetry_events(ws)
        check(
            "7) telemetry roundtrip — 신규 필드 보존",
            len(events) == 1
            and events[0].query_tokens == ["registry", "federation"]
            and events[0].query_source == QUERY_SOURCE_CONTEXT,
            f"events={[(e.query_tokens, e.query_source) for e in events]}",
        )

        # 8) 되주입 — state 내용이 결과를 결정한다
        _write_state(state, "완전히 다른 축 mavis attach", [])
        tokens8, _ = derive_context_query_tokens(state, base_tokens=BASE)
        check(
            "8) 되주입 — state 내용 변경 → token 변경",
            "mavis" in tokens8 and "registry" not in tokens8,
            f"tokens={tokens8}",
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
