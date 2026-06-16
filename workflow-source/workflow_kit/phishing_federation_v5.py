"""workflow_kit.phishing_federation_v5 - 3 source weighted voting (v0.7.50+).

ADR-023 follow-up: v4 의 *3 source extension* 의 *operational* 보강.
- fetch_federated_phishing_urls_v5: 3 source weighted voting (configurable 3rd source)
- build_default_sources_v5: 3 source default (PhishTank + OpenPhish + custom)
- 3rd source is user-provided (e.g. URLhaus free API) - keeps it FREE tier

Federation v1 -> v2 -> v3 -> v4 -> v5 의 *operational* 의 *evolution*:
- v1 (v0.7.45): hard-coded 2 sources
- v2 (v0.7.46): extensible
- v3 (v0.7.48): cross-source verification (count)
- v4 (v0.7.49): weighted voting (confidence)
- v5 (v0.7.50): 3 source weighted voting (configurable 3rd source)

3 source 의 *weighted voting* 의 *false positive reduction* 의 *operational* 보강.
All FREE tier - 3rd source 의 *user-provided callable* 의 *low-friction* 정공법.
"""

from __future__ import annotations

from typing import Callable


def fetch_federated_phishing_urls_v5(
    sources_with_weights: list[tuple[Callable[[], list[str]], float]],
    *,
    min_confidence: float = 0.0,
) -> list[tuple[str, float, list[str]]]:
    """Fetch + score phishing URLs with 3 source weighted voting (v0.7.50+).

    Each source is a (callable, weight) pair. Returns URLs sorted by confidence desc.
    Typical usage: 3 sources (PhishTank + OpenPhish + URLhaus/etc).

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
                url_data[normalized] = {"confidence": 0.0, "sources": []}
            url_data[normalized]["confidence"] = float(url_data[normalized]["confidence"]) + weight
            url_data[normalized]["sources"].append(source_name)
    filtered = [
        (url, data["confidence"], data["sources"])
        for url, data in url_data.items()
        if float(data["confidence"]) >= min_confidence
    ]
    return sorted(filtered, key=lambda x: (-float(x[1]), x[0]))


def build_default_sources_v5(
    phishtank_api_key: str | None = None,
    third_source: Callable[[], list[str]] | None = None,
    third_weight: float = 0.9,
    *,
    include_phishtank: bool = True,
    include_openphish: bool = True,
    include_third: bool = True,
) -> list[tuple[Callable[[], list[str]], float]]:
    """Build default 3 source list with weights (v0.7.50+).

    PhishTank weight = 1.0 (community-verified)
    OpenPhish weight = 0.8 (high-frequency, smaller dataset)
    Third source weight = 0.9 (user-provided, e.g. URLhaus, abuse.ch)

    Args:
        phishtank_api_key: PhishTank API key (free tier: 5 req/hour)
        third_source: optional callable for 3rd source (e.g. URLhaus)
        third_weight: weight for 3rd source (default 0.9)
        include_phishtank: whether to include PhishTank (default True)
        include_openphish: whether to include OpenPhish (default True)
        include_third: whether to include 3rd source (default True)

    Returns:
        list of (callable, weight) tuples
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
    if include_third and third_source is not None:
        sources.append((third_source, third_weight))
    return sources
