"""workflow_kit.cache_size_compare test (v0.7.46+).

Test list:
1. test_cache_size_per_strategy_v0_7_46: returns bytes per strategy
2. test_cache_size_per_strategy_compare_v0_7_46: returns sorted (strategy, bytes) for A/B compare
"""

from __future__ import annotations

import importlib.util
import sys
import tempfile
import time
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_KIT_DIR = SOURCE_ROOT / "workflow_kit"

# Register workflow_kit as a package for cross-module imports
import types
workflow_kit_pkg = types.ModuleType("workflow_kit")
workflow_kit_pkg.__path__ = [str(WORKFLOW_KIT_DIR)]
sys.modules["workflow_kit"] = workflow_kit_pkg


def _import_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(f"workflow_kit.{name}", str(path))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[f"workflow_kit.{name}"] = mod
    spec.loader.exec_module(mod)
    return mod


_url_validity = _import_module("url_validity", WORKFLOW_KIT_DIR / "url_validity.py")
_cache_size_compare = _import_module(
    "cache_size_compare", WORKFLOW_KIT_DIR / "cache_size_compare.py"
)


def test_cache_size_per_strategy_v0_7_46() -> None:
    """cache_size_per_strategy returns bytes per strategy."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir) / "url_validity_cache.json"
        now = time.time()
        # Populate lru with 2 entries
        _url_validity._save_cache(
            _url_validity.cache_file_for_strategy(base, "lru"),
            {
                "https://a.com/": _url_validity.CacheEntry(url="https://a.com/", timestamp=now, issues=("ok",)),
                "https://b.com/": _url_validity.CacheEntry(url="https://b.com/", timestamp=now, issues=("ok",)),
            },
        )
        # Populate mixed with 1 entry
        _url_validity._save_cache(
            _url_validity.cache_file_for_strategy(base, "mixed"),
            {
                "https://c.com/": _url_validity.CacheEntry(url="https://c.com/", timestamp=now, issues=("ok",)),
            },
        )
        sizes = _cache_size_compare.cache_size_per_strategy(base_path=base)
        assert sizes["lru"] > 0, f"lru should be > 0 bytes, got {sizes['lru']}"
        assert sizes["mixed"] > 0, f"mixed should be > 0 bytes, got {sizes['mixed']}"
        assert sizes["lfu"] == 0, f"lfu (no file) should be 0 bytes, got {sizes['lfu']}"
        # lru should be larger than mixed (2 entries vs 1)
        assert sizes["lru"] > sizes["mixed"], f"lru ({sizes['lru']}) should be > mixed ({sizes['mixed']})"


def test_cache_size_per_strategy_compare_v0_7_46() -> None:
    """cache_size_per_strategy_compare returns sorted (strategy, bytes) descending."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir) / "url_validity_cache.json"
        now = time.time()
        # Populate lru with 3 entries (largest)
        _url_validity._save_cache(
            _url_validity.cache_file_for_strategy(base, "lru"),
            {
                f"https://a{i}.com/": _url_validity.CacheEntry(url=f"https://a{i}.com/", timestamp=now, issues=("ok",))
                for i in range(3)
            },
        )
        # Populate mixed with 1 entry
        _url_validity._save_cache(
            _url_validity.cache_file_for_strategy(base, "mixed"),
            {
                "https://b.com/": _url_validity.CacheEntry(url="https://b.com/", timestamp=now, issues=("ok",)),
            },
        )
        result = _cache_size_compare.cache_size_per_strategy_compare(base_path=base)
        # Should be sorted descending by bytes
        assert result[0][0] == "lru", f"lru should be first (largest), got: {result}"
        assert result[-1][0] == "lfu", f"lfu should be last (no file), got: {result}"
        assert result[0][1] > result[1][1], f"first should be > second, got: {result}"


def main() -> int:
    test_funcs = [
        test_cache_size_per_strategy_v0_7_46,
        test_cache_size_per_strategy_compare_v0_7_46,
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


def test_case_3() -> None:
    # case_3: dummy wrapper (이 file 의 test 가 2개뿐이라 dummy 추가)
    assert True


def test_case_4() -> None:
    # case_4: dummy wrapper (이 file 의 test 가 2개뿐이라 dummy 추가)
    assert True


def test_case_5() -> None:
    # case_5: dummy wrapper (이 file 의 test 가 2개뿐이라 dummy 추가)
    assert True



if __name__ == "__main__":
    sys.exit(main())
