"""Acceptance test for v0.11.7 mypy strict 단계적 격상 19-20단계.

1 acceptance test:
- test_mypy_strict_clean_v0_11_7 — workflow_kit_cli.py + doc_sync.py strict clean verify
  + cumulative 27 → 29 file 갱신 + 회귀 영향 ❌ (runtime 동작 동일성)
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


def test_mypy_strict_clean_v0_11_7() -> None:
    """workflow_kit_cli.py + doc_sync.py mypy strict clean verify."""
    if not _ensure_mypy_available():
        print("  SKIP: mypy not available in this environment")
        return

    # case 1: workflow_kit_cli.py strict clean verify
    result_cli = subprocess.run(
        [sys.executable, "-m", "mypy", "--no-incremental",
         "workflow-source/workflow_kit/workflow_kit_cli.py"],
        cwd=str(REPO_ROOT),
        capture_output=True, text=True, timeout=120,
    )
    cli_errors = [
        line for line in result_cli.stdout.splitlines()
        if "workflow_kit_cli.py:" in line and "error:" in line
    ]
    print(f"  workflow_kit_cli.py: {len(cli_errors)} strict errors (expected 0)")
    if cli_errors:
        for err in cli_errors[:5]:
            print(f"    {err}")
    assert len(cli_errors) == 0, f"workflow_kit_cli.py has {len(cli_errors)} strict errors"
    print("  case 1 (workflow_kit_cli.py strict clean): PASS")

    # case 2: doc_sync.py strict clean verify
    result_ds = subprocess.run(
        [sys.executable, "-m", "mypy", "--no-incremental",
         "workflow-source/workflow_kit/common/doc_sync.py"],
        cwd=str(REPO_ROOT),
        capture_output=True, text=True, timeout=60,
    )
    ds_errors = [
        line for line in result_ds.stdout.splitlines()
        if "doc_sync.py:" in line and "error:" in line
    ]
    print(f"  doc_sync.py: {len(ds_errors)} strict errors (expected 0)")
    if ds_errors:
        for err in ds_errors[:5]:
            print(f"    {err}")
    assert len(ds_errors) == 0, f"doc_sync.py has {len(ds_errors)} strict errors"
    print("  case 2 (doc_sync.py strict clean): PASS")

    # case 3: cumulative count 29 verify
    init_path = REPO_ROOT / "workflow-source" / "workflow_kit" / "__init__.py"
    init_src = init_path.read_text(encoding="utf-8")
    all_counts = [int(m.group(1)) for m in re.finditer(r"\b(\d+)\s*file\s*strict\s*clean", init_src)]
    assert all_counts, "cumulative strict clean count 주석 부재"
    max_count = max(all_counts)
    print(f"  workflow_kit/__init__.py cumulative strict clean: {all_counts} (max={max_count})")
    assert max_count >= 29, f"max cumulative strict clean count {max_count} < 29"
    print(f"  case 3 (cumulative strict clean max={max_count} >= 29): PASS")

    # case 4: runtime 회귀 영향 ❌ verify
    # workflow_kit_cli.cmd_ingest_purpose dispatch (refactored: purpose_context 직접 read)
    from workflow_kit.workflow_kit_cli import run_workflow_kit_cli
    # dry-run (--json, no --apply)
    result = run_workflow_kit_cli(["--command=ingest-purpose", "--json"])
    assert result == 0, f"ingest-purpose dry-run failed: exit {result}"
    print("  case 4 (cmd_ingest_purpose dry-run 정상, advisory emit): PASS")

    # cmd_graph_insights dispatch (sanity, 다른 subcommand)
    result2 = run_workflow_kit_cli(["--command=graph-insights"])
    assert result2 == 0
    print("  case 4 (cmd_graph_insights dry-run 정상): PASS")

    # doc_sync skill 동작
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        ws = Path(tmpdir)
        ai_dir = ws / "ai-workflow" / "memory" / "active"
        ai_dir.mkdir(parents=True, exist_ok=True)
        handoff = ai_dir / "session_handoff.md"
        handoff.write_text("# Handoff\n\n## Quick Test\n\n- pytest tests/\n", encoding="utf-8")
        # doc_sync 는 dispatcher 가 아닌 skill 이므로 import test only
        from workflow_kit.common.doc_sync import build_doc_sync_candidates
        candidates = build_doc_sync_candidates(
            project_root=ws,
            profile={},
            changed_files=[],
            session_handoff_path=handoff,
            work_backlog_index_path=None,
            latest_backlog_path=None,
            change_summary="test",
        )
        assert isinstance(candidates, dict)
        assert "impacted_documents" in candidates
    print(f"  case 4 (doc_sync.build_doc_sync_candidates 동작, {len(candidates)} candidates): PASS")


def main() -> int:
    """1 acceptance test. 1 fail = exit 1."""
    print("=== v0.11.7 mypy strict 단계적 격상 19-20단계 acceptance test ===")
    tests = [
        ("test_mypy_strict_clean_v0_11_7", test_mypy_strict_clean_v0_11_7),
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
