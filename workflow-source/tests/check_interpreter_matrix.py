#!/usr/bin/env python3
"""검사를 도는 **Python 해석기 축**의 정본 ↔ CI ↔ 로컬 재현 정합.

TASK-2026-09-21-main-006. 계약과 실측 근거는
`workflow_kit/common/interpreter_matrix.py` docstring 이 정본이다.

2026-09-21, `check_python_floor_syntax` case 3 이 **로컬 3.13 green / CI 3.11 red**
였다 (9915e4ad). 같은 모양을 저장소가 두 번 겪고 두 번 고쳤다 (`sdk_matrix`,
`branch_matrix`) — 이것이 세 번째 축이다.

이 축에서 특히 고약했던 것은 **한쪽 커버리지가 우연이었다**는 점이다. 3.13 은
아무 데도 선언돼 있지 않고 개발자 `.venv` 에 깔린 것에 기대고 있었다 — `.venv` 를
다시 만들면 조용히 사라진다. 그래서 두 해석기를 선언하고 CI 가 둘 다 밟는다.

검증 케이스 (9):
    1. registry 자체 정합 (버전 중복 없음, role 이 각각 정확히 하나)
    2. `dev-local` 선언이 `.python-version` 과 묶여 있다 (출처 대조)
    3. `--github-matrix` 가 yml 의 fromJSON 이 먹는 형태다
    4. smoke.yml 이 registry 에서 해석기를 주입한다 (복제가 아니라 주입)
    5. smoke.yml 에 해석기 버전이 직접 적혀 있지 않다 (복제 검출)
    6. **파생 범위** — 검사를 돌리는 workflow 전부가 축을 밟거나 면제 선언이 있다
    7. `--assert-running` 이 긍정 증거다 (불일치·미선언을 거부한다)
    8. runner 가 검사를 `sys.executable` 로 띄운다 (축이 서는 기전의 동결)
    9. 선언된 해석기를 이 호스트에서 실제로 구할 수 있다 (로컬 재현 가능성)

Stdlib only.
"""

from __future__ import annotations

#: 전역 선언 (spec `core/test_impact_tiering_spec.md` §2). kit 전체가 import 표면이고
#: (`branch_matrix` 와 같은 이유 — import 는 transitively 닫힌다), CI workflow 전부를
#: 훑어 범위를 파생하므로 `.github/workflows/*` 도 입력이다.
WATCHES = (
    "workflow-source/workflow_kit/*",
    # `workflow_kit/__init__` 이 `__version__` 을 여기서 파싱한다 — import 만 해도
    # 닿는다. meta-watch 실측(2026-09-21)이 선언 밖 접근으로 잡아냈다.
    "workflow-source/pyproject.toml",
    "workflow-source/tests/run_all_checks.py",
    ".github/workflows/*",
    ".python-version",
)

#: 이 검사가 강제하는 정본 요구 (spec `core/test_impact_tiering_spec.md` §7).
ENFORCES = ("check-interpreter-axis-is-declared-not-incidental",)

#: case 9 가 `uv python install` 로 해석기를 내려받을 수 있다 — 기본 60s 를 넘긴다.
CHECK_TIMEOUT_S = 150

import json
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from workflow_kit.common.interpreter_matrix import (  # noqa: E402
    AXIS_EXEMPT_WORKFLOWS,
    GATE_INTERPRETERS,
    ROLE_CI_RUNNER,
    ROLE_DEV_LOCAL,
    assert_running,
    declared_local_version,
    github_matrix_json,
    role_version,
    running_version,
    versions,
)

WORKFLOW_DIR = REPO_ROOT / ".github" / "workflows"
SMOKE_YML = WORKFLOW_DIR / "smoke.yml"
RUNNER = SOURCE_ROOT / "tests" / "run_all_checks.py"
REGISTRY_CONSUMER = "workflow_kit.common.interpreter_matrix --github-matrix"

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


def case_3_github_matrix_shape() -> None:
    parsed = json.loads(github_matrix_json())
    ok = (isinstance(parsed, list) and parsed == list(versions())
          and all(isinstance(v, str) for v in parsed))
    _record("case 3 (github-matrix 형태)", ok,
            f"{parsed}" if ok else f"yml 이 먹는 형태가 아니다: {parsed!r}")


def case_4_smoke_yml_consumes_registry() -> None:
    """registry → prepare → matrix → setup-python 배선이 **끊기지 않았는가**.

    첫 구현은 파일 전체에서 `matrix.python` 문자열을 찾았는데, job 이름과 artifact
    이름에도 그것이 들어 있어 **정작 setup-python 의 배선을 끊어도 통과**했다
    (되주입 실측 2026-09-21). 판정을 배선 자체로 옮긴다 — `python-version:` 이
    받는 값을 전부 보고, 하나라도 매트릭스가 아니면 red 다.
    """
    text = SMOKE_YML.read_text(encoding="utf-8")
    body = "\n".join(line for line in text.splitlines()
                     if not line.lstrip().startswith("#"))
    missing = [needle for needle in
               (REGISTRY_CONSUMER, "fromJSON(needs.prepare.outputs.interpreters)")
               if needle not in body]
    if missing:
        _record("case 4 (smoke.yml 이 registry 를 주입받는다)", False,
                f"없는 배선: {missing}")
        return
    bound = re.findall(r"python-version:\s*(.+)$", body, re.MULTILINE)
    stray = [value.strip() for value in bound
             if value.strip() != "${{ matrix.python }}"]
    _record("case 4 (smoke.yml 이 registry 를 주입받는다)",
            bool(bound) and not stray,
            f"setup-python {len(bound)}곳 전부 매트릭스에서 받는다" if bound and not stray
            else (f"매트릭스에서 안 받는 python-version: {stray}" if stray
                  else "python-version 바인딩이 하나도 없다 — 배선이 통째로 사라졌다"))


def case_5_smoke_yml_does_not_hardcode_versions() -> None:
    """버전 문자열의 복제를 잡는다. 복제하면 갈라지고, 갈라진 쪽이 조용히 이긴다."""
    body = "\n".join(
        line for line in SMOKE_YML.read_text(encoding="utf-8").splitlines()
        if not line.lstrip().startswith("#")
    )
    literals = re.findall(r"""python-version:\s*["']?(\d+\.\d+)["']?""", body)
    _record("case 5 (smoke.yml 에 버전 리터럴이 없다)", not literals,
            "OK — setup-python 이 매트릭스에서 받는다" if not literals
            else f"직접 적힌 python-version: {literals} (정본: interpreter_matrix.py)")


def case_6_every_check_running_workflow_is_on_the_axis() -> None:
    """**범위를 파생한다** — 포함 목록은 그 밖이 조용히 갈라진다.

    2026-09-21 에 같은 모양을 두 번 만났다 (smoke 수 주장 / 어휘 범위). 그래서
    "축을 밟는 workflow 목록" 을 손으로 두지 않고, `run_all_checks.py` 를 부르는
    workflow 를 디스크에서 파생한 뒤 그중 registry 도 안 읽고 면제 선언도 없는
    것을 red 로 잡는다.
    """
    runners: list[str] = []
    for path in sorted(WORKFLOW_DIR.glob("*.yml")):
        if "run_all_checks.py" in path.read_text(encoding="utf-8"):
            runners.append(path.name)
    if not runners:
        _record("case 6 (검사를 돌리는 workflow 전부가 축 위에 있다)", False,
                "run_all_checks.py 를 부르는 workflow 를 하나도 못 찾았다 — 파생이 고장났다")
        return
    uncovered = []
    for name in runners:
        text = (WORKFLOW_DIR / name).read_text(encoding="utf-8")
        if REGISTRY_CONSUMER in text:
            continue
        if name in AXIS_EXEMPT_WORKFLOWS:
            continue
        uncovered.append(name)
    _record(
        "case 6 (검사를 돌리는 workflow 전부가 축 위에 있다)",
        not uncovered,
        f"파생 {runners} · 면제 {sorted(AXIS_EXEMPT_WORKFLOWS)}" if not uncovered
        else f"축도 안 밟고 면제 선언도 없는 workflow: {uncovered}",
    )


def case_7_assert_running_is_positive_evidence() -> None:
    """`--assert-running` 이 실제로 거른다. 늘 0 을 내면 CI 의 증거가 사라진다."""
    here = running_version()
    other = next((v for v in versions() if v != here), None)
    if assert_running(here) != 0:
        _record("case 7 (--assert-running 이 긍정 증거)", False,
                f"실행 중인 해석기 {here} 를 스스로 거부했다")
        return
    if other is not None and assert_running(other) == 0:
        _record("case 7 (--assert-running 이 긍정 증거)", False,
                f"{here} 로 돌면서 {other} 선언을 통과시켰다 — 판정이 죽어 있다")
        return
    if assert_running("2.7") == 0:
        _record("case 7 (--assert-running 이 긍정 증거)", False,
                "미선언 버전(2.7)을 통과시켰다")
        return
    _record("case 7 (--assert-running 이 긍정 증거)", True,
            f"{here} 일치 통과 · {other} 불일치 거부 · 미선언 거부")


def case_8_runner_spawns_checks_with_sys_executable() -> None:
    """축이 서는 **기전**을 동결한다.

    runner 가 검사를 `sys.executable` 로 띄우기 때문에 "runner 를 다른 해석기로
    돌린다" 가 곧 축이 된다. 여기가 `"python3"` 같은 리터럴로 바뀌면 셀은 계속
    green 인 채로 축이 사라진다 — CI 에서는 `setup-python` 이 PATH 를 앞에 깔아
    **우연히 같은 버전**이라 아무 데서도 안 보인다.
    """
    text = RUNNER.read_text(encoding="utf-8")
    spawn = re.search(r"\[\s*(sys\.executable|['\"][^'\"]+['\"])\s*,\s*str\(check_path\)", text)
    ok = bool(spawn) and spawn.group(1) == "sys.executable"
    _record("case 8 (runner 가 sys.executable 로 검사를 띄운다)", ok,
            "OK" if ok else
            f"검사 spawn 이 sys.executable 이 아니다: {spawn.group(1) if spawn else '패턴 자체를 못 찾았다'}")


def case_9_declared_interpreters_are_obtainable() -> None:
    """선언한 해석기를 이 호스트에서 **실제로 구할 수 있는가** (로컬 재현 가능성).

    긍정 증거로 판정한다 — "못 구했다" 는 통과가 아니라 미측정이다
    (`python_floor` 와 같은 규율). 구하지 못하는 환경(현재 CI: uv 도 3.13 도 없다)
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
            _record("case 9 (선언된 해석기를 구할 수 있다)", False,
                    f"python{version} 로 얻은 것이 {actual} 다 ({path})")
            return
        obtained.append(f"{version}({path})")

    if unmeasured:
        for version in unmeasured:
            print(f"    [unmeasured] python{version} 를 구하지 못했다 — "
                  f"전수로 올리려면 `uv python install {version}`")
        print("    [unmeasured] 못 잰 것: 그 해석기의 로컬 재현 가능성. "
              "CI 셀 자체는 setup-python 이 보장한다")
    _record(
        "case 9 (선언된 해석기를 구할 수 있다)",
        bool(obtained),
        f"구함 {obtained}" + (f" · 미측정 {unmeasured}" if unmeasured else " (선언 전부)"),
    )


def main() -> int:
    print("=== 해석기 매트릭스 정합 (TASK-2026-09-21-main-006) ===")
    for fn in (case_1_registry_is_coherent,
               case_2_dev_local_is_tied_to_the_repo_pin,
               case_3_github_matrix_shape,
               case_4_smoke_yml_consumes_registry,
               case_5_smoke_yml_does_not_hardcode_versions,
               case_6_every_check_running_workflow_is_on_the_axis,
               case_7_assert_running_is_positive_evidence,
               case_8_runner_spawns_checks_with_sys_executable,
               case_9_declared_interpreters_are_obtainable):
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
