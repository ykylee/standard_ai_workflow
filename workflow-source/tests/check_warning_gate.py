#!/usr/bin/env python3
"""검사 실행이 내는 **Python 경고**를 게이트 신호로 다루는 계약.

TASK-2026-09-21-main-007. 계약과 실측 근거는
`workflow_kit/common/check_warnings.py` docstring 이 정본이다.

82차(main-006)가 해석기 축을 세웠지만 **그 축이 보는 것은 종료 코드뿐**이었다.
3.12+ 에서만 나는 `SyntaxWarning: invalid escape sequence` 는 exit 0 이라 CI 4셀이
전부 green 이었고, 그 결함은 사람이 두 실행의 출력을 눈으로 대조해서 찾았다.

전수 census(2026-09-21, 288검사 × 2해석기)가 판정 경계를 정했다:

| | py3.13 | py3.11 |
|---|---|---|
| 저장소 안 | 6 | 6 |
| 서드파티 | 0 | 2 |

**갈린 2건은 전부 서드파티** 였고 원인도 해석기가 아니라 두 venv 의 의존성 해석
차이였다. 그래서 '해석기 간 출력 차이를 red' 는 기각했다 — 오늘 당장 위양성 2건이고
잡음 정규화로도 못 없앤다(실제로 다른 버전이다). 대신 **출처(위치)로 가른다**:
저장소 코드가 낸 것만 red, 서드파티는 보고만. 그러면 셀 간 비교 인프라가 필요 없다 —
각 셀이 독립적으로 판정해도 3.12+ 에서만 나는 경고는 그 셀이 red 가 된다.

검증 케이스 (7):
    1. 추출기는 Python 경고만 뽑는다 (검사가 찍는 `WARN:` 산문은 아니다)
    2. 정규화가 실행마다 달라지는 조각을 지운다 (tmp 경로 · 객체 주소)
    3. 출처 분류 — 저장소 / 서드파티 / 귀속 불가
    4. `<unknown>` 은 게이트 대상이다 (이 축을 만든 결함의 위치가 정확히 그것이다)
    5. 서드파티는 게이트 대상이 아니다 (위양성 없음)
    6. runner 가 저장소 경고로 red 가 된다 — 검사 자신은 exit 0 인데도 (end-to-end)
    7. `call_deprecated` 는 삼키되 **경고가 났는지 단언**한다

Stdlib only.
"""

from __future__ import annotations

#: 전역 선언 (spec `core/test_impact_tiering_spec.md` §2). case 6 이 runner 를
#: 임시 probe 로 돌리므로 입력 표면이 kit + tests 전체다.
WATCHES = (
    "workflow-source/workflow_kit/*",
    "workflow-source/pyproject.toml",
    "workflow-source/tests/run_all_checks.py",
)

#: 이 검사가 강제하는 정본 요구 (spec `core/test_impact_tiering_spec.md` §7).
ENFORCES = ("repo-warnings-are-a-gate-signal",)

#: case 6 이 runner 를 한 번 더 띄운다 — 기본 60s 를 넘길 수 있다.
CHECK_TIMEOUT_S = 150

import json
import os
import subprocess
import sys
import warnings
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from workflow_kit.common.check_warnings import (  # noqa: E402
    GATED_ORIGINS,
    ORIGIN_REPO,
    ORIGIN_THIRD_PARTY,
    ORIGIN_UNATTRIBUTED,
    call_deprecated,
    classify,
    extract,
    normalize,
)

RUNNER = SOURCE_ROOT / "tests" / "run_all_checks.py"

_failures: list[str] = []
_passes: list[str] = []


def _record(case: str, ok: bool, detail: str = "") -> None:
    (_passes if ok else _failures).append(case if ok else f"{case}: {detail}")
    print(f"  {case}: {'PASS' if ok else 'FAIL'}{(' — ' + detail) if detail else ''}")


def case_1_extracts_only_python_warnings() -> None:
    """검사가 사람용으로 찍는 `WARN:` 산문을 경고로 세면 안 된다.

    실제로 그런 출력이 있다 — `check_phishing_keywords` 의
    `WARN: OpenPhish fetch attempt 3 failed`. 그것까지 세면 게이트가 첫날부터
    잡음으로 red 다.
    """
    sample = (
        "  PASS: something\n"
        "WARN: OpenPhish fetch attempt 3 failed: OSError: simulated network error\n"
        "  [warn] 넓은 선언 — 성능 잡음일 뿐\n"
        # **위치 없이 범주 이름만 든 산문.** 첫 표본 셋은 `...Warning:` 토큰이 아예
        # 없어서, 위치 요구를 지워도 통과했다 — 되주입이 그것을 잡았다 (2026-09-21).
        # 판별의 근거가 '위치+줄 번호' 임을 실제로 재려면 이 줄이 있어야 한다.
        "  실패 사유를 요약하면 SyntaxWarning: invalid escape sequence 였다\n"
        "  ✗ case 2: DeprecationWarning: 옛 경로를 아직 부른다\n"
        "/repo/x.py:12: DeprecationWarning: old path\n"
        "=== 6/6 PASS ==="
    )
    found = extract(sample)
    ok = len(found) == 1 and found[0].category == "DeprecationWarning" and found[0].line == 12
    _record("case 1 (Python 경고만 뽑는다)", ok,
            "1건 추출 · 범주 이름만 든 산문 4줄 제외" if ok
            else f"뽑힌 것: {[w.render() for w in found]}")


def case_2_normalizes_volatile_fragments() -> None:
    """실행마다 달라지는 조각을 지운다 — 안 지우면 같은 경고가 매번 다른 문자열이다."""
    a = "/var/tmp/gate-abc123/check_x-q1w2/p.py:3: UserWarning: obj at 0x7f00aa11"
    b = "/var/tmp/gate-zzz999/check_x-e3r4/p.py:3: UserWarning: obj at 0x7fbb0099"
    ok = normalize(a) == normalize(b) and "<TMP>" in normalize(a) and "<ADDR>" in normalize(a)
    _record("case 2 (휘발성 조각 정규화)", ok,
            "tmp 경로·주소가 같은 키로 접힌다" if ok
            else f"정규화 후에도 갈린다:\n    {normalize(a)}\n    {normalize(b)}")


def case_3_classifies_origin() -> None:
    root = str(REPO_ROOT)
    cases = [
        (f"{root}/workflow-source/tests/check_x.py:12: DeprecationWarning: m", ORIGIN_REPO),
        (f"{root}/.venv/lib/python3.13/site-packages/p.py:9: UserWarning: m", ORIGIN_THIRD_PARTY),
        (f"{root}/.venv-interpreter-matrix/3.11/lib/python3.11/site-packages/q.py:1: UserWarning: m",
         ORIGIN_THIRD_PARTY),
        # `.venv` 조각이 **없는** 서드파티 경로. 위 두 표본은 둘 다 `.venv` 라
        # `_THIRD_PARTY_PARTS` 분기를 한 번도 안 밟았고, 그것을 망가뜨려도 case 가
        # 통과했다 — 되주입이 잡았다 (2026-09-21). 표본이 분기를 덮어야 한다.
        (f"{root}/workflow-source/build/lib/site-packages/r.py:5: UserWarning: m",
         ORIGIN_THIRD_PARTY),
        ("/usr/lib/python3.13/foo.py:3: DeprecationWarning: m", ORIGIN_THIRD_PARTY),
        ("<unknown>:93: SyntaxWarning: m", ORIGIN_UNATTRIBUTED),
    ]
    wrong = []
    for text, expected in cases:
        parsed = extract(text)
        actual = classify(parsed[0], root) if parsed else "(추출 실패)"
        if actual != expected:
            wrong.append(f"{text[:60]} → {actual} (기대 {expected})")
    _record("case 3 (출처 분류)", not wrong,
            f"{len(cases)}종 전부 일치" if not wrong else "; ".join(wrong))


def case_4_unattributed_is_gated() -> None:
    """`<unknown>` 을 서드파티로 밀면 **이 축을 만든 결함이 그대로 빠져나간다.**

    2026-09-21 의 `SyntaxWarning: invalid escape sequence` 위치가 정확히
    `<unknown>:93` 이었다 — 문자열을 `compile()` 한 결과라 파일 이름이 없다.
    """
    parsed = extract("<unknown>:93: SyntaxWarning: invalid escape sequence '\\`'")
    origin = classify(parsed[0], str(REPO_ROOT))
    _record("case 4 (귀속 불가도 게이트 대상)", origin in GATED_ORIGINS,
            f"{origin} ∈ {list(GATED_ORIGINS)}" if origin in GATED_ORIGINS
            else f"{origin} 은 게이트 대상이 아니다 — 82차 결함이 빠져나간다")


def case_5_third_party_is_not_gated() -> None:
    """서드파티를 red 로 만들면 우리가 못 고치는 만성 red 가 된다 (2026-08-10 실측).

    census 에서 두 해석기가 갈린 2건이 전부 이 부류였다.
    """
    parsed = extract(
        f"{REPO_ROOT}/.venv-interpreter-matrix/3.11/lib/python3.11/site-packages/"
        "pydantic_settings/sources/utils.py:47: IncompleteFieldDefinitionWarning: x"
    )
    origin = classify(parsed[0], str(REPO_ROOT))
    _record("case 5 (서드파티는 게이트 대상 아님)", origin not in GATED_ORIGINS,
            f"{origin} — 보고만 한다" if origin not in GATED_ORIGINS
            else "서드파티가 red 가 된다 — census 의 2건이 즉시 만성 red 다")


def case_6_runner_reds_on_repo_warning() -> None:
    """**end-to-end**: 검사가 exit 0 인데도 저장소 경고가 있으면 runner 가 red 다.

    선언만 보고 통과시키면 안 된다 — 게이트가 실제로 종료 코드를 바꾸는지가 이
    축의 전부다 (그러지 않으면 82차와 똑같이 '전부 green' 이 된다).
    """
    probe = SOURCE_ROOT / "tests" / "check_zzz_warning_probe.py"
    probe_src = (
        '#!/usr/bin/env python3\n'
        '"""임시 probe (check_warning_gate case 6) — 자신은 통과하면서 경고만 낸다."""\n'
        'WATCHES_ALL_REASON = "probe"\n'
        'import warnings\n'
        'warnings.warn("probe 가 낸 저장소 경고", DeprecationWarning, stacklevel=1)\n'
        'print("  probe: PASS")\n'
        'print("\\n1/1 passed")\n'
        'raise SystemExit(0)\n'
    )
    try:
        probe.write_text(probe_src, encoding="utf-8")
        proc = subprocess.run(
            [sys.executable, str(RUNNER), "--filter=zzz_warning_probe",
             "--no-meta-watch", "--json"],
            capture_output=True, text=True, timeout=120, cwd=str(REPO_ROOT),
            env={**os.environ, "PYTHONPATH": str(SOURCE_ROOT)},
        )
        data = json.loads(proc.stdout) if proc.stdout.strip() else {}
        gated = data.get("warnings", {}).get("gated", [])
        check_passed = data.get("failed", 1) == 0 and data.get("total", 0) == 1
        ok = proc.returncode != 0 and bool(gated) and check_passed
        _record(
            "case 6 (검사는 exit 0 인데 게이트가 red)", ok,
            f"runner exit {proc.returncode} · 게이트 경고 {len(gated)}건 · 검사 자신은 통과"
            if ok else
            f"runner exit {proc.returncode} · gated={gated} · total={data.get('total')} "
            f"failed={data.get('failed')}",
        )
    finally:
        probe.unlink(missing_ok=True)


def case_7_call_deprecated_asserts_the_warning() -> None:
    """의도한 deprecation 호출은 삼키되 **경고가 났는지 단언**한다.

    그냥 삼키면 '의도한 것' 과 '모르고 낸 것' 이 같은 모양이 된다.
    """
    def legacy() -> str:
        warnings.warn("옛 경로", DeprecationWarning, stacklevel=2)
        return "ok"

    def modern() -> str:
        return "ok"

    with warnings.catch_warnings(record=True) as leaked:
        warnings.simplefilter("always")
        got = call_deprecated(legacy)
    if got != "ok" or leaked:
        _record("case 7 (call_deprecated 계약)", False,
                f"반환 {got!r} · 밖으로 샌 경고 {len(leaked)}건 (0 이어야 한다)")
        return
    try:
        call_deprecated(modern)
    except AssertionError:
        _record("case 7 (call_deprecated 계약)", True,
                "경고를 삼키고 반환은 보존 · 경고가 없으면 단언 실패")
        return
    _record("case 7 (call_deprecated 계약)", False,
            "DeprecationWarning 을 내지 않는 함수도 통과시켰다 — 계약이 죽어 있다")


def main() -> int:
    print("=== 경고 게이트 계약 (TASK-2026-09-21-main-007) ===")
    for fn in (case_1_extracts_only_python_warnings,
               case_2_normalizes_volatile_fragments,
               case_3_classifies_origin,
               case_4_unattributed_is_gated,
               case_5_third_party_is_not_gated,
               case_6_runner_reds_on_repo_warning,
               case_7_call_deprecated_asserts_the_warning):
        try:
            fn()
        except Exception as exc:  # noqa: BLE001
            _record(fn.__name__, False, f"{type(exc).__name__}: {exc}")
    total = len(_passes) + len(_failures)
    print(f"\n{len(_passes)}/{total} passed")
    if _failures:
        for entry in _failures:
            print(f"  ✗ {entry}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
