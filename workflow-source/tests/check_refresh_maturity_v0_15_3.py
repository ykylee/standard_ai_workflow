#!/usr/bin/env python3
"""Smoke test — refresh-maturity 의 v0.15.3+ release_error gate 정합.

v0.14.6 의 out-of-scope 2 해소 정합성 검증. step 6.7 가 release_error
(`results["error"]` 존재) 시에만 maturity refresh 호출.

3 cases:
  1) release_error 부재 (성공): step 6.7 의 `maturity_refresh` 가
     `skipped_due_to_release_success: True` field 포함 — refresh 호출 안 됨
  2) release_error 존재 (실패): step 6.7 의 `maturity_refresh` 가
     `refreshed: bool` field 포함 (실제 refresh 호출) + `before` / `after` 정합
  3) release_error + --no-legacy-memory: 두 gate 모두 적용,
     `legacy_memory_strict_opt_out: True` field 포함
"""

from __future__ import annotations

import argparse
import io
import json
import sys
from contextlib import redirect_stdout
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "workflow-source" / "tools" / "release_pipeline.py"
MATURITY_PATH = REPO_ROOT / "workflow-source" / "core" / "maturity_matrix.json"


def _emulate_step_6_7(*, error_present: bool, legacy_memory: bool | None) -> dict:
    """step 6.7 의 로직을 emulate (실제 cmd_release 호출 없이).

    cmd_release 는 외부 의존성 (gh, network) 이 있어, step 6.7 의 release_error
    gate 검증만 inline 으로 분리.
    """
    args = argparse.Namespace(
        dry_run=False,
        skip_self_recover=False,
        skip_bidir_link=False,
        legacy_memory=legacy_memory,
    )
    results: dict = {}
    if error_present:
        results["error"] = f"simulated release_error: gh release create failed (exit 1)"

    # release_pipeline 의 step 6.7 로직 그대로 emulate
    import sys as _sys
    if str(REPO_ROOT / "workflow-source" / "tools") not in _sys.path:
        _sys.path.insert(0, str(REPO_ROOT / "workflow-source" / "tools"))
    import release_pipeline

    release_error = "error" in results
    buf = io.StringIO()
    if release_error and not getattr(args, "dry_run", False) and release_pipeline.refresh_maturity_last_updated is not None:
        with redirect_stdout(buf):
            try:
                maturity_result = release_pipeline.cmd_refresh_maturity(args)
                results["maturity_refresh"] = maturity_result
            except Exception as exc:  # noqa: BLE001
                results["maturity_refresh"] = {"error": str(exc), "warning": True}
                print(f"  [maturity] WARN: {exc}")
    elif not release_error:
        results["maturity_refresh"] = {
            "skipped_due_to_release_success": True,
            "reason": "v0.15.3+ release 성공 시 maturity refresh skip. release_error fallback 만 호출.",
        }
    return results


def case_1_release_success_skip() -> bool:
    """1) release_error 부재 (성공): step 6.7 skip — `skipped_due_to_release_success: True`."""
    results = _emulate_step_6_7(error_present=False, legacy_memory=None)
    mr = results.get("maturity_refresh", {})
    if mr.get("skipped_due_to_release_success") is not True:
        print(f"  FAIL: release 성공 시 skip 안 됨: {mr}")
        return False
    if "refreshed" in mr:
        print(f"  FAIL: release 성공 시 refreshed field 부재해야 함: {mr}")
        return False
    if "release_error" not in mr.get("reason", "").lower():
        print(f"  FAIL: reason should mention 'release_error': {mr.get('reason')!r}")
        return False
    return True


def case_2_release_error_refresh() -> bool:
    """2) release_error 존재 (실패): step 6.7 호출 — `refreshed: bool` + before/after 정합."""
    # baseline 캡처
    mm_before = json.loads(MATURITY_PATH.read_text(encoding="utf-8"))
    last_updated_before = mm_before.get("last_updated")

    results = _emulate_step_6_7(error_present=True, legacy_memory=None)
    mr = results.get("maturity_refresh", {})
    if mr.get("skipped_due_to_release_success") is True:
        print(f"  FAIL: release_error 시 skip 표시됨 (호출되어야 함): {mr}")
        return False
    if "refreshed" not in mr:
        print(f"  FAIL: release_error 시 refreshed field 부재: {mr}")
        return False
    if "error" in mr:
        print(f"  FAIL: release_error 시 error field: {mr}")
        return False
    # 실제 file 정합 (already today 면 refreshed=False 이지만 호출은 됨)
    mm_after = json.loads(MATURITY_PATH.read_text(encoding="utf-8"))
    if mm_after.get("last_updated") != last_updated_before:
        print(f"  FAIL: file last_updated changed unexpectedly: {last_updated_before!r} -> {mm_after.get('last_updated')!r}")
        return False
    return True


def case_3_release_error_with_legacy_strict() -> bool:
    """3) release_error + --no-legacy-memory: 두 gate 모두 — strict opt-out 우선."""
    results = _emulate_step_6_7(error_present=True, legacy_memory=False)
    mr = results.get("maturity_refresh", {})
    if mr.get("skipped_due_to_release_success") is True:
        print(f"  FAIL: release_error + strict opt-out 시 skip 표시: {mr}")
        return False
    if mr.get("legacy_memory_strict_opt_out") is not True:
        print(f"  FAIL: --no-legacy-memory strict opt-out flag 부재: {mr}")
        return False
    if mr.get("refreshed") is not False:
        print(f"  FAIL: strict opt-out 시 refreshed=True (skip 되어야 함): {mr}")
        return False
    if "skip_reason" not in mr:
        print(f"  FAIL: skip_reason missing: {mr}")
        return False
    return True


def main() -> int:
    cases = [
        ("case_1_release_success_skip", case_1_release_success_skip),
        ("case_2_release_error_refresh", case_2_release_error_refresh),
        ("case_3_release_error_with_legacy_strict", case_3_release_error_with_legacy_strict),
    ]
    results: list[tuple[str, bool]] = []
    for name, fn in cases:
        results.append((name, fn()))
    passed = sum(1 for _, ok in results if ok)
    for name, ok in results:
        marker = "PASS" if ok else "FAIL"
        print(f"  [{marker}] {name}")
    print(f"\n=== {passed}/{len(cases)} PASS ===")
    if passed != len(cases):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
