#!/usr/bin/env python3
"""pre-push hook installer — §0.8 #4 (TASK-2026-08-08-main-019)

표준 §5D.4 의 *3-layer defense* 중 2nd layer (client-side). `git push --force` 를
`.git/hooks/pre-push` 에서 차단. **3개 sub-command**:

- `install`   — `.git/hooks/pre-push` 를 `tools/hooks/pre-push-no-force.sh` 로 교체.
               기존 hook 있으면 `pre-push.bak.<UTC-ISO>` 으로 backup. idempotent.
- `uninstall` — `.git/hooks/pre-push` 제거 + 가장 최근 backup 에서 복원. 복원할
               backup 없으면 그냥 빈 hook (또는 사용자 default).
- `status`    — hook 설치 여부 + 내용 hash + backup list.

`--dry-run` (default) 시 *시뮬레이션* — 실제 write 없음. `--apply` 시 실제 변경.

## 사용법

```bash
# 설치 (preview)
python3 workflow-source/tools/install_pre_push_hook.py install

# 실제 설치
python3 workflow-source/tools/install_pre_push_hook.py install --apply

# 상태 확인
python3 workflow-source/tools/install_pre_push_hook.py status

# 제거 (가장 최근 backup 에서 복원)
python3 workflow-source/tools/install_pre_push_hook.py uninstall --apply
```

Cross-ref: `core/multi_workspace_orchestration.md` §0.8 #4 / §5D.5 (TASK-019).
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
HOOK_SOURCE = REPO_ROOT / "workflow-source" / "tools" / "hooks" / "pre-push-no-force.sh"


def _git_root(cwd: Path) -> Path | None:
    """``git rev-parse --show-toplevel``. 실패 시 None. hook target = `<git_root>/.git/hooks/pre-push`."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0 or not result.stdout.strip():
        return None
    return Path(result.stdout.strip())


def _now_utc_compact() -> str:
    """UTC ISO timestamp, 'Z' 제거 + ':' 제거 (filename safe). 예: 20260808T225500Z."""
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _utc_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _hook_path(git_root: Path) -> Path:
    return git_root / ".git" / "hooks" / "pre-push"


def _backup_list(git_root: Path) -> list[Path]:
    """``.git/hooks/pre-push.bak.*`` 목록. 최신 우선 정렬."""
    hooks_dir = git_root / ".git" / "hooks"
    if not hooks_dir.is_dir():
        return []
    return sorted(hooks_dir.glob("pre-push.bak.*"), reverse=True)


def cmd_install(args: argparse.Namespace) -> int:
    git_root = _git_root(REPO_ROOT)
    if git_root is None:
        print("ERROR: not a git repository (git rev-parse --show-toplevel failed)", file=sys.stderr)
        return 2
    target = _hook_path(git_root)
    if not HOOK_SOURCE.is_file():
        print(f"ERROR: hook source not found: {HOOK_SOURCE}", file=sys.stderr)
        return 2

    backups_before = _backup_list(git_root)
    backup_new: Path | None = None
    if target.is_file() and target.read_bytes() != HOOK_SOURCE.read_bytes():
        backup_new = target.parent / f"pre-push.bak.{_now_utc_compact()}"
        action_msg = f"backup existing → {backup_new.name}, install new"
    elif target.is_file():
        action_msg = "identical content, no-op (idempotent)"
    else:
        action_msg = "no existing hook, install new"

    print(f"  git_root: {git_root}")
    print(f"  target:   {target}")
    print(f"  source:   {HOOK_SOURCE}")
    print(f"  action:   {action_msg}")
    if backups_before:
        print(f"  existing backups: {len(backups_before)}")

    if not args.apply:
        print("  (dry-run — no changes applied; use --apply to install)")
        return 0

    if target.is_file() and target.read_bytes() != HOOK_SOURCE.read_bytes():
        target.rename(backup_new)
    shutil.copy2(HOOK_SOURCE, target)
    target.chmod(0o755)
    print(f"  ✓ installed: {target} (mode 0o755)")
    return 0


def cmd_uninstall(args: argparse.Namespace) -> int:
    git_root = _git_root(REPO_ROOT)
    if git_root is None:
        print("ERROR: not a git repository", file=sys.stderr)
        return 2
    target = _hook_path(git_root)
    if not target.is_file():
        print(f"  = no hook installed at {target} (no-op)")
        return 0

    backups = _backup_list(git_root)
    latest = backups[0] if backups else None

    if not args.apply:
        print(f"  target: {target}")
        print(f"  latest backup: {latest or '(none)'}")
        print(f"  action: would remove {target}" + (f" + restore {latest}" if latest else ""))
        print("  (dry-run — no changes applied)")
        return 0

    target.unlink()
    print(f"  ✓ removed: {target}")
    if latest is not None:
        shutil.copy2(latest, target)
        target.chmod(0o755)
        print(f"  ✓ restored from backup: {latest}")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    git_root = _git_root(REPO_ROOT)
    if git_root is None:
        print("ERROR: not a git repository", file=sys.stderr)
        return 2
    target = _hook_path(git_root)
    backups = _backup_list(git_root)
    payload: dict = {
        "git_root": str(git_root),
        "hook_path": str(target),
        "hook_installed": target.is_file(),
        "hook_matches_source": (
            target.is_file() and HOOK_SOURCE.is_file()
            and target.read_bytes() == HOOK_SOURCE.read_bytes()
        ),
        "source_path": str(HOOK_SOURCE),
        "backups": [str(p) for p in backups],
        "checked_at": _utc_iso(),
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    print(f"  git_root:     {git_root}")
    print(f"  hook_path:    {target}")
    print(f"  installed:    {target.is_file()}")
    if target.is_file() and HOOK_SOURCE.is_file():
        match = target.read_bytes() == HOOK_SOURCE.read_bytes()
        print(f"  matches src:  {match}")
    print(f"  source:       {HOOK_SOURCE}")
    print(f"  backups:      {len(backups)}")
    for b in backups:
        print(f"    - {b.name}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="pre-push hook installer (--force 이중화, §0.8 #4)")
    sub = p.add_subparsers(dest="command", required=True)

    sp_install = sub.add_parser("install", help="install pre-push hook")
    sp_install.add_argument("--apply", action="store_true", help="실제 write (default: dry-run)")
    sp_install.set_defaults(func=cmd_install)

    sp_uninstall = sub.add_parser("uninstall", help="uninstall + restore from latest backup")
    sp_uninstall.add_argument("--apply", action="store_true", help="실제 write (default: dry-run)")
    sp_uninstall.set_defaults(func=cmd_uninstall)

    sp_status = sub.add_parser("status", help="hook 설치 상태")
    sp_status.add_argument("--json", action="store_true")
    sp_status.set_defaults(func=cmd_status)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
