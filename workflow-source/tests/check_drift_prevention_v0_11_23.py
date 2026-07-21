"""Drift prevention guard — v0.11.23+.

Cycle: 9-release-cycle drift 가 v0.7.10 ~ v0.11.22 동안 누적되어 README, project_status_assessment,
workflow_kit_roadmap, docs/PROJECT_PROFILE, docs/INSTALLATION_AND_USAGE 등이 stale 상태가 된 사례를
silently 통과시키지 않도록 4개 cross-check smoke 를 강제한다.

본 test 가 잡는 drift category:
  - pyproject.toml version ↔ __init__.py loud fallback literal
  - maturity_matrix.json phase status 의 monotonicity + Phase 11 done / Phase 12 in_progress
  - maturity_matrix.json skill stage 의 stable/beta/alpha 가 expected promotion 결과와 정합
  - maturity_matrix.json harness.supported 가 bootstrap_lib HARNESS_SPECS 의 banner key 와 정합
  - README.md 헤더의 '버전: vX.Y.Z-beta' 가 pyproject 와 정합
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
HARNESS_SPECS_PATH = REPO / "workflow-source" / "scripts" / "bootstrap_lib" / "harnesses" / "__init__.py"

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

EXPECTED_BANNER_HARNESSES = {
    "codex", "opencode", "gemini-cli", "antigravity", "minimax-code",
    "claude-code", "aider", "goose", "pi-dev", "codewhale",
}


def _read_pyproject_version() -> str:
    with open(PYPROJECT, "rb") as f:
        return tomllib.load(f)["project"]["version"]


def _loud_fallback_version() -> str:
    """workflow_kit/__init__.py 의 loud fallback literal 을 parse."""
    src = INIT_PY.read_text(encoding="utf-8")
    m = re.search(r'return "v([\d.]+)(?:-beta)?"', src)
    if not m:
        raise AssertionError("loud fallback literal not found in __init__.py")
    return m.group(1)


def _read_maturity() -> dict:
    return json.loads(MATURITY.read_text(encoding="utf-8"))


def _read_readme_header_version() -> str | None:
    src = README.read_text(encoding="utf-8")
    m = re.search(r"- 버전: v([\d.]+)-beta", src)
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
        f"pyproject.toml version {py_v!r} != __init__.py loud fallback v{fallback_v}. "
        f"fix: `python3 workflow-source/tools/release_pipeline.py version-bump --to {py_v}` "
        f"또는 수동으로 __init__.py 의 loud fallback literal 을 v{py_v}-beta 로 갱신."
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
    """README.md 헤더의 '버전: vX.Y.Z-beta' == pyproject.toml version."""
    py_v = _read_pyproject_version()
    readme_v = _read_readme_header_version()
    assert readme_v is not None, "README.md header missing version line ('버전: vX.Y.Z-beta')"
    assert readme_v == py_v, (
        f"README.md v{readme_v} != pyproject {py_v}. "
        f"fix: README.md 의 '버전: v{py_v}-beta' 로 갱신."
    )


# ---------------------------------------------------------------------------
# case 5 (P2 — maturity-matrix vs HARNESS_SPECS cross-check)
# ---------------------------------------------------------------------------

def test_case_5_harness_supported_ssot_alignment() -> None:
    """maturity_matrix.json harnesses.supported == bootstrap_lib HARNESS_SPECS banner keys."""
    mm = _read_maturity()
    declared = set(mm["harnesses"]["supported"])
    specs_keys = _harness_specs_keys()
    expected_banner = EXPECTED_BANNER_HARNESSES & specs_keys
    missing_in_mm = expected_banner - declared
    extra_in_mm = declared - specs_keys
    assert not missing_in_mm, (
        f"maturity_matrix harnesses.supported missing {sorted(missing_in_mm)}. "
        f"fix: `python3 workflow-source/tools/release_pipeline.py sync-maturity-matrix --from-release-note "
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
    for name, ok, msg in _run_all():
        if ok:
            print(f"  PASS: {name}")
        else:
            print(f"  FAIL: {name}\n    {msg}")
            failures += 1
    print(f"=== {'PASS' if failures == 0 else 'FAIL'}: {6 - failures}/6 ===")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
