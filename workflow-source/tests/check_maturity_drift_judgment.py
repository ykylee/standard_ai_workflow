"""maturity 정합 판정의 **어휘와 근거** (v1.0.4).

## 왜 필요한가

§2.47 이 `--maturity` 를 처음으로 *실제로* 돌게 만들자 두 건이 나왔다. 하나는 진짜
드리프트였고 하나는 **위양성**이었다.

1. `task-modes` 가 "stable 인데 test_path 가 없다" 는 warning 을 냈다. 그런데 그 항목은
   `kind: "spec"` — 실행 표면이 없는 명세라 `test_path` 가 null 인 것이 정상이다.
   그 규약을 아는 자리가 `check_maturity_registry.py` **하나뿐**이었고, kit 이 배포하는
   린터는 몰랐다. 규약이 두 곳에 있고 한쪽만 아는 것 — 위양성을 내는 검사는 무시당한다.
2. roadmap 이 Phase 13 을 `planned 진입 대기` 로 적고 있었다(릴리스 하루 전 상태).
   그런데 예전 판정은 milestone `name` 문자열의 **포함 여부** 하나였다 — 그 문자열
   한 줄만 넣으면 roadmap 이 여전히 "아직 시작 안 했다" 고 말해도 통과한다. §2.47 에서
   지운 것과 같은 종류의 검사(통과하면서 아무것도 보장하지 못하는)가 여기에도 있었다.

## 계약

1. `kind: "spec"` 항목은 `test_path` 부재로 경고받지 않는다. 대신 `spec_path` 가 근거다.
2. 선언한 `spec_path` 가 없으면 issue, 선언 자체가 없으면 warning.
3. 비-spec 항목의 stable/beta 는 여전히 `test_path` 를 요구한다.
4. matrix 가 `in_progress` 인 milestone 을 roadmap 이 `planned` 로 적고 있으면 issue —
   **name 을 언급하는 것만으로는 통과하지 못한다.**
5. 어휘 정본은 `workflow_kit/common/maturity.py` 한 곳이고, 소비자는 리터럴 사본을
   갖지 않는다.

Cross-ref: releases/Beta-v1.0.0.md §2.48.
"""

from __future__ import annotations

#: 이 검사의 입력 표면 (spec `core/test_impact_tiering_spec.md` §2).
#: 게이트 채취 실측에서 뽑아 넓은 쪽으로 올렸다 — 좁으면 meta-watch 가 red 로 잡는다.
WATCHES = (
    "workflow-source/core/*",
    "workflow-source/pyproject.toml",
    "workflow-source/tests/*",
    "workflow-source/workflow_kit/*",
)

import json
import sys
import tempfile
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SOURCE_ROOT.parent
sys.path.insert(0, str(SOURCE_ROOT))

from workflow_kit.common.linter import check_maturity_consistency  # noqa: E402
from workflow_kit.common.maturity import (  # noqa: E402
    SKILL_KIND_SPEC,
    is_spec_entry,
    requires_test_path,
    roadmap_planned_contradictions,
)

MILESTONE_KEY = "Phase 13"
MILESTONE_NAME = "Operational Intelligence v1.0 + 2-Year Guarantee Follow-up"


def _matrix(skills: dict, milestone_status: str = "done") -> dict:
    return {
        "skills": skills,
        "milestones": {
            "Phase 12": {"name": "Operational Intelligence", "status": "done"},
            MILESTONE_KEY: {"name": MILESTONE_NAME, "status": milestone_status},
        },
    }


def _run(td: str, matrix: dict, roadmap: str | None = None, files: tuple[str, ...] = ()) -> dict:
    root = Path(td)
    matrix_path = root / "core" / "maturity_matrix.json"
    matrix_path.parent.mkdir(parents=True, exist_ok=True)
    matrix_path.write_text(json.dumps(matrix), encoding="utf-8")
    for rel in files:
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("# fixture\n", encoding="utf-8")
    roadmap_path = root / "core" / "workflow_kit_roadmap.md"
    if roadmap is not None:
        roadmap_path.write_text(roadmap, encoding="utf-8")
    return check_maturity_consistency(matrix_path, roadmap_path, root)


# --- 1. spec 어휘 -----------------------------------------------------------


def test_spec_entry_is_not_warned_for_missing_test_path() -> None:
    """`kind: spec` 은 test_path 가 없어도 경고 대상이 아니다 (원래 위양성)."""
    with tempfile.TemporaryDirectory() as td:
        result = _run(
            td,
            _matrix({"task-modes": {
                "stage": "stable", "test_path": None,
                "kind": SKILL_KIND_SPEC, "spec_path": "core/workflow_task_modes.md",
            }}),
            files=("core/workflow_task_modes.md",),
        )
        assert not any("task-modes" in w for w in result["warnings"]), result["warnings"]
        assert result["status"] == "ok", result


def test_spec_entry_with_missing_spec_file_is_an_issue() -> None:
    """근거를 선언했는데 그 파일이 없으면 통과시키지 않는다."""
    with tempfile.TemporaryDirectory() as td:
        result = _run(
            td,
            _matrix({"task-modes": {
                "stage": "stable", "test_path": None,
                "kind": SKILL_KIND_SPEC, "spec_path": "core/does_not_exist.md",
            }}),
        )
        codes = [i["code"] for i in result["issues"]]
        assert "missing_spec_file" in codes, codes


def test_spec_entry_without_any_evidence_is_warned() -> None:
    """spec 이라면서 `spec_path` 조차 없으면 근거가 없는 것이다."""
    with tempfile.TemporaryDirectory() as td:
        result = _run(td, _matrix({"ghost-spec": {"stage": "stable", "kind": SKILL_KIND_SPEC}}))
        assert any("ghost-spec" in w for w in result["warnings"]), result["warnings"]


def test_executable_stable_still_requires_test_path() -> None:
    """spec 이 아닌 stable 은 여전히 test_path 를 요구한다 (완화가 아니다)."""
    with tempfile.TemporaryDirectory() as td:
        result = _run(td, _matrix({"real-skill": {"stage": "stable", "test_path": None}}))
        assert any("real-skill" in w for w in result["warnings"]), result["warnings"]


# --- 2. roadmap 정합 --------------------------------------------------------


def test_roadmap_marking_in_progress_phase_as_planned_is_an_issue() -> None:
    """matrix 가 `in_progress` 인데 roadmap 이 `planned` 면 모순이다."""
    with tempfile.TemporaryDirectory() as td:
        roadmap = (
            f"# Roadmap\n\n## 1. 현재 단계 ({MILESTONE_KEY} planned 진입 대기)\n\n"
            f"{MILESTONE_NAME} 는 v1.0.0 stable 진입 후 시작한다.\n"
        )
        result = _run(td, _matrix({}, milestone_status="in_progress"), roadmap=roadmap)
        codes = [i["code"] for i in result["issues"]]
        assert "roadmap_milestone_still_planned" in codes, codes
        # name 은 본문에 있으므로 옛 판정(문자열 포함)만으로는 통과했을 상황이다.
        assert "roadmap_milestone_mismatch" not in codes, codes


def test_mentioning_the_name_alone_does_not_satisfy_the_check() -> None:
    """이름만 적어 두고 상태를 안 고치면 여전히 실패한다 (판정 우회 방지)."""
    with tempfile.TemporaryDirectory() as td:
        roadmap = f"# Roadmap\n\n{MILESTONE_NAME}\n\n{MILESTONE_KEY}: planned\n"
        result = _run(td, _matrix({}, milestone_status="in_progress"), roadmap=roadmap)
        assert result["status"] == "issues_found", result


def test_aligned_roadmap_produces_no_issue() -> None:
    """roadmap 이 실제로 현재 단계라고 적으면 통과한다."""
    with tempfile.TemporaryDirectory() as td:
        roadmap = (
            f"# Roadmap\n\n## 1. 현재 단계 ({MILESTONE_KEY} in_progress)\n\n"
            f"{MILESTONE_NAME} 는 2026-07-21 에 시작됐다.\n"
        )
        result = _run(td, _matrix({}, milestone_status="in_progress"), roadmap=roadmap)
        assert result["status"] == "ok", result


def test_phase_key_matching_respects_digit_boundary() -> None:
    """`Phase 1` 이 `Phase 13` 줄에 걸리면 없는 모순을 만든다."""
    line = "Phase 13 은 planned 다"
    assert roadmap_planned_contradictions(line, "Phase 13") == [line]
    assert roadmap_planned_contradictions(line, "Phase 1") == []


# --- 3. 정본이 하나인가 -----------------------------------------------------


def test_vocabulary_has_no_literal_copies() -> None:
    """소비자 2곳이 `"spec"` 리터럴을 다시 들고 있지 않다."""
    consumers = (
        SOURCE_ROOT / "workflow_kit" / "common" / "linter.py",
        SOURCE_ROOT / "tests" / "check_maturity_registry.py",
    )
    offenders: list[str] = []
    for path in consumers:
        for num, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if '"spec"' in line and "SKILL_KIND_SPEC" not in line and not line.lstrip().startswith("#"):
                offenders.append(f"{path.name}:{num}: {line.strip()}")
    assert not offenders, "어휘 사본이 남아 있다:\n  " + "\n  ".join(offenders)
    # helper 가 실제로 그 판정을 한다는 것도 함께 고정한다.
    assert is_spec_entry({"kind": SKILL_KIND_SPEC})
    assert not requires_test_path({"kind": SKILL_KIND_SPEC, "stage": "stable"})
    assert requires_test_path({"stage": "stable"})


# --- 4. 이 저장소의 실제 상태 -----------------------------------------------


def test_this_repo_matrix_and_roadmap_agree() -> None:
    """실저장소에서 maturity 판정이 `ok` 다 (§2.48 에서 드리프트 2건 해소)."""
    result = check_maturity_consistency(
        SOURCE_ROOT / "core" / "maturity_matrix.json",
        SOURCE_ROOT / "core" / "workflow_kit_roadmap.md",
        SOURCE_ROOT,
    )
    assert result["status"] == "ok", result
    assert not result["warnings"], result["warnings"]


def main() -> int:
    test_funcs = [
        test_spec_entry_is_not_warned_for_missing_test_path,
        test_spec_entry_with_missing_spec_file_is_an_issue,
        test_spec_entry_without_any_evidence_is_warned,
        test_executable_stable_still_requires_test_path,
        test_roadmap_marking_in_progress_phase_as_planned_is_an_issue,
        test_mentioning_the_name_alone_does_not_satisfy_the_check,
        test_aligned_roadmap_produces_no_issue,
        test_phase_key_matching_respects_digit_boundary,
        test_vocabulary_has_no_literal_copies,
        test_this_repo_matrix_and_roadmap_agree,
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
