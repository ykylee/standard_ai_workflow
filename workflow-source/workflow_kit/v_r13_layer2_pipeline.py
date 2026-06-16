"""workflow_kit.v_r13_layer2_pipeline - V-R13 layer 2 full pipeline (v0.7.49+).

ADR-019 + ADR-023 follow-up: V-R13 layer 2 의 *full pipeline* 의 *operational* 보강.
- run_layer2_pipeline(url, *, user, token, requests_get) -> PipelineResult
- Single function: parse -> dispatch -> format -> return all results

Pipeline 의 *one-call* 의 *operational* 의 *low-friction* 정공법.
CLI surface 의 *simplicity* 의 *operational* 보강.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from workflow_kit.v_r13_commit_diff_integration import (
    check_url_semantic_with_commit_diff,
    format_commit_diff_summary,
    parse_range_from_url,
)


@dataclass
class PipelineResult:
    """V-R13 layer 2 pipeline result (v0.7.49+)."""
    url: str
    has_range: bool
    range_a: str | None
    range_b: str | None
    vendor: str
    commit_count: int
    summary: str
    raw_result: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "url": self.url,
            "has_range": self.has_range,
            "range_a": self.range_a,
            "range_b": self.range_b,
            "vendor": self.vendor,
            "commit_count": self.commit_count,
            "summary": self.summary,
        }


def run_layer2_pipeline(
    url: str,
    *,
    user: str | None = None,
    token: str | None = None,
    requests_get=None,
) -> PipelineResult:
    """Run V-R13 layer 2 full pipeline (v0.7.49+).

    Combines: parse_range_from_url + check_url_semantic_with_commit_diff +
    format_commit_diff_summary, into a single PipelineResult.

    Args:
        url: V-R13 URL (with optional ?range=A..B)
        user, token: optional credentials
        requests_get: optional injected requests_get for testing

    Returns:
        PipelineResult dataclass with all parsed + diff + summary data.
    """
    range_parts = parse_range_from_url(url)
    if range_parts is None:
        # No range: short-circuit
        result: dict[str, Any] = {
            "has_range": False,
            "range_a": None,
            "range_b": None,
            "commit_count": 0,
            "commits": [],
            "vendor": "unknown",
        }
        # Detect vendor from URL host
        from urllib.parse import urlparse
        host = urlparse(url).netloc.lower()
        if "github.com" in host:
            result["vendor"] = "github"
        elif "bitbucket.org" in host:
            result["vendor"] = "bitbucket"
        return PipelineResult(
            url=url,
            has_range=False,
            range_a=None,
            range_b=None,
            vendor=result["vendor"],
            commit_count=0,
            summary=format_commit_diff_summary(result),
            raw_result=result,
        )
    # Has range: full pipeline
    result = check_url_semantic_with_commit_diff(
        url=url, user=user, token=token, requests_get=requests_get,
    )
    return PipelineResult(
        url=url,
        has_range=result["has_range"],
        range_a=result["range_a"],
        range_b=result["range_b"],
        vendor=result["vendor"],
        commit_count=result["commit_count"],
        summary=format_commit_diff_summary(result),
        raw_result=result,
    )


def run_layer2_pipeline_batch(
    urls: list[str],
    *,
    user: str | None = None,
    token: str | None = None,
    requests_get=None,
) -> list[PipelineResult]:
    """Run V-R13 layer 2 pipeline for multiple URLs (v0.7.49+).

    Args:
        urls: list of V-R13 URLs
        user, token: optional credentials
        requests_get: optional injected requests_get for testing

    Returns:
        List of PipelineResult (one per URL)
    """
    return [
        run_layer2_pipeline(url, user=user, token=token, requests_get=requests_get)
        for url in urls
    ]
