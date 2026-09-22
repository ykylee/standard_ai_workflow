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
    "선언 하한 해석기로 **저장소 루트** 아래 git 추적 *.py 전수를 컴파일한다 — "
    "meta-watch 실측(2026-09-21) 566개 파일 접근. 입력 표면이 소스 트리 전체다"
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

from workflow_kit.common.python_floor import (  # noqa: E402
    declared_floor,
    iter_sources,
    packaged_declaration,
    probe,
    resolve_scope,
)

#: 컴파일 대상 루트와 하한 선언 파일. **저장소 루트** 다 — `workflow-source/` 로
#: 좁히면 그 밖의 git 추적 소스 8개를 조용히 안 잰다 (main-009).
COMPILE_ROOT, PYPROJECT = resolve_scope(REPO_ROOT)

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
    floor = declared_floor(PYPROJECT)
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
    # 열거는 `iter_sources` 하나다 — 여기 사본을 두면 실물 해석기 경로(case 2 의
    # 전수 측정)와 부분 측정이 **다른 집합** 을 재게 된다. 실제로 이 사본은
    # `.venv*` 제외가 빠져 있었다 (main-009).
    for path in iter_sources(COMPILE_ROOT):
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
    result = probe(COMPILE_ROOT, PYPROJECT)
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

    floor = declared_floor(PYPROJECT)
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

    **판정이 실행 인터프리터에 달려 있다** (2026-09-21 CI 실측으로 배웠다). PEP 701
    표본은 **3.12+ 에서만** `feature_version` 을 빠져나간다 — 3.11 이하에서는
    토크나이저가 그 문자열을 아예 못 읽어 `feature_version` 과 무관하게 거부된다.
    즉 `feature_version` 이 불충분한 것은 **실행 인터프리터가 하한보다 새로울 때**이고,
    그것이 바로 이 축이 존재하는 상황이다.

    처음엔 이 사실을 무조건으로 단언해서 로컬(3.13) green · CI(3.11) red 가 났다.
    호스트가 판정을 가르는 자리는 조건을 **명시**하고, 해당 없으면 통과로도 실패로도
    세지 않는다.
    """
    floor = declared_floor(PYPROJECT)
    if floor is None:
        _record("case 3 (feature_version 은 대체 불가)", False, "하한을 못 읽어 전제가 깨졌다")
        return

    def accepted(src: str) -> bool:
        try:
            ast.parse(src, feature_version=floor)
            return True
        except SyntaxError:
            return False

    # 대조군은 실행 버전과 무관하게 항상 성립해야 한다 — 수단 자체의 건전성.
    if accepted(_TYPE_ALIAS_SAMPLE):
        _record("case 3 (feature_version 은 대체 불가)", False,
                "feature_version 이 type alias 도 못 잡는다 — 이 수단 자체가 고장났다")
        return

    running = sys.version_info[:2]
    if running < (3, 12):
        # 실행 인터프리터가 PEP 701 을 아예 못 읽는다. 이 호스트에서는 표본으로
        # '대체 불가' 를 실증할 수 없다 — 해당 없음이지 통과가 아니다.
        _record(
            "case 3 (feature_version 은 대체 불가)",
            True,
            f"[해당 없음] 실행 {running[0]}.{running[1]} 은 PEP 701 을 토크나이저가 못 읽어 "
            f"표본으로 실증 불가 — 이 축이 겨냥하는 상황(실행 > 하한 {floor[0]}.{floor[1]})이 "
            "아니다. 대조군(type alias)은 정상 거부",
        )
        return

    if not accepted(_PEP701_SAMPLE):
        _record(
            "case 3 (feature_version 은 대체 불가)", False,
            f"실행 {running[0]}.{running[1]} 인데 feature_version 이 PEP 701 을 거부하기 "
            "시작했다 — 이 검사의 전제가 바뀌었다. 실물 해석기가 여전히 필요한지 다시 잴 것",
        )
        return

    _record(
        "case 3 (feature_version 은 대체 불가)", True,
        f"실행 {running[0]}.{running[1]} > 하한 {floor[0]}.{floor[1]} 에서 "
        "feature_version 이 PEP 701 을 통과시킨다(대체 불가) · type alias 는 거부(수단 정상)",
    )


def case_4_scope_is_derived_not_a_hand_list() -> None:
    """범위가 git 추적 `*.py` **전수** 인가 — 좁아지면 red.

    이 case 가 없으면 범위는 조용히 줄어든다. 실제로 그랬다 (main-009): 대상이
    `workflow-source/` 라 `main.py` · MCP 서버 스크립트 6종 ·
    `scripts/audit_mkdocs_links.py` **8개**가 밖에 있었고, 그중 MCP 서버 스크립트는
    실제로 배포·서빙된다. 결함이 0 이었던 것은 운이지 측정이 아니다.

    **좁아지는 쪽만 red 다.** 추적 밖 파일까지 컴파일하는 것은 범위가 *넓은* 것이라
    이 실패 모드가 아니다 (아직 `git add` 안 한 새 파일이 정확히 그것이다).
    """
    import subprocess
    proc = subprocess.run(["git", "ls-files", "*.py"],
                          cwd=REPO_ROOT, capture_output=True, text=True)
    if proc.returncode != 0:
        _record("case 4 (범위가 git 추적 전수와 일치)", False,
                f"git ls-files 실패: {proc.stderr.strip()[:160]}")
        return
    tracked = {line for line in proc.stdout.split() if line}
    swept = {str(path.relative_to(REPO_ROOT)) for path in iter_sources(COMPILE_ROOT)}
    missing = sorted(tracked - swept)
    extra = len(swept - tracked)
    _record(
        "case 4 (범위가 git 추적 전수와 일치)",
        not missing,
        f"git 추적 *.py {len(tracked)}개 전부 대상" + (f" (+추적 밖 {extra}건)" if extra else "")
        if not missing
        else f"추적되는데 범위 밖 {len(missing)}건 {missing[:3]} — 범위가 조용히 좁아졌다",
    )


def case_5_floor_comes_from_the_packaged_declaration() -> None:
    """하한 선언은 **배포되는 패키지** 의 것이다 — 루트 scaffold 가 아니다.

    main-009 가 컴파일 루트를 저장소 루트로 넓히면서 생긴 함정이다. 이 저장소의
    루트 `pyproject.toml` 은 배포되지 않는 placeholder scaffold 이고
    `requires-python = ">=3.13"` 을 선언한다 (의도된 불일치, 그 파일 머리말이 정본).
    루트를 넓히면서 **선언까지 루트로 옮기면** 하한이 3.10 → 3.13 으로 올라가고,
    개발 해석기가 이미 3.13 이라 **전부 통과하며 이 축이 아무것도 재지 않게 된다.**

    조용히 무력화되는 자리라 여기서 동결한다: 선택된 선언이 실제 패키지의 것이고,
    그것이 루트 scaffold 보다 **낮거나 같은** 하한을 말하는지 본다.
    """
    root_pyproject = REPO_ROOT / "pyproject.toml"
    packaged_path = packaged_declaration(REPO_ROOT)

    # **가장 먼저 이것을 본다.** 배포 패키지의 선언이 디스크에 있는데 다른 것을
    # 골랐다면 그것이 이 case 가 막는 결함이다. 되주입이 이 순서를 강제했다 —
    # 처음엔 '선택된 선언 == 루트 pyproject 면 소비 프로젝트' 로 봐서, 정작 선언이
    # 루트로 뒤바뀐 주입이 **[해당 없음]으로 통과**했다 (case 3 이 대신 터졌다).
    if packaged_path.is_file() and PYPROJECT.resolve() != packaged_path.resolve():
        _record("case 5 (하한 선언은 배포 패키지의 것)", False,
                f"배포 패키지 선언({packaged_path.relative_to(REPO_ROOT)})이 있는데 "
                f"{PYPROJECT} 를 골랐다 — 하한이 뒤바뀌면 이 축은 조용히 아무것도 재지 않는다")
        return
    if not packaged_path.is_file():
        _record("case 5 (하한 선언은 배포 패키지의 것)", True,
                "[해당 없음] 배포 패키지 pyproject 가 없다 (소비 프로젝트 형태)")
        return
    if not root_pyproject.is_file():
        _record("case 5 (하한 선언은 배포 패키지의 것)", True,
                "[해당 없음] 루트 pyproject 가 없다 — 선언이 갈릴 자리가 아니다")
        return

    packaged, scaffold = declared_floor(PYPROJECT), declared_floor(root_pyproject)
    if packaged is None:
        _record("하한 선언은 배포 패키지의 것", False,
                f"패키지 선언({PYPROJECT}) 에서 requires-python 을 못 읽었다")
        return
    if scaffold is not None and packaged > scaffold:
        _record("case 5 (하한 선언은 배포 패키지의 것)", False,
                f"선택된 하한 {packaged} 이 루트 scaffold {scaffold} 보다 높다 — "
                "선언 출처가 뒤바뀌었는지 확인하라. 하한이 올라가면 이 축은 조용히 "
                "아무것도 재지 않는다")
        return
    _record(
        "case 5 (하한 선언은 배포 패키지의 것)", True,
        f"선언 출처 {PYPROJECT.relative_to(REPO_ROOT)} → 하한 {packaged[0]}.{packaged[1]} "
        f"(루트 scaffold 는 {scaffold[0]}.{scaffold[1]} — 읽지 않는다)"
        if scaffold else
        f"선언 출처 {PYPROJECT.relative_to(REPO_ROOT)} → 하한 {packaged[0]}.{packaged[1]}",
    )


def case_6_ci_installs_the_floor_interpreter() -> None:
    """**CI 셀이 하한 해석기를 깐다** — 배선의 *부재* 를 잡는다 (main-007).

    되주입이 이 case 를 만들게 했다: `smoke.yml` 에서 하한 `setup-python` 단계를
    **통째로 지워도** 기존 검사는 9/9 PASS 였다. 리터럴 복제는 막고 있었지만
    배선이 사라지는 것은 아무도 안 봤다 — 그러면 CI 는 조용히 부분 측정으로
    떨어지고(PEP 701 부류를 못 본다) 게이트는 계속 green 이다.

    판정은 셋이다: ① prepare job 이 하한을 **선언에서** 파생해 출력하고
    ② 셀이 그 출력을 `setup-python` 에 바인딩하며 ③ 그 바인딩이 매트릭스 해석기
    바인딩보다 **먼저** 온다. ③이 계약인 이유: `setup-python` 은 PATH 앞에
    붙으므로 나중에 깐 것이 `python3` 을 차지한다. 순서가 뒤집히면 셀이 하한으로
    돌아 `--assert-running` 이 red 가 된다.
    """
    workflow = REPO_ROOT / ".github" / "workflows" / "smoke.yml"
    if not workflow.is_file():
        _record("case 6 (CI 가 하한 해석기를 깐다)", False, f"{workflow} 가 없다")
        return
    body = "\n".join(
        line for line in workflow.read_text(encoding="utf-8").splitlines()
        if not line.lstrip().startswith("#")
    )
    floor_binding = "${{ needs.prepare.outputs.python_floor }}"
    problems: list[str] = []
    if "python_floor:" not in body:
        problems.append("prepare job 이 python_floor 를 출력하지 않는다")
    if "--declared-floor" not in body:
        problems.append("하한을 선언에서 파생하는 호출(--declared-floor)이 없다")
    if floor_binding not in body:
        problems.append(f"셀이 하한을 setup-python 에 바인딩하지 않는다 ({floor_binding})")
    else:
        floor_at = body.index(floor_binding)
        matrix_binding = "${{ matrix.python }}"
        matrix_at = body.find(matrix_binding, body.index("jobs:"))
        # 매트릭스 바인딩은 `setup-python` 것만 본다 — job name 등에도 쓰이므로
        # 하한 바인딩 **뒤에** 오는 첫 등장으로 판정하면 순서를 오독한다.
        setup_matrix = body.find("python-version: " + matrix_binding)
        if setup_matrix == -1:
            problems.append("매트릭스 해석기 바인딩을 못 찾았다")
        elif floor_at > setup_matrix:
            problems.append(
                "하한 setup 이 매트릭스 setup **뒤에** 온다 — 나중에 깐 것이 "
                "python3 을 차지하므로 셀이 하한으로 돌게 된다"
            )
        _ = matrix_at
    _record(
        "case 6 (CI 가 하한 해석기를 깐다)",
        not problems,
        "prepare 가 선언에서 파생 → 셀이 매트릭스보다 먼저 바인딩"
        if not problems else "; ".join(problems),
    )


def main() -> int:
    print("=== 선언 하한 Python 문법 호환 (TASK-2026-09-21-main-005) ===")
    for fn in (case_1_floor_comes_from_the_declaration,
               case_2_real_interpreter_compiled_everything,
               case_3_feature_version_cannot_replace_it,
               case_4_scope_is_derived_not_a_hand_list,
               case_5_floor_comes_from_the_packaged_declaration,
               case_6_ci_installs_the_floor_interpreter):
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
