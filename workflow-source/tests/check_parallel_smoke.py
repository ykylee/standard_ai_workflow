"""smoke 병렬 실행 + 정숙 구간 계약 (TASK-2026-08-10-main-018).

CI job 604s 중 576s 가 smoke 실행이었고, 267개 check 의 시간 분포는 극단적이라
(상위 13개가 50%, 하위 133개 합계 9.8s) 병렬화가 유일하게 큰 지렛대였다.
실측 345s → 85s.

병렬화가 어려웠던 이유는 성능이 아니라 **저장소 전역 상태를 관찰하는 check** 다.
`check_no_repo_write` 는 실행 전후의 `git status` 를 비교하고,
`check_source_without_runtime_layer` 는 저장소를 통째로 복사한다. 둘 다 관찰
대상이 저장소 자신이라 격리로 풀리지 않는다 — 그래서 정숙 구간(병렬이 끝난 뒤
직렬)이 있다.

이 검사가 지키는 것은 **그 구조** 다. 마커가 사라지거나, 분류가 일부를 흘리거나,
병렬이 실제로는 동시 실행이 아니게 되면 여기서 잡힌다.

검증 케이스 (8):
    1. `--jobs` 해석 계약 (auto / 정수 / 잘못된 값)
    2. 마커 판정은 AST 기반이고, 주석·문자열 언급에 속지 않는다
    3. 실제 저장소에서 정숙 구간이 비어 있지 않다 (구조가 살아 있다)
    4. 분류가 전체를 보존하고 순서를 지킨다 (누락·중복 없음)
    5. 정숙 check 는 병렬 구간에 들어가지 않는다
    6. 병렬이 실제로 동시 실행한다 (벽시계 < 합계)
    7. `--jobs 1` 과 병렬의 판정이 같다 (표본)
    8. 정숙 구간이 병렬 구간 **뒤** 에 온다 (결과 순서로 관찰)
    9. sandbox 사본 복사는 **소멸 파일에 내성** 이 있다 (병렬 중 transient 파일
       race — TASK-2026-08-11-main-006). 소멸 아닌 오류는 그대로 던진다.

Stdlib only.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
TESTS_DIR = SOURCE_ROOT / "tests"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))

import run_all_checks as R  # noqa: E402

RUNNER = TESTS_DIR / "run_all_checks.py"
# 표본: 서로 독립이고 빠르며, 정숙 마커가 없는 것들.
SAMPLE_FILTER = "wiki_source_rule,paths,docs"


REQUIRES_QUIET_REPO = True
"""runner 를 subprocess 로 불러 다른 check 를 실행한다 — 그 대상이 저장소를 건드릴 수 있다 (TASK-018 실측).

되돌리므로 전후 비교로는 안 걸리지만, 그 **사이** 를 다른 check 가 보면 깨진다.
병렬 구간이 끝난 뒤 정숙 구간에서 직렬로 돈다."""
def _run_runner(*extra: str) -> dict:
    proc = subprocess.run(
        [sys.executable, str(RUNNER), f"--filter={SAMPLE_FILTER}", "--json",
         "--no-guard", *extra],
        capture_output=True, text=True, timeout=600,
        env={**os.environ, "PYTHONPATH": str(SOURCE_ROOT)},
    )
    return json.loads(proc.stdout)


def test_resolve_jobs_contract() -> None:
    auto = R._resolve_jobs("auto")
    assert 1 <= auto <= R.MAX_AUTO_JOBS, f"auto 가 상한을 벗어났다: {auto}"
    assert R._resolve_jobs("3") == 3
    assert R._resolve_jobs("1") == 1
    for bad in ("0", "-2", "abc", ""):
        try:
            R._resolve_jobs(bad)
        except ValueError:
            continue
        raise AssertionError(f"잘못된 --jobs 를 통과시켰다: {bad!r}")


def test_marker_is_ast_based() -> None:
    """주석이나 문자열에 이름이 나오는 것만으로는 정숙이 되지 않는다."""
    with tempfile.TemporaryDirectory() as tmp:
        decoy = Path(tmp) / "check_decoy.py"
        decoy.write_text(
            f'"""문서에 {R.QUIET_MARKER} 를 언급만 한다."""\n'
            f"# {R.QUIET_MARKER} = True  (주석)\n"
            f'NOTE = "{R.QUIET_MARKER} = True"\n',
            encoding="utf-8",
        )
        assert not R.requires_quiet_repo(decoy), (
            "주석/문자열 언급을 선언으로 오인했다 — 문자열 매칭으로 후퇴한 것이다"
        )

        real = Path(tmp) / "check_real.py"
        real.write_text(f"{R.QUIET_MARKER} = True\n", encoding="utf-8")
        assert R.requires_quiet_repo(real), "실제 선언을 못 읽었다"

        false_decl = Path(tmp) / "check_false.py"
        false_decl.write_text(f"{R.QUIET_MARKER} = False\n", encoding="utf-8")
        assert not R.requires_quiet_repo(false_decl), "False 선언을 참으로 읽었다"


def test_quiet_partition_is_not_empty() -> None:
    """실제 저장소에 정숙 구간이 살아 있다.

    비어 있다면 마커가 사라진 것이고, 그러면 병렬 실행이 조용히 오탐을 내기
    시작한다 (실측에서 정확히 그 둘만 깨졌다).
    """
    checks = R.discover_checks(TESTS_DIR)
    _parallel, quiet = R.partition_checks(checks)
    assert quiet, (
        "정숙 구간이 비었다 — 저장소 전역을 관찰하는 check 가 병렬 구간으로 흘렀다"
    )
    names = {p.stem for p in quiet}
    assert "check_no_repo_write" in names, (
        f"check_no_repo_write 가 정숙 구간에 없다 (현재: {sorted(names)})"
    )


def test_partition_preserves_everything() -> None:
    checks = R.discover_checks(TESTS_DIR)
    parallel, quiet = R.partition_checks(checks)
    assert len(parallel) + len(quiet) == len(checks), (
        f"분류에서 유실됐다: {len(parallel)}+{len(quiet)} != {len(checks)}"
    )
    assert set(parallel) | set(quiet) == set(checks), "분류가 원본 집합과 다르다"
    assert not (set(parallel) & set(quiet)), "같은 check 가 양쪽에 있다"
    # 순서 보존 — 출력이 실행 타이밍에 흔들리면 두 실행을 비교할 수 없다.
    assert parallel == [c for c in checks if c in set(parallel)], "병렬 구간 순서가 흐트러졌다"
    assert quiet == [c for c in checks if c in set(quiet)], "정숙 구간 순서가 흐트러졌다"


def test_quiet_checks_are_not_in_parallel_batch() -> None:
    checks = R.discover_checks(TESTS_DIR)
    parallel, quiet = R.partition_checks(checks)
    for path in quiet:
        assert path not in parallel, f"정숙 check 가 병렬 구간에도 있다: {path.stem}"
        assert R.requires_quiet_repo(path), f"정숙으로 분류됐는데 선언이 없다: {path.stem}"
    for path in parallel:
        assert not R.requires_quiet_repo(path), (
            f"선언이 있는데 병렬 구간에 있다: {path.stem}"
        )


def test_parallel_actually_overlaps() -> None:
    """벽시계가 check 합계보다 확실히 작다 = 실제로 동시에 돌았다.

    `--jobs` 를 받아만 두고 순차로 도는 회귀를 잡는다.
    """
    data = _run_runner("--jobs=4")
    assert data["total"] >= 3, f"표본이 너무 작다: {data['total']}"
    serial_sum = sum(r["duration_sec"] for r in data["results"])
    wall = data["total_duration_sec"]
    assert wall < serial_sum, (
        f"벽시계 {wall}s 가 합계 {serial_sum}s 보다 작지 않다 — 동시 실행이 아니다"
    )


def test_serial_and_parallel_agree() -> None:
    serial = _run_runner("--jobs=1")
    parallel = _run_runner("--jobs=4")
    s = {r["name"]: r["exit_code"] for r in serial["results"]}
    p = {r["name"]: r["exit_code"] for r in parallel["results"]}
    assert s.keys() == p.keys(), (
        f"실행된 check 집합이 다르다: 직렬-병렬={s.keys() - p.keys()}, "
        f"병렬-직렬={p.keys() - s.keys()}"
    )
    disagreed = {k: (s[k], p[k]) for k in s if s[k] != p[k]}
    assert not disagreed, f"직렬과 병렬의 판정이 다르다: {disagreed}"


def test_quiet_runs_after_parallel() -> None:
    """정숙 구간이 병렬 구간 뒤에 온다 — 결과 배열의 순서로 관찰한다."""
    checks = R.discover_checks(TESTS_DIR)
    parallel, quiet = R.partition_checks(checks)
    if not quiet or not parallel:
        raise AssertionError("표본 부족 — 구조가 이미 깨졌다")

    class _Args:
        timeout = 120
        fail_fast = False

    guard = R.ResourceGuard(tmp_root=tempfile.gettempdir(), enabled=False)
    # 정숙 1개 + 빠른 병렬 2개만 골라 실제 run_pass 를 돌린다.
    fast = [c for c in parallel if c.stem in
            ("check_wiki_source_rule", "check_paths")][:2]
    subset = fast + quiet[:1]
    summary = R.run_pass(subset, _Args(), guard, None, jobs=2)
    names = [r.name for r in summary.results]
    assert names, "결과가 비었다"
    assert names[-1] == quiet[0].stem, (
        f"정숙 check 가 마지막이 아니다: {names} — 병렬 구간과 섞여 돌았다"
    )


def test_sandbox_copy_tolerates_vanished_files() -> None:
    """사본 복사는 소멸 파일을 건너뛰고, 소멸 아닌 오류는 던진다 (TASK-2026-08-11-main-006).

    실사례: PERF 벤치마크가 저장소에 남기던 transient 파일이 `copytree` 스캔과
    복사 사이에 사라져 `check_bidir_link_v0_13_3` 가 shutil.Error 로 flake.
    `shutil.copy2` 를 감싸 소멸/권한 오류를 결정적으로 주입한다.
    """
    import shutil

    from _repo_sandbox import repo_sandbox

    with tempfile.TemporaryDirectory(prefix="vanish-src-") as td:
        src = Path(td) / "tree"
        (src / "sub").mkdir(parents=True)
        (src / "keep.txt").write_text("k", encoding="utf-8")
        (src / "sub" / "vanish.txt").write_text("v", encoding="utf-8")
        orig_copy2 = shutil.copy2

        def _vanishing_copy2(s, d, *a, **kw):  # noqa: ANN001
            if str(s).endswith("vanish.txt"):
                raise FileNotFoundError(2, "No such file or directory", str(s))
            return orig_copy2(s, d, *a, **kw)

        shutil.copy2 = _vanishing_copy2
        try:
            with repo_sandbox(src) as sandbox:
                assert (sandbox / "keep.txt").exists(), "정상 파일이 복사되지 않았다"
                assert not (sandbox / "sub" / "vanish.txt").exists(), "소멸 파일이 복사됐다?"
        finally:
            shutil.copy2 = orig_copy2

        # 소멸이 아닌 오류 (권한 등) 는 삼키면 안 된다 — 조용한 쪽이 틀린 쪽이다.
        def _denied_copy2(s, d, *a, **kw):  # noqa: ANN001
            if str(s).endswith("keep.txt"):
                raise PermissionError(13, "Permission denied", str(s))
            return orig_copy2(s, d, *a, **kw)

        shutil.copy2 = _denied_copy2
        try:
            raised = False
            try:
                with repo_sandbox(src):
                    pass
            except (shutil.Error, PermissionError):
                raised = True
            assert raised, "소멸 아닌 오류가 조용히 삼켜졌다"
        finally:
            shutil.copy2 = orig_copy2


def main() -> int:
    test_funcs = [
        test_resolve_jobs_contract,
        test_marker_is_ast_based,
        test_quiet_partition_is_not_empty,
        test_partition_preserves_everything,
        test_quiet_checks_are_not_in_parallel_batch,
        test_parallel_actually_overlaps,
        test_serial_and_parallel_agree,
        test_quiet_runs_after_parallel,
        test_sandbox_copy_tolerates_vanished_files,
    ]
    failures: list[tuple[str, str]] = []
    for func in test_funcs:
        started = time.time()
        try:
            func()
            print(f"  PASS: {func.__name__} ({time.time()-started:.1f}s)")
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
