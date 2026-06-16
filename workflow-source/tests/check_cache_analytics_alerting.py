"""workflow_kit.cache_analytics_alerting test (v0.7.51+).

Test list:
1. test_check_alerts_size_threshold_v0_7_51: triggers size alert when exceeded
2. test_check_alerts_hit_rate_threshold_v0_7_51: triggers hit_rate alert when below
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[1]
ALERTING = SOURCE_ROOT / "workflow_kit" / "cache_analytics_alerting.py"


def _import_module():
    spec = importlib.util.spec_from_file_location("cache_analytics_alerting", str(ALERTING))
    mod = importlib.util.module_from_spec(spec)
    sys.modules["cache_analytics_alerting"] = mod
    spec.loader.exec_module(mod)
    return mod


def test_check_alerts_size_threshold_v0_7_51() -> None:
    """check_alerts triggers size alert when exceeded."""
    mod = _import_module()
    analytics = {
        "lru": {"size": 100, "hits": 50, "misses": 50, "hit_rate": 0.5, "evictions": 0},
        "lfu": {"size": 200, "hits": 100, "misses": 100, "hit_rate": 0.5, "evictions": 5},
    }
    thresholds = mod.AlertThresholds(max_size=150)
    alerts = mod.check_alerts(analytics, thresholds)
    # lru (100) under 150: no alert
    # lfu (200) over 150: 1 alert
    assert len(alerts) == 1, f"expected 1 alert, got {len(alerts)}"
    assert alerts[0].strategy == "lfu"
    assert alerts[0].metric == "size"
    assert alerts[0].value == 200.0


def test_check_alerts_hit_rate_threshold_v0_7_51() -> None:
    """check_alerts triggers hit_rate alert when below threshold."""
    mod = _import_module()
    analytics = {
        "lru": {"size": 100, "hits": 10, "misses": 90, "hit_rate": 0.1, "evictions": 0},
    }
    thresholds = mod.AlertThresholds(min_hit_rate=0.5)
    alerts = mod.check_alerts(analytics, thresholds)
    assert len(alerts) == 1
    assert alerts[0].metric == "hit_rate"
    assert alerts[0].severity == "critical"


def main() -> int:
    test_funcs = [
        test_check_alerts_size_threshold_v0_7_51,
        test_check_alerts_hit_rate_threshold_v0_7_51,
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
