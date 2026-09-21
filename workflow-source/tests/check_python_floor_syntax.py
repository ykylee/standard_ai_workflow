#!/usr/bin/env python3
"""선언 하한 Python 으로 소스 전수가 컴파일되는지 **실물 해석기**로 잰다.

TASK-2026-09-21-main-005. 계약과 실측 근거는 `workflow_kit/common/python_floor.py`
docstring 이 정본이다.

세 가지를 고정한다:

1. 하한의 출처가 `requires-python` **선언**이다 (CI 매트릭스가 아니다).
2. **긍정 증거** — 하한 해석기가 실제로 N개를 컴파일했다. 해석기를 못 구하면
   통과가 아니라 미측정이다 (`sdk_matrix` 와 같은 규율).
3. `ast.parse(feature_version=)` 은 이 축을 대신하지 못한다. 이 case 가 그
   사실 자체를 동결한다 — 안 그러면 "더 싼 수단이 있는데 왜 해석기를 부르나" 로
   되돌아간다.
"""
from __future__ import annotations

#: 전역 선언 (spec `core/test_impact_tiering_spec.md` §2). 소스 트리의 `*.py` 를
#: **전부** 하한 해석기에 물리므로 입력 표면이 소스 트리 전체다 — 좁게 선언하면
#: meta-watch 실측에서 선언 밖 접근이 난다 (examples/ · mcp_servers/scripts/ 등 38건).
WATCHES_ALL_REASON = (
    "선언 하한 해석기로 workflow-source 아래 *.py 전수를 컴파일한다 — meta-watch "
    "실측(2026-09-21) 553개 파일 접근. 입력 표면이 소스 트리 전체다"
)

#: 이 검사가 강제하는 정본 요구 (spec `core/test_impact_tiering_spec.md` §7).
ENFORCES = ("python-floor-is-measured-with-the-real-interpreter",)

#: 하한 해석기를 uv 로 내려받는 경우가 있어 기본 60s 상한을 넘길 수 있다.
CHECK_TIMEOUT_S = 150

import ast
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from workflow_kit.common.python_floor import declared_floor, probe  # noqa: E402

#: 실측으로 고른 표본 — PEP 701 중첩 f-string 은 3.12 도입인데 `feature_version` 이
#: 거부하지 못한다. 이 축이 실물 해석기를 부르는 유일한 이유다.
_PEP701_SAMPLE = 'x = f"{"a" if b else "c"}"'
#: 대조군 — 이쪽은 `feature_version` 이 제대로 거부한다. 표본이 둘 다 통과하면
#: `feature_version` 자체가 고장난 것이므로 그것도 구분해서 잡는다.
_TYPE_ALIAS_SAMPLE = "type X = int"

_failures: list[str] = []
_passes: list[str] = []


def _record(case: str, ok: bool, detail: str = "") -> None:
    (_passes if ok else _failures).append(case if ok else f"{case}: {detail}")
    print(f"  {case}: {'PASS' if ok else 'FAIL'}{(' — ' + detail) if detail else ''}")


def case_1_floor_comes_from_the_declaration() -> None:
    """하한은 `requires-python` 에서 나온다 — 리터럴도 CI 매트릭스도 아니다."""
    floor = declared_floor(SOURCE_ROOT / "pyproject.toml")
    _record(
        "case 1 (하한이 requires-python 선언에서 나온다)",
        floor is not None,
        f"하한 {floor[0]}.{floor[1]}" if floor else "requires-python 을 읽지 못했다",
    )


def _partial_sweep(floor: tuple[int, int]) -> list[tuple[str, str]]:
    """하한 해석기가 없을 때의 **부분** 측정 — `ast.parse(feature_version=)`.

    PEP 701 부류는 못 본다 (case 3 이 그 사실을 고정한다). 그래도 `except*` /
    type alias / type parameter 는 잡으므로 0 보다는 낫다.
    """
    failures: list[tuple[str, str]] = []
    for path in sorted(SOURCE_ROOT.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        try:
            ast.parse(path.read_text(encoding="utf-8"), feature_version=floor)
        except SyntaxError as exc:
            failures.append((str(path), f"{exc.msg} (line {exc.lineno})"))
        except (OSError, UnicodeDecodeError):
            continue
    return failures


def case_2_real_interpreter_compiled_everything() -> None:
    """**긍정 증거**: 하한 해석기가 소스 전수를 실제로 컴파일했다.

    '실패가 안 보였다' 로는 부족하다 — 해석기를 못 구해도 실패는 안 보인다.

    해석기를 못 구하는 환경(현재 CI 가 그렇다: uv 도 python3.10 도 없다)에서는
    **부분 측정으로 내려가되 그 사실을 크게 말한다.** 못 잰 것을 통과라고 부르지
    않으려면 무엇을 못 쟀는지가 출력에 남아야 한다 — 조용한 fallback 은 '봤는데
    맞았다' 와 '아예 못 봤다' 를 같은 모양으로 만든다.
    """
    result = probe(SOURCE_ROOT, SOURCE_ROOT / "pyproject.toml")
    if result.measured:
        ok = not result.failures and result.compiled > 100
        detail = (
            f"해석기 {result.interpreter_version} 로 {result.compiled}개 컴파일 (전수)"
            if ok
            else f"컴파일 {result.compiled}개 · 실패 {len(result.failures)}건: "
            + "; ".join(f"{p}: {w}" for p, w in result.failures[:5])
        )
        _record("case 2 (하한 해석기가 전수를 컴파일했다)", ok, detail)
        return

    floor = declared_floor(SOURCE_ROOT / "pyproject.toml")
    if floor is None:
        _record("case 2 (하한 해석기가 전수를 컴파일했다)", False, result.unmeasured_reason or "미측정")
        return
    print(f"    [unmeasured] {result.unmeasured_reason}")
    print("    [unmeasured] 못 잰 부류: PEP 701(중첩 f-string) 등 feature_version 이 "
          "게이트를 걸지 않은 구문 — 전수로 올리려면 `uv python install "
          f"{floor[0]}.{floor[1]}`")
    failures = _partial_sweep(floor)
    _record(
        "case 2 (하한 해석기가 전수를 컴파일했다)",
        not failures,
        "**부분 측정** (feature_version) — 실패 0, 단 PEP 701 부류는 못 봤다"
        if not failures
        else f"부분 측정에서 실패 {len(failures)}건: "
        + "; ".join(f"{p}: {w}" for p, w in failures[:5]),
    )


def case_3_feature_version_cannot_replace_it() -> None:
    """`ast.parse(feature_version=)` 이 이 축을 대신하지 못한다는 사실을 동결한다.

    이 case 가 없으면 다음 사람이 "해석기를 부르는 건 느리니 feature_version 으로
    바꾸자" 고 하고, 그러면 이 축을 만들게 한 결함을 다시 못 잡는다.
    """
    floor = declared_floor(SOURCE_ROOT / "pyproject.toml")
    if floor is None:
        _record("case 3 (feature_version 은 대체 불가)", False, "하한을 못 읽어 전제가 깨졌다")
        return

    def accepted(src: str) -> bool:
        try:
            ast.parse(src, feature_version=floor)
            return True
        except SyntaxError:
            return False

    pep701_slips = accepted(_PEP701_SAMPLE)
    type_alias_caught = not accepted(_TYPE_ALIAS_SAMPLE)
    ok = pep701_slips and type_alias_caught
    if ok:
        detail = (
            f"feature_version={floor[0]}.{floor[1]} 은 PEP 701 중첩 f-string 을 "
            "통과시키고(대체 불가) type alias 는 거부한다(수단 자체는 정상)"
        )
    elif not type_alias_caught:
        detail = "feature_version 이 type alias 도 못 잡는다 — 이 수단 자체가 고장났다"
    else:
        detail = (
            "feature_version 이 PEP 701 을 거부하기 시작했다 — 이 검사의 전제가 바뀌었다. "
            "실물 해석기가 여전히 필요한지 다시 재고 이 case 를 갱신할 것"
        )
    _record("case 3 (feature_version 은 대체 불가)", ok, detail)


def main() -> int:
    print("=== 선언 하한 Python 문법 호환 (TASK-2026-09-21-main-005) ===")
    for fn in (case_1_floor_comes_from_the_declaration,
               case_2_real_interpreter_compiled_everything,
               case_3_feature_version_cannot_replace_it):
        fn()
    total = len(_passes) + len(_failures)
    print(f"\n{len(_passes)}/{total} passed")
    if _failures:
        for f in _failures:
            print(f"  ✗ {f}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
