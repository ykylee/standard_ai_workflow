"""선언한 mcp SDK 버전 registry 가 **실제 저장소와 같은 것을 말하는가** (TASK-2026-07-31-main-001).

## 왜 필요한가

CI 가 mcp 1.x 와 2.x 를 동시에 밟은 것은 설계가 아니라 설치 순서였다. `smoke` 는
`requirements-dev.txt` 의 고정 핀이 editable install *뒤에* 깔려 되돌리기 때문에 1.x 로
돌고, `mypy-strict` / `mcp-inspector` 는 그 파일을 안 깔아 상한 없는 extra 가 최신을
집는다. **그 한 줄을 지우면 1.x 커버리지가 조용히 사라지는데 아무 검사도 실패하지
않았다.**

정본(`workflow_kit/common/sdk_matrix.py`)을 만드는 것만으로는 이 문제가 안 풀린다.
선언은 사실이 아니라 주장이라서, 선언과 실제 파일이 갈라지면 **선언 쪽이 조용히
이긴다** (§2.35 의 "관측하지 않은 값을 관측한 것처럼" 과 같은 모양). 그래서 이 검사가
정본과 저장소 표면을 묶는다:

- `requirements-dev.txt` 의 핀 ↔ registry 의 floor
- `pyproject.toml` 의 `mcp-sdk` extra 상한 (새 major 를 소비자에게 막지 않는다)

2026-09-23 CI workflow 폐지(TASK-2026-09-23-main-022)로 workflow 정책 registry
(`WORKFLOW_POLICIES`)와 그것을 yml 과 대조하던 case 다섯(정책 정합 · 선언 workflow
실재/`--record` · 역방향 · yml 버전 복제 · yml 두 층 검증), `--github-matrix` 형태,
pinned 정책 강제는 대상을 잃어 삭제했다. "두 층을 둘 다 본다" 는 이제
`run_local_matrix` 가 셀마다 직접 부르는지로 잰다 (case 6).

## 계약

1. registry 자체가 말이 된다 — floor 는 정확히 하나, 버전은 중복 없고, 근거가 비어
   있지 않으며, **1.x 와 2.x 를 둘 다** 포함한다 (이 matrix 의 존재 이유다).
2. registry 의 floor 가 `requirements-dev.txt` 의 핀과 같다.
3. `mcp-sdk` extra 에 상한이 없다.
4. SDK 없이 건너뛸 수 있는 검사는 전부 증거가 선언돼 있다 (완전성).
5. 선언한 증거 문자열이 그 파일에 실제로 있다.
6. `--run-local` 이 셀마다 "깔렸는가"(`_assert_installed`)와 "그것으로 실제로
   쟀는가"(`judge_exercised`)를 **둘 다** 부른다.
7. 판정 함수가 실제로 걸린다 — 어긋난 버전, 미설치, skip 한 검사, 안 돈 검사,
   exit != 0, 침묵을 되주입해 각각 실패하는지 본다.

Cross-ref: TASK-2026-07-31-main-001, releases/Beta-v1.0.0.md §2.45.
"""

from __future__ import annotations

#: 이 검사의 입력 표면 (spec `core/test_impact_tiering_spec.md` §2).
#: 게이트 채취 실측에서 뽑아 넓은 쪽으로 올렸다 — 좁으면 meta-watch 가 red 로 잡는다.
WATCHES = (
    "requirements-dev.txt",
    "workflow-source/pyproject.toml",
    "workflow-source/tests/*",
    "workflow-source/workflow_kit/*",
)

import inspect
import re
import sys
import tomllib
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SOURCE_ROOT.parent
sys.path.insert(0, str(SOURCE_ROOT))

from workflow_kit.common import sdk_matrix  # noqa: E402
from workflow_kit.common.sdk_matrix import (  # noqa: E402
    LOCAL_MATRIX_FILTER,
    PINNED_VERSIONS,
    ROLE_FLOOR,
    SDK_EXERCISING_CHECKS,
    _assert_installed,
    judge_exercised,
    floor_version,
    pinned_versions,
)

MATRIX_FILTER = tuple(LOCAL_MATRIX_FILTER.split(","))
"""`--run-local` 이 `run_all_checks --filter` 에 넘기는 값. 아래 완전성 검사가 쓴다."""

REQUIREMENTS_DEV = REPO_ROOT / "requirements-dev.txt"
PYPROJECT_PATH = SOURCE_ROOT / "pyproject.toml"

_skipped: list[str] = []


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
        "이 matrix 의 존재 이유가 두 major 커버리지를 선언으로 만드는 것이다"
    )


def test_floor_matches_requirements_dev_pin() -> None:
    """개발 `.venv` 가 실제로 깔아 도는 버전이 registry 의 floor 와 같은가."""
    pinned = _pinned_requirement(REQUIREMENTS_DEV.read_text(encoding="utf-8"), "mcp")
    assert pinned is not None, (
        "requirements-dev.txt 에서 mcp 고정 핀을 못 찾았다 — 개발 전량 검사가 "
        "하한에서 돈다는 근거를 잃었다 (핀을 지웠다면 registry 의 floor 도 같이 볼 것)"
    )
    assert pinned == floor_version(), (
        f"requirements-dev.txt 핀({pinned}) 과 registry floor({floor_version()}) 가 갈렸다 — "
        "개발 전량 검사는 실제로 전자로 돈다"
    )


def test_extra_has_no_upper_bound() -> None:
    """`mcp-sdk` extra 가 새 major 를 막지 않는가 (소비자에게 상한을 강요하지 않는다)."""
    data = tomllib.loads(PYPROJECT_PATH.read_text(encoding="utf-8"))
    specs = [
        spec
        for spec in data["project"]["optional-dependencies"]["mcp-sdk"]
        if spec.replace(" ", "").startswith("mcp")
    ]
    assert specs, "mcp-sdk extra 에 mcp requirement 가 없다"
    for spec in specs:
        assert "<" not in spec, (
            f"mcp-sdk extra 에 상한이 생겼다 ({spec}) — 두 major 를 모두 해석한다는 "
            "registry 의 전제(1.x·2.x 셀)와 어긋난다. 핀을 의도했다면 registry 를 먼저 고칠 것"
        )


def test_every_skip_capable_check_is_declared() -> None:
    """**완전성.** SDK 없이 통째로 건너뛸 수 있는 검사는 전부 증거가 선언돼 있어야 한다.

    선언 안 된 채로 새 검사가 늘면, 그 검사는 셀 안에서 조용히 skip 하고도 green 을
    낸다 — 이 matrix 가 막으려는 바로 그 상태다.
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


def test_run_local_verifies_both_layers() -> None:
    """`--run-local` 이 셀마다 두 층을 **둘 다** 부른다.

    폐지된 CI 에서는 yml 이 `--assert-installed` / `--assert-exercised` 를 부르는지로
    쟀다. 이제 그 판정을 부르는 곳은 `run_local_matrix` 하나라, 거기서 빠지면
    SDK 검사가 skip 후 exit 0 으로 끝나도 로컬 매트릭스가 green 이 된다.
    """
    source = inspect.getsource(sdk_matrix.run_local_matrix)
    for call, why in (
        ("_assert_installed(", "요청한 버전이 실제로 깔렸는가"),
        ("judge_exercised(observe_exercised(", "그 SDK 로 실제로 쟀는가 (skip 은 통과가 아니다)"),
    ):
        assert call in source, (
            f"run_local_matrix 가 `{call}` 를 부르지 않는다 — {why} 를 안 본다"
        )


def test_verdicts_actually_fire() -> None:
    """되주입: 어긋남이 각각 다른 신호로 실패하는가."""
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


def main() -> int:
    test_funcs = [
        test_registry_is_coherent,
        test_floor_matches_requirements_dev_pin,
        test_extra_has_no_upper_bound,
        test_every_skip_capable_check_is_declared,
        test_declared_evidence_matches_reality,
        test_run_local_verifies_both_layers,
        test_verdicts_actually_fire,
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
