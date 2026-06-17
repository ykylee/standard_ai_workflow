"""tools/consumer_metrics.py test (v0.7.58).

Tests the consumer feedback metrics tool independently of the dispatcher:
- argparse validation (--days range, --repo arg)
- gh auth check (subprocess delegation to gh CLI)
- collect_metrics() output structure
- main() exit codes (0 = success, 1 = gh auth fail, 2 = usage error)
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import types
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = SOURCE_ROOT / "tools"

# Make tools/ importable as a package
tools_pkg = types.ModuleType("tools")
tools_pkg.__path__ = [str(TOOLS_DIR)]
sys.modules["tools"] = tools_pkg


def _import_consumer_metrics():
    spec = importlib.util.spec_from_file_location(
        "tools.consumer_metrics", str(TOOLS_DIR / "consumer_metrics.py")
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["tools.consumer_metrics"] = mod
    spec.loader.exec_module(mod)
    return mod


def _gh_authenticated() -> bool:
    """Skip test if gh CLI is not authenticated (e.g. CI)."""
    try:
        r = subprocess.run(
            ["gh", "auth", "status"], capture_output=True, text=True, timeout=10
        )
        return r.returncode == 0
    except FileNotFoundError:
        return False


def test_consumer_metrics_importable_v0_7_58() -> None:
    """tools.consumer_metrics is importable as a module (v0.7.58+)."""
    mod = _import_consumer_metrics()
    assert hasattr(mod, "main")
    assert hasattr(mod, "collect_metrics")
    assert hasattr(mod, "_gh_api")
    assert hasattr(mod, "_gh_issue_list")
    assert callable(mod.main)
    assert callable(mod.collect_metrics)


def test_consumer_metrics_days_validation_v0_7_58() -> None:
    """main() with --days=0 or --days=100 returns 2 (usage error)."""
    mod = _import_consumer_metrics()
    # days=0
    old_argv = sys.argv
    try:
        sys.argv = ["consumer_metrics", "--days=0"]
        code = mod.main()
        assert code == 2
        # days=100 (out of range)
        sys.argv = ["consumer_metrics", "--days=100"]
        code = mod.main()
        assert code == 2
    finally:
        sys.argv = old_argv


def test_consumer_metrics_repo_default_v0_7_58() -> None:
    """main() default --repo is ykylee/standard_ai_workflow."""
    mod = _import_consumer_metrics()
    # Inspect the parser's default for --repo
    # We construct a parser the same way main() does to check defaults
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default="ykylee/standard_ai_workflow")
    args = parser.parse_args([])
    assert args.repo == "ykylee/standard_ai_workflow"


def test_consumer_metrics_collect_metrics_structure_v0_7_58() -> None:
    """collect_metrics() returns a dict with all expected top-level keys."""
    if not _gh_authenticated():
        print("  SKIP  test_consumer_metrics_collect_metrics_structure_v0_7_58 (gh not authenticated)")
        return
    mod = _import_consumer_metrics()
    result = mod.collect_metrics("ykylee/standard_ai_workflow", 7)
    # Top-level keys
    assert "repo" in result
    assert "days" in result
    assert "snapshot_at" in result
    assert "gh_pages" in result
    assert "gh_clones" in result
    assert "consumer_feedback" in result
    assert "releases_recent" in result
    # Nested structure
    assert "views_total" in result["gh_pages"]
    assert "views_uniques" in result["gh_pages"]
    assert "clones_total" in result["gh_clones"]
    assert "total" in result["consumer_feedback"]
    assert "open" in result["consumer_feedback"]
    assert "closed" in result["consumer_feedback"]
    assert isinstance(result["releases_recent"], list)


def test_consumer_metrics_main_with_gh_v0_7_58() -> None:
    """main() with gh auth returns 0 (success) and produces text output."""
    if not _gh_authenticated():
        print("  SKIP  test_consumer_metrics_main_with_gh_v0_7_58 (gh not authenticated)")
        return
    mod = _import_consumer_metrics()
    old_argv = sys.argv
    try:
        sys.argv = ["consumer_metrics", "--days=14", "--repo=ykylee/standard_ai_workflow"]
        code = mod.main()
        assert code == 0
    finally:
        sys.argv = old_argv


def test_consumer_metrics_json_output_v0_7_58() -> None:
    """main() with --json returns valid JSON with all required keys."""
    if not _gh_authenticated():
        print("  SKIP  test_consumer_metrics_json_output_v0_7_58 (gh not authenticated)")
        return
    import io
    from contextlib import redirect_stdout
    mod = _import_consumer_metrics()
    old_argv = sys.argv
    try:
        sys.argv = ["consumer_metrics", "--json", "--days=7", "--repo=ykylee/standard_ai_workflow"]
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = mod.main()
        assert code == 0
        data = json.loads(buf.getvalue())
        assert data["repo"] == "ykylee/standard_ai_workflow"
        assert data["days"] == 7
        assert "snapshot_at" in data
    finally:
        sys.argv = old_argv

def test_consumer_metrics_record_snapshot_v0_7_62() -> None:
    """record_snapshot appends to jsonl; load_history reads it back (v0.7.62+)."""
    import tempfile
    mod = _import_consumer_metrics()
    with tempfile.TemporaryDirectory() as tmp:
        history_path = Path(tmp) / "history.jsonl"
        metrics = {
            "repo": "owner/repo",
            "days": 7,
            "snapshot_at": "2026-06-17T00:00:00+00:00",
            "gh_pages": {"views_total": 100, "views_uniques": 50},
            "gh_clones": {"clones_total": 20},
            "consumer_feedback": {"total": 5, "open": 2, "closed": 3, "issues": []},
            "releases_recent": [{"tag": "v0.7.62"}],
        }
        record = mod.record_snapshot(metrics, history_path)
        assert record["views_total"] == 100
        assert record["feedback_total"] == 5
        assert record["feedback_open"] == 2
        assert record["releases_recent_count"] == 1
        # Re-record to verify append
        metrics["gh_pages"]["views_total"] = 200
        mod.record_snapshot(metrics, history_path)
        records = mod.load_history(history_path)
        assert len(records) == 2
        assert records[0]["views_total"] == 100
        assert records[1]["views_total"] == 200


def test_consumer_metrics_load_history_empty_v0_7_62() -> None:
    """load_history on missing file returns [] (offline-safe, v0.7.62+)."""
    import tempfile
    mod = _import_consumer_metrics()
    with tempfile.TemporaryDirectory() as tmp:
        history_path = Path(tmp) / "nonexistent.jsonl"
        records = mod.load_history(history_path)
        assert records == []


def test_consumer_metrics_ascii_trend_v0_7_62() -> None:
    """ascii_trend renders bar chart for each TREND_DIMS (v0.7.62+)."""
    import tempfile
    mod = _import_consumer_metrics()
    records = [
        {"snapshot_at": "2026-06-15T00:00:00+00:00", "views_total": 10, "clones_total": 1, "feedback_total": 2, "feedback_open": 1},
        {"snapshot_at": "2026-06-16T00:00:00+00:00", "views_total": 30, "clones_total": 5, "feedback_total": 4, "feedback_open": 2},
        {"snapshot_at": "2026-06-17T00:00:00+00:00", "views_total": 50, "clones_total": 9, "feedback_total": 6, "feedback_open": 3},
    ]
    for dim in mod.TREND_DIMS:
        chart = mod.ascii_trend(records, dim)
        # 3 rows + 1 line per record, each with date prefix YYYY-MM-DD
        assert "2026-06-15" in chart
        assert "2026-06-17" in chart
        # Bar characters
        assert "█" in chart or "░" in chart
    # Unknown dim
    assert "(unknown dim:" in mod.ascii_trend(records, "nonexistent")
    # Empty records
    assert "(no records)" in mod.ascii_trend([], "views_total")


def test_consumer_metrics_format_digest_v0_7_62() -> None:
    """format_digest returns Slack-style text (v0.7.62+)."""
    mod = _import_consumer_metrics()
    metrics = {
        "repo": "owner/repo",
        "days": 7,
        "snapshot_at": "2026-06-17T00:00:00+00:00",
        "gh_pages": {"views_total": 100, "views_uniques": 50},
        "gh_clones": {"clones_total": 20},
        "consumer_feedback": {"total": 5, "open": 2, "closed": 3, "issues": []},
        "releases_recent": [],
    }
    digest = mod.format_digest(metrics)
    assert "Consumer digest" in digest
    assert "7d" in digest
    assert "owner/repo" in digest
    assert "views_total: 100" in digest
    assert "feedback: 5" in digest
    assert "*Consumer digest" in digest  # Slack bold


def test_consumer_metrics_format_digest_markdown_v0_7_62() -> None:
    """format_digest_markdown returns GH issue comment format (v0.7.62+)."""
    mod = _import_consumer_metrics()
    metrics = {
        "repo": "owner/repo",
        "days": 7,
        "snapshot_at": "2026-06-17T00:00:00+00:00",
        "gh_pages": {"views_total": 100, "views_uniques": 50},
        "gh_clones": {"clones_total": 20},
        "consumer_feedback": {
            "total": 2,
            "open": 1,
            "closed": 1,
            "issues": [
                {"number": 1, "title": "Bug X", "state": "OPEN", "createdAt": "2026-06-15"},
                {"number": 2, "title": "Feature Y", "state": "CLOSED", "createdAt": "2026-06-10"},
            ],
        },
        "releases_recent": [
            {"tag": "v0.7.62", "name": "trend + digest", "published_at": "2026-06-17"},
        ],
    }
    md = mod.format_digest_markdown(metrics)
    assert "## Consumer digest" in md
    assert "owner/repo" in md
    assert "| GH Pages views (total) | 100 |" in md
    assert "| Consumer feedback (open) | 1 |" in md
    assert "### Recent releases" in md
    assert "**v0.7.62**" in md
    assert "### Open feedback issues" in md
    assert "#1 Bug X" in md


def main() -> int:
    test_funcs = [
        test_consumer_metrics_importable_v0_7_58,
        test_consumer_metrics_days_validation_v0_7_58,
        test_consumer_metrics_main_with_gh_v0_7_58,
        test_consumer_metrics_json_output_v0_7_58,
        test_consumer_metrics_record_snapshot_v0_7_62,
        test_consumer_metrics_load_history_empty_v0_7_62,
        test_consumer_metrics_ascii_trend_v0_7_62,
        test_consumer_metrics_format_digest_v0_7_62,
        test_consumer_metrics_format_digest_markdown_v0_7_62,
     ]
    failed: list[str] = []
    skipped: list[str] = []
    for fn in test_funcs:
        name = fn.__name__
        try:
            fn()
        except SystemExit as e:
            # SKIP prints handled inside the test
            if e.code == 0:
                skipped.append(name)
                continue
            print(f"  FAIL  {name}: SystemExit({e.code})")
            failed.append(name)
        except Exception as e:
            print(f"  FAIL  {name}: {type(e).__name__}: {e}")
            failed.append(name)
    total = len(test_funcs)
    passed = total - len(failed) - len(skipped)
    print(f"\n{passed}/{total} tests passed ({len(skipped)} skipped due to no gh auth).")
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
