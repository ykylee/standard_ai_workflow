"""workflow_kit.cache_lfu_decay_persist - per-URL LFU decay score persistence (v0.7.49+).

ADR-021 follow-up: per-URL LFU decay score 의 *persistence* 의 *operational* 보강.
- save_decay_scores(scores, path): write per-URL decay scores to disk (JSON)
- load_decay_scores(path) -> dict[str, float]: load per-URL decay scores from disk
- update_decay_score(scores, url, score, path): update + persist single URL's score

Per-URL LFU decay score 의 *persistence* 의 *low-friction* 정공법.
Cache reload 시 *preserved score* 의 *operational* 보강.
"""

from __future__ import annotations

import json
import os
import time
from typing import Any


def save_decay_scores(
    scores: dict[str, float],
    path: str,
    *,
    now: float | None = None,
) -> None:
    """Save per-URL decay scores to disk (v0.7.49+).

    Args:
        scores: dict of url -> decay_score
        path: filesystem path
        now: optional override for current time
    """
    if now is None:
        now = time.time()
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    payload = {
        "version": 1,
        "saved_at": now,
        "scores": scores,
    }
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, sort_keys=True)


def load_decay_scores(path: str) -> dict[str, float]:
    """Load per-URL decay scores from disk (v0.7.49+).

    Args:
        path: filesystem path

    Returns:
        dict of url -> decay_score (empty dict on error or missing file)
    """
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as fh:
            payload = json.load(fh)
        if isinstance(payload, dict) and "scores" in payload:
            scores = payload["scores"]
            if isinstance(scores, dict):
                return {str(k): float(v) for k, v in scores.items()}
        return {}
    except (OSError, json.JSONDecodeError, ValueError, TypeError):
        return {}


def update_decay_score(
    scores: dict[str, float],
    url: str,
    score: float,
    path: str,
) -> dict[str, float]:
    """Update a single URL's decay score and persist (v0.7.49+).

    Args:
        scores: existing scores dict (will be updated in place)
        url: URL key
        score: new decay score
        path: filesystem path to persist to

    Returns:
        The updated scores dict
    """
    scores[url] = score
    save_decay_scores(scores, path)
    return scores


def get_decay_score(
    scores: dict[str, float],
    url: str,
    default: float = 0.0,
) -> float:
    """Get a URL's decay score with default fallback (v0.7.49+).

    Args:
        scores: scores dict
        url: URL key
        default: default value if URL not in scores

    Returns:
        The decay score (or default)
    """
    return scores.get(url, default)


def merge_decay_scores(
    *score_dicts: dict[str, float],
) -> dict[str, float]:
    """Merge multiple score dicts (later overrides earlier) (v0.7.49+).

    Args:
        *score_dicts: variable number of score dicts

    Returns:
        Merged dict
    """
    merged: dict[str, float] = {}
    for d in score_dicts:
        merged.update(d)
    return merged
