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

검증 케이스 (13):
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
    10. `CHECK_TIMEOUT_S` 선언은 timeout 을 **늘릴 수만** 있고 실제로 적용된다
        (TASK-2026-08-11-main-015 — 무거운 check 가 병렬 부하에서 60s 를 넘던
        flake). 선언한 check 는 짧은 `--timeout` 에도 살아남고, 무선언 check 는
        같은 조건에서 TIMEOUT 으로 죽는다 — 양방향이어야 계약이다.
    11. 병렬 구간 제출은 LPT 다 (TASK-2026-09-28-main-003) — 미상·선언이 먼저,
        기록은 긴 순, 동률은 이름. 집합 보존 + 출처별 개수가 입력과 맞는다.
    12. 소요 기록은 **병합** 저장되고 (안 돈 검사 값 유지), 깨진 파일은 사유를
        내고 빈 기록으로 간다 — 순서 힌트가 판정을 깨뜨리면 안 된다.
    13. 다른 tests-dir 로 돈 runner 는 기록을 읽지도 쓰지도 않고, 그 사실을
        schedule 에 남긴다. 결과 보고 순서는 LPT 여도 discover 순서다.

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
    # 상한 8 을 걷었다 (TASK-2026-09-28-main-003) — auto 는 코어 수 그대로다.
    assert auto == max(1, os.cpu_count() or 4), f"auto 가 코어 수가 아니다: {auto}"
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
    # **이름을 못 박지 않는다** (TASK-2026-09-22-main-008). 예전에는
    # `check_no_repo_write` 가 정숙 구간에 있는지를 카나리로 썼는데, 그 검사가
    # 정당한 이유로 병렬 구간으로 옮겨가자(감시가 러너로 흡수돼 임시 저장소만
    # 쓰게 됐다) 이 단언이 red 가 됐다 — 배치를 기대값으로 삼은 fixture 였다.
    #
    # 계약은 "누가 거기 있는가" 가 아니라 **"선언과 배치가 일치하는가"** 다.
    declared = {
        path.stem for path in checks
        if f"{R.QUIET_MARKER} = True" in path.read_text(encoding="utf-8", errors="ignore")
    }
    placed = {p.stem for p in quiet}
    assert placed == declared, (
        f"선언과 배치가 갈렸다 — 선언만: {sorted(declared - placed)} / "
        f"배치만: {sorted(placed - declared)}"
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


def test_declared_timeout_extends_and_default_kills() -> None:
    """`CHECK_TIMEOUT_S` 계약 (TASK-2026-08-11-main-015).

    같은 3s 짜리 check 를 `--timeout=1` 로 돌린다: 선언(30s) 이 있으면 살아남고
    없으면 TIMEOUT — 선언이 장식이 아니라 실제 적용됨을 양방향으로 고정한다.
    decoy (주석/문자열/음수) 는 선언으로 치지 않는다.
    """
    # 단위 계약: 선언은 max 로만 합쳐진다 + AST 기반이라 decoy 에 속지 않는다.
    with tempfile.TemporaryDirectory() as tmp:
        declared = Path(tmp) / "check_u_declared.py"
        declared.write_text(f"{R.TIMEOUT_MARKER} = 150\n", encoding="utf-8")
        assert R.effective_timeout(declared, 60) == 150, "선언이 CLI 값을 못 늘렸다"
        assert R.effective_timeout(declared, 300) == 300, "선언이 CLI 값을 줄였다 — max 여야 한다"

        decoy = Path(tmp) / "check_u_decoy.py"
        decoy.write_text(
            f'"""{R.TIMEOUT_MARKER} = 999 를 언급만 한다."""\n'
            f"# {R.TIMEOUT_MARKER} = 999\n"
            f'NOTE = "{R.TIMEOUT_MARKER} = 999"\n'
            f"{R.TIMEOUT_MARKER} = -5\n",
            encoding="utf-8",
        )
        assert R.effective_timeout(decoy, 60) == 60, "decoy/음수 선언을 적용했다"

    # 실행 계약: runner subprocess 로 양방향 실증.
    with tempfile.TemporaryDirectory() as tmp:
        body = "import time\ntime.sleep(3)\nraise SystemExit(0)\n"
        (Path(tmp) / "check_slow_declared.py").write_text(
            f"{R.TIMEOUT_MARKER} = 30\n{body}", encoding="utf-8")
        (Path(tmp) / "check_slow_undeclared.py").write_text(body, encoding="utf-8")

        proc = subprocess.run(
            [sys.executable, str(RUNNER), f"--tests-dir={tmp}", "--timeout=1",
             "--jobs=2", "--json", "--no-guard"],
            capture_output=True, text=True, timeout=120,
            env={**os.environ, "PYTHONPATH": str(SOURCE_ROOT)},
        )
        data = json.loads(proc.stdout)
        by_name = {r["name"]: r for r in data["results"]}
        assert by_name["check_slow_declared"]["exit_code"] == 0, (
            f"선언(30s)한 3s check 가 --timeout=1 에 죽었다 — 선언이 적용되지 않는다: "
            f"{by_name['check_slow_declared']}"
        )
        undeclared = by_name["check_slow_undeclared"]
        assert undeclared["exit_code"] != 0 and "timeout" in undeclared["error_excerpt"], (
            f"무선언 3s check 가 --timeout=1 을 살아남았다 — timeout 자체가 죽었다: {undeclared}"
        )


def test_lpt_schedule_order() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)

        def mk(name: str, body: str = "") -> Path:
            path = root / f"{name}.py"
            path.write_text(body, encoding="utf-8")
            return path

        a_short = mk("check_a_short")
        b_long = mk("check_b_long")
        c_mid = mk("check_c_mid")
        d_tie = mk("check_d_tie")
        e_new = mk("check_e_new")
        f_decl = mk("check_f_decl", f"{R.TIMEOUT_MARKER} = 150\n")
        g_decl_small = mk("check_g_decl_small", f"{R.TIMEOUT_MARKER} = 90\n")
        checks = [a_short, b_long, c_mid, d_tie, e_new, f_decl, g_decl_small]
        durations = {"check_a_short": 0.3, "check_b_long": 40.0,
                     "check_c_mid": 9.0, "check_d_tie": 9.0}
        ordered, counts = R.schedule_order(checks, durations)
        assert [p.stem for p in ordered] == [
            "check_f_decl", "check_g_decl_small", "check_e_new",   # 기록 없음 먼저
            "check_b_long", "check_c_mid", "check_d_tie", "check_a_short",
        ], f"LPT 순서가 아니다: {[p.stem for p in ordered]}"
        assert counts == {"recorded": 4, "declared": 2, "unknown": 1}, counts
        assert set(ordered) == set(checks) and len(ordered) == len(checks), "집합이 변했다"
        again, _ = R.schedule_order(list(reversed(checks)), durations)
        assert again == ordered, "입력 순서에 따라 결과가 흔들린다 — 동률 규칙이 없다"
        # 기록이 전혀 없으면 선언 → 알파벳 (첫 실행 fallback)
        cold, cold_counts = R.schedule_order(checks, {})
        assert [p.stem for p in cold][:2] == ["check_f_decl", "check_g_decl_small"]
        assert [p.stem for p in cold][2:] == sorted(p.stem for p in checks
                                                   if p not in (f_decl, g_decl_small))
        assert cold_counts == {"recorded": 0, "declared": 2, "unknown": 5}, cold_counts

        # 함수만 맞고 run_pass 가 그것을 안 쓰면 소용없다 — 실제 제출 순서를 본다.
        # 동기 가짜 executor 로 제출을 그대로 기록한다 (스레드 경합 없이 결정적).
        from concurrent.futures import Future

        submitted: list[str] = []

        class _SyncPool:
            def __init__(self, max_workers: int) -> None:
                pass

            def __enter__(self):  # noqa: ANN204
                return self

            def __exit__(self, *exc) -> None:  # noqa: ANN002
                return None

            def submit(self, fn, path, **kw):  # noqa: ANN001, ANN003
                submitted.append(path.stem)
                fut: Future = Future()
                fut.set_result(R.CheckResult(name=path.stem, path=str(path),
                                             exit_code=0, duration_sec=0.0))
                return fut

        class _Args:
            timeout = 60
            fail_fast = False

        orig_pool = R.ThreadPoolExecutor
        R.ThreadPoolExecutor = _SyncPool
        try:
            summary = R.run_pass(checks, _Args(),
                                 R.ResourceGuard(tmp_root=tmp, enabled=False), None,
                                 jobs=4, durations=durations, history_note="")
        finally:
            R.ThreadPoolExecutor = orig_pool
        assert submitted == [p.stem for p in ordered], (
            f"run_pass 가 LPT 순서로 제출하지 않는다: {submitted}")
        assert [r.name for r in summary.results] == [p.stem for p in checks], (
            "결과 보고가 discover 순서가 아니다 — 두 실행을 나란히 비교할 수 없다")
        assert summary.schedule["recorded"] == 4 and summary.schedule["jobs"] == 4, (
            summary.schedule)


def test_duration_history_merges_and_survives_corruption() -> None:
    def result(name: str, sec: float) -> "R.CheckResult":
        return R.CheckResult(name=name, path=name, exit_code=0, duration_sec=sec)

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / R.DURATIONS_FILENAME
        loaded, note = R.load_durations(path)
        assert loaded == {} and "없음" in note, (loaded, note)
        R.save_durations(path, [result("check_x", 3.0), result("check_y", 7.5)])
        R.save_durations(path, [result("check_x", 4.25)])
        loaded, note = R.load_durations(path)
        assert note == "" and loaded == {"check_x": 4.25, "check_y": 7.5}, (
            f"병합이 아니다 (안 돈 검사 값이 사라졌거나 갱신이 안 됐다): {loaded}")
        assert not list(Path(tmp).glob("*.tmp")), "원자적 교체의 임시 파일이 남았다"
        path.write_text("{not json", encoding="utf-8")
        loaded, note = R.load_durations(path)
        assert loaded == {} and note, f"깨진 기록을 조용히 받아들였다: {loaded} / {note!r}"
        path.write_text(json.dumps({"schema": 999, "durations": {"check_x": 1}}),
                        encoding="utf-8")
        loaded, note = R.load_durations(path)
        assert loaded == {} and "스키마" in note, (loaded, note)
        assert R.load_durations(None)[1], "git 저장소 아님이 사유 없이 지나갔다"


def test_fixture_runner_leaves_history_alone() -> None:
    history = R.durations_path(REPO_ROOT)
    before = history.stat().st_mtime_ns if history and history.exists() else None
    with tempfile.TemporaryDirectory() as tmp:
        for name in ("check_b_one", "check_a_two", "check_c_three"):
            (Path(tmp) / f"{name}.py").write_text("raise SystemExit(0)\n", encoding="utf-8")
        proc = subprocess.run(
            [sys.executable, str(RUNNER), f"--tests-dir={tmp}", "--jobs=2", "--json",
             "--no-guard", "--no-lock"],
            capture_output=True, text=True, timeout=120,
            env={k: v for k, v in {**os.environ, "PYTHONPATH": str(SOURCE_ROOT)}.items()
                 if k != R.RUNNER_LOCK_ENV},
        )
        data = json.loads(proc.stdout)
    sch = data["schedule"]
    assert sch.get("order") == "lpt" and sch.get("jobs") == 2, sch
    assert sch["recorded"] == 0 and sch["unknown"] == 3, f"fixture 가 기록을 읽었다: {sch}"
    assert "tests-dir" in sch["history_note"], f"미사용 사유가 없다: {sch}"
    assert [r["name"] for r in data["results"]] == [
        "check_a_two", "check_b_one", "check_c_three"], "결과가 discover 순서가 아니다"
    after = history.stat().st_mtime_ns if history and history.exists() else None
    assert after == before, "fixture runner 가 실제 소요 기록을 건드렸다"


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
        test_declared_timeout_extends_and_default_kills,
        test_lpt_schedule_order,
        test_duration_history_merges_and_survives_corruption,
        test_fixture_runner_leaves_history_alone,
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
