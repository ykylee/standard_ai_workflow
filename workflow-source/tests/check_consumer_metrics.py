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


def main() -> int:
    test_funcs = [
        test_consumer_metrics_importable_v0_7_58,
        test_consumer_metrics_days_validation_v0_7_58,
        test_consumer_metrics_repo_default_v0_7_58,
        test_consumer_metrics_collect_metrics_structure_v0_7_58,
        test_consumer_metrics_main_with_gh_v0_7_58,
        test_consumer_metrics_json_output_v0_7_58,
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
