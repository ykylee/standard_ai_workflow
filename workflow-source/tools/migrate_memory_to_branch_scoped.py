#!/usr/bin/env python3
"""v1.0.0: active/ 평면 layout → branch-scoped layout 마이그레이션.

    ai-workflow/memory/active/          ai-workflow/memory/active/
    ├── state.json          ──►        ├── <branch>/
    ├── backlog/                       │   ├── state.json
    ├── sessions/                      │   ├── backlog/
    ├── session_analysis_*.md          │   ├── sessions/
    │                                  │   └── session_analysis_*.md
    ├── PROJECT_PROFILE.md   (유지)     ├── PROJECT_PROFILE.md
    ├── PURPOSE.md           (유지)     ├── PURPOSE.md
    └── memory_index/        (유지)     └── memory_index/

**왜**: 다중 브랜치 동시 작업 시 backlog index / task 번호 / state.json 이 서로를
덮어쓰지 않도록 *물리적으로* 분리한다. 브랜치 작업이 끝나면
`archive_branch_memory.py` 가 `memory/archived/<branch>/` 로 옮겨 이력으로 남긴다.

**공유로 남기는 것** (브랜치와 무관한 프로젝트 정체성 / 통합 검색):
  PROJECT_PROFILE.md, PURPOSE.md, README.md, *_assessment.md,
  state.json.template, memory_index/

Usage:
    python3 tools/migrate_memory_to_branch_scoped.py --dry-run
    python3 tools/migrate_memory_to_branch_scoped.py --apply [--branch main]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from workflow_kit.common.paths import (  # noqa: E402
    get_current_branch,
    memory_active_dir,
)

# 브랜치별로 옮길 항목 (작업 상태)
MOVE_DIRS = ("backlog", "sessions")
MOVE_FILES = ("state.json",)
MOVE_GLOBS = ("session_analysis_*.md",)

# active/ 에 그대로 두는 항목 (공유)
KEEP = {
    "PROJECT_PROFILE.md", "PURPOSE.md", "README.md", "state.json.template",
    "project_status_assessment.md", "repository_assessment.md", "memory_index",
}


def plan_moves(active_dir: Path, branch: str) -> list[tuple[Path, Path]]:
    """(src, dst) 이동 계획. 이미 branch-scoped 인 항목은 건너뛴다."""
    target = active_dir / branch
    moves: list[tuple[Path, Path]] = []
    for name in MOVE_DIRS + MOVE_FILES:
        src = active_dir / name
        if src.exists() and src.resolve() != (target / name).resolve():
            moves.append((src, target / name))
    for pattern in MOVE_GLOBS:
        for src in sorted(active_dir.glob(pattern)):
            if src.is_file():
                moves.append((src, target / src.name))
    return moves


def _git_mv(src: Path, dst: Path, *, repo_root: Path) -> tuple[bool, str]:
    """git mv 로 이동 (히스토리 보존). 실패 시 (False, stderr)."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(
        ["git", "mv", str(src.relative_to(repo_root)), str(dst.relative_to(repo_root))],
        cwd=str(repo_root), capture_output=True, text=True,
    )
    return proc.returncode == 0, proc.stderr.strip()


def rewrite_state_paths(state_path: Path, branch: str) -> bool:
    """state.json 의 source_of_truth 경로를 branch-scoped 로 갱신."""
    if not state_path.exists():
        return False
    data = json.loads(state_path.read_text(encoding="utf-8"))
    sot = data.get("source_of_truth")
    if not isinstance(sot, dict):
        return False
    changed = False
    for key, value in list(sot.items()):
        if not isinstance(value, str) or "memory/active/" not in value:
            continue
        head, _, tail = value.partition("memory/active/")
        if tail.startswith(f"{branch}/") or not tail:
            continue
        sot[key] = f"{head}memory/active/{branch}/{tail}"
        changed = True
    if changed:
        state_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return changed


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--active-dir", default=memory_active_dir(str(REPO_ROOT)))
    p.add_argument("--branch", default=None, help="대상 브랜치 slug (default: 현재 브랜치)")
    p.add_argument("--apply", action="store_true", help="실제 이동 (default: dry-run)")
    p.add_argument("--dry-run", action="store_true", dest="dry_run")
    p.add_argument("--json", action="store_true")
    args = p.parse_args()

    active_dir = Path(args.active_dir).resolve()
    branch = args.branch or get_current_branch()
    if not active_dir.is_dir():
        print(f"[error] active dir 부재: {active_dir}", file=sys.stderr)
        return 2

    moves = plan_moves(active_dir, branch)
    result: dict = {
        "mode": "apply" if args.apply and not args.dry_run else "dry-run",
        "branch": branch,
        "active_dir": str(active_dir),
        "moves": [{"from": str(s), "to": str(d)} for s, d in moves],
        "kept": sorted(n for n in KEEP if (active_dir / n).exists()),
        "moved": 0, "errors": [],
    }

    if result["mode"] == "apply":
        for src, dst in moves:
            ok, err = _git_mv(src, dst, repo_root=REPO_ROOT)
            if not ok:  # git 추적 밖이면 일반 이동으로 폴백
                try:
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    src.rename(dst)
                    ok = True
                except OSError as exc:
                    result["errors"].append(f"{src.name}: {err or exc}")
            if ok:
                result["moved"] += 1
        result["state_paths_rewritten"] = rewrite_state_paths(
            active_dir / branch / "state.json", branch)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"=== branch-scoped memory 마이그레이션 ({result['mode']}) ===")
        print(f"  branch: {branch}")
        for m in result["moves"]:
            print(f"  MOVE  {Path(m['from']).name}  →  {branch}/{Path(m['to']).name}")
        print(f"  KEEP  {', '.join(result['kept'])}")
        if result["mode"] == "apply":
            print(f"  moved={result['moved']}  state_paths_rewritten={result.get('state_paths_rewritten')}")
        for e in result["errors"]:
            print(f"  ERROR {e}", file=sys.stderr)
    return 1 if result["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
