"""workflow_kit.cache_analytics_alerting_cli test (v0.7.52+).

Test list:
1. test_run_alerting_cli_no_flag_returns_2_v0_7_52: missing --alert returns 2
2. test_run_alerting_cli_no_alerts_returns_0_v0_7_52: empty cache + no thresholds returns 0
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


_alerting = _import_module("cache_analytics_alerting", WORKFLOW_KIT_DIR / "cache_analytics_alerting.py")
_cli = _import_module("cache_analytics_alerting_cli", WORKFLOW_KIT_DIR / "cache_analytics_alerting_cli.py")


def test_run_alerting_cli_no_flag_returns_2_v0_7_52() -> None:
    """run_alerting_cli returns 2 when --alert is missing."""
    code = _cli.run_alerting_cli([])
    assert code == 2, f"expected exit 2, got {code}"


def test_run_alerting_cli_no_alerts_returns_0_v0_7_52() -> None:
    """run_alerting_cli with no cache files + no thresholds returns 0 (no alerts)."""
    code = _cli.run_alerting_cli([
        "--alert", "--cache-path=/tmp/nonexistent_v0_7_52_cache.json",
    ])
    assert code == 0, f"expected exit 0 (no alerts), got {code}"


def main() -> int:
    test_funcs = [
        test_run_alerting_cli_no_flag_returns_2_v0_7_52,
        test_run_alerting_cli_no_alerts_returns_0_v0_7_52,
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
