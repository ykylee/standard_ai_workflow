"""Acceptance test for v0.11.13 mypy CI cross-verify (Layer 1 ↔ Layer 2 정합).

1 acceptance test:
- test_mypy_ci_cross_verify_v0_11_13 — `_cross_verify_ci_mypy` helper + `_resolve_cross_verify_verdict`
  + cmd_release 통합 + argparse --skip-cross-verify / --strict-cross-verify flag
  + dispatcher 2 flag forwarding + release_pipeline_lib.cmd_release 2 kwarg
  + verdict matrix 4 outcome (sanity / drift_warning / ci_stale / ci_fail) + 실 gh CLI integration
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_mypy_ci_cross_verify_v0_11_13() -> None:
    """v0.11.13 mypy CI cross-verify (Layer 1 ↔ Layer 2 정합) verify."""
    # case 1: _cross_verify_ci_mypy helper 존재 + gh run list invocation
    rp_path = REPO_ROOT / "workflow-source" / "tools" / "release_pipeline.py"
    rp_text = rp_path.read_text(encoding="utf-8")
    assert "def _cross_verify_ci_mypy" in rp_text, "release_pipeline._cross_verify_ci_mypy helper 부재"
    # gh run list invocation (CI 조회)
    assert re.search(
        r"gh.*run.*list.*mypy-strict\.yml",
        rp_text,
        re.DOTALL,
    ), "gh run list --workflow mypy-strict.yml invocation 부재"
    # 6 verdict 정의 정합 (sanity / drift_warning / ci_stale / ci_fail / absent / skipped)
    # + 7th = no_local_verify
    expected_verdicts = {
        "sanity", "drift_warning", "ci_stale", "ci_fail", "absent", "skipped", "no_local_verify",
        "ci_sanity",  # internal Layer 1 only
    }
    found_verdicts = set(re.findall(r'"(sanity|drift_warning|ci_stale|ci_fail|absent|skipped|no_local_verify|ci_sanity)"', rp_text))
    missing = expected_verdicts - found_verdicts
    assert not missing, f"verdict 정의 누락: {missing}"
    print(f"  case 1 (_cross_verify_ci_mypy helper + gh run list + {len(found_verdicts)} verdict): PASS")

    # case 2: _resolve_cross_verify_verdict helper + verdict matrix
    assert "def _resolve_cross_verify_verdict" in rp_text, "_resolve_cross_verify_verdict helper 부재"
    # verdict matrix 의 4 분기 (ci_sanity + local ok / ci_sanity + local fail / ci_sanity + local skipped / non-ci_sanity)
    for verdict in ("sanity", "drift_warning", "no_local_verify", "ci_stale", "ci_fail", "absent", "skipped"):
        assert f'"{verdict}"' in rp_text, f"verdict {verdict!r} in _resolve_cross_verify_verdict 부재"
    print("  case 2 (_resolve_cross_verify_verdict helper + verdict matrix 4 분기): PASS")

    # case 3: argparse --skip-cross-verify / --strict-cross-verify flag
    assert re.search(
        r'p_rel\.add_argument\(["\']--skip-cross-verify',
        rp_text,
    ), "argparse --skip-cross-verify flag 부재"
    assert re.search(
        r'p_rel\.add_argument\(["\']--strict-cross-verify',
        rp_text,
    ), "argparse --strict-cross-verify flag 부재"
    print("  case 3 (argparse --skip-cross-verify / --strict-cross-verify): PASS")

    # case 4: cmd_release 의 cross-verify 통합 (1번 cross-verify, 2.5번 verdict 결합)
    # 1번 (cross-verify) + 2.5번 (_resolve_cross_verify_verdict 호출)
    assert "_cross_verify_ci_mypy()" in rp_text, "cmd_release 안의 _cross_verify_ci_mypy() 호출 부재"
    assert "_resolve_cross_verify_verdict(" in rp_text, "cmd_release 안의 _resolve_cross_verify_verdict() 호출 부재"
    # validate fail 시에도 cross-verify 결과 포함 (advisory)
    assert "validate_failed" in rp_text, "validate_failed flag 부재 (validate fail 시 cross-verify 결과 포함 정합)"
    print("  case 4 (cmd_release 의 1번 cross-verify + 2.5번 verdict 결합 + validate_failed flag): PASS")

    # case 5: cmd_release_create dispatcher 가 2 flag forwarding
    cli_path = REPO_ROOT / "workflow-source" / "workflow_kit" / "workflow_kit_cli.py"
    cli_text = cli_path.read_text(encoding="utf-8")
    create_section = re.search(
        r"def cmd_release_create.*?(?=\n\ndef |\nclass |\Z)",
        cli_text,
        re.DOTALL,
    )
    assert create_section, "cmd_release_create 함수 부재"
    create_text = create_section.group(0)
    for flag in ("--skip-cross-verify", "--strict-cross-verify"):
        assert flag in create_text, f"cmd_release_create dispatcher {flag} flag 부재"
    for kw in ("skip_cross_verify=", "strict_cross_verify="):
        assert kw in create_text, f"cmd_release_create dispatcher kwargs '{kw}' 부재"
    # docstring 에 2 flag 설명 (또는 둘 중 하나)
    for desc_alts in (
        ("mypy CI cross-verify",),  # --skip-cross-verify
        ("drift", "ci_stale", "ci_fail"),  # --strict-cross-verify
    ):
        assert any(d in create_text for d in desc_alts), (
            f"cmd_release_create docstring 설명 부재: {desc_alts!r}"
        )
    print("  case 5 (cmd_release_create dispatcher 2 flag forwarding + docstring): PASS")

    # case 6: release_pipeline_lib.cmd_release 2 kwarg forwarding + _make_args default
    lib_path = REPO_ROOT / "workflow-source" / "tools" / "release_pipeline_lib.py"
    lib_text = lib_path.read_text(encoding="utf-8")
    lib_release_section = re.search(
        r"def cmd_release\(.*?def ",
        lib_text,
        re.DOTALL,
    )
    assert lib_release_section, "release_pipeline_lib.cmd_release 함수 부재"
    lib_release_text = lib_release_section.group(0)
    for kw in ("skip_cross_verify:", "strict_cross_verify:"):
        assert kw in lib_release_text, f"release_pipeline_lib.cmd_release {kw} kwarg 부재"
    # _make_args default
    assert "skip_cross_verify" in lib_text and "strict_cross_verify" in lib_text, (
        "release_pipeline_lib._make_args 의 cross-verify flag default 부재"
    )
    print("  case 6 (release_pipeline_lib.cmd_release 2 kwarg + _make_args default): PASS")

    # case 7: helper 직접 실행 (실 gh CLI integration)
    # pytest-like fixture: CI 가 query 가능하면 sanity/ci_sanity verdict, query 불가하면 absent/skipped
    sys.path.insert(0, str(REPO_ROOT / "workflow-source"))
    sys.path.insert(0, str(REPO_ROOT / "workflow-source" / "tools"))
    from release_pipeline import _cross_verify_ci_mypy, _resolve_cross_verify_verdict
    ci_mypy = _cross_verify_ci_mypy()
    # verdict schema 정합
    assert "verdict" in ci_mypy, "ci_mypy.verdict 부재"
    assert "head_sha" in ci_mypy, "ci_mypy.head_sha 부재"
    assert "message" in ci_mypy, "ci_mypy.message 부재"
    verdict = ci_mypy.get("verdict")
    if verdict == "ci_sanity":
        # CI 정상: ci_run 도 있어야 함
        assert ci_mypy.get("ci_run") is not None, "ci_sanity verdict 인데 ci_run None"
        assert ci_mypy.get("ci_run", {}).get("conclusion") == "success", (
            f"ci_sanity 인데 ci_run.conclusion != success: {ci_mypy.get('ci_run', {}).get('conclusion')}"
        )
        print(f"  case 7 (_cross_verify_ci_mypy 실제 gh CLI integration: verdict={verdict!r}): PASS")
    elif verdict in ("absent", "skipped"):
        print(f"  case 7 (_cross_verify_ci_mypy: gh CLI absent/skipped, verdict={verdict!r}): SKIP")
    else:
        raise AssertionError(f"_cross_verify_ci_mypy unexpected verdict: {verdict!r}")

    # case 8: _resolve_cross_verify_verdict 의 4 outcome verify
    # helper 직접 호출로 verdict matrix 4 outcome 검증
    base_ci = {
        "verdict": "ci_sanity",
        "ci_run": {"conclusion": "success", "headSha": "abc1234", "databaseId": 1},
        "head_sha": "abc1234",
        "head_sha_match": True,
        "message": "test",
    }
    # 8a: ci_sanity + local ok → sanity
    local_ok = {"ok": True, "skipped": False, "error_count": 0}
    assert _resolve_cross_verify_verdict(base_ci, local_ok) == "sanity", (
        f"ci_sanity+local ok → expected 'sanity', got {_resolve_cross_verify_verdict(base_ci, local_ok)!r}"
    )
    # 8b: ci_sanity + local fail → drift_warning
    local_fail = {"ok": False, "skipped": False, "error_count": 3}
    assert _resolve_cross_verify_verdict(base_ci, local_fail) == "drift_warning", (
        f"ci_sanity+local fail → expected 'drift_warning', got {_resolve_cross_verify_verdict(base_ci, local_fail)!r}"
    )
    # 8c: ci_sanity + local skipped → no_local_verify
    local_skipped = {"ok": True, "skipped": True, "error_count": 0}
    assert _resolve_cross_verify_verdict(base_ci, local_skipped) == "no_local_verify", (
        f"ci_sanity+local skipped → expected 'no_local_verify', got {_resolve_cross_verify_verdict(base_ci, local_skipped)!r}"
    )
    # 8d: ci_fail (non-ci_sanity) → ci_fail (CI-only verdict 유지)
    ci_fail = {**base_ci, "verdict": "ci_fail"}
    assert _resolve_cross_verify_verdict(ci_fail, local_ok) == "ci_fail", (
        f"ci_fail → expected 'ci_fail', got {_resolve_cross_verify_verdict(ci_fail, local_ok)!r}"
    )
    # 8e: ci_stale → ci_stale
    ci_stale = {**base_ci, "verdict": "ci_stale"}
    assert _resolve_cross_verify_verdict(ci_stale, local_ok) == "ci_stale", (
        f"ci_stale → expected 'ci_stale', got {_resolve_cross_verify_verdict(ci_stale, local_ok)!r}"
    )
    # 8f: absent → absent
    absent = {**base_ci, "verdict": "absent"}
    assert _resolve_cross_verify_verdict(absent, local_ok) == "absent", (
        f"absent → expected 'absent', got {_resolve_cross_verify_verdict(absent, local_ok)!r}"
    )
    print("  case 8 (_resolve_cross_verify_verdict verdict matrix 6 outcome verify): PASS")


def main() -> int:
    """1 acceptance test. 1 fail = exit 1."""
    print("=== v0.11.13 mypy CI cross-verify (Layer 1 ↔ Layer 2) acceptance test ===")
    print("=== v0.11.12 의 '다음' §1 follow-up ===")
    tests = [
        ("test_mypy_ci_cross_verify_v0_11_13", test_mypy_ci_cross_verify_v0_11_13),
    ]
    passed = 0
    failed = 0
    for name, fn in tests:
        print(f"\n[{name}]")
        try:
            fn()
            passed += 1
            print(f"  ✓ {name} PASS")
        except AssertionError as e:
            failed += 1
            print(f"  ✗ {name} FAIL: {e}")
        except Exception as e:
            failed += 1
            print(f"  ✗ {name} ERROR: {type(e).__name__}: {e}")

    print(f"\n=== Result: {passed}/{passed+failed} PASS ===")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
