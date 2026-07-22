"""state.json 을 **읽는 곳과 쓰는 곳이 같은 파일인가** (v1.0.1+).

## 왜 필요한가

v1.0.0 의 branch-scoped 전환에서 `state.json` 경로가 절반만 옮겨졌다.

- **hint** (`build_state_cache_refresh_hint`) → `workflow_state_path()` = `active/<branch>/state.json` ✅
- **writer** (`refresh_workflow_state_cache`) → `memory_dir / "state.json"` = `active/state.json` ❌

reader 는 전부 branch-scoped 를 보므로, refresh 는 **아무도 읽지 않는 파일**을 새로
만들고 정작 읽히는 `active/<branch>/state.json` 은 영원히 갱신되지 않았다. 겉으로는
"refreshed" 라고 보고하므로 조용히 실패한다 — 2026-07-21 이후 state.json 이 통째로
멈춰 있던 원인이 이것이다.

같은 호출 경로에 두 번째 결함도 있었다: `backlog-update` 가 `--apply` 없이도 state
cache 를 재생성했다. **초안만 달라는 호출이 저장소에 파일을 만든다** (skill 권한 경계
§5 위반 + dry-run 오염 — `release --auto-bump --dry-run` 과 같은 부류).

Test list (4 case):
1. test_writer_writes_branch_scoped_path
2. test_hint_path_matches_writer_path          ← writer ↔ reader 정합
3. test_legacy_repo_still_writes_legacy_path   ← 미마이그레이션 저장소 호환
4. test_backlog_update_draft_does_not_write_state

Cross-ref: workflow-source/MEMORY_GOVERNANCE.md §2 (branch-scoped layout) +
workflow_kit/common/paths.py `workflow_state_path`.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SOURCE_ROOT))

TEST_BRANCH = "smoke-branch"


def _make_workspace(td: str, *, legacy: bool = False) -> Path:
    """branch-scoped(또는 legacy) 메모리 layout 을 갖춘 최소 workspace.

    `PROJECT_PROFILE.md` 는 docs/ 에 둔다 (bootstrap 정식 배치).
    """
    ws = Path(td)
    (ws / "docs").mkdir(parents=True, exist_ok=True)
    (ws / "docs" / "PROJECT_PROFILE.md").write_text("# Profile\n", encoding="utf-8")
    active = ws / "ai-workflow" / "memory" / "active"
    if legacy:
        # 미마이그레이션 저장소 — active/ 바로 아래에 state.json 과 backlog/ 가 있다.
        (active / "backlog" / "tasks").mkdir(parents=True, exist_ok=True)
        (active / "state.json").write_text("{}", encoding="utf-8")
    else:
        base = active / TEST_BRANCH
        (base / "backlog" / "tasks").mkdir(parents=True, exist_ok=True)
        (base / "sessions").mkdir(parents=True, exist_ok=True)
        (base / "state.json").write_text("{}", encoding="utf-8")
    return ws


def _refresh(ws: Path) -> dict:
    from workflow_kit.common.workflow_state import refresh_workflow_state_cache

    return refresh_workflow_state_cache(
        project_profile_path=ws / "docs" / "PROJECT_PROFILE.md",
        generated_at="2026-07-22",
    )


def _with_branch(fn):
    """`CODEX_WORKFLOW_BRANCH` 로 브랜치를 고정 — 실행 저장소의 브랜치에 의존하지 않는다."""
    def wrapper() -> None:
        before = os.environ.get("CODEX_WORKFLOW_BRANCH")
        os.environ["CODEX_WORKFLOW_BRANCH"] = TEST_BRANCH
        try:
            fn()
        finally:
            if before is None:
                os.environ.pop("CODEX_WORKFLOW_BRANCH", None)
            else:
                os.environ["CODEX_WORKFLOW_BRANCH"] = before
    wrapper.__name__ = fn.__name__
    return wrapper


# --- Tests ---


@_with_branch
def test_writer_writes_branch_scoped_path() -> None:
    """refresh 는 `active/<branch>/state.json` 을 갱신하고, legacy 파일을 만들지 않는다."""
    with tempfile.TemporaryDirectory() as td:
        ws = _make_workspace(td)
        result = _refresh(ws)
        assert result["status"] == "refreshed", result
        branch_scoped = ws / "ai-workflow" / "memory" / "active" / TEST_BRANCH / "state.json"
        legacy = ws / "ai-workflow" / "memory" / "active" / "state.json"
        assert Path(result["state_path"]) == branch_scoped.resolve(), result["state_path"]
        assert json.loads(branch_scoped.read_text(encoding="utf-8")), "branch-scoped 가 비어 있다"
        assert not legacy.exists(), "아무도 읽지 않는 legacy state.json 을 만들었다"


@_with_branch
def test_hint_path_matches_writer_path() -> None:
    """hint 가 알려주는 경로와 writer 가 실제로 쓰는 경로가 같아야 한다."""
    from workflow_kit.common.workflow_state import build_state_cache_refresh_hint

    with tempfile.TemporaryDirectory() as td:
        ws = _make_workspace(td)
        hint = build_state_cache_refresh_hint(
            project_profile_path=ws / "docs" / "PROJECT_PROFILE.md",
        )
        written = _refresh(ws)["state_path"]
        assert Path(hint["state_path"]) == Path(written), (hint["state_path"], written)


@_with_branch
def test_legacy_repo_still_writes_legacy_path() -> None:
    """branch-scoped 가 없고 legacy 만 있는 저장소는 계속 legacy 를 갱신한다."""
    with tempfile.TemporaryDirectory() as td:
        ws = _make_workspace(td, legacy=True)
        result = _refresh(ws)
        legacy = ws / "ai-workflow" / "memory" / "active" / "state.json"
        assert Path(result["state_path"]) == legacy.resolve(), result["state_path"]


@_with_branch
def test_backlog_update_draft_does_not_write_state() -> None:
    """`--apply` 없는 backlog-update 는 저장소에 아무것도 쓰지 않는다."""
    with tempfile.TemporaryDirectory() as td:
        ws = _make_workspace(td)
        before = sorted(p.relative_to(ws) for p in ws.rglob("*") if p.is_file())
        env = dict(os.environ)
        env["PYTHONPATH"] = str(SOURCE_ROOT)
        proc = subprocess.run(
            [sys.executable,
             str(SOURCE_ROOT / "skills" / "backlog-update" / "scripts" / "run_backlog_update.py"),
             "--project-profile-path", str(ws / "docs" / "PROJECT_PROFILE.md"),
             "--task-name", "draft only",
             "--task-brief", "draft only",
             "--target-date", "2026-07-22",
             "--mode", "create"],
            capture_output=True, text=True, check=False, env=env, cwd=str(ws),
        )
        assert proc.returncode == 0, proc.stderr[-2000:]
        payload = json.loads(proc.stdout)
        assert payload["state_cache_status"] == "skipped", payload["state_cache_status"]
        after = sorted(p.relative_to(ws) for p in ws.rglob("*") if p.is_file())
        assert after == before, f"draft 모드가 파일을 만들었다: {set(after) - set(before)}"


def main() -> int:
    test_funcs = [
        test_writer_writes_branch_scoped_path,
        test_hint_path_matches_writer_path,
        test_legacy_repo_still_writes_legacy_path,
        test_backlog_update_draft_does_not_write_state,
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
