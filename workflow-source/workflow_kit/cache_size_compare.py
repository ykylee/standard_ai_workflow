"""workflow_kit.cache_size_compare - per-strategy cache size comparison (v0.7.46+).

ADR-024 follow-up: per-strategy cache file 의 *size comparison* 의 *operational* 보강.
- cache_size_per_strategy(base_path): returns dict[str, int] of bytes per strategy
- cache_size_per_strategy_compare(base_path): returns sorted list of (strategy, bytes) for A/B compare
"""

from __future__ import annotations

from pathlib import Path

from workflow_kit.url_validity import DEFAULT_CACHE_FILE, cache_file_for_strategy


def cache_size_per_strategy(base_path: Path | None = None) -> dict[str, int]:
    """Return cache file size in bytes per strategy (v0.7.46+).

    Args:
        base_path: base cache file path (default: ~/.workflow_kit/url_validity_cache.json)

    Returns:
        dict mapping strategy name to file size in bytes (0 if file doesn't exist)
    """
    base = base_path or DEFAULT_CACHE_FILE
    sizes: dict[str, int] = {}
    for strategy in ("lru", "lfu", "mixed"):
        cf = cache_file_for_strategy(base, strategy)
        if cf.exists():
            sizes[strategy] = cf.stat().st_size
        else:
            sizes[strategy] = 0
    return sizes


def cache_size_per_strategy_compare(base_path: Path | None = None) -> list[tuple[str, int]]:
    """Return sorted list of (strategy, bytes) for A/B compare (v0.7.46+).

    Returns:
        list of (strategy, bytes) sorted by bytes descending (largest first)
    """
    sizes = cache_size_per_strategy(base_path)
    return sorted(sizes.items(), key=lambda x: -x[1])
