"""한 호스트의 워크벤치들 — 포트 분배 · 저장소 이름 · 호스트 공용 목록 (TASK-2026-11-17-claude-remote-sync-check-234c32-005).

소유자 지시(2026-11-17): 여러 세션(worktree · 저장소)이 동시에 작업하면 워크벤치가 여러 개 뜬다. 결정 D1=hash · D2=list.

- **포트** — ``--port`` 를 주지 않으면 checkout 경로의 해시로 ``PORT_BASE`` ~ ``PORT_BASE + PORT_SPAN - 1`` 중 하나를
  먼저 고르고(같은 checkout 은 늘 같은 포트 — 북마크가 유지된다), 차 있으면 그 범위에서 다음 포트로 넘어간다.
- **저장소 이름** — worktree 의 디렉터리 이름이 아니라 저장소 이름: ``.git`` 파일(``gitdir: …/.git/worktrees/<w>``)을 따라가
  공통 ``.git`` 의 부모 이름을 쓴다. git 이 아니면 checkout 디렉터리 이름. 하위 프로세스 없이 파일만 읽는다.
- **호스트 공용 목록** — 서버가 뜨면 ``<cache>/workflow_kit/workbenches/<checkout 해시>.json`` 에 자기를 적고 내릴 때 지운다.
  ``workbench --list`` 는 pid 가 살아 있는 것만 보인다(죽은 기록은 지운다). 위치는 ``WORKFLOW_KIT_WORKBENCH_REGISTRY`` 로 바꿀 수 있다
  (검사는 임시 디렉터리로 돌린다 — 사용자 캐시를 건드리지 않는다).
"""

from __future__ import annotations

import hashlib
import json
import os
import secrets
from pathlib import Path
from typing import Any

PORT_BASE = 8766
PORT_SPAN = 100
REGISTRY_ENV = "WORKFLOW_KIT_WORKBENCH_REGISTRY"


def checkout_key(workspace: Path) -> str:
    return hashlib.sha256(str(workspace.resolve()).encode("utf-8")).hexdigest()[:16]


def preferred_port(workspace: Path) -> int:
    return PORT_BASE + int(checkout_key(workspace), 16) % PORT_SPAN


def candidate_ports(workspace: Path) -> list[int]:
    """해시 포트부터 범위를 한 바퀴 — 차 있는 포트를 건너뛸 순서."""
    first = preferred_port(workspace) - PORT_BASE
    return [PORT_BASE + (first + step) % PORT_SPAN for step in range(PORT_SPAN)]


def repo_name(workspace: Path) -> str:
    """저장소 이름 — worktree 면 공통 ``.git`` 의 부모 이름, git 이 아니면 디렉터리 이름."""
    root = workspace.resolve()
    marker = root / ".git"
    try:
        if marker.is_file():
            text = marker.read_text(encoding="utf-8").strip()
            if text.startswith("gitdir:"):
                gitdir = Path(text[len("gitdir:"):].strip())
                if not gitdir.is_absolute():
                    gitdir = (root / gitdir).resolve()
                # <repo>/.git/worktrees/<name> → <repo>/.git
                common = gitdir.parent.parent if gitdir.parent.name == "worktrees" else gitdir
                if common.name == ".git":
                    return common.parent.name
                return common.name.removesuffix(".git") or root.name
    except (OSError, UnicodeDecodeError):
        pass
    return root.name


def head_branch(workspace: Path) -> str | None:
    """checkout 의 지금 브랜치 — ``HEAD`` 파일만 읽는다 (목록은 띄운 뒤 바뀐 브랜치를 보여야 한다). 분리 HEAD · git 아님은 ``None``."""
    root = workspace.resolve()
    marker = root / ".git"
    try:
        if marker.is_file():
            text = marker.read_text(encoding="utf-8").strip()
            gitdir = Path(text[len("gitdir:"):].strip()) if text.startswith("gitdir:") else None
            if gitdir is None:
                return None
            head = (gitdir if gitdir.is_absolute() else root / gitdir) / "HEAD"
        else:
            head = marker / "HEAD"
        ref = head.read_text(encoding="utf-8").strip()
    except (OSError, UnicodeDecodeError):
        return None
    return ref[len("ref: refs/heads/"):] if ref.startswith("ref: refs/heads/") else None


def registry_dir() -> Path:
    override = os.environ.get(REGISTRY_ENV)
    if override:
        return Path(override)
    base = os.environ.get("XDG_CACHE_HOME") or (Path.home() / ".cache")
    return Path(base) / "workflow_kit" / "workbenches"


def register(workspace: Path, payload: dict[str, Any]) -> Path | None:
    """자기를 호스트 공용 목록에 적는다. 쓰지 못하면 ``None`` — 목록은 편의라 서버 시작을 막지 않는다."""
    try:
        directory = registry_dir()
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"{checkout_key(workspace)}.json"
        temp = directory / f".{path.name}.{os.getpid()}.{secrets.token_hex(4)}"
        temp.write_text(json.dumps({**payload, "workspace": str(workspace.resolve()), "repo": repo_name(workspace)},
                                   ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        os.replace(temp, path)
        return path
    except OSError:
        return None


def unregister(workspace: Path, pid: int) -> None:
    path = registry_dir() / f"{checkout_key(workspace)}.json"
    try:
        if json.loads(path.read_text(encoding="utf-8")).get("pid") == pid:
            path.unlink(missing_ok=True)
    except (OSError, ValueError):
        pass


def live_entries(pid_alive: Any) -> list[dict[str, Any]]:
    """살아 있는 워크벤치들 — 죽은 pid 의 기록은 지운다. 저장소 · 포트 순."""
    directory = registry_dir()
    out: list[dict[str, Any]] = []
    if not directory.is_dir():
        return out
    for path in sorted(directory.glob("*.json")):
        try:
            entry = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not isinstance(entry, dict) or not pid_alive(entry.get("pid")):
            path.unlink(missing_ok=True)
            continue
        out.append(entry)
    out.sort(key=lambda e: (str(e.get("repo", "")), int(e.get("port") or 0)))
    return out
