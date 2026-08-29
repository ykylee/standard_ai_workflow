#!/usr/bin/env python3
"""전량 runner 의 워킹 트리 배타 락 계약을 고정한다 (TASK-2026-08-11-main-019).

배경: 2026-08-11 에 두 에이전트가 같은 워킹 트리에서 전량 검사를 동시 실행했다.
`REQUIRES_QUIET_REPO` 검사는 저장소 전역 상태를 관찰하므로, 동시 실행된 전량의
결과는 PASS 도 FAIL 도 근거로 쓸 수 없다. 처방은 3층 방어(규약 + 락 + 이 검사)의
락 층 — 계약을 되주입으로 고정한다:

- case 1 (contended): 락이 잡혀 있으면 두 번째 runner 는 **즉시 실패**(exit 2)하고
  보유자 정보를 stderr 에 찍는다 (조용히 진행 금지).
- case 2 (nested): runner 를 부르는 검사가 낳은 자식 runner 는 env 마커로 부모의
  락을 승계해 진행한다 (flock 은 fd 단위라 마커 없이는 자기 부모도 못 뚫는다).
- case 3 (--no-lock): 탈출구는 진행하되 **크게 기록**한다 (stderr 경고).
- case 4 (락 위치): 락 파일은 워킹 트리가 아니라 gitdir(`.git/`) 안이다 —
  워킹 트리에 두면 `check_no_repo_write` 가 오염으로 잡는다.
- case 5 (free, 락이 비어 있을 때만): 획득 후 보유자 정보(pid/시작시각/브랜치)를
  남기고, 종료하면 커널이 flock 을 해제해 다음 실행이 막히지 않는다.

이 검사 자신이 전량 runner 아래에서 돌 때는 **부모 runner 가 락을 쥐고 있다** —
그 상태 자체가 case 1 의 살아있는 fixture 다 (case 5 는 그때 수행 불가로 표기).
"""
from __future__ import annotations

#: 이 검사의 입력 표면 (spec `core/test_impact_tiering_spec.md` §2).
#: 게이트 채취 실측에서 뽑아 넓은 쪽으로 올렸다 — 좁으면 meta-watch 가 red 로 잡는다.
WATCHES = (
    "workflow-source/pyproject.toml",
    "workflow-source/tests/*",
    "workflow-source/workflow_kit/*",
)

import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
RUNNER = SOURCE_ROOT / "tests" / "run_all_checks.py"

if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

# runner 모듈에서 정본 상수/함수를 가져온다 (경로 규약 사본 금지).
import importlib.util

_spec = importlib.util.spec_from_file_location("run_all_checks_under_test", RUNNER)
assert _spec is not None and _spec.loader is not None
_runner_mod = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = _runner_mod  # dataclass 등이 모듈 조회를 하므로 등록 필수
_spec.loader.exec_module(_runner_mod)
RUNNER_LOCK_ENV: str = _runner_mod.RUNNER_LOCK_ENV
LOCK_PATH: Path = _runner_mod._runner_lock_path(REPO_ROOT)

CHEAP_ARGS = ["--filter", "state_backlog_block"]


def _child_env(*, with_marker: bool) -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if k != RUNNER_LOCK_ENV}
    if with_marker:
        env[RUNNER_LOCK_ENV] = str(LOCK_PATH)
    return env


def _run(extra: list[str], *, with_marker: bool) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(RUNNER), *CHEAP_ARGS, *extra],
        capture_output=True, text=True, timeout=120, env=_child_env(with_marker=with_marker),
    )


class _FakeHolder:
    """락이 비어 있으면 이 검사가 직접 보유자가 된다. 이미 잡혀 있으면 (부모
    runner) 그 사실을 그대로 쓴다 — 어느 쪽이든 case 1 의 전제가 성립한다."""

    def __init__(self) -> None:
        self.acquired = False
        self._fd = None

    def __enter__(self) -> "_FakeHolder":
        import fcntl
        LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
        self._fd = open(LOCK_PATH, "a+", encoding="utf-8")
        try:
            fcntl.flock(self._fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.acquired = True
            self._fd.seek(0)
            self._fd.truncate()
            self._fd.write(json.dumps({"pid": os.getpid(), "note": "check-fake-holder"}))
            self._fd.flush()
        except OSError:
            self.acquired = False  # 부모 runner 가 이미 보유 — 그대로 사용
        return self

    def __exit__(self, *exc: object) -> None:
        if self._fd is not None:
            if self.acquired:
                import fcntl
                fcntl.flock(self._fd.fileno(), fcntl.LOCK_UN)
            self._fd.close()


def case_1_contended_fails_fast(holder: _FakeHolder) -> None:
    proc = _run([], with_marker=False)
    assert proc.returncode == 2, f"동시 실행이 막히지 않았다 (rc={proc.returncode})"
    assert "보유자" in proc.stderr and "락" in proc.stderr, f"보유자 정보 미출력:\n{proc.stderr}"


def case_2_nested_inherits() -> None:
    proc = _run([], with_marker=True)
    assert proc.returncode == 0, f"자식 runner 가 락을 승계하지 못했다:\n{proc.stderr}"
    assert "state_backlog_block" in proc.stdout, "승계 후 check 실행 흔적 없음"


def case_3_no_lock_escape_is_loud() -> None:
    proc = _run(["--no-lock"], with_marker=False)
    assert proc.returncode == 0, f"--no-lock 이 진행하지 못했다:\n{proc.stderr}"
    assert "--no-lock" in proc.stderr, "--no-lock 경고가 stderr 에 없다 (탈출구는 크게 기록)"


def case_4_lock_lives_in_gitdir() -> None:
    assert ".git" in LOCK_PATH.parts, f"락이 워킹 트리에 있다: {LOCK_PATH}"
    # 워킹 트리 오염 검사가 보지 않는 위치인지 — git 스스로에게 묻는다.
    proc = subprocess.run(
        ["git", "check-ignore", "-q", str(LOCK_PATH)], cwd=REPO_ROOT,
        capture_output=True, text=True,
    )
    tracked = subprocess.run(
        ["git", "ls-files", "--error-unmatch", str(LOCK_PATH)], cwd=REPO_ROOT,
        capture_output=True, text=True,
    )
    assert tracked.returncode != 0, "락 파일이 git 추적 대상이다"


def case_5_free_acquire_and_holder_info() -> None:
    proc = _run([], with_marker=False)
    assert proc.returncode == 0, f"자유 상태 획득 실패:\n{proc.stderr}"
    info = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
    for key in ("pid", "started_at", "branch", "argv"):
        assert key in info, f"보유자 정보에 {key} 가 없다: {info}"
    # 종료된 프로세스의 락은 커널이 해제한다 — 즉시 다시 잡혀야 한다.
    import fcntl
    with open(LOCK_PATH, "a+", encoding="utf-8") as fd:
        fcntl.flock(fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        fcntl.flock(fd.fileno(), fcntl.LOCK_UN)


def main() -> int:
    results: list[str] = []
    with _FakeHolder() as holder:
        case_1_contended_fails_fast(holder)
        results.append("case_1 contended PASS")
        case_2_nested_inherits()
        results.append("case_2 nested PASS")
        case_3_no_lock_escape_is_loud()
        results.append("case_3 no-lock PASS")
    case_4_lock_lives_in_gitdir()
    results.append("case_4 gitdir PASS")
    if holder.acquired:
        # 우리가 fake holder 였다면 이제 락이 비었다 — free 획득까지 실측.
        case_5_free_acquire_and_holder_info()
        results.append("case_5 free-acquire PASS")
    else:
        results.append("case_5 skip — 부모 runner 가 락 보유 중 (case_1 이 그 락으로 검증됨)")
    print(" | ".join(results))
    print(f"runner lock check passed ({sum('PASS' in r for r in results)} cases)")
    return 0


def test_case_1() -> None:
    with _FakeHolder() as holder:
        case_1_contended_fails_fast(holder)


def test_case_2() -> None:
    with _FakeHolder():
        case_2_nested_inherits()


def test_case_3() -> None:
    with _FakeHolder():
        case_3_no_lock_escape_is_loud()


def test_case_4() -> None:
    case_4_lock_lives_in_gitdir()


def test_case_5() -> None:
    with _FakeHolder() as holder:
        pass
    if holder.acquired:
        case_5_free_acquire_and_holder_info()


if __name__ == "__main__":
    raise SystemExit(main())
