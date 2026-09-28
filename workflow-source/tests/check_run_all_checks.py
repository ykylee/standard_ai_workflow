"""tests/run_all_checks.py smoke test (v0.7.6+).

77+ check_*.py 의 통합 runner 정합성 검증.
v0.7.1 score_wiki_trend.py (10 test) / v0.7.5 refresh_wiki_memory (10 test) 의 패턴 따라.

Test 구성 (8 test):
1. discover_checks (filter 없음 → 77 file, --filter=baselines → 1 file)
2. discover_checks (--filter=baselines,wiki → 2 file substring OR)
3. parse_output (All N tests passed.)
4. parse_output (N/M tests failed:)
5. run_one (가벼운 check_unit_of_work_template — 대상이 보고한 수와 대조)
6. run_one (실제 check_refresh_wiki_memory 10/10)
7. aggregate (passed/failed/total_passed_tests 정합)
8. main CLI (--json 집계 — 가벼운 fixture 검사 2개, --no-such-filter)

Reference:
- tests/run_all_checks.py 본체
- tests/check_unit_of_work_template.py · check_security_baseline.py (fixture — 가벼운 것을 고른다)
- tests/check_refresh_wiki_memory.py (10 test)
- tools/refresh_wiki_memory.py (v0.7.5, dry-run → fix → apply 패턴)
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[1]
TESTS_DIR = SOURCE_ROOT / "tests"
RUNNER = TESTS_DIR / "run_all_checks.py"


def _import_runner():
    """run_all_checks.py 를 importlib 로 로드.

    Python 3.14 dataclass + KW_ONLY 의 sys.modules.get(cls.__module__).__dict__ 호출 위해
    명시적 sys.modules 등록 필수 (importlib 만으로는 부족).
    """
    import importlib.util
    import sys
    spec = importlib.util.spec_from_file_location("run_all_checks", str(RUNNER))
    mod = importlib.util.module_from_spec(spec)
    sys.modules["run_all_checks"] = mod  # 3.14 dataclass 호환
    spec.loader.exec_module(mod)
    return mod


# --- Test 1: discover_checks ---


def test_discover_checks_all() -> None:
    """filter 없음 → check_*.py 70+ file 발견."""
    mod = _import_runner()
    checks = mod.discover_checks(TESTS_DIR)
    assert len(checks) >= 70, f"expected 70+ checks, got {len(checks)}"
    # 모두 .py file
    assert all(c.suffix == ".py" for c in checks)
    # 모두 check_ prefix
    assert all(c.stem.startswith("check_") for c in checks)


def test_discover_checks_filter_substring() -> None:
    """--filter=baselines → 1 file, --filter=baselines,wiki → 2 file."""
    mod = _import_runner()
    bl = mod.discover_checks(TESTS_DIR, "baselines")
    assert len(bl) >= 1
    assert all("baselines" in c.stem for c in bl)

    bl_wiki = mod.discover_checks(TESTS_DIR, "baselines,wiki")
    assert len(bl_wiki) >= 2
    # substring OR match
    assert all("baselines" in c.stem or "wiki" in c.stem for c in bl_wiki)


def test_discover_checks_filter_no_match() -> None:
    """--filter=zzz_no_match_zzz → 0 file."""
    mod = _import_runner()
    none = mod.discover_checks(TESTS_DIR, "zzz_no_match_zzz")
    assert len(none) == 0


# --- Test 2: parse_output ---


def test_parse_output_pass() -> None:
    """'All N tests passed.' → passed=N, failed=0."""
    mod = _import_runner()
    passed, failed, last = mod.parse_output("All 16 tests passed.\n")
    assert passed == 16
    assert failed == 0
    assert "16" in last


def test_parse_output_fail() -> None:
    """'N/M tests failed:' → failed=N, last_line 보존."""
    mod = _import_runner()
    output = "  FAIL  test_x: assertion\n\n1/10 tests failed:\n  - test_x: assertion"
    passed, failed, last = mod.parse_output(output)
    assert failed == 1
    assert "test_x" in last


# --- Test 3: run_one (실제 check 실행) ---


def test_run_one_baselines() -> None:
    """run_one(가벼운 검사) → exit 0, 대상이 보고한 test 수 그대로.

    재는 것은 `run_one` 의 종료 코드·test 수 파싱이지 대상의 내용이 아니다. 대상은
    원래 `check_baselines_compliance`(단독 8.6s, 게이트 부하에서 17.9s — 상한
    30s)였는데 이 검사 단독 시간의 절반 가까이를 fixture 가 썼다
    (TASK-2026-09-28-main-008). 이름은 호출 이력 호환으로 둔다.
    """
    mod = _import_runner()
    target = TESTS_DIR / "check_unit_of_work_template.py"
    result = mod.run_one(target, timeout=30)
    assert result.exit_code == 0, f"exit {result.exit_code}: {result.error_excerpt}"
    assert result.failed == 0
    reported = re.search(r"All (\d+) tests passed", result.last_line or "")
    assert reported, f"last_line 파싱 실패: {result.last_line!r}"
    assert result.passed == int(reported.group(1)) > 0, (
        f"parse 불일치: passed={result.passed}, last_line={result.last_line!r}"
    )


def test_run_one_refresh_wiki() -> None:
    """run_one(check_refresh_wiki_memory.py) → exit 0, 전량 PASS + 파싱 정합."""
    mod = _import_runner()
    target = TESTS_DIR / "check_refresh_wiki_memory.py"
    result = mod.run_one(target, timeout=30)
    assert result.exit_code == 0
    assert result.failed == 0
    # 대상 check 의 test 개수는 늘어난다(10 → 14). 리터럴을 박으면 test 추가마다
    # 여기가 red 가 되므로, 파싱 정합은 대상이 스스로 보고한 숫자와 대조해 검증한다.
    assert result.passed >= 10, f"passed={result.passed} (expected >= 10)"
    reported = re.search(r"All (\d+) tests passed", result.last_line or "")
    assert reported, f"last_line 파싱 실패: {result.last_line!r}"
    assert result.passed == int(reported.group(1)), (
        f"parse 불일치: passed={result.passed}, last_line={result.last_line!r}"
    )


# --- Test 4: aggregate ---


def test_aggregate() -> None:
    """aggregate 가 passed/failed/test 합계 정확히 계산."""
    mod = _import_runner()
    results = [
        mod.CheckResult(name="a", path="a", exit_code=0, duration_sec=1.0,
                        passed=16, failed=0, last_line="All 16 tests passed."),
        mod.CheckResult(name="b", path="b", exit_code=0, duration_sec=0.5,
                        passed=10, failed=0, last_line="All 10 tests passed."),
    ]
    summary = mod.aggregate(results, duration=1.5)
    assert summary.total == 2
    assert summary.passed == 2
    assert summary.failed == 0
    assert summary.total_passed_tests == 26
    assert summary.total_failed_tests == 0
    assert summary.total_duration_sec == 1.5


# --- Test 5: main CLI ---


def test_cli_json_output() -> None:
    """--json output 의 집계 — 검사 수 · 통과 수 · 하위 test 수 합.

    fixture 는 `All N tests passed.` 를 내는(러너가 하위 test 수를 읽는) **가벼운**
    검사 둘이다. 예전 `--filter=baselines,refresh_wiki` 는 실제로 검사 3개
    (`baselines_compliance` 8.6s 포함)에 걸려 이 검사 단독 19s 중 9s 를 썼다
    (TASK-2026-09-28-main-008). 재는 것은 집계이지 fixture 검사의 내용이 아니다.
    """
    proc = subprocess.run(
        [sys.executable, str(RUNNER), "--filter=security_baseline,unit_of_work_template", "--json"],
        capture_output=True, text=True, timeout=60,
    )
    assert proc.returncode == 0, f"exit {proc.returncode}: {proc.stderr}"
    out = json.loads(proc.stdout)
    assert out["total"] == 2, f"fixture 필터가 {out['total']}개에 걸렸다 (2개여야 한다)"
    assert out["passed"] == 2
    assert out["failed"] == 0
    per_check = [r["passed"] for r in out["results"]]
    # 하위 test 수를 못 읽으면 0 이 되고 합이 조용히 줄어든다 — 각각 0 보다 커야 한다.
    assert all(n > 0 for n in per_check), f"하위 test 수를 못 읽은 검사가 있다: {out['results']}"
    assert out["total_passed_tests"] == sum(per_check), (
        f"total_passed_tests={out['total_passed_tests']} != 개별 합 {sum(per_check)}"
    )


def test_cli_no_match_filter_errors() -> None:
    """--filter=zzz_no_match_zzz → exit 2 (매치 0)."""
    proc = subprocess.run(
        [sys.executable, str(RUNNER), "--filter=zzz_no_match_zzz"],
        capture_output=True, text=True, timeout=30,
    )
    assert proc.returncode == 2
    assert "0 file 매치" in proc.stderr or "부재" in proc.stderr


# --- 메인 실행 ---


def test_error_excerpt_keeps_failure_reason() -> None:
    """실패 사유가 excerpt 에 남는가 (v1.0.2).

    이전 구현은 *마지막 3줄* 을 잘랐는데, check 들이 끝에 요약 줄 + 빈 줄을 붙이고
    개행으로 끝나는 문자열은 split 시 빈 원소가 하나 더 생기므로, 사유가 적힌 줄은
    뒤에서 4번째가 되어 **항상 잘렸다**. CI 아티팩트에 `=== Result: 0/1 PASS ===` 만
    남아 원인을 알 수 없었다.
    """
    from run_all_checks import _error_excerpt

    output = (
        "  case 5 (...): PASS\n"
        "  case 6 (...): PASS\n"
        "  ✗ test_x FAIL: full validate summary local_mypy != ok\n"
        "\n"
        "=== Result: 0/1 PASS ===\n"
    )
    excerpt = _error_excerpt(output)
    assert "local_mypy != ok" in excerpt, f"실패 사유가 excerpt 에 없다: {excerpt!r}"

    # Traceback 형태도 사유가 남아야 한다.
    tb = (
        "Traceback (most recent call last):\n"
        '  File "x.py", line 1, in <module>\n'
        "AssertionError: 무언가 어긋났다\n"
    )
    assert "AssertionError" in _error_excerpt(tb), _error_excerpt(tb)

    # 표지가 없으면 마지막 비어 있지 않은 줄들로 떨어진다 (빈 문자열 반환 금지).
    assert _error_excerpt("a\nb\n\n").strip(), "표지 없는 출력에서 excerpt 가 비었다"


def main() -> int:
    test_funcs = [
        test_discover_checks_all,
        test_discover_checks_filter_substring,
        test_discover_checks_filter_no_match,
        test_parse_output_pass,
        test_parse_output_fail,
        test_run_one_baselines,
        test_run_one_refresh_wiki,
        test_aggregate,
        test_cli_json_output,
        test_cli_no_match_filter_errors,
        test_error_excerpt_keeps_failure_reason,
    ]

    passed = 0
    failed = 0
    failures: list[tuple[str, str]] = []
    for func in test_funcs:
        try:
            func()
            print(f"  PASS  {func.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"  FAIL  {func.__name__}: {e}")
            failed += 1
            failures.append((func.__name__, str(e)))
        except Exception as e:  # noqa: BLE001
            print(f"  ERROR {func.__name__}: {type(e).__name__}: {e}")
            failed += 1
            failures.append((func.__name__, f"{type(e).__name__}: {e}"))

    print()
    if failed == 0:
        print(f"All {passed} tests passed.")
        return 0
    print(f"{failed}/{passed + failed} tests failed:")
    for name, err in failures:
        print(f"  - {name}: {err}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
