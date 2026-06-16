"""workflow_kit.url_validity — URL validity check (V-R10, v0.7.35+ PoC).

ADR-010 채택. wiki frontmatter `resource` (ADR-006) + `last_ingested_from` URL 의
8 offline check + optional online HEAD request. PoC 단계: offline 8 check 만.

Offline check (8):
  1. URL scheme — `https://` only
  2. URL host parseable (RFC 3986)
  3. No path traversal (`..`)
  4. No internal/private IP (10/8, 192.168/16, 172.16/12, fc00::/7)
  5. No localhost (`localhost`, `127.0.0.1`, `::1`)
  6. No `file://` scheme
  7. No credentials in URL (`user:pass@`)
  8. GitHub URL form (if host = `github.com`): `/blob/<branch>/<path>` or `/tree/<branch>/<path>`

Online check (opt-in, `--v-r10-online`):
  - HTTP HEAD request → 200 / 3xx / 4xx / 5xx / timeout / TLS error / DNS fail

Usage:
    from workflow_kit.url_validity import check_url, UrlIssue

    issues = check_url("https://example.com/spec.md")
    for issue in issues:
        if issue.severity == "error":
            print(f"FAIL: {issue.message}")

CLI:
    python -m workflow_kit.url_validity <url>...
"""

from __future__ import annotations

import argparse
import ipaddress
import re
import sys
from dataclasses import dataclass
from typing import Literal
from urllib.parse import urlparse


# ---------------------------------------------------------------------------
# Severity
# ---------------------------------------------------------------------------
Severity = Literal["error", "warn"]


# ---------------------------------------------------------------------------
# Issue dataclass
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class UrlIssue:
    """Single URL validity issue."""

    rule: str  # e.g. "V-R10-scheme", "V-R10-localhost"
    severity: Severity
    message: str


# ---------------------------------------------------------------------------
# Offline check
# ---------------------------------------------------------------------------
_ALLOWED_SCHEMES: frozenset[str] = frozenset({"https"})
_LOCALHOST_NAMES: frozenset[str] = frozenset({"localhost"})


def _is_private_ip(host: str) -> bool:
    """Check if host is a private/internal IP address (IPv4 or IPv6)."""
    # strip IPv6 brackets
    raw = host.strip("[]")
    try:
        ip = ipaddress.ip_address(raw)
    except ValueError:
        return False
    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_multicast
    )


def _is_github_url(url: str) -> bool:
    """Check if URL is a GitHub URL."""
    try:
        parsed = urlparse(url)
    except ValueError:
        return False
    return parsed.hostname in ("github.com", "www.github.com")


def _has_credentials(url: str) -> bool:
    """Check if URL has user:pass@ credentials."""
    try:
        parsed = urlparse(url)
    except ValueError:
        return False
    return bool(parsed.username) or bool(parsed.password)


def _has_path_traversal(url: str) -> bool:
    """Check if URL path contains `..` segment."""
    try:
        parsed = urlparse(url)
    except ValueError:
        return False
    if not parsed.path:
        return False
    return any(seg == ".." for seg in parsed.path.split("/"))


def check_url(url: str) -> list[UrlIssue]:
    """Run all offline V-R10 checks on a URL.

    Returns a list of UrlIssue (empty if all checks pass).
    """
    issues: list[UrlIssue] = []

    # 1. scheme check
    try:
        parsed = urlparse(url)
    except ValueError as e:
        issues.append(UrlIssue(rule="V-R10-parse", severity="error", message=f"URL parse failed: {e}"))
        return issues

    scheme = parsed.scheme.lower()
    if not scheme:
        issues.append(UrlIssue(rule="V-R10-scheme", severity="error", message="URL missing scheme"))
    elif scheme not in _ALLOWED_SCHEMES:
        issues.append(
            UrlIssue(
                rule="V-R10-scheme",
                severity="error",
                message=f"scheme {scheme!r} not allowed (only https://)",
            )
        )

    # 2. host parseable
    host = parsed.hostname or ""
    if not host:
        if scheme:
            issues.append(UrlIssue(rule="V-R10-host", severity="error", message="URL missing host"))
    else:
        # 5. localhost
        if host.lower() in _LOCALHOST_NAMES or host.lower().endswith(".local"):
            issues.append(
                UrlIssue(
                    rule="V-R10-localhost",
                    severity="error",
                    message=f"localhost host {host!r} not allowed",
                )
            )
        # 4. private IP
        elif _is_private_ip(host):
            issues.append(
                UrlIssue(
                    rule="V-R10-private-ip",
                    severity="error",
                    message=f"private/internal IP {host!r} not allowed",
                )
            )

    # 3. path traversal
    if _has_path_traversal(url):
        issues.append(
            UrlIssue(
                rule="V-R10-traversal",
                severity="error",
                message="URL path contains `..` segment (traversal)",
            )
        )

    # 6. file:// scheme — already covered by scheme check, but explicit
    if scheme == "file":
        issues.append(
            UrlIssue(
                rule="V-R10-file-scheme",
                severity="error",
                message="file:// scheme not allowed",
            )
        )

    # 7. credentials
    if _has_credentials(url):
        issues.append(
            UrlIssue(
                rule="V-R10-credentials",
                severity="error",
                message="URL contains user:pass@ credentials (security risk)",
            )
        )

    # 8. GitHub URL form (soft warn)
    if _is_github_url(url):
        path = parsed.path
        # /owner/repo  (root) or /owner/repo/blob/branch/path or /owner/repo/tree/branch/path
        parts = [p for p in path.split("/") if p]
        if len(parts) >= 3 and parts[2] not in ("blob", "tree", "raw", "commits", "issues", "pull", "wiki", "actions"):
            issues.append(
                UrlIssue(
                    rule="V-R10-github-form",
                    severity="warn",
                    message=f"github.com URL form unusual: {url!r} (expected /owner/repo/blob/branch/...)",
                )
            )

    return issues


# ---------------------------------------------------------------------------
# Online HEAD layer (ADR-012)
# ---------------------------------------------------------------------------
def check_url_online(
    url: str,
    *,
    timeout: float = 10.0,
    user_agent: str = "workflow-kit-url-validity/0.7.35",
) -> list[UrlIssue]:
    """Online V-R10 check: HTTP HEAD request to detect stale URL.

    ADR-012. opt-in. CI/local dev --v-r10-online flag 시에만 활성.

    Returns:
        list[UrlIssue]:
        - HTTP 200 OK: pass (no issues)
        - HTTP 3xx: follow 1 hop, recheck
        - HTTP 404/410: ERROR (stale URL)
        - HTTP 5xx: WARN (transient, retry next run)
        - timeout: WARN (slow host)
        - TLS error: ERROR (security risk)
        - DNS failure: ERROR (host does not exist)
        - rate limit 429: WARN (back off)

    Note:
        - urllib.request 만 사용 (no extra dep)
        - HEAD request 만 (no body download)
        - 최대 1 redirect hop
    """
    import socket
    import ssl
    import urllib.error
    import urllib.request

    issues: list[UrlIssue] = []
    try:
        req = urllib.request.Request(url, method="HEAD")
        req.add_header("User-Agent", user_agent)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            status = resp.status
            if 200 <= status < 300:
                # OK
                return issues
            if 300 <= status < 400 and status != 304:
                # redirect — follow 1 hop
                location = resp.headers.get("Location", "")
                if location:
                    try:
                        return check_url_online(location, timeout=timeout, user_agent=user_agent)
                    except Exception as e:  # noqa: BLE001
                        issues.append(
                            UrlIssue(
                                rule="V-R10-online-redirect",
                                severity="warn",
                                message=f"redirect target failed: {e}",
                            )
                        )
                        return issues
                return issues
            if status in (404, 410):
                issues.append(
                    UrlIssue(
                        rule="V-R10-online-stale",
                        severity="error",
                        message=f"HTTP {status}: URL appears stale (not found / gone)",
                    )
                )
            elif 500 <= status < 600:
                issues.append(
                    UrlIssue(
                        rule="V-R10-online-server-error",
                        severity="warn",
                        message=f"HTTP {status}: server error (transient, retry next run)",
                    )
                )
            elif status == 429:
                issues.append(
                    UrlIssue(
                        rule="V-R10-online-rate-limit",
                        severity="warn",
                        message="HTTP 429: rate limited (back off)",
                    )
                )
            else:
                issues.append(
                    UrlIssue(
                        rule="V-R10-online-unexpected",
                        severity="warn",
                        message=f"HTTP {status}: unexpected status",
                    )
                )
    except urllib.error.HTTPError as e:
        # urllib raises HTTPError for 4xx/5xx (unlike urlopen for 2xx/3xx)
        status = e.code
        if status in (404, 410):
            issues.append(
                UrlIssue(
                    rule="V-R10-online-stale",
                    severity="error",
                    message=f"HTTP {status}: URL appears stale (not found / gone)",
                )
            )
        elif 500 <= status < 600:
            issues.append(
                UrlIssue(
                    rule="V-R10-online-server-error",
                    severity="warn",
                    message=f"HTTP {status}: server error (transient, retry next run)",
                )
            )
        elif status == 429:
            issues.append(
                UrlIssue(
                    rule="V-R10-online-rate-limit",
                    severity="warn",
                    message="HTTP 429: rate limited (back off)",
                )
            )
        else:
            issues.append(
                UrlIssue(
                    rule="V-R10-online-http-error",
                    severity="warn",
                    message=f"HTTP {status}: {e.reason}",
                )
            )
    except socket.timeout:
        issues.append(
            UrlIssue(
                rule="V-R10-online-timeout",
                severity="warn",
                message=f"connection timeout after {timeout}s",
            )
        )
    except ssl.SSLError as e:
        issues.append(
            UrlIssue(
                rule="V-R10-online-tls",
                severity="error",
                message=f"TLS error: {e}",
            )
        )
    except urllib.error.URLError as e:
        # DNS failure, connection refused, etc.
        issues.append(
            UrlIssue(
                rule="V-R10-online-url-error",
                severity="error",
                message=f"URL error (DNS / connection): {e.reason}",
            )
        )
    except Exception as e:  # noqa: BLE001
        issues.append(
            UrlIssue(
                rule="V-R10-online-unexpected",
                severity="warn",
                message=f"unexpected error: {e}",
            )
        )
    return issues

def _build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="workflow_kit.url_validity",
        description="V-R10 URL validity check (offline 8 + optional online HEAD)",
    )
    p.add_argument("urls", nargs="+", help="URLs to check")
    p.add_argument("--mode", choices=["strict", "loose"], default="strict", help="lint mode (ADR-007)")
    p.add_argument(
        "--online",
        action="store_true",
        help="run online HEAD check (ADR-012, --v-r10-online equivalent). Default: offline only.",
    )
    p.add_argument(
        "--timeout",
        type=float,
        default=10.0,
        help="online HEAD timeout in seconds (default: 10.0)",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_arg_parser().parse_args(argv)
    failed = 0
    for url in args.urls:
        issues = check_url(url)
        if args.online:
            issues.extend(check_url_online(url, timeout=args.timeout))
        if args.mode == "loose":
            issues = [
                UrlIssue(rule=i.rule, severity="warn" if i.severity == "error" else i.severity, message=i.message)
                for i in issues
            ]
        if not issues:
            print(f"  PASS  {url}")
        else:
            for issue in issues:
                print(f"  [{issue.severity.upper()}] {issue.rule} {url}: {issue.message}")
                if issue.severity == "error":
                    failed += 1
    return 1 if failed > 0 else 0


if __name__ == "__main__":
    sys.exit(main())


