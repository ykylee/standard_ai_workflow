"""저장소 **사본** 에서 도구를 돌리기 위한 공용 헬퍼 (TASK-2026-08-10-main-019).

파일명이 `check_` 로 시작하지 않으므로 runner 가 검사로 줍지 않는다 (헬퍼다).

## 왜 필요한가

여러 검사가 `release_pipeline` 같은 도구를 **원본 저장소에 `--apply` 로** 돌린 뒤
되돌려 왔다. 되돌리므로 `check_no_repo_write` 의 전후 비교는 통과하지만, 그 **사이**
저장소에는 잘못된 값이 들어 있다:

- `pyproject.toml` 의 version 이 `99.99.99` 로 바뀐 순간이 있다
- `README.md` / `workflow_kit/__init__.py` 도 함께 흔들린다
- 실패해서 죽으면 (SIGKILL 포함) **되돌아오지 않는다**

CLAUDE.md 는 "여러 에이전트가 함께 일할 수 있다" 를 전제한다. 그 순간 다른 에이전트가
버전을 읽으면 99.99.99 를 본다. 병렬 실행에서 다른 check 가 깨진 것은 증상일 뿐이고,
협업 중이면 그대로 실사고다.

## 쓰는 법

    from _repo_sandbox import repo_sandbox

    with repo_sandbox(REPO_ROOT) as sandbox:
        subprocess.run([sys.executable, str(sandbox / "workflow-source" / "tools" /
                        "release_pipeline.py"), "version-bump", "--apply"], cwd=sandbox)
        # 사본의 pyproject 를 검증한다. 원본은 내내 그대로다.

사본은 `TMPDIR` 아래에 잡히므로 runner 의 전용 temp 에 들어가고 종료 시 회수된다.
"""

from __future__ import annotations

import shutil
import tempfile
from contextlib import contextmanager
from collections.abc import Iterator
from pathlib import Path

_BASE_IGNORE = (
    "__pycache__", "*.pyc", ".venv*", ".mypy_cache", ".pytest_cache",
    "node_modules", "dist", "build", "*.egg-info",
)
"""검증에 쓰이지 않으면서 복사만 비싸지는 것들."""


def _copy_ignore_vanished(src: str, dst: str) -> None:
    """스캔 시점엔 있었지만 복사 시점에 사라진 파일은 건너뛴다.

    병렬 실행 중 다른 check/도구가 만든 임시 파일은 복사 도중 소멸할 수 있다
    (실사례: PERF 벤치마크의 transient log 와 race → shutil.Error). 스냅샷
    복사에서 "지금은 없는 파일" 은 결함이 아니라 정상 상태다.
    """
    try:
        shutil.copy2(src, dst)
    except FileNotFoundError:
        pass


def _vanished_only(exc: shutil.Error) -> bool:
    """copytree 집계 오류가 전부 '파일 소멸(ENOENT)' 인지 판정."""
    errors = exc.args[0] if exc.args else []
    return bool(errors) and all("[Errno 2]" in str(err) for err in errors)


@contextmanager
def repo_sandbox(repo_root: Path, *, include_git: bool = False) -> Iterator[Path]:
    """`repo_root` 의 사본을 만들어 그 경로를 준다. 원본은 **읽기만** 한다.

    Args:
        repo_root: 복사할 저장소 루트.
        include_git: `.git` 도 복사할지. 도구가 실제 히스토리(`HEAD~3..HEAD` 등)나
            브랜치 이름을 요구할 때만 True — 기본은 제외한다 (23MB, 0.3s 차이).

    비용 실측: `.git` 제외 0.24s / 18MB, 포함 0.52s / 41MB.
    """
    patterns = list(_BASE_IGNORE)
    if not include_git:
        patterns.append(".git")
    with tempfile.TemporaryDirectory(prefix="repo-sandbox-") as tmp:
        sandbox = Path(tmp) / "repo"
        try:
            shutil.copytree(repo_root, sandbox,
                            ignore=shutil.ignore_patterns(*patterns), symlinks=True,
                            copy_function=_copy_ignore_vanished)
        except shutil.Error as exc:
            # copy_function 이 파일 본문 소멸은 삼키지만, 디렉터리 stat/목록 단계의
            # 소멸은 여기로 온다. 소멸 이외의 오류가 하나라도 섞였으면 그대로 던진다
            # — 조용한 쪽이 틀린 쪽이다.
            if not _vanished_only(exc):
                raise
        yield sandbox
