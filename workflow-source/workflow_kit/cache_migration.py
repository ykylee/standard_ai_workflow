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
    }
