"""handoff §4("최근 완료 작업 목록")의 **상한** 계약 (v1.0.3).

## 왜 필요한가

`recent_done_items` 는 세 곳이 안다.

| 자리 | 하는 일 | 상한을 알았나 |
|---|---|---|
| `sync_handoff_status` | handoff §4 에 append | **몰랐다 — 무한히 쌓았다** |
| `build_workflow_state_payload` | state.json 조립 | 알았다 (`RECENT_DONE_ITEMS_CAP`) |
| `linter.handoff_bloat` | 넘쳤는지 본다 | 리터럴 `10` 을 따로 들고 있었다 |

쓰는 쪽에만 상한이 없어서 `backlog-update --apply` 를 돌릴 때마다 handoff 가 11번째
줄을 얻었고, `handoff_bloat` 가 그걸 잡으면 **사람이 손으로 가장 오래된 한 줄을
지웠다**. 2026-07-28 과 2026-07-31 두 번의 close-out 에서 연속으로 재발했다 — 도구가
만든 초과를 사람이 치우는 수작업이 고정 비용이 됐다.

## 계약

1. 쓰는 쪽이 상한을 적용한다 — `sync_handoff_status` 를 몇 번 부르든 §4 는 상한 이하다.
2. 버리는 쪽은 **가장 오래된 것**이다 (§4 는 뒤가 최신인 append 목록).
3. 상한은 `project_docs.RECENT_DONE_ITEMS_CAP` **한 곳**이 정본이다 — 쓰는 쪽/조립하는
   쪽/보는 쪽이 전부 그 이름을 읽는다 (사본을 들고 있으면 이 검사가 실패한다).
4. `in_progress` / `blocked` 에는 상한이 없다 — 전부 보여야 하는 사실이다.

Cross-ref: releases/Beta-v1.0.0.md §2.46.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SOURCE_ROOT))

from workflow_kit.common import linter as linter_mod  # noqa: E402
from workflow_kit.common import project_docs as project_docs_mod  # noqa: E402
from workflow_kit.common import workflow_writes as writes_mod  # noqa: E402
from workflow_kit.common.project_docs import (  # noqa: E402
    RECENT_DONE_ITEMS_CAP,
    parse_handoff,
)
from workflow_kit.common.state import builder as builder_mod  # noqa: E402
from workflow_kit.common.workflow_writes import sync_handoff_status  # noqa: E402

HANDOFF_TEMPLATE = """# Session Handoff

- 문서 목적: 다음 세션이 바로 이어받을 수 있도록 현재 상태를 요약한다.
- 최종 수정일: 2026-01-01

## 2. 진행 중 작업

- 현재 `in_progress` 작업:
-

## 3. 차단 작업

- 현재 `blocked` 작업:
-

## 4. 최근 완료 작업

- 최근 완료 작업 목록:
-
"""


def _handoff(td: str) -> Path:
    path = Path(td) / "session_handoff.md"
    path.write_text(HANDOFF_TEMPLATE, encoding="utf-8")
    return path


def _done_items(path: Path) -> list[str]:
    return [
        line.strip()[2:].strip()
        for line in _section_lines(path, "최근 완료 작업 목록")
        if line.strip().startswith("- ") and line.strip()[2:].strip()
    ]


def _section_lines(path: Path, label: str) -> list[str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    out: list[str] = []
    collecting = False
    for line in lines:
        stripped = line.strip()
        if stripped == f"- {label}:":
            collecting = True
            continue
        if not collecting:
            continue
        if stripped.startswith("## ") or (stripped.startswith("- ") and stripped.endswith(":")):
            break
        out.append(line)
    return out


# --- 1. 쓰는 쪽이 상한을 적용한다 ----------------------------------------


def test_writer_caps_done_section() -> None:
    """상한보다 많이 완료해도 §4 는 상한 이하로 유지된다."""
    with tempfile.TemporaryDirectory() as td:
        path = _handoff(td)
        labels = [f"TASK-2026-06-{n:02d}-main-001 완료 {n}" for n in range(1, RECENT_DONE_ITEMS_CAP + 4)]
        for label in labels:
            sync_handoff_status(handoff_path=path, task_label=label, status="done")

        items = _done_items(path)
        assert len(items) == RECENT_DONE_ITEMS_CAP, (
            f"§4 가 상한({RECENT_DONE_ITEMS_CAP})을 넘었다: {len(items)}개\n{items}"
        )
        # 파서가 보는 값도 같아야 한다 — `handoff_bloat` 는 이 경로로 센다.
        parsed = parse_handoff(path)["recent_done_items"]
        assert len(parsed) == RECENT_DONE_ITEMS_CAP, parsed


def test_writer_drops_oldest_not_newest() -> None:
    """버리는 것은 가장 오래된 것이다 — 최신이 사라지면 목록의 이름이 거짓이 된다."""
    with tempfile.TemporaryDirectory() as td:
        path = _handoff(td)
        labels = [f"TASK-2026-06-{n:02d}-main-001 완료 {n}" for n in range(1, RECENT_DONE_ITEMS_CAP + 4)]
        for label in labels:
            sync_handoff_status(handoff_path=path, task_label=label, status="done")

        items = _done_items(path)
        assert items == labels[-RECENT_DONE_ITEMS_CAP:], (
            f"최신 {RECENT_DONE_ITEMS_CAP}건이 아니다.\n기대: {labels[-RECENT_DONE_ITEMS_CAP:]}\n실제: {items}"
        )
        for dropped in labels[: len(labels) - RECENT_DONE_ITEMS_CAP]:
            assert dropped not in items, f"오래된 {dropped} 가 남았다: {items}"


def test_in_progress_and_blocked_are_not_capped() -> None:
    """진행 중 / 차단은 상한이 없다 — 몇 건이든 전부 보여야 한다."""
    with tempfile.TemporaryDirectory() as td:
        path = _handoff(td)
        count = RECENT_DONE_ITEMS_CAP + 3
        for n in range(1, count + 1):
            sync_handoff_status(
                handoff_path=path, task_label=f"TASK-2026-06-{n:02d}-main-002 진행 {n}", status="in_progress"
            )
        items = [
            line.strip()[2:].strip()
            for line in _section_lines(path, "현재 `in_progress` 작업")
            if line.strip().startswith("- ") and line.strip()[2:].strip()
        ]
        assert len(items) == count, f"in_progress 에 상한이 걸렸다: {len(items)}/{count}\n{items}"


def test_status_move_still_works_at_cap() -> None:
    """상한에 닿은 뒤에도 done → in_progress 이동이 그대로 동작한다."""
    with tempfile.TemporaryDirectory() as td:
        path = _handoff(td)
        labels = [f"TASK-2026-06-{n:02d}-main-001 완료 {n}" for n in range(1, RECENT_DONE_ITEMS_CAP + 1)]
        for label in labels:
            sync_handoff_status(handoff_path=path, task_label=label, status="done")

        reopened = labels[-1]
        sync_handoff_status(handoff_path=path, task_label=reopened, status="in_progress")

        done = _done_items(path)
        assert reopened not in done, f"다시 연 작업이 완료 목록에 남았다: {done}"
        in_progress = [
            line.strip()[2:].strip()
            for line in _section_lines(path, "현재 `in_progress` 작업")
            if line.strip().startswith("- ") and line.strip()[2:].strip()
        ]
        assert in_progress == [reopened], in_progress


# --- 2. 상한의 단일 출처 --------------------------------------------------


def test_cap_is_one_object_everywhere() -> None:
    """상한을 아는 세 자리가 **같은 정본 이름**을 읽는다."""
    canonical = project_docs_mod.RECENT_DONE_ITEMS_CAP
    for module in (writes_mod, linter_mod, builder_mod):
        actual = getattr(module, "RECENT_DONE_ITEMS_CAP", None)
        assert actual is not None, (
            f"{module.__name__} 이 상한 정본을 import 하지 않는다 — 사본을 들고 있을 가능성이 높다."
        )
        assert actual == canonical, (
            f"{module.__name__}.RECENT_DONE_ITEMS_CAP={actual} 이 정본({canonical})과 갈라졌다."
        )


def test_writer_reads_the_constant_not_a_literal() -> None:
    """정본 값을 바꾸면 쓰는 쪽의 동작이 따라온다 (리터럴이면 안 따라온다)."""
    with tempfile.TemporaryDirectory() as td:
        path = _handoff(td)
        original = writes_mod.RECENT_DONE_ITEMS_CAP
        writes_mod.RECENT_DONE_ITEMS_CAP = 3
        try:
            for n in range(1, 8):
                sync_handoff_status(
                    handoff_path=path, task_label=f"TASK-2026-06-{n:02d}-main-001 완료 {n}", status="done"
                )
            items = _done_items(path)
        finally:
            writes_mod.RECENT_DONE_ITEMS_CAP = original
        assert len(items) == 3, (
            f"상한을 3으로 바꿨는데 {len(items)}개다 — 리터럴을 보고 있다.\n{items}"
        )


def test_linter_reads_the_constant_not_a_literal() -> None:
    """보는 쪽도 마찬가지다 — 정본을 낮추면 그만큼에서 `handoff_bloat` 가 켜진다.

    판정을 여기서 다시 쓰지 않는다(그러면 재현일 뿐 검증이 아니다). 프로덕션
    `check_workflow_consistency` 를 그대로 부르고, 정본만 갈아 끼운다.
    """
    with tempfile.TemporaryDirectory() as td:
        path = _handoff(td)
        # 정본 그대로: 상한만큼만 채운다 → bloat 아님.
        for n in range(1, RECENT_DONE_ITEMS_CAP + 1):
            sync_handoff_status(
                handoff_path=path, task_label=f"TASK-2026-06-{n:02d}-main-001 완료 {n}", status="done"
            )
        assert not _bloat_codes(td, path), (
            f"상한({RECENT_DONE_ITEMS_CAP})만큼인데 bloat 로 잡혔다."
        )

        original = linter_mod.RECENT_DONE_ITEMS_CAP
        linter_mod.RECENT_DONE_ITEMS_CAP = RECENT_DONE_ITEMS_CAP - 2
        try:
            codes = _bloat_codes(td, path)
        finally:
            linter_mod.RECENT_DONE_ITEMS_CAP = original
        assert codes, (
            f"정본을 {RECENT_DONE_ITEMS_CAP - 2} 로 낮췄는데 handoff_bloat 가 안 켜졌다 — "
            "린터가 리터럴을 보고 있다."
        )


def _bloat_codes(td: str, handoff_path: Path) -> list[str]:
    """프로덕션 린터를 돌려 `handoff_bloat` issue code 만 뽑는다."""
    state_path = Path(td) / "state.json"
    state_path.write_text('{"session": {"in_progress_items": []}}\n', encoding="utf-8")
    backlog_path = Path(td) / "2026-06-01.md"
    backlog_path.write_text("# Backlog Index — 2026-06-01\n\n## Tasks\n", encoding="utf-8")
    result = linter_mod.check_workflow_consistency(state_path, handoff_path, backlog_path)
    return [
        str(issue.get("code"))
        for issue in result.get("issues", [])
        if issue.get("code") == "handoff_bloat"
    ]


def main() -> int:
    test_funcs = [
        test_writer_caps_done_section,
        test_writer_drops_oldest_not_newest,
        test_in_progress_and_blocked_are_not_capped,
        test_status_move_still_works_at_cap,
        test_cap_is_one_object_everywhere,
        test_writer_reads_the_constant_not_a_literal,
        test_linter_reads_the_constant_not_a_literal,
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
