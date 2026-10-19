#!/usr/bin/env python3
"""Umbrella test for T1 Memory Lint — branch-scoped (TASK-2026-10-19-main-002 · main-003).

- contradiction (T1a): **은퇴.** `archive/<latest>/work_backlog.md` 를 보던 legacy 경로라 항상 skip 됐다.
  handoff ↔ backlog 상태 정합은 `check_state_reconcile.py`(ID 키 양방향, TASK-2026-09-02-main-002)가 정본이다.
- stale: 90+ days without modification — **branch-scoped** (TASK-2026-10-19-main-002): 살아 있는 메모리는
  `active/<branch>/` 이고 `active/` 루트는 공유층(`migrate_memory_to_branch_scoped.KEEP`)이라 바뀌지 않는 게
  정상이다. 브랜치 디렉터리의 마지막 **git 커밋 일자**로 잰다(mtime 은 호스트마다 달라 새 clone 은 통과하고
  옛 호스트만 red 였다); 미추적이면 mtime. 루트의 KEEP 밖 파일은 종전대로 잰다.
- orphan (T1c): `active/<branch>/backlog/tasks/*.md` 가 같은 브랜치의 `backlog/<date>.md` 어디에도 안 보이면 red.
  legacy 는 `active/work_backlog.md` 를 봐서 항상 skip 됐다.
- missing (T1d): handoff · daily index 가 참조한 TASK id 는 그 브랜치 `tasks/` 또는 `archived/**/backlog/tasks/`
  (합류한 worktree 브랜치 — 118차 실측 7건) 에 파일이 있어야 한다. legacy 는 errors 를 채우지 않아 항상 PASS 였다.
  ID 정규식(`project_docs.TASK_ID_PATTERN`)이 못 읽는 task 파일 stem 은 따로 red — 조용한 미분류 금지.
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

from workflow_kit.common.project_docs import TASK_ID_PATTERN  # noqa: E402
from workflow_kit.tools.migrate_memory_to_branch_scoped import (  # noqa: E402
    KEEP as SHARED_ROOT_ITEMS,
)

ACTIVE_DIR = REPO_ROOT / "ai-workflow" / "memory" / "active"
ARCHIVED_BRANCHES = REPO_ROOT / "ai-workflow" / "memory" / "archived"
TASK_ID_RE = re.compile(rf"\b{TASK_ID_PATTERN}\b")
STALE_DAYS = 90


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


def _branch_dirs(active_dir: Path) -> list[Path]:
    """`session_handoff.md` 가 있는 디렉터리 = 브랜치 메모리 (중첩 브랜치 `claude/x/` 포함, 루트 제외)."""
    return sorted(h.parent for h in active_dir.rglob("session_handoff.md") if h.parent != active_dir)


def orphan_entries(active_dir: Path) -> list[str]:
    """T1c — 브랜치별 task 파일이 같은 브랜치의 daily index 어디에도 안 보이면 보고.

    index 형식은 시기마다 달랐다(`- **ID** …` 만 있던 옛 형식 / `path:` 링크 줄). 그래서 링크 문법이 아니라
    **ID 출현**으로 잰다 — 사람이 쓴 산문도 index 에 있으면 '연결' 로 치는 쪽이 오보가 적다.
    """
    errors: list[str] = []
    for branch_dir in _branch_dirs(active_dir):
        tasks_dir = branch_dir / "backlog" / "tasks"
        if not tasks_dir.is_dir():
            continue
        rel = branch_dir.relative_to(active_dir).as_posix()
        mentioned: set[str] = set()
        for index in (branch_dir / "backlog").glob("*.md"):
            mentioned.update(TASK_ID_RE.findall(index.read_text(encoding="utf-8")))
        for task in sorted(tasks_dir.glob("*.md")):
            if not TASK_ID_RE.fullmatch(task.stem):
                errors.append(f"[T1c] ID 정규식이 못 읽는 task 파일: {rel}/backlog/tasks/{task.name}")
            elif task.stem not in mentioned:
                errors.append(f"[T1c] Orphan task file: {rel}/backlog/tasks/{task.name} (같은 브랜치 daily index 어디에도 없다)")
    return errors


_INDEX_ENTRY_RE = re.compile(rf"^- \*\*({TASK_ID_PATTERN})\*\*")
_INDEX_PATH_RE = re.compile(r"^\s+- path:\s*(.+?)\s*$")


def _declared_paths(index_text: str) -> dict[str, str]:
    """daily index 의 항목별 `path:` 선언 ``{id: 경로}`` — 마크다운 링크면 target, 아니면 백틱을 벗긴 본문."""
    out: dict[str, str] = {}
    current: str | None = None
    for line in index_text.splitlines():
        head = _INDEX_ENTRY_RE.match(line)
        if head:
            current = head.group(1)
            continue
        tail = _INDEX_PATH_RE.match(line)
        if tail and current:
            raw = tail.group(1)
            link = re.search(r"\]\(([^)]+)\)", raw)
            out[current] = (link.group(1) if link else raw).strip("`").strip()
    return out


def missing_entries(active_dir: Path, archived_dir: Path) -> list[str]:
    """T1d — handoff · daily index 가 참조한 TASK id 의 SSOT 파일이 없으면 보고.

    해소 순서: index 가 `path:` 를 선언했으면 **그 파일**(브랜치 디렉터리 또는 backlog/ 기준 — session 종류는
    `sessions/…` 를 가리킨다) → 그 브랜치 `backlog/tasks/<id>.md` → `archived/**/backlog/tasks/<id>.md`.
    """
    errors: list[str] = []
    archived_ids = {p.stem for p in archived_dir.rglob("backlog/tasks/*.md")} if archived_dir.is_dir() else set()
    for branch_dir in _branch_dirs(active_dir):
        rel = branch_dir.relative_to(active_dir).as_posix()
        backlog_dir = branch_dir / "backlog"
        own_ids = {p.stem for p in (backlog_dir / "tasks").glob("*.md")}
        indexes = sorted(backlog_dir.glob("*.md"))
        declared: dict[str, str] = {}
        for index in indexes:
            declared.update(_declared_paths(index.read_text(encoding="utf-8")))
        for src in [branch_dir / "session_handoff.md", *indexes]:
            if not src.is_file():
                continue
            src_rel = src.relative_to(branch_dir).as_posix()
            for task_id in sorted(set(TASK_ID_RE.findall(src.read_text(encoding="utf-8")))):
                if task_id in own_ids or task_id in archived_ids:
                    continue
                path = declared.get(task_id)
                if path and any((base / path).is_file() for base in (branch_dir, backlog_dir)):
                    continue
                where = f"선언한 path `{path}` 도" if path else f"{rel}/backlog/tasks/ 에도"
                errors.append(f"[T1d] Missing task file: {task_id} — {rel}/{src_rel} 가 참조하는데 {where} archived/ 에도 없다")
    return errors


def check_orphan() -> list[str]:
    """T1c: task files with no mention in the same branch's daily indexes."""
    return orphan_entries(ACTIVE_DIR)


_LOOSE_TASK_RE = re.compile(r"\bTASK-[A-Za-z0-9._-]+")


def unclassified_refs(active_dir: Path) -> list[str]:
    """`TASK-…` 꼴이지만 ``TASK_ID_PATTERN`` 에 안 맞아 T1d 가 **재지 않는** 참조 (옛 `TASK-013` · `TASK-V051-001` · `TASK-XXX`).

    통과로 세지 않고 숫자로 보고만 한다 — 조용한 미분류 금지.
    """
    found: set[str] = set()
    for branch_dir in _branch_dirs(active_dir):
        for src in [branch_dir / "session_handoff.md", *sorted((branch_dir / "backlog").glob("*.md"))]:
            if src.is_file():
                text = src.read_text(encoding="utf-8")
                found.update(tok for tok in _LOOSE_TASK_RE.findall(text) if not TASK_ID_RE.fullmatch(tok))
    return sorted(found)


def check_missing() -> list[str]:
    """T1d: TASK ids referenced by handoff / daily index with no file (branch or archived)."""
    skipped = unclassified_refs(ACTIVE_DIR)
    if skipped:
        print(f"  ~ [T1d] ID 정규식에 안 맞아 재지 않은 참조 {len(skipped)}건 (통과 아님): {skipped[:6]}{' …' if len(skipped) > 6 else ''}")
    return missing_entries(ACTIVE_DIR, ARCHIVED_BRANCHES)


def check_link_selftest() -> list[str]:
    """T1c · T1d 판정이 살아 있는지 — 임시 메모리에 되주입."""
    errors: list[str] = []
    with tempfile.TemporaryDirectory() as td:
        active = Path(td) / "active"
        archived = Path(td) / "archived"
        branch = active / "claude" / "x"
        (branch / "backlog" / "tasks").mkdir(parents=True)
        linked, orphan, legacy = "TASK-2026-10-19-claude-x-001", "TASK-2026-10-19-claude-x-002", "TASK-2026-07-20-001"
        joined, dangling = "TASK-2026-10-02-feat-auto-1234abcd-003", "TASK-2026-10-19-claude-x-009"
        for tid in (linked, orphan, legacy):
            (branch / "backlog" / "tasks" / f"{tid}.md").write_text(f"# {tid} — t\n", encoding="utf-8")
        (branch / "backlog" / "tasks" / "notes.md").write_text("x", encoding="utf-8")  # ID 가 아닌 파일
        sess_ok, sess_gone = "TASK-2026-10-19-claude-x-004", "TASK-2026-10-19-claude-x-005"
        (branch / "sessions").mkdir()
        (branch / "sessions" / "audit.md").write_text("s", encoding="utf-8")
        (branch / "backlog" / "2026-10-19.md").write_text(
            f"- **{linked}** [generic] t\n  - path: [`./tasks/{linked}.md`](./tasks/{linked}.md)\n- **{legacy}** [release] 옛 형식\n"
            f"- **{sess_ok}** [session] 세션 기록\n  - path: `sessions/audit.md`\n"
            f"- **{sess_gone}** [session] 사라진 기록\n  - path: `sessions/gone.md`\n",
            encoding="utf-8")
        (branch / "session_handoff.md").write_text(f"- {linked} t\n- (합류) {joined}\n- {dangling} 없는 task\n", encoding="utf-8")
        (archived / "feat" / "auto-1234abcd" / "backlog" / "tasks").mkdir(parents=True)
        (archived / "feat" / "auto-1234abcd" / "backlog" / "tasks" / f"{joined}.md").write_text("# j\n", encoding="utf-8")
        got_orphan = orphan_entries(active)
        want_orphan = ["[T1c] ID 정규식이 못 읽는 task 파일: claude/x/backlog/tasks/notes.md",
                       f"[T1c] Orphan task file: claude/x/backlog/tasks/{orphan}.md (같은 브랜치 daily index 어디에도 없다)"]
        if set(got_orphan) != set(want_orphan):
            errors.append(f"[T1c-selftest] 기대 {sorted(want_orphan)} ≠ 실제 {sorted(got_orphan)}")
        got_missing = missing_entries(active, archived)
        want_missing = {f"[T1d] Missing task file: {dangling} — claude/x/session_handoff.md 가 참조하는데 "
                        "claude/x/backlog/tasks/ 에도 archived/ 에도 없다",
                        f"[T1d] Missing task file: {sess_gone} — claude/x/backlog/2026-10-19.md 가 참조하는데 "
                        "선언한 path `sessions/gone.md` 도 archived/ 에도 없다"}
        if set(got_missing) != want_missing:
            errors.append(f"[T1d-selftest] 기대 {sorted(want_missing)} ≠ 실제 {sorted(got_missing)}")
    return errors


def main() -> int:
    results: list[str] = []
    failures = 0

    checks = [
        ("stale", check_stale),
        ("stale-selftest", check_stale_selftest),
        ("orphan", check_orphan),
        ("missing", check_missing),
        ("link-selftest", check_link_selftest),
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
