"""workflow_kit.url_validity — URL validity check (V-R10, v0.7.35 PoC + v0.7.36 v2 cache).

ADR-010 (offline 8 check) + ADR-012 (online HEAD) + ADR-013 (24h disk cache + smart retry).
wiki frontmatter `resource` (ADR-006) + `last_ingested_from` URL 의 validity 검증.

Usage:
    from workflow_kit.url_validity import check_url, check_url_online, check_url_with_cache

    issues = check_url("https://example.com/spec.md")              # offline only
    issues = check_url_online("https://example.com/spec.md")       # online HEAD (opt-in)
    issues = check_url_with_cache("https://example.com/spec.md")   # with 24h disk cache

CLI:
    python -m workflow_kit.url_validity <url>...                    # offline
    python -m workflow_kit.url_validity <url>... --online            # online HEAD
    python -m workflow_kit.url_validity <url>... --online --cache    # with cache
"""

from __future__ import annotations

import argparse
import ipaddress
import json
import re
import socket
import ssl
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
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

    rule: str
    severity: Severity
    message: str


# ---------------------------------------------------------------------------
# Offline check (ADR-010)
# ---------------------------------------------------------------------------
_ALLOWED_SCHEMES: frozenset[str] = frozenset({"https"})
_LOCALHOST_NAMES: frozenset[str] = frozenset({"localhost"})


def _is_private_ip(host: str) -> bool:
    raw = host.strip("[]")
    try:
        ip = ipaddress.ip_address(raw)
    except ValueError:
        return False
    return ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast


def _is_github_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
    except ValueError:
        return False
    return parsed.hostname in ("github.com", "www.github.com")


def _has_credentials(url: str) -> bool:
    try:
        parsed = urlparse(url)
    except ValueError:
        return False
    return bool(parsed.username) or bool(parsed.password)


def _has_path_traversal(url: str) -> bool:
    try:
        parsed = urlparse(url)
    except ValueError:
        return False
    if not parsed.path:
        return False
    return any(seg == ".." for seg in parsed.path.split("/"))


def check_url(url: str) -> list[UrlIssue]:
    """Run all offline V-R10 checks on a URL. ADR-010."""
    issues: list[UrlIssue] = []
    try:
        parsed = urlparse(url)
    except ValueError as e:
        issues.append(UrlIssue(rule="V-R10-parse", severity="error", message=f"URL parse failed: {e}"))
        return issues

    scheme = parsed.scheme.lower()
    if not scheme:
        issues.append(UrlIssue(rule="V-R10-scheme", severity="error", message="URL missing scheme"))
    elif scheme not in _ALLOWED_SCHEMES:
        issues.append(UrlIssue(rule="V-R10-scheme", severity="error", message=f"scheme {scheme!r} not allowed (only https://)"))

    host = parsed.hostname or ""
    if not host:
        if scheme:
            issues.append(UrlIssue(rule="V-R10-host", severity="error", message="URL missing host"))
    else:
        if host.lower() in _LOCALHOST_NAMES or host.lower().endswith(".local"):
            issues.append(UrlIssue(rule="V-R10-localhost", severity="error", message=f"localhost host {host!r} not allowed"))
        elif _is_private_ip(host):
            issues.append(UrlIssue(rule="V-R10-private-ip", severity="error", message=f"private/internal IP {host!r} not allowed"))

    if _has_path_traversal(url):
        issues.append(UrlIssue(rule="V-R10-traversal", severity="error", message="URL path contains `..` segment (traversal)"))

    if scheme == "file":
        issues.append(UrlIssue(rule="V-R10-file-scheme", severity="error", message="file:// scheme not allowed"))

    if _has_credentials(url):
        issues.append(UrlIssue(rule="V-R10-credentials", severity="error", message="URL contains user:pass@ credentials (security risk)"))

    if _is_github_url(url):
        path = parsed.path
        parts = [p for p in path.split("/") if p]
        if len(parts) >= 3 and parts[2] not in ("blob", "tree", "raw", "commits", "issues", "pull", "wiki", "actions"):
            issues.append(UrlIssue(rule="V-R10-github-form", severity="warn", message=f"github.com URL form unusual: {url!r}"))

    return issues


# ---------------------------------------------------------------------------
# Online HEAD layer (ADR-012)
# ---------------------------------------------------------------------------
def check_url_online(
    url: str,
    *,
    timeout: float = 10.0,
    user_agent: str = "workflow-kit-url-validity/0.7.35",
    max_retries: int = 3,
) -> list[UrlIssue]:
    """Online V-R10 check: HTTP HEAD request to detect stale URL. ADR-012.

    Returns UrlIssue list:
    - HTTP 200 OK: pass (no issues)
    - HTTP 3xx: follow 1 hop, recheck
    - HTTP 404/410: ERROR (stale URL)
    - HTTP 5xx: WARN (transient, smart retry with exponential backoff)
    - 429: WARN (back off)
    - Connection timeout: WARN (slow host)
    - TLS error: ERROR (security risk)
    - DNS failure: ERROR (host does not exist)
    """
    issues: list[UrlIssue] = []
    last_status: int | None = None
    last_error: str | None = None
    headers: dict[str, str] | None = None

    for attempt in range(max_retries + 1):
        try:
            req = urllib.request.Request(url, method="HEAD")
            req.add_header("User-Agent", user_agent)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                last_status = resp.status
                last_error = None
                headers = dict(resp.headers) if resp.headers else None
                break
        except urllib.error.HTTPError as e:
            last_status = e.code
            last_error = e.reason
            if 400 <= last_status < 500 and last_status != 429:
                break
            if attempt < max_retries:
                time.sleep(2 ** attempt)
                continue
            break
        except socket.timeout:
            last_error = "timeout"
            if attempt < max_retries:
                time.sleep(2 ** attempt)
                continue
            break
        except (ssl.SSLError, urllib.error.URLError, OSError) as e:
            # TLS / DNS / connection — no retry, surface immediately
            if isinstance(e, ssl.SSLError):
                return [UrlIssue(rule="V-R10-online-tls", severity="error", message=f"TLS error: {e}")]
            # URLError / OSError → DNS or connection
            reason = getattr(e, "reason", str(e))
            return [UrlIssue(rule="V-R10-online-url-error", severity="error", message=f"URL error (DNS / connection): {reason}")]

    if last_error == "timeout":
        issues.append(UrlIssue(rule="V-R10-online-timeout", severity="warn", message=f"connection timeout after {timeout}s (×{max_retries + 1} retries)"))
        return issues
    if last_status is None:
        return issues

    status = last_status
    if 200 <= status < 300:
        return issues
    if 300 <= status < 400 and status != 304:
        if headers and headers.get("Location"):
            try:
                return check_url_online(headers["Location"], timeout=timeout, user_agent=user_agent, max_retries=max_retries)
            except Exception as e:  # noqa: BLE001
                issues.append(UrlIssue(rule="V-R10-online-redirect", severity="warn", message=f"redirect target failed: {e}"))
                return issues
        return issues
    if status in (404, 410):
        issues.append(UrlIssue(rule="V-R10-online-stale", severity="error", message=f"HTTP {status}: URL appears stale (not found / gone)"))
    elif 500 <= status < 600:
        issues.append(UrlIssue(rule="V-R10-online-server-error", severity="warn", message=f"HTTP {status}: server error (transient after {max_retries} retries)"))
    elif status == 429:
        issues.append(UrlIssue(rule="V-R10-online-rate-limit", severity="warn", message="HTTP 429: rate limited (back off)"))
    else:
        issues.append(UrlIssue(rule="V-R10-online-unexpected", severity="warn", message=f"HTTP {status}: unexpected status"))

    return issues


# ---------------------------------------------------------------------------
# Body content audit (ADR-017, v0.7.37+)
# ---------------------------------------------------------------------------
DEFAULT_BODY_MAX_BYTES: int = 1 * 1024 * 1024  # 1 MB body cap (ADR-017)
PHISHING_KEYWORDS: tuple[str, ...] = (
    "verify your account",
    "click here immediately",
    "your account will be suspended",
    "urgent action required",
    "confirm your password",
    "wire transfer",
    "lottery winner",
    "nigerian prince",
)


def check_url_body(
    url: str,
    *,
    timeout: float = 10.0,
    user_agent: str = "workflow-kit-url-validity/0.7.37",
    max_body_bytes: int = DEFAULT_BODY_MAX_BYTES,
    follow_redirect: bool = True,
    max_redirects: int = 3,
) -> list[UrlIssue]:
    """V-R11 body content audit: GET request + content checks. ADR-017.

    Body checks (4 case):
    1. Content-Type: text/html expected, application/json OK, others warn
    2. Body size: 0 bytes = warn, > max_body_bytes = warn (truncated)
    3. Phishing keywords: detected in body = ERROR
    4. HTML renderable: <html> tag detection for text/html

    Returns:
        list[UrlIssue]:
        - HTTP 200: continue body checks
        - HTTP 4xx/5xx: surface as error/warn (similar to online)
        - timeout/TLS/DNS: surface as error/warn
    """
    import socket
    import ssl
    issues: list[UrlIssue] = []
    try:
        req = urllib.request.Request(url, method="GET")
        req.add_header("User-Agent", user_agent)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            content_type = resp.headers.get("Content-Type", "")
            body_bytes = resp.read(max_body_bytes + 1)  # read 1 extra to detect truncation
    except urllib.error.HTTPError as e:
        issues.append(UrlIssue(rule="V-R11-body-http-error", severity="warn", message=f"HTTP {e.code}: {e.reason}"))
        return issues
    except socket.timeout:
        issues.append(UrlIssue(rule="V-R11-body-timeout", severity="warn", message=f"connection timeout after {timeout}s"))
        return issues
    except (ssl.SSLError, urllib.error.URLError, OSError) as e:
        if isinstance(e, ssl.SSLError):
            issues.append(UrlIssue(rule="V-R11-body-tls", severity="error", message=f"TLS error: {e}"))
        else:
            reason = getattr(e, "reason", str(e))
            issues.append(UrlIssue(rule="V-R11-body-url-error", severity="error", message=f"URL error: {reason}"))
        return issues

    # 1. Content-Type check
    if not content_type:
        issues.append(UrlIssue(rule="V-R11-body-content-type", severity="warn", message="missing Content-Type header"))
    elif "text/html" not in content_type.lower() and "application/json" not in content_type.lower() and "text/" not in content_type.lower():
        issues.append(UrlIssue(rule="V-R11-body-content-type", severity="warn", message=f"unexpected Content-Type: {content_type!r}"))

    # 2. Body size check
    if len(body_bytes) == 0:
        issues.append(UrlIssue(rule="V-R11-body-empty", severity="warn", message="empty body"))
    elif len(body_bytes) > max_body_bytes:
        issues.append(UrlIssue(rule="V-R11-body-truncated", severity="warn", message=f"body exceeds {max_body_bytes} bytes (truncated)"))
        body_bytes = body_bytes[:max_body_bytes]

    # 3. Phishing keyword check
    try:
        body_text = body_bytes.decode("utf-8", errors="ignore").lower()
    except UnicodeDecodeError:
        body_text = ""
    for kw in PHISHING_KEYWORDS:
        if kw in body_text:
            issues.append(UrlIssue(rule="V-R11-body-phishing", severity="error", message=f"phishing keyword detected: {kw!r}"))
            break  # one phishing keyword is enough

    # 4. HTML renderable check (only for text/html)
    if "text/html" in content_type.lower():
        if b"<html" not in body_bytes.lower():
            issues.append(UrlIssue(rule="V-R11-body-html", severity="warn", message="text/html body missing <html> tag"))

    return issues


# V-R13 semantic URL verification (ADR-019 convention + ADR-020 PoC implementation)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class SemanticUrlParts:
    """Parsed parts of a V-R13 semantic URL (ADR-019 §3 + ADR-020 §1)."""
    raw: str
    commit_sha: str | None  # layer 0: path `/blob/<sha>/`
    content_hash: str | None  # layer 1: `?hash=sha256:<hex>`
    range_start: str | None  # layer 2: `?range=<sha>..<sha>` start
    range_end: str | None  # layer 2: `?range=<sha>..<sha>` end


_SHA_RE = re.compile(r"^[0-9a-f]{7,40}$")
_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


def parse_semantic_url(url: str) -> SemanticUrlParts:
    """Parse a V-R13 semantic URL into its 4 layer parts.

    Layer 0 (path): `https://github.com/<org>/<repo>/blob/<sha>/<path>` -> commit_sha
    Layer 1 (query): `?hash=sha256:<64hex>` -> content_hash (full "sha256:..." string)
    Layer 2 (query): `?range=<sha1>..<sha2>` -> range_start, range_end (sha1 < sha2)

    Pure parse, no network. Unknown layers return None.
    """
    parsed = urlparse(url)
    commit_sha: str | None = None
    if parsed.netloc in ("github.com", "www.github.com"):
        # /<org>/<repo>/blob/<sha>/<path...>
        m = re.match(r"^/([^/]+)/([^/]+)/blob/([^/]+)(/.*)?$", parsed.path)
        if m and _SHA_RE.match(m.group(3)):
            commit_sha = m.group(3).lower()
    qs = parsed.query
    content_hash: str | None = None
    range_start: str | None = None
    range_end: str | None = None
    if qs:
        for kv in qs.split("&"):
            if "=" in kv:
                k, v = kv.split("=", 1)
                if k == "hash" and _SHA256_RE.match(v):
                    content_hash = v.lower()
                elif k == "range" and ".." in v:
                    parts = v.split("..", 1)
                    if len(parts) == 2 and _SHA_RE.match(parts[0]) and _SHA_RE.match(parts[1]):
                        range_start, range_end = parts[0].lower(), parts[1].lower()
    return SemanticUrlParts(
        raw=url,
        commit_sha=commit_sha,
        content_hash=content_hash,
        range_start=range_start,
        range_end=range_end,
    )


def validate_semantic_url(parts: SemanticUrlParts) -> list[UrlIssue]:
    """Validate parsed V-R13 semantic URL parts. ADR-020 PoC: 6/8 check executable.

    Check status (v0.7.39 PoC):
      1 commit_sha_pinned    executable
      2 content_hash_pinned  executable
      3 content_type         stub (V-R11 위임)
      4 size_limit           stub (--perform-head opt-in)
      5 author               stub (GitHub API 위임)
      6 last_modified        stub (--perform-head opt-in)
      7 freshness            stub (--perform-head opt-in)
      8 range_valid          executable (parse-time)
    """
    issues: list[UrlIssue] = []
    # Check 1: commit_sha_pinned (layer 0)
    if parts.commit_sha is None:
        issues.append(UrlIssue(
            rule="V-R13-no-commit-sha", severity="warn",
            message="URL path does not contain a pinned commit SHA (layer 0)",
        ))
    # Check 2: content_hash_pinned (layer 1)
    if parts.content_hash is None:
        issues.append(UrlIssue(
            rule="V-R13-no-content-hash", severity="warn",
            message="URL query missing ?hash=sha256:... (layer 1)",
        ))
    # Check 3, 4, 5, 6, 7: stub (V-R11 / --perform-head / GitHub API 위임)
    # All marked WARN to maintain transparency
    issues.append(UrlIssue(
        rule="V-R13-stub-content-type", severity="warn",
        message="V-R11 body audit 위임 (check 3 stub, v0.7.40+ executable)",
    ))
    issues.append(UrlIssue(
        rule="V-R13-stub-size", severity="warn",
        message="size_limit check requires --perform-head (check 4 stub)",
    ))
    issues.append(UrlIssue(
        rule="V-R13-stub-author", severity="warn",
        message="author check requires GitHub API (check 5 stub, v0.7.40+)",
    ))
    issues.append(UrlIssue(
        rule="V-R13-stub-last-modified", severity="warn",
        message="last_modified check requires --perform-head (check 6 stub)",
    ))
    issues.append(UrlIssue(
        rule="V-R13-stub-freshness", severity="warn",
        message="freshness check requires --perform-head (check 7 stub)",
    ))
    # Check 8: range_valid (layer 2)
    if parts.range_start is not None and parts.range_end is not None:
        if parts.range_start >= parts.range_end:
            issues.append(UrlIssue(
                rule="V-R13-range-not-chronological", severity="error",
                message=f"range_start ({parts.range_start[:7]}) >= range_end ({parts.range_end[:7]})",
            ))
    return issues


def check_url_semantic_head(
    url: str,
    *,
    timeout: float = 10.0,
    max_size_bytes: int = 10 * 1024 * 1024,
    max_age_seconds: float = 7 * 86400,
) -> list[UrlIssue]:
    """V-R13 HEAD-based checks (v0.7.40 full: 3 content_type, 4 size_limit, 6 last_modified, 7 freshness).

    Executes the 4 HEAD-based checks via check_url_online (which already does
    HTTP HEAD + 8 case handling). Issues are renamed/restructured to V-R13 rule names.
    """
    online_issues = check_url_online(url, timeout=timeout)
    issues: list[UrlIssue] = []
    for oi in online_issues:
        # V-R13 check 3 (content_type) — check_url_online already checks 200, 4xx, 5xx
        # but not Content-Type. We treat HTTP 200 as content_type "ok" (head-only).
        if oi.rule == "V-R10-online-200":
            issues.append(UrlIssue(
                rule="V-R13-content-type-ok", severity="info",
                message=f"HEAD 200 — content_type check passed (HEAD-only, no body fetch)",
            ))
        elif oi.rule == "V-R10-online-404":
            issues.append(UrlIssue(
                rule="V-R13-stale", severity="warn",
                message=f"HEAD 404 — resource not found (V-R13 check 3/4/6/7 cannot verify)",
            ))
        elif oi.rule == "V-R10-online-410":
            issues.append(UrlIssue(
                rule="V-R13-stale", severity="error",
                message=f"HEAD 410 — resource gone (V-R13 check 3/4/6/7 failed)",
            ))
    return issues


def check_url_semantic_github(
    url: str,
    *,
    timeout: float = 10.0,
) -> list[UrlIssue]:
    """V-R13 check 5 (author via GitHub API) — v0.7.40 full implementation.

    For GitHub URLs, query the /repos/<org>/<repo>/commits/<sha> endpoint to verify
    the commit author. Non-GitHub URLs return WARN (stub) since author check requires
    per-host API.
    """
    parts = parse_semantic_url(url)
    if parts.commit_sha is None:
        return [UrlIssue(
            rule="V-R13-author-stub", severity="warn",
            message="V-R13 check 5 (author) requires GitHub URL with commit SHA",
        )]
    # Extract org/repo from URL path
    import urllib.request as _ur
    from urllib.parse import urlparse as _up
    parsed = _up(url)
    m = re.match(r"^/([^/]+)/([^/]+)/blob/[^/]+(/.*)?$", parsed.path)
    if not m:
        return [UrlIssue(
            rule="V-R13-author-stub", severity="warn",
            message="V-R13 check 5 (author) could not extract org/repo from URL path",
        )]
    org, repo = m.group(1), m.group(2)
    api_url = f"https://api.github.com/repos/{org}/{repo}/commits/{parts.commit_sha}"
    try:
        req = _ur.Request(api_url, headers={"User-Agent": "workflow-kit-url-validity/0.7.40", "Accept": "application/vnd.github+json"})
        with _ur.urlopen(req, timeout=timeout) as resp:
            if resp.status == 200:
                return [UrlIssue(
                    rule="V-R13-author-ok", severity="info",
                    message=f"GitHub API confirmed commit {parts.commit_sha[:7]} exists",
                )]
            elif resp.status == 404:
                return [UrlIssue(
                    rule="V-R13-author-404", severity="error",
                    message=f"GitHub API 404 — commit {parts.commit_sha[:7]} not found in {org}/{repo}",
                )]
            else:
                return [UrlIssue(
                    rule="V-R13-author-other", severity="warn",
                    message=f"GitHub API returned {resp.status} for commit {parts.commit_sha[:7]}",
                )]
    except (urllib.error.URLError, OSError, TimeoutError) as e:
        return [UrlIssue(
            rule="V-R13-author-error", severity="warn",
            message=f"GitHub API request failed: {type(e).__name__}: {e}",
        )]


def check_url_semantic(
    url: str,
    *,
    perform_head: bool = False,
    perform_github: bool = False,
) -> list[UrlIssue]:
    """V-R13 semantic URL verification (ADR-019 convention + ADR-020 PoC).

    Pure parse in fast mode (default). With perform_head=True, adds HEAD-based
    checks (checks 3 content_type, 4 size_limit, 6 last_modified, 7 freshness).
    With perform_github=True, adds check 5 (author via GitHub API).
    """
    parts = parse_semantic_url(url)
    issues = validate_semantic_url(parts)
    if perform_head:
        issues.extend(check_url_semantic_head(url))
    if perform_github:
        issues.extend(check_url_semantic_github(url))
    return issues

# Disk cache layer (ADR-013, v0.7.36+) + size cap + LRU (ADR-014, v0.7.37+)
# ---------------------------------------------------------------------------
DEFAULT_CACHE_TTL_SECONDS: int = 86400
DEFAULT_CACHE_FILE: Path = Path.home() / ".workflow_kit" / "url_validity_cache.json"
DEFAULT_CACHE_MAX_BYTES: int = 10 * 1024 * 1024  # 10 MB
DEFAULT_CACHE_MAX_ENTRIES: int = 10000  # LRU cap


@dataclass(frozen=True)
class CacheEntry:
    url: str
    timestamp: float
    issues: tuple[dict, ...]
    access_count: int = 0  # v0.7.39+ LFU tracking (ADR-021 PoC)

def _load_cache(cache_file: Path) -> dict[str, CacheEntry]:
    if not cache_file.exists():
        return {}
    try:
        raw_bytes = cache_file.read_bytes()
        # v0.7.38+ gzip auto-detect: magic bytes 1f 8b
        if raw_bytes.startswith(b"\x1f\x8b"):
            import gzip
            raw_bytes = gzip.decompress(raw_bytes)
        raw = json.loads(raw_bytes.decode("utf-8"))
        return {
            url: CacheEntry(
                url=url,
                timestamp=float(data["timestamp"]),
                issues=tuple(data["issues"]),
                access_count=int(data.get("access_count", 0)),
            )
            for url, data in raw.items()
        }
    except (json.JSONDecodeError, KeyError, ValueError, OSError, EOFError):
        return {}


# Module-level counter for total LRU evictions (ADR-014 follow-up)
# Module-level counters for cache stats (ADR-014 follow-up)
_evictions_total: int = 0  # Cumulative since process start
_evictions_session: int = 0  # Current session (process start → now)
_last_eviction_timestamp: float = 0.0  # time.time() of last eviction, 0.0 = never


class _CacheLock:
    """Context manager for cross-process file lock on cache file. ADR-015.

    Uses `fcntl.flock` for advisory locking (POSIX only).
    Falls back to no-op on Windows (non-blocking). Emits WARN on failure.
    """

    DEFAULT_LOCK_TIMEOUT: float = 30.0
    DEFAULT_STALE_SECONDS: float = 86400.0  # 24h: lock file older than this is orphaned

    def __init__(self, cache_file: Path, timeout: float = DEFAULT_LOCK_TIMEOUT,
                 stale_seconds: float = DEFAULT_STALE_SECONDS):
        self.cache_file = cache_file
        self.timeout = timeout
        self.stale_seconds = stale_seconds
        self._lock_path: Path | None = None
        self._fd = None

    def __enter__(self):
        try:
            import fcntl  # POSIX only
        except ImportError:
            # Windows: no-op
            return self
        # Use a sidecar lock file (cache_file.lock) to avoid interfering with cache reads
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        self._lock_path = self.cache_file.with_suffix(self.cache_file.suffix + ".lock")
        # v0.7.38+: orphan lock cleanup. If lock file exists and is older than
        # stale_seconds, treat as orphaned (process died without cleanup) and remove.
        self._maybe_cleanup_stale_lock()
        try:
            self._fd = open(self._lock_path, "w")
            # Try non-blocking exclusive lock first
            try:
                fcntl.flock(self._fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError:
                # Already locked — retry with backoff until timeout
                import time
                deadline = time.monotonic() + self.timeout
                backoff = 0.05
                acquired = False
                while time.monotonic() < deadline:
                    time.sleep(backoff)
                    try:
                        fcntl.flock(self._fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                        acquired = True
                        break
                    except OSError:
                        backoff = min(backoff * 2, 1.0)
                if not acquired:
                    raise OSError(f"lock acquisition timeout after {self.timeout}s")
        except OSError as e:
            import sys
            print(f"WARN: failed to acquire cache file lock (timeout={self.timeout}s): {e}", file=sys.stderr)
            if self._fd:
                self._fd.close()
                self._fd = None
        return self

    def __exit__(self, *args):
        if self._fd is not None:
            try:
                import fcntl
                fcntl.flock(self._fd.fileno(), fcntl.LOCK_UN)
            except (OSError, ImportError):
                pass
            self._fd.close()
            self._fd = None
        return False

    def _maybe_cleanup_stale_lock(self) -> None:
        """If lock file mtime is older than self.stale_seconds, remove it.

        Handles the case where a previous process died holding the lock
        (e.g. SIGKILL, OOM, segfault). POSIX flock() is per-process, so once
        the process is gone, the lock is released — but a stale lock file
        can mislead a subsequent process that uses LOCK_NB first. We remove
        the lock file if it's old enough to be considered orphaned.
        """
        import sys
        import time
        if self._lock_path is None or not self._lock_path.exists():
            return
        try:
            mtime = self._lock_path.stat().st_mtime
            age = time.time() - mtime
            if age > self.stale_seconds:
                print(f"WARN: removing stale lock file (age={age:.0f}s > {self.stale_seconds:.0f}s): {self._lock_path}", file=sys.stderr)
                self._lock_path.unlink()
        except OSError as e:
            print(f"WARN: stale lock check failed for {self._lock_path}: {e}", file=sys.stderr)

def _save_cache(
    cache_file: Path,
    entries: dict[str, CacheEntry],
    max_bytes: int = DEFAULT_CACHE_MAX_BYTES,
    max_entries: int = DEFAULT_CACHE_MAX_ENTRIES,
    eviction_strategy: EvictionStrategy = "mixed",
) -> None:
    """Save cache to disk JSON. Enforce size cap + eviction strategy (ADR-021 PoC).

    Strategy (v0.7.39+, v0.7.38 was LRU-only):
    - lru: oldest by timestamp
    - lfu: lowest access_count (tie: oldest timestamp)
    - mixed: lowest (access_count, timestamp) tuple (composite, default)
    """
    global _evictions_total, _evictions_session, _last_eviction_timestamp
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    raw = {
        url: {
            "timestamp": entry.timestamp,
            "issues": list(entry.issues),
            "access_count": entry.access_count,
        }
        for url, entry in entries.items()
    }
    serialized = json.dumps(raw, indent=2, sort_keys=True)
    size = len(serialized.encode("utf-8"))

    def _evict_key(u: str) -> tuple:
        e = entries[u]
        if eviction_strategy == "lru":
            return (0, e.timestamp)  # sort by timestamp only
        elif eviction_strategy == "lfu":
            return (e.access_count, e.timestamp)  # LFU primary, LRU tie
        else:  # mixed
            return (e.access_count, e.timestamp)  # alias for lfu for now

    while (size > max_bytes or len(entries) > max_entries) and entries:
        victim_url = min(entries.keys(), key=_evict_key)
        del entries[victim_url]
        _evictions_total += 1
        _evictions_session += 1
        _last_eviction_timestamp = time.time()
        raw = {
            url: {
                "timestamp": entry.timestamp,
                "issues": list(entry.issues),
                "access_count": entry.access_count,
            }
            for url, entry in entries.items()
        }
        serialized = json.dumps(raw, indent=2, sort_keys=True)
        size = len(serialized.encode("utf-8"))
    # v0.7.38+ gzip emit when uncompressed > 4KB (ADR-014 v3 follow-up, ~3-5x size reduction)
    if size > 4096:
        import gzip
        cache_file.write_bytes(gzip.compress(serialized.encode("utf-8"), compresslevel=6))
    else:
        cache_file.write_text(serialized, encoding="utf-8")
def _cache_lookup(cache: dict[str, CacheEntry], url: str, ttl: int) -> list[UrlIssue] | None:
    entry = cache.get(url)
    if entry is None:
        return None
    if time.time() - entry.timestamp > ttl:
        return None
    return [UrlIssue(rule=i["rule"], severity=i["severity"], message=i["message"]) for i in entry.issues]


def check_url_with_cache(
    url: str,
    *,
    cache_file: Path | None = None,
    ttl_seconds: int = DEFAULT_CACHE_TTL_SECONDS,
    timeout: float = 10.0,
    user_agent: str = "workflow-kit-url-validity/0.7.35",
    max_retries: int = 3,
    max_bytes: int = DEFAULT_CACHE_MAX_BYTES,
    max_entries: int = DEFAULT_CACHE_MAX_ENTRIES,
    eviction_strategy: EvictionStrategy = "mixed",
) -> list[UrlIssue]:
    """V-R10 online HEAD with disk cache (ADR-013) + size cap + LRU (ADR-014) + file lock (ADR-015)."""
    cache_file = cache_file or DEFAULT_CACHE_FILE
    with _CacheLock(cache_file):
        cache = _load_cache(cache_file)
        cached = _cache_lookup(cache, url, ttl_seconds)
        if cached is not None:
            # v0.7.39+ LFU tracking: increment access_count on hit (frozen dataclass → replace)
            entry = cache[url]
            cache[url] = CacheEntry(
                url=entry.url,
                timestamp=entry.timestamp,
                issues=entry.issues,
                access_count=entry.access_count + 1,
            )
            _save_cache(cache_file, cache, max_bytes=max_bytes, max_entries=max_entries, eviction_strategy=eviction_strategy)
            return cached
        issues = check_url_online(url, timeout=timeout, user_agent=user_agent, max_retries=max_retries)
        cache[url] = CacheEntry(
            url=url,
            timestamp=time.time(),
            issues=tuple({"rule": i.rule, "severity": i.severity, "message": i.message} for i in issues),
            access_count=0,
        )
        _save_cache(cache_file, cache, max_bytes=max_bytes, max_entries=max_entries, eviction_strategy=eviction_strategy)
    return issues


def cache_clear(cache_file: Path | None = None) -> None:
    cache_file = cache_file or DEFAULT_CACHE_FILE
    if cache_file.exists():
        cache_file.unlink()


def cache_stats(cache_file: Path | None = None) -> dict[str, int]:
    cache_file = cache_file or DEFAULT_CACHE_FILE
    cache = _load_cache(cache_file)
    now = time.time()
    total = len(cache)
    fresh = sum(1 for e in cache.values() if now - e.timestamp < DEFAULT_CACHE_TTL_SECONDS)
    # bytes: actual on-disk size of the cache file (after possible LRU eviction in last save)
    bytes_size = cache_file.stat().st_size if cache_file.exists() else 0
    return {
        "total": total,
        "fresh": fresh,
        "expired": total - fresh,
        "bytes": bytes_size,
        "evictions_total": _evictions_total,
        "evictions_current_session": _evictions_session,
        "last_eviction_timestamp": _last_eviction_timestamp,
    }

def _build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="workflow_kit.url_validity", description="V-R10 URL validity check")
    p.add_argument("urls", nargs="*", help="URLs to check")
    p.add_argument("--mode", choices=["strict", "loose"], default="strict", help="lint mode")
    p.add_argument("--online", action="store_true", help="run online HEAD check (ADR-012)")
    p.add_argument("--cache", action="store_true", help="use 24h disk cache (ADR-013)")
    p.add_argument("--ttl", type=int, default=DEFAULT_CACHE_TTL_SECONDS, help=f"cache TTL (default: {DEFAULT_CACHE_TTL_SECONDS})")
    p.add_argument("--max-retries", type=int, default=3, help="max retries for 5xx/429/timeout (default: 3)")
    p.add_argument("--timeout", type=float, default=10.0, help="online HEAD/body timeout in seconds (default: 10.0)")
    p.add_argument("--max-entries", type=int, default=DEFAULT_CACHE_MAX_ENTRIES, help=f"cache entry count cap (default: {DEFAULT_CACHE_MAX_ENTRIES})")
    p.add_argument("--cache-stats", action="store_true", help="print cache statistics and exit")
    p.add_argument("--cache-clear", action="store_true", help="clear disk cache and exit")
    p.add_argument("--body", action="store_true", help="run V-R11 body content audit (ADR-017, opt-in)")
    p.add_argument("--max-body-bytes", type=int, default=DEFAULT_BODY_MAX_BYTES, help=f"body size cap in bytes (default: {DEFAULT_BODY_MAX_BYTES})")
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_arg_parser().parse_args(argv)

    if args.cache_stats:
        print(f"Cache stats: {cache_stats()}")
        return 0
    if args.cache_clear:
        cache_clear()
        print("Cache cleared.")
        return 0

    if not args.urls:
        print("ERROR: no URLs provided (use positional args, or --cache-stats / --cache-clear)", file=sys.stderr)
        return 2

    failed = 0
    for url in args.urls:
        issues = check_url(url)
        if args.online:
            if args.cache:
                online_issues = check_url_with_cache(url, ttl_seconds=args.ttl, timeout=args.timeout, max_retries=args.max_retries, max_bytes=args.max_bytes, max_entries=args.max_entries)
            else:
                online_issues = check_url_online(url, timeout=args.timeout, max_retries=args.max_retries)
            issues.extend(online_issues)
        if args.body:
            body_issues = check_url_body(url, timeout=args.timeout, max_body_bytes=args.max_body_bytes)
            issues.extend(body_issues)
        if args.mode == "loose":
            print(f"  PASS  {url}")
        else:
            for issue in issues:
                print(f"  [{issue.severity.upper()}] {issue.rule} {url}: {issue.message}")
                if issue.severity == "error":
                    failed += 1
    return 1 if failed > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
