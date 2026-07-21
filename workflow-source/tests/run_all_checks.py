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
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[1]
TESTS_DIR = SOURCE_ROOT / "tests"

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
    rel = str(check_path.relative_to(SOURCE_ROOT))
    tmp_root = Path(guard.tmp_root) if guard else Path(tempfile.gettempdir())
    tmp_root.mkdir(parents=True, exist_ok=True)
    tmp_dir = Path(tempfile.mkdtemp(prefix=f"{check_path.stem}-", dir=str(tmp_root)))

    env = os.environ.copy()
    env["TMPDIR"] = str(tmp_dir)
    env.setdefault("PYTHONPATH", str(SOURCE_ROOT))

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
        error_excerpt="".join(output.split("\n")[-3:])[:200] if proc.returncode != 0 else "",
        tmp_peak_mb=tmp_peak, killed_children=int(killed),
    )


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
    args = p.parse_args()

    tests_dir = Path(args.tests_dir)
    if not tests_dir.exists():
        print(f"[error] tests dir 부재: {tests_dir}", file=sys.stderr)
        return 2

    checks = discover_checks(tests_dir, args.filter)
    if not checks:
        print(f"[error] check_*.py 0 file 매치: {tests_dir} (filter={args.filter})",
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

    start = time.time()
    results: list[CheckResult] = []
    aborted = ""
    for check_path in checks:
        aborted = guard.violation()
        if aborted:
            break
        result = run_one(check_path, timeout=args.timeout, guard=guard)
        results.append(result)
        if args.fail_fast and result.exit_code != 0:
            break
    summary = aggregate(results, time.time() - start)
    summary.aborted_reason = aborted
    if aborted and not args.json:
        print(f"\n[abort] resource guard: {aborted}", file=sys.stderr)

    if args.json:
        print(json.dumps(asdict(summary), ensure_ascii=False, indent=2))
    else:
        print_human(summary)

    if summary.aborted_reason:
        return 3    # resource guard 발동 — 완주하지 않았으므로 PASS 로 오독되면 안 된다
    return 0 if summary.failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
