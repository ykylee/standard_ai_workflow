#!/usr/bin/env python3
r"""worktree 합류 반영 — 모 브랜치에 병합된 브랜치 메모리가 모 브랜치 메모리에 기록된다 (6 cases).

## 왜 이 검사가 필요한가 (TASK-2026-10-02-main-004)

110·111차는 worktree 브랜치가 main 에 fast-forward 된 뒤 main 세션이 **손으로** 브랜치 메모리를 강제
아카이브하고 handoff §5 포인터를 적었다. 손일이 빠지면 worktree 의 task 는 `archived/` 로 들어가 main
집계에서 사라지고, 열린 task 는 아카이브를 막고, 이어받은 task 의 결과는 브랜치가 삭제된 뒤에야 돌아온다.
소유자 결정(2026-10-02): HEAD 에 병합된 브랜치 네임스페이스는 **worktree 가 살아 있어도** 기본 브랜치
체크아웃의 session-start 가 반영 + 아카이브한다.

판정이 호스트 저장소에 달리지 않게 매 case 가 임시 저장소(origin + clone + 살아 있는 `git worktree`)를
만들고 브랜치·CI env 를 비운 좁은 환경에서 모듈을 띄운다.

5 cases:
  1) 병합된 살아 있는 worktree 브랜치 → main 의 session-start 가 반영한다: 이어받은 task 의 결과를 원본에
     되돌려 적고 handoff 목록을 옮긴다 · 자체 완료 task 는 '최근 완료' · 자체 열린 task 는 `merged_from`
     원류와 함께 이월(브랜치 사본은 `carried_over_to`) · §5 합류 줄(브랜치@sha) · 합류 기록 · 아카이브.
     worktree 는 그대로 살아 있고, 두 번째 시작에는 정합 경고도 재반영도 없다
  2) 병합 뒤 브랜치에 새 커밋이 있으면(tip 이 HEAD 의 조상이 아니다) 반영하지 않는다
  3) 기본 브랜치가 아닌 체크아웃은 남의 네임스페이스가 섞여 들어와도 반영하지 않는다
  4) `--no-reflect` 면 병합된 살아 있는 브랜치를 건드리지 않는다
  5) 이월할 열린 task 가 모 브랜치에 같은 ID 로 있으면 막는다 — 아무것도 옮기지 않는다
  6) worktree 에서 브랜치 오버라이드로 기본 브랜치를 강제해도(`CODEX_WORKFLOW_BRANCH=main`) 실제 checkout
     브랜치는 반영 · 아카이브하지 않는다 — 115차 게이트에서 저장소 관찰 검사가 자기 브랜치 메모리를
     archived/ 로 옮겼다 (TASK-2026-10-02-claude-remote-sync-status-1ce0a3-003)
"""

from __future__ import annotations

#: 이 검사의 입력 표면 (spec `core/test_impact_tiering_spec.md` §2).
WATCHES = (
    "workflow-source/pyproject.toml",
    "workflow-source/workflow_kit/*",
)

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
sys.path.insert(0, str(SOURCE_ROOT))

from workflow_kit.common.reconcile import STATE_CONFLICT_MARKER  # noqa: E402
from workflow_kit.common.state.memory_index import TELEMETRY_SKIP_ROOT_ENV  # noqa: E402

FAILURES: list[str] = []
JOIN_MARK = "합류한 브랜치"
MEM = Path("ai-workflow") / "memory"


def _record(name: str, ok: bool, detail: str = "") -> None:
    print(f"{'PASS' if ok else 'FAIL'}: {name}" + ("" if ok else f" — {detail}"))
    if not ok:
        FAILURES.append(name)


def _env() -> dict[str, str]:
    env = {"PYTHONPATH": str(SOURCE_ROOT), "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
           "HOME": os.environ.get("HOME", "/tmp"), "GIT_CONFIG_NOSYSTEM": "1"}
    if TELEMETRY_SKIP_ROOT_ENV in os.environ:
        env[TELEMETRY_SKIP_ROOT_ENV] = os.environ[TELEMETRY_SKIP_ROOT_ENV]
    return env


def _git(cwd: Path, *args: str) -> str:
    return subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", *args], cwd=cwd, check=True,
                          capture_output=True, text=True, env=_env()).stdout.strip()


def _module(cwd: Path, module: str, *args: str,
            extra_env: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-m", module, *args], cwd=cwd, capture_output=True, text=True,
                          env={**_env(), **(extra_env or {})}, timeout=180)


def _session_start(cwd: Path, extra_env: dict[str, str] | None = None) -> dict:
    proc = _module(cwd, "workflow_kit.tools.session_start", extra_env=extra_env)
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        return {"status": "unparsable", "warnings": [proc.stderr[-300:]]}


def _backlog(cwd: Path, *args: str) -> subprocess.CompletedProcess:
    return _module(cwd, "workflow_kit.tools.backlog_update", "--project-profile-path", "docs/PROJECT_PROFILE.md",
                   "--apply", *args)


def _task(task_id: str, status: str, title: str) -> str:
    return (f"---\nid: {task_id}\nstatus: {status}\nsource_path: backlog/2026-10-01.md\nkind: generic\n---\n\n"
            f"# {task_id} — {title}\n\n## 📝 Description\n\n- 상태: {status}\n")


def _make(tmp: Path) -> tuple[Path, Path]:
    """origin(main 메모리: 차단 1 · 계획 1) → clone(main) + 살아 있는 worktree(claude/w)."""
    origin = tmp / "origin"
    base = origin / MEM / "active" / "main"
    (origin / "docs").mkdir(parents=True)
    (base / "backlog" / "tasks").mkdir(parents=True)
    (base / "sessions").mkdir()
    _git(tmp, "init", "-q", "-b", "main", str(origin))
    (origin / "docs" / "PROJECT_PROFILE.md").write_text("# Project Profile\n\n- 프로젝트명: join probe\n", encoding="utf-8")
    (base / "sessions" / "s.md").write_text("# s\n", encoding="utf-8")
    (base / "session_handoff.md").write_text(
        "# Session Handoff\n\n## 1. 현재 작업 요약\n\n- 현재 기준선: 모 기준선\n- 현재 주 작업 축: 모 축\n\n"
        "## 2. 진행 중 작업\n\n- 현재 `in_progress` 작업:\n-\n\n## 3. 차단 작업\n\n- 현재 `blocked` 작업:\n"
        "- TASK-2026-10-01-main-001 막힌 일\n\n## 4. 최근 완료 작업\n\n- 최근 완료 작업 목록:\n\n"
        "## 5. 다음 세션 시작 포인트\n\n- 모 다음 걸음\n", encoding="utf-8")
    index = ["# Backlog Index", "", "## Tasks", ""]
    for task_id, status, title in (("TASK-2026-10-01-main-001", "blocked", "막힌 일"),
                                   ("TASK-2026-10-01-main-002", "planned", "할 일")):
        (base / "backlog" / "tasks" / f"{task_id}.md").write_text(_task(task_id, status, title), encoding="utf-8")
        index += [f"- **{task_id}** [generic] {title}", f"  - path: [x](./tasks/{task_id}.md)", f"  - status: {status}"]
    (base / "backlog" / "2026-10-01.md").write_text("\n".join(index) + "\n", encoding="utf-8")
    _git(origin, "add", "-A")
    _git(origin, "commit", "-qm", "init")
    clone, wt = tmp / "clone", tmp / "wt"
    _git(tmp, "clone", "-q", str(origin), str(clone))
    _git(clone, "worktree", "add", "-q", str(wt), "-b", "claude/w")
    return clone, wt


def _work_in_worktree(wt: Path) -> dict[str, str]:
    """이어받기 → 이어받은 task 완료 · 자체 task 완료 1 · 계획 1 → 커밋."""
    _session_start(wt)
    _backlog(wt, "--task-id", "TASK-2026-10-01-main-002", "--mode", "update", "--task-name", "x",
             "--status", "done", "--validation-result", "검증", "--result-note", "worktree 에서 끝냄")
    created = {}
    for key, title in (("done", "자체 완료 일"), ("open", "자체 남은 일")):
        proc = _backlog(wt, "--task-name", title, "--task-brief", title, "--status",
                        "in_progress" if key == "done" else "planned", "--wbs", "exempt", "--wbs-exempt-reason", "probe")
        created[key] = json.loads(proc.stdout)["task_id"]
    _backlog(wt, "--task-id", created["done"], "--mode", "update", "--task-name", "x", "--status", "done",
             "--validation-result", "검증")
    _git(wt, "add", "-A")
    _git(wt, "commit", "-qm", "worktree work")
    return created


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="join-reflect-") as raw:
        tmp = Path(raw)

        # --- case 1: 병합된 살아 있는 worktree → 반영 -------------------------------
        clone, wt = _make(tmp / "c1")
        own = _work_in_worktree(wt)
        sha = _git(wt, "rev-parse", "--short", "HEAD")
        _git(clone, "merge", "-q", "--ff-only", "claude/w")
        first = _session_start(clone)
        active, archived = clone / MEM / "active", clone / MEM / "archived"
        main_dir = active / "main"
        handoff = (main_dir / "session_handoff.md").read_text(encoding="utf-8")
        recent = handoff.split("최근 완료 작업 목록:", 1)[-1].split("## 5.", 1)[0]
        carried = main_dir / "backlog" / "tasks" / f"{own['open']}.md"
        carried_text = carried.read_text(encoding="utf-8") if carried.is_file() else ""
        branch_copy = archived / "claude" / "w" / "backlog" / "tasks" / f"{own['open']}.md"
        written = (main_dir / "backlog" / "tasks" / "TASK-2026-10-01-main-002.md").read_text(encoding="utf-8")
        problems = []
        if not any(JOIN_MARK in w for w in first.get("warnings", [])):
            problems.append("합류 warning 없음")
        if "status: done" not in written or "inherited_from" in written:
            problems.append("이어받은 task 결과가 원본에 원류 줄 없이 안 돌아왔다")
        if "TASK-2026-10-01-main-002" not in recent or own["done"] not in recent:
            problems.append(f"최근 완료 목록: {recent.strip()[:200]}")
        if f"merged_from: claude/w@{sha}" not in carried_text:
            problems.append("열린 자체 task 가 원류와 함께 이월되지 않았다")
        if not branch_copy.is_file() or "carried_over_to:" not in branch_copy.read_text(encoding="utf-8"):
            problems.append("브랜치 사본에 이월 표시 없음")
        if f"(합류 `claude/w@{sha}`" not in handoff:
            problems.append("§5 합류 줄 없음")
        if not list((main_dir / "sessions").glob("merge_claude-w_*.md")):
            problems.append("합류 기록 없음")
        if (active / "claude" / "w").exists():
            problems.append("아카이브되지 않았다")
        if not wt.is_dir() or "claude/w" not in _git(clone, "worktree", "list"):
            problems.append("worktree 가 사라졌다")
        again = _session_start(clone)
        if any(JOIN_MARK in w or STATE_CONFLICT_MARKER in w for w in again.get("warnings", [])):
            problems.append(f"두 번째 시작 warning: {again.get('warnings')}")
        _record("test_merged_live_worktree_is_reflected", first.get("status") == "ok" and not problems,
                "; ".join(problems))

        # --- case 2: 병합 뒤 브랜치가 더 나갔다 → 반영 안 함 -------------------------
        clone, wt = _make(tmp / "c2")
        _work_in_worktree(wt)
        _git(clone, "merge", "-q", "--ff-only", "claude/w")
        (wt / "later.txt").write_text("x\n", encoding="utf-8")
        _git(wt, "add", "-A")
        _git(wt, "commit", "-qm", "after merge")
        result = _session_start(clone)
        _record("test_branch_ahead_of_head_is_not_reflected",
                not any(JOIN_MARK in w for w in result.get("warnings", []))
                and (clone / MEM / "active" / "claude" / "w").is_dir(),
                f"warnings={[w[:80] for w in result.get('warnings', [])]}")

        # --- case 3: 기본 브랜치가 아닌 체크아웃 → 반영 안 함 ------------------------
        clone, wt = _make(tmp / "c3")
        _work_in_worktree(wt)
        _git(clone, "checkout", "-q", "-b", "feat/other")
        _git(clone, "merge", "-q", "--ff-only", "claude/w")
        result = _session_start(clone)
        _record("test_non_default_checkout_does_not_reflect",
                not any(JOIN_MARK in w for w in result.get("warnings", []))
                and (clone / MEM / "active" / "claude" / "w").is_dir(),
                f"warnings={[w[:80] for w in result.get('warnings', [])]}")

        # --- case 4: --no-reflect ---------------------------------------------------
        clone, wt = _make(tmp / "c4")
        _work_in_worktree(wt)
        _git(clone, "merge", "-q", "--ff-only", "claude/w")
        proc = _module(clone, "workflow_kit.tools.archive_branch_memory", "--apply", "--json", "--no-reflect")
        out = json.loads(proc.stdout)
        _record("test_no_reflect_leaves_merged_branch",
                not out.get("joined") and (clone / MEM / "active" / "claude" / "w").is_dir(),
                f"joined={out.get('joined')}")

        # --- case 5: 이월 ID 충돌 → 막는다 -------------------------------------------
        clone, wt = _make(tmp / "c5")
        own = _work_in_worktree(wt)
        _git(clone, "merge", "-q", "--ff-only", "claude/w")
        clash = clone / MEM / "active" / "main" / "backlog" / "tasks" / f"{own['open']}.md"
        clash.write_text(_task(own["open"], "planned", "모 브랜치에 먼저 생긴 같은 ID"), encoding="utf-8")
        before = (clone / MEM / "active" / "main" / "session_handoff.md").read_bytes()
        proc = _module(clone, "workflow_kit.tools.archive_branch_memory", "--apply", "--json")
        out = json.loads(proc.stdout)
        blocked = [c for c in out.get("candidates", []) if c.get("action") == "blocked"]
        _record("test_carry_clash_blocks",
                bool(blocked) and own["open"] in blocked[0].get("reason", "") and not out.get("joined")
                and (clone / MEM / "active" / "claude" / "w").is_dir()
                and (clone / MEM / "active" / "main" / "session_handoff.md").read_bytes() == before,
                f"candidates={out.get('candidates')}")

        # --- case 6: worktree 에서 기본 브랜치 강제 → 자기 브랜치를 건드리지 않는다 ----
        clone, wt = _make(tmp / "c6")
        _work_in_worktree(wt)
        before = (wt / MEM / "active" / "main" / "session_handoff.md").read_bytes()
        result = _session_start(wt, extra_env={"CODEX_WORKFLOW_BRANCH": "main"})
        status = _git(wt, "status", "--porcelain")
        _record("test_forced_default_in_worktree_keeps_own_branch",
                not any(JOIN_MARK in w for w in result.get("warnings", []))
                and (wt / MEM / "active" / "claude" / "w").is_dir()
                and not (wt / MEM / "archived" / "claude" / "w").exists()
                and (wt / MEM / "active" / "main" / "session_handoff.md").read_bytes() == before
                and status == "",
                f"warnings={[w[:80] for w in result.get('warnings', [])]} status={status[:200]}")

    print()
    if FAILURES:
        print(f"=== FAIL: {len(FAILURES)} case(s) — {FAILURES} ===")
        return 1
    print("=== PASS: branch join reflect (6 cases) ===")
    return 0


def test_branch_join_reflect() -> None:
    assert main() == 0, "branch join reflect FAIL"


if __name__ == "__main__":
    raise SystemExit(main())
