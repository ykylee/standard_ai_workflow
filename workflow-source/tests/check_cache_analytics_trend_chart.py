"""workflow_kit.cache_analytics_trend_chart test (v0.7.50+).

Test list:
1. test_render_trend_chart_ascii_basic_v0_7_50: renders ASCII chart with header + bars
2. test_render_trend_chart_ascii_empty_v0_7_50: empty snapshots returns "No snapshots"
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[1]
CHART = SOURCE_ROOT / "workflow_kit" / "cache_analytics_trend_chart.py"


def _import_module():
    spec = importlib.util.spec_from_file_location("cache_analytics_trend_chart", str(CHART))
    mod = importlib.util.module_from_spec(spec)
    sys.modules["cache_analytics_trend_chart"] = mod
    spec.loader.exec_module(mod)
    return mod


def test_render_trend_chart_ascii_basic_v0_7_50() -> None:
    """render_trend_chart_ascii renders chart with header + bars."""
    mod = _import_module()
    snapshots = [
        {"timestamp": 1000.0, "total_size": 5},
        {"timestamp": 2000.0, "total_size": 10},
        {"timestamp": 3000.0, "total_size": 20},
    ]
    output = mod.render_trend_chart_ascii(snapshots, metric="total_size", width=30, height=5)
    assert "Trend Chart" in output
    assert "=" in output
    # Should have at least one bar character
    assert "█" in output, f"expected bar chars in: {output}"


def test_render_trend_chart_ascii_empty_v0_7_50() -> None:
    """render_trend_chart_ascii with empty snapshots returns 'No snapshots'."""
    mod = _import_module()
    output = mod.render_trend_chart_ascii([], metric="total_size")
    assert "No snapshots" in output, f"unexpected: {output}"


def main() -> int:
    test_funcs = [
        test_render_trend_chart_ascii_basic_v0_7_50,
        test_render_trend_chart_ascii_empty_v0_7_50,
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
