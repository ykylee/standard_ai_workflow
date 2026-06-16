"""workflow_kit.cache_migration test (v0.7.44+).

Test list:
1. test_migrate_to_per_strategy_cache_v0_7_44: single file -> mixed file
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
_cache_migration = _import_module(
    "cache_migration", WORKFLOW_KIT_DIR / "cache_migration.py"
)


def test_migrate_to_per_strategy_cache_v0_7_44() -> None:
    """migrate_to_per_strategy_cache moves v0.7.41 single file -> 3 per-strategy files (mixed)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir) / "url_validity_cache.json"
        # Create v0.7.41 single file with 2 entries
        now = time.time()
        entries = {
            "https://a.com/": _url_validity.CacheEntry(url="https://a.com/", timestamp=now, issues=("ok",), access_count=5),
            "https://b.com/": _url_validity.CacheEntry(url="https://b.com/", timestamp=now, issues=("ok",), access_count=10),
        }
        _url_validity._save_cache(base, entries)
        assert base.exists()
        # Migrate
        result = _cache_migration.migrate_to_per_strategy_cache(base_path=base)
        assert result["migrated"] is True, f"migration should have occurred: {result}"
        assert result["entries_migrated"] == 2, f"expected 2 entries migrated, got {result['entries_migrated']}"
        # Source should be deleted
        assert not base.exists(), f"source should be deleted, but exists: {base}"
        # Mixed file should exist with entries
        mixed_file = Path(result["mixed_file"])
        assert mixed_file.exists(), f"mixed file should exist: {mixed_file}"
        loaded = _url_validity._load_cache(mixed_file)
        assert "https://a.com/" in loaded, f"a.com should be in mixed file, got: {list(loaded.keys())}"
        assert "https://b.com/" in loaded, f"b.com should be in mixed file, got: {list(loaded.keys())}"


def test_split_to_per_strategy_v0_7_45() -> None:
    """split_to_per_strategy splits mixed file by access_count threshold (default 10)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir) / "url_validity_cache.json"
        # First, create v0.7.41 single file and migrate to mixed
        now = time.time()
        entries = {
            "https://low.com/": _url_validity.CacheEntry(url="https://low.com/", timestamp=now, issues=("ok",), access_count=0),
            "https://mid.com/": _url_validity.CacheEntry(url="https://mid.com/", timestamp=now, issues=("ok",), access_count=5),
            "https://high.com/": _url_validity.CacheEntry(url="https://high.com/", timestamp=now, issues=("ok",), access_count=100),
        }
        _url_validity._save_cache(base, entries)
        _cache_migration.migrate_to_per_strategy_cache(base_path=base)
        # Now split
        result = _cache_migration.split_to_per_strategy(base_path=base, lfu_threshold=10)
        assert result["split"] is True, f"split should have occurred: {result}"
        # LRU file: low + mid (access_count < 10)
        assert result["lru_entries"] == 2, f"expected 2 LRU entries, got {result['lru_entries']}"
        # LFU file: high (access_count >= 10)
        assert result["lfu_entries"] == 1, f"expected 1 LFU entry, got {result['lfu_entries']}"
        # Verify files
        lru_file = Path(result["lru_file"])
        lfu_file = Path(result["lfu_file"])
        assert lru_file.exists(), f"lru file should exist: {lru_file}"
        assert lfu_file.exists(), f"lfu file should exist: {lfu_file}"
        lru_loaded = _url_validity._load_cache(lru_file)
        lfu_loaded = _url_validity._load_cache(lfu_file)
        assert "https://low.com/" in lru_loaded
        assert "https://mid.com/" in lru_loaded
        assert "https://high.com/" in lfu_loaded


def main() -> int:
    test_funcs = [
        test_migrate_to_per_strategy_cache_v0_7_44,
        test_split_to_per_strategy_v0_7_45,
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
