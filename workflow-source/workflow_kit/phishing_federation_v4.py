"""workflow_kit.phishing_federation_v4 - phishing federation v4 (v0.7.49+).

ADR-023 follow-up: v3 의 cross-source verification 의 *weighted voting* 의 *operational* 보강.
- fetch_federated_phishing_urls_v4: returns URLs with weighted confidence score
- Per-source weights: PhishTank=1.0, OpenPhish=0.8, etc. (configurable)
- Returns list sorted by confidence desc

Phishing federation v1 -> v2 -> v3 -> v4 의 *operational* 의 *evolution*:
- v1 (v0.7.45): hard-coded 2 sources
- v2 (v0.7.46): extensible
- v3 (v0.7.48): cross-source verification (>= N sources)
- v4 (v0.7.49): weighted voting with per-source confidence scores

Weighted voting 의 *false positive reduction* 의 *operational* 의 *low-friction* 정공법.
"""

from __future__ import annotations

from typing import Callable


def fetch_federated_phishing_urls_v4(
    sources_with_weights: list[tuple[Callable[[], list[str]], float]],
    *,
    min_confidence: float = 0.0,
) -> list[tuple[str, float, list[str]]]:
    """Fetch + score phishing URLs with weighted voting (v0.7.49+).

    Each source has a weight (confidence in that source's data quality).
    URL's confidence = sum of weights for sources that reported it.

    Args:
        sources_with_weights: list of (callable, weight) tuples
        min_confidence: filter out URLs with confidence < this threshold (default 0.0)

    Returns:
        List of (url, confidence, source_names) tuples sorted by confidence desc, then url asc.
    """
    url_data: dict[str, dict[str, object]] = {}
    for idx, (source, weight) in enumerate(sources_with_weights):
        source_name = f"source_{idx}"
        try:
            result = source()
        except Exception:
            continue
        for url in result:
            normalized = url.strip().lower()
            if normalized not in url_data:
                url_data[normalized] = {
                    "confidence": 0.0,
                    "sources": [],
                }
            url_data[normalized]["confidence"] = float(url_data[normalized]["confidence"]) + weight
            url_data[normalized]["sources"].append(source_name)
    # Filter and sort
    filtered = [
        (url, data["confidence"], data["sources"])
        for url, data in url_data.items()
        if float(data["confidence"]) >= min_confidence
    ]
    return sorted(filtered, key=lambda x: (-float(x[1]), x[0]))


def build_default_sources_v4(
    phishtank_api_key: str | None = None,
    *,
    include_phishtank: bool = True,
    include_openphish: bool = True,
) -> list[tuple[Callable[[], list[str]], float]]:
    """Build default 2-source list with weights (v0.7.49+).

    PhishTank weight = 1.0 (community-verified)
    OpenPhish weight = 0.8 (high-frequency, smaller dataset)
    """
    from workflow_kit.phishing_keywords import (
        fetch_phishtank_feed,
        fetch_openphish_feed,
    )
    sources: list[tuple[Callable[[], list[str]], float]] = []
    if include_phishtank and phishtank_api_key:
        sources.append((lambda: fetch_phishtank_feed(phishtank_api_key), 1.0))
    if include_openphish:
        sources.append((fetch_openphish_feed, 0.8))
    return sources
