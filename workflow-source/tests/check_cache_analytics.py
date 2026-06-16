"""workflow_kit.cache_analytics test (v0.7.47+).

Test list:
1. test_cache_analytics_per_strategy_hit_rate_v0_7_47: per-strategy hit rate computation
2. test_cache_analytics_summary_cross_strategy_v0_7_47: aggregate + lru_to_lfu_size_ratio
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


_analytics = _import_module("cache_analytics", WORKFLOW_KIT_DIR / "cache_analytics.py")


def test_cache_analytics_per_strategy_hit_rate_v0_7_47() -> None:
    """cache_analytics returns per-strategy hit rate."""
    cache = {
        "https://a.com/": {"strategy": "lru", "hits": 10, "misses": 5, "evictions": 0},
        "https://b.com/": {"strategy": "lru", "hits": 20, "misses": 0, "evictions": 1},
        "https://c.com/": {"strategy": "lfu", "hits": 5, "misses": 15, "evictions": 0},
    }
    result = _analytics.cache_analytics(cache)
    assert "lru" in result
    assert "lfu" in result
    # LRU: 30 hits, 5 misses -> 30/35 = 0.8571
    assert abs(result["lru"]["hit_rate"] - 30 / 35) < 0.001
    # LFU: 5 hits, 15 misses -> 5/20 = 0.25
    assert abs(result["lfu"]["hit_rate"] - 0.25) < 0.001


def test_cache_analytics_summary_cross_strategy_v0_7_47() -> None:
    """cache_analytics_summary returns aggregate + lru_to_lfu_size_ratio."""
    cache = {
        "https://a.com/": {"strategy": "lru", "hits": 10, "misses": 5, "evictions": 0},
        "https://b.com/": {"strategy": "lru", "hits": 0, "misses": 0, "evictions": 0},
        "https://c.com/": {"strategy": "lru", "hits": 0, "misses": 0, "evictions": 0},
        "https://d.com/": {"strategy": "lfu", "hits": 0, "misses": 0, "evictions": 0},
    }
    summary = _analytics.cache_analytics_summary(cache)
    assert summary["total_size"] == 4
    assert summary["total_hits"] == 10
    assert summary["total_misses"] == 5
    # LRU: 3 entries, LFU: 1 entry -> ratio = 3.0
    assert summary["lru_to_lfu_size_ratio"] == 3.0
    # Overall hit rate: 10/(10+5) = 0.6667
    assert abs(summary["overall_hit_rate"] - 10 / 15) < 0.001


def main() -> int:
    test_funcs = [
        test_cache_analytics_per_strategy_hit_rate_v0_7_47,
        test_cache_analytics_summary_cross_strategy_v0_7_47,
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
