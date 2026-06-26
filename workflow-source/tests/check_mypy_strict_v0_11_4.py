"""Acceptance test for v0.11.4 mypy strict 단계적 격상 13-14단계.

1 acceptance test:
- test_mypy_strict_clean_v0_11_4 — output_contracts.py + milestones.py strict clean verify
  + cumulative 21 → 23 file 갱신 + 회귀 영향 ❌ (runtime 동작 동일성)
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


def test_mypy_strict_clean_v0_11_4() -> None:
    """output_contracts.py + milestones.py mypy strict clean verify."""
    if not _ensure_mypy_available():
        print("  SKIP: mypy not available in this environment")
        return

    # case 1: output_contracts.py strict clean verify
    result_oc = subprocess.run(
        [sys.executable, "-m", "mypy", "--no-incremental",
         "workflow-source/workflow_kit/common/output_contracts.py"],
        cwd=str(REPO_ROOT),
        capture_output=True, text=True, timeout=60,
    )
    oc_errors = [
        line for line in result_oc.stdout.splitlines()
        if "output_contracts.py:" in line and "error:" in line
    ]
    print(f"  output_contracts.py: {len(oc_errors)} strict errors (expected 0)")
    if oc_errors:
        for err in oc_errors:
            print(f"    {err}")
    assert len(oc_errors) == 0, f"output_contracts.py has {len(oc_errors)} strict errors"
    print("  case 1 (output_contracts.py strict clean): PASS")

    # case 2: milestones.py strict clean verify
    result_ms = subprocess.run(
        [sys.executable, "-m", "mypy", "--no-incremental",
         "workflow-source/workflow_kit/common/milestones.py"],
        cwd=str(REPO_ROOT),
        capture_output=True, text=True, timeout=60,
    )
    ms_errors = [
        line for line in result_ms.stdout.splitlines()
        if "milestones.py:" in line and "error:" in line
    ]
    print(f"  milestones.py: {len(ms_errors)} strict errors (expected 0)")
    if ms_errors:
        for err in ms_errors:
            print(f"    {err}")
    assert len(ms_errors) == 0, f"milestones.py has {len(ms_errors)} strict errors"
    print("  case 2 (milestones.py strict clean): PASS")

    # case 3: workflow_kit/__init__.py cumulative count 갱신 (21 → 23)
    init_path = REPO_ROOT / "workflow-source" / "workflow_kit" / "__init__.py"
    init_src = init_path.read_text(encoding="utf-8")
    all_counts = [int(m.group(1)) for m in re.finditer(r"\b(\d+)\s*file\s*strict\s*clean", init_src)]
    assert all_counts, "cumulative strict clean count 주석 부재"
    max_count = max(all_counts)
    print(f"  workflow_kit/__init__.py cumulative strict clean: {all_counts} (max={max_count})")
    assert max_count >= 23, f"max cumulative strict clean count {max_count} < 23"
    print(f"  case 3 (cumulative strict clean max={max_count} >= 23): PASS")

    # case 4: runtime 회귀 영향 ❌ verify (output_contracts 주요 API 동작 동일)
    from workflow_kit.common.output_contracts import (
        output_json_schema_bundle,
        output_json_schema_for_family,
        validate_output_payload,
        ErrorOutput,
    )

    # output_json_schema_bundle 정상 동작
    bundle = output_json_schema_bundle()
    assert "outputs" in bundle
    assert "errors" in bundle
    assert isinstance(bundle["outputs"], dict)
    assert isinstance(bundle["errors"], dict)
    print(f"  case 4 (output_json_schema_bundle 동작, {len(bundle['outputs'])} families): PASS")

    # output_json_schema_for_family 정상 동작
    schema = output_json_schema_for_family("session_start")
    assert isinstance(schema, dict)
    assert "type" in schema or "properties" in schema
    print(f"  case 4 (output_json_schema_for_family 동작): PASS")

    # validate_output_payload 정상 동작
    valid_payload = {"status": "ok", "summary": ["test"], "source_documents": {"session_handoff_path": "x", "work_backlog_index_path": "y", "project_profile_path": "z"}}
    errors = validate_output_payload(valid_payload, family="session_start")
    assert isinstance(errors, list)
    print(f"  case 4 (validate_output_payload 동작, errors={len(errors)}): PASS")

    # milestones assess_milestone_progress 정상 동작 (Path 인자 필요)
    from workflow_kit.common.milestones import assess_milestone_progress
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        matrix_path = Path(tmpdir) / "matrix.json"
        backlog_path = Path(tmpdir) / "backlog.md"
        matrix_path.write_text('{"milestones": {}}', encoding="utf-8")
        backlog_path.write_text("---\n---\n\n# Backlog\n", encoding="utf-8")
        result = assess_milestone_progress(matrix_path, backlog_path)
        assert isinstance(result, dict)
        assert "status" in result
    print("  case 4 (assess_milestone_progress 동작): PASS")


def main() -> int:
    """1 acceptance test. 1 fail = exit 1."""
    print("=== v0.11.4 mypy strict 단계적 격상 13-14단계 acceptance test ===")
    tests = [
        ("test_mypy_strict_clean_v0_11_4", test_mypy_strict_clean_v0_11_4),
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
