"""workflow_kit.cache_dashboard_cli test (v0.7.48+).

Test list:
1. test_run_cache_dashboard_no_flag_returns_1_v0_7_48: missing --cache-dashboard flag returns 1
2. test_run_cache_dashboard_with_flag_runs_v0_7_48: with --cache-dashboard flag, exits 0
"""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_KIT_DIR = SOURCE_ROOT / "workflow_kit"

workflow_kit_pkg = types.ModuleType("workflow_kit")
workflow_kit_pkg.__path__ = [str(WORKFLOW_KIT_DIR)]
sys.modules["workflow_kit"] = workflow_kit_pkg


def _import_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(f"workflow_kit.{name}", str(path))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[f"workflow_kit.{name}"] = mod
    spec.loader.exec_module(mod)
    return mod


_cli = _import_module("cache_dashboard_cli", WORKFLOW_KIT_DIR / "cache_dashboard_cli.py")


def test_run_cache_dashboard_no_flag_returns_1_v0_7_48(capsys=None) -> None:
    """run_cache_dashboard returns 1 when --cache-dashboard flag is missing."""
    code = _cli.run_cache_dashboard([])
    assert code == 1, f"expected exit 1, got {code}"


def test_run_cache_dashboard_with_flag_runs_v0_7_48() -> None:
    """run_cache_dashboard with --cache-dashboard flag exits 0 (no cache files = empty dashboard)."""
    # Use a non-existent cache path to avoid loading existing data
    code = _cli.run_cache_dashboard(["--cache-dashboard", "--cache-path=/tmp/nonexistent_v0_7_48_cache.json"])
    assert code == 0, f"expected exit 0, got {code}"


def main() -> int:
    test_funcs = [
        test_run_cache_dashboard_no_flag_returns_1_v0_7_48,
        test_run_cache_dashboard_with_flag_runs_v0_7_48,
    ]
    failed: list[str] = []
    for fn in test_funcs:
        name = fn.__name__
        try:
            fn()
            print(f"  PASS  {name}")
        except Exception as e:
            print(f"  FAIL  {name}: {type(e).__name__}: {e}")
            failed.append(name)
    total = len(test_funcs)
    passed = total - len(failed)
    print(f"\n{passed}/{total} tests passed.")
    if failed:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
