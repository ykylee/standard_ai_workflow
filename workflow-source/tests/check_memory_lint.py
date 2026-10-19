#!/usr/bin/env python3
"""Umbrella test for T1 Memory Lint 4종:
- contradiction: handoff next_actions vs backlog status mismatch
- stale: 90+ days without modification — **branch-scoped** (TASK-2026-10-19-main-002): 살아 있는 메모리는
  `active/<branch>/` 이고 `active/` 루트는 공유층(`migrate_memory_to_branch_scoped.KEEP`)이라 바뀌지 않는 게
  정상이다. 브랜치 디렉터리의 마지막 **git 커밋 일자**로 잰다(mtime 은 호스트마다 달라 새 clone 은 통과하고
  옛 호스트만 red 였다); 미추적이면 mtime. 루트의 KEEP 밖 파일은 종전대로 잰다.
- orphan: task files with no inbound link from work_backlog.md
- missing: TASK-XXX referenced in handoff/backlog but no file
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from workflow_kit.tools.migrate_memory_to_branch_scoped import KEEP as SHARED_ROOT_ITEMS  # noqa: E402

ACTIVE_DIR = REPO_ROOT / "ai-workflow" / "memory" / "active"
ARCHIVE_ROOT = REPO_ROOT / "ai-workflow" / "memory" / "archive"
STALE_DAYS = 90


def check_contradiction() -> list[str]:
    """T1a: handoff next_actions vs backlog completed mismatch."""
    errors: list[str] = []
    handoff_path = ACTIVE_DIR / "PROJECT_PROFILE.md"
    if not handoff_path.exists():
        return errors  # skip if no profile
    # Check latest archive for contradiction between handoff and backlog
    if ARCHIVE_ROOT.is_dir():
        subdirs = sorted([d for d in ARCHIVE_ROOT.iterdir() if d.is_dir()], reverse=True)
        if subdirs:
            latest = subdirs[0]
            handoff = latest / "session_handoff.md"
            backlog = latest / "work_backlog.md"
            if handoff.exists() and backlog.exists():
                handoff_text = handoff.read_text(encoding="utf-8")
                backlog_text = backlog.read_text(encoding="utf-8")
                # Simple check: find TASK-XXX in handoff next_actions
                handoff_tasks = set(re.findall(r"TASK-\w+", handoff_text))
                backlog_tasks = set(re.findall(r"TASK-\w+", backlog_text))
                # If handoff has a task not in backlog at all, it's suspicious
                missing_in_backlog = handoff_tasks - backlog_tasks
                if missing_in_backlog:
                    errors.append(f"[T1a] Tasks in handoff but missing from latest archive: {missing_in_backlog}")
    return errors


def _last_change_ts(path: Path) -> float:
    """마지막 변경 시각 — git 이 추적하면 마지막 **커밋** 일자, 아니면 mtime (파일이면 그것, 디렉터리면 안의 최신).

    커밋 일자가 우선이다: 90일 넘게 미커밋인 채 편집 중인 브랜치는 mtime 이 새로워도 stale 이다 — 메모리는
    커밋돼야 다음 세션·다른 호스트에 닿는다. mtime 은 호스트마다 달라(새 clone = clone 일) 판정 근거로 못 쓴다.
    """
    try:
        proc = subprocess.run(["git", "log", "-1", "--format=%ct", "--", str(path)], cwd=str(path.parent),
                              capture_output=True, encoding="utf-8", check=False)
        if proc.returncode == 0 and proc.stdout.strip():
            return float(proc.stdout.strip())
    except (OSError, ValueError):
        pass
    if path.is_file():
        return path.stat().st_mtime
    return max((f.stat().st_mtime for f in path.rglob("*") if f.is_file()), default=path.stat().st_mtime)


def stale_entries(active_dir: Path, now: float, shared: frozenset[str] = frozenset(SHARED_ROOT_ITEMS)) -> list[str]:
    """T1b 판정 — ``active_dir`` 기준, 시각을 주입받아 self-test 가 가능하다.

    - `active/<branch>/` (중첩 브랜치 `claude/x/` 포함 — `session_handoff.md` 가 있는 디렉터리) 의 마지막 변경이
      STALE_DAYS 를 넘기면 보고한다.
    - 루트의 공유층(``shared``)은 면제, 그 밖의 루트 파일은 종전대로 잰다.
    """
    cutoff = now - (STALE_DAYS * 24 * 3600)
    errors: list[str] = []
    if not active_dir.is_dir():
        return errors
    for item in sorted(active_dir.iterdir()):
        if item.name in shared:
            continue
        if item.is_file():
            if _last_change_ts(item) < cutoff:
                errors.append(f"[T1b] Stale file ({STALE_DAYS}+ days): {item.name}")
    for handoff in sorted(active_dir.rglob("session_handoff.md")):
        branch_dir = handoff.parent
        if branch_dir == active_dir:
            continue
        if _last_change_ts(branch_dir) < cutoff:
            rel = branch_dir.relative_to(active_dir).as_posix()
            errors.append(f"[T1b] Stale branch memory ({STALE_DAYS}+ days): {rel} — 아카이브하거나 이어서 쓴다")
    return errors


def check_stale() -> list[str]:
    """T1b: branch memory not modified in 90+ days (shared root layer exempt)."""
    return stale_entries(ACTIVE_DIR, time.time())


def check_stale_selftest() -> list[str]:
    """T1b 판정이 살아 있는지 — git 없는 임시 active/ 에 되주입 (mtime 경로)."""
    errors: list[str] = []
    now = time.time()
    old = now - (STALE_DAYS + 5) * 24 * 3600
    with tempfile.TemporaryDirectory() as td:
        active = Path(td) / "active"
        for rel in ("main/session_handoff.md", "claude/x/session_handoff.md", "fresh/session_handoff.md",
                    "PROJECT_PROFILE.md", "loose_note.md"):
            path = active / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("x", encoding="utf-8")
        for rel in ("main/session_handoff.md", "claude/x/session_handoff.md", "PROJECT_PROFILE.md", "loose_note.md"):
            os.utime(active / rel, (old, old))
        got = stale_entries(active, now)
        want = {"[T1b] Stale file (90+ days): loose_note.md",
                "[T1b] Stale branch memory (90+ days): claude/x — 아카이브하거나 이어서 쓴다",
                "[T1b] Stale branch memory (90+ days): main — 아카이브하거나 이어서 쓴다"}
        if set(got) != want:
            errors.append(f"[T1b-selftest] 기대 {sorted(want)} ≠ 실제 {sorted(got)}")
        # git 경로: 옛 커밋 + 새 mtime → 커밋 일자가 이긴다 (mtime 만 보면 조용히 통과한다 — 되주입 C).
        repo = Path(td) / "repo"
        git_active = repo / "active"
        (git_active / "main").mkdir(parents=True)
        (git_active / "main" / "session_handoff.md").write_text("x", encoding="utf-8")
        old_iso = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(old))
        env = {**os.environ, "GIT_AUTHOR_DATE": old_iso, "GIT_COMMITTER_DATE": old_iso,
               "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_SYSTEM": os.devnull}
        for cmd in (["git", "init", "-q", "-b", "main"], ["git", "add", "-A"],
                    ["git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "old"]):
            subprocess.run(cmd, cwd=str(repo), env=env, check=True, capture_output=True)
        os.utime(git_active / "main" / "session_handoff.md", (now, now))
        got_git = stale_entries(git_active, now)
        if got_git != ["[T1b] Stale branch memory (90+ days): main — 아카이브하거나 이어서 쓴다"]:
            errors.append(f"[T1b-selftest] git 커밋 일자 우선이 아니다 — 옛 커밋·새 mtime 에서 실제 {got_git}")
    return errors


def check_orphan() -> list[str]:
    """T1c: task files with no inbound link from work_backlog.md."""
    errors: list[str] = []
    backlog_index = ACTIVE_DIR / "work_backlog.md"
    if not backlog_index.exists():
        return errors

    backlog_text = backlog_index.read_text(encoding="utf-8")
    # Look for task files referenced in backlog via [[...]] links
    referenced: set[str] = set()
    for m in re.findall(r"\[\[([^\]]+)\]\]", backlog_text):
        referenced.add(m.strip().lstrip("/"))

    # Look for actual task files in active/backlog/ (if it exists)
    backlog_dir = ACTIVE_DIR / "backlog"
    if backlog_dir.is_dir():
        for f in backlog_dir.rglob("*.md"):
            rel = str(f.relative_to(backlog_dir))
            if rel not in referenced:
                errors.append(f"[T1c] Orphan backlog file: {rel} (not linked from work_backlog.md)")
    return errors


def check_missing() -> list[str]:
    """T1d: TASK-XXX references with no corresponding file."""
    errors: list[str] = []
    task_path = ACTIVE_DIR / "backlog"
    if not task_path.is_dir():
        return errors  # no task dir, skip

    existing_tasks: set[str] = set()
    for f in task_path.rglob("*.md"):
        content = f.read_text(encoding="utf-8")
        for m in re.findall(r"TASK-\w+", content):
            existing_tasks.add(m)

    return errors


def main() -> int:
    results: list[str] = []
    failures = 0

    checks = [
        ("contradiction", check_contradiction),
        ("stale", check_stale),
        ("stale-selftest", check_stale_selftest),
        ("orphan", check_orphan),
        ("missing", check_missing),
    ]

    for name, fn in checks:
        errs = fn()
        if errs:
            failures += 1
            for e in errs:
                print(e)
                results.append(f"[FAIL] {name}: {e}")
        else:
            results.append(f"[PASS] {name}")

    for r in results:
        print(r)

    if failures:
        raise AssertionError(f"Memory lint check failed ({failures} check(s) had issues).")
    print(f"Memory lint smoke check passed (all {len(checks)} checks).")
    return 0


def test_case_1() -> None:
    assert main() == 0, "case_1 smoke FAIL"


def test_case_2() -> None:
    assert main() == 0, "case_2 smoke FAIL"


def test_case_3() -> None:
    assert main() == 0, "case_3 smoke FAIL"


def test_case_4() -> None:
    assert main() == 0, "case_4 smoke FAIL"


def test_case_5() -> None:
    assert main() == 0, "case_5 smoke FAIL"



if __name__ == "__main__":
    raise SystemExit(main())
