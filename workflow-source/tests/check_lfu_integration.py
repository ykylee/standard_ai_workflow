"""workflow_kit.lfu_integration test (v0.7.44+).

Test list:
1. test_lfu_eviction_keeps_high_frequency: high-frequency entry survives eviction
2. test_save_cache_with_lfu_writes_file: end-to-end file write
"""

from __future__ import annotations

import importlib.util
import sys
import time
import tempfile
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


_lfu_config = _import_module("lfu_config", WORKFLOW_KIT_DIR / "lfu_config.py")
_url_validity = _import_module("url_validity", WORKFLOW_KIT_DIR / "url_validity.py")
_lfu_integration = _import_module("lfu_integration", WORKFLOW_KIT_DIR / "lfu_integration.py")


def test_lfu_eviction_keeps_high_frequency() -> None:
    """LFU eviction keeps high-frequency entry, evicts low-frequency first."""
    now = time.time()
    entries = {
        "https://high.com/": _url_validity.CacheEntry(url="https://high.com/", timestamp=now, issues=("ok",), access_count=100),
        "https://low.com/": _url_validity.CacheEntry(url="https://low.com/", timestamp=now, issues=("ok",), access_count=0),
    }
    config = _lfu_config.LFUConfig(frequency_weight=1.0, recency_weight=0.0, decay_seconds=86400.0)
    # Evict the low-frequency entry
    victim = min(entries.keys(), key=lambda u: _lfu_integration._evict_key_with_lfu(u, entries, config))
    assert victim == "https://low.com/", f"low-freq should be evicted first, got: {victim}"


def test_save_cache_with_lfu_writes_file() -> None:
    """save_cache_with_lfu writes a valid cache file (low freq evicted, high freq kept)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cache_file = Path(tmpdir) / "cache.json"
        now = time.time()
        entries = {
            "https://high.com/": _url_validity.CacheEntry(url="https://high.com/", timestamp=now, issues=("ok",), access_count=100),
            "https://low.com/": _url_validity.CacheEntry(url="https://low.com/", timestamp=now, issues=("ok",), access_count=0),
            "https://mid.com/": _url_validity.CacheEntry(url="https://mid.com/", timestamp=now, issues=("ok",), access_count=5),
        }
        # max_entries=1 to force eviction
        config = _lfu_config.LFUConfig(frequency_weight=1.0, recency_weight=0.0, decay_seconds=86400.0)
        _lfu_integration.save_cache_with_lfu(
            cache_file, entries, config, max_bytes=10 * 1024 * 1024, max_entries=1
        )
        # Verify only 1 entry kept (the high-freq one)
        assert cache_file.exists(), f"cache file not written: {cache_file}"
        # Use the helper from url_validity to load
        loaded = _url_validity._load_cache(cache_file)
        assert "https://high.com/" in loaded, f"high-freq should be kept, got: {list(loaded.keys())}"
        assert "https://low.com/" not in loaded, f"low-freq should be evicted, got: {list(loaded.keys())}"


def main() -> int:
    test_funcs = [
        test_lfu_eviction_keeps_high_frequency,
        test_save_cache_with_lfu_writes_file,
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
