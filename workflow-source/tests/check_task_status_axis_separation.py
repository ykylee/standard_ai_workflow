"""task frontmatter 의 **진행 상태 축 / 출처 축 분리** 계약 (v1.0.3).

## 왜 필요한가

`migrate_active_to_appendonly.py` 는 legacy 이관 task 에 표준 어휘 밖의
`status: recorded` 를 적었다. 그 값이 실제로 뜻한 것은 진행 상태가 아니라
**"legacy `work_backlog.md` 에서 이관됐고 진행 상태는 모른다"** 는 *출처* 사실이었다.
두 축을 한 칸에 넣은 결과:

  1. state builder 는 `recorded` 를 몰라 done/in_progress/blocked 어디에도 넣지 못했고,
  2. daily index fallback 이 "어느 목록에도 없으니 done" 으로 되살려
  3. **미완료 3건이 완료로 보고**됐다 (§2.38 에서 (1)(2) 를 막았고, 여기서 발생원을 막는다).

축을 분리한 뒤에도 같은 결함이 재발할 수 있는 지점이 하나 남는다: **status 를 비웠을 때
누군가 기본값으로 채우는 것**. `_aggregate_from_appendonly_layout` 은 예전에 status 줄이
없으면 `planned` 로 떨어뜨렸는데, 그것도 판정이다 (이미 끝난 작업을 "아직 시작 안 함" 으로
기록한다). 근거가 없으면 채우지 않고 드러내야 한다.

## 계약

1. 이관 도구는 **판정 근거가 있을 때만** `status` 를 쓴다 (release entry → `done`).
   근거가 없는 generic/session entry 는 `status` 줄 자체를 쓰지 않는다.
2. 이관 도구가 쓰는 `status` 는 **항상 `TASK_STATUSES` 안**이다 (어휘 밖 값 금지).
3. 출처는 `provenance` 로 적는다.
4. `status` 줄이 없는 task 는 어느 판정 목록에도 들어가지 않고
   `unknown_status_items` 에 `<ID>: <미기재>` 로 드러난다.
5. 저장소의 실제 task 파일에 어휘 밖 status 가 없다 (선언과 사실의 일치).

Cross-ref: releases/Beta-v1.0.0.md §2.39, MEMORY_GOVERNANCE.md "두 축을 섞지 않는다".
"""

from __future__ import annotations

#: 이 검사의 입력 표면 (spec `core/test_impact_tiering_spec.md` §2).
#: 게이트 채취 실측에서 뽑아 넓은 쪽으로 올렸다 — 좁으면 meta-watch 가 red 로 잡는다.
WATCHES = (
    "ai-workflow/memory/active/*",
    "workflow-source/pyproject.toml",
    "workflow-source/workflow_kit/*",
)

import importlib.util
import json
import os
import re
import sys
import tempfile
from pathlib import Path
from types import ModuleType

SOURCE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SOURCE_ROOT.parent
sys.path.insert(0, str(SOURCE_ROOT))

from workflow_kit.common.paths import workflow_state_path  # noqa: E402
from workflow_kit.common.project_docs import (  # noqa: E402
    MISSING_STATUS_MARKER,
    TASK_PROVENANCE_MIGRATED_LEGACY,
    TASK_STATUSES,
)
from workflow_kit.common.state.builder import (  # noqa: E402
    _aggregate_from_appendonly_layout,
)
from workflow_kit.common.workflow_state import refresh_workflow_state_cache  # noqa: E402

BRANCH = "status-axis-smoke"
MIGRATE_TOOL = SOURCE_ROOT / "workflow_kit" / "tools" / "migrate_active_to_appendonly.py"
FRONTMATTER_STATUS_RE = re.compile(r"^status:\s*(\S+)\s*$", re.M)


def _load_migrate_tool() -> ModuleType:
    spec = importlib.util.spec_from_file_location("migrate_active_to_appendonly", str(MIGRATE_TOOL))
    assert spec is not None and spec.loader is not None, MIGRATE_TOOL
    mod = importlib.util.module_from_spec(spec)
    # `@dataclass` 가 annotation 해석 시 `sys.modules[cls.__module__]` 를 본다.
    # 등록 전에 exec 하면 AttributeError 로 죽는다.
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


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


def _write_raw_task(ws: Path, *, task_id: str, date: str, title: str, body: str) -> None:
    """frontmatter 를 **그대로** 쓴다 (status 줄을 뺀 상태를 만들기 위해)."""
    tasks_dir = _branch_dir(ws) / "backlog" / "tasks"
    (tasks_dir / f"{task_id}.md").write_text(body, encoding="utf-8")
    daily = _branch_dir(ws) / "backlog" / f"{date}.md"
    daily.write_text(
        f"# Backlog Index — {date}\n\n## Tasks\n\n"
        f"- **{task_id}** [generic] {title}\n"
        f"  - path: [`./tasks/{task_id}.md`](./tasks/{task_id}.md)\n",
        encoding="utf-8",
    )


def _aggregate(ws: Path) -> dict[str, list[str]]:
    base = _branch_dir(ws)
    return _aggregate_from_appendonly_layout(
        daily_backlog_dir=base / "backlog",
        tasks_dir=base / "backlog" / "tasks",
        sessions_dir=base / "sessions",
    )


# --- 1. 이관 도구는 근거 없이 판정하지 않는다 -----------------------------


def test_migration_tool_omits_status_without_basis() -> None:
    """generic/session entry 에는 `status` 줄이 없고 `provenance` 가 붙는다."""
    mod = _load_migrate_tool()
    for kind in ("generic", "session"):
        entry = mod.Entry(
            raw_path=f"main/backlog/2026-05-01.md",
            anchor=f"main-{kind}",
            date="2026-05-01",
            summary="legacy 한 줄 요약",
            body_lines=["- 2026-05-01: legacy 한 줄 요약"],
            kind=kind,
            task_id="TASK-2026-05-01-001",
        )
        text = mod.build_task_file(entry)
        assert FRONTMATTER_STATUS_RE.search(text) is None, (
            f"kind={kind} 인데 근거 없이 status 를 적었다:\n{text[:400]}"
        )
        assert f"provenance: {TASK_PROVENANCE_MIGRATED_LEGACY}" in text, (
            f"kind={kind} 에 provenance 가 없다 — 출처 축이 사라졌다:\n{text[:400]}"
        )


def test_migration_tool_writes_done_only_for_release() -> None:
    """근거가 있는 release entry 에만 `done` 을 쓴다."""
    mod = _load_migrate_tool()
    entry = mod.Entry(
        raw_path="main/releases/Beta-v0.9.0.md",
        anchor="main-release",
        date="2026-05-01",
        summary="v0.9.0 발행",
        body_lines=["- 2026-05-01: v0.9.0 발행"],
        kind="release",
        task_id="TASK-2026-05-01-002",
    )
    text = mod.build_task_file(entry)
    match = FRONTMATTER_STATUS_RE.search(text)
    assert match is not None, f"release entry 에 status 가 없다:\n{text[:400]}"
    assert match.group(1) == "done", match.group(1)
    assert f"provenance: {TASK_PROVENANCE_MIGRATED_LEGACY}" in text, text[:400]


def test_migration_tool_never_writes_out_of_vocabulary_status() -> None:
    """어떤 kind 든 쓰는 status 는 표준 어휘 안이다 (`recorded` 재발 방지)."""
    mod = _load_migrate_tool()
    for kind in ("generic", "session", "release", "unexpected-kind"):
        entry = mod.Entry(
            raw_path="main/backlog/2026-05-01.md",
            anchor="a",
            date="2026-05-01",
            summary="s",
            body_lines=["- 2026-05-01: s"],
            kind=kind,
            task_id="TASK-2026-05-01-003",
        )
        match = FRONTMATTER_STATUS_RE.search(mod.build_task_file(entry))
        if match is None:
            continue
        assert match.group(1) in TASK_STATUSES, (
            f"kind={kind} 가 표준 어휘 밖의 status `{match.group(1)}` 를 썼다 — "
            f"builder 가 이 값을 모르면 daily index fallback 이 done 으로 되살린다"
        )


# --- 2. 비어 있는 status 를 기본값으로 채우지 않는다 ----------------------


@_with_branch
def test_missing_status_is_not_guessed() -> None:
    """`status` 줄이 없는 task 는 어느 판정 목록에도 안 가고 `<미기재>` 로 드러난다."""
    with tempfile.TemporaryDirectory() as td:
        ws = _workspace(td)
        task_id = "TASK-2026-05-01-001"
        _write_raw_task(
            ws,
            task_id=task_id,
            date="2026-05-01",
            title="판정 근거 없는 이관 잔재",
            body=(
                "---\n"
                f"id: {task_id}\n"
                "created_at: 2026-05-01\n"
                f"provenance: {TASK_PROVENANCE_MIGRATED_LEGACY}\n"
                "kind: generic\n"
                "---\n"
                "\n"
                f"# {task_id} — 판정 근거 없는 이관 잔재\n"
            ),
        )

        agg = _aggregate(ws)
        for bucket in ("done_items", "in_progress_items", "blocked_items"):
            assert task_id not in agg[bucket], (
                f"판정 근거가 없는 task 가 {bucket} 로 분류됐다 — {agg[bucket]}"
            )
        assert not any("판정 근거 없는" in item for item in agg["recent_done_items"]), (
            agg["recent_done_items"]
        )
        assert f"{task_id}: {MISSING_STATUS_MARKER}" in agg["unknown_status_items"], (
            f"미기재가 조용히 기본값으로 채워졌다 — {agg['unknown_status_items']}"
        )


@_with_branch
def test_missing_status_stays_out_of_state_payload() -> None:
    """state.json 까지 가도 완료로 나타나지 않는다 (end-to-end)."""
    with tempfile.TemporaryDirectory() as td:
        ws = _workspace(td)
        task_id = "TASK-2026-05-01-001"
        _write_raw_task(
            ws,
            task_id=task_id,
            date="2026-05-01",
            title="미판정 이관 잔재",
            body=(
                "---\n"
                f"id: {task_id}\n"
                "created_at: 2026-05-01\n"
                f"provenance: {TASK_PROVENANCE_MIGRATED_LEGACY}\n"
                "---\n"
                "\n"
                f"# {task_id} — 미판정 이관 잔재\n"
            ),
        )
        profile = ws / "docs" / "PROJECT_PROFILE.md"
        result = refresh_workflow_state_cache(
            project_profile_path=profile, generated_at="2026-07-28"
        )
        assert result["status"] == "refreshed", result
        state = json.loads(workflow_state_path(profile).read_text(encoding="utf-8"))

        recent = state["session"]["recent_done_items"]
        assert not any("미판정 이관 잔재" in item for item in recent), recent
        assert not any(task_id in item for item in recent), recent


# --- 3. 저장소의 실제 task 파일 (선언과 사실) -----------------------------


def test_repository_task_files_have_no_out_of_vocabulary_status() -> None:
    """실저장소 전수: `status` 가 있으면 반드시 표준 어휘 안이다."""
    active = REPO_ROOT / "ai-workflow" / "memory" / "active"
    if not active.exists():
        print("    (skip: ai-workflow/memory/active 없음 — 배포본)")
        return
    offenders: list[str] = []
    checked = 0
    for task_file in active.glob("*/backlog/tasks/TASK-*.md"):
        try:
            text = task_file.read_text(encoding="utf-8")
        except OSError:
            continue
        fm_match = re.match(r"^---\n(.+?)\n---", text, re.S)
        if not fm_match:
            continue
        checked += 1
        match = FRONTMATTER_STATUS_RE.search(fm_match.group(1))
        if match is not None and match.group(1) not in TASK_STATUSES:
            offenders.append(f"{task_file.relative_to(REPO_ROOT)}: {match.group(1)}")
    assert not offenders, (
        "표준 어휘 밖의 status 를 가진 task 파일이 있다 (진행 상태 축에 출처를 적은 것은 "
        "아닌지 확인할 것 — 출처는 `provenance` 로):\n  " + "\n  ".join(offenders)
    )
    print(f"    (task 파일 {checked}건 검사)")


def main() -> int:
    test_funcs = [
        test_migration_tool_omits_status_without_basis,
        test_migration_tool_writes_done_only_for_release,
        test_migration_tool_never_writes_out_of_vocabulary_status,
        test_missing_status_is_not_guessed,
        test_missing_status_stays_out_of_state_payload,
        test_repository_task_files_have_no_out_of_vocabulary_status,
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
