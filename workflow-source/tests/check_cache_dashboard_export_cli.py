"""workflow_kit.cache_dashboard_export_cli test (v0.7.51+).

Test list:
1. test_run_dashboard_export_cli_no_flag_returns_1_v0_7_51: missing --dashboard-export returns 1
2. test_run_dashboard_export_cli_no_output_returns_1_v0_7_51: missing --output returns 1
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


_export = _import_module("cache_dashboard_export", WORKFLOW_KIT_DIR / "cache_dashboard_export.py")
_cli = _import_module("cache_dashboard_export_cli", WORKFLOW_KIT_DIR / "cache_dashboard_export_cli.py")


def test_run_dashboard_export_cli_no_flag_returns_1_v0_7_51() -> None:
    """run_dashboard_export_cli returns 1 when --dashboard-export is missing."""
    code = _cli.run_dashboard_export_cli([])
    assert code == 1, f"expected exit 1, got {code}"


def test_run_dashboard_export_cli_no_output_returns_1_v0_7_51() -> None:
    """run_dashboard_export_cli returns 1 when --output is missing."""
    code = _cli.run_dashboard_export_cli(["--dashboard-export"])
    assert code == 1, f"expected exit 1, got {code}"


def main() -> int:
    test_funcs = [
        test_run_dashboard_export_cli_no_flag_returns_1_v0_7_51,
        test_run_dashboard_export_cli_no_output_returns_1_v0_7_51,
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
