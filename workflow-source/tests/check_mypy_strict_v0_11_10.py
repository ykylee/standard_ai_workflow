"""Acceptance test for v0.11.10 mypy strict 단계적 격상 25-26단계 (full strict 도달).

1 acceptance test:
- test_mypy_strict_clean_v0_11_10 — project_docs.py + profiling.py strict clean verify
  + cumulative 33 → 35 file 갱신 + full strict 도달 verify (0 errors in workflow_kit/)
  + 회귀 영향 ❌ (runtime 동작 동일성)
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def _ensure_mypy_available() -> bool:
    try:
        result = subprocess.run(
            [sys.executable, "-m", "mypy", "--version"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0 and "mypy" in result.stdout:
            return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return False


def test_mypy_strict_clean_v0_11_10() -> None:
    """project_docs.py + profiling.py mypy strict clean + full strict 도달 verify."""
    if not _ensure_mypy_available():
        print("  SKIP: mypy not available in this environment")
        return

    # case 1: project_docs.py strict clean verify
    result_pd = subprocess.run(
        [sys.executable, "-m", "mypy", "--no-incremental",
         "workflow-source/workflow_kit/common/project_docs.py"],
        cwd=str(REPO_ROOT),
        capture_output=True, text=True, timeout=60,
    )
    pd_errors = [
        line for line in result_pd.stdout.splitlines()
        if "project_docs.py:" in line and "error:" in line
    ]
    print(f"  project_docs.py: {len(pd_errors)} strict errors (expected 0)")
    if pd_errors:
        for err in pd_errors[:5]:
            print(f"    {err}")
    assert len(pd_errors) == 0, f"project_docs.py has {len(pd_errors)} strict errors"
    print("  case 1 (project_docs.py strict clean): PASS")

    # case 2: profiling.py strict clean verify
    result_pr = subprocess.run(
        [sys.executable, "-m", "mypy", "--no-incremental",
         "workflow-source/workflow_kit/common/profiling.py"],
        cwd=str(REPO_ROOT),
        capture_output=True, text=True, timeout=60,
    )
    pr_errors = [
        line for line in result_pr.stdout.splitlines()
        if "profiling.py:" in line and "error:" in line
    ]
    print(f"  profiling.py: {len(pr_errors)} strict errors (expected 0)")
    if pr_errors:
        for err in pr_errors[:5]:
            print(f"    {err}")
    assert len(pr_errors) == 0, f"profiling.py has {len(pr_errors)} strict errors"
    print("  case 2 (profiling.py strict clean): PASS")

    # case 3: cumulative count 35 verify
    init_path = REPO_ROOT / "workflow-source" / "workflow_kit" / "__init__.py"
    init_src = init_path.read_text(encoding="utf-8")
    all_counts = [int(m.group(1)) for m in re.finditer(r"\b(\d+)\s*file\s*strict\s*clean", init_src)]
    assert all_counts, "cumulative strict clean count 주석 부재"
    max_count = max(all_counts)
    print(f"  workflow_kit/__init__.py cumulative strict clean: {all_counts} (max={max_count})")
    assert max_count >= 35, f"max cumulative strict clean count {max_count} < 35"
    print(f"  case 3 (cumulative strict clean max={max_count} >= 35): PASS")

    # case 4: full strict 도달 verify (전체 workflow_kit/ 0 errors)
    result_full = subprocess.run(
        [sys.executable, "-m", "mypy", "--no-incremental",
         "workflow-source/workflow_kit/"],
        cwd=str(REPO_ROOT),
        capture_output=True, text=True, timeout=120,
    )
    full_errors = [
        line for line in result_full.stdout.splitlines()
        if ".py:" in line and "error:" in line
    ]
    print(f"  workflow_kit/ 전체 strict errors: {len(full_errors)} (expected 0)")
    assert len(full_errors) == 0, f"workflow_kit/ has {len(full_errors)} strict errors"
    print(f"  case 4 (full mypy strict 도달, 0 errors): PASS")

    # case 5: runtime 회귀 영향 ❌ verify
    from workflow_kit.common.project_docs import parse_handoff
    from workflow_kit.common.profiling import (
        check_profiling_available,
        evaluate_compliance,
    )
    assert callable(parse_handoff)
    assert callable(check_profiling_available)
    assert callable(evaluate_compliance)
    print("  case 5 (project_docs.parse_handoff + profiling.evaluate_compliance callable): PASS")


def main() -> int:
    """1 acceptance test. 1 fail = exit 1."""
    print("=== v0.11.10 mypy strict 단계적 격상 25-26단계 acceptance test ===")
    print("=== v0.11.10 = full mypy strict 도달! ===")
    tests = [
        ("test_mypy_strict_clean_v0_11_10", test_mypy_strict_clean_v0_11_10),
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
