#!/usr/bin/env python3
"""v1.0.0: 종료된 브랜치의 메모리를 `memory/archived/<branch>/` 로 자동 아카이브.

**왜 필요한가**: 브랜치별 메모리(`active/<branch>/`)는 동시 작업 충돌을 없애지만,
브랜치가 사라진 뒤에도 디렉터리가 남으면 *고아* 가 된다. 실제로 이 저장소에는
`gemini/phase6~10`, `codex/phase6` 가 1.5개월간 고아로 방치돼 있었다.

**탐지 방식**: hook 은 브랜치 삭제를 잡지 못하므로 **역방향 점검** 을 쓴다 —
`active/<slug>/` 가 있는데 git 에 그 브랜치(로컬/원격)가 없으면 "종료된 브랜치"로 본다.
이러면 고아가 구조적으로 생길 수 없다.

**protected main 호환**: 본 도구는 *파일 이동만* 수행하고 commit/push 는 하지 않는다.
작업 브랜치에서 실행하면 그 변경이 해당 브랜치의 PR 에 실려 merge 된다 (piggyback).
main 에 직접 쓰지 않으므로 protected branch 정책과 충돌하지 않는다.

Usage:
    python3 tools/archive_branch_memory.py --dry-run
    python3 tools/archive_branch_memory.py --apply
    python3 tools/archive_branch_memory.py --apply --branch feature/old   # 특정 브랜치 강제
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from workflow_kit.common.paths import get_current_branch  # noqa: E402

# active/ 직속에서 브랜치가 아닌 공유 항목 (아카이브 대상에서 제외)
SHARED_NAMES = {
    "PROJECT_PROFILE.md", "PURPOSE.md", "README.md", "state.json",
    "state.json.template", "project_status_assessment.md",
    "repository_assessment.md", "memory_index", "backlog", "sessions",
}


def _git(args: list[str], *, repo_root: Path) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=str(repo_root),
                          capture_output=True, text=True)


def branch_exists(name: str, *, repo_root: Path) -> bool:
    """로컬 또는 원격에 해당 브랜치가 존재하는지."""
    for ref in (f"refs/heads/{name}", f"refs/remotes/origin/{name}"):
        if _git(["rev-parse", "--verify", "--quiet", ref], repo_root=repo_root).returncode == 0:
            return True
    return False


def find_branch_memories(active_dir: Path) -> list[tuple[str, Path]]:
    """active/ 하위에서 '브랜치 메모리 세트'로 보이는 디렉터리를 찾는다.

    판별: `backlog/` 를 갖거나 `state.json` 을 가진 디렉터리. 브랜치명에 `/` 가 있으면
    중첩 디렉터리가 되므로 rglob 으로 훑되, 다른 후보의 하위인 것은 제외한다.
    """
    found: list[tuple[str, Path]] = []
    for path in sorted(active_dir.rglob("*")):
        if not path.is_dir():
            continue
        rel = path.relative_to(active_dir)
        if rel.parts[0] in SHARED_NAMES:
            continue
        if not ((path / "backlog").is_dir() or (path / "state.json").is_file()):
            continue
        found.append((rel.as_posix(), path))
    # 다른 후보의 하위 디렉터리는 제외 (가장 바깥만 브랜치 루트로 인정)
    roots: list[tuple[str, Path]] = []
    for name, path in found:
        if any(name != other and name.startswith(f"{other}/") for other, _ in found):
            continue
        roots.append((name, path))
    return roots


def _move(src: Path, dst: Path, *, repo_root: Path) -> str | None:
    """git mv 로 이동 (히스토리 보존). 실패 시 일반 이동 폴백. 오류 메시지 반환."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    stderr = ""
    # memory root 가 repo 밖일 수 있다 (본 kit 은 외부 프로젝트에 배포된다).
    # 그 경우 git mv 는 적용 불가이므로 일반 이동으로 처리한다.
    try:
        rel_src = src.relative_to(repo_root)
        rel_dst = dst.relative_to(repo_root)
    except ValueError:
        rel_src = rel_dst = None
    if rel_src is not None and rel_dst is not None:
        proc = _git(["mv", str(rel_src), str(rel_dst)], repo_root=repo_root)
        if proc.returncode == 0:
            return None
        stderr = proc.stderr.strip()
    try:
        src.rename(dst)
        return None
    except OSError as exc:
        return f"{src.name}: {stderr or exc}"


def write_metadata(dst: Path, branch: str, *, repo_root: Path) -> None:
    """`.archived.json` — 과거 이력 조회를 위한 메타데이터."""
    tasks_dir = dst / "backlog" / "tasks"
    task_ids = sorted(p.stem for p in tasks_dir.glob("TASK-*.md")) if tasks_dir.is_dir() else []
    merge_commit = _git(
        ["log", "-1", "--format=%H", "--all", f"--grep=Merge.*{branch}"], repo_root=repo_root
    ).stdout.strip() or None
    (dst / ".archived.json").write_text(
        json.dumps(
            {
                "branch": branch,
                "archived_at": date.today().isoformat(),
                "merge_commit": merge_commit,
                "task_ids": task_ids,
                "task_count": len(task_ids),
                "note": "종료된 브랜치의 메모리. 과거 이력 조회 대상 (읽기 전용).",
            },
            ensure_ascii=False, indent=2,
        ) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--memory-root", default=str(REPO_ROOT / "ai-workflow" / "memory"))
    p.add_argument("--branch", action="append", dest="branches", default=[],
                   help="강제로 아카이브할 브랜치 (git 존재 여부 무시)")
    p.add_argument("--keep", action="append", default=["main"],
                   help="아카이브에서 제외할 브랜치 (default: main)")
    p.add_argument("--apply", action="store_true", help="실제 이동 (default: dry-run)")
    p.add_argument("--dry-run", action="store_true", dest="dry_run", help="계획만 출력 (default)")
    p.add_argument("--json", action="store_true")
    args = p.parse_args()
    if args.dry_run:
        args.apply = False

    memory_root = Path(args.memory_root).resolve()
    active_dir = memory_root / "active"
    archived_dir = memory_root / "archived"
    if not active_dir.is_dir():
        print(f"[error] active dir 부재: {active_dir}", file=sys.stderr)
        return 2

    current = get_current_branch()
    keep = set(args.keep) | {current}
    forced = set(args.branches)

    candidates = []
    for name, path in find_branch_memories(active_dir):
        if name in keep and name not in forced:
            reason = "keep (현재 브랜치이거나 보존 대상)"
            candidates.append({"branch": name, "action": "skip", "reason": reason})
            continue
        if name not in forced and branch_exists(name, repo_root=REPO_ROOT):
            candidates.append({"branch": name, "action": "skip", "reason": "git 에 브랜치가 살아 있음"})
            continue
        candidates.append({
            "branch": name, "action": "archive",
            "reason": "강제 지정" if name in forced else "git 에 브랜치 없음 (종료됨)",
            "from": str(path), "to": str(archived_dir / name),
        })

    result = {
        "mode": "apply" if args.apply else "dry-run",
        "current_branch": current,
        "candidates": candidates,
        "archived": 0,
        "errors": [],
    }

    if args.apply:
        for c in candidates:
            if c["action"] != "archive":
                continue
            src, dst = Path(c["from"]), Path(c["to"])
            if dst.exists():
                result["errors"].append(f"{c['branch']}: 대상이 이미 존재 ({dst})")
                continue
            err = _move(src, dst, repo_root=REPO_ROOT)
            if err:
                result["errors"].append(err)
                continue
            write_metadata(dst, c["branch"], repo_root=REPO_ROOT)
            result["archived"] += 1

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"=== branch memory 아카이브 ({result['mode']}) — 현재 브랜치: {current} ===")
        for c in candidates:
            mark = "ARCHIVE" if c["action"] == "archive" else "skip   "
            print(f"  {mark}  {c['branch']:<28} {c['reason']}")
        if args.apply:
            print(f"  archived={result['archived']}")
        for e in result["errors"]:
            print(f"  ERROR {e}", file=sys.stderr)
        if any(c["action"] == "archive" for c in candidates) and not args.apply:
            print("\n  → 실제 이동: --apply (commit/push 는 하지 않음; 작업 브랜치 PR 에 실어 보내세요)")
    return 1 if result["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
