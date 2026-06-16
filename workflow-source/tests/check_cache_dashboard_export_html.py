"""workflow_kit.cache_dashboard_export HTML test (v0.7.50+).

Test list:
1. test_export_dashboard_html_v0_7_50: HTML has <table>, <th>, <tr>, <td> tags
2. test_write_dashboard_html_format_v0_7_50: write_dashboard with format='html' writes HTML file
"""

from __future__ import annotations

import importlib.util
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


_export = _import_module("cache_dashboard_export", WORKFLOW_KIT_DIR / "cache_dashboard_export.py")


def test_export_dashboard_html_v0_7_50() -> None:
    """export_dashboard_html returns HTML with table + cells."""
    cache = {
        "https://a.com/": {"strategy": "lru", "hits": 10, "misses": 5, "evictions": 0},
        "https://b.com/": {"strategy": "lfu", "hits": 20, "misses": 10, "evictions": 1},
    }
    output = _export.export_dashboard_html(cache)
    assert "<!DOCTYPE html>" in output
    assert "<table>" in output
    assert "<th>strategy</th>" in output
    assert "lru" in output
    assert "lfu" in output
    assert "TOTAL" in output


def test_write_dashboard_html_format_v0_7_50() -> None:
    """write_dashboard with format='html' writes a valid HTML file."""
    cache = {
        "https://a.com/": {"strategy": "lru", "hits": 10, "misses": 5, "evictions": 0},
    }
    with tempfile.TemporaryDirectory() as tmpdir:
        path = str(Path(tmpdir) / "dashboard.html")
        _export.write_dashboard(cache, path, format="html")
        with open(path, "r", encoding="utf-8") as fh:
            content = fh.read()
        assert "<!DOCTYPE html>" in content
        assert "lru" in content


def main() -> int:
    test_funcs = [
        test_export_dashboard_html_v0_7_50,
        test_write_dashboard_html_format_v0_7_50,
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
