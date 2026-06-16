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


def main() -> int:
    test_funcs = [
        test_migrate_to_per_strategy_cache_v0_7_44,
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
