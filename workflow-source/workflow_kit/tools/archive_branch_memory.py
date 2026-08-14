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
    wk archive-branch-memory --dry-run
    wk archive-branch-memory --apply
    wk archive-branch-memory --apply --branch feature/old   # 특정 브랜치 강제
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from collections.abc import Callable
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from workflow_kit.common.paths import (  # noqa: E402
    get_current_branch,
    memory_dir_for_workspace,
)

# active/ 직속에서 브랜치가 아닌 공유 항목 (아카이브 대상에서 제외)
SHARED_NAMES = {
    "PROJECT_PROFILE.md", "PURPOSE.md", "README.md", "state.json",
    "state.json.template", "project_status_assessment.md",
    "repository_assessment.md", "memory_index", "backlog", "sessions",
}

#: 이관된 task 임을 밝히는 frontmatter key. 값은 이월 대상 task ID.
CARRIED_OVER_KEY = "carried_over_to"

# 참조 재작성 시 훑지 않을 디렉터리 (비용만 크고 링크가 없다).
SKIP_SCAN_DIRS = {
    ".git", ".venv", ".venv-sdk-matrix", "node_modules", "dist", "build",
    "__pycache__", ".mypy_cache", ".pytest_cache",
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


def open_tasks(branch_dir: Path) -> list[tuple[str, str]]:
    """아직 끝나지 않은 task — `(task_id, status)`.

    `done` 이 아닌 것 전부다. status 를 아예 안 적은 task 는 **판정 근거가 없다는
    뜻**이므로(§2.39) 미완료로 본다 — 모르는 것을 끝난 것으로 취급하면 그게 곧 소실이다.

    예외는 `carried_over_to` 하나다. 브랜치는 끝났는데 일이 안 끝난 경우가 있고,
    그때 `done` 으로 적으면 **거짓**이다. 진행 상태(`status`)와 이관 사실을 한 칸에
    섞지 않는다는 §2.39 의 원칙 그대로, 이관은 **별도 축**으로 적고 이 판정만
    면제한다 — 어디로 갔는지가 파일에 남으므로 추적이 끊기지 않는다.
    """
    tasks_dir = branch_dir / "backlog" / "tasks"
    if not tasks_dir.is_dir():
        return []
    out: list[tuple[str, str]] = []
    for path in sorted(tasks_dir.glob("TASK-*.md")):
        front = _frontmatter(path.read_text(encoding="utf-8"))
        if front.get(CARRIED_OVER_KEY) or front.get("status") == "done":
            continue
        out.append((path.stem, front.get("status") or "(미기재)"))
    return out


def _frontmatter(text: str) -> dict[str, str]:
    """앞머리 `---` 블록만 key/value 로 읽는다.

    **본문을 섞어 읽으면 안 된다.** 앞선 구현은 파일 앞 20줄을 그냥 훑어서, 본문에
    적힌 `status: …` 줄을 frontmatter 로 오인했다 (실측). 본문에 `status: done` 이
    한 줄만 있으면 **미완료 task 가 완료로 판정되어 그대로 아카이브로 사라진다** —
    이 함수가 막으려던 바로 그 사고다. 줄 수 상한도 없앴다 (긴 frontmatter 에서
    status 를 놓치던 자리).
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    out: dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if ":" not in line or line.startswith((" ", "\t", "#")):
            continue
        key, value = line.split(":", 1)
        out[key.strip()] = value.strip()
    return out


def rewrite_moved_references(
    *, branch: str, memory_root: Path, repo_root: Path,
) -> list[str]:
    """`active/<branch>/…` 를 가리키던 참조를 `archived/<branch>/…` 로 옮긴다.

    **이동만 하고 참조를 안 고치면 이력이 그 자리에서 끊긴다.** 실측(2026-08-13):
    아카이브된 22개 문서 중 12개가 깨진 링크를 갖고 있었고, `state.json` 의
    `source_of_truth` 5개 경로가 전부 사라진 `active/…` 를 가리키고 있었다.

    두 형태를 처리한다:

    - **markdown 링크** — `../../../active/<branch>/…` 같은 상대 경로라 문자열 치환이
      안 통한다. 링크를 **해석해서** 대상이 없고 archived 쪽에 있으면 그 파일 기준
      상대 경로로 다시 쓴다.
    - **JSON 문자열 경로** — `state.json` 의 저장소 상대 경로는 문자열 치환으로 족하다.

    Returns: 고친 파일의 저장소 상대 경로 목록.
    """
    active_branch = memory_root / "active" / branch
    archived_branch = memory_root / "archived" / branch
    changed: list[str] = []

    def _rel(path: Path) -> str:
        try:
            return path.relative_to(repo_root).as_posix()
        except ValueError:
            return str(path)

    # 저장소 + (저장소 밖이면) memory root. 이 kit 은 외부 프로젝트에 배포되며
    # memory root 가 저장소 밖일 수 있다 (`_move` 의 같은 전제). 저장소만 훑으면
    # 그 배치에서는 참조 재작성이 통째로 no-op 이 된다.
    scan_roots = [repo_root]
    if not str(memory_root).startswith(str(repo_root)):
        scan_roots.append(memory_root)

    for path in sorted(q for root in scan_roots for q in root.rglob("*.md")):
        if any(part in SKIP_SCAN_DIRS for part in path.parts):
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if "active/" not in text:
            continue
        new_text = _rewrite_markdown_links(
            text, doc_dir=path.parent, old_root=active_branch, new_root=archived_branch,
        )
        if new_text != text:
            path.write_text(new_text, encoding="utf-8")
            changed.append(_rel(path))

    # 반대 방향 — 이동한 것은 대상이 아니라 **문서 자신**이다. 위 루프의
    # `"active/" not in text` 가드에 안 걸리는 형태이기도 하다: 살아 있는 대상을
    # 가리키는 상대 링크(`../../main/state.json`)에는 그 낱말이 없다.
    for path in sorted(archived_branch.rglob("*.md")):
        text = path.read_text(encoding="utf-8", errors="replace")
        old_doc_dir = active_branch / path.parent.relative_to(archived_branch)
        new_text = _rewrite_relocated_links(
            text, old_doc_dir=old_doc_dir, new_doc_dir=path.parent,
        )
        if new_text != text:
            path.write_text(new_text, encoding="utf-8")
            changed.append(_rel(path))

    # JSON 안의 경로 문자열은 **저장소 상대**(`ai-workflow/memory/active/<b>/…`)로
    # 적히지만, memory root 가 저장소 밖인 배치에서는 절대 경로일 수도 있다.
    # 그래서 저장소 기준 접두사가 아니라 **`active/<branch>/` 라는 경로 조각**을
    # 옮긴다 — 앞에 경계(`/` 또는 문자열 시작)를 요구해 `inactive/…` 같은 이름에
    # 잘못 걸리지 않게 한다.
    seg_old, seg_new = f"active/{branch}/", f"archived/{branch}/"
    pattern = re.compile(r"(?<![\w.-])" + re.escape(seg_old))
    for path in sorted(archived_branch.rglob("*.json")):
        text = path.read_text(encoding="utf-8")
        new_text = pattern.sub(seg_new, text)
        if new_text == text:
            continue
        path.write_text(new_text, encoding="utf-8")
        changed.append(_rel(path))

    # 한 파일이 두 규칙(대상 이동·문서 이동)에 다 걸리면 두 번 잡힌다 — 목록은 한 번만.
    return list(dict.fromkeys(changed))


def _map_relative_links(
    text: str, *, doc_dir: Path, map_target: "Callable[[str], Path | None]",
) -> str:
    """`](경로)` 의 상대 경로를 map_target 으로 사상한다. None 이면 그대로 둔다.

    파싱은 여기 한 곳이다 — 제목(`path "제목"`)·`<>` 감싸기·scheme 제외·앵커 분리를
    규칙마다 다시 구현하면 그중 하나가 조용히 빠진다.
    """
    def repl(m: "re.Match[str]") -> str:
        raw = m.group(1).strip()
        # `](path "제목")` / `](path '제목')` — CommonMark 가 허용하는 형태다.
        # 분리하지 않으면 경로가 `path "제목"` 이 되어 매칭이 빗나가고, 깨진 링크가
        # 조용히 남는다.
        title_match = re.match(r"^(\S+)(\s+[\"'(].*)$", raw)
        link, title = (title_match.group(1), title_match.group(2)) if title_match else (raw, "")
        wrapped = link.startswith("<") and link.endswith(">")
        if wrapped:
            link = link[1:-1]
        if link.startswith(("http://", "https://", "#", "mailto:")):
            return m.group(0)
        path_part, sep, anchor = link.partition("#")
        mapped = map_target(path_part)
        if mapped is None:
            return m.group(0)
        # **앵커를 보존한다.** 떼고 쓰면 링크는 살아나지만 문서의 엉뚱한 곳으로 간다 —
        # 고친 척하고 정보를 잃는 쪽이 더 나쁘다.
        rewritten = os.path.relpath(mapped, doc_dir).replace(os.sep, "/") + sep + anchor
        if wrapped:
            rewritten = f"<{rewritten}>"
        return "](" + rewritten + title + ")"

    return re.sub(r"\]\(([^)]+)\)", repl, text)


def _rewrite_markdown_links(
    text: str, *, doc_dir: Path, old_root: Path, new_root: Path,
) -> str:
    """`](경로)` 중 old_root 아래를 가리키며 **지금은 없는** 링크를 new_root 로 옮긴다.

    대상이 여전히 존재하면 건드리지 않는다 — 살아 있는 링크를 고치면 그게 손상이다.
    """
    # **양쪽 root 를 여기서 resolve 한다.** 호출자가 안 한 경로를 넘기면 macOS 의
    # `/var` ↔ `/private/var` 심링크 하나로 `relative_to` 가 전부 ValueError 가 되어
    # **재작성이 통째로 침묵**한다 (오류도 안 난다). 실측으로 밟았다.
    old_root, new_root = Path(old_root).resolve(), Path(new_root).resolve()
    # `doc_dir` 도 같이 맞춘다. 한쪽만 resolve 하면 상대 경로가 `../../../private/var/…`
    # 처럼 터무니없이 길어진다 (링크는 살지만 읽을 수 없는 문서가 된다).
    doc_dir = Path(doc_dir).resolve()

    def map_target(path_part: str) -> Path | None:
        target = (doc_dir / path_part).resolve()
        if target.exists():
            return None
        try:
            moved = new_root / target.relative_to(old_root)
        except ValueError:
            return None
        return moved if moved.exists() else None

    return _map_relative_links(text, doc_dir=doc_dir, map_target=map_target)


def _rewrite_relocated_links(
    text: str, *, old_doc_dir: Path, new_doc_dir: Path,
) -> str:
    """문서 **자신이 이동해서** 풀린 상대 링크를 새 위치 기준으로 다시 쓴다.

    :func:`_rewrite_markdown_links` 는 **대상이 이동한** 링크를 고친다. 이 함수는
    반대 방향이다 — 대상(`active/main/state.json` 같은 살아 있는 파일)은 그대로인데
    문서가 `active/<b>/` → `archived/<b>/` 로 옮겨져 상대 경로의 기준점이 바뀌었다.
    브랜치 세션 기록이 active/main 을 가리키면 아카이브 후 archived/main 으로 풀려
    깨진다 (TASK-2026-08-14-main-006 — 같은 함정을 사람이 두 번 밟고서야 도구가 됐다).

    판정은 **이동 전 기준으로 풀리던 링크인가**다:

    - 새 위치에서 풀리면 → 살아 있는 링크, 불변 (브랜치 내부 상호 링크가 여기 온다 —
      문서와 대상이 함께 옮겨져 상대 구조가 보존된다)
    - 새 위치에서 안 풀리고 **옛 위치에서 풀리면** → 재작성 (문서 이동이 깬 링크)
    - 옛 위치에서도 안 풀리면 → 불변. 태어날 때부터 깨진 링크를 고친 척하지 않는다 —
      그건 `check_archive_history_integrity` 가 잡아야 할 진짜 결함이다
      (2026-08-13 에 실제로 그런 링크가 1건 있었다)
    """
    old_doc_dir, new_doc_dir = Path(old_doc_dir).resolve(), Path(new_doc_dir).resolve()

    def map_target(path_part: str) -> Path | None:
        if (new_doc_dir / path_part).resolve().exists():
            return None
        old_target = (old_doc_dir / path_part).resolve()
        return old_target if old_target.exists() else None

    return _map_relative_links(text, doc_dir=new_doc_dir, map_target=map_target)


def write_metadata(
    dst: Path, branch: str, *, repo_root: Path, open_task_list: list[tuple[str, str]],
) -> None:
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
                # 미완료인 채로 아카이브된 것이 있으면 **명시적으로** 남긴다.
                # 기본 경로에서는 애초에 막히므로, 여기 값이 비어있지 않다는 것은
                # 운영자가 `--allow-open-tasks` 로 의도해서 넘겼다는 뜻이다.
                "open_task_ids": [tid for tid, _ in open_task_list],
                "note": "종료된 브랜치의 메모리. 과거 이력 조회 대상 (읽기 전용).",
            },
            ensure_ascii=False, indent=2,
        ) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--memory-root", default=str(memory_dir_for_workspace(REPO_ROOT)))
    p.add_argument("--branch", action="append", dest="branches", default=[],
                   help="강제로 아카이브할 브랜치 (git 존재 여부 무시)")
    p.add_argument("--keep", action="append", default=["main"],
                   help="아카이브에서 제외할 브랜치 (default: main)")
    p.add_argument("--allow-open-tasks", action="store_true",
                   help="미완료 task 가 있어도 아카이브한다 (기본은 차단 — 소실 방지)")
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
        open_list = open_tasks(path)
        if open_list and not args.allow_open_tasks:
            # **미완료 task 를 데리고 아카이브로 들어가면 그대로 소실된다.**
            # archived/ 는 어떤 집계도 안 본다 (state 생성기·dashboard 모두 active/ 만
            # 훑는다). 실측 2026-08-13: `…-guard-003`(planned)이 그렇게 사라졌고,
            # 사람이 눈으로 알아채 이월했다. 그래서 **기본은 차단**이다 — 보이게
            # 하는 것으로는 부족하고, 이월 여부는 사람이 판단할 일이다.
            candidates.append({
                "branch": name, "action": "blocked",
                "reason": (
                    f"미완료 task {len(open_list)}건 — 먼저 이월하거나 닫을 것: "
                    + ", ".join(f"{tid}({st})" for tid, st in open_list)
                ),
                "open_tasks": [{"id": tid, "status": st} for tid, st in open_list],
            })
            continue
        candidates.append({
            "branch": name, "action": "archive",
            "reason": "강제 지정" if name in forced else "git 에 브랜치 없음 (종료됨)",
            "from": str(path), "to": str(archived_dir / name),
            "open_tasks": [{"id": tid, "status": st} for tid, st in open_list],
        })

    result = {
        "mode": "apply" if args.apply else "dry-run",
        "current_branch": current,
        "candidates": candidates,
        "archived": 0,
        "blocked": sum(1 for c in candidates if c["action"] == "blocked"),
        "rewritten_references": [],
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
            open_list = [(o["id"], o["status"]) for o in c.get("open_tasks", [])]
            write_metadata(dst, c["branch"], repo_root=REPO_ROOT,
                           open_task_list=open_list)
            # 이동 **직후** 참조를 옮긴다. 이 한 걸음이 빠져 있어서 아카이브가
            # 이력을 끊어 왔다 (모듈 docstring 의 실측).
            result["rewritten_references"].extend(rewrite_moved_references(
                branch=c["branch"], memory_root=memory_root, repo_root=REPO_ROOT,
            ))
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
            for ref in result["rewritten_references"]:
                print(f"  ref 재작성  {ref}")
        if result["blocked"]:
            print(f"\n  → 미완료 task 때문에 {result['blocked']}건을 막았다. "
                  "`wk backlog-update` 로 이월하거나 닫은 뒤 다시 실행한다 "
                  "(의도한 것이면 --allow-open-tasks).")
        for e in result["errors"]:
            print(f"  ERROR {e}", file=sys.stderr)
        if any(c["action"] == "archive" for c in candidates) and not args.apply:
            print("\n  → 실제 이동: --apply (commit/push 는 하지 않음; 작업 브랜치 PR 에 실어 보내세요)")
    return 1 if (result["errors"] or result["blocked"]) else 0


if __name__ == "__main__":
    raise SystemExit(main())
