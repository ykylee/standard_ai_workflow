"""경로 해석기들이 **같은 workspace 에 같은 branch** 를 내는가 (v1.0.6).

## 왜 필요한가

v1.0.1 이 `branch_for_workspace` 를 만들며 규칙을 선언했다 — *workspace 로
파라미터화된 함수는 그 workspace 의 git 을 본다. 호출 위치가 답을 바꾸면 안 된다.*
그런데 그 규칙을 적용한 곳은 `state_path_for_workspace` **하나뿐**이었고,
profile 을 받는 `workflow_branch_dir` / `workflow_archived_branch_dir` 는
`get_current_branch()`(= 이 모듈이 속한 저장소)를 계속 쓰고 있었다. 실측:

    repoB(feature/probe-branch) 의 profile 로
      state_path_for_workspace → …/active/feature/probe-branch/state.json
      workflow_branch_dir      → …/active/main          ← 모듈 저장소의 branch

즉 **state.json 과 handoff/backlog 가 서로 다른 branch 디렉터리**를 가리켰다.

**기존 검사들이 이걸 못 본 이유**: fixture 를 `get_current_branch()` 로 만들고
그 결과를 `get_current_branch()` 와 비교했다. 자기 자신과 비교하는 검사는 두 해석기가
갈라져도 통과한다. 그래서 이 검사는 **모듈 저장소와 다른 branch 의 workspace** 를
실제로 만들어서 본다.

## 계약

1. 같은 workspace 에 대해 세 해석기(`state_path_for_workspace` /
   `workflow_branch_dir` / `workflow_archived_branch_dir`)가 **같은 slug** 를 쓴다.
2. 그 slug 는 **workspace 자신의** branch 다 (모듈 저장소의 것이 아니다).
3. workspace 가 git 저장소가 아니면 기존 동작(모듈 저장소 기준)으로 되돌아간다.

Cross-ref: releases/Beta-v1.0.0.md §2.50.
"""

from __future__ import annotations

import contextlib
import os
import subprocess
import sys
import tempfile
from collections.abc import Iterator
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SOURCE_ROOT))

from workflow_kit.common.paths import (  # noqa: E402
    BRANCH_ENV_KEYS,
    branch_for_workspace,
    get_current_branch,
    state_path_for_workspace,
    workflow_archived_branch_dir,
    workflow_branch_dir,
)

PROBE_BRANCH = "feature/branch-resolver-probe"


@contextlib.contextmanager
def _without_branch_env() -> Iterator[None]:
    """`BRANCH_ENV_KEYS` 를 비운다 — **CI 에서 이게 없으면 검사가 무력화된다**.

    GitHub Actions 는 `GITHUB_REF_NAME` 을 항상 세팅하고, 그 값이 *모든* workspace 에
    우선한다. 그래서 env 를 안 지우면 어떤 workspace 를 물어도 CI 의 branch 가 나와서
    "두 해석기가 합의한다" 가 자동으로 참이 된다 — 실제로 이 검사의 첫 버전이 로컬에서
    통과하고 러너에서 `fixture 준비 실패: main` 으로 깨졌다.

    env 우선 규칙 자체는 `test_branch_env_override_wins` 가 따로 고정한다.
    """
    saved = {k: os.environ.pop(k, None) for k in BRANCH_ENV_KEYS}
    try:
        yield
    finally:
        for key, value in saved.items():
            if value is not None:
                os.environ[key] = value


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(
        ["git", *args], cwd=str(cwd), check=True,
        capture_output=True, text=True, timeout=60,
        env={"PATH": "/usr/bin:/bin", "HOME": str(cwd), "GIT_CONFIG_GLOBAL": "/dev/null"},
    )


def _workspace(td: str, *, git: bool = True) -> Path:
    ws = Path(td) / "consumer"
    (ws / "docs").mkdir(parents=True)
    (ws / "docs" / "PROJECT_PROFILE.md").write_text("# Project Profile\n", encoding="utf-8")
    if git:
        _git(ws, "init", "-q", ".")
        _git(ws, "checkout", "-q", "-b", PROBE_BRANCH)
        _git(ws, "add", "-A")
        _git(ws, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "init")
    return ws


def _slug_after_memory(path: Path, marker: str) -> str:
    """`…/memory/<marker>/<slug>[/…]` 에서 slug 를 뽑는다."""
    parts = path.as_posix().split(f"/memory/{marker}/", 1)
    assert len(parts) == 2, path
    tail = parts[1]
    # state.json 은 `<slug>/state.json`, dir 은 `<slug>` 다. 파일명만 떼어 낸다.
    if tail.endswith("/state.json"):
        tail = tail[: -len("/state.json")]
    return tail


def test_resolvers_agree_on_a_foreign_workspace() -> None:
    """모듈 저장소와 **다른** branch 의 workspace 에서 셋이 같은 slug 를 쓴다."""
    with _without_branch_env():
        with tempfile.TemporaryDirectory() as td:
            ws = _workspace(td)
            profile = ws / "docs" / "PROJECT_PROFILE.md"

            actual = branch_for_workspace(ws)
            assert actual == PROBE_BRANCH, f"fixture 준비 실패: {actual}"
            assert get_current_branch() != PROBE_BRANCH, (
                "모듈 저장소가 우연히 probe branch 와 같다 — 이 검사는 두 값이 달라야 의미가 있다."
            )

            active = _slug_after_memory(workflow_branch_dir(profile), "active")
            archived = _slug_after_memory(workflow_archived_branch_dir(profile), "archived")
            state = _slug_after_memory(state_path_for_workspace(ws), "active")

            assert active == archived == state == PROBE_BRANCH, (
                f"해석기가 갈라졌다 — branch_dir={active} archived={archived} state={state} "
                f"(workspace 의 실제 branch={PROBE_BRANCH}, 모듈 저장소={get_current_branch()})"
            )


def test_state_and_docs_land_in_the_same_branch_dir() -> None:
    """state.json 과 handoff/backlog 가 **같은 디렉터리**에 있다.

    갈라지면 한쪽만 갱신되고 다른 쪽은 조용히 옛 값을 읽는다.
    """
    with _without_branch_env():
        with tempfile.TemporaryDirectory() as td:
            ws = _workspace(td)
            profile = ws / "docs" / "PROJECT_PROFILE.md"
            # macOS 에서 `Path.resolve()` 가 `/private/var/folders/...` prefix 를
            # 추가한다 (TASK-2026-08-11-main-017 §2챕터 — mktemp 가 `/var/folders/...`
            # 를 반환하고 helper 가 resolve 후 `/private/...` 를 반환하면 raw vs
            # resolve 비교가 fail). 비교 양쪽을 resolve() 로 통일한다.
            assert state_path_for_workspace(ws).parent.resolve() == workflow_branch_dir(profile).resolve(), (
                f"{state_path_for_workspace(ws).parent} != {workflow_branch_dir(profile)}"
            )


def test_non_git_workspace_falls_back_to_module_repo() -> None:
    """git 저장소가 아니면 기존 동작으로 되돌아간다 (temp fixture 호환)."""
    with _without_branch_env():
        with tempfile.TemporaryDirectory() as td:
            ws = _workspace(td, git=False)
            profile = ws / "docs" / "PROJECT_PROFILE.md"
            slug = _slug_after_memory(workflow_branch_dir(profile), "active")
            assert slug == get_current_branch(), (slug, get_current_branch())


def test_explicit_branch_argument_still_wins() -> None:
    """`--branch` 상당의 명시 인자가 있으면 그것이 우선한다."""
    with _without_branch_env():
        with tempfile.TemporaryDirectory() as td:
            ws = _workspace(td)
            profile = ws / "docs" / "PROJECT_PROFILE.md"
            slug = _slug_after_memory(
                workflow_archived_branch_dir(profile, branch="release/x"), "archived"
            )
            assert slug == "release/x", slug


def test_branch_env_override_wins() -> None:
    """`GITHUB_REF_NAME` 등 env 는 workspace 의 git 보다 우선한다 (의도된 동작).

    CI checkout 의 branch 를 그대로 쓰기 위한 장치다. 이 규칙을 **알고 있으라고**
    고정해 둔다 — 모르면 위 검사들이 CI 에서 조용히 무력화된다.
    """
    with tempfile.TemporaryDirectory() as td:
        ws = _workspace(td)
        saved = {k: os.environ.pop(k, None) for k in BRANCH_ENV_KEYS}
        try:
            os.environ["GITHUB_REF_NAME"] = "release/from-env"
            assert branch_for_workspace(ws) == "release/from-env", branch_for_workspace(ws)
        finally:
            os.environ.pop("GITHUB_REF_NAME", None)
            for key, value in saved.items():
                if value is not None:
                    os.environ[key] = value


def main() -> int:
    test_funcs = [
        test_resolvers_agree_on_a_foreign_workspace,
        test_state_and_docs_land_in_the_same_branch_dir,
        test_non_git_workspace_falls_back_to_module_repo,
        test_explicit_branch_argument_still_wins,
        test_branch_env_override_wins,
    ]
    failures: list[tuple[str, str]] = []
    for func in test_funcs:
        try:
            func()
            print(f"  PASS: {func.__name__}")
        except AssertionError as e:
            failures.append((func.__name__, f"AssertionError: {e}"))
            print(f"  FAIL: {func.__name__} — {e}")
        except Exception as e:  # noqa: BLE001
            failures.append((func.__name__, f"{type(e).__name__}: {e}"))
            print(f"  FAIL: {func.__name__} — {type(e).__name__}: {e}")

    total = len(test_funcs)
    print(f"\n{total - len(failures)}/{total} PASS")
    if failures:
        for name, err in failures:
            print(f"  - {name}: {err}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
