"""workflow_kit.v_r13_commit_diff_integration - V-R13 layer 2 commit-level diff integration (v0.7.48+).

ADR-019 + ADR-023 follow-up: V-R13 layer 2 의 *operational* integration 보강.
- check_url_semantic_with_commit_diff: combines V-R13 parse + commit diff verification
- format_commit_diff_summary: returns a human-readable summary string

V-R13 layer 2 commit-level diff 의 *existing v-r13 checks* 와의 *integration* 의 *low-friction* 정공법.
"""

from __future__ import annotations

from typing import Any
from urllib.parse import urlparse, parse_qs

from workflow_kit.v_r13_commit_diff import check_url_semantic_commit_diff_dispatch


def parse_range_from_url(url: str) -> tuple[str, str] | None:
    """Extract ?range=A..B from a V-R13 semantic URL (v0.7.48+).

    Args:
        url: V-R13 URL with optional ?range= query param

    Returns:
        (range_a, range_b) tuple if ?range=A..B is present, else None
    """
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    range_strs = qs.get("range", [])
    if not range_strs:
        return None
    parts = range_strs[0].split("..")
    if len(parts) != 2:
        return None
    return parts[0], parts[1]


def check_url_semantic_with_commit_diff(
    url: str,
    *,
    user: str | None = None,
    token: str | None = None,
    requests_get=None,
) -> dict[str, Any]:
    """Check V-R13 URL with commit-level diff (v0.7.48+).

    Combines:
    1. Parse ?range=A..B from URL
    2. Dispatch to GitHub/Bitbucket commit diff API
    3. Return summary dict

    Args:
        url: V-R13 URL with ?range=A..B query
        user, token: optional credentials
        requests_get: optional injected requests_get for testing

    Returns:
        dict with keys:
          - has_range: bool (True if ?range=A..B was present)
          - range_a, range_b: str (or None)
          - commit_count: int (number of commits in range)
          - commits: list[dict] (commit list, empty on error)
          - vendor: str (github / bitbucket / unknown)
    """
    range_parts = parse_range_from_url(url)
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    vendor = "github" if "github.com" in host else "bitbucket" if "bitbucket.org" in host else "unknown"
    if range_parts is None:
        return {
            "has_range": False,
            "range_a": None,
            "range_b": None,
            "commit_count": 0,
            "commits": [],
            "vendor": vendor,
        }
    range_a, range_b = range_parts
    commits = check_url_semantic_commit_diff_dispatch(
        url=url, range_a=range_a, range_b=range_b,
        user=user, token=token, requests_get=requests_get,
    )
    return {
        "has_range": True,
        "range_a": range_a,
        "range_b": range_b,
        "commit_count": len(commits),
        "commits": commits,
        "vendor": vendor,
    }


def format_commit_diff_summary(result: dict[str, Any]) -> str:
    """Format commit diff result as a human-readable summary (v0.7.48+).

    Args:
        result: dict from check_url_semantic_with_commit_diff

    Returns:
        Multi-line summary string
    """
    if not result.get("has_range"):
        return f"[V-R13 layer 2] no ?range=A..B in URL (vendor={result.get('vendor', 'unknown')})"
    range_a = result.get("range_a", "?")
    range_b = result.get("range_b", "?")
    count = result.get("commit_count", 0)
    vendor = result.get("vendor", "unknown")
    return (
        f"[V-R13 layer 2] {vendor} range={range_a}..{range_b} -> {count} commits\n"
        f"  commits:\n"
        + "\n".join(
            f"    - {c.get('sha', c.get('hash', '?'))[:8]}: "
            f"{c.get('commit', {}).get('message', c.get('message', ''))[:60]}"
            for c in result.get("commits", [])
        )
    )
