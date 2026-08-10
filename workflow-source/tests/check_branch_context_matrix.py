"""브랜치 컨텍스트 정본 ↔ CI ↔ 로컬 runner 정합 (TASK-2026-08-10-main-017).

TASK-016 이 실측한 대가: `check_release_pre_check_gates` case 7 이 slash 셀에서만
red 였고, **15연속 red 인 동안 로컬 전량 검사는 계속 green** 이었다. 결함이
어려워서가 아니라 로컬에 그 축을 밟을 방법이 없어서 열흘 가까이 걸렸다.

그래서 정본을 `workflow_kit/common/branch_matrix.py` 하나로 두고 CI 와 로컬이
같은 것을 읽게 했다. 이 검사는 **그 관계가 유지되는지** 를 잰다 — 셀 목록이
yml 로 복제되거나, runner 가 정본을 안 읽게 되면 비대칭이 조용히 돌아온다.

검증 케이스 (8):
    1. registry 자체 정합 (label 중복 없음, native 정확히 하나, 슬래시 셀 존재)
    2. `apply_context` 계약 — native 는 상속된 오버라이드까지 **지우고**,
       slash 는 최우선 키로 주입하며 상속을 이긴다
    3. `--github-matrix` 가 yml 의 fromJSON 이 먹는 형태다
    4. smoke.yml 이 prepare job 의 출력을 matrix 로 쓴다 (복제가 아니라 주입)
    5. smoke.yml 에 브랜치 문자열이 직접 적혀 있지 않다 (복제 검출)
    6. run_all_checks 가 `--branch-context` 를 정본에서 만든다
    7. runner 가 요청한 컨텍스트를 subprocess 에 **실제로** 주입한다 (end-to-end)
    8. `all` 이 선언된 컨텍스트 전부를 돈다 (목록이 줄면 잡힌다)

Stdlib only.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from workflow_kit.common.branch_matrix import (  # noqa: E402
    BRANCH_CONTEXTS,
    OVERRIDE_ENV_KEY,
    apply_context,
    context_for,
    github_matrix_json,
    labels,
)

SMOKE_YML = REPO_ROOT / ".github/workflows/smoke.yml"
RUNNER = SOURCE_ROOT / "tests" / "run_all_checks.py"
PROBE_FILTER = "release_pre_check"
"""end-to-end 케이스가 쓰는 check. 브랜치 컨텍스트에 따라 case 수가 갈리는 검사다
(native 14 / slash 13 + SKIP) — 그래서 주입이 실제로 먹었는지 관찰할 수 있다."""


def test_registry_is_coherent() -> None:
    names = labels()
    assert len(set(names)) == len(names), f"label 이 중복 선언됐다: {names}"

    natives = [ctx for ctx in BRANCH_CONTEXTS if not ctx.workflow_branch]
    assert len(natives) == 1, (
        f"덮지 않는 컨텍스트는 정확히 하나여야 한다 (현재 {len(natives)}건) — "
        "둘이면 같은 것을 두 번 재면서 셀이 늘었다고 착각한다"
    )

    slashed = [ctx for ctx in BRANCH_CONTEXTS if "/" in ctx.workflow_branch]
    assert slashed, (
        "슬래시가 든 브랜치 컨텍스트가 없다 — 중첩 디렉터리 경로를 밟는 셀이 "
        "사라지면 §2.55 류 결함이 다시 안 보이게 된다"
    )


def test_apply_context_contract() -> None:
    native = next(ctx for ctx in BRANCH_CONTEXTS if not ctx.workflow_branch)
    assert OVERRIDE_ENV_KEY not in apply_context({}, native), (
        "native 는 오버라이드를 넣으면 안 된다 — 빈 값을 넣으면 다음 env 키로 흘러가, "
        "'native 를 쟀다' 와 '빈 값이라 흘렀다' 가 같은 모양이 된다"
    )
    # 상속된 오버라이드를 **지운다**. 안 지우면 native 를 명시적으로 요청해도
    # 부모 값이 이겨서 다른 축을 잰다 (첫 구현의 실제 결함).
    inherited = {OVERRIDE_ENV_KEY: "feature/somewhere-else", "KEEP": "1"}
    applied = apply_context(inherited, native)
    assert OVERRIDE_ENV_KEY not in applied, (
        f"native 가 상속된 {OVERRIDE_ENV_KEY} 를 안 지운다 — 요청한 컨텍스트와 "
        f"다른 것을 재게 된다 (applied={applied})"
    )
    assert applied["KEEP"] == "1", "관계 없는 env 까지 지웠다"
    assert inherited[OVERRIDE_ENV_KEY] == "feature/somewhere-else", "원본 env 를 변형했다"

    for ctx in BRANCH_CONTEXTS:
        if not ctx.workflow_branch:
            continue
        assert apply_context({}, ctx)[OVERRIDE_ENV_KEY] == ctx.workflow_branch, (
            f"{ctx.label} 의 주입이 정본 키({OVERRIDE_ENV_KEY})를 안 쓴다"
        )
        assert apply_context(inherited, ctx)[OVERRIDE_ENV_KEY] == ctx.workflow_branch, (
            f"{ctx.label} 이 상속된 오버라이드를 못 이긴다"
        )


def test_github_matrix_shape() -> None:
    parsed = json.loads(github_matrix_json())
    assert isinstance(parsed, list) and parsed, "매트릭스가 비어 있다"
    assert len(parsed) == len(BRANCH_CONTEXTS), (
        f"매트릭스 {len(parsed)}셀 ≠ 선언 {len(BRANCH_CONTEXTS)}건"
    )
    for cell in parsed:
        assert set(cell) == {"label", "workflow_branch"}, (
            f"셀 키가 yml 이 읽는 것과 다르다: {sorted(cell)}"
        )


def test_smoke_yml_consumes_registry() -> None:
    text = SMOKE_YML.read_text(encoding="utf-8")
    assert "workflow_kit.common.branch_matrix --github-matrix" in text, (
        "smoke.yml 이 정본에서 컨텍스트 목록을 받지 않는다"
    )
    assert "fromJSON(needs.prepare.outputs.contexts)" in text, (
        "smoke.yml 이 prepare job 의 출력을 matrix 로 쓰지 않는다"
    )


def test_smoke_yml_does_not_duplicate_branches() -> None:
    text = SMOKE_YML.read_text(encoding="utf-8")
    # 주석은 뺀다 — 설명에 브랜치 이름이 나오는 것은 복제가 아니다.
    body = "\n".join(
        line for line in text.splitlines() if not line.lstrip().startswith("#")
    )
    leaked = [
        ctx.workflow_branch for ctx in BRANCH_CONTEXTS
        if ctx.workflow_branch and ctx.workflow_branch in body
    ]
    assert not leaked, (
        f"smoke.yml 에 브랜치 문자열이 직접 적혀 있다: {leaked} — "
        "복제하면 갈라지고, 갈라진 쪽이 조용히 이긴다 (정본: branch_matrix.py)"
    )


def test_runner_declares_contexts_from_registry() -> None:
    help_text = subprocess.run(
        [sys.executable, str(RUNNER), "--help"],
        capture_output=True, text=True, timeout=60,
        env={**os.environ, "PYTHONPATH": str(SOURCE_ROOT)},
    ).stdout
    assert "--branch-context" in help_text, "runner 에 --branch-context 가 없다"
    for label in labels():
        assert label in help_text, (
            f"runner 의 선언 목록에 {label!r} 가 없다 — 정본에서 만들지 않는 것이다"
        )


def _run_probe(*extra: str) -> str:
    proc = subprocess.run(
        [sys.executable, str(RUNNER), f"--filter={PROBE_FILTER}", "--json", *extra],
        capture_output=True, text=True, timeout=300,
        env={**os.environ, "PYTHONPATH": str(SOURCE_ROOT)},
    )
    return proc.stdout


def test_runner_actually_injects_context() -> None:
    """요청한 컨텍스트가 subprocess 까지 닿는가 (end-to-end).

    선언만 보고 통과시키면 안 된다 — 주입이 조용히 안 먹는 것이 정확히 CI 가
    `RESOLVED != OVERRIDE` 로 잡으려던 실패 양상이다.
    """
    slash = context_for("slash")
    assert slash is not None, "slash 컨텍스트가 사라졌다"

    data = json.loads(_run_probe("--branch-context=slash"))
    assert data["total"] == 1, f"probe check 를 못 찾았다: total={data['total']}"
    last_line = data["results"][0]["last_line"]
    # slash 는 state.json 이 없어 7b 가 SKIP → case 수가 native 보다 하나 적다.
    assert "13/13" in last_line, (
        f"slash 컨텍스트가 주입되지 않았다 (last_line={last_line!r}) — "
        "native 라면 14/14 가 나온다"
    )

    native = json.loads(_run_probe("--branch-context=native"))
    native_line = native["results"][0]["last_line"]
    assert "14/14" in native_line, (
        f"native 가 14/14 가 아니다 (last_line={native_line!r})"
    )


def test_all_runs_every_declared_context() -> None:
    data = json.loads(_run_probe("--branch-context=all"))
    assert "contexts" in data, "all 모드가 컨텍스트별 결과를 내지 않는다"
    seen = [entry["label"] for entry in data["contexts"]]
    assert seen == list(labels()), (
        f"all 이 돈 컨텍스트 {seen} ≠ 선언 {list(labels())} — "
        "선언을 늘려도 로컬 재현이 따라오지 않으면 비대칭이 돌아온다"
    )


def main() -> int:
    test_funcs = [
        test_registry_is_coherent,
        test_apply_context_contract,
        test_github_matrix_shape,
        test_smoke_yml_consumes_registry,
        test_smoke_yml_does_not_duplicate_branches,
        test_runner_declares_contexts_from_registry,
        test_runner_actually_injects_context,
        test_all_runs_every_declared_context,
    ]
    failures: list[tuple[str, str]] = []
    for func in test_funcs:
        try:
            func()
            print(f"  PASS: {func.__name__}")
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
