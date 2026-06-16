"""workflow_kit.cache_lfu_decay - LFUConfig + _save_cache direct integration (v0.7.47+).

ADR-021 follow-up: LFUConfig 의 compute_lfu_score_with_decay 의 *direct* integration 보강.
- save_cache_with_decay: writes cache entries with decay-weighted LFU scores
- select_eviction_candidates_with_decay: picks eviction candidates by lowest decay score

This module wraps url_validity._save_cache (not modifies it) to avoid edit conflicts.
LFUConfig 의 direct integration 의 *low-friction* 정공법.
"""

from __future__ import annotations

import time
from typing import Any


def save_cache_with_decay(
    cache: dict[str, dict[str, Any]],
    cache_path: str,
    config,  # LFUConfig
    *,
    now: float | None = None,
) -> dict[str, float]:
    """Save cache entries to disk with decay-weighted LFU scores (v0.7.47+).

    Args:
        cache: dict of url -> {status, body, timestamp, access_count, ...}
        cache_path: filesystem path to write to
        config: LFUConfig instance (from workflow_kit.lfu_config)
        now: optional override for current time (for testing)

    Returns:
        dict of url -> decay_score (for inspection)
    """
    from workflow_kit.lfu_config import compute_lfu_score_with_decay
    if now is None:
        now = time.time()
    scores: dict[str, float] = {}
    for url, entry in cache.items():
        access_count = entry.get("access_count", 0)
        timestamp = entry.get("timestamp", now)
        age = max(0.0, now - timestamp)
        try:
            score = compute_lfu_score_with_decay(
                access_count=access_count, age_seconds=age, config=config,
            )
        except ValueError:
            score = float(access_count)
        scores[url] = score
    _write_cache_file(cache_path, cache, scores)
    return scores


def select_eviction_candidates_with_decay(
    cache: dict[str, dict[str, Any]],
    config,
    n: int,
    *,
    now: float | None = None,
) -> list[str]:
    """Pick n URLs with the lowest decay-weighted LFU scores (v0.7.47+).

    Args:
        cache: dict of url -> {status, body, timestamp, access_count, ...}
        config: LFUConfig instance
        n: number of eviction candidates to return
        now: optional override for current time (for testing)

    Returns:
        List of URLs sorted by lowest decay_score (most-evictable first).
    """
    scores = save_cache_with_decay(cache, "<in-memory>", config, now=now)
    sorted_urls = sorted(scores.items(), key=lambda kv: kv[1])
    return [url for url, _ in sorted_urls[:n]]


def _write_cache_file(
    cache_path: str,
    cache: dict[str, dict[str, Any]],
    scores: dict[str, float],
) -> None:
    """Write cache + scores to disk (helper, JSON format)."""
    import json
    import os
    os.makedirs(os.path.dirname(cache_path) or ".", exist_ok=True)
    payload = {
        "version": 1,
        "entries": cache,
        "lfu_decay_scores": scores,
    }
    with open(cache_path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh)
