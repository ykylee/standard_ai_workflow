#!/usr/bin/env python3
r"""Smoke test — `tools/seed_workspace_memory.py` (6 cases).

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

6 cases:
  1) dry-run 은 아무것도 쓰지 않는다
  2) **apply 후 session-start 가 status=ok + (seed 산출물發) warnings 없이 돈다** (핵심)
     — `state.json 부재` 한 줄은 제외한다. seed 는 파생 파일을 만들지 않으므로
     정상이고, 그 줄을 판정에 넣으면 결과가 **호스트 저장소의 브랜치 상태**에
     달린다 (main 통과 / detached HEAD·메모리 없는 브랜치 FAIL).
  3) 멱등 — 재실행이 기존 handoff/backlog 를 덮어쓰지 않고 task 번호만 증가
  4) state.json 까지 생성기로 만든다 — seed 한 번으로 시작 가능한 상태가 된다
  5) 갓 seed 한 sessions/ 가 비어 있지 않고, 첫 세션 기록이 seed 사건을 담는다 (main-005)
  6) 생성된 task 파일이 append-only layout frontmatter 규약에 맞는다

Refs:
  - core/global_workflow_standard.md §10.2
  - core/multi_workspace_orchestration.md §5A.2 (실패 실측)
  - MEMORY_GOVERNANCE.md §2 (task frontmatter)
"""

from __future__ import annotations

#: 이 검사의 입력 표면 (spec `core/test_impact_tiering_spec.md` §2).
#: 게이트 채취 실측에서 뽑아 넓은 쪽으로 올렸다 — 좁으면 meta-watch 가 red 로 잡는다.
WATCHES = (
    "docs/PROJECT_PROFILE.md",
    "workflow-source/pyproject.toml",
    "workflow-source/workflow_kit/*",
)

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
        # 대상 workspace 의 profile. 이전에는 이 fixture 에 profile 이 없었고,
        # seed 가 **모듈 저장소의** profile 을 빌려 state.json 을 만들어서 green
        # 이었다 — 소비자 workspace 에 kit 의 프로젝트 메타를 찍는 결함족의 한
        # 모양이다 (TASK-2026-08-28-main-013). 이제 대상 트리에서 찾는다.
        (Path(tmp) / "docs").mkdir(parents=True, exist_ok=True)
        (Path(tmp) / "docs" / "PROJECT_PROFILE.md").write_text(
            PROFILE.read_text(encoding="utf-8"), encoding="utf-8")
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

        # --- case 4: state.json 까지 만들어 **시작 가능한 상태**로 끝낸다 ------
        #
        # v1.2.1 에서 계약이 뒤집혔다. 이전 계약은 "파생 파일이므로 seed 는 만들지
        # 않는다" 였는데, 그 결과 seed 직후의 브랜치가 항상 절반짜리였고
        # `check_appendonly_memory_layout` / `check_memory_freeze_lint` /
        # `check_branch_context_matrix` 가 red 였다 (2026-08-13 에 두 번 밟았다).
        # **여전히 생성물이다** — seed 가 손으로 쓰는 게 아니라 생성기를 호출한다.
        # 달라진 것은 "누가 그 호출을 책임지는가" 이고, 답은 seed 다.
        state_path = branch_dir / "state.json"
        _record("test_state_json_generated", state_path.is_file(),
                "seed 가 state.json 을 만들지 않아 브랜치가 절반짜리로 남는다")
        if state_path.is_file():
            sot = json.loads(state_path.read_text(encoding="utf-8")).get("source_of_truth", {})
            # **브랜치 축 key 만 본다.** `project_profile_path` 는 브랜치 무관 공유
            # 문서라 여기 섞으면 정상을 FAIL 로 만든다 (처음에 그렇게 걸렸다).
            branch_keys = ("session_handoff_path", "daily_backlog_dir", "tasks_dir", "sessions_dir")
            # **절대/상대 둘 다 정상이다.** state.json 의 경로는 workspace 안이면
            # 저장소 상대로 적힌다 (`safe_relpath`) — profile 이 대상 workspace 에
            # 있게 된 뒤로 이쪽이 정상 형태다 (TASK-2026-08-28-main-013). 그래서
            # 절대 경로 접두가 아니라 **브랜치 구간**이 들어 있는지를 본다.
            branch_segment = f"active/{BRANCH}"
            wrong = {k: sot.get(k) for k in branch_keys
                     if branch_segment not in str(sot.get(k)).replace("\\", "/")}
            _record(
                "test_state_json_points_at_branch",
                not wrong,
                f"state.json 이 이 브랜치를 가리키지 않는다: {wrong}",
            )

        # --- case 5: 갓 seed 한 브랜치가 layout 판정을 통과한다 (main-005) ----
        #
        # 빈 `sessions/` 만 만들던 때는 `check_appendonly_memory_layout` 이 seed
        # 직후에도 red 였다 — "한 벌이면 green" 이 거짓이었다. 판정 술어는 layout
        # 검사의 case 1 과 같다: **`.gitkeep` 제외 파일 1개 이상**. 검사를 "갓 만든
        # 것" 예외로 푸는 방향은 일부러 피했다 (오래된 절반짜리도 같이 통과한다) —
        # 대신 seed 가 seed 사건 자체를 담은 첫 세션 기록을 쓴다.
        session_files = [f for f in (branch_dir / "sessions").iterdir()
                         if f.name != ".gitkeep"]
        _record("test_sessions_not_empty_after_seed", bool(session_files),
                "seed 직후 sessions/ 가 비어 있다 — layout 검사가 red 가 된다")
        if session_files:
            record_text = session_files[0].read_text(encoding="utf-8")
            _record("test_session_record_is_truthful",
                    task_id in record_text and BRANCH in record_text,
                    f"세션 기록이 seed 사건(브랜치·task)을 담지 않는다: {session_files[0].name}")

        # --- case 6: task frontmatter 규약 --------------------------------
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
    print("=== PASS: seed_workspace_memory smoke (11 assertions) ===")
    return 0


def test_seed_workspace_memory() -> None:
    assert main() == 0, "seed_workspace_memory smoke FAIL"


if __name__ == "__main__":
    raise SystemExit(main())
