"""workflow_kit.cache_dashboard_export test (v0.7.49+).

Test list:
1. test_export_dashboard_json_v0_7_49: exports JSON with strategies + totals
2. test_export_dashboard_markdown_v0_7_49: exports Markdown table with header + rows
"""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
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
_dashboard = _import_module("cache_dashboard", WORKFLOW_KIT_DIR / "cache_dashboard.py")
_export = _import_module("cache_dashboard_export", WORKFLOW_KIT_DIR / "cache_dashboard_export.py")


def test_export_dashboard_json_v0_7_49() -> None:
    """export_dashboard_json returns valid JSON with strategies + totals."""
    cache = {
        "https://a.com/": {"strategy": "lru", "hits": 10, "misses": 5, "evictions": 0},
        "https://b.com/": {"strategy": "lfu", "hits": 20, "misses": 10, "evictions": 1},
    }
    output = _export.export_dashboard_json(cache)
    parsed = json.loads(output)
    assert "strategies" in parsed
    assert "totals" in parsed
    assert "lru" in parsed["strategies"]
    assert "lfu" in parsed["strategies"]


def test_export_dashboard_markdown_v0_7_49() -> None:
    """export_dashboard_markdown returns Markdown table with header + rows."""
    cache = {
        "https://a.com/": {"strategy": "lru", "hits": 10, "misses": 5, "evictions": 0},
        "https://b.com/": {"strategy": "lfu", "hits": 20, "misses": 10, "evictions": 1},
    }
    output = _export.export_dashboard_markdown(cache)
    assert "# Per-Strategy Cache Dashboard" in output
    assert "| strategy | size |" in output
    assert "lru" in output
    assert "lfu" in output
    assert "TOTAL" in output


def main() -> int:
    test_funcs = [
        test_export_dashboard_json_v0_7_49,
        test_export_dashboard_markdown_v0_7_49,
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
