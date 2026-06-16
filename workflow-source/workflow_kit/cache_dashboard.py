"""workflow_kit.cache_dashboard - per-strategy cache dashboard (v0.7.48+).

ADR-024 follow-up: per-strategy cache 의 *dashboard* 의 *operational* 보강.
- cache_dashboard: returns formatted table string (strategy / size / hits / misses / hit_rate / evictions)
- cache_dashboard_dict: returns dict version (for machine consumption)

Per-strategy cache dashboard 의 *formatted output* 의 *operational* 의 *low-friction* 정공법.
"""

from __future__ import annotations

from typing import Any


def cache_dashboard(
    cache: dict[str, dict[str, Any]],
    *,
    hits_field: str = "hits",
    miss_field: str = "misses",
    eviction_field: str = "evictions",
) -> str:
    """Format per-strategy cache analytics as a dashboard table (v0.7.48+).

    Args:
        cache: dict of url -> entry (with 'strategy', 'hits', 'misses', 'evictions' fields)
        hits_field: name of hits counter field in entry
        miss_field: name of misses counter field in entry
        eviction_field: name of evictions counter field in entry

    Returns:
        Multi-line formatted table string. Columns: strategy, size, hits, misses, hit_rate, evictions.
    """
    from workflow_kit.cache_analytics import cache_analytics
    by_strategy = cache_analytics(
        cache, hits_field=hits_field, miss_field=miss_field, eviction_field=eviction_field,
    )
    lines = [
        "Per-Strategy Cache Dashboard",
        "=" * 60,
        f"{'strategy':<10} {'size':>6} {'hits':>8} {'misses':>8} {'hit_rate':>10} {'evictions':>10}",
        "-" * 60,
    ]
    for strategy in sorted(by_strategy.keys()):
        s = by_strategy[strategy]
        lines.append(
            f"{strategy:<10} {s['size']:>6} {s['hits']:>8} {s['misses']:>8} "
            f"{s['hit_rate']:>10.4f} {s['evictions']:>10}"
        )
    lines.append("=" * 60)
    total_size = sum(s["size"] for s in by_strategy.values())
    total_hits = sum(s["hits"] for s in by_strategy.values())
    total_misses = sum(s["misses"] for s in by_strategy.values())
    total_evictions = sum(s["evictions"] for s in by_strategy.values())
    total_requests = total_hits + total_misses
    overall_hit_rate = (total_hits / total_requests) if total_requests > 0 else 0.0
    lines.append(
        f"{'TOTAL':<10} {total_size:>6} {total_hits:>8} {total_misses:>8} "
        f"{overall_hit_rate:>10.4f} {total_evictions:>10}"
    )
    return "\n".join(lines)


def cache_dashboard_dict(
    cache: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Return dashboard as dict (machine-readable) (v0.7.48+).

    Returns:
        dict with 'strategies' (per-strategy) + 'totals' (aggregate)
    """
    from workflow_kit.cache_analytics import cache_analytics, cache_analytics_summary
    return {
        "strategies": cache_analytics(cache),
        "totals": cache_analytics_summary(cache),
    }
