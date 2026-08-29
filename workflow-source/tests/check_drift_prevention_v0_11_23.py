"""Drift prevention guard — v0.11.23+.

Cycle: 9-release-cycle drift 가 v0.7.10 ~ v0.11.22 동안 누적되어 README, project_status_assessment,
workflow_kit_roadmap, docs/PROJECT_PROFILE, docs/INSTALLATION_AND_USAGE 등이 stale 상태가 된 사례를
silently 통과시키지 않도록 4개 cross-check smoke 를 강제한다.

본 test 가 잡는 drift category:
  - pyproject.toml version ↔ __init__.py loud fallback literal
  - maturity_matrix.json phase status 의 monotonicity + Phase 11 done / Phase 12 in_progress
  - maturity_matrix.json skill stage 의 stable/beta/alpha 가 expected promotion 결과와 정합
  - maturity_matrix.json harness.supported 가 bootstrap_lib HARNESS_SPECS 의 banner key 와 정합
  - README.md 헤더의 '버전: vX.Y.Z' 가 pyproject 와 정합
  - maturity_matrix.json 의 last_updated 가 HEAD commit date 와 ±N일 이내

기대 동작:
  - 본 smoke 가 fail 이면 CI mypy-strict workflow + smoke.yml 의 두 군데에서 모두 fail
  - release_pipeline.py release --apply 시 validate step 에서도 same check 가 inline 으로 호출됨
  - `tools/release_pipeline.py sync-maturity-matrix` 가 본 smoke 가 검출한 drift 를 자동 fix

CI integration:
  - .github/workflows/smoke.yml 의 smoke step 에 자동 포함 (workflow-source/tests/check_*.py glob)
  - .github/workflows/mypy-strict.yml 의 mypy step 후 보조 검증 (--check-drift flag 향후 추가 여지)

본 test 는 v0.11.23 의 4-7 cycle (Phase 12 의 운영 자동화) 의 일부.
"""
from __future__ import annotations

#: 이 검사의 입력 표면 (spec `core/test_impact_tiering_spec.md` §2).
#: 게이트 채취 실측에서 뽑아 넓은 쪽으로 올렸다 — 좁으면 meta-watch 가 red 로 잡는다.
WATCHES = (
    "LICENSE",
    "README.md",
    "workflow-source/LICENSE",
    "workflow-source/core/*",
    "workflow-source/pyproject.toml",
    "workflow-source/workflow_kit/*",
)

import json
import re
import subprocess
import sys
import tomllib
from pathlib import Path
from typing import Iterable

REPO = Path(__file__).resolve().parents[2]
PYPROJECT = REPO / "workflow-source" / "pyproject.toml"
INIT_PY = REPO / "workflow-source" / "workflow_kit" / "__init__.py"
MATURITY = REPO / "workflow-source" / "core" / "maturity_matrix.json"
README = REPO / "README.md"
HARNESS_SPECS_PATH = REPO / "workflow-source" / "workflow_kit" / "bootstrap_lib" / "harnesses" / "__init__.py"

# 본 smoke 가 안정적으로 유지될 expected promotion 결과 (v0.11.21 기준).
# 본 release 에서 추가 stable 승격이 일어나면 이 set 을 갱신해야 한다.
EXPECTED_STABLE_SKILLS = {
    "session-start",
    "backlog-update",
    "doc-sync",
    "merge-doc-reconcile",
    "validation-plan",
    "code-index-update",
    "workflow-linter",
    "project-status-assessment",
    "robust-patcher",
    "automated-repro-scaffold",
    "task-modes",
    "git-conflict-resolver",
}

#: v1.1.3+: 하드코딩 목록을 **정본에서 유도** 로 바꿨다.
#:
#: 예전에는 10개를 손으로 적어 두고 `EXPECTED_BANNER_HARNESSES & specs_keys` 로
#: 좁혀 비교했다. 그래서 **새 harness 가 추가돼도 이 검사는 몰랐다** — 이름은
#: "SSOT alignment" 인데 정본 전체를 보지 않았다. 실제로 `mavis` (v1.1.0 에서 harness
#: 로 등록) 가 `maturity_matrix.json` 에 빠져 있었는데 6/6 PASS 였다 (2026-08-09 실측).
#:
#: 이제 기대값은 `HARNESS_SPECS` 전체에서 아래 제외분을 뺀 것이다.
#: `harnesses.supported` 는 **overlay 를 배포하는** harness 목록이다 (파일시스템의
#: `harnesses/<name>/` 과 1:1). 아래 둘은 그 정의에 해당하지 않는다 — 넣으면
#: `check_harness_v0_15_9` 의 *3-way set equality* 가 깨진다 (2026-08-09 실측).
NON_OVERLAY_HARNESSES = {
    "custom": (
        "자사 harness 에 wire-up 하는 **어댑터 템플릿** 이다 "
        "(`.workflow-kits/custom/SKILL.md`). 배포되는 overlay 가 아니다."
    ),
    "mavis": (
        "**project-local 산출물이 0** 인 harness — 표준 §6.5.2 의 글로벌 "
        "`~/.minimax/mcp/mcp.json` merge 만 emit 한다 (v1.1.0, TASK-2026-08-08-main-007). "
        "`harnesses/mavis/` 디렉터리가 없는 것이 설계이므로 overlay 목록에 넣지 않는다. "
        "`HARNESS_SPECS` 에는 있다 — bootstrap `--harness mavis` 는 정상 동작한다."
    ),
}


def _read_pyproject_version() -> str:
    with open(PYPROJECT, "rb") as f:
        return tomllib.load(f)["project"]["version"]


def _loud_fallback_version() -> str:
    """workflow_kit/__init__.py 의 loud fallback literal 을 parse."""
    src = INIT_PY.read_text(encoding="utf-8")
    # v1.2.1: 리터럴이 `return "1.2.1"` 형태. 구 포맷(v..., -beta)도 받아 준다.
    m = re.search(r'return "v?([\d.]+)(?:-beta)?"', src)
    if not m:
        raise AssertionError("loud fallback literal not found in __init__.py")
    return m.group(1)


def _read_maturity() -> dict:
    return json.loads(MATURITY.read_text(encoding="utf-8"))


def _read_readme_header_version() -> str | None:
    src = README.read_text(encoding="utf-8")
    # v1.2.1: stable 정리로 `-beta` 접미사가 사라졌다. 구 포맷도 받아 준다.
    m = re.search(r"- 버전: v([\d.]+)(?:-beta)?", src)
    return m.group(1) if m else None


def _head_commit_date() -> str:
    proc = subprocess.run(
        ["git", "log", "-1", "--format=%cs"],
        cwd=str(REPO), capture_output=True, text=True, timeout=10,
    )
    return proc.stdout.strip()


def _parse_last_updated(mm: dict) -> str:
    return mm.get("last_updated", "")


def _harness_specs_keys() -> set[str]:
    """bootstrap_lib/harnesses/__init__.py 의 HARNESS_SPECS dict literal key set."""
    src = HARNESS_SPECS_PATH.read_text(encoding="utf-8")
    # dict literal 의 key 만 추출. 단순 regex — value 부분에 : " 가 있는 경우 매치.
    return set(re.findall(r'^\s*"([\w-]+)"\s*:\s*HarnessSpec\(', src, flags=re.MULTILINE))


# ---------------------------------------------------------------------------
# case 1 — pyproject version ↔ __init__.py loud fallback
# ---------------------------------------------------------------------------

def test_case_1_pyproject_loud_fallback_sync() -> None:
    """pyproject.toml [project] version == __init__.py loud fallback literal."""
    py_v = _read_pyproject_version()
    fallback_v = _loud_fallback_version()
    assert py_v == fallback_v, (
        f"pyproject.toml version {py_v!r} != __init__.py loud fallback {fallback_v}. "
        f"fix: `python3 workflow-source/workflow_kit/tools/release_pipeline.py version-bump --to {py_v}` "
        f"또는 수동으로 __init__.py 의 loud fallback literal 을 {py_v} 로 갱신."
    )


# ---------------------------------------------------------------------------
# case 2 — maturity_matrix phase monotonicity + Phase 11/12 done / Phase 13 planned
# ---------------------------------------------------------------------------

def test_case_2_maturity_matrix_phase_status() -> None:
    """Phase status 단조성 + Phase 11/12 done / Phase 13 planned 정합.

    Phase 12 close-out (v0.15.20, commit ab202d8): Operational Intelligence +
    Deprecation Stabilization 완료. Phase 13 follow-up 진입 대기 (v1.0.0 stable 진입
    후 정식 start). 상세: workflow-source/core/phase_13_followup.md.
    """
    mm = _read_maturity()
    milestones = mm["milestones"]
    allowed = {"done", "in_progress", "planned"}
    for k, v in milestones.items():
        assert v["status"] in allowed, f"{k} has unknown status {v['status']!r}"
    assert milestones["Phase 11"]["status"] == "done", (
        f"Phase 11 should be 'done' (closed in v0.9.0). "
        f"got {milestones['Phase 11']['status']!r}."
    )
    assert milestones["Phase 12"]["status"] == "done", (
        f"Phase 12 should be 'done' (closed in v0.15.20). "
        f"got {milestones['Phase 12']['status']!r}."
    )
    # Phase 13 정합: v1.0.0 stable 진입과 함께 정식 start (planned → in_progress).
    # v1.0.0 이전에는 entry 자체가 없을 수 있으므로 정의된 경우에만 검증.
    if "Phase 13" in milestones:
        assert milestones["Phase 13"]["status"] == "in_progress", (
            f"Phase 13 should be 'in_progress' (v1.0.0 stable 진입과 함께 정식 start). "
            f"got {milestones['Phase 13']['status']!r}."
        )


# ---------------------------------------------------------------------------
# case 3 — maturity_matrix skill stage = expected
# ---------------------------------------------------------------------------

def test_case_3_skill_stage_matches_promotion_set() -> None:
    """EXPECTED_STABLE_SKILLS 의 모든 skill 이 stage=stable + promoted_in_release 키 보유."""
    mm = _read_maturity()
    skills = mm["skills"]
    for name in EXPECTED_STABLE_SKILLS:
        entry = skills.get(name)
        assert entry is not None, f"maturity_matrix skills missing: {name!r}"
        assert entry["stage"] == "stable", (
            f"skill {name!r} expected stage='stable' (per promotion history) "
            f"got {entry['stage']!r}"
        )
        assert "promoted_in_release" in entry, (
            f"skill {name!r} stable but missing 'promoted_in_release' provenance key"
        )


# ---------------------------------------------------------------------------
# case 4 — README.md header version = pyproject
# ---------------------------------------------------------------------------

def test_case_4_readme_header_version_sync() -> None:
    """README.md 헤더의 '버전: vX.Y.Z' == pyproject.toml version."""
    py_v = _read_pyproject_version()
    readme_v = _read_readme_header_version()
    assert readme_v is not None, "README.md header missing version line ('버전: vX.Y.Z')"
    assert readme_v == py_v, (
        f"README.md v{readme_v} != pyproject {py_v}. "
        f"fix: README.md 의 '버전: v{py_v}' 로 갱신."
    )


# ---------------------------------------------------------------------------
# case 5 (P2 — maturity-matrix vs HARNESS_SPECS cross-check)
# ---------------------------------------------------------------------------

def test_case_5_harness_supported_ssot_alignment() -> None:
    """maturity_matrix.json harnesses.supported == bootstrap_lib HARNESS_SPECS banner keys."""
    mm = _read_maturity()
    declared = set(mm["harnesses"]["supported"])
    specs_keys = _harness_specs_keys()
    # 제외 목록에 이유가 없으면 그 자체가 결함이다 (원장은 이유가 정본).
    for name, reason in NON_OVERLAY_HARNESSES.items():
        assert reason.strip(), f"NON_OVERLAY_HARNESSES[{name}] 에 이유가 없다"
    expected_banner = specs_keys - set(NON_OVERLAY_HARNESSES)
    missing_in_mm = expected_banner - declared
    extra_in_mm = declared - specs_keys
    assert not missing_in_mm, (
        f"maturity_matrix harnesses.supported missing {sorted(missing_in_mm)}. "
        f"fix: `python3 workflow-source/workflow_kit/tools/release_pipeline.py sync-maturity-matrix --from-release-note "
        f"workflow-source/releases/Beta-v<NEW_VERSION>.md --apply`"
    )
    assert not extra_in_mm, (
        f"maturity_matrix harnesses.supported has extra entries {sorted(extra_in_mm)} "
        f"not in HARNESS_SPECS (likely stale)."
    )


# ---------------------------------------------------------------------------
# case 6 (P2 — last_updated freshness)
# ---------------------------------------------------------------------------

def test_case_6_maturity_last_updated_freshness() -> None:
    """maturity_matrix.json 의 last_updated 가 HEAD commit date 와 ±14일 이내.

    본 test 는 "드리프트 누적" 의 가장 흔한 지표. 14일 이상 stale 이면
    `release_pipeline.py sync-maturity-matrix` 가 호출되지 않은 것.
    """
    from datetime import date, datetime
    last = _parse_last_updated(_read_maturity())
    head = _head_commit_date()
    if not last or not head:
        # SSOT 아직 empty 일 수 있음 — soft skip
        return
    try:
        last_d = date.fromisoformat(last)
        head_d = date.fromisoformat(head)
    except ValueError:
        # soft skip (포맷이 ISO 아닌 경우 — 본 smoke 의 false-positive 방지)
        return
    delta_days = abs((head_d - last_d).days)
    if delta_days > 14:
        raise AssertionError(
            f"maturity_matrix last_updated={last} vs HEAD commit date={head} "
            f"differs by {delta_days} days (>14). "
            f"fix: SSOT 갱신 (release --apply 시 자동 sync; 또는 수동 patch)."
        )


def test_case_7_license_copy_matches_canonical() -> None:
    """`workflow-source/LICENSE` 사본이 루트 정본과 byte 동일 (v1.2.1).

    라이선스 전문은 저장소 루트가 정본이다 (GitHub 이 읽는 자리). 그런데 패키지
    build root 는 `workflow-source/` 라서 setuptools 의 `license-files` 가 루트를
    볼 수 없다 — 배포물에 전문을 실으려면 build root 안에 사본이 필요하다.

    사본은 반드시 갈라지므로 여기서 byte 동일을 강제한다. 둘 중 하나만 고치면
    배포물의 라이선스가 저장소가 말하는 라이선스와 달라지는데, 그건 조용히
    일어나고 배포된 뒤에는 되돌릴 수 없다.
    """
    canonical = REPO / "LICENSE"
    copy = REPO / "workflow-source" / "LICENSE"
    assert canonical.is_file(), (
        "루트 LICENSE 부재 — pyproject 는 MIT 를 선언하는데 전문이 없으면 "
        "MIT 가 요구하는 '고지 포함' 을 재배포자가 이행할 수 없다."
    )
    assert copy.is_file(), (
        "workflow-source/LICENSE 부재 — 배포물(wheel/sdist)에 라이선스 전문이 "
        "실리지 않는다. fix: `cp LICENSE workflow-source/LICENSE`"
    )
    assert copy.read_bytes() == canonical.read_bytes(), (
        "workflow-source/LICENSE 가 루트 정본과 다르다 (배포물의 라이선스가 "
        "저장소 선언과 갈라졌다). fix: `cp LICENSE workflow-source/LICENSE`"
    )


# ---------------------------------------------------------------------------
# runner
# ---------------------------------------------------------------------------

def _run_all() -> Iterable[tuple[str, bool, str]]:
    cases = [
        ("test_case_1_pyproject_loud_fallback_sync", test_case_1_pyproject_loud_fallback_sync),
        ("test_case_2_maturity_matrix_phase_status", test_case_2_maturity_matrix_phase_status),
        ("test_case_3_skill_stage_matches_promotion_set", test_case_3_skill_stage_matches_promotion_set),
        ("test_case_4_readme_header_version_sync", test_case_4_readme_header_version_sync),
        ("test_case_5_harness_supported_ssot_alignment", test_case_5_harness_supported_ssot_alignment),
        ("test_case_6_maturity_last_updated_freshness", test_case_6_maturity_last_updated_freshness),
        ("test_case_7_license_copy_matches_canonical", test_case_7_license_copy_matches_canonical),
    ]
    for name, fn in cases:
        try:
            fn()
            yield name, True, ""
        except AssertionError as exc:
            yield name, False, str(exc)


def main() -> int:
    print("=== drift prevention guard (v0.11.23+) ===")
    failures = 0
    total = 0
    for name, ok, msg in _run_all():
        total += 1
        if ok:
            print(f"  PASS: {name}")
        else:
            print(f"  FAIL: {name}\n    {msg}")
            failures += 1
    # v1.2.1 (TASK-2026-08-13-main-007): 총계를 **실행 결과에서 파생**한다.
    # 이전에는 `{6 - failures}/6` 하드코딩이라, case 를 추가해도 6/6 이라 보고했고
    # (case 7 추가 직후 실측) case 를 **빼도** 6/6 이었다 — 요약이 사실이 아니었다.
    print(f"=== {'PASS' if failures == 0 else 'FAIL'}: {total - failures}/{total} ===")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
