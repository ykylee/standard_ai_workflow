"""`state.json` 의 `latest_backlog_path` / `backlog` block 계약 (v1.0.3).

## 왜 필요한가

append-only layout(`backlog/<날짜>.md` + `backlog/tasks/`) 저장소에서 `state.json` 의

    source_of_truth.latest_backlog_path : null
    backlog.latest_backlog_path         : null
    backlog.task_count                  : 0

가 **항상** 이 값이었다. task 파일이 107건 있는 저장소에서다. 원인은 세 갈래의 경로
해석이 전부 `legacy_index_present`(= 구형 `work_backlog.md` 가 있는가) 하나에 매달려
있었던 것이다 — 그래서 호출자가 `--latest-backlog-path` 로 **명시한 인자까지 버려졌다**
(2026-07-31 실측: 넘겨도 그대로 `null`).

"모른다" 와 "0 이다" 는 다른 말이다. `task_count: 0` 은 모른다는 표시가 아니라 **틀린
사실**이고, 이 필드를 읽는 skill(session-start / doc-sync / validation-plan /
merge-doc-reconcile)은 최신 backlog 를 가리키는 포인터를 통째로 잃고 있었다.

## 계약

1. 호출자가 명시한 `latest_backlog_path` 는 legacy index 유무와 무관하게 존중된다.
2. 명시하지 않으면 append-only layout 의 daily 디렉터리에서 **가장 최신** 파일을 고른다.
3. `backlog.task_count` 는 그 파일이 실제로 담은 task 수다 (0 을 날조하지 않는다).
   완료된 task 는 `current_focus` 가 되지 않는다 — 끝난 일은 초점이 아니다.
4. 실재하지 않는 경로는 `null` 로 떨어진다 — 없는 파일을 가리키지 않는다.
5. legacy layout(구형 index 만 있는 저장소)의 동작은 그대로다.
6. 이 저장소 자신의 `state.json` 도 그 계약을 만족한다 (self-application).

Cross-ref: releases/Beta-v1.0.0.md §2.46.
"""

from __future__ import annotations

#: 이 검사의 입력 표면 (spec `core/test_impact_tiering_spec.md` §2).
#: 게이트 채취 실측에서 뽑아 넓은 쪽으로 올렸다 — 좁으면 meta-watch 가 red 로 잡는다.
WATCHES = (
    "ai-workflow/memory/active/*",
    "workflow-source/pyproject.toml",
    "workflow-source/workflow_kit/*",
)

import json
import sys
import tempfile
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SOURCE_ROOT.parent
sys.path.insert(0, str(SOURCE_ROOT))

from workflow_kit.common.project_docs import parse_backlog  # noqa: E402
from workflow_kit.common.state.builder import build_workflow_state_payload  # noqa: E402
from workflow_kit.common.workflow_writes import upsert_backlog_entry  # noqa: E402

BRANCH = "backlog-block-smoke"

PROFILE = """# Project Profile

- 문서 목적: 검사용 fixture.
- 최종 수정일: 2026-07-31

## 1. 기본 정보

- 프로젝트 이름: Backlog Block Fixture
- 문서 홈: docs/index.md
"""


def _workspace(td: str) -> Path:
    ws = Path(td)
    (ws / "docs").mkdir(parents=True)
    (ws / "docs" / "PROJECT_PROFILE.md").write_text(PROFILE, encoding="utf-8")
    base = ws / "ai-workflow" / "memory" / "active" / BRANCH
    (base / "backlog" / "tasks").mkdir(parents=True)
    (base / "sessions").mkdir(parents=True)
    return ws


def _branch_dir(ws: Path) -> Path:
    return ws / "ai-workflow" / "memory" / "active" / BRANCH


def _write_task(ws: Path, *, date: str, seq: int, title: str, status: str = "done") -> str:
    """프로덕션 writer 로 daily index + task 파일을 쓴다."""
    task_id = f"TASK-{date}-{BRANCH}-{seq:03d}"
    upsert_backlog_entry(
        backlog_path=_branch_dir(ws) / "backlog" / f"{date}.md",
        task_id=task_id,
        entry_lines=[
            "---",
            f"id: {task_id}",
            f"status: {status}",
            f"created_at: {date}",
            "source_anchor: backlog-block-smoke",
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


def _payload(ws: Path, **overrides: object) -> dict:
    base = _branch_dir(ws)
    kwargs: dict = {
        "project_profile_path": ws / "docs" / "PROJECT_PROFILE.md",
        "daily_backlog_dir": base / "backlog",
        "tasks_dir": base / "backlog" / "tasks",
        "sessions_dir": base / "sessions",
        "generated_at": "2026-07-31",
        "workspace_root": ws,
    }
    kwargs.update(overrides)
    return build_workflow_state_payload(**kwargs)  # type: ignore[arg-type]


# --- 1. 명시한 인자를 버리지 않는다 --------------------------------------


def test_explicit_latest_backlog_path_is_honored() -> None:
    """legacy index 가 없어도 호출자가 넘긴 경로를 그대로 쓴다 (원래 결함)."""
    with tempfile.TemporaryDirectory() as td:
        ws = _workspace(td)
        _write_task(ws, date="2026-07-30", seq=1, title="어제 것")
        _write_task(ws, date="2026-07-31", seq=1, title="오늘 것")
        explicit = _branch_dir(ws) / "backlog" / "2026-07-30.md"

        payload = _payload(ws, latest_backlog_path=explicit)
        for block in ("source_of_truth", "backlog"):
            actual = payload[block]["latest_backlog_path"]
            assert actual is not None and actual.endswith("2026-07-30.md"), (
                f"{block}.latest_backlog_path 가 명시한 인자를 버렸다: {actual!r}"
            )


# --- 2. 명시하지 않으면 최신 daily 를 고른다 -----------------------------


def test_latest_daily_backlog_is_resolved_without_legacy_index() -> None:
    """append-only layout 만으로도 최신 daily 파일을 찾는다."""
    with tempfile.TemporaryDirectory() as td:
        ws = _workspace(td)
        for day in ("2026-07-02", "2026-07-31", "2026-07-11"):
            _write_task(ws, date=day, seq=1, title=f"{day} 작업")

        payload = _payload(ws)
        actual = payload["source_of_truth"]["latest_backlog_path"]
        assert actual is not None, "append-only layout 에서 latest_backlog_path 가 null 이다."
        assert actual.endswith("2026-07-31.md"), f"최신이 아니다: {actual}"


def test_empty_backlog_dir_stays_null() -> None:
    """가리킬 파일이 없으면 `null` 이다 — 없는 경로를 지어내지 않는다."""
    with tempfile.TemporaryDirectory() as td:
        ws = _workspace(td)
        payload = _payload(ws)
        assert payload["source_of_truth"]["latest_backlog_path"] is None
        assert payload["backlog"]["latest_backlog_path"] is None
        assert payload["backlog"]["task_count"] == 0


def test_nonexistent_explicit_path_falls_back_to_null() -> None:
    """실재하지 않는 경로를 명시하면 그것을 그대로 적지 않는다."""
    with tempfile.TemporaryDirectory() as td:
        ws = _workspace(td)
        _write_task(ws, date="2026-07-31", seq=1, title="오늘 것")
        ghost = _branch_dir(ws) / "backlog" / "2099-01-01.md"

        payload = _payload(ws, latest_backlog_path=ghost)
        assert payload["source_of_truth"]["latest_backlog_path"] is None, (
            "실재하지 않는 경로가 state.json 에 적혔다."
        )


# --- 3. task_count 가 사실을 적는다 --------------------------------------


def test_task_count_matches_the_backlog_it_points_at() -> None:
    """`task_count` 는 가리키는 backlog 의 task 수다."""
    with tempfile.TemporaryDirectory() as td:
        ws = _workspace(td)
        _write_task(ws, date="2026-07-30", seq=1, title="어제 1")
        for seq, title in enumerate(("오늘 1", "오늘 2", "오늘 3"), start=1):
            _write_task(ws, date="2026-07-31", seq=seq, title=title, status="in_progress")

        payload = _payload(ws)
        pointed = _branch_dir(ws) / "backlog" / "2026-07-31.md"
        expected = len(parse_backlog(pointed)["tasks"])  # type: ignore[arg-type]
        assert expected == 3, f"fixture 가 기대와 다르다: {expected}"
        assert payload["backlog"]["task_count"] == expected, (
            f"task_count={payload['backlog']['task_count']} 인데 실제 {expected} 건이다."
        )
        assert len(payload["backlog"]["in_progress_items"]) == 3, payload["backlog"]


def test_completed_task_does_not_become_current_focus() -> None:
    """전부 `done` 인 날의 첫 task 가 "현재 초점" 으로 올라오지 않는다.

    `backlog` block 이 살아나면서 드러난 자리다 — `current_focus` 의 fallback 이
    "최신 backlog 의 첫 task" 였고, 그 목록이 비어 있던 동안에는 발현하지 않았다.
    """
    with tempfile.TemporaryDirectory() as td:
        ws = _workspace(td)
        _write_task(ws, date="2026-07-31", seq=1, title="끝난 일 1", status="done")
        _write_task(ws, date="2026-07-31", seq=2, title="끝난 일 2", status="done")

        payload = _payload(ws)
        assert payload["session"]["current_focus"] is None, (
            f"완료된 작업이 현재 초점이 됐다: {payload['session']['current_focus']!r}"
        )

        # 아직 안 끝난 것이 있으면 그것을 고른다.
        pending_id = _write_task(ws, date="2026-07-31", seq=3, title="아직 하는 일", status="in_progress")
        focus = _payload(ws)["session"]["current_focus"]
        assert focus is not None and pending_id in focus, (
            f"진행 중인 {pending_id} 가 초점이 아니다: {focus!r}"
        )


# --- 4. legacy layout 회귀 -----------------------------------------------


def test_legacy_index_layout_still_resolves() -> None:
    """구형 `work_backlog.md` 인덱스만 있는 저장소의 동작은 그대로다."""
    with tempfile.TemporaryDirectory() as td:
        ws = _workspace(td)
        legacy_dir = ws / "legacy"
        legacy_dir.mkdir()
        daily = legacy_dir / "2026-05-02.md"
        daily.write_text(
            "# 2026-05-02 작업 백로그\n\n## TASK-2026-05-02-001 구형 작업\n\n- 상태: done\n",
            encoding="utf-8",
        )
        index = legacy_dir / "work_backlog.md"
        index.write_text(
            "# Work Backlog\n\n## 날짜별 백로그 문서\n\n- [2026-05-02 작업 백로그](./2026-05-02.md)\n",
            encoding="utf-8",
        )

        payload = _payload(
            ws,
            daily_backlog_dir=None,
            tasks_dir=None,
            sessions_dir=None,
            work_backlog_index_path=index,
        )
        actual = payload["source_of_truth"]["latest_backlog_path"]
        assert actual is not None and actual.endswith("2026-05-02.md"), actual
        assert payload["backlog"]["task_count"] == 1, payload["backlog"]


# --- 5. self-application -------------------------------------------------


def test_this_repository_state_json_points_somewhere_real() -> None:
    """이 저장소 자신의 `state.json` 도 같은 계약을 만족한다.

    fixture 만으로는 "호출자가 실제로 그 인자를 넘기는가" 를 재지 못한다. 여기서는
    **커밋된 산출물**을 본다 — 이 필드가 다시 `null` 로 굳으면 여기서 실패한다.
    """
    candidates = sorted((REPO_ROOT / "ai-workflow" / "memory" / "active").glob("*/state.json"))
    if not candidates:
        print("    (skip: branch-scoped state.json 없음)")
        return
    checked = 0
    for state_path in candidates:
        state = json.loads(state_path.read_text(encoding="utf-8"))
        backlog_dir_rel = state.get("source_of_truth", {}).get("daily_backlog_dir")
        if not backlog_dir_rel:
            continue
        backlog_dir = REPO_ROOT / backlog_dir_rel
        if not any(backlog_dir.glob("[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9].md")):
            continue
        checked += 1
        latest = state["source_of_truth"].get("latest_backlog_path")
        assert latest, (
            f"{state_path.relative_to(REPO_ROOT)} 의 latest_backlog_path 가 null 이다 — "
            f"{backlog_dir_rel} 에 daily backlog 가 실재하는데도."
        )
        assert (REPO_ROOT / latest).is_file(), f"가리키는 파일이 없다: {latest}"
        assert state["backlog"]["task_count"] > 0, (
            f"{state_path.relative_to(REPO_ROOT)} 의 task_count 가 0 인데 "
            f"{latest} 는 task 를 담고 있다."
        )
    if checked == 0:
        print("    (skip: daily backlog 를 가진 branch state 없음)")


def main() -> int:
    test_funcs = [
        test_explicit_latest_backlog_path_is_honored,
        test_latest_daily_backlog_is_resolved_without_legacy_index,
        test_empty_backlog_dir_stays_null,
        test_nonexistent_explicit_path_falls_back_to_null,
        test_task_count_matches_the_backlog_it_points_at,
        test_completed_task_does_not_become_current_focus,
        test_legacy_index_layout_still_resolves,
        test_this_repository_state_json_points_somewhere_real,
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
