"""`state.json.session.recent_done_items` 의 **순서와 상한** 계약 (v1.0.3).

## 왜 필요한가

이 필드는 "최근 완료 작업"을 표방하는데, 실제로는 *어느 기준으로도 최신을 고르지
않았다*. 조립된 목록은

    tasks_dir(ID 사전순)  ++  daily index 잔여분(파일 날짜순)

이었고, aggregate 가 `[-10:]` 로 **뒤** 10개를, builder 가 다시 `[:10]` 로 **앞** 10개를
잘랐다. 두 slice 의 방향이 반대라 서로를 무효화했고, 뒤에 붙는 daily 잔여분이 하필
저장소에서 가장 오래된 task 들이라 **최신 4건이 밀려나고 2026-04-24 항목이 최신 자리에
앉았다** (실측: `TASK-2026-07-22-003` 이 목록에서 사라짐).

같은 경로에 두 번째 결함이 있었다. daily index fallback 은 `done/in_progress/blocked`
어느 목록에도 없는 ID 를 **무조건 done 으로** 되살렸다. 그래서 어휘 밖의 status
(`status: recorded` 3건) 를 가진 task 가 완료로 보고됐다 — task 파일이 SSOT 인데
파생물인 daily index 가 그걸 덮어썼다.

## 계약

1. `recent_done_items` 는 **최신순**이다 (소비자가 전부 앞에서 자른다).
2. 상한은 `RECENT_DONE_ITEMS_CAP` **한 곳**에서 **한 번**만 적용된다.
3. task 파일이 있으면 그것이 SSOT — daily index 가 판정을 덮어쓰지 않는다.
4. 어휘 밖 status 는 조용히 버려지지 않고 `unknown_status_items` 로 드러난다.
5. handoff §4(손으로도 쌓일 수 있는 파생물)가 task SSOT 를 밀어내지 않는다.
   — 쓰는 쪽의 상한은 v1.0.3 §2.46 에서 `check_handoff_done_cap.py` 가 따로 고정한다.

Cross-ref: releases/Beta-v1.0.0.md §2.38.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SOURCE_ROOT))

from workflow_kit.common.paths import workflow_state_path  # noqa: E402
from workflow_kit.common.state.builder import (  # noqa: E402
    RECENT_DONE_ITEMS_CAP,
    _aggregate_from_appendonly_layout,
)
from workflow_kit.common.workflow_state import refresh_workflow_state_cache  # noqa: E402
from workflow_kit.common.workflow_writes import upsert_backlog_entry  # noqa: E402

BRANCH = "recent-done-smoke"


def _workspace(td: str) -> Path:
    ws = Path(td)
    (ws / "docs").mkdir(parents=True)
    (ws / "docs" / "PROJECT_PROFILE.md").write_text("# Profile\n", encoding="utf-8")
    base = ws / "ai-workflow" / "memory" / "active" / BRANCH
    (base / "backlog" / "tasks").mkdir(parents=True)
    (base / "sessions").mkdir(parents=True)
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


def _write_task(ws: Path, *, date: str, seq: int, title: str, status: str = "done") -> str:
    """프로덕션 writer 로 daily index + task 파일을 쓴다. task_id 반환."""
    task_id = f"TASK-{date}-{BRANCH}-{seq:03d}"
    upsert_backlog_entry(
        backlog_path=_branch_dir(ws) / "backlog" / f"{date}.md",
        task_id=task_id,
        entry_lines=[
            "---",
            f"id: {task_id}",
            f"status: {status}",
            f"created_at: {date}",
            "source_anchor: recent-done-smoke",
            f"source_path: backlog/{date}.md",
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
    return task_id


def _aggregate(ws: Path) -> dict[str, list[str]]:
    base = _branch_dir(ws)
    return _aggregate_from_appendonly_layout(
        daily_backlog_dir=base / "backlog",
        tasks_dir=base / "backlog" / "tasks",
        sessions_dir=base / "sessions",
    )


def _state(ws: Path) -> dict:
    profile = ws / "docs" / "PROJECT_PROFILE.md"
    result = refresh_workflow_state_cache(project_profile_path=profile, generated_at="2026-07-28")
    assert result["status"] == "refreshed", result
    return json.loads(workflow_state_path(profile).read_text(encoding="utf-8"))


# --- 1. 최신순 + 상한 1회 -------------------------------------------------


@_with_branch
def test_recent_done_items_are_newest_first() -> None:
    """상한을 넘겨도 남는 것은 **최신** 이고, 순서는 최신 → 오래된 순이다."""
    with tempfile.TemporaryDirectory() as td:
        ws = _workspace(td)
        # 상한보다 2개 많게. 오래된 것부터 쓴다 — 쓰는 순서가 결과를 좌우하면 안 된다.
        dates = [f"2026-06-{day:02d}" for day in range(1, RECENT_DONE_ITEMS_CAP + 3)]
        for day, date in enumerate(dates, start=1):
            _write_task(ws, date=date, seq=1, title=f"완료 {day:02d}일")

        recent = _state(ws)["session"]["recent_done_items"]
        assert len(recent) == RECENT_DONE_ITEMS_CAP, (
            f"상한이 두 번 적용되거나 적용되지 않았다: {len(recent)}개 — {recent}"
        )

        newest = dates[-RECENT_DONE_ITEMS_CAP:][::-1]  # 최신순 기대값
        for rank, date in enumerate(newest):
            assert date in recent[rank], (
                f"{rank}번째가 최신순이 아니다 — 기대 {date}, 실제 {recent[rank]!r}\n"
                f"전체: {recent}"
            )

        dropped = dates[: len(dates) - RECENT_DONE_ITEMS_CAP]
        for date in dropped:
            assert not any(date in item for item in recent), (
                f"가장 오래된 {date} 가 최신 자리를 차지했다: {recent}"
            )


# --- 2. task 파일이 SSOT --------------------------------------------------


@_with_branch
def test_daily_index_does_not_resurrect_non_done_task() -> None:
    """어휘 밖 status 의 task 를 daily index fallback 이 done 으로 되살리지 않는다."""
    with tempfile.TemporaryDirectory() as td:
        ws = _workspace(td)
        recorded_id = _write_task(
            ws, date="2026-06-01", seq=1, title="마이그레이션 잔재", status="recorded"
        )
        done_id = _write_task(ws, date="2026-06-02", seq=1, title="진짜 완료")

        agg = _aggregate(ws)
        assert recorded_id not in agg["done_items"], (
            f"status: recorded 인 task 가 done 으로 보고됐다 — {agg['done_items']}"
        )
        assert done_id in agg["done_items"], agg["done_items"]
        assert any(recorded_id in item for item in agg["unknown_status_items"]), (
            f"어휘 밖 status 가 조용히 사라졌다 — {agg['unknown_status_items']}"
        )
        assert not any("마이그레이션 잔재" in item for item in agg["recent_done_items"]), (
            agg["recent_done_items"]
        )


@_with_branch
def test_planned_task_is_not_reported_done() -> None:
    """`planned` 도 마찬가지다 — daily index 에 실렸다는 이유로 완료가 되지 않는다."""
    with tempfile.TemporaryDirectory() as td:
        ws = _workspace(td)
        planned_id = _write_task(ws, date="2026-06-01", seq=1, title="아직 안 함", status="planned")
        agg = _aggregate(ws)
        assert planned_id not in agg["done_items"], agg["done_items"]
        assert agg["unknown_status_items"] == [], agg["unknown_status_items"]


# --- 3. daily-only 항목은 자기 날짜 자리에 -------------------------------


@_with_branch
def test_daily_only_entry_keeps_its_chronological_slot() -> None:
    """task 파일이 없는 구형 index 항목은 **자기 날짜** 자리에 놓인다 (맨 앞 ❌).

    이게 원래 증상이다: daily 잔여분이 목록 뒤에 붙고 `[-10:]` 가 그 뒤를 잘라,
    저장소에서 가장 오래된 항목이 "최근 완료" 자리를 차지했다.
    """
    with tempfile.TemporaryDirectory() as td:
        ws = _workspace(td)
        legacy_id = _write_task(ws, date="2026-01-05", seq=1, title="아주 오래된 것")
        # task 파일만 지워 "index 는 있는데 task 파일이 없는" 구형 상태를 만든다.
        (_branch_dir(ws) / "backlog" / "tasks" / f"{legacy_id}.md").unlink()
        for day in range(1, 4):
            _write_task(ws, date=f"2026-06-{day:02d}", seq=1, title=f"최근 {day}")

        recent = _aggregate(ws)["recent_done_items"]
        assert "아주 오래된 것" in recent[-1], (
            f"구형 index 항목이 최신 자리에 앉았다 — {recent}"
        )
        assert "최근 3" in recent[0], recent


# --- 4. handoff 는 task SSOT 를 밀어내지 않는다 --------------------------


@_with_branch
def test_handoff_does_not_crowd_out_task_ssot() -> None:
    """손으로 쌓인 handoff §4(파생물)가 최신 task 를 밀어내지 않는다."""
    with tempfile.TemporaryDirectory() as td:
        ws = _workspace(td)
        handoff_lines = ["# Session Handoff", "", "- 최근 완료 작업 목록:"]
        handoff_lines += [f"- 손으로 적은 옛 항목 {n}" for n in range(1, RECENT_DONE_ITEMS_CAP + 1)]
        (_branch_dir(ws) / "session_handoff.md").write_text(
            "\n".join(handoff_lines) + "\n", encoding="utf-8"
        )
        titles = [f"최신 작업 {n}" for n in range(1, 4)]
        for n, title in enumerate(titles, start=1):
            _write_task(ws, date=f"2026-06-{n:02d}", seq=1, title=title)

        recent = _state(ws)["session"]["recent_done_items"]
        missing = [t for t in titles if not any(t in item for item in recent)]
        assert not missing, (
            f"handoff 의 옛 항목이 상한을 차지해 task SSOT 가 밀려났다: {missing}\n실제: {recent}"
        )


def main() -> int:
    test_funcs = [
        test_recent_done_items_are_newest_first,
        test_daily_index_does_not_resurrect_non_done_task,
        test_planned_task_is_not_reported_done,
        test_daily_only_entry_keeps_its_chronological_slot,
        test_handoff_does_not_crowd_out_task_ssot,
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
    print(f"\n{total - len(failures)}/{total} PASS")
    if failures:
        for name, err in failures:
            print(f"  - {name}: {err}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
