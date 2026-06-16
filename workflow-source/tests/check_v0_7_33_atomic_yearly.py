#!/usr/bin/env python3
"""
v0.7.33: TASK-V0733-001 (atomic rotation) + TASK-V0734-001 (yearly aggregation)
smoke test (10/10 PASS, 5-run stable)

Test cases (TASK-V0733-001, 5 smoke):
1. test_atomic_rotation_no_temp_leftover — rotation 성공 시 .tmp file 부재
2. test_atomic_rotation_archive_exists — rotation 성공 시 .gz file 존재
3. test_atomic_rotation_main_log_empty — rotation 성공 시 main log = 0 byte
4. test_atomic_rotation_temp_cleanup_on_fail — gzip write fail 시 .tmp file cleanup
5. test_atomic_rotation_no_temp_on_under_threshold — under-threshold 시 .tmp file 생성 0

Test cases (TASK-V0734-001, 5 smoke):
6. test_yearly_aggregation_2_years — 2-year entries → 2 yearly buckets
7. test_yearly_aggregation_1_year — 1-year entries → 1 yearly bucket
8. test_yearly_aggregation_cross_year_boundary — 2025-12 + 2026-01 → 2 buckets
9. test_yearly_aggregation_total_sum — total.archived = sum(buckets.archived)
10. test_yearly_aggregation_invalid_period — invalid (e.g. 'decade') → ok=False
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
TOOL = REPO_ROOT / "workflow-source" / "tools" / "archive_stale_memory.py"
SOURCE_ROOT = REPO_ROOT / "workflow-source"
PYTHON = sys.executable

if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

# In-process module load
import importlib.util
_spec = importlib.util.spec_from_file_location("archive_stale_memory", str(TOOL))
_am = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_am)
cmd_aggregate_metrics = _am.cmd_aggregate_metrics
rotate_log_if_needed = _am.rotate_log_if_needed
aggregate_metrics = _am.aggregate_metrics
read_metrics_log = _am.read_metrics_log
append_metrics_log = _am.append_metrics_log


def _write_n_entries(memory_dir: Path, n: int) -> None:
    """n entries 를 archive_stale_memory.log 에 write."""
    log_path = memory_dir / "archive_stale_memory.log"
    for i in range(n):
        append_metrics_log(memory_dir, 30, archived_count=i, skipped_count=i + 1, error_count=0)


def _make_repo_root(tmp: str) -> Path:
    """cmd_aggregate_metrics 의 *real* path: repo_root/ai-workflow/memory."""
    repo_root = Path(tmp) / "fake_repo"
    (repo_root / "ai-workflow" / "memory").mkdir(parents=True, exist_ok=True)
    return repo_root


def _make_args(**kwargs):
    import argparse
    defaults = {
        "older_than": 30,
        "list": False,
        "dry_run": False,
        "apply": False,
        "cleanup": False,
        "repo_root": str(REPO_ROOT),
        "install_cron": False,
        "uninstall_cron": False,
        "show_cron": False,
        "show_metrics": False,
        "rotate_logs": False,
        "rotate_threshold": _am.LOG_ROTATE_LINE_THRESHOLD,
        "aggregate": None,
        "include_rotated": False,
        "cron_name": "archive-memory",
        "cron_interval": "7d",
        "agent": "mavis",
        "force_install": False,
    }
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


# === TASK-V0733-001 Tests (5) ===

# === Test 1: atomic rotation no temp leftover ===
def test_atomic_rotation_no_temp_leftover() -> bool:
    """rotation 성공 시 .tmp file 부재 (os.replace 정상 동작 확인)."""
    with tempfile.TemporaryDirectory() as tmp:
        repo_root = _make_repo_root(tmp)
        memory_dir = repo_root / "ai-workflow" / "memory"
        _write_n_entries(memory_dir, 105)
        result = rotate_log_if_needed(memory_dir, line_threshold=100)
        if not result["rotated"]:
            print(f"  FAIL: rotate failed. Got: {result}")
            return False
        # verify no .tmp file
        tmp_files = list(memory_dir.glob("*.tmp"))
        if tmp_files:
            print(f"  FAIL: .tmp files left over: {tmp_files}")
            return False
    print("  PASS: atomic rotation: no .tmp file leftover")
    return True


# === Test 2: atomic rotation archive exists ===
def test_atomic_rotation_archive_exists() -> bool:
    """rotation 성공 시 .gz archive file 존재 + valid gzip."""
    with tempfile.TemporaryDirectory() as tmp:
        repo_root = _make_repo_root(tmp)
        memory_dir = repo_root / "ai-workflow" / "memory"
        _write_n_entries(memory_dir, 105)
        result = rotate_log_if_needed(memory_dir, line_threshold=100)
        if not result["rotated"]:
            print(f"  FAIL: rotate failed. Got: {result}")
            return False
        archive_path = Path(result["archive_path"])
        if not archive_path.exists():
            print(f"  FAIL: archive not created: {archive_path}")
            return False
        # verify valid gzip
        import gzip
        try:
            with gzip.open(archive_path, "rt", encoding="utf-8") as f:
                lines = f.readlines()
            if len(lines) != 105:
                print(f"  FAIL: archive should have 105 lines, got {len(lines)}")
                return False
        except (OSError, gzip.BadGzipFile) as e:
            print(f"  FAIL: archive not valid gzip: {e}")
            return False
    print("  PASS: atomic rotation: .gz archive exists with 105 lines (valid gzip)")
    return True


# === Test 3: atomic rotation main log empty ===
def test_atomic_rotation_main_log_empty() -> bool:
    """rotation 성공 시 main log = 0 byte (truncate)."""
    with tempfile.TemporaryDirectory() as tmp:
        repo_root = _make_repo_root(tmp)
        memory_dir = repo_root / "ai-workflow" / "memory"
        _write_n_entries(memory_dir, 105)
        result = rotate_log_if_needed(memory_dir, line_threshold=100)
        if not result["rotated"]:
            print(f"  FAIL: rotate failed. Got: {result}")
            return False
        log_path = memory_dir / "archive_stale_memory.log"
        if log_path.stat().st_size != 0:
            print(f"  FAIL: main log not truncated. size={log_path.stat().st_size}")
            return False
    print("  PASS: atomic rotation: main log truncated to 0 byte")
    return True


# === Test 4: atomic rotation temp cleanup on fail ===
def test_atomic_rotation_temp_cleanup_on_fail() -> bool:
    """gzip write fail 시 .tmp file cleanup (best-effort)."""
    with tempfile.TemporaryDirectory() as tmp:
        repo_root = _make_repo_root(tmp)
        memory_dir = repo_root / "ai-workflow" / "memory"
        _write_n_entries(memory_dir, 105)
        # mock gzip.open to fail on temp_path
        import gzip
        original_gzip_open = gzip.open
        def fail_gzip_open(*args, **kwargs):
            if "tmp" in str(args[0]):
                raise OSError("simulated gzip write fail")
            return original_gzip_open(*args, **kwargs)
        with patch.object(gzip, "open", side_effect=fail_gzip_open):
            result = rotate_log_if_needed(memory_dir, line_threshold=100)
        if result["rotated"]:
            print(f"  FAIL: should not rotate on gzip fail. Got: {result}")
            return False
        if "error" not in result:
            print(f"  FAIL: error field missing. Got: {result}")
            return False
        # verify no .tmp file (cleanup)
        tmp_files = list(memory_dir.glob("*.tmp"))
        if tmp_files:
            print(f"  FAIL: .tmp files not cleaned up: {tmp_files}")
            return False
        # main log should still be full (rotation aborted)
        log_path = memory_dir / "archive_stale_memory.log"
        if log_path.stat().st_size == 0:
            print(f"  FAIL: main log was truncated despite rotation fail (crash safety violation)")
            return False
    print("  PASS: atomic rotation: gzip fail → .tmp cleanup, main log preserved (crash safety)")
    return True


# === Test 5: atomic rotation no temp on under threshold ===
def test_atomic_rotation_no_temp_on_under_threshold() -> bool:
    """under-threshold 시 .tmp file 생성 0 (no rotate)."""
    with tempfile.TemporaryDirectory() as tmp:
        repo_root = _make_repo_root(tmp)
        memory_dir = repo_root / "ai-workflow" / "memory"
        _write_n_entries(memory_dir, 50)  # 50 < 100
        result = rotate_log_if_needed(memory_dir, line_threshold=100)
        if result["rotated"]:
            print(f"  FAIL: should not rotate (50 < 100). Got: {result}")
            return False
        # no .tmp, no .gz
        tmp_files = list(memory_dir.glob("*.tmp"))
        gz_files = list(memory_dir.glob("*.gz"))
        if tmp_files or gz_files:
            print(f"  FAIL: temp/gz files created despite no rotate. tmp={tmp_files}, gz={gz_files}")
            return False
    print("  PASS: atomic rotation: under threshold → no .tmp/.gz files")
    return True


# === TASK-V0734-001 Tests (5) ===

# === Test 6: yearly aggregation 2 years ===
def test_yearly_aggregation_2_years() -> bool:
    """2-year entries → 2 yearly buckets."""
    with tempfile.TemporaryDirectory() as tmp:
        repo_root = _make_repo_root(tmp)
        memory_dir = repo_root / "ai-workflow" / "memory"
        log_path = memory_dir / "archive_stale_memory.log"
        # 2025: 3 entries, 2026: 2 entries
        lines = [
            "2025-01-15T13:00:00Z\tolder_than=30\tarchived=1\tskipped=0\terror=0",
            "2025-06-15T13:00:00Z\tolder_than=30\tarchived=2\tskipped=0\terror=0",
            "2025-12-15T13:00:00Z\tolder_than=30\tarchived=3\tskipped=0\terror=0",
            "2026-03-15T13:00:00Z\tolder_than=30\tarchived=4\tskipped=0\terror=0",
            "2026-09-15T13:00:00Z\tolder_than=30\tarchived=5\tskipped=0\terror=0",
        ]
        log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        entries = read_metrics_log(memory_dir)
        result = aggregate_metrics(entries, period="yearly")
        if result["period"] != "yearly":
            print(f"  FAIL: period != 'yearly'. Got: {result['period']}")
            return False
        if len(result["buckets"]) != 2:
            print(f"  FAIL: expected 2 yearly buckets, got {len(result['buckets'])}. Buckets: {result['buckets']}")
            return False
        # 2025: count=3, archived=1+2+3=6
        # 2026: count=2, archived=4+5=9
        b_2025 = next(b for b in result["buckets"] if b["bucket"] == "2025")
        b_2026 = next(b for b in result["buckets"] if b["bucket"] == "2026")
        if b_2025["count"] != 3 or b_2025["archived"] != 6:
            print(f"  FAIL: 2025 bucket wrong. Got: {b_2025}")
            return False
        if b_2026["count"] != 2 or b_2026["archived"] != 9:
            print(f"  FAIL: 2026 bucket wrong. Got: {b_2026}")
            return False
    print("  PASS: 5 entries (2 years) → 2 yearly buckets (2025: 3, 2026: 2)")
    return True


# === Test 7: yearly aggregation 1 year ===
def test_yearly_aggregation_1_year() -> bool:
    """1-year entries → 1 yearly bucket."""
    with tempfile.TemporaryDirectory() as tmp:
        repo_root = _make_repo_root(tmp)
        memory_dir = repo_root / "ai-workflow" / "memory"
        log_path = memory_dir / "archive_stale_memory.log"
        # 2026: 3 entries
        lines = [
            "2026-01-15T13:00:00Z\tolder_than=30\tarchived=1\tskipped=0\terror=0",
            "2026-06-15T13:00:00Z\tolder_than=30\tarchived=2\tskipped=0\terror=0",
            "2026-12-15T13:00:00Z\tolder_than=30\tarchived=3\tskipped=0\terror=0",
        ]
        log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        entries = read_metrics_log(memory_dir)
        result = aggregate_metrics(entries, period="yearly")
        if len(result["buckets"]) != 1:
            print(f"  FAIL: expected 1 yearly bucket, got {len(result['buckets'])}")
            return False
        b = result["buckets"][0]
        if b["bucket"] != "2026" or b["count"] != 3:
            print(f"  FAIL: 2026 bucket wrong. Got: {b}")
            return False
    print("  PASS: 3 entries (1 year) → 1 yearly bucket (2026)")
    return True


# === Test 8: yearly aggregation cross year boundary ===
def test_yearly_aggregation_cross_year_boundary() -> bool:
    """2025-12 + 2026-01 → 2 buckets (cross-year)."""
    with tempfile.TemporaryDirectory() as tmp:
        repo_root = _make_repo_root(tmp)
        memory_dir = repo_root / "ai-workflow" / "memory"
        log_path = memory_dir / "archive_stale_memory.log"
        lines = [
            "2025-12-15T13:00:00Z\tolder_than=30\tarchived=1\tskipped=0\terror=0",
            "2026-01-15T13:00:00Z\tolder_than=30\tarchived=2\tskipped=0\terror=0",
        ]
        log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        entries = read_metrics_log(memory_dir)
        result = aggregate_metrics(entries, period="yearly")
        if len(result["buckets"]) != 2:
            print(f"  FAIL: expected 2 yearly buckets (2025 + 2026), got {len(result['buckets'])}. Buckets: {result['buckets']}")
            return False
        b_2025 = next(b for b in result["buckets"] if b["bucket"] == "2025")
        b_2026 = next(b for b in result["buckets"] if b["bucket"] == "2026")
        if b_2025["archived"] != 1 or b_2026["archived"] != 2:
            print(f"  FAIL: cross-year wrong. 2025={b_2025['archived']}, 2026={b_2026['archived']}")
            return False
    print("  PASS: 2025-12 + 2026-01 → 2 yearly buckets (cross-year boundary)")
    return True


# === Test 9: yearly aggregation total sum ===
def test_yearly_aggregation_total_sum() -> bool:
    """total.archived = sum(buckets.archived) (sum 정합)."""
    with tempfile.TemporaryDirectory() as tmp:
        repo_root = _make_repo_root(tmp)
        memory_dir = repo_root / "ai-workflow" / "memory"
        log_path = memory_dir / "archive_stale_memory.log"
        # 3 years, 4 entries total
        lines = [
            "2024-06-15T13:00:00Z\tolder_than=30\tarchived=1\tskipped=0\terror=0",
            "2025-03-15T13:00:00Z\tolder_than=30\tarchived=2\tskipped=0\terror=0",
            "2025-09-15T13:00:00Z\tolder_than=30\tarchived=3\tskipped=0\terror=0",
            "2026-01-15T13:00:00Z\tolder_than=30\tarchived=4\tskipped=0\terror=0",
        ]
        log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        entries = read_metrics_log(memory_dir)
        result = aggregate_metrics(entries, period="yearly")
        # total.archived = 1+2+3+4 = 10
        if result["total"]["archived"] != 10:
            print(f"  FAIL: expected total.archived=10, got {result['total']['archived']}")
            return False
        # total.count = 4
        if result["total"]["count"] != 4:
            print(f"  FAIL: expected total.count=4, got {result['total']['count']}")
            return False
        # sum of buckets
        bucket_sum = sum(b["archived"] for b in result["buckets"])
        if bucket_sum != 10:
            print(f"  FAIL: bucket sum != 10: {bucket_sum}")
            return False
    print("  PASS: 4 entries (3 years) → total.archived=10 = sum(buckets.archived)")
    return True


# === Test 10: yearly aggregation invalid period ===
def test_yearly_aggregation_invalid_period() -> bool:
    """invalid --aggregate (e.g. 'decade') → ok=False, error message."""
    with tempfile.TemporaryDirectory() as tmp:
        repo_root = _make_repo_root(tmp)
        args = _make_args(aggregate="decade", repo_root=str(repo_root))
        result = cmd_aggregate_metrics(args)
        if result.get("ok") is not False:
            print(f"  FAIL: expected ok=False, got {result}")
            return False
        if "invalid" not in result.get("error", "").lower() and "expected" not in result.get("error", "").lower():
            print(f"  FAIL: error message missing. Got: {result.get('error')!r}")
            return False
    print("  PASS: invalid --aggregate=decade → ok=False, error message")
    return True


# === Main ===
def main() -> int:
    print("=" * 60)
    print("TASK-V0733-001 + TASK-V0734-001 smoke test (v0.7.33)")
    print("=" * 60)

    tests = [
        # TASK-V0733-001 (5)
        test_atomic_rotation_no_temp_leftover,
        test_atomic_rotation_archive_exists,
        test_atomic_rotation_main_log_empty,
        test_atomic_rotation_temp_cleanup_on_fail,
        test_atomic_rotation_no_temp_on_under_threshold,
        # TASK-V0734-001 (5)
        test_yearly_aggregation_2_years,
        test_yearly_aggregation_1_year,
        test_yearly_aggregation_cross_year_boundary,
        test_yearly_aggregation_total_sum,
        test_yearly_aggregation_invalid_period,
    ]
    passed = 0
    for test in tests:
        print(f"\n{test.__name__}:")
        if test():
            passed += 1

    print()
    print("=" * 60)
    print(f"Result: {passed}/{len(tests)} PASS")
    print("=" * 60)
    return 0 if passed == len(tests) else 1


if __name__ == "__main__":
    sys.exit(main())
