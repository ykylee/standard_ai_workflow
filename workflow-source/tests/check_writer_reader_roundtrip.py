"""생성물마다 **쓴 코드와 읽는 코드를 실제로 붙여본다** (v1.0.1+).

## 왜 필요한가

한 사이클에 같은 모양의 결함이 세 번 나왔다 — *같은 사실이 두 곳에 있는데 둘을
이어주는 기계적 장치가 없다*:

| 사례 | 두 곳 | 왜 기존 테스트가 못 잡았나 |
|---|---|---|
| north-star 지표 | 정의(wiki) ↔ 구현 | proxy 를 north-star 자리에 앉혀도 타입은 맞다 |
| `state.json` | writer 경로 ↔ reader 경로 | 각자 자기 경로에서 정상 동작, **서로 만나지 않는다** |
| task ID 정규식 | 4곳에 복제 | 각 정규식이 자기 테스트를 통과한다 |

공통점은 **부품별 테스트는 전부 green 인데 조립하면 안 맞는다**는 것이다. 그래서 본
smoke 는 단언을 하나로 통일한다: *프로덕션 writer 로 쓰고 **프로덕션 reader 로 되읽어
같은 것이 나오는가***.

> **테스트가 fixture 를 손으로 써 두면 이 결함을 못 잡는다.** 손으로 쓴 fixture 는
> reader 의 기대에 맞춰져 있어서, writer 가 딴 데다 쓰고 있어도 통과한다. 반드시
> 실제 writer 를 호출해야 한다.

Test list (7 pair):
1. state.json          — refresh_workflow_state_cache      → workflow_state_path + json
2. daily index / task  — upsert_backlog_entry              → parse_backlog_task_entries
3. append-only 집계    — upsert_backlog_entry              → builder aggregate
4. maturity 선언       — refresh_maturity_last_updated     → collect_drift_prevention
5. drift 원장          — _append_drift_ledger_entry        → collect_silent_failing_cycles
6. telemetry           — append_telemetry_event            → summarize_telemetry
7. session handoff     — sync_handoff_status               → parse_handoff

Cross-ref: releases/Beta-v1.0.0.md §2.19~§2.21 (세 사례) .
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SOURCE_ROOT))
sys.path.insert(0, str(SOURCE_ROOT / "tools"))

from workflow_kit.common.dashboard_data import (  # noqa: E402
    collect_drift_prevention,
    collect_silent_failing_cycles,
)
from workflow_kit.common.paths import workflow_state_path  # noqa: E402
from workflow_kit.common.project_docs import (  # noqa: E402
    parse_backlog_task_entries,
    parse_handoff,
)
from workflow_kit.common.schemas.memory_index import (  # noqa: E402
    MemoryEntry,
    MemoryIndexTelemetryEvent,
)
from workflow_kit.common.state.builder import _aggregate_from_appendonly_layout  # noqa: E402
from workflow_kit.common.state.cache import refresh_maturity_last_updated  # noqa: E402
from workflow_kit.common.state.memory_index import (  # noqa: E402
    append_telemetry_event,
    load_memory_index,
    save_memory_entry,
    summarize_telemetry,
)
from workflow_kit.common.workflow_state import refresh_workflow_state_cache  # noqa: E402
from workflow_kit.common.workflow_writes import (  # noqa: E402
    sync_handoff_status,
    upsert_backlog_entry,
)

BRANCH = "roundtrip-smoke"


def _workspace(td: str) -> Path:
    """docs/PROJECT_PROFILE.md + branch-scoped 메모리 layout 을 갖춘 temp workspace."""
    ws = Path(td)
    (ws / "docs").mkdir(parents=True)
    (ws / "docs" / "PROJECT_PROFILE.md").write_text("# Profile\n", encoding="utf-8")
    base = ws / "ai-workflow" / "memory" / "active" / BRANCH
    (base / "backlog" / "tasks").mkdir(parents=True)
    (base / "sessions").mkdir(parents=True)
    # 이미 갱신돼 온 state.json 이 **있는** 상태를 재현한다. 빈 저장소에서는 writer 가
    # legacy 경로에 써도 reader 의 fallback 이 같은 파일을 집어 우연히 일치해버린다 —
    # 실제 저장소(추적 중인 branch-scoped 파일이 존재)와 다른 상황이라 결함을 놓친다.
    (base / "state.json").write_text('{"generated_at": "2026-01-01"}\n', encoding="utf-8")
    return ws


def _branch_dir(ws: Path) -> Path:
    return ws / "ai-workflow" / "memory" / "active" / BRANCH


def _with_branch(fn):
    def wrapper() -> None:
        before = os.environ.get("CODEX_WORKFLOW_BRANCH")
        os.environ["CODEX_WORKFLOW_BRANCH"] = BRANCH
        try:
            fn()
        finally:
            if before is None:
                os.environ.pop("CODEX_WORKFLOW_BRANCH", None)
            else:
                os.environ["CODEX_WORKFLOW_BRANCH"] = before
    wrapper.__name__ = fn.__name__
    return wrapper


def _write_task(ws: Path, *, task_id: str, title: str, status: str) -> Path:
    backlog_path = _branch_dir(ws) / "backlog" / "2026-07-22.md"
    upsert_backlog_entry(
        backlog_path=backlog_path,
        task_id=task_id,
        entry_lines=[
            "---",
            f"id: {task_id}",
            f"status: {status}",
            "created_at: 2026-07-22",
            "source_anchor: roundtrip",
            "source_path: backlog/2026-07-22.md",
            "kind: generic",
            "---",
            "",
            f"# {task_id} — {title}",
            "",
            f"- 상태: {status}",
        ],
        title=title,
        kind="generic",
        status=status,
    )
    return backlog_path


# --- Round-trip pairs ---


@_with_branch
def test_state_json_write_then_read() -> None:
    """writer 가 쓴 state.json 을 reader 가 *같은 경로에서* 읽는다."""
    with tempfile.TemporaryDirectory() as td:
        ws = _workspace(td)
        profile = ws / "docs" / "PROJECT_PROFILE.md"
        result = refresh_workflow_state_cache(
            project_profile_path=profile, generated_at="2026-07-22",
        )
        assert result["status"] == "refreshed", result
        read_path = workflow_state_path(profile)
        assert read_path.exists(), f"reader 가 보는 경로에 파일이 없다: {read_path}"
        assert Path(result["state_path"]) == read_path.resolve(), (
            f"writer 가 쓴 곳 {result['state_path']} ≠ reader 가 읽는 곳 {read_path}"
        )
        read_back = json.loads(read_path.read_text(encoding="utf-8"))["generated_at"]
        assert read_back == "2026-07-22", (
            f"reader 가 갱신 전 값을 읽고 있다: {read_back} (writer 는 2026-07-22 를 썼다)"
        )


@_with_branch
def test_backlog_write_then_parse() -> None:
    """daily index 에 쓴 task 를 backlog reader 가 되찾는다 (link 를 따라 본문까지)."""
    with tempfile.TemporaryDirectory() as td:
        ws = _workspace(td)
        task_id = f"TASK-2026-07-22-{BRANCH}-001"
        backlog_path = _write_task(ws, task_id=task_id, title="왕복 검증", status="in_progress")
        tasks = parse_backlog_task_entries(backlog_path)
        assert [t["task_id"] for t in tasks] == [task_id], tasks
        assert tasks[0]["status"] == "in_progress", tasks[0]


@_with_branch
def test_backlog_write_then_state_aggregate() -> None:
    """builder 의 집계가 writer 산출물에서 task 를 본다 (state.json 의 실제 source)."""
    with tempfile.TemporaryDirectory() as td:
        ws = _workspace(td)
        done_id = f"TASK-2026-07-22-{BRANCH}-001"
        wip_id = f"TASK-2026-07-22-{BRANCH}-002"
        _write_task(ws, task_id=done_id, title="완료된 것", status="done")
        _write_task(ws, task_id=wip_id, title="진행 중인 것", status="in_progress")
        base = _branch_dir(ws)
        agg = _aggregate_from_appendonly_layout(
            daily_backlog_dir=base / "backlog",
            tasks_dir=base / "backlog" / "tasks",
            sessions_dir=base / "sessions",
        )
        assert done_id in agg["done_items"], agg
        assert wip_id in agg["in_progress_items"], agg
        assert any("완료된 것" in s for s in agg["recent_done_items"]), agg["recent_done_items"]


def test_maturity_write_then_panel_read() -> None:
    """refresh 가 쓴 last_updated 를 Panel 1 collector 가 그대로 읽는다."""
    with tempfile.TemporaryDirectory() as td:
        ws = Path(td)
        matrix = ws / "workflow-source" / "core" / "maturity_matrix.json"
        matrix.parent.mkdir(parents=True)
        matrix.write_text(json.dumps({"last_updated": "2026-01-01"}), encoding="utf-8")
        written = refresh_maturity_last_updated(matrix, today="2026-07-22")
        assert written["updated"] is True, written
        panel = collect_drift_prevention(ws, inline_guard=False)
        assert panel["maturity_last_updated"] == "2026-07-22", panel


def test_drift_ledger_write_then_north_star_read() -> None:
    """release pipeline 이 append 한 원장을 dashboard 가 세어 north-star 를 낸다."""
    from release_pipeline import _append_drift_ledger_entry

    with tempfile.TemporaryDirectory() as td:
        ws = Path(td)
        args = argparse.Namespace(dry_run=False, version="v1.0.1", workspace_root=str(ws))
        clean = _append_drift_ledger_entry(args, {"recovered": [], "manual_required": [],
                                                  "re_check": {"guard_status": "pass"}})
        assert clean["status"] == "ok", clean
        dirty = _append_drift_ledger_entry(args, {"recovered": [], "manual_required": ["case_x"],
                                                  "re_check": {"guard_status": "fail"}})
        assert dirty["status"] == "ok", dirty

        north_star = collect_silent_failing_cycles(ws)
        assert north_star["measured_cycles"] == 2, north_star
        assert north_star["count"] == 1, north_star
        assert north_star["measured"] is True


def test_telemetry_write_then_summarize() -> None:
    """emit 한 telemetry event 를 summarize 가 by_source 로 집계한다."""
    with tempfile.TemporaryDirectory() as td:
        ws = Path(td)
        append_telemetry_event(ws, MemoryIndexTelemetryEvent(
            timestamp=datetime.now(timezone.utc),
            source="roundtrip",
            workspace_root=str(ws),
            query_tokens_count=2,
            selected_count=1,
        ))
        summary = summarize_telemetry(ws)
        assert summary.total_calls == 1, summary
        assert "roundtrip" in summary.by_source, summary.by_source


def test_memory_entry_write_then_load() -> None:
    """save_memory_entry 가 쓴 entry 를 load_memory_index 가 되읽는다."""
    with tempfile.TemporaryDirectory() as td:
        ws = Path(td)
        now = datetime.now(timezone.utc)
        entry = MemoryEntry(
            id="MEM-2026-07-22-001",
            primary_abstraction="writer reader roundtrip contract",
            cue_anchors=["roundtrip"],
            created_at=now,
            updated_at=now,
        )
        save_memory_entry(ws, entry)
        loaded = load_memory_index(ws)
        assert [e.id for e in loaded] == ["MEM-2026-07-22-001"], loaded


def test_handoff_write_then_parse() -> None:
    """sync_handoff_status 가 옮긴 task 를 handoff parser 가 같은 상태로 읽는다."""
    with tempfile.TemporaryDirectory() as td:
        ws = Path(td)
        handoff = ws / "session_handoff.md"
        handoff.write_text(
            "# 세션 인계 문서\n\n"
            "- 현재 기준선: baseline\n"
            "- 현재 주 작업 축: axis\n"
            "- 현재 `in_progress` 작업:\n"
            "- TASK-001 이전 작업\n"
            "- 현재 `blocked` 작업:\n"
            "- \n"
            "- 최근 완료 작업 목록:\n"
            "- \n",
            encoding="utf-8",
        )
        sync_handoff_status(handoff_path=handoff, task_label="TASK-002 막힌 작업", status="blocked")
        parsed = parse_handoff(handoff)
        assert "TASK-002 막힌 작업" in parsed["blocked_items"], parsed["blocked_items"]


def main() -> int:
    test_funcs = [
        test_state_json_write_then_read,
        test_backlog_write_then_parse,
        test_backlog_write_then_state_aggregate,
        test_maturity_write_then_panel_read,
        test_drift_ledger_write_then_north_star_read,
        test_telemetry_write_then_summarize,
        test_memory_entry_write_then_load,
        test_handoff_write_then_parse,
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
