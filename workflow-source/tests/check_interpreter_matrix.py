#!/usr/bin/env python3
"""검사를 도는 **Python 해석기 축**의 정본 ↔ 로컬 재현 정합.

TASK-2026-09-21-main-006. 계약과 실측 근거는
`workflow_kit/common/interpreter_matrix.py` docstring 이 정본이다.

2026-09-21, `check_python_floor_syntax` case 3 이 **로컬 3.13 green / CI 3.11 red**
였다 (9915e4ad). 같은 모양을 저장소가 두 번 겪고 두 번 고쳤다 (`sdk_matrix`,
`branch_matrix`) — 이것이 세 번째 축이다.

이 축에서 특히 고약했던 것은 **한쪽 커버리지가 우연이었다**는 점이다. 3.13 은
아무 데도 선언돼 있지 않고 개발자 `.venv` 에 깔린 것에 기대고 있었다 — `.venv` 를
다시 만들면 조용히 사라진다. 그래서 두 해석기를 선언하고 `--run-local` 이 둘 다
밟는다.

2026-09-23 CI workflow 폐지(TASK-2026-09-23-main-022)로 CI 배선을 재던 case
다섯(`--github-matrix` 형태 · smoke.yml 주입 · yml 버전 리터럴 · 검사 workflow 파생
범위 · `--assert-running`)은 대상을 잃어 삭제했다.

검증 케이스 (4):
    1. registry 자체 정합 (버전 중복 없음, role 이 각각 정확히 하나)
    2. `dev-local` 선언이 `.python-version` 과 묶여 있다 (출처 대조)
    3. runner 가 검사를 `sys.executable` 로 띄운다 (축이 서는 기전의 동결)
    4. 선언된 해석기를 이 호스트에서 실제로 구할 수 있다 (로컬 재현 가능성)

Stdlib only.
"""

from __future__ import annotations

#: 전역 선언 (spec `core/test_impact_tiering_spec.md` §2). kit 전체가 import 표면이다
#: (`branch_matrix` 와 같은 이유 — import 는 transitively 닫힌다).
WATCHES = (
    "workflow-source/workflow_kit/*",
    # `workflow_kit/__init__` 이 `__version__` 을 여기서 파싱한다 — import 만 해도
    # 닿는다. meta-watch 실측(2026-09-21)이 선언 밖 접근으로 잡아냈다.
    "workflow-source/pyproject.toml",
    "workflow-source/tests/run_all_checks.py",
    ".python-version",
)

#: 이 검사가 강제하는 정본 요구 (spec `core/test_impact_tiering_spec.md` §7).
ENFORCES = ("check-interpreter-axis-is-declared-not-incidental",)

#: case 4 가 `uv python install` 로 해석기를 내려받을 수 있다 — 기본 60s 를 넘긴다.
CHECK_TIMEOUT_S = 150

import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from workflow_kit.common.interpreter_matrix import (  # noqa: E402
    GATE_INTERPRETERS,
    ROLE_CI_RUNNER,
    ROLE_DEV_LOCAL,
    declared_local_version,
    role_version,
    running_version,
    versions,
)

RUNNER = SOURCE_ROOT / "tests" / "run_all_checks.py"

_failures: list[str] = []
_passes: list[str] = []


def _record(case: str, ok: bool, detail: str = "") -> None:
    (_passes if ok else _failures).append(case if ok else f"{case}: {detail}")
    print(f"  {case}: {'PASS' if ok else 'FAIL'}{(' — ' + detail) if detail else ''}")


def case_1_registry_is_coherent() -> None:
    declared = versions()
    if len(set(declared)) != len(declared):
        _record("case 1 (registry 정합)", False, f"버전이 중복 선언됐다: {declared}")
        return
    if len(declared) < 2:
        _record("case 1 (registry 정합)", False,
                f"해석기가 {len(declared)}개다 — 축이 하나면 재는 것이 없다")
        return
    for role in (ROLE_CI_RUNNER, ROLE_DEV_LOCAL):
        matched = [i for i in GATE_INTERPRETERS if i.role == role]
        if len(matched) != 1:
            _record("case 1 (registry 정합)", False,
                    f"role {role!r} 이 {len(matched)}건이다 — 정확히 하나여야 한다")
            return
    missing = [i.version for i in GATE_INTERPRETERS if not (i.source and i.reason)]
    if missing:
        _record("case 1 (registry 정합)", False,
                f"출처/이유가 빈 선언: {missing} — 근거 없는 선언은 다음 사람이 못 고친다")
        return
    _record("case 1 (registry 정합)", True, f"선언 {list(declared)}")


def case_2_dev_local_is_tied_to_the_repo_pin() -> None:
    """`dev-local` 은 `.python-version` 과 묶여 있어야 한다.

    이 축을 만든 이유 자체가 "3.13 커버리지가 선언이 아니라 우연이었다" 다.
    registry 가 저장소의 실제 pin 과 갈라지면 같은 자리로 돌아간다.
    """
    pinned = declared_local_version(REPO_ROOT)
    declared = role_version(ROLE_DEV_LOCAL)
    if pinned is None:
        _record("case 2 (dev-local 이 .python-version 과 묶여 있다)", False,
                ".python-version 을 읽지 못했다 — 선언의 출처가 사라졌다")
        return
    _record(
        "case 2 (dev-local 이 .python-version 과 묶여 있다)",
        pinned == declared,
        f".python-version={pinned} · registry dev-local={declared}"
        + ("" if pinned == declared else " — 갈라졌다"),
    )


def case_3_runner_spawns_checks_with_sys_executable() -> None:
    """축이 서는 **기전**을 동결한다.

    runner 가 검사를 `sys.executable` 로 띄우기 때문에 "runner 를 다른 해석기로
    돌린다" 가 곧 축이 된다. 여기가 `"python3"` 같은 리터럴로 바뀌면 셀은 계속
    green 인 채로 축이 사라진다 — `--run-local` 의 venv 는 PATH 의 `python3` 과
    **우연히 같은 버전**일 수 있어 아무 데서도 안 보인다.
    """
    text = RUNNER.read_text(encoding="utf-8")
    spawn = re.search(r"\[\s*(sys\.executable|['\"][^'\"]+['\"])\s*,\s*str\(check_path\)", text)
    ok = bool(spawn) and spawn.group(1) == "sys.executable"
    _record("case 3 (runner 가 sys.executable 로 검사를 띄운다)", ok,
            "OK" if ok else
            f"검사 spawn 이 sys.executable 이 아니다: {spawn.group(1) if spawn else '패턴 자체를 못 찾았다'}")


def case_4_declared_interpreters_are_obtainable() -> None:
    """선언한 해석기를 이 호스트에서 **실제로 구할 수 있는가** (로컬 재현 가능성).

    긍정 증거로 판정한다 — "못 구했다" 는 통과가 아니라 미측정이다
    (`python_floor` 와 같은 규율). 구하지 못하는 환경(uv 도 그 해석기도 없다)
    에서는 무엇을 못 쟀는지와 어떻게 올리는지를 출력에 남긴다.
    """
    from workflow_kit.common.python_floor import find_interpreter

    obtained: list[str] = []
    unmeasured: list[str] = []
    for version in versions():
        if version == running_version():
            obtained.append(f"{version}(실행 중)")
            continue
        major, minor = (int(p) for p in version.split("."))
        path = find_interpreter((major, minor))
        if path is None:
            unmeasured.append(version)
            continue
        actual = subprocess.run(  # noqa: S603
            [path, "-c", "import sys;print('%d.%d'%sys.version_info[:2])"],
            capture_output=True, text=True, timeout=60,
        ).stdout.strip()
        if actual != version:
            _record("case 4 (선언된 해석기를 구할 수 있다)", False,
                    f"python{version} 로 얻은 것이 {actual} 다 ({path})")
            return
        obtained.append(f"{version}({path})")

    if unmeasured:
        for version in unmeasured:
            print(f"    [unmeasured] python{version} 를 구하지 못했다 — "
                  f"전수로 올리려면 `uv python install {version}`")
        print("    [unmeasured] 못 잰 것: 그 해석기의 로컬 재현 가능성 "
              "(`--run-local` 도 그 축을 미측정으로 보고한다)")
    _record(
        "case 4 (선언된 해석기를 구할 수 있다)",
        bool(obtained),
        f"구함 {obtained}" + (f" · 미측정 {unmeasured}" if unmeasured else " (선언 전부)"),
    )


def main() -> int:
    print("=== 해석기 매트릭스 정합 (TASK-2026-09-21-main-006) ===")
    for fn in (case_1_registry_is_coherent,
               case_2_dev_local_is_tied_to_the_repo_pin,
               case_3_runner_spawns_checks_with_sys_executable,
               case_4_declared_interpreters_are_obtainable):
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
