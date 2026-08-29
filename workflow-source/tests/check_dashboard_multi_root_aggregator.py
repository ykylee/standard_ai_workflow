#!/usr/bin/env python3
"""Smoke test — dashboard `_branch_state_paths` 복수 root 취합 (6 cases).

## 왜 이 검사가 필요한가

표준 §10.2 의 dashboard Panel 5 는 *모든 브랜치의 state.json 을 합친 뷰* 다 (§7.3).
v0.15.20+ 부터는 *동일 저장소의 다른 worktree* 도 자동으로 합류시켜야 한다 —
registry 가 아직 없는 0-config 경로 (TASK-2026-08-08-main-003, handoff §5 후보 1).

핵심 위험은 두 가지다:

1. **시그니처 회귀** — `_branch_state_paths(root)` 의 단일 호출 결과가 그대로
   유지되지 않으면 기존 dashboard 통합 검사(v0.13.0~)가 모두 깨진다.
2. **집계 파일로의 회귀** — §6 의 *"집계는 파일이 아니라 뷰"* 원칙을 새 파일 생성으로
   어기면 안 된다. 이 검사는 *view* 가 맞는지를 직접 본다.

6 cases:
  1) 단일 root 호출 = 기존 동작 / 후방 호환
  2) 추가 root 의 state.json 이 timeline 에 합류 (Panel 5 data shape)
  3) dedupe — 동일 root 를 두 번 넣어도 한 번만
  4) `WORKFLOW_EXTRA_ROOTS` env 1개로 합류
  5) `git worktree list` 결과의 self 경로 자동 제외
  6) `git` 부재 시뮬레이션 — `_auto_extra_roots` 가 빈 리스트로 fallback
     (실제 시뮬레이션: `cwd` 를 git 저장소가 아닌 tmpdir 로 둠)

Refs:
  - workflow-source/core/multi_workspace_orchestration.md §7.3
  - workflow-source/core/multi_workspace_orchestration.md §6 (파생 뷰 원칙)
  - workflow-source/workflow_kit/common/dashboard_data.py (`_branch_state_paths`,
    `_auto_extra_roots`, `_env_extra_roots`, `collect_recent_releases`)
"""

from __future__ import annotations

#: 이 검사의 입력 표면 (spec `core/test_impact_tiering_spec.md` §2).
#: 게이트 채취 실측에서 뽑아 넓은 쪽으로 올렸다 — 좁으면 meta-watch 가 red 로 잡는다.
WATCHES = (
    "workflow-source/pyproject.toml",
    "workflow-source/workflow_kit/*",
)

import json
import os
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from workflow_kit.common.dashboard_data import (  # noqa: E402
    _branch_state_paths,
    _auto_extra_roots,
    _env_extra_roots,
    collect_recent_releases,
)


def _write_state(root: Path, branch: str, items: list[str]) -> Path:
    """tempdir 의 정합 layout(`<root>/ai-workflow/memory/active/<branch>/state.json`)
    에 테스트용 state.json 을 만든다. 단일 recent_done_items 만 채운다."""
    state_path = root / "ai-workflow" / "memory" / "active" / branch / "state.json"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        json.dumps({"session": {"recent_done_items": items}}, ensure_ascii=False),
        encoding="utf-8",
    )
    return state_path


def _assert(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


def test_single_root_backward_compatible() -> None:
    """case 1: 단일 root 호출은 시그니처/결과 동일."""
    baseline = _branch_state_paths(REPO_ROOT)
    _assert(len(baseline) >= 1, "단일 root 호출 결과 0건 — 회귀 위험")
    # extra 가 비어 있으면 단일 호출과 같은 셋
    same = _branch_state_paths(REPO_ROOT, *[])
    _assert(
        [p.name for p in baseline] == [p.name for p in same],
        f"단일 root 와 *[] 호출 결과가 갈랐다: {baseline} vs {same}",
    )


def test_extra_root_merges_into_timeline() -> None:
    """case 2: 추가 root 의 state.json 이 Panel 5 timeline 에 합류.

    v1.1.5: primary root 를 **실제 저장소가 아니라 tmp fixture** 로 바꿨다.
    이전에는 REPO_ROOT 를 primary 로 써서 "저장소의 recent_done_items 가
    top_n(50) 미만" 이라는 암묵 전제가 있었고, 목록이 50개를 넘자 fixture
    marker 가 컷 밖으로 밀려 깨졌다 — 살아있는 저장소 상태는 기대값이 아니다
    (doctor exit-on-fail smoke 와 같은 부류). 합류 *메커니즘* 검증에는
    fixture 두 root 면 충분하다.
    """
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        primary = base / "primary"
        extra = base / "extra"
        _write_state(primary, "demo-feat-main", ["__primary_item__"])
        _write_state(extra, "demo-feat-x", ["__extra_marker__"])
        # baseline 도 extra_roots=() 명시 — 미지정이면 0-config 경로가 글로벌
        # registry 에 등록된 실제 워크스페이스들을 자동 합류시켜 (설계된 기능)
        # baseline 이 이 호스트의 registry 상태에 따라 달라진다.
        baseline = collect_recent_releases(primary, top_n=50, extra_roots=())
        merged = collect_recent_releases(
            primary, top_n=50, extra_roots=(extra,)
        )
    _assert(
        "__extra_marker__" in [it["preview"] for it in merged["timeline"]],
        f"extra root 의 marker 가 timeline 에 없음: {merged}",
    )
    _assert(
        merged["items_total"] >= baseline["items_total"] + 1,
        "extra 합류 후 items_total 이 늘어나지 않음",
    )


def test_dedupe_same_root_twice() -> None:
    """case 3: 동일 root 2번 넣어도 dedupe."""
    with tempfile.TemporaryDirectory() as td:
        tdp = Path(td)
        _write_state(tdp, "demo-feat-x", ["__dup_marker__"])
        once = _branch_state_paths(REPO_ROOT, tdp)
        twice = _branch_state_paths(REPO_ROOT, tdp, tdp)
    _assert(
        len(once) == len(twice),
        f"dedupe 실패: {len(once)} vs {len(twice)}",
    )


def test_env_extra_roots() -> None:
    """case 4: WORKFLOW_EXTRA_ROOTS env 1개로 합류."""
    saved = os.environ.pop("WORKFLOW_EXTRA_ROOTS", None)
    try:
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            _write_state(tdp, "demo-feat-y", ["__env_marker__"])
            os.environ["WORKFLOW_EXTRA_ROOTS"] = str(tdp)
            # env → _env_extra_roots 가 노출시키는지만 본다 (실제 collect 는
            # _auto_extra_roots 가 0-config 로 합류시키므로 별도 검증)
            env_paths = _env_extra_roots()
            _assert(
                tdp in env_paths,
                f"env 가 반영 안 됨: {env_paths}",
            )
    finally:
        if saved is None:
            os.environ.pop("WORKFLOW_EXTRA_ROOTS", None)
        else:
            os.environ["WORKFLOW_EXTRA_ROOTS"] = saved


def test_auto_extra_roots_excludes_self() -> None:
    """case 5: git worktree list 의 self 경로가 자동 합류에서 제외된다."""
    autos = _auto_extra_roots(REPO_ROOT)
    # 이 저장소는 단일 worktree 운영이므로 결과 0건이 정상 (self 1개만 발견되어 제외).
    # 그래도 self_root 와 같은 경로가 *없음* 만 검증하면 충분.
    self_key = REPO_ROOT.resolve()
    for p in autos:
        try:
            key = p.resolve()
        except OSError:
            key = p
        _assert(key != self_key, f"self 경로가 extras 에 들어갔다: {p}")


def test_git_failure_returns_empty() -> None:
    """case 6: git 부재 / 실패 시 fallback = 빈 리스트."""
    with tempfile.TemporaryDirectory() as td:
        not_repo = Path(td)
        # not_repo 는 git 저장소가 아니다 (worktree list 가 stderr 로 실패).
        autos = _auto_extra_roots(not_repo)
    _assert(
        autos == [],
        f"git 부재 환경에서 extras 가 비어있지 않음: {autos}",
    )


def main() -> int:
    tests = [
        test_single_root_backward_compatible,
        test_extra_root_merges_into_timeline,
        test_dedupe_same_root_twice,
        test_env_extra_roots,
        test_auto_extra_roots_excludes_self,
        test_git_failure_returns_empty,
    ]
    passed = 0
    for t in tests:
        try:
            t()
        except AssertionError as e:
            print(f"FAIL  {t.__name__}: {e}")
            return 1
        except Exception as e:  # pragma: no cover
            print(f"ERROR {t.__name__}: {type(e).__name__}: {e}")
            return 2
        print(f"PASS  {t.__name__}")
        passed += 1
    print(f"\n{passed}/{len(tests)} passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
