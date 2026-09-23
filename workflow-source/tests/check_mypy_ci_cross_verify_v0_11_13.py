"""Acceptance test for v0.11.13 mypy CI cross-verify (Layer 1 ↔ Layer 2 정합).

1 acceptance test:
- test_mypy_ci_cross_verify_v0_11_13 — `_cross_verify_ci_mypy` helper + `_resolve_cross_verify_verdict`
  + cmd_release 통합 + argparse --skip-cross-verify / --strict-cross-verify flag
  + dispatcher 2 flag forwarding + release_pipeline_lib.cmd_release 2 kwarg
  + verdict matrix 4 outcome (sanity / drift_warning / ci_stale / ci_fail)

2026-09-23 CI workflow 폐지(TASK-2026-09-23-main-022)로 Layer 1(`mypy-strict.yml`)이
사라졌다. `_cross_verify_ci_mypy` 는 이제 gh 를 부르지 않고 늘 ``skipped`` 를 낸다 —
case 1 은 그 행동(gh 미호출 + skipped)을 재고, 실 gh CLI integration 을 재던 case 7 은
대상을 잃어 삭제했다. verdict 매트릭스(case 8)와 플래그 배선(case 2~6)은 인터페이스가
남아 있는 동안 유지한다.
"""
from __future__ import annotations

#: 이 검사의 입력 표면 (spec `core/test_impact_tiering_spec.md` §2).
#: 게이트 채취 실측에서 뽑아 넓은 쪽으로 올렸다 — 좁으면 meta-watch 가 red 로 잡는다.
WATCHES = (
    "workflow-source/pyproject.toml",
    "workflow-source/workflow_kit/*",
)

import re
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def _observe_cross_verify() -> tuple[dict, list[list[str]]]:
    """`_cross_verify_ci_mypy()` 를 실제로 부르고, 그 사이 띄운 subprocess argv 를 모은다."""
    sys.path.insert(0, str(REPO_ROOT / "workflow-source"))
    sys.path.insert(0, str(REPO_ROOT / "workflow-source" / "workflow_kit" / "tools"))
    from release_pipeline import _cross_verify_ci_mypy

    spawned: list[list[str]] = []
    real_run = subprocess.run

    def _recording_run(argv, *args, **kwargs):  # type: ignore[no-untyped-def]
        spawned.append([str(a) for a in argv] if isinstance(argv, (list, tuple)) else [str(argv)])
        return real_run(argv, *args, **kwargs)

    subprocess.run = _recording_run  # type: ignore[assignment]
    try:
        result = _cross_verify_ci_mypy()
    finally:
        subprocess.run = real_run  # type: ignore[assignment]
    return result, spawned


def test_mypy_ci_cross_verify_v0_11_13() -> None:
    """v0.11.13 mypy CI cross-verify (Layer 1 ↔ Layer 2 정합) verify."""
    # case 1: _cross_verify_ci_mypy 는 Layer 1 폐지(main-022) 후 **gh 를 부르지 않고**
    # 늘 skipped 를 낸다. 옛 mypy-strict run 을 집으면 영구 ci_stale 이 되므로,
    # gh 호출이 되살아나면 red 다.
    rp_path = REPO_ROOT / "workflow-source" / "workflow_kit" / "tools" / "release_pipeline.py"
    rp_text = rp_path.read_text(encoding="utf-8")
    assert "def _cross_verify_ci_mypy" in rp_text, "release_pipeline._cross_verify_ci_mypy helper 부재"
    ci_mypy, spawned = _observe_cross_verify()
    gh_calls = [argv for argv in spawned if argv and Path(argv[0]).name == "gh"]
    assert not gh_calls, f"폐지된 Layer 1 을 조회하려고 gh 를 불렀다: {gh_calls}"
    assert ci_mypy.get("verdict") == "skipped", (
        f"Layer 1 폐지 후 verdict 는 skipped 여야 한다: {ci_mypy.get('verdict')!r}"
    )
    assert ci_mypy.get("ci_run") is None, f"조회하지 않았는데 ci_run 이 있다: {ci_mypy.get('ci_run')!r}"
    for key in ("verdict", "head_sha", "message"):
        assert key in ci_mypy, f"ci_mypy.{key} 부재 (출력 스키마)"
    assert "main-022" in str(ci_mypy.get("message")), (
        f"skipped 사유가 폐지를 말하지 않는다: {ci_mypy.get('message')!r}"
    )
    # 6 verdict 정의 정합 (sanity / drift_warning / ci_stale / ci_fail / absent / skipped)
    # + 7th = no_local_verify
    expected_verdicts = {
        "sanity", "drift_warning", "ci_stale", "ci_fail", "absent", "skipped", "no_local_verify",
        "ci_sanity",  # internal Layer 1 only
    }
    found_verdicts = set(re.findall(r'"(sanity|drift_warning|ci_stale|ci_fail|absent|skipped|no_local_verify|ci_sanity)"', rp_text))
    missing = expected_verdicts - found_verdicts
    assert not missing, f"verdict 정의 누락: {missing}"
    print(f"  case 1 (_cross_verify_ci_mypy: gh 미호출 + skipped + {len(found_verdicts)} verdict): PASS")

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
    lib_path = REPO_ROOT / "workflow-source" / "workflow_kit" / "tools" / "release_pipeline_lib.py"
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

    from release_pipeline import _resolve_cross_verify_verdict

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
