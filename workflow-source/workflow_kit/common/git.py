"""Git utilities for workflow automation."""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass, asdict
from typing import Any, List, Dict, Optional
from pathlib import Path

@dataclass
class CommitEntry:
    subject: str
    hash: str
    author: str
    date: str
    category: str

def get_git_log(repo_path: str | Path, commit_range: str) -> List[str]:
    try:
        cmd = ["git", "-C", str(repo_path), "log", "--pretty=format:%s|%h|%an|%ad", "--date=iso", commit_range]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        if not result.stdout.strip():
            return []
        return result.stdout.strip().split("\n")
    except subprocess.CalledProcessError:
        return []

def categorize_message(message: str) -> str:
    m = message.lower()
    if any(kw in m for kw in ["feat", "add", "implement"]): return "Feature"
    if any(kw in m for kw in ["fix", "bug", "patch"]): return "Bug Fix"
    if any(kw in m for kw in ["docs", "readme", "markdown"]): return "Docs"
    if any(kw in m for kw in ["refactor", "clean", "simplify"]): return "Refactor"
    if any(kw in m for kw in ["test", "spec", "check"]): return "Test"
    if any(kw in m for kw in ["chore", "config", "build", "ci", "deps"]): return "Chore"
    return "Other"

def process_logs(logs: List[str]) -> List[CommitEntry]:
    entries = []
    for line in logs:
        parts = line.split("|")
        if len(parts) < 4: continue
        subject, h, author, date = parts[0], parts[1], parts[2], parts[3]
        category = categorize_message(subject)
        entries.append(CommitEntry(subject, h, author, date, category))
    return entries

def generate_git_markdown_summary(entries: List[CommitEntry], commit_range: str) -> str:
    if not entries:
        return f"No commits found in range `{commit_range}`."

    cat_map: Dict[str, List[str]] = {}
    for e in entries:
        if e.category not in cat_map: cat_map[e.category] = []
        cat_map[e.category].append(f"- {e.subject} (`{e.hash}`)")

    md = [f"### Git 작업 요약 ({commit_range})\n"]
    for cat in ["Feature", "Bug Fix", "Refactor", "Docs", "Test", "Chore", "Other"]:
        if cat in cat_map:
            md.append(f"#### {cat}")
            md.extend(cat_map[cat])
            md.append("")
    return "\n".join(md)

def summarize_git_history(repo_path: str | Path, commit_range: str) -> dict[str, Any]:
    logs = get_git_log(repo_path, commit_range)
    entries = process_logs(logs)
    return {
        "entries": entries,
        "markdown": generate_git_markdown_summary(entries, commit_range),
        "commit_count": len(entries)
    }


@dataclass
class RemoteTaskIds:
    """원격이 이미 알고 있는 task ID 와, 그것을 **어떻게 알았는지**.

    `consulted` 가 False 면 목록이 비어 있다는 사실이 '원격에 없다' 는 뜻이 아니라
    **'못 봤다'** 는 뜻이다 — 그 둘을 같게 취급하면 조용한 거짓 안심이 된다
    (`_doc_stamp.py` / `check_smoke_trend_cross` 와 같은 규약: 모름 ≠ 안전).
    """
    ids: frozenset[str]
    consulted: bool
    ref: str
    reason: str


def remote_known_task_ids(
    tasks_dir: str | Path,
    *,
    remote: str = "origin",
    branch: str | None = None,
    timeout: int = 15,
) -> RemoteTaskIds:
    """`refs/remotes/<remote>/<branch>` 가 들고 있는 task ID 집합.

    ## 왜 필요한가 (TASK-2026-09-07-main-006)

    채번기는 로컬 `tasks/` (또는 오늘자 backlog 인덱스) 만 읽는다. 그런데
    `seed_workspace_memory.next_task_id` 의 docstring 은 "번호는 브랜치 안에서만
    매긴다 — 브랜치별로 격리돼 있으므로 **다른 호스트가 동시에 만들어도 겹치지
    않는다**" 고 **보증**했다. 브랜치 격리는 *브랜치가 다를 때* 성립하는 것이고,
    두 호스트가 **같은 브랜치**(대개 main)에 있으면 아무것도 막지 않는다.

    2026-09-04 실측: 두 호스트가 같은 날 각각 `main-002` 를 매겼고, **push 가
    거절돼서야** 알았다. 뒤에 올린 쪽이 자기 ID 를 비키면서 코드 주석과 문서의
    ID 참조 6곳을 함께 고쳐야 했다.

    **네트워크를 쓰지 않는다.** 원격 추적 ref 는 로컬에 있으므로 `git ls-tree`
    하나로 읽힌다. 대신 그 ref 는 마지막 fetch 시점에 멈춰 있어서, 이 함수는
    무엇을 근거로 답했는지(`consulted` / `ref` / `reason`)를 함께 돌려준다 —
    호출자가 "확인했다" 와 "못 봤다" 를 구분해 사용자에게 말할 수 있어야 한다.
    fetch 는 여기서 하지 않는다: 채번마다 네트워크를 타면 오프라인에서 도구가
    멈추고, 느려지며, 무엇보다 **실패를 조용히 통과로 바꾸기 쉽다**.

    저장소 루트와 pathspec 은 **여기서** 구한다. 호출자가 상대경로를 만들게 하면
    절대경로를 넘기기 쉽고, 그러면 `ls-tree` 가 아무것도 못 찾고 **조용히 빈
    목록**을 낸다 — 그것을 "원격에 task 가 없다" 로 읽으면 채번이 다시 겹친다.
    조용한 빈 결과가 곧 이 함수가 막으려는 실패 모드다.

    Args:
        tasks_dir: tasks 디렉터리 (절대경로 권장). 이 경로에서 저장소를 찾는다.
        remote: 원격 이름 (기본 `origin`).
        branch: 대상 브랜치. 미지정 시 현재 브랜치.

    Returns:
        `RemoteTaskIds` — `consulted=False` 면 `ids` 는 **판단 근거가 아니다**.
    """
    loc = _remote_tasks_location(tasks_dir, remote, branch, timeout)
    if isinstance(loc, RemoteTaskIds):
        return loc
    root, relpath, ref = loc

    listing = _run_git(
        ["ls-tree", "-r", "--name-only", ref, "--", relpath], root, timeout
    )
    if listing is None or listing.returncode != 0:
        return RemoteTaskIds(frozenset(), False, ref, f"{ref} 의 트리를 읽지 못했다")

    ids = {
        Path(line).stem
        for line in listing.stdout.splitlines()
        if line.endswith(".md") and Path(line).name.startswith("TASK-")
    }
    return RemoteTaskIds(frozenset(ids), True, ref, "")


@dataclass
class TaskIdCollisions:
    """같은 task ID 가 로컬과 원격에서 **다른 task** 를 가리키는 경우.

    `consulted` 가 False 면 `collisions` 가 비어 있다는 것은 '충돌 없음' 이 아니라
    **'못 봤다'** 다 (`RemoteTaskIds` 와 같은 규약).
    """
    collisions: tuple[tuple[str, str, str], ...]   # (task_id, 로컬 제목, 원격 제목)
    consulted: bool
    ref: str
    reason: str


def _task_heading(text: str) -> str:
    """task 파일의 `# TASK-… — 제목` 줄. 없으면 빈 문자열."""
    for line in text.splitlines():
        if line.startswith("# TASK-"):
            return line.strip()
    return ""


def task_id_collisions(
    tasks_dir: str | Path,
    *,
    remote: str = "origin",
    branch: str | None = None,
    timeout: int = 15,
) -> TaskIdCollisions:
    """워킹 트리의 task 파일 중 **원격에 같은 ID 가 다른 제목으로** 있는 것.

    ## 왜 필요한가 (TASK-2026-09-23-main-016)

    채번은 원격 추적 ref 도 본다(`remote_known_task_ids`). 그래도 **아직 커밋하지 않은**
    task 는 누구도 볼 수 없다 — 87차 실측: 한 에이전트가 미커밋으로
    `TASK-2026-09-23-main-009` 를 쓰는 사이 다른 호스트가 같은 ID 를 다른 task 에
    채번해 push 했고, 동기화 때 소유자 확인을 받아 재번호했다. 그동안 대시보드의
    `multi_agent_concurrent_write_conflict` 는 git 충돌 표식만 세어 **0 (pass)** 였다.
    채번 시점에 막을 수 없는 경우이므로 **fetch 뒤 검출**이 수단이다.

    후보는 `git diff --name-only <ref>` 하나로 얻는다 — ref 와 워킹 트리가 **다른**
    파일이고, ref 에만 있고 인덱스에 없는 경로(= 로컬이 untracked 로 같은 이름을 쓴
    경우)도 여기 나온다. untracked 목록을 따로 구했던 첫 구현은 되주입에서 판정에
    아무 기여가 없음이 드러나 걷었다. 후보 중 원격에 있는 것만 제목 줄을 비교한다 —
    같은 task 의 상태 갱신은 제목이 같으므로 충돌이 아니다.
    네트워크는 쓰지 않는다 (ref 는 마지막 fetch 시점).
    """
    loc = _remote_tasks_location(tasks_dir, remote, branch, timeout)
    if isinstance(loc, RemoteTaskIds):
        return TaskIdCollisions((), False, loc.ref, loc.reason)
    root, relpath, ref = loc

    changed = _run_git(["diff", "--name-only", ref, "--", relpath], root, timeout)
    remote_listing = _run_git(["ls-tree", "-r", "--name-only", ref, "--", relpath], root, timeout)
    if any(p is None or p.returncode != 0 for p in (changed, remote_listing)):
        return TaskIdCollisions((), False, ref, f"{ref} 와 워킹 트리를 비교하지 못했다")
    assert changed is not None and remote_listing is not None
    on_remote = set(remote_listing.stdout.splitlines())
    candidates = {
        line for line in changed.stdout.splitlines()
        if line in on_remote and Path(line).name.startswith("TASK-") and line.endswith(".md")
    }

    found: list[tuple[str, str, str]] = []
    for rel in sorted(candidates):
        local_path = root / rel
        if not local_path.is_file():
            continue  # 로컬에서 지운 파일은 충돌이 아니다
        shown = _run_git(["show", f"{ref}:{rel}"], root, timeout)
        if shown is None or shown.returncode != 0:
            return TaskIdCollisions(tuple(found), False, ref, f"{ref}:{rel} 를 읽지 못했다")
        local_head = _task_heading(local_path.read_text(encoding="utf-8", errors="replace"))
        remote_head = _task_heading(shown.stdout)
        if local_head != remote_head:
            found.append((Path(rel).stem, local_head, remote_head))
    return TaskIdCollisions(tuple(found), True, ref, "")


def _remote_tasks_location(
    tasks_dir: str | Path, remote: str, branch: str | None, timeout: int,
) -> "tuple[Path, str, str] | RemoteTaskIds":
    """(저장소 루트, tasks 의 저장소 상대경로, 원격 추적 ref) — 못 구하면 그 이유를 담은
    `RemoteTaskIds(consulted=False)`.

    `remote_known_task_ids` 와 `task_id_collisions` 가 **같은 해석**을 쓴다 — 경로
    계산이 둘로 갈라지면 한쪽만 절대경로를 넘겨 조용히 빈 목록을 낸다.
    """
    tasks_path = Path(tasks_dir)
    # 디렉터리가 아직 없을 수 있다 (seed 직전). 존재하는 조상에서 저장소를 찾는다.
    anchor = tasks_path
    while not anchor.exists() and anchor != anchor.parent:
        anchor = anchor.parent

    top = _run_git(["rev-parse", "--show-toplevel"], anchor, timeout)
    if top is None or top.returncode != 0 or not top.stdout.strip():
        return RemoteTaskIds(frozenset(), False, "", "git 저장소를 찾지 못했다")
    root = Path(top.stdout.strip())

    try:
        relpath = tasks_path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return RemoteTaskIds(
            frozenset(), False, "",
            f"tasks 디렉터리가 저장소({root}) 밖에 있다: {tasks_path}",
        )

    slug = branch
    if slug is None:
        proc = _run_git(["rev-parse", "--abbrev-ref", "HEAD"], root, timeout)
        if proc is None or proc.returncode != 0 or not proc.stdout.strip():
            return RemoteTaskIds(frozenset(), False, "", "현재 브랜치를 얻지 못했다")
        slug = proc.stdout.strip()
    ref = f"refs/remotes/{remote}/{slug}"

    verify = _run_git(["rev-parse", "--verify", "--quiet", ref], root, timeout)
    if verify is None or verify.returncode != 0:
        return RemoteTaskIds(
            frozenset(), False, ref,
            f"원격 추적 ref 가 없다 ({ref}) — 원격이 없거나 이 브랜치를 아직 fetch 하지 않았다",
        )
    return root, relpath, ref


def _run_git(
    args: List[str], cwd: Path, timeout: int
) -> "subprocess.CompletedProcess[str] | None":
    """`git <args>` 실행. 실행 자체가 불가하면 ``None`` (호출자가 '못 봤다' 로 다룬다)."""
    try:
        return subprocess.run(
            ["git", *args], cwd=str(cwd), capture_output=True, text=True, timeout=timeout
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
