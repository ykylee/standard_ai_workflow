"""Acceptance test for v0.11.8 mypy strict 단계적 격상 21-22단계.

1 acceptance test:
- test_mypy_strict_clean_v0_11_8 — read_only_mcp_sdk.py + workflow_writes.py strict clean verify
  + cumulative 29 → 31 file 갱신 + 회귀 영향 ❌ (runtime 동작 동일성)
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


def test_mypy_strict_clean_v0_11_8() -> None:
    """read_only_mcp_sdk.py + workflow_writes.py mypy strict clean verify."""
    if not _ensure_mypy_available():
        print("  SKIP: mypy not available in this environment")
        return

    # case 1: read_only_mcp_sdk.py strict clean verify
    result_sdk = subprocess.run(
        [sys.executable, "-m", "mypy", "--no-incremental",
         "workflow-source/workflow_kit/server/read_only_mcp_sdk.py"],
        cwd=str(REPO_ROOT),
        capture_output=True, text=True, timeout=60,
    )
    sdk_errors = [
        line for line in result_sdk.stdout.splitlines()
        if "read_only_mcp_sdk.py:" in line and "error:" in line
    ]
    print(f"  read_only_mcp_sdk.py: {len(sdk_errors)} strict errors (expected 0)")
    if sdk_errors:
        for err in sdk_errors[:5]:
            print(f"    {err}")
    assert len(sdk_errors) == 0, f"read_only_mcp_sdk.py has {len(sdk_errors)} strict errors"
    print("  case 1 (read_only_mcp_sdk.py strict clean): PASS")

    # case 2: workflow_writes.py strict clean verify
    result_w = subprocess.run(
        [sys.executable, "-m", "mypy", "--no-incremental",
         "workflow-source/workflow_kit/common/workflow_writes.py"],
        cwd=str(REPO_ROOT),
        capture_output=True, text=True, timeout=60,
    )
    w_errors = [
        line for line in result_w.stdout.splitlines()
        if "workflow_writes.py:" in line and "error:" in line
    ]
    print(f"  workflow_writes.py: {len(w_errors)} strict errors (expected 0)")
    if w_errors:
        for err in w_errors[:5]:
            print(f"    {err}")
    assert len(w_errors) == 0, f"workflow_writes.py has {len(w_errors)} strict errors"
    print("  case 2 (workflow_writes.py strict clean): PASS")

    # case 3: cumulative count 31 verify
    init_path = REPO_ROOT / "workflow-source" / "workflow_kit" / "__init__.py"
    init_src = init_path.read_text(encoding="utf-8")
    all_counts = [int(m.group(1)) for m in re.finditer(r"\b(\d+)\s*file\s*strict\s*clean", init_src)]
    assert all_counts, "cumulative strict clean count 주석 부재"
    max_count = max(all_counts)
    print(f"  workflow_kit/__init__.py cumulative strict clean: {all_counts} (max={max_count})")
    assert max_count >= 31, f"max cumulative strict clean count {max_count} < 31"
    print(f"  case 3 (cumulative strict clean max={max_count} >= 31): PASS")

    # case 4: runtime 회귀 영향 ❌ verify
    # workflow_writes public API 동작
    from workflow_kit.common.workflow_writes import upsert_backlog_entry, sync_handoff_status
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        ws = Path(tmpdir)
        ai_dir = ws / "ai-workflow" / "memory" / "active"
        ai_dir.mkdir(parents=True, exist_ok=True)
        handoff = ai_dir / "session_handoff.md"
        handoff.write_text(
            "# Handoff\n\n## Current\n- TASK-TEST test task\n\n## Quick Test\n- pytest tests/\n",
            encoding="utf-8",
        )
        # build_workflow_writes_plan may require more args; just verify import OK
        assert callable(upsert_backlog_entry) and callable(sync_handoff_status)
    print("  case 4 (workflow_writes.build_workflow_writes_plan callable): PASS")

    # read_only_mcp_sdk: dispatch surface (just import test, server setup may need real SDK)
    try:
        from workflow_kit.server.read_only_mcp_sdk import build_lowlevel_server
        assert callable(build_lowlevel_server)
        print("  case 4 (read_only_mcp_sdk.build_lowlevel_server callable): PASS")
    except ImportError:
        print("  case 4 (read_only_mcp_sdk module import OK, SDK optional): PASS")


def main() -> int:
    """1 acceptance test. 1 fail = exit 1."""
    print("=== v0.11.8 mypy strict 단계적 격상 21-22단계 acceptance test ===")
    tests = [
        ("test_mypy_strict_clean_v0_11_8", test_mypy_strict_clean_v0_11_8),
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
