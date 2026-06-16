"""workflow_kit.v_r13_commit_diff - V-R13 layer 2 commit-level diff (v0.7.47+).

ADR-023 follow-up: V-R13 layer 2 (?range=A..B) 의 *commit-level diff* 의 *cross-vendor* 보강.
- check_url_semantic_commit_diff_github: GitHub commits between range A..B
- check_url_semantic_commit_diff_bitbucket: Bitbucket commits between range A..B
- check_url_semantic_commit_diff_dispatch: auto-routes by URL host

Cross-vendor commit-level diff 는 v0.7.41 의 *file-level range diff* 의 *operational* 보강.
Layer 2 (?range=A..B) 의 *commit-level granularity* 의 *operational* 의 *low-friction* 정공법.
"""

from __future__ import annotations

import urllib.error
import urllib.request
import base64
from typing import Any


def check_url_semantic_commit_diff_github(
    org: str,
    repo: str,
    range_a: str,
    range_b: str,
    *,
    user: str | None = None,
    token: str | None = None,
    requests_get=None,
) -> list[dict[str, Any]]:
    """Return list of commit dicts between range_a..range_b on GitHub.

    GET https://api.github.com/repos/{org}/{repo}/compare/{range_a}...{range_b}

    Args:
        org: GitHub org
        repo: GitHub repo
        range_a: earlier ref (sha/branch/tag)
        range_b: later ref (sha/branch/tag)
        user, token: GitHub PAT credentials (optional, but recommended for rate limits)
        requests_get: optional injected requests_get for testing

    Returns:
        List of commit dicts (each has 'sha', 'commit.message', 'commit.author', etc.)
        Empty list on error.
    """
    if requests_get is None:
        def requests_get(url: str, **kwargs):
            return urllib.request.urlopen(
                urllib.request.Request(url, headers=kwargs.get("headers", {})),
                timeout=kwargs.get("timeout", 30),
            )
    url = f"https://api.github.com/repos/{org}/{repo}/compare/{range_a}...{range_b}"
    headers = {"User-Agent": "workflow-kit-url-validity/0.7.47", "Accept": "application/vnd.github+json"}
    if user and token:
        auth_str = base64.b64encode(f"{user}:{token}".encode("utf-8")).decode("ascii")
        headers["Authorization"] = f"Basic {auth_str}"
    try:
        response = requests_get(url, headers=headers, timeout=10)
        if response.status == 200:
            import json
            data = json.loads(response.read().decode("utf-8"))
            if isinstance(data, dict) and "commits" in data:
                return data["commits"]
            return []
        return []
    except (urllib.error.URLError, OSError, TimeoutError, ValueError):
        return []


def check_url_semantic_commit_diff_bitbucket(
    workspace: str,
    repo: str,
    range_a: str,
    range_b: str,
    *,
    user: str | None = None,
    token: str | None = None,
    requests_get=None,
) -> list[dict[str, Any]]:
    """Return list of commit dicts between range_a..range_b on Bitbucket.

    GET https://api.bitbucket.org/2.0/repositories/{workspace}/{repo}/commits?since={range_a}&until={range_b}

    Args:
        workspace: Bitbucket workspace (org)
        repo: Bitbucket repo
        range_a: earlier ref (sha/branch/tag)
        range_b: later ref (sha/branch/tag)
        user, token: Bitbucket app password (optional, for authenticated higher rate limit)
        requests_get: optional injected requests_get for testing

    Returns:
        List of commit dicts (each has 'hash', 'message', 'author', 'date')
        Empty list on error.
    """
    if requests_get is None:
        def requests_get(url: str, **kwargs):
            return urllib.request.urlopen(
                urllib.request.Request(url, headers=kwargs.get("headers", {})),
                timeout=kwargs.get("timeout", 30),
            )
    url = f"https://api.bitbucket.org/2.0/repositories/{workspace}/{repo}/commits?since={range_a}&until={range_b}"
    headers = {"User-Agent": "workflow-kit-url-validity/0.7.47"}
    if user and token:
        auth_str = base64.b64encode(f"{user}:{token}".encode("utf-8")).decode("ascii")
        headers["Authorization"] = f"Basic {auth_str}"
    try:
        response = requests_get(url, headers=headers, timeout=10)
        if response.status == 200:
            import json
            data = json.loads(response.read().decode("utf-8"))
            if isinstance(data, dict) and "values" in data:
                return data["values"]
            return []
        return []
    except (urllib.error.URLError, OSError, TimeoutError, ValueError):
        return []


def check_url_semantic_commit_diff_dispatch(
    url: str,
    range_a: str,
    range_b: str,
    *,
    user: str | None = None,
    token: str | None = None,
    requests_get=None,
) -> list[dict[str, Any]]:
    """Auto-route commit-level diff by URL host (v0.7.47+).

    Args:
        url: V-R13 URL to determine host (e.g. https://github.com/foo/bar or https://bitbucket.org/foo/bar)
        range_a: earlier ref
        range_b: later ref
        user, token: optional credentials
        requests_get: optional injected requests_get for testing

    Returns:
        List of commit dicts from the appropriate vendor API.
        Empty list for unsupported hosts.
    """
    from urllib.parse import urlparse
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    if "github.com" in host:
        # Path: /{org}/{repo}
        parts = parsed.path.strip("/").split("/")
        if len(parts) >= 2:
            return check_url_semantic_commit_diff_github(
                org=parts[0], repo=parts[1].replace(".git", ""),
                range_a=range_a, range_b=range_b,
                user=user, token=token, requests_get=requests_get,
            )
    elif "bitbucket.org" in host:
        # Path: /{workspace}/{repo}
        parts = parsed.path.strip("/").split("/")
        if len(parts) >= 2:
            return check_url_semantic_commit_diff_bitbucket(
                workspace=parts[0], repo=parts[1].replace(".git", ""),
                range_a=range_a, range_b=range_b,
                user=user, token=token, requests_get=requests_get,
            )
    return []
