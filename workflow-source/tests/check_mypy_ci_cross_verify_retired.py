"""mypy CI cross-verify (v0.11.13) 은퇴 검사 — TASK-2026-09-24-main-001.

v0.11.13 은 release 가 Layer 1(GH Actions `mypy-strict.yml`) 결과와 Layer 2(validate 의
local mypy)를 대조해 `ci_mypy` verdict 를 냈다. 2026-09-23 CI 폐지(main-022)로 Layer 1
이 사라지자 그 helper 는 늘 ``skipped`` 를 내는 껍데기가 됐고, 이 task 가 표면을 걷었다.

이 검사가 재는 것 (옛 파일 `check_mypy_ci_cross_verify_v0_11_13.py` 를 대체):

- case 1: cross-verify helper 3종(`_cross_verify_ci_mypy` · `_resolve_cross_verify_verdict`
  · `release_status._check_ci_mypy`)이 되살아나지 않았다. 늘 skipped 인 칸은 재는 것이
  없는데 숫자는 멀쩡해 보이는 판정이라, 돌아오면 red 다.
- case 2: 옛 플래그 `--skip-cross-verify` / `--strict-cross-verify` 는 **받기만 한다**.
  소비자 호출이 argparse 에서 깨지지 않고, stderr 로 은퇴를 알리며, 결과에 `ci_mypy` 가
  없고, `--strict-cross-verify` 가 release 를 막지 않는다 (막을 근거가 없다).
"""
from __future__ import annotations

#: 이 검사의 입력 표면 (spec `core/test_impact_tiering_spec.md` §2).
WATCHES = (
    "workflow-source/workflow_kit/*",
)

import json
import os
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
PIPELINE_PY = SOURCE_ROOT / "workflow_kit" / "tools" / "release_pipeline.py"
RELEASE_STATUS_PY = SOURCE_ROOT / "workflow_kit" / "release_status.py"


def _run_release(*extra: str) -> subprocess.CompletedProcess[str]:
    # 저장소에 아무것도 쓰지 않는 dry-run 단말 경로 (check_release_pre_check_gates 와 같은 skip 집합).
    argv = [sys.executable, str(PIPELINE_PY), "release", "--version", "9.9.9",
            "--skip-validate", "--skip-self-recover",
            "--skip-bidir-link", "--skip-doc-headers-update",
            "--skip-maturity-matrix-sync", "--skip-changelog-gen",
            "--skip-smoke-count-check", "--json", *extra]
    return subprocess.run(
        argv, capture_output=True, text=True, timeout=120,
        env={**os.environ, "PYTHONPATH": str(SOURCE_ROOT)},
    )


def test_cross_verify_helpers_retired() -> None:
    rp_text = PIPELINE_PY.read_text(encoding="utf-8")
    rs_text = RELEASE_STATUS_PY.read_text(encoding="utf-8")
    for name, text in (("_cross_verify_ci_mypy", rp_text),
                       ("_resolve_cross_verify_verdict", rp_text),
                       ("_check_ci_mypy", rs_text)):
        assert f"def {name}" not in text, f"은퇴한 {name} 가 되살아났다"
    print("  case 1 (cross-verify helper 3종 부재): PASS")


def test_retired_flags_are_accepted_noop() -> None:
    proc = _run_release("--skip-cross-verify", "--strict-cross-verify")
    assert "unrecognized arguments" not in proc.stderr, (
        f"옛 플래그가 argparse 에서 거부됐다 — 소비자 호출이 깨진다: {proc.stderr[-400:]!r}"
    )
    try:
        result = json.loads(proc.stdout)
    except json.JSONDecodeError as e:
        raise AssertionError(
            f"release --json 출력을 못 읽었다 ({e}): stdout={proc.stdout[-400:]!r} "
            f"stderr={proc.stderr[-400:]!r}"
        ) from None
    for flag in ("--skip-cross-verify", "--strict-cross-verify"):
        assert f"{flag} 는 은퇴했다" in proc.stderr, f"{flag} 은퇴 경고가 stderr 에 없다: {proc.stderr[-400:]!r}"
    assert "ci_mypy" not in result, f"은퇴한 ci_mypy 가 결과에 남았다: {result.get('ci_mypy')!r}"
    assert "ci_mypy" not in str(result.get("summary")), f"summary 에 ci_mypy 가 남았다: {result.get('summary')!r}"
    assert "cross-verify" not in str(result.get("error") or ""), (
        f"--strict-cross-verify 가 여전히 release 를 막는다: {result.get('error')!r}"
    )
    print("  case 2 (옛 플래그 수용 + stderr 경고 + ci_mypy 부재 + strict 무효): PASS")


def main() -> int:
    print("=== mypy CI cross-verify 은퇴 검사 (TASK-2026-09-24-main-001) ===")
    tests = [
        ("test_cross_verify_helpers_retired", test_cross_verify_helpers_retired),
        ("test_retired_flags_are_accepted_noop", test_retired_flags_are_accepted_noop),
    ]
    passed = failed = 0
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
