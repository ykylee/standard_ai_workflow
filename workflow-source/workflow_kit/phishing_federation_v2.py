"""workflow_kit.phishing_federation_v2 - extensible multi-source phishing federation (v0.7.46+).

ADR-023 follow-up: multi-source federation 의 *extensible* 정공법.
- fetch_federated_phishing_urls_v2: accepts a list of source callables, dedups + sorts
- v1 (v0.7.45) was hard-coded for 2 sources (PhishTank + OpenPhish)
- v2 (v0.7.46) is extensible: caller provides any number of sources

Each source is a callable that returns a list[str] (phishing URLs).
"""

from __future__ import annotations

from typing import Callable


def fetch_federated_phishing_urls_v2(
    sources: list[Callable[[], list[str]]],
) -> list[str]:
    """Fetch + dedup phishing URLs from an extensible list of sources (v0.7.46+).

    Each source is a callable that returns a list[str] of phishing URLs.
    Sources that return [] (e.g. due to API failure) are silently skipped.

    Args:
        sources: list of callables, each returns list[str] of phishing URLs

    Returns:
        Sorted, deduped list of phishing URLs (case-insensitive).
    """
    urls: set[str] = set()
    for source in sources:
        try:
            result = source()
            for url in result:
                urls.add(url.strip().lower())
        except Exception:
            pass  # silent fallback on source failure
    return sorted(urls)


def build_default_sources_v2(
    phishtank_api_key: str | None = None,
    *,
    include_phishtank: bool = True,
    include_openphish: bool = True,
) -> list[Callable[[], list[str]]]:
    """Build the default 2-source list (PhishTank + OpenPhish) for federation v2.

    Args:
        phishtank_api_key: PhishTank API key (free tier: 5 req/hour)
        include_phishtank: whether to include PhishTank (default True)
        include_openphish: whether to include OpenPhish (default True)

    Returns:
        list of callables for fetch_federated_phishing_urls_v2
    """
    from workflow_kit.phishing_keywords import (
        fetch_phishtank_feed,
        fetch_openphish_feed,
    )
    sources: list[Callable[[], list[str]]] = []
    if include_phishtank and phishtank_api_key:
        sources.append(lambda: fetch_phishtank_feed(phishtank_api_key))
    if include_openphish:
        sources.append(fetch_openphish_feed)
    return sources
