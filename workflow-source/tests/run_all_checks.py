#!/usr/bin/env python3
"""v0.7.6+: workflow-source 의 check_*.py smoke test 통합 runner (77 file).

77+ check_*.py 를 한 번에 실행 + 결과 집계. 운영 layer 의 *단일 진입점*.
R-3 단계 분리 (refresh_wiki_memory 와 동일 패턴).

Usage:
    # 전체 77 check 실행
    python3 run_all_checks.py

    # filter (e.g. baselines + wiki 만)
    python3 run_all_checks.py --filter=baselines,wiki

    # JSON 출력 (CI 통합)
    python3 run_all_checks.py --json

    # fail-fast (첫 실패 시 중단)
    python3 run_all_checks.py --fail-fast

    # 특정 dir
    python3 run_all_checks.py --tests-dir=tests

    # 전량 실행 (권장) — temp 를 실디스크에 두고 resource guard 활성
    python3 run_all_checks.py --tmp-dir=/var/tmp/saw-smoke --timeout=120

Resource guard (v1.0.0):
    smoke 전량 실행 중 (1) tmpfs 경유 OOM 과 (2) 디스크 211GB 점유 사고가 실제로 발생했다.
    원인은 개별 check 의 버그가 아니라 *실행 방식* 이었으므로 러너가 직접 방어한다.

    - check 마다 **전용 TMPDIR** 을 주고 종료 후 무조건 삭제 (누수 축적 원천 차단)
    - **프로세스 그룹** 격리 + 종료 시 그룹째 정리 (고아 자식 누적 차단)
    - **디스크 여유 / temp 총량** 상한 초과 시 즉시 중단 (exit 3)
    - TMPDIR 이 tmpfs 면 preflight 경고

Reference:
- tests/check_baselines_compliance.py (16 test) — v0.7.5
- tests/check_refresh_wiki_memory.py (10 test) — v0.7.5
- tools/refresh_wiki_memory.py (v0.7.5, 1차 출처 / 2차 출처 path 명시 패턴)
- workflow_kit/metadata.py (v0.7.6, [tool.workflow-doctor] config loader)
"""

from __future__ import annotations

import argparse
import ast
import datetime
import fnmatch
import functools
import hashlib
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field, asdict
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[1]
TESTS_DIR = SOURCE_ROOT / "tests"

if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from workflow_kit.common.branch_matrix import (  # noqa: E402
    BranchContext, apply_context, context_for, contexts, labels,
)

# --- v1.0.0 resource guard 기본 임계 -----------------------------------------
# 배경: smoke 전량 실행 중 두 종류의 사고가 실제로 발생했다.
#   (1) TMPDIR 이 tmpfs(/tmp) 였을 때 — temp 누수가 *RAM* 을 잠식해 OOM → 세션 kill.
#   (2) TMPDIR 이 실디스크(/var/tmp) 였을 때 — temp 누수가 디스크를 211GB 채움.
# 즉 "temp 를 어디에 두느냐" 는 해법이 아니고, *상한 강제* 와 *정리 보장* 이 해법이다.
# 여유 공간은 *절대값과 비율을 함께* 본다. tmpfs 는 보통 수 GB 라 절대값만 쓰면 정상
# 상태에서도 오탐하고, 대용량 디스크는 비율만 쓰면 수십 GB 누수를 놓친다.
DEFAULT_MIN_DISK_FREE_MB = 1024    # 여유가 1GB 미만이면 무조건 중단
DEFAULT_MIN_DISK_FREE_RATIO = 0.05  # 또는 전체의 5% 미만이면 중단
DEFAULT_MAX_TMP_MB = 2048          # temp 총량이 2GB 초과하면 누수 폭주로 보고 중단

# --- v1.1.7 병렬 실행 (TASK-018) ---------------------------------------------
# 측정: CI job 604s 중 smoke 실행이 576s 였고, 267개 check 의 시간 분포는 극단적이다
# (상위 13개가 50%, 하위 133개 합계 9.8s). 개별 최적화보다 병렬화가 압도적이라
# 8-way 실측에서 345s → 69.8s (4.9배) 였다.
#
# 각 check 는 이미 전용 TMPDIR + 전용 프로세스 그룹으로 격리돼 있어 대체로 병렬
# 안전하다. 유일한 장애물이던 `check_source_without_runtime_layer` (원본 저장소의
# `ai-workflow/` 를 rename 해 숨기던 것) 는 같은 task 에서 사본 검증으로 고쳤다.
MAX_AUTO_JOBS = 8
"""`--jobs auto` 의 상한. 코어가 더 많아도 여기서 멈춘다 — check 는 subprocess 라
I/O 대기가 많지만, 동시 temp 사용량도 함께 늘기 때문이다 (guard 의 2GB 상한)."""

QUIET_MARKER = "REQUIRES_QUIET_REPO"

"""check 가 **저장소 전역 상태** 를 관찰한다고 스스로 선언하는 이름.

이런 check 는 격리로 해결되지 않는다 — 관찰 대상이 저장소 자신이기 때문이다.
`check_no_repo_write` 는 실행 전후의 `git status` 를 비교하므로 같은 순간 누가
무엇이든 건드리면 오탐하고, `check_source_without_runtime_layer` 는 저장소를
통째로 복사하므로 복사 순간의 일시 상태를 그대로 굳힌다. 실측에서 병렬로 돌린
전량 검사가 정확히 이 둘만 추가로 깨뜨렸다.

그래서 이들은 **아무도 저장소를 건드리지 않는 동안**(정숙 구간) 직렬로 돌린다.
소속을 runner 안의 목록으로 두지 않는 이유는 §2.53 과 같다 — 목록은 파일에서
멀어지면 드리프트한다. 선언을 check 파일 안에 두면 파일과 함께 움직인다."""

# --- v1.1.7 전량 검사 배타 락 (TASK-2026-08-11-main-019) ----------------------
# 2026-08-11 실측: 두 에이전트가 같은 워킹 트리에서 전량 검사를 동시에 돌렸다.
# REQUIRES_QUIET_REPO 검사는 살아있는 저장소 전역 상태를 관찰하므로 runner 두 개가
# 서로의 정숙 구간을 침범하면 **그 실행의 PASS 도 FAIL 도 근거로 쓸 수 없다.**
# 그래서 진입에서 워킹 트리 루트 기준 배타 락을 잡고, 이미 잡혀 있으면 보유자
# 정보를 찍고 즉시 실패한다 (조용히 진행 금지 — "모름 ≠ 안전").
#
# 설계 (선례: workflow_kit/url_validity.py `_CacheLock`, ADR-015):
# - `fcntl.flock` advisory lock. 프로세스가 죽으면 커널이 자동 해제하므로
#   stale 락이 다음 실행을 막는 일이 없다 (PID 생존 확인이 따로 필요 없는 이유).
# - 락 파일은 **`.git/` 안** — 워킹 트리에 두면 `check_no_repo_write` 가 오염으로
#   잡는다. git worktree 는 `.git` 이 파일이라 gitdir 을 따라간다.
# - **재진입**: runner 를 부르는 검사(check_parallel_smoke 등)가 낳은 자식 runner 는
#   env 마커로 부모의 락을 물려받는다 (flock 은 fd 단위라 같은 파일을 다시 열면
#   자기 자신도 막는다).
# - 파일은 unlink 하지 않는다 — 삭제/재생성 경쟁이 두 프로세스에 서로 다른 inode
#   의 락을 쥐여 줄 수 있다. 내용(보유자 정보)은 정보용이다.
# - 한계: 이 락은 **runner 동시 실행**만 막는다. 에이전트가 파일을 직접 편집하는
#   충돌은 워크스페이스 분리(worktree)가 정공법이고, 락은 그 위의 안전망이다.
RUNNER_LOCK_ENV = "RUN_ALL_CHECKS_LOCK_HELD"


def _runner_lock_path(repo_root: Path) -> Path:
    gitdir = repo_root / ".git"
    if gitdir.is_dir():
        return gitdir / "run_all_checks.lock"
    if gitdir.is_file():
        # worktree: `.git` 은 "gitdir: <path>" 한 줄짜리 파일이다.
        text = gitdir.read_text(encoding="utf-8").strip()
        if text.startswith("gitdir:"):
            actual = Path(text.split(":", 1)[1].strip())
            if not actual.is_absolute():
                actual = (repo_root / actual).resolve()
            if actual.is_dir():
                return actual / "run_all_checks.lock"
    # git 저장소가 아니면 (사본 검증 등) 루트 경로로 갈린 temp 락을 쓴다.
    digest = hashlib.sha256(str(repo_root).encode("utf-8")).hexdigest()[:16]
    return Path(tempfile.gettempdir()) / f"run_all_checks-{digest}.lock"


class RunnerLock:
    """전량 runner 의 워킹 트리 배타 락. 획득 실패 시 보유자 정보를 돌려준다."""

    def __init__(self, repo_root: Path) -> None:
        self.lock_path = _runner_lock_path(repo_root)
        self._fd: object | None = None
        self._nested = os.environ.get(RUNNER_LOCK_ENV) == str(self.lock_path)

    def acquire(self) -> tuple[bool, str]:
        """(획득/승계 성공?, 실패 시 보유자 설명)."""
        if self._nested:
            return True, "(부모 runner 의 락을 승계)"
        try:
            import fcntl
        except ImportError:  # Windows: advisory no-op (선례와 동일)
            return True, "(fcntl 없음 — 락 없이 진행)"
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        fd = open(self.lock_path, "a+", encoding="utf-8")
        try:
            fcntl.flock(fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            fd.seek(0)
            holder = fd.read().strip() or "(보유자 정보 없음)"
            fd.close()
            return False, holder
        branch = ""
        try:
            proc = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                capture_output=True, text=True, timeout=5,
                cwd=str(self.lock_path.parent),
            )
            branch = proc.stdout.strip()
        except Exception:  # noqa: BLE001 - 보유자 정보는 best effort
            pass
        fd.seek(0)
        fd.truncate()
        fd.write(json.dumps({
            "pid": os.getpid(),
            "started_at": datetime.datetime.now().isoformat(timespec="seconds"),
            "branch": branch,
            "argv": sys.argv[1:],
        }, ensure_ascii=False))
        fd.flush()
        self._fd = fd
        # 자식 runner (runner 를 부르는 검사) 는 이 마커로 락을 승계한다.
        os.environ[RUNNER_LOCK_ENV] = str(self.lock_path)
        return True, ""

    def release(self) -> None:
        if self._fd is None:
            return
        try:
            import fcntl
            fcntl.flock(self._fd.fileno(), fcntl.LOCK_UN)  # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001
            pass
        try:
            self._fd.close()  # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001
            pass
        self._fd = None
        os.environ.pop(RUNNER_LOCK_ENV, None)


WATCHES_MARKER = "WATCHES"
"""check 가 **자기가 관찰하는 저장소 경로** 를 스스로 선언하는 이름 (glob 튜플).

`--changed` 는 이 선언을 보고 *변경과 무관한* check 를 건너뛴다. 선언을 runner
안의 표로 두지 않는 이유는 `REQUIRES_QUIET_REPO` 와 같다 — 목록은 파일에서
멀어지면 드리프트하고, 그 드리프트는 **조용히 안 도는 검사**로 나타난다.

계약 두 가지:

1. **미선언 = 항상 실행.** 선택은 사각지대를 만들지 않는 방향으로만 작동한다.
   선언을 깜빡한 check 는 느려질 뿐 놓치지 않는다.
2. **자기 파일이 바뀌면 무조건 실행.** 선언 자체가 바뀐 경우를 포함한다.

예:
    WATCHES = ("workflow-source/workflow_kit/tools/release_pipeline*.py",
               "workflow-source/workflow_kit/release_status.py")
"""

TIMEOUT_MARKER = "CHECK_TIMEOUT_S"
"""check 가 **자기 timeout 상한(초)** 을 스스로 선언하는 이름.

기본 60s 는 행(hang) 을 잡기 위한 상한인데, 단독 실행 ~30s 인 무거운 check 는
병렬 부하(12코어 jobs=8+)에서 2배까지 늘어져 상한을 넘는다 — 2026-08-11 로컬
전량에서 `check_release_summary_v0_11_15` / `check_release_status_auto_bump_v0_11_16`
이 정확히 그렇게 TIMEOUT flake 났다 (solo 28~31s, 부하 시 52~55s 관측).

선언 값은 CLI `--timeout` 과 **max** 로 합친다 — 선언은 상한을 늘릴 수만 있다.
행 검출은 유지된다 (150s 선언도 무한 행은 잡는다). 목록이 아니라 파일 안 선언인
이유는 QUIET_MARKER 와 같다."""


@dataclass
class CheckResult:
    """개별 check_*.py 실행 결과."""
    name: str
    path: str
    exit_code: int
    duration_sec: float
    passed: int = 0
    failed: int = 0
    last_line: str = ""
    error_excerpt: str = ""
    tmp_peak_mb: int = 0        # 이 check 가 전용 TMPDIR 에 남긴 최대 용량
    killed_children: int = 0    # 종료 후 강제 정리된 잔여 자식 프로세스 유무 (0/1)


@dataclass
class RunSummary:
    """전체 run 집계."""
    total: int = 0
    passed: int = 0
    failed: int = 0
    total_duration_sec: float = 0.0
    total_passed_tests: int = 0
    total_failed_tests: int = 0
    results: list[CheckResult] = field(default_factory=list)
    aborted_reason: str = ""    # resource guard 발동 시 사유 (빈 문자열이면 정상 완주)


@dataclass
class ResourceGuard:
    """smoke 전량 실행의 리소스 폭주를 *구조적으로* 차단하는 가드.

    개별 check 의 버그가 아니라 *실행 방식* 이 사고를 만들었기 때문에, 러너 자신이
    상한을 강제한다. 위반 시 즉시 중단하여 시스템 전체가 죽는 것을 막는다.
    """
    tmp_root: str
    min_disk_free_mb: int = DEFAULT_MIN_DISK_FREE_MB
    max_tmp_mb: int = DEFAULT_MAX_TMP_MB
    min_disk_free_ratio: float = DEFAULT_MIN_DISK_FREE_RATIO
    enabled: bool = True

    def preflight(self) -> str:
        """실행 전 1회 점검. 경고 문자열 (빈 문자열이면 이상 없음)."""
        if not self.enabled:
            return ""
        if _is_tmpfs(Path(self.tmp_root)):
            return (
                f"TMPDIR({self.tmp_root}) 이 tmpfs(RAM) 입니다 — temp 누수가 곧 RAM 고갈/OOM 이 "
                f"됩니다. --tmp-dir 로 실디스크 경로를 지정하는 것을 권장합니다."
            )
        return ""

    def violation(self) -> str:
        """현재 리소스 상태의 위반 사유 (빈 문자열이면 정상)."""
        if not self.enabled:
            return ""
        try:
            usage = shutil.disk_usage(self.tmp_root)
        except OSError:
            return ""
        free_mb = usage.free // (1024 * 1024)
        total_mb = max(usage.total // (1024 * 1024), 1)
        ratio = free_mb / total_mb
        if free_mb < self.min_disk_free_mb or ratio < self.min_disk_free_ratio:
            return (
                f"disk free {free_mb}MB ({ratio:.1%} of {total_mb}MB) — "
                f"하한 {self.min_disk_free_mb}MB / {self.min_disk_free_ratio:.0%} 미달, 폭주 차단을 위해 중단"
            )
        tmp_mb = _dir_size_mb(Path(self.tmp_root))
        if tmp_mb > self.max_tmp_mb:
            return f"temp {tmp_mb}MB > {self.max_tmp_mb}MB — 누수 폭주 차단을 위해 중단"
        return ""


def discover_checks(tests_dir: Path, filter_pattern: str | None = None) -> list[Path]:
    """tests/check_*.py glob. --filter 적용 시 name substring match (comma-separated OR)."""
    all_checks = sorted(tests_dir.glob("check_*.py"))
    if not filter_pattern:
        return all_checks
    needles = [n.strip() for n in filter_pattern.split(",") if n.strip()]
    if not needles:
        return all_checks
    return [
        c for c in all_checks
        if any(n in c.stem for n in needles)
    ]


def changed_paths(repo_root: Path, base: str | None) -> tuple[list[str], str]:
    """변경된 저장소 상대 경로 목록과 **그 목록을 어디서 얻었는지**를 함께 준다.

    출처를 같이 돌려주는 이유: 선택 실행은 "무엇을 안 돌렸는가" 가 결과의 일부라,
    기준을 출력하지 않으면 나중에 그 실행이 무엇을 근거로 좁혀졌는지 알 수 없다.

    - `base` 없음: 워킹 트리 vs HEAD (미추적 파일 포함) — *지금 편집 중인 것*.
    - `base` 지정: `<base>...HEAD` 의 diff + 워킹 트리 변경.

    git 이 없거나 명령이 실패하면 `([], 사유)` 를 준다. 호출자는 그 경우
    **아무것도 건너뛰지 않는다** (모름 ≠ 안전).
    """
    def _git(*argv: str) -> tuple[int, str]:
        try:
            proc = subprocess.run(["git", *argv], cwd=str(repo_root),
                                  capture_output=True, text=True, timeout=30)
        except (OSError, subprocess.SubprocessError) as e:
            return 1, str(e)
        return proc.returncode, proc.stdout

    paths: set[str] = set()
    rc, out = _git("status", "--porcelain", "--untracked-files=all")
    if rc != 0:
        return [], f"git status 실패 — 선택하지 않는다 ({out.strip()[:120]})"
    for line in out.splitlines():
        if not line.strip():
            continue
        entry = line[3:]
        # rename 은 "old -> new" 로 온다. 둘 다 변경으로 센다.
        for part in entry.split(" -> "):
            part = part.strip().strip('"')
            if part:
                paths.add(part)
    source = "워킹 트리 vs HEAD (미추적 포함)"
    if base:
        rc2, out2 = _git("diff", "--name-only", f"{base}...HEAD")
        if rc2 != 0:
            return [], f"git diff {base}...HEAD 실패 — 선택하지 않는다"
        paths.update(ln.strip() for ln in out2.splitlines() if ln.strip())
        source = f"{base}...HEAD + 워킹 트리"
    return sorted(paths), source


def select_by_change(
    checks: list[Path], changed: list[str], repo_root: Path,
) -> tuple[list[Path], list[tuple[Path, str]]]:
    """(실행할 check, [(건너뛴 check, 사유)]) 로 가른다.

    실행 조건은 셋 중 하나라도 참이면 된다:

    1. `WATCHES` **미선언** — 항상 실행 (보수적 기본값)
    2. 자기 파일이 바뀌었다 — 선언이 바뀐 경우를 포함한다
    3. 선언한 glob 중 하나가 변경 경로와 맞는다

    `fnmatch` 는 `*` 가 `/` 도 먹으므로 실제보다 **넓게** 맞는다. 그 방향의 오차는
    검사를 더 돌리게 할 뿐이라 안전한 쪽이다.
    """
    changed_set = set(changed)
    run: list[Path] = []
    skipped: list[tuple[Path, str]] = []
    for check in checks:
        globs = watched_globs(check)
        if not globs:
            run.append(check)
            continue
        try:
            own = check.resolve().relative_to(repo_root.resolve()).as_posix()
        except ValueError:
            own = ""
        if own and own in changed_set:
            run.append(check)
            continue
        if any(fnmatch.fnmatch(c, g) for c in changed for g in globs):
            run.append(check)
            continue
        skipped.append((check, f"WATCHES {list(globs)} 와 변경 경로가 겹치지 않음"))
    return run, skipped


def report_change_selection(
    changed: list[str], source: str, run: list[Path], skipped: list[tuple[Path, str]],
) -> None:
    """무엇을 **안 돌렸는지** 를 반드시 찍는다.

    조용한 축소는 읽는 사람에게 "전부 돌았다" 로 보인다. 건너뛴 것은 개수만이 아니라
    **이름과 사유**까지 전부 낸다 — 목록이 길어지는 쪽이 낫다.
    """
    print(f"=== --changed 선택 실행 (기준: {source}) ===")
    print(f"  변경 경로 {len(changed)}건")
    for c in changed[:40]:
        print(f"    ~ {c}")
    if len(changed) > 40:
        print(f"    ... 외 {len(changed) - 40}건")
    print(f"  실행 {len(run)} / 건너뜀 {len(skipped)}")
    for check, why in skipped:
        print(f"    skip  {check.stem}  — {why}")
    print("  ⚠ 이 실행은 **게이트가 아니다** — push 직전에는 전량 2축을 돌린다.")
    print()


def parse_output(output: str) -> tuple[int, int, str]:
    """check_*.py 의 stdout 에서 (passed, failed, last_line) 추출.

    형식 예:
        All 16 tests passed.
        1/10 tests failed:
        All X tests passed.
    """
    passed = 0
    failed = 0
    last_line = ""
    for line in output.strip().split("\n"):
        line = line.rstrip()
        if not line:
            continue
        last_line = line
        m = re.match(r"^All (\d+) tests passed\.$", line)
        if m:
            passed = int(m.group(1))
            failed = 0
            continue
        m = re.match(r"^(\d+)/(\d+) tests failed:", line)
        if m:
            failed = int(m.group(1))
            # total = int(m.group(2))  # not used; check_* 가 PASS 도 함께 보고
            continue
    return passed, failed, last_line


def _dir_size_mb(path: Path) -> int:
    """dir 의 총 용량 (MB). 접근 불가 항목은 건너뛴다."""
    total = 0
    for root, _dirs, files in os.walk(path, onerror=lambda _e: None):
        for name in files:
            try:
                total += os.lstat(os.path.join(root, name)).st_size
            except OSError:
                continue
    return total // (1024 * 1024)


def _is_tmpfs(path: Path) -> bool:
    """path 가 tmpfs(RAM) 위에 있는지. tmpfs 면 temp 누수가 곧 RAM 고갈이다."""
    try:
        mounts = Path("/proc/mounts").read_text(encoding="utf-8")
    except OSError:
        return False
    best, best_fs = "", ""
    for line in mounts.splitlines():
        parts = line.split()
        if len(parts) < 3:
            continue
        mnt, fstype = parts[1], parts[2]
        if str(path).startswith(mnt) and len(mnt) > len(best):
            best, best_fs = mnt, fstype
    return best_fs == "tmpfs"


def _kill_process_group(proc: subprocess.Popen) -> bool:
    """자식이 만든 *프로세스 그룹 전체* 를 정리하고, 실제로 정리 대상이 있었는지 반환.

    `timeout` 이 부모만 죽이면 Popen 으로 띄운 손자 프로세스(MCP stdio 서버 등)가
    **고아로 잔존**한다. 이것이 수백 개 누적되어 CPU/RAM 을 잠식한 사고의 원인이었다.
    """
    try:
        pgid = os.getpgid(proc.pid)
    except (ProcessLookupError, PermissionError):
        return False
    killed = False
    for sig in (signal.SIGTERM, signal.SIGKILL):
        try:
            os.killpg(pgid, sig)
            killed = True
        except (ProcessLookupError, PermissionError):
            break
        time.sleep(0.1)
    return killed


def run_one(
    check_path: Path,
    timeout: int = 60,
    *,
    guard: "ResourceGuard | None" = None,
    branch_context: "BranchContext | None" = None,
) -> CheckResult:
    """단일 check_*.py 를 *격리* 실행 + CheckResult 반환.

    격리 3종 (v1.0.0):
    1. **전용 TMPDIR**: check 마다 별도 temp dir 을 주고 종료 후 무조건 삭제한다.
       테스트가 스스로 정리하지 않아도 누수가 축적되지 않는다.
    2. **프로세스 그룹**: `start_new_session=True` 로 새 그룹을 만들고 종료 시
       그룹째 정리한다 → 고아 자식 누적 차단.
    3. **timeout**: 만료 시 그룹 전체에 SIGTERM → SIGKILL.
    """
    start = time.time()
    try:
        rel = str(check_path.relative_to(SOURCE_ROOT))
    except ValueError:
        # `--tests-dir` 가 저장소 밖(fixture dir 등)을 가리키면 상대화가 불가능하다
        # — 표시용 경로일 뿐이므로 절대 경로로 보고한다.
        rel = str(check_path)
    tmp_root = Path(guard.tmp_root) if guard else Path(tempfile.gettempdir())
    tmp_root.mkdir(parents=True, exist_ok=True)
    tmp_dir = Path(tempfile.mkdtemp(prefix=f"{check_path.stem}-", dir=str(tmp_root)))

    env = os.environ.copy()
    env["TMPDIR"] = str(tmp_dir)
    env.setdefault("PYTHONPATH", str(SOURCE_ROOT))
    # 브랜치 컨텍스트 (v1.1.7). 요청한 컨텍스트가 호출자 환경에 밀리면 "그 축을
    # 쟀다" 는 보고가 거짓이 되므로, native 는 상속된 오버라이드를 지우기까지 한다
    # (`apply_context` 주석 참조).
    if branch_context is not None:
        env = apply_context(env, branch_context)

    proc = subprocess.Popen(
        [sys.executable, str(check_path)],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        env=env, start_new_session=True,
    )
    timed_out = False
    try:
        out, err = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        _kill_process_group(proc)
        try:
            out, err = proc.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            out, err = "", ""
    duration = time.time() - start

    tmp_peak = _dir_size_mb(tmp_dir)
    killed = _kill_process_group(proc)          # 잔여 손자 정리
    shutil.rmtree(tmp_dir, ignore_errors=True)  # temp 누수 원천 차단

    if timed_out:
        return CheckResult(
            name=check_path.stem, path=rel, exit_code=-1,
            duration_sec=round(duration, 2), passed=0, failed=0,
            last_line="TIMEOUT", error_excerpt=f"timeout after {timeout}s",
            tmp_peak_mb=tmp_peak, killed_children=int(killed),
        )
    output = (out or "") + (err or "")
    passed, failed, last_line = parse_output(output)
    return CheckResult(
        name=check_path.stem, path=rel,
        exit_code=proc.returncode,
        duration_sec=round(duration, 2),
        passed=passed, failed=failed, last_line=last_line,
        error_excerpt=_error_excerpt(output) if proc.returncode != 0 else "",
        tmp_peak_mb=tmp_peak, killed_children=int(killed),
    )


def _error_excerpt(output: str, *, limit: int = 1200) -> str:
    """실패 **사유**가 적힌 줄을 골라 낸다 (v1.0.2).

    이전에는 `"".join(output.split("\\n")[-3:])` 로 *마지막 3줄* 을 잘랐다. 그런데
    대부분의 check 는 끝에 요약 줄(`=== Result: 0/1 PASS ===`)과 빈 줄을 붙이고,
    문자열이 개행으로 끝나면 split 결과의 마지막 원소는 빈 문자열이다. 그래서 정작
    사유가 적힌 줄은 **뒤에서 4번째**가 되어 항상 잘려 나갔다.

    결과적으로 CI 아티팩트에는 "=== Result: 0/1 PASS ===" 만 남아, 무엇이 왜 실패했는지
    알 수 없었다. 실제로 이 결함 때문에 원인 파악에 push 왕복을 한 번 더 썼다.

    고정 위치 대신 **실패 표지가 있는 줄**을 고르고, 없으면 마지막 비어 있지 않은
    줄들로 떨어진다.

    상한은 400 → **1200** (2026-08-20). 400 자는 mypy INTERNAL ERROR 의 보일러플레이트
    (안내 문구 + 문서 URL)를 채우고 정작 traceback 직전에서 끊겼다 — 4번째 사건까지
    원인이 안 좁혀진 이유의 절반이 이 절단이었다 (TASK-2026-08-13-main-004 관찰 3차).
    """
    lines = [ln.rstrip() for ln in output.splitlines() if ln.strip()]
    if not lines:
        return ""
    markers = ("FAIL", "✗", "Error", "error:", "Traceback", "assert", "Exception", "AssertionError")
    hits = [ln for ln in lines if any(m in ln for m in markers)]
    chosen = hits[-4:] if hits else lines[-4:]
    return " | ".join(chosen)[:limit]


def aggregate(results: list[CheckResult], duration: float) -> RunSummary:
    """CheckResult list → RunSummary 집계."""
    summary = RunSummary(
        total=len(results),
        passed=sum(1 for r in results if r.exit_code == 0),
        failed=sum(1 for r in results if r.exit_code != 0),
        total_duration_sec=round(duration, 2),
        total_passed_tests=sum(r.passed for r in results),
        total_failed_tests=sum(r.failed for r in results),
        results=results,
    )
    return summary


def print_human(summary: RunSummary) -> None:
    """사람이 읽기 좋은 출력."""
    print(f"=== workflow-source check runner (v0.7.6) ===\n")
    print(f"  total:   {summary.total}")
    print(f"  passed:  {summary.passed} (exit 0)")
    print(f"  failed:  {summary.failed} (exit != 0)")
    print(f"  duration: {summary.total_duration_sec}s")
    print(f"  test pass: {summary.total_passed_tests}")
    print(f"  test fail: {summary.total_failed_tests}")
    leaky = [r for r in summary.results if r.tmp_peak_mb > 0 or r.killed_children]
    if leaky:
        print(f"  resource: {len(leaky)} check 가 temp/자식 잔여를 남겨 러너가 회수함")
    if summary.aborted_reason:
        print(f"  ABORTED: {summary.aborted_reason}")
    print()
    print(f"  --- per-check ---")
    for r in summary.results:
        status = "PASS" if r.exit_code == 0 else f"FAIL({r.exit_code})"
        line_excerpt = r.last_line[:60] if r.last_line else ""
        print(f"  [{status}] {r.name} ({r.duration_sec}s) {line_excerpt}")
    if summary.failed > 0:
        print(f"\n  --- failures ---")
        for r in summary.results:
            if r.exit_code != 0:
                print(f"  ✗ {r.name}: {r.error_excerpt}")


@functools.lru_cache(maxsize=None)
def _scan_markers(check_path_str: str) -> tuple[bool, int, tuple[str, ...]]:
    """(REQUIRES_QUIET_REPO, CHECK_TIMEOUT_S, WATCHES) 를 한 번의 AST parse 로 읽는다.

    import 하지 않는다 — 선언은 파일의 최상위 상수라야 한다. parse 못 하는
    파일은 (False, 0, ()): 어차피 실행도 못 하며, 병렬 구간에서 실패하게 둔다.
    `WATCHES` 가 빈 튜플이면 **미선언과 같게** 다뤄진다 (= 항상 실행).
    """
    quiet = False
    timeout_s = 0
    watches: tuple[str, ...] = ()
    try:
        with warnings.catch_warnings():
            # 대상 파일의 SyntaxWarning(잘못된 escape 등)이 runner 출력에 새지 않게
            # — baselines 의 신호 계수와 같은 처리다.
            warnings.simplefilter("ignore", SyntaxWarning)
            tree = ast.parse(Path(check_path_str).read_text(encoding="utf-8"))
    except (SyntaxError, OSError):
        return False, 0, ()
    for node in tree.body:
        targets = (node.targets if isinstance(node, ast.Assign)
                   else [node.target] if isinstance(node, ast.AnnAssign) else [])
        for target in targets:
            if not isinstance(target, ast.Name):
                continue
            value = node.value
            if target.id == WATCHES_MARKER and isinstance(value, (ast.Tuple, ast.List)):
                globs = [e.value for e in value.elts
                         if isinstance(e, ast.Constant) and isinstance(e.value, str)]
                if len(globs) == len(value.elts):
                    watches = tuple(globs)
                # 원소 하나라도 리터럴 문자열이 아니면 **선언 없음으로 본다** —
                # 반쯤 읽은 선언으로 검사를 건너뛰면 그게 곧 사각지대다.
                continue
            if not isinstance(value, ast.Constant):
                continue
            if target.id == QUIET_MARKER and value.value is True:
                quiet = True
            elif (target.id == TIMEOUT_MARKER
                  and isinstance(value.value, int) and value.value > 0):
                timeout_s = value.value
    return quiet, timeout_s, watches


def requires_quiet_repo(check_path: Path) -> bool:
    """check 가 `REQUIRES_QUIET_REPO = True` 를 선언했는가."""
    return _scan_markers(str(check_path))[0]


def effective_timeout(check_path: Path, cli_timeout: int) -> int:
    """CLI `--timeout` 과 파일 안 `CHECK_TIMEOUT_S` 선언의 max — 선언은 늘릴 수만 있다."""
    return max(cli_timeout, _scan_markers(str(check_path))[1])


def watched_globs(check_path: Path) -> tuple[str, ...]:
    """check 가 선언한 관찰 경로 glob. 빈 튜플이면 미선언 = 항상 실행."""
    return _scan_markers(str(check_path))[2]


def partition_checks(checks: list[Path]) -> tuple[list[Path], list[Path]]:
    """(병렬 가능, 정숙 구간 필요) 로 가른다. 순서는 각각 원래 순서를 지킨다."""
    parallel = [p for p in checks if not requires_quiet_repo(p)]
    quiet = [p for p in checks if requires_quiet_repo(p)]
    return parallel, quiet


def _resolve_jobs(raw: str) -> int:
    """`--jobs` 값 해석. `auto` = min(코어, MAX_AUTO_JOBS)."""
    if raw == "auto":
        return max(1, min(os.cpu_count() or 4, MAX_AUTO_JOBS))
    try:
        n = int(raw)
    except ValueError:
        raise ValueError(f"--jobs 는 정수 또는 'auto': {raw!r}") from None
    if n < 1:
        raise ValueError(f"--jobs 는 1 이상: {n}")
    return n


def run_pass(
    checks: list[Path],
    args: argparse.Namespace,
    guard: "ResourceGuard",
    branch_context: "BranchContext | None",
    jobs: int = 1,
) -> RunSummary:
    """check 전량을 **한 컨텍스트로** 한 바퀴 돌린다.

    `jobs == 1` 은 **기존 순차 경로 그대로** 다. 재현이 필요할 때 `--jobs 1` 이 옛
    동작과 한 치도 다르지 않아야 하므로, 병렬 경로를 1-worker 로 돌려 대신하지 않는다.
    """
    start = time.time()
    results: list[CheckResult] = []
    aborted = ""

    # 정숙 구간이 필요한 check 는 병렬 구간에서 빼둔다 (jobs == 1 이면 가를 이유가 없다).
    quiet: list[Path] = []
    if jobs > 1:
        checks, quiet = partition_checks(checks)

    if jobs == 1:
        for check_path in checks:
            aborted = guard.violation()
            if aborted:
                break
            result = run_one(check_path, timeout=effective_timeout(check_path, args.timeout),
                             guard=guard, branch_context=branch_context)
            results.append(result)
            if args.fail_fast and result.exit_code != 0:
                break
    else:
        done: dict[Path, CheckResult] = {}
        with ThreadPoolExecutor(max_workers=jobs) as pool:
            futures = {
                pool.submit(run_one, path, timeout=effective_timeout(path, args.timeout),
                            guard=guard, branch_context=branch_context): path
                for path in checks
            }
            for fut in as_completed(futures):
                done[futures[fut]] = fut.result()
                aborted = guard.violation()
                if aborted or (args.fail_fast
                               and done[futures[fut]].exit_code != 0):
                    # 남은 작업을 취소한다. 이미 실행 중인 것은 끝나므로 결과가
                    # 조금 더 모일 수 있다 — 그건 버리지 않고 그대로 보고한다.
                    for pending in futures:
                        pending.cancel()
                    break
        # 완료 순서가 아니라 **discover 순서** 로 정렬한다. 출력이 실행 타이밍에
        # 따라 흔들리면 두 실행을 나란히 비교할 수 없다.
        results = [done[path] for path in checks if path in done]

    # 정숙 구간 — 병렬 구간이 **완전히 끝난 뒤** 직렬로. 이들은 저장소 전역을
    # 관찰하므로 옆에서 아무것도 돌지 않아야 정확하다.
    if quiet and not aborted:
        for check_path in quiet:
            aborted = guard.violation()
            if aborted:
                break
            result = run_one(check_path, timeout=effective_timeout(check_path, args.timeout),
                             guard=guard, branch_context=branch_context)
            results.append(result)
            if args.fail_fast and result.exit_code != 0:
                break

    summary = aggregate(results, time.time() - start)
    summary.aborted_reason = aborted
    return summary


def main() -> int:
    p = argparse.ArgumentParser(
        description="workflow-source 의 check_*.py 통합 runner (v0.7.6+)",
    )
    p.add_argument("--tests-dir", default=str(TESTS_DIR),
                   help="check_*.py glob dir (default: tests/)")
    p.add_argument("--filter", default=None,
                   help="comma-separated name substring (e.g. baselines,wiki)")
    p.add_argument("--fail-fast", action="store_true",
                   help="첫 실패 시 중단")
    p.add_argument("--timeout", type=int, default=60,
                   help="per-check timeout (default: 60s)")
    p.add_argument("--json", action="store_true",
                   help="JSON 출력 (CI 통합)")
    p.add_argument("--tmp-dir", default=None, dest="tmp_dir",
                   help="check 별 전용 temp 의 상위 dir. tmpfs(RAM) 회피용 실디스크 경로 권장 "
                        "(default: 시스템 temp)")
    p.add_argument("--min-disk-free-mb", type=int, default=DEFAULT_MIN_DISK_FREE_MB,
                   dest="min_disk_free_mb",
                   help=f"디스크 여유 절대 하한 (default: {DEFAULT_MIN_DISK_FREE_MB}MB). 비율 하한과 OR 조건")
    p.add_argument("--max-tmp-mb", type=int, default=DEFAULT_MAX_TMP_MB, dest="max_tmp_mb",
                   help=f"temp 총량 상한 (default: {DEFAULT_MAX_TMP_MB}MB). 초과하면 중단")
    p.add_argument("--no-guard", action="store_true", dest="no_guard",
                   help="resource guard 비활성 (권장하지 않음)")
    p.add_argument("--jobs", "-j", default="auto", dest="jobs", metavar="N",
                   help=f"동시 실행 수 (default: auto = min(코어, {MAX_AUTO_JOBS})). "
                        "`1` 은 순차 — 재현이 필요할 때 쓴다")
    p.add_argument("--branch-context", default=None, dest="branch_context",
                   metavar="LABEL",
                   help="브랜치 컨텍스트로 돌린다 (정본: workflow_kit/common/branch_matrix.py). "
                        f"선언: {', '.join(labels())}, all. "
                        "미지정이면 호출자 환경 그대로 (기존 동작). "
                        "push 전 CI 재현은 --branch-context=all")
    p.add_argument("--changed", action="store_true", dest="changed",
                   help=("변경과 무관한 check 를 건너뛴다 (WATCHES 선언 기준). "
                         "미선언 check 는 항상 실행하고, 건너뛴 것은 전부 출력한다. "
                         "**게이트가 아니다** — push 직전에는 전량 2축을 돌린다."))
    p.add_argument("--changed-base", default=None, dest="changed_base", metavar="REF",
                   help="--changed 의 비교 기준 (기본: 워킹 트리 vs HEAD). 예: origin/main")
    p.add_argument("--no-lock", action="store_true", dest="no_lock",
                   help="워킹 트리 배타 락을 잡지 않는다 (권장하지 않음 — 동시 실행된 "
                        "전량 결과는 PASS 도 FAIL 도 근거가 못 된다)")
    args = p.parse_args()

    # v1.1.7 (TASK-2026-08-11-main-019): 전량 검사 배타 락. 다른 runner 가 이미
    # 이 워킹 트리에서 돌고 있으면 즉시 실패한다 — 정숙 구간을 서로 침범한 실행의
    # 결과는 근거로 쓸 수 없기 때문이다.
    lock = RunnerLock(SOURCE_ROOT.parent)
    if args.no_lock:
        print("[warn] --no-lock: 배타 락 없이 진행한다. 다른 runner 와 동시 실행이면 "
              "이 실행의 결과는 근거로 쓸 수 없다.", file=sys.stderr)
    else:
        acquired, holder = lock.acquire()
        if not acquired:
            print("[error] 다른 전량 runner 가 이 워킹 트리의 락을 쥐고 있다 — "
                  f"동시 실행은 정숙 구간을 침범한다 ({lock.lock_path}).\n"
                  f"[error] 보유자: {holder}", file=sys.stderr)
            return 2
        # 명시적 release 는 두지 않는다 — flock 은 프로세스 종료 시 커널이 해제하고,
        # runner 는 main 반환 즉시 종료한다. 중간 예외/타임아웃/kill 모두 안전하다.

    try:
        jobs = _resolve_jobs(args.jobs)
    except ValueError as e:
        print(f"[error] {e}", file=sys.stderr)
        return 2

    tests_dir = Path(args.tests_dir)
    if not tests_dir.exists():
        print(f"[error] tests dir 부재: {tests_dir}", file=sys.stderr)
        return 2

    checks = discover_checks(tests_dir, args.filter)
    if not checks:
        print(f"[error] check_*.py 0 file 매치: {tests_dir} (filter={args.filter})",
              file=sys.stderr)
        return 2

    if args.changed:
        repo_root = SOURCE_ROOT.parent
        changed, source = changed_paths(repo_root, args.changed_base)
        if not changed:
            # 변경이 0건이면 **선택할 근거가 없다.** 여기서 전량으로 되돌아가면
            # `--changed` 가 조용히 게이트인 척하고, 0개를 돌리고 "통과" 라고 하면
            # 더 나쁘다. 그래서 아무것도 안 돌리되 그 사실을 크게 찍고 끝낸다.
            print(f"=== --changed: 변경 0건 ({source}) ===")
            print("  실행할 check 가 없다. 이 결과는 **통과가 아니라 '잴 것이 없음'** 이다.",
                  file=sys.stderr)
            return 0
        checks, skipped = select_by_change(checks, changed, repo_root)
        if not args.json:
            report_change_selection(changed, source, checks, skipped)
        if not checks:
            print("[error] --changed 가 모든 check 를 걸렀다 — 선언이 과하게 좁다.",
                  file=sys.stderr)
            return 2

    guard = ResourceGuard(
        tmp_root=args.tmp_dir or tempfile.gettempdir(),
        min_disk_free_mb=args.min_disk_free_mb,
        max_tmp_mb=args.max_tmp_mb,
        enabled=not args.no_guard,
    )
    warning = guard.preflight()
    if warning and not args.json:
        print(f"[warn] {warning}\n", file=sys.stderr)

    # 브랜치 컨텍스트 해석 (v1.1.7). 미지정 = 호출자 환경 그대로 (기존 동작).
    selected: list[BranchContext | None]
    if args.branch_context is None:
        selected = [None]
    elif args.branch_context == "all":
        selected = list(contexts())
    else:
        ctx = context_for(args.branch_context)
        if ctx is None:
            print(f"[error] 알 수 없는 브랜치 컨텍스트: {args.branch_context!r} "
                  f"(선언: {', '.join(labels())}, all)", file=sys.stderr)
            return 2
        selected = [ctx]

    passes: list[tuple[str, RunSummary]] = []
    for ctx in selected:
        label = ctx.label if ctx else "(환경 그대로)"
        if len(selected) > 1 and not args.json:
            branch = ctx.workflow_branch if ctx and ctx.workflow_branch else "덮지 않음"
            print(f"\n=== 브랜치 컨텍스트: {label} ({branch}) ===\n")
        summary = run_pass(checks, args, guard, ctx, jobs=jobs)
        passes.append((label, summary))
        if summary.aborted_reason and not args.json:
            print(f"\n[abort] resource guard: {summary.aborted_reason}", file=sys.stderr)
        # guard 가 발동했으면 남은 컨텍스트를 더 돌리지 않는다 — 자원이 이미 한계다.
        if summary.aborted_reason:
            break

    if args.json:
        if len(selected) > 1:
            # 다중 컨텍스트는 새 형태. 단일은 아래에서 기존 형태를 유지한다 —
            # CI 의 요약 스크립트가 `data["total"]` / `data["results"]` 를 직접 읽는다.
            print(json.dumps(
                {"contexts": [{"label": label, "summary": asdict(s)} for label, s in passes]},
                ensure_ascii=False, indent=2,
            ))
        else:
            print(json.dumps(asdict(passes[0][1]), ensure_ascii=False, indent=2))
    else:
        for label, summary in passes:
            if len(passes) > 1:
                print(f"\n----- {label} -----")
            print_human(summary)

    if any(s.aborted_reason for _, s in passes):
        return 3    # resource guard 발동 — 완주하지 않았으므로 PASS 로 오독되면 안 된다
    return 0 if all(s.failed == 0 for _, s in passes) else 1


if __name__ == "__main__":
    sys.exit(main())
