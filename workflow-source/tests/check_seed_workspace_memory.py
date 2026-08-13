#!/usr/bin/env python3
r"""Smoke test — `tools/seed_workspace_memory.py` (5 cases).

## 왜 이 검사가 필요한가

새 워크스페이스의 메모리는 아무도 만들어 주지 않는다. 그래서 브랜치만 만들고
`session-start` 를 돌리면 `missing_required_document` 로 **시작조차 못 한다**
(2026-08-07 실측). seed 도구는 그 실패를 닫는 도구이므로, **정말로 닫혔는지**를
검사가 직접 확인해야 한다 — 파일이 생겼는지가 아니라 `session-start` 가 도는지를 본다.

seed 가 만드는 문서는 `session-start` 파서와 **문구 단위로** 맞아야 한다. 실제로
초안에서 세 번 어긋났다:

- `주 작업 축` vs 정본 `현재 주 작업 축` → 필수 섹션 누락 warning
- 백틱 포함 → summary 에 깨진 문자열이 새어 나옴
- `- <ID> <제목>: <상태>` 형식 → 파서는 `현재 \`in_progress\` 작업:` 라벨 뒤의 목록을
  읽으므로 handoff in_progress 가 **빈 리스트**가 되고 backlog 와 불일치 warning

셋 다 "파일은 생겼는데 복원은 안 되는" 부류다. case 2 가 이 부류를 통째로 막는다.

5 cases:
  1) dry-run 은 아무것도 쓰지 않는다
  2) **apply 후 session-start 가 status=ok + (seed 산출물發) warnings 없이 돈다** (핵심)
     — `state.json 부재` 한 줄은 제외한다. seed 는 파생 파일을 만들지 않으므로
     정상이고, 그 줄을 판정에 넣으면 결과가 **호스트 저장소의 브랜치 상태**에
     달린다 (main 통과 / detached HEAD·메모리 없는 브랜치 FAIL).
  3) 멱등 — 재실행이 기존 handoff/backlog 를 덮어쓰지 않고 task 번호만 증가
  4) state.json 을 만들지 않는다 (파생 파일은 rebuild 담당)
  5) 생성된 task 파일이 append-only layout frontmatter 규약에 맞는다

Refs:
  - core/global_workflow_standard.md §10.2
  - core/multi_workspace_orchestration.md §5A.2 (실패 실측)
  - MEMORY_GOVERNANCE.md §2 (task frontmatter)
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
sys.path.insert(0, str(SOURCE_ROOT))

from workflow_kit.common.purpose_graph import STATE_ABSENT_WARNING  # noqa: E402

SEED_TOOL = SOURCE_ROOT / "workflow_kit" / "tools" / "seed_workspace_memory.py"
SESSION_START = SOURCE_ROOT / "skills" / "session-start" / "scripts" / "run_session_start.py"
PROFILE = REPO_ROOT / "docs" / "PROJECT_PROFILE.md"

BRANCH = "feat-seed-smoke"
TODAY = "2026-08-07"
AXIS = "seed smoke 축"
TITLE = "seed smoke task"

FAILURES: list[str] = []


def _record(name: str, ok: bool, detail: str = "") -> None:
    print(f"{'PASS' if ok else 'FAIL'}: {name}" + ("" if ok else f" — {detail}"))
    if not ok:
        FAILURES.append(name)


def _run(args: list[str]) -> subprocess.CompletedProcess:
    env = {"PYTHONPATH": str(SOURCE_ROOT), "PATH": "/usr/bin:/bin:/usr/local/bin"}
    return subprocess.run([sys.executable, *args], capture_output=True, text=True, env=env)


def _seed(memory_root: Path, *, apply: bool, axis: str = AXIS,
          title: str = TITLE) -> dict:
    args = [
        str(SEED_TOOL), "--memory-root", str(memory_root), "--branch", BRANCH,
        "--axis", axis, "--task-title", title, "--today", TODAY, "--json",
    ]
    args.append("--apply" if apply else "--dry-run")
    proc = _run(args)
    assert proc.returncode == 0, f"seed 실패: {proc.stderr}"
    return json.loads(proc.stdout)


def _session_start(branch_dir: Path) -> dict:
    proc = _run([
        str(SESSION_START),
        "--session-handoff-path", str(branch_dir / "session_handoff.md"),
        "--work-backlog-index-path", str(branch_dir / "backlog" / f"{TODAY}.md"),
        "--project-profile-path", str(PROFILE),
    ])
    return json.loads(proc.stdout)


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        memory_root = Path(tmp) / "ai-workflow" / "memory"
        (memory_root / "active").mkdir(parents=True)
        branch_dir = memory_root / "active" / BRANCH

        # --- case 1: dry-run 은 쓰지 않는다 -------------------------------
        _seed(memory_root, apply=False)
        _record("test_dry_run_writes_nothing", not branch_dir.exists(),
                f"dry-run 이 {branch_dir} 를 만들었다")

        # --- case 2: apply 후 session-start 가 깨끗이 돈다 (핵심) ----------
        result = _seed(memory_root, apply=True)
        started = _session_start(branch_dir)
        _record(
            "test_session_start_ok_after_seed",
            started.get("status") == "ok",
            f"status={started.get('status')} error_code={started.get('error_code')}",
        )
        # seed 산출물에서 온 warning 만 본다. `state.json 부재` 는 **호스트 저장소**의
        # 상태에서 오던 잡음이었다: 이 검사는 임시 workspace 를 판정한다면서
        # `--project-profile-path` 로 실제 저장소를 가리켜, state.json 을 그쪽에서
        # 찾고 있었다. main 에서는 그게 채워져 있어 통과했고, detached HEAD(=CI 의 PR
        # checkout)나 메모리 디렉터리 없는 브랜치에서는 못 찾아 FAIL 했다 — 판정이
        # seed 산출물이 아니라 호스트 상태에 달려 있었다. seed 는 state.json 을
        # 일부러 만들지 않으므로(아래 test_no_state_json) 이 한 줄은 정상이다.
        residual = [w for w in started.get("warnings", []) if w != STATE_ABSENT_WARNING]
        _record(
            "test_session_start_has_no_warnings",
            not residual,
            f"warnings={started.get('warnings')}",
        )
        task_id = result["task_id"]
        _record(
            "test_in_progress_roundtrips",
            any(task_id in item for item in started.get("in_progress_items", [])),
            f"in_progress={started.get('in_progress_items')}",
        )

        # --- case 3: 멱등 ------------------------------------------------
        handoff = branch_dir / "session_handoff.md"
        before = handoff.read_text(encoding="utf-8")
        second = _seed(memory_root, apply=True, axis="다른 축", title="다른 제목")
        _record("test_rerun_preserves_handoff",
                handoff.read_text(encoding="utf-8") == before,
                "재실행이 기존 handoff 를 덮어썼다")
        _record("test_rerun_increments_task_id", second["task_id"] != task_id,
                f"task_id 가 재사용됐다: {second['task_id']}")

        # --- case 4: state.json 은 만들지 않는다 ---------------------------
        _record("test_no_state_json", not (branch_dir / "state.json").exists(),
                "seed 가 파생 파일 state.json 을 만들었다")

        # --- case 5: task frontmatter 규약 --------------------------------
        task_file = branch_dir / "backlog" / "tasks" / f"{task_id}.md"
        text = task_file.read_text(encoding="utf-8")
        required = ("id:", "status:", "created_at:", "source_anchor:", "source_path:", "kind:")
        missing = [k for k in required if k not in text]
        _record("test_task_frontmatter_complete", not missing and text.startswith("---"),
                f"누락 키: {missing}")

    print()
    if FAILURES:
        print(f"=== FAIL: {len(FAILURES)} case(s) — {FAILURES} ===")
        return 1
    print("=== PASS: seed_workspace_memory smoke (7 assertions) ===")
    return 0


def test_seed_workspace_memory() -> None:
    assert main() == 0, "seed_workspace_memory smoke FAIL"


if __name__ == "__main__":
    raise SystemExit(main())
