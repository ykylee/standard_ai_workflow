"""workflow_kit.cache_migration - v0.7.41 single file -> 3 per-strategy files (v0.7.44+).

ADR-024 follow-up: per-strategy cache file 의 *full migration* 의 *operational* 보강.
- migrate_to_per_strategy_cache(base_path): reads v0.7.41 single file
  and splits into 3 per-strategy files (lru/lfu/mixed).
- The default strategy is "mixed" (entries are copied as-is to the mixed file).
- LRU/LFU-specific splitting is a v0.7.45+ follow-up (requires per-entry access_count tracking).

Backward compat:
- If single file does not exist, returns immediately (WARN)
- If per-strategy files already exist, returns immediately (WARN)
- Original single file is DELETED on successful migration (WARN emitted)
"""

from __future__ import annotations

import sys
from pathlib import Path

from workflow_kit.url_validity import (
    DEFAULT_CACHE_FILE,
    _load_cache,
    cache_file_for_strategy,
    CacheEntry,
)
def migrate_to_per_strategy_cache(base_path: Path | None = None) -> dict[str, object]:
    """Migrate v0.7.41 single cache file to 3 per-strategy files (v0.7.44+, ADR-024 follow-up).

    Args:
        base_path: base cache file path (default: ~/.workflow_kit/url_validity_cache.json)

    Returns:
        dict with migration status:
          - migrated: bool (True if migration occurred)
          - source: str (source single file path)
          - lru_file: str (per-strategy lru file path)
          - lfu_file: str (per-strategy lfu file path)
          - mixed_file: str (per-strategy mixed file path)
          - entries_migrated: int (number of entries migrated)
    """
    base = base_path or DEFAULT_CACHE_FILE
    lru_file = cache_file_for_strategy(base, "lru")
    lfu_file = cache_file_for_strategy(base, "lfu")
    mixed_file = cache_file_for_strategy(base, "mixed")
    result = {
        "migrated": False,
        "source": str(base),
        "lru_file": str(lru_file),
        "lfu_file": str(lfu_file),
        "mixed_file": str(mixed_file),
        "entries_migrated": 0,
    }
    # If per-strategy files already exist, abort
    if lru_file.exists() or lfu_file.exists() or mixed_file.exists():
        print(f"WARN: per-strategy files already exist; skipping migration", file=sys.stderr)
        return result
    # If source does not exist, abort
    if not base.exists():
        print(f"WARN: source single file does not exist ({base}); skipping migration", file=sys.stderr)
        return result
    # Load source entries
    entries = _load_cache(base)
    if not entries:
        print(f"WARN: source single file is empty ({base}); skipping migration", file=sys.stderr)
        return result
    # Write to mixed file (default strategy)
    import json
    raw = {
        url: {
            "timestamp": entry.timestamp,
            "issues": list(entry.issues),
            "access_count": entry.access_count,
        }
        for url, entry in entries.items()
    }
    serialized = json.dumps(raw, indent=2, sort_keys=True)
    mixed_file.parent.mkdir(parents=True, exist_ok=True)
    mixed_file.write_text(serialized, encoding="utf-8")
    # Delete source
    base.unlink()
    print(f"INFO: migrated {len(entries)} entries from {base} to {mixed_file}", file=sys.stderr)
    return {
        "migrated": True,
        "source": str(base),
        "lru_file": str(lru_file),
        "lfu_file": str(lfu_file),
        "mixed_file": str(mixed_file),
        "entries_migrated": len(entries),
        "entries_migrated": len(entries),
    }


def split_to_per_strategy(
    base_path: Path | None = None,
    *,
    lfu_threshold: int = 10,
) -> dict[str, object]:
    """Split per-strategy mixed file into LRU + LFU files (v0.7.45+).

    Reads the mixed file (created by migrate_to_per_strategy_cache) and splits
    entries into 2 files:
    - LRU file: entries with access_count < lfu_threshold
    - LFU file: entries with access_count >= lfu_threshold

    Args:
        base_path: base cache file path (default: ~/.workflow_kit/url_validity_cache.json)
        lfu_threshold: access_count threshold for LFU classification (default 10)

    Returns:
        dict with split status:
          - split: bool
          - mixed_file: str
          - lru_file: str
          - lfu_file: str
          - lru_entries: int
          - lfu_entries: int
    """
    base = base_path or DEFAULT_CACHE_FILE
    lru_file = cache_file_for_strategy(base, "lru")
    lfu_file = cache_file_for_strategy(base, "lfu")
    mixed_file = cache_file_for_strategy(base, "mixed")
    result = {
        "split": False,
        "mixed_file": str(mixed_file),
        "lru_file": str(lru_file),
        "lfu_file": str(lfu_file),
        "lru_entries": 0,
        "lfu_entries": 0,
    }
    if not mixed_file.exists():
        print(f"WARN: mixed file does not exist ({mixed_file}); skipping split", file=sys.stderr)
        return result
    entries = _load_cache(mixed_file)
    if not entries:
        print(f"WARN: mixed file is empty ({mixed_file}); skipping split", file=sys.stderr)
        return result
    lru_entries: dict[str, CacheEntry] = {}
    lfu_entries: dict[str, CacheEntry] = {}
    for url, entry in entries.items():
        if entry.access_count >= lfu_threshold:
            lfu_entries[url] = entry
        else:
            lru_entries[url] = entry
    # Write LRU file
    if lru_entries:
        from workflow_kit.url_validity import _save_cache
        _save_cache(lru_file, lru_entries)
    # Write LFU file
    if lfu_entries:
        from workflow_kit.url_validity import _save_cache
        _save_cache(lfu_file, lfu_entries)
    print(
        f"INFO: split {len(entries)} entries -> {len(lru_entries)} LRU + {len(lfu_entries)} LFU "
        f"(threshold={lfu_threshold})",
        file=sys.stderr,
    )
    return {
        "split": True,
        "mixed_file": str(mixed_file),
        "lru_file": str(lru_file),
        "lfu_file": str(lfu_file),
        "lru_entries": len(lru_entries),
        "lfu_entries": len(lfu_entries),
    }
