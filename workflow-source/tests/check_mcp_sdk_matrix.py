"""선언한 mcp SDK 버전 정책이 **실제 CI 와 같은 것을 말하는가** (TASK-2026-07-31-main-001).

## 왜 필요한가

CI 가 mcp 1.x 와 2.x 를 동시에 밟은 것은 설계가 아니라 설치 순서였다. `smoke` 는
`requirements-dev.txt` 의 고정 핀이 editable install *뒤에* 깔려 되돌리기 때문에 1.x 로
돌고, `mypy-strict` / `mcp-inspector` 는 그 파일을 안 깔아 상한 없는 extra 가 최신을
집는다. **그 한 줄을 지우면 1.x 커버리지가 조용히 사라지는데 아무 검사도 실패하지
않았다.**

정본(`workflow_kit/common/sdk_matrix.py`)을 만드는 것만으로는 이 문제가 안 풀린다.
선언은 사실이 아니라 주장이라서, 선언과 실제 파일이 갈라지면 **선언 쪽이 조용히
이긴다** (§2.35 의 "관측하지 않은 값을 관측한 것처럼" 과 같은 모양). 그래서 이 검사가
정본과 세 표면을 묶는다:

- `requirements-dev.txt` 의 핀 ↔ registry 의 floor
- `pyproject.toml` 의 `mcp-sdk` extra 상한 ↔ registry 의 floating 선언
- `.github/workflows/*.yml` ↔ registry 의 workflow 정책 (**양방향**)

## 계약

1. registry 자체가 말이 된다 — floor 는 정확히 하나, 버전은 중복 없고, 근거가 비어
   있지 않으며, **1.x 와 2.x 를 둘 다** 포함한다 (이 matrix 의 존재 이유다).
2. registry 의 floor 가 `requirements-dev.txt` 의 핀과 같다.
3. `mcp-sdk` extra 에 상한이 없다 — floating 이라고 선언한 job 이 실제로 부동이다.
4. registry 가 아는 workflow 는 전부 실재하고, `--record` 로 실측을 남긴다.
5. **역방향**: mcp 를 설치하는 workflow 중 정책이 선언 안 된 것이 없다. 새 job 이
   조용히 늘어나는 것이 이 결함의 원래 모양이었다.
6. matrix workflow 는 버전 목록을 `--github-matrix` 로 받고 **버전 문자열을 직접 적지
   않는다**. 복제는 반드시 갈라진다.
7. matrix workflow 는 "깔렸는가"(`--assert-installed`)와 "그것으로 실제로
   쟀는가"(`--assert-not-skipped`)를 **둘 다** 본다.
8. 판정 함수가 실제로 걸린다 — 어긋난 버전, 미설치, skip 한 검사, 정책 없는 workflow
   네 가지를 되주입해 각각 다른 신호로 실패하는지 본다.

Cross-ref: TASK-2026-07-31-main-001, releases/Beta-v1.0.0.md §2.45.
"""

from __future__ import annotations

import json
import re
import sys
import tomllib
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SOURCE_ROOT.parent
sys.path.insert(0, str(SOURCE_ROOT))

from workflow_kit.common.sdk_matrix import (  # noqa: E402
    PINNED_VERSIONS,
    POLICY_FLOATING,
    POLICY_MATRIX,
    POLICY_PINNED,
    ROLE_FLOOR,
    SDK_EXERCISING_CHECKS,
    WORKFLOW_POLICIES,
    _assert_installed,
    judge_exercised,
    floor_version,
    github_matrix_json,
    pinned_versions,
    render_record,
)

MATRIX_FILTER = ("mcp", "optional_dep")
"""matrix workflow 가 `run_all_checks --filter` 에 넘기는 값. 아래 완전성 검사가 쓴다."""

WORKFLOW_DIR = REPO_ROOT / ".github/workflows"
REQUIREMENTS_DEV = REPO_ROOT / "requirements-dev.txt"
PYPROJECT_PATH = SOURCE_ROOT / "pyproject.toml"
MODULE_CLI = "workflow_kit.common.sdk_matrix"

_skipped: list[str] = []


def _workflow_text(name: str) -> str:
    return (WORKFLOW_DIR / f"{name}.yml").read_text(encoding="utf-8")


def _installs_mcp(text: str) -> bool:
    """그 workflow 가 mcp 를 깔고 도는가 (extra 또는 배포판 직접 설치)."""
    return "mcp-sdk]" in text or "mcp[cli]" in text


def _pinned_requirement(text: str, distribution: str) -> str | None:
    match = re.search(rf"^{re.escape(distribution)}(?:\[[^\]]*\])?==([^\s#]+)", text, re.MULTILINE)
    return match.group(1) if match else None


def test_registry_is_coherent() -> None:
    versions = pinned_versions()
    assert len(set(versions)) == len(versions), f"버전이 중복 선언됐다: {versions}"

    floors = [pinned for pinned in PINNED_VERSIONS if pinned.role == ROLE_FLOOR]
    assert len(floors) == 1, (
        f"floor role 은 정확히 하나여야 한다 (현재 {len(floors)}건) — "
        "하한이 둘이면 어느 쪽이 하한인지 아무도 모른다"
    )

    for pinned in PINNED_VERSIONS:
        assert pinned.reason.strip(), f"{pinned.version}: 왜 이 버전을 밟는지 근거가 비어 있다"
        assert re.fullmatch(r"\d+\.\d+\.\d+", pinned.version), (
            f"버전 형식이 아니다: {pinned.version}"
        )

    majors = {version.split(".", 1)[0] for version in versions}
    assert {"1", "2"} <= majors, (
        f"matrix 가 두 major 를 밟지 않는다 (major: {sorted(majors)}) — "
        "이 workflow 의 존재 이유가 두 major 커버리지를 선언으로 만드는 것이다"
    )


def test_policies_are_coherent() -> None:
    workflows = [entry.workflow for entry in WORKFLOW_POLICIES]
    assert len(set(workflows)) == len(workflows), f"workflow 정책이 중복 선언됐다: {workflows}"

    matrix_owners = [entry for entry in WORKFLOW_POLICIES if entry.policy == POLICY_MATRIX]
    assert len(matrix_owners) == 1, (
        f"matrix 정책을 가진 workflow 는 하나여야 한다 (현재 {len(matrix_owners)}건)"
    )

    for entry in WORKFLOW_POLICIES:
        assert entry.source.strip(), f"{entry.workflow}: 버전이 어디서 오는지가 비어 있다"
        assert entry.reason.strip(), f"{entry.workflow}: 왜 그 정책인지가 비어 있다"
        if entry.policy == POLICY_PINNED:
            assert entry.expected_role, (
                f"{entry.workflow}: pinned 인데 어느 role 을 고정하는지 안 적혀 있다"
            )


def test_floor_matches_requirements_dev_pin() -> None:
    """smoke 가 실제로 깔아 도는 버전이 registry 의 floor 와 같은가."""
    pinned = _pinned_requirement(REQUIREMENTS_DEV.read_text(encoding="utf-8"), "mcp")
    assert pinned is not None, (
        "requirements-dev.txt 에서 mcp 고정 핀을 못 찾았다 — smoke 의 pinned 정책이 "
        "근거를 잃었다 (핀을 지웠다면 registry 의 smoke 정책도 같이 바꿔야 한다)"
    )
    assert pinned == floor_version(), (
        f"requirements-dev.txt 핀({pinned}) 과 registry floor({floor_version()}) 가 갈렸다 — "
        "smoke 는 실제로 전자로 돈다"
    )


def test_extra_has_no_upper_bound() -> None:
    """floating 이라고 선언한 job 이 실제로 부동인가."""
    data = tomllib.loads(PYPROJECT_PATH.read_text(encoding="utf-8"))
    specs = [
        spec
        for spec in data["project"]["optional-dependencies"]["mcp-sdk"]
        if spec.replace(" ", "").startswith("mcp")
    ]
    assert specs, "mcp-sdk extra 에 mcp requirement 가 없다"
    floating_jobs = [e.workflow for e in WORKFLOW_POLICIES if e.policy == POLICY_FLOATING]
    for spec in specs:
        assert "<" not in spec, (
            f"mcp-sdk extra 에 상한이 생겼다 ({spec}) — {floating_jobs} 는 floating 이라고 "
            "선언돼 있는데 더 이상 부동이 아니다. 핀을 의도했다면 registry 를 먼저 고칠 것"
        )


def test_declared_workflows_exist_and_record() -> None:
    problems: list[str] = []
    for entry in WORKFLOW_POLICIES:
        path = WORKFLOW_DIR / f"{entry.workflow}.yml"
        if not path.exists():
            problems.append(f"{entry.workflow}: 선언됐는데 {path.name} 이 없다")
            continue
        text = path.read_text(encoding="utf-8")
        if entry.policy == POLICY_MATRIX:
            continue
        needle = f"--record {entry.workflow}"
        if needle not in text:
            problems.append(
                f"{entry.workflow}: 정책은 선언됐는데 `{needle}` 를 호출하지 않는다 "
                "— 실측이 어디에도 안 남는다"
            )
    assert not problems, "\n      ".join(problems)


def test_every_mcp_installing_workflow_declares_a_policy() -> None:
    """역방향. 정책 없이 mcp 를 깔고 도는 job 이 있으면 그것이 다음 사고다."""
    declared = {entry.workflow for entry in WORKFLOW_POLICIES}
    undeclared: list[str] = []
    for path in sorted(WORKFLOW_DIR.glob("*.yml")):
        if path.stem in declared:
            continue
        if _installs_mcp(path.read_text(encoding="utf-8")):
            undeclared.append(path.stem)
    assert not undeclared, (
        f"mcp 를 깔면서 버전 정책이 선언 안 된 workflow: {undeclared} — "
        "sdk_matrix.WORKFLOW_POLICIES 에 등록할 것"
    )


def test_matrix_workflow_does_not_duplicate_versions() -> None:
    entry = next(e for e in WORKFLOW_POLICIES if e.policy == POLICY_MATRIX)
    text = _workflow_text(entry.workflow)
    assert f"{MODULE_CLI} --github-matrix" in text, (
        f"{entry.workflow}.yml 이 정본에서 버전 목록을 받지 않는다"
    )
    assert "fromJson(needs." in text, (
        f"{entry.workflow}.yml 이 prepare job 의 출력을 matrix 로 쓰지 않는다"
    )
    leaked = [version for version in pinned_versions() if version in text]
    assert not leaked, (
        f"{entry.workflow}.yml 에 버전 문자열이 직접 적혀 있다: {leaked} — "
        "복제는 갈라진다. 목록은 registry 한 곳에만 둔다"
    )


def test_matrix_workflow_verifies_both_layers() -> None:
    entry = next(e for e in WORKFLOW_POLICIES if e.policy == POLICY_MATRIX)
    text = _workflow_text(entry.workflow)
    for flag, why in (
        ("--assert-installed", "요청한 버전이 실제로 깔렸는가"),
        ("--assert-exercised", "그 SDK 로 실제로 쟀는가 (skip 은 통과가 아니다)"),
    ):
        assert f"{MODULE_CLI} {flag}" in text, (
            f"{entry.workflow}.yml 이 `{flag}` 를 부르지 않는다 — {why} 를 안 본다"
        )


def test_github_matrix_output_is_valid_json_array() -> None:
    parsed = json.loads(github_matrix_json())
    assert isinstance(parsed, list) and parsed, "fromJson 이 받을 배열이 아니다"
    assert all(isinstance(item, str) for item in parsed), (
        f"matrix 항목이 문자열이 아니다: {parsed}"
    )
    assert parsed == list(pinned_versions())


def test_every_skip_capable_check_is_declared() -> None:
    """**완전성.** SDK 없이 통째로 건너뛸 수 있는 검사는 전부 증거가 선언돼 있어야 한다.

    선언 안 된 채로 새 검사가 늘면, 그 검사는 셀 안에서 조용히 skip 하고도 green 을
    낸다 — 이 workflow 가 막으려는 바로 그 상태다.
    """
    declared = {entry.path for entry in SDK_EXERCISING_CHECKS}
    tests_dir = SOURCE_ROOT / "tests"
    undeclared: list[str] = []
    for path in sorted(tests_dir.glob("check_*.py")):
        if not any(token in path.name for token in MATRIX_FILTER):
            continue
        source = path.read_text(encoding="utf-8")
        if not re.search(r'print\(\s*f?"Skipping', source):
            continue
        if f"tests/{path.name}" not in declared:
            undeclared.append(path.name)
    assert not undeclared, (
        f"SDK 없이 건너뛸 수 있는데 증거가 선언 안 된 검사: {undeclared} — "
        "sdk_matrix.SDK_EXERCISING_CHECKS 에 등록할 것"
    )


def test_declared_evidence_matches_reality() -> None:
    """선언한 증거 문자열이 그 파일이 실제로 출력하는 문자열인가."""
    problems: list[str] = []
    for entry in SDK_EXERCISING_CHECKS:
        path = REPO_ROOT / "workflow-source" / entry.path
        if not path.exists():
            problems.append(f"{entry.path}: 선언됐는데 파일이 없다")
            continue
        if entry.evidence not in path.read_text(encoding="utf-8"):
            problems.append(
                f"{entry.path}: 증거 '{entry.evidence}' 가 그 파일에 없다 — "
                "성공 메시지가 바뀌었다면 판정이 항상 실패한다"
            )
        assert entry.why.strip(), f"{entry.path}: why 가 비어 있다"
    assert not problems, "\n      ".join(problems)


def test_verdicts_actually_fire() -> None:
    """되주입: 네 가지 어긋남이 각각 다른 신호로 실패하는가."""
    mismatch = _assert_installed("1.27.0", "2.0.0")
    assert mismatch is not None and "2.0.0" in mismatch and "1.27.0" in mismatch, (
        f"버전이 어긋났는데 통과했다: {mismatch}"
    )

    missing = _assert_installed("1.27.0", None)
    assert missing is not None and "설치" in missing, f"미설치인데 통과했다: {missing}"
    assert missing != mismatch, "미설치와 버전 불일치가 같은 메시지로 나온다 — 구분되지 않는다"

    real = {entry.path: (0, f"...\n{entry.evidence}\n") for entry in SDK_EXERCISING_CHECKS}
    assert not judge_exercised(real), "증거가 다 있는데 실패했다"

    first = SDK_EXERCISING_CHECKS[0].path
    skipped = dict(real, **{first: (0, "Skipping Read-only MCP SDK stdio smoke check: mcp not installed.")})
    problems = judge_exercised(skipped)
    assert len(problems) == 1 and first in problems[0], (
        f"SDK 미설치로 건너뛴 검사를 못 잡았다 (exit 0 이라 통과해 버렸는가): {problems}"
    )

    missing = judge_exercised({k: v for k, v in real.items() if k != first})
    assert len(missing) == 1 and "실행하지 못했다" in missing[0], (
        f"검사가 아예 안 돌았는데 통과했다: {missing}"
    )

    nonzero = judge_exercised(dict(real, **{first: (1, SDK_EXERCISING_CHECKS[0].evidence)}))
    assert len(nonzero) == 1 and "exit 1" in nonzero[0], (
        f"성공 메시지가 있어도 exit != 0 이면 실패해야 한다: {nonzero}"
    )

    silent = judge_exercised({path: (0, "") for path in real})
    assert len(silent) == len(SDK_EXERCISING_CHECKS), (
        "긍정 증거 없이도 통과한다 — skip 처럼 안 보이면 넘어가는 판정이면 안 된다"
    )

    _line, problem = render_record("어디에도-없는-workflow", "2.0.0")
    assert problem is not None and "WORKFLOW_POLICIES" in problem, (
        f"정책 없는 workflow 가 통과했다: {problem}"
    )


def test_pinned_policy_enforces_its_role() -> None:
    """pinned job 은 실측이 어긋나면 실패하고, floating job 은 기록만 한다."""
    pinned_entry = next(e for e in WORKFLOW_POLICIES if e.policy == POLICY_PINNED)
    _line, problem = render_record(pinned_entry.workflow, "9.9.9")
    assert problem is not None, (
        f"{pinned_entry.workflow} 는 pinned 인데 엉뚱한 버전이 통과했다"
    )

    line, problem = render_record(pinned_entry.workflow, floor_version())
    assert problem is None, f"floor 를 깔았는데 실패했다: {problem}"
    assert floor_version() in line

    floating_entry = next(e for e in WORKFLOW_POLICIES if e.policy == POLICY_FLOATING)
    line, problem = render_record(floating_entry.workflow, "9.9.9")
    assert problem is None, (
        f"{floating_entry.workflow} 는 floating 인데 강제하고 있다 — 조기 경보를 red 로 "
        f"바꾸는 것은 이 층의 일이 아니다: {problem}"
    )
    assert "9.9.9" in line, "floating 이면 최소한 집힌 값은 남아야 한다"


def main() -> int:
    test_funcs = [
        test_registry_is_coherent,
        test_policies_are_coherent,
        test_floor_matches_requirements_dev_pin,
        test_extra_has_no_upper_bound,
        test_declared_workflows_exist_and_record,
        test_every_mcp_installing_workflow_declares_a_policy,
        test_matrix_workflow_does_not_duplicate_versions,
        test_matrix_workflow_verifies_both_layers,
        test_every_skip_capable_check_is_declared,
        test_declared_evidence_matches_reality,
        test_github_matrix_output_is_valid_json_array,
        test_verdicts_actually_fire,
        test_pinned_policy_enforces_its_role,
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

    if _skipped:
        print(f"  (skip) {len(_skipped)}건: {', '.join(sorted(set(_skipped)))}")

    total = len(test_funcs)
    print(f"\n{total - len(failures)}/{total} PASS")
    if failures:
        for name, err in failures:
            print(f"  - {name}: {err}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
