"""workflow_kit.common.dashboard_workspace_roots - Panel 5 workspace root 합류 helper.

`dashboard_data.py` 에서 verbatim 분리 (2026-08-11). branch-scoped 메모리 집계에
필요한 state.json 경로 union + worktree/registry/env 기반 추가 root 발견 + in-flight
신뢰도(3-way signal) 계산을 담당한다. `collect_recent_releases` (집계 본체) 는
`dashboard_data.py` 에 남아 이 module 의 helper 를 호출한다.
"""

from __future__ import annotations

import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

from workflow_kit.common.paths import memory_active_dir

__all__: list[str] = [
    "_branch_state_paths",
    "_auto_extra_roots",
    "_env_extra_roots",
    "_worktree_branch_map",
    "_state_path_to_worktree_root",
    "_confidence_for_state_path",
    "_registry_extra_roots",
]


def _branch_state_paths(*roots: Path) -> list[Path]:
    """`active/<branch>/state.json` 을 모두 반환 (branch-scoped 집계용).

    브랜치별 메모리에서는 각 브랜치가 자기 state.json 을 가지므로, 프로젝트 전체의
    "현재 상태"는 이들을 합친 *뷰* 로 계산한다. 별도 집계 파일을 커밋하지 않으므로
    protected main 에서도 merge 마다 갱신할 대상이 생기지 않는다.

    v0.15.20+: 단일 `root` 호출은 그대로 동작 (후방 호환). 복수 `*roots` 를 넘기면
    `active/<branch>/state.json` 들을 union + dedupe (정규화 경로) + sort 해서 돌려준다.
    registry 가 무엇을 훑을지 알려주는 자리이며 (multi_workspace_orchestration.md §7.3),
    registry 미존재 시 호출자(``collect_recent_releases``)가 자체적으로 worktree 경로를
    합류시킨다.
    """
    seen: set[Path] = set()
    out: list[Path] = []
    for raw in roots:
        if raw is None:
            continue
        try:
            root = Path(raw)
        except TypeError:
            continue
        active = memory_active_dir(root)
        if not active.is_dir():
            continue
        for p in active.rglob("state.json"):
            if not p.is_file():
                continue
            try:
                key = p.resolve()
            except OSError:
                key = p
            if key in seen:
                continue
            seen.add(key)
            out.append(p)
    return sorted(out)


def _auto_extra_roots(self_root: Path) -> list[Path]:
    """`self_root` 외에 *같은 저장소* 의 worktree 경로를 자동으로 합류시킨다.

    registry 없이도 한 저장소 안의 여러 worktree 메모리를 dashboard 가 모아 보게 하기
    위한 0-config 경로 (TASK-2026-08-08-main-003, multi_workspace_orchestration.md §7.3).
    `git` 부재 / `git worktree list` 실패 / 결과 0개 시 조용히 빈 리스트를 돌려준다.
    """
    try:
        proc = subprocess.run(
            ["git", "worktree", "list", "--porcelain"],
            cwd=self_root,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []
    if proc.returncode != 0 or not proc.stdout:
        return []
    try:
        self_key = self_root.resolve()
    except OSError:
        self_key = self_root
    extras: list[Path] = []
    for line in proc.stdout.splitlines():
        stripped = line.strip()
        if not stripped.startswith("worktree "):
            continue
        candidate = Path(stripped[len("worktree "):].strip())
        try:
            key = candidate.resolve()
        except OSError:
            key = candidate
        if key == self_key:
            continue
        extras.append(candidate)
    return extras


def _env_extra_roots() -> list[Path]:
    """`WORKFLOW_EXTRA_ROOTS` env (`os.pathsep` 구분) → 경로 목록.

    빈 항목 / 존재하지 않는 경로여도 *조용히* 유지한다 — 호출자(
    ``_branch_state_paths``)가 `is_dir()` 체크로 알아서 거른다.
    """
    raw = os.environ.get("WORKFLOW_EXTRA_ROOTS", "")
    if not raw:
        return []
    out: list[Path] = []
    for piece in raw.split(os.pathsep):
        p = piece.strip()
        if not p:
            continue
        out.append(Path(p))
    return out


# ---------------------------------------------------------------------------
# v0.15.22+ (TASK-2026-08-08-main-014, §0.8 #2) — in-flight 신뢰도 (3-way signal)
# ---------------------------------------------------------------------------


def _worktree_branch_map(self_root: Path) -> dict[str, str]:
    """`git worktree list --porcelain` → ``{abs_path_str: branch_str}`` 매핑.

    `git` 부재 / 실패 / 결과 0개 시 빈 dict. registry 의 *branch 정합 확인* 용
    단일 경로 — confidence() 의 3-way 신호 (path + last_seen + branch) 중 마지막.
    """
    try:
        proc = subprocess.run(
            ["git", "worktree", "list", "--porcelain"],
            cwd=self_root,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return {}
    if proc.returncode != 0 or not proc.stdout:
        return {}
    out: dict[str, str] = {}
    cur_path: Path | None = None
    cur_branch: str | None = None
    for line in proc.stdout.splitlines():
        if line.startswith("worktree "):
            if cur_path is not None and cur_branch is not None:
                try:
                    out[str(cur_path.resolve())] = cur_branch
                except OSError:
                    out[str(cur_path)] = cur_branch
            cur_path = Path(line[len("worktree "):].strip())
            cur_branch = None
        elif line.startswith("branch "):
            ref = line[len("branch "):].strip()
            # refs/heads/<name> → <name> 변환
            if ref.startswith("refs/heads/"):
                ref = ref[len("refs/heads/"):]
            cur_branch = ref
    # 마지막 entry
    if cur_path is not None and cur_branch is not None:
        try:
            out[str(cur_path.resolve())] = cur_branch
        except OSError:
            out[str(cur_path)] = cur_branch
    return out


def _state_path_to_worktree_root(state_path: Path) -> Path | None:
    """`<wt>/ai-workflow/memory/active/<branch>/state.json` → `<wt>/`.

    state.json 의 `parents[4]` 가 worktree root (state.json, <branch>, active, memory,
    ai-workflow, worktree_root). 5단계 위로 갈 수 없으면 None — 호출자가 fresh 로
    fallback 한다.
    """
    try:
        return state_path.parents[4]
    except IndexError:
        return None


def _confidence_for_state_path(
    state_path: Path,
    *,
    main_root: Path,
    registry_entries: list[Any],
    branch_map: dict[str, str],
    now: datetime | None = None,
) -> str:
    """state.json 한 건의 in-flight 신뢰도 계산. dashboard Panel 5 가 호출.

    결정 순서 (§0.8 #2 정공법):
        1. worktree root 가 main_root 와 같으면 → ``fresh`` (merge 후라 신뢰)
        2. registry 에 등록돼 있으면 → ``workspace_registry.confidence(entry, ...)``
        3. 그 외 (registry 미등록) → ``fresh`` (penalty ❌ — 등록 누락을 *신뢰도 저하*
           로 보지 않음. §0.8 #2 의 *표시* 가 *판정* 으로 번지지 않게.)
    """
    wt = _state_path_to_worktree_root(state_path)
    if wt is None:
        return "fresh"
    try:
        wt_key = str(wt.resolve())
        main_key = str(main_root.resolve())
    except OSError:
        wt_key = str(wt)
        main_key = str(main_root)
    if wt_key == main_key:
        return "fresh"
    # local import: registry module 의 import cycle 회피 (§0.7 _registry_extra_roots 와 같은 패턴).
    from workflow_kit.common import workspace_registry as _wr  # noqa: PLC0415
    for entry in registry_entries:
        if not getattr(entry, "path", None):
            continue
        try:
            if str(Path(entry.path).resolve()) != wt_key:
                continue
        except OSError:
            if str(entry.path) != wt_key:
                continue
        return _wr.confidence(
            entry,
            worktree_branch=branch_map.get(wt_key),
            now=now,
        )
    return "fresh"


def _registry_extra_roots(self_root: Path) -> list[Path]:
    """workspace_registry (§7.1) 가 알려주는 호스트의 추가 worktree 경로.

    v0.15.24+ (TASK-2026-08-08-main-016) — local + remote (federation) 모두 합류.
    ``merge_with_remotes()`` 가 local registry + known_hosts 의 remote registry 들을
    dedup + last_seen_at 최신 우선으로 합친 결과를 path 화. registry 부재 / read
    실패 / 모든 remote 가 unreachable 시 *조용히* local 만 반환 (caller 가 fallback).

    Remote path 가 이 호스트의 filesystem 에 *없어도* rglob 가 silent skip
    (``is_file()`` 체크) — 그래서 *조용히* 동작. remote 의 in-flight 가시성은
    Panel 5 의 metadata (source_host_id) 로 식별 가능.
    """
    try:
        # local import: dashboard 가 registry 모듈에 *순환 의존* 으로 끌려 들어가는
        # 일을 피한다. registry 자체가 dashboard 를 import 하지 않으니 안전.
        from workflow_kit.common import workspace_registry as _wr
    except ImportError:
        return []
    try:
        local_entries = _wr.list_entries()
        # dashboard 호출은 *짧은* timeout (default 1s) — 사용자 응답성을 우선.
        # cache fallback 이 graceful skip 을 보장하므로 timeout 도 안전.
        merged, _errors = _wr.merge_with_remotes(
            local_entries,
            timeout=float(os.environ.get("WORKFLOW_DASHBOARD_PULL_TIMEOUT", "1.0") or 1.0),
            use_cache=True,
        )
    except Exception:  # noqa: BLE001 — 모든 registry 실패 시 조용히 empty
        return []
    try:
        self_key = self_root.resolve()
    except OSError:
        self_key = self_root
    out: list[Path] = []
    seen: set[Path] = set()
    for entry in merged:
        path_str = getattr(entry, "path", None)
        if not path_str:
            continue
        p = Path(path_str)
        try:
            key = p.resolve()
        except OSError:
            key = p
        if key == self_key:
            continue
        if key in seen:
            continue
        seen.add(key)
        out.append(p)
    return out
