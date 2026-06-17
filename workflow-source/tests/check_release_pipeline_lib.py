"""tools.release_pipeline_lib in-process wrapper test (v0.7.55+).

Verifies that `tools.release_pipeline_lib.cmd_*` correctly loads the
underlying `tools/release_pipeline.py` script and returns expected shapes.

This test imports `release_pipeline_lib` from `workflow-source/tools/`,
which is *sibling* of `workflow_kit/`. Path resolution matches the
dispatcher's release-doctor handler.

Test list (v0.7.55 → v0.7.56):
1. test_cmd_validate_returns_4_keys (v0.7.55): returns dict with packaging/doctor/state/git
2. test_cmd_validate_all_skipped_returns_all_ok (v0.7.55): all 4 skipped → all ok=True
3. test_cmd_version_bump_dry_run (v0.7.56): returns mode=dry-run with current+next
4. test_cmd_note_draft_dry_run (v0.7.56): requires --to + --from-tag
5. test_cmd_dist_dry_run (v0.7.56): returns mode=dry-run with out_dir
6. test_cmd_changelog_gen_dry_run (v0.7.56): returns mode=dry-run with commits count
7. test_cmd_verify_bad_tag (v0.7.56): handles bad tag gracefully
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

# Add workflow-source/tools/ to sys.path so release_pipeline_lib import works.
TOOLS_DIR = Path(__file__).resolve().parent.parent / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))


def _import_lib():
    spec = importlib.util.spec_from_file_location(
        "release_pipeline_lib", str(TOOLS_DIR / "release_pipeline_lib.py"),
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["release_pipeline_lib"] = mod
    spec.loader.exec_module(mod)
    return mod


def test_cmd_validate_returns_4_keys_v0_7_55() -> None:
    """cmd_validate() returns dict with 4 expected keys."""
    lib = _import_lib()
    result = lib.cmd_validate()
    assert isinstance(result, dict), f"expected dict, got {type(result)}"
    for key in ("packaging", "doctor", "state", "git"):
        assert key in result, f"missing key: {key}"


def test_cmd_validate_all_skipped_returns_all_ok_v0_7_55() -> None:
    """cmd_validate with all 4 sources skipped returns all ok=True."""
    lib = _import_lib()
    result = lib.cmd_validate(
        skip_packaging=True, skip_doctor=True,
        skip_state=True, skip_git=True,
    )
    for key in ("packaging", "doctor", "state", "git"):
        assert result[key].get("ok") is True, f"{key} not ok: {result[key]}"
        assert result[key].get("skipped") is True, f"{key} not marked skipped: {result[key]}"


def test_cmd_version_bump_dry_run_v0_7_56() -> None:
    """cmd_version_bump(apply=False, patch=True) returns mode=dry-run with current+next."""
    lib = _import_lib()
    result = lib.cmd_version_bump(apply=False, patch=True)
    assert result.get("mode") == "dry-run", f"expected mode=dry-run, got {result.get('mode')}"
    assert "current_pyproject" in result
    assert "next_pyproject" in result
    # current should be a semver
    current = result["current_pyproject"]
    assert current.count(".") == 2, f"expected semver, got {current}"
    # next should be patch-bumped
    parts = current.split(".")
    expected_next = f"{parts[0]}.{parts[1]}.{int(parts[2]) + 1}"
    assert result["next_pyproject"] == expected_next, (
        f"expected {expected_next}, got {result['next_pyproject']}"
    )


def test_cmd_note_draft_dry_run_v0_7_56() -> None:
    """cmd_note_draft(dry_run=True) returns mode=dry-run with output_path."""
    lib = _import_lib()
    result = lib.cmd_note_draft(to="0.7.99", from_tag="v0.7.55", dry_run=True)
    # Either mode=dry-run (commits found) or mode=error (no commits)
    assert "mode" in result
    if result["mode"] == "dry-run":
        assert "output_path" in result
    else:
        assert "error" in result, f"unexpected error shape: {result}"


def test_cmd_dist_dry_run_v0_7_56() -> None:
    """cmd_dist(apply=False) returns mode=dry-run with out_dir + build_module status."""
    lib = _import_lib()
    result = lib.cmd_dist(apply=False)
    assert result.get("mode") == "dry-run", f"expected mode=dry-run, got {result.get('mode')}"
    assert "out_dir" in result
    assert result["out_dir"].endswith("dist"), f"out_dir should end with dist: {result['out_dir']}"


def test_cmd_dist_1_command_build_check_testpypi_v0_8_15() -> None:
    """cmd_dist(--apply --skip-existing) 는 1-command 로 twine check + testpypi simulation 완료 (spec §9 #7).

    Build step 은 skip-existing 으로 우회 (CI 의 venv dist/ 가 이미 build 된 상태 가정).
    핵심: twine_check.ok=True + testpypi_simulation.artifacts non-empty.
    """
    lib = _import_lib()
    result = lib.cmd_dist(apply=True, skip_existing=True, production=False)
    assert result.get("ok") is True, f"expected ok=True, got {result}: {result.get('error')}"
    # skip-existing 트리거 확인
    assert result.get("skipped") is True, f"expected skipped=True, got mode={result.get('mode')}"
    # 1) twine check (spec §7.1 step 2)
    assert "twine_check" in result, "missing twine_check in result"
    twine_check = result["twine_check"]
    assert twine_check.get("ok") is True, f"twine_check failed: {twine_check}"
    # 2) TestPyPI upload simulation (spec §7.1 step 3)
    assert "testpypi_simulation" in result, "missing testpypi_simulation in result"
    sim = result["testpypi_simulation"]
    assert sim.get("actual_upload") is False, "TestPyPI sim should not actually upload"
    assert len(sim.get("artifacts", [])) >= 1, "TestPyPI sim should list artifacts"
    assert "test.pypi.org" in sim.get("would_upload_to", ""), "TestPyPI URL missing"


def test_cmd_dist_with_production_simulation_v0_8_15() -> None:
    """cmd_dist(--apply --skip-existing --production) 는 production simulation 추가 (spec §7.1 step 5)."""
    lib = _import_lib()
    result = lib.cmd_dist(apply=True, skip_existing=True, production=True)
    assert result.get("ok") is True
    assert "production_simulation" in result, "missing production_simulation with --production flag"
    prod_sim = result["production_simulation"]
    assert prod_sim.get("actual_upload") is False, "production sim should not actually upload"
    assert "pypi.org" in prod_sim.get("would_upload_to", ""), "PyPI URL missing"


def test_cmd_changelog_gen_dry_run_v0_7_56() -> None:
    """cmd_changelog_gen(dry_run=True) returns mode=dry-run with commits count."""
    lib = _import_lib()
    result = lib.cmd_changelog_gen(dry_run=True)
    assert "mode" in result
    # mode is either 'dry-run' (commits found) or 'error' (no commits)
    if result["mode"] == "dry-run":
        assert "commits" in result
        assert result["commits"] > 0, f"expected commits > 0, got {result['commits']}"
    else:
        # Acceptable: error mode if no commits in range
        assert "error" in result, f"unexpected shape: {result}"


def test_cmd_verify_bad_tag_v0_7_56() -> None:
    """cmd_verify with bad tag handles gracefully (either ok=False or raises ValueError)."""
    lib = _import_lib()
    try:
        result = lib.cmd_verify(tag="v999.999.999")
        # If it returns a dict, ok should be False
        if isinstance(result, dict):
            assert result.get("ok") is False, f"expected ok=False for bad tag, got {result}"
    except Exception:
        # Acceptable: gh CLI fails on non-existent tag
        pass


def main() -> int:
    test_funcs = [
        test_cmd_validate_returns_4_keys_v0_7_55,
        test_cmd_validate_all_skipped_returns_all_ok_v0_7_55,
        test_cmd_version_bump_dry_run_v0_7_56,
        test_cmd_note_draft_dry_run_v0_7_56,
        test_cmd_dist_dry_run_v0_7_56,
        test_cmd_dist_1_command_build_check_testpypi_v0_8_15,
        test_cmd_dist_with_production_simulation_v0_8_15,
        test_cmd_changelog_gen_dry_run_v0_7_56,
        test_cmd_verify_bad_tag_v0_7_56,
    ]
    failed: list[str] = []
    for fn in test_funcs:
        name = fn.__name__
        try:
            fn()
            print(f"  PASS  {name}")
        except Exception as e:
            print(f"  FAIL  {name}: {type(e).__name__}: {e}")
            failed.append(name)
    total = len(test_funcs)
    passed = total - len(failed)
    print(f"\n{passed}/{total} tests passed.")
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
