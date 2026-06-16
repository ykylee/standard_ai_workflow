"""workflow_kit.cache_dashboard_export - cache dashboard export to JSON/Markdown (v0.7.49+).

ADR-024 follow-up: per-strategy cache dashboard 의 *export* 의 *operational* 보강.
- export_dashboard_json(cache) -> str: JSON-serialized dashboard
- export_dashboard_markdown(cache) -> str: Markdown-formatted dashboard
- write_dashboard(cache, path, *, format="json") -> None: write to disk

Export 의 *operational* 의 *low-friction* 정공법.
External consumers (PR review, ops review) 의 *machine-readable* 의 *operational* 보강.
"""

from __future__ import annotations

import json
import os
from typing import Any, Literal


def export_dashboard_json(cache: dict[str, dict[str, Any]]) -> str:
    """Export dashboard as JSON (v0.7.49+).

    Args:
        cache: dict of url -> entry

    Returns:
        JSON string
    """
    from workflow_kit.cache_dashboard import cache_dashboard_dict
    return json.dumps(cache_dashboard_dict(cache), indent=2, sort_keys=True)


def export_dashboard_markdown(cache: dict[str, dict[str, Any]]) -> str:
    """Export dashboard as Markdown (v0.7.49+).

    Args:
        cache: dict of url -> entry

    Returns:
        Markdown-formatted string
    """
    from workflow_kit.cache_dashboard import cache_dashboard_dict
    data = cache_dashboard_dict(cache)
    lines = [
        "# Per-Strategy Cache Dashboard",
        "",
        "| strategy | size | hits | misses | hit_rate | evictions |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for strategy in sorted(data["strategies"].keys()):
        s = data["strategies"][strategy]
        lines.append(
            f"| {strategy} | {s['size']} | {s['hits']} | {s['misses']} | "
            f"{s['hit_rate']:.4f} | {s['evictions']} |"
        )
    totals = data["totals"]
    lines.append(
        f"| **TOTAL** | **{totals['total_size']}** | **{totals['total_hits']}** | "
        f"**{totals['total_misses']}** | **{totals['overall_hit_rate']:.4f}** | "
        f"**{totals['total_evictions']}** |"
    )
    return "\n".join(lines)


def write_dashboard(
    cache: dict[str, dict[str, Any]],
    path: str,
    *,
    format: Literal["json", "markdown"] = "json",
) -> None:
    """Write dashboard to disk (v0.7.49+).

    Args:
        cache: dict of url -> entry
        path: filesystem path
        format: 'json' or 'markdown'
    """
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    if format == "json":
        content = export_dashboard_json(cache)
    elif format == "markdown":
        content = export_dashboard_markdown(cache)
    else:
        raise ValueError(f"unknown format: {format}")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)
