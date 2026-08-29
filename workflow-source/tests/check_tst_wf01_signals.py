"""TST-WF-01 verification-signal 측정 회귀 (TASK-2026-08-10-main-004)

TST-WF-01 은 두 번 잘못 운영됐다: 이름-count 측정이 정당한 case 관행을 못 봐
만성 red 였고 (→ v1.1.4 partial 선언 예외), 그 전에는 측정을 채우려고
`assert True` dummy 575개를 심었다 (v0.15.18 — 가짜 신호로 compliant).
v1.1.5 재설계(`_count_verification_signals`, AST)가 두 결함을 모두 갚는지 고정한다.

검증 케이스 (11):
    1. `def test_*` 정의가 신호로 세어진다
    2. inline `check(label, cond)` 호출식이 세어진다 (v1.1.4 이전 측정의 사각 1)
    3. `failures.append(...)` 수집식이 세어진다 (사각 2)
    4. `assert` 문이 세어진다 — 단 `assert True` 는 제외
    5. `assert True` dummy wrapper 는 **세어지지 않는다** (v0.15.18 가짜 신호 배제)
    6. 신호 0 파일이 있으면 non_compliant (결함 되주입 — 검증 없는 검사를 잡는다)
    7. parse 불가 파일은 신호 0 → non_compliant (실행될 수 없는 검사는 통과가 아니다)
    8. 실제 저장소: TST-WF-01 compliant + testing baseline 이 hard 로도 non_compliant 아님
    9. tests 디렉터리가 비어 있으면 non_compliant (0 files 를 잰 것은 통과가 아니다)
    10. `raise AssertionError(...)` 가 세어진다 (사각 3 — TASK-2026-08-13-main-009)
    11. 다른 예외 / bare `raise` 는 세지 않는다 (floor 를 무력화하지 않는다)

사각 3 의 성격: v1.1.5 재설계 후에도 `raise AssertionError` 는 신호가 아니었다.
저장소 smoke **89개**가 그 관용구를 쓰는데도 red 가 안 난 이유는 그 파일들이 다른
형태를 곁들였기 때문이고, 그 형태만 쓰는 파일이 하나 들어오자 min 이 0 이 됐다 —
"우연히 green" 이던 자리다. case 10/11 은 인정 범위를 넓히되 (10) 넓힌 범위가
floor 를 못 쓰게 만들지 않는지 (11) 를 같이 고정한다.

fixture 는 tmpdir 의 가짜 project_root (`<tmp>/workflow-source/tests/`) — 실제
저장소를 쓰지도, 건드리지도 않는다.

Stdlib only.
"""

from __future__ import annotations

#: 이 검사의 입력 표면 (spec `core/test_impact_tiering_spec.md` §2).
#: 게이트 채취 실측에서 뽑아 넓은 쪽으로 올렸다 — 좁으면 meta-watch 가 red 로 잡는다.
WATCHES = (
    "ai-workflow/memory/active/*",
    "workflow-source/pyproject.toml",
    "workflow-source/tests/*",
    "workflow-source/workflow_kit/*",
)

import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from workflow_kit.common.contracts.baselines import (  # noqa: E402
    _count_verification_signals,
    _eval_testing_baseline,
)


def _tst01_status(project_root: Path) -> str:
    summary = _eval_testing_baseline(project_root)
    rule = next(r for r in summary.results if r.rule_id == "TST-WF-01")
    return rule.status


def _fake_root(tmp: str, files: dict[str, str]) -> Path:
    root = Path(tmp)
    tests = root / "workflow-source" / "tests"
    tests.mkdir(parents=True, exist_ok=True)
    for name, body in files.items():
        (tests / name).write_text(body, encoding="utf-8")
    return root


def main() -> int:
    failures: list[str] = []

    def check(label: str, cond: bool, detail: str = "") -> None:
        if cond:
            print(f"PASS: {label}")
        else:
            print(f"FAIL: {label} — {detail}")
            failures.append(label)

    # 1)~5) 신호 counting 단위 검증
    check(
        "1) def test_* 정의가 세어진다",
        _count_verification_signals("def test_alpha():\n    run()\n") == 1,
    )
    check(
        "2) inline check() 호출식이 세어진다",
        _count_verification_signals(
            "def main():\n    check('a', 1 == 1)\n    check('b', 2 == 2)\n"
        ) == 2,
    )
    check(
        "3) failures.append 수집식이 세어진다",
        _count_verification_signals(
            "def main():\n    failures = []\n    if bad():\n        failures.append('x')\n"
        ) == 1,
    )
    n_assert = _count_verification_signals(
        "def helper():\n    assert compute() == 3\n    assert True\n"
    )
    check(
        "4) assert 는 세어지고 assert True 는 제외된다",
        n_assert == 1,
        f"count={n_assert}",
    )
    check(
        "5) assert True dummy wrapper 는 신호가 아니다",
        _count_verification_signals(
            "def test_case_4():\n    # dummy\n    assert True\n\n"
            "def test_case_5():\n    assert True\n"
        ) == 0,
    )

    n_raise = _count_verification_signals(
        "def main():\n"
        "    if not ok():\n"
        "        raise AssertionError('bad')\n"
        "    if not ok2():\n"
        "        raise AssertionError\n"
    )
    check(
        "10) raise AssertionError 가 세어진다 (호출형·bare 둘 다)",
        n_raise == 2,
        f"count={n_raise}",
    )
    n_other = _count_verification_signals(
        "def main():\n"
        "    try:\n"
        "        run()\n"
        "    except OSError:\n"
        "        raise\n"
        "    if bad():\n"
        "        raise ValueError('nope')\n"
        "    raise SystemExit(main())\n"
    )
    check(
        "11) 다른 예외·bare raise 는 세지 않는다",
        n_other == 0,
        f"count={n_other}",
    )

    with tempfile.TemporaryDirectory() as tmp:
        # 6) 신호 0 파일 되주입 → non_compliant
        root = _fake_root(tmp, {
            "check_real.py": "def test_a():\n    assert f() == 1\n" * 5,
            "check_empty.py": "print('hello')\n",
        })
        check(
            "6) 신호 0 파일이 있으면 non_compliant (되주입)",
            _tst01_status(root) == "non_compliant",
        )

        # 7) parse 불가 파일 → non_compliant
        root2 = _fake_root(tmp + "/b", {
            "check_broken.py": "def test_a(:\n",
        })
        check(
            "7) parse 불가 파일은 non_compliant",
            _tst01_status(root2) == "non_compliant",
        )

        # 9 준비) 빈 tests 디렉터리
        root3 = _fake_root(tmp + "/c", {})
        check(
            "9) smoke 파일 0개면 non_compliant (0 files ≠ 통과)",
            _tst01_status(root3) == "non_compliant",
        )

    # 8) 실제 저장소 — compliant + testing baseline 전체가 non_compliant 아님
    summary = _eval_testing_baseline(REPO_ROOT)
    tst01 = next(r for r in summary.results if r.rule_id == "TST-WF-01")
    check(
        "8) 실제 저장소 TST-WF-01 compliant (hard 복귀 후에도)",
        tst01.status == "compliant" and summary.status != "non_compliant",
        f"tst01={tst01.status} baseline={summary.status} notes={tst01.notes!r}",
    )

    total = 11
    if failures:
        print(f"{total - len(failures)}/{total} PASS — FAILED: {failures}")
        return 1
    print(f"{total}/{total} PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
