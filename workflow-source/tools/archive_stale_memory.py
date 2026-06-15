#!/usr/bin/env python3
"""
v0.7.28: TASK-V0726-004 — detached HEAD memory dir cleanup (stale archive)

F-7 (v0.7.26) 의 fix 로 detached HEAD 시 memory dir name = 7-char short SHA.
*시간이 지나면* 옛 commit 의 short SHA dir 가 누적 (e.g. 30+ days).
본 tool 은 *age-based* auto-archive: N day 이전의 short SHA dir → archive/ 로 move.

Usage:
    # 1. dry-run: 어떤 dir 이 archive 후보인지 list
    python3 tools/archive_stale_memory.py --older-than=30 --dry-run

    # 2. apply: 실제 archive (move to archive/<date>/<sha>/)
    python3 tools/archive_stale_memory.py --older-than=30 --apply

    # 3. list: 모든 short SHA dir (age 무관)
    python3 tools/archive_stale_memory.py --list --dry-run

    # 4. cleanup: apply 와 동일, --apply alias
    python3 tools/archive_stale_memory.py --older-than=30 --cleanup

    # 5. REPO_ROOT override
    python3 tools/archive_stale_memory.py --repo-root=/path/to/repo --older-than=30 --dry-run

1차 출처:
- v0.7.17 release note (in-repo redirect, memory dir 의 SSOT)
- v0.7.26 release note (F-7 branch detection, detached HEAD → short SHA)
- v0.7.18 release note (destructive subcommand 정공법, --dry-run 필수)
- v0.7.25 release note (F-6 closure, SHA256 hash 기반 idempotency)
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import sys
from pathlib import Path

# === Path setup ===
_LEGACY_REPO_ROOT = Path.home() / "repos" / "standard_ai_workflow_minimax"
_DEPRECATION_WARNED = False


def get_repo_root(cli_value: str | os.PathLike[str] | None = None, *, _suppress_warning: bool = False) -> Path:
    """REPO_ROOT 결정 (priority: CLI flag > env var > git rev-parse > legacy fallback).
    v0.7.12 의 4-priority 정공법.
    """
    global _DEPRECATION_WARNED

    if cli_value is not None:
        p = Path(cli_value).expanduser().resolve()
        return p

    env_val = os.environ.get("STANDARD_AI_WF_REPO")
    if env_val:
        p = Path(env_val).expanduser().resolve()
        return p

    try:
        import subprocess as sp
        proc = sp.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, timeout=5,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            return Path(proc.stdout.strip()).resolve()
    except (Exception,):
        pass

    if not _DEPRECATION_WARNED and not _suppress_warning:
        _DEPRECATION_WARNED = True
        print(
            f"[DEPRECATION] archive_stale_memory.py: REPO_ROOT auto-detect 실패 — legacy fallback 사용 ({_LEGACY_REPO_ROOT}).",
            file=sys.stderr,
        )
    return _LEGACY_REPO_ROOT


# === Memory dir path ===
def get_memory_dir(repo_root: Path) -> Path:
    """`ai-workflow/memory/` 의 path. v0.7.17 의 in-repo redirect 의 SSOT."""
    return repo_root / "ai-workflow" / "memory"


# === Detection helpers ===
SHORT_SHA_RE = re.compile(r"^[a-f0-9]{7}$")


def is_short_sha_dir(path: Path) -> bool:
    """dir name 이 7-char hex (short SHA) 인지 확인. F-7 (v0.7.26) 의 detached HEAD 의
    dir name pattern. named branch (e.g. 'main', 'feat/x') 는 *불일치*."""
    if not path.is_dir():
        return False
    return bool(SHORT_SHA_RE.match(path.name))


def get_dir_age_days(path: Path) -> int:
    """dir 의 mtime 기준 age (day)."""
    mtime = path.stat().st_mtime
    mtime_dt = dt.datetime.fromtimestamp(mtime, tz=dt.timezone.utc)
    now_dt = dt.datetime.now(tz=dt.timezone.utc)
    return (now_dt - mtime_dt).days


def build_archive_path(memory_dir: Path, sha: str, archive_date: str) -> Path:
    """archive target path: `archive/<date>/<sha>/`."""
    return memory_dir / "archive" / archive_date / sha


def check_already_archived(memory_dir: Path, sha: str) -> bool:
    """sha 가 *이미* archive/ 하위에 있는지 확인. idempotency."""
    archive_base = memory_dir / "archive"
    if not archive_base.exists():
        return False
    for archive_dir in archive_base.iterdir():
        if not archive_dir.is_dir():
            continue
        candidate = archive_dir / sha
        if candidate.exists():
            return True
    return False


def sha256_of_dir(path: Path) -> str:
    """dir 의 SHA256 (file 들의 SHA256 concat). idempotency 의 1차 출처 (v0.7.25)."""
    h = hashlib.sha256()
    for f in sorted(path.rglob("*")):
        if f.is_file():
            h.update(f.read_bytes())
    return h.hexdigest()


# === Subcommand logic ===
def cmd_list(args: argparse.Namespace) -> dict:
    """모든 short SHA dir list (age 무관, dry-run 만)."""
    repo_root = get_repo_root(args.repo_root)
    memory_dir = get_memory_dir(repo_root)
    if not memory_dir.exists():
        return {"error": f"memory dir not found: {memory_dir}", "items": []}

    items = []
    for entry in memory_dir.iterdir():
        if not is_short_sha_dir(entry):
            continue
        if check_already_archived(memory_dir, entry.name):
            continue
        age = get_dir_age_days(entry)
        items.append({
            "sha": entry.name,
            "path": str(entry),
            "age_days": age,
            "size_bytes": sum(f.stat().st_size for f in entry.rglob("*") if f.is_file()),
        })

    items.sort(key=lambda x: -x["age_days"])
    return {"mode": "list", "memory_dir": str(memory_dir), "items": items, "count": len(items)}


def cmd_archive(args: argparse.Namespace) -> dict:
    """age-based archive. dry-run or apply.

    Args:
        args: argparse.Namespace with --older-than, --dry-run/--apply, --repo-root.
    """
    repo_root = get_repo_root(args.repo_root)
    memory_dir = get_memory_dir(repo_root)
    if not memory_dir.exists():
        return {"error": f"memory dir not found: {memory_dir}", "items": []}

    older_than = args.older_than
    if older_than < 0:
        return {"error": f"--older-than must be >= 0 (got {older_than})", "items": []}

    today = dt.date.today().strftime("%Y-%m-%d")
    candidates = []
    archived = []
    skipped = []

    for entry in memory_dir.iterdir():
        if not is_short_sha_dir(entry):
            continue
        if check_already_archived(memory_dir, entry.name):
            skipped.append({"sha": entry.name, "reason": "already-archived", "path": str(entry)})
            continue
        age = get_dir_age_days(entry)
        if age < older_than:
            skipped.append({"sha": entry.name, "reason": "too-recent", "age_days": age, "path": str(entry)})
            continue
        candidates.append({
            "sha": entry.name,
            "path": str(entry),
            "age_days": age,
            "archive_target": str(build_archive_path(memory_dir, entry.name, today)),
        })

    if args.dry_run:
        return {
            "mode": "dry-run",
            "memory_dir": str(memory_dir),
            "older_than": older_than,
            "candidates": candidates,
            "skipped": skipped,
            "candidate_count": len(candidates),
        }

    # apply mode
    for cand in candidates:
        src = Path(cand["path"])
        dst = Path(cand["archive_target"])
        dst.parent.mkdir(parents=True, exist_ok=True)
        if dst.exists():
            skipped.append({"sha": cand["sha"], "reason": "archive-target-exists", "path": str(dst)})
            continue
        try:
            shutil.move(str(src), str(dst))
            archived.append({
                "sha": cand["sha"],
                "src": str(src),
                "dst": str(dst),
                "age_days": cand["age_days"],
                "sha256": sha256_of_dir(dst),
            })
        except (OSError, shutil.Error) as e:
            skipped.append({"sha": cand["sha"], "reason": f"move-fail: {e}", "path": str(src)})

    return {
        "mode": "apply",
        "memory_dir": str(memory_dir),
        "older_than": older_than,
        "archived": archived,
        "skipped": skipped,
        "archived_count": len(archived),
        "skipped_count": len(skipped),
    }


# === argparse ===
def build_argparser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="archive_stale_memory",
        description="TASK-V0726-004 (v0.7.28): detached HEAD memory dir age-based auto-archive (short SHA dir)",
    )
    p.add_argument(
        "--older-than", type=int, default=30,
        help="N day 이전의 short SHA dir 를 archive (default: 30)",
    )
    p.add_argument(
        "--list", action="store_true",
        help="모든 short SHA dir list (--older-than 무시, dry-run 만).",
    )
    p.add_argument(
        "--dry-run", action="store_true",
        help="dry-run mode: print what will be done, no file move.",
    )
    p.add_argument(
        "--apply", action="store_true",
        help="apply mode: actually move dirs to archive/.",
    )
    p.add_argument(
        "--cleanup", action="store_true",
        help="--apply alias (semantic clarity).",
    )
    p.add_argument(
        "--repo-root", type=str, default=None,
        help="REPO_ROOT override (priority 1, v0.7.12 정공법).",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_argparser()
    args = parser.parse_args(argv)

    # mode 결정
    if args.list:
        if args.apply or args.cleanup:
            parser.error("--list 와 --apply/--cleanup 은 mutually exclusive (--list 는 dry-run 만)")
        # force dry-run
        args.dry_run = True
        result = cmd_list(args)
    else:
        if not args.dry_run and not args.apply and not args.cleanup:
            parser.error("at least one of --dry-run, --apply, or --cleanup is required")
        if args.cleanup:
            args.apply = True
        result = cmd_archive(args)

    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
