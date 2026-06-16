"""workflow_kit.phishing_federation_v3 - phishing federation v3 (v0.7.48+).

ADR-023 follow-up: v2 의 extensibility 의 follow-up.
- fetch_federated_phishing_urls_v3: union with cross-source verification (URLs in >= 2 sources)
- fetch_federated_phishing_urls_v3_with_min: configurable min source count (default 2)
- Returns the *high-confidence* URLs (cross-verified)

Cross-source verification 의 *operational* 보강.
- v1 (v0.7.45): hard-coded 2 sources
- v2 (v0.7.46): extensible, dedup + sort
- v3 (v0.7.48): extensible + cross-source verification (URLs in >= 2 sources)

High-confidence URL list 의 *operational* 의 *low-friction* 정공법.
False positive 의 *cross-source verification* 의 *operational* 보강.
"""

from __future__ import annotations

from typing import Callable


def fetch_federated_phishing_urls_v3(
    sources: list[Callable[[], list[str]]],
    *,
    min_source_count: int = 2,
) -> dict[str, list[str]]:
    """Fetch + cross-verify phishing URLs across multiple sources (v0.7.48+).

    Each source is a callable that returns a list[str] of phishing URLs.
    Returns URLs that appear in at least `min_source_count` distinct sources.

    Args:
        sources: list of callables, each returns list[str] of phishing URLs
        min_source_count: minimum number of sources that must agree (default 2)

    Returns:
        dict of url -> list of source indices that reported it (sorted by cross-source count desc)
    """
    # Map each URL to set of source indices
    url_sources: dict[str, set[int]] = {}
    for idx, source in enumerate(sources):
        try:
            result = source()
        except Exception:
            continue
        for url in result:
            normalized = url.strip().lower()
            if normalized not in url_sources:
                url_sources[normalized] = set()
            url_sources[normalized].add(idx)
    # Filter by min_source_count
    verified: dict[str, list[str]] = {}
    for url, source_indices in url_sources.items():
        if len(source_indices) >= min_source_count:
            verified[url] = [f"source_{i}" for i in sorted(source_indices)]
    # Sort by cross-source count desc, then URL asc
    return dict(sorted(verified.items(), key=lambda kv: (-len(kv[1]), kv[0])))


def fetch_federated_phishing_urls_v3_with_min(
    sources: list[Callable[[], list[str]]],
    min_source_count: int,
) -> list[str]:
    """Return flat list of URLs verified by >= min_source_count sources (v0.7.48+).

    Args:
        sources: list of callables
        min_source_count: minimum number of sources that must agree

    Returns:
        List of high-confidence URLs (sorted alphabetically).
    """
    result = fetch_federated_phishing_urls_v3(sources, min_source_count=min_source_count)
    return sorted(result.keys())
