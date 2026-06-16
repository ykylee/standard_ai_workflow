"""workflow_kit.phishing_keywords — V-R11 phishing keyword list with external feed support (v0.7.39+).

ADR-017 (V-R11 body audit) 의 phishing keyword detection 의 keyword list source.

Sources (fallback chain, v0.7.39+):
  1. Custom override (function argument)
  2. External feed (PhishTank-style, JSONL file or HTTPS URL)
  3. Bundled baseline (8 keywords, V-R11 v0.7.37+)

Design:
  - Pure functions, no I/O at import time
  - `load_phishing_keywords()` is the main entry point
  - `phishing_feed_update_status()` is for diagnostic
  - External feed is OPTIONAL (default: bundled only)

Usage:
    from workflow_kit.phishing_keywords import load_phishing_keywords, bundled_keywords

    kws = load_phishing_keywords()  # bundled only
    kws = load_phishing_keywords(external_feed=Path("./phishtank-feed.jsonl"))
    kws = load_phishing_keywords(custom=["your custom keyword"])

External feed format (JSONL, one keyword per line):
    {"keyword": "verify your account", "source": "phishtank", "added_at": "2026-06-16"}
    {"keyword": "click here immediately", "source": "openphish", "added_at": "2026-06-15"}
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable


# Bundled baseline (8 keywords, V-R11 v0.7.37+, ADR-017).
# This is the default fallback if no external feed is configured.
BUNDLED_KEYWORDS: tuple[str, ...] = (
    "verify your account",
    "click here immediately",
    "your account will be suspended",
    "urgent action required",
    "confirm your password",
    "wire transfer",
    "lottery winner",
    "nigerian prince",
)


def bundled_keywords() -> tuple[str, ...]:
    """Return the bundled baseline phishing keywords (8 keywords, immutable)."""
    return BUNDLED_KEYWORDS


def _load_external_feed(feed: Path) -> list[str]:
    """Load phishing keywords from an external JSONL file.

    Format: one JSON object per line with at minimum a `keyword` field.
    Other fields (`source`, `added_at`) are ignored.

    Errors (file not found, parse error, etc.) are silently swallowed —
    external feed is OPTIONAL, and the bundled baseline is always available.
    """
    if not feed.exists():
        return []
    out: list[str] = []
    try:
        for line in feed.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                kw = obj.get("keyword")
                if isinstance(kw, str) and kw.strip():
                    out.append(kw.strip())
            except json.JSONDecodeError:
                continue  # skip malformed lines
    except OSError:
        return []
    return out


def load_phishing_keywords(
    external_feed: Path | None = None,
    custom: Iterable[str] | None = None,
) -> tuple[str, ...]:
    """Load phishing keywords from fallback chain (v0.7.39+).

    Order:
      1. custom (user-provided Iterable) — highest priority, deduped first
      2. external_feed (Path to JSONL file) — appended after custom
      3. bundled (BUNDLED_KEYWORDS, 8 baseline) — fallback

    Returns:
        Deduped tuple of keywords (preserving first-occurrence order).
    """
    seen: set[str] = set()
    out: list[str] = []
    for kw in custom or ():
        kw = kw.strip().lower()
        if kw and kw not in seen:
            seen.add(kw)
            out.append(kw)
    for kw in _load_external_feed(external_feed) if external_feed else []:
        kw = kw.strip().lower()
        if kw and kw not in seen:
            seen.add(kw)
            out.append(kw)
    for kw in BUNDLED_KEYWORDS:
        kw = kw.strip().lower()
        if kw and kw not in seen:
            seen.add(kw)
            out.append(kw)
    return tuple(out)


def phishing_feed_update_status(
    external_feed: Path | None = None,
) -> dict[str, object]:
    """Diagnostic: report feed file status without raising.

    Returns dict with:
      - feed_path: str (or None)
      - feed_exists: bool
      - feed_size_bytes: int
      - feed_keyword_count: int
      - bundled_count: int
      - last_modified: float (or None)
    """
    if external_feed is None:
        return {
            "feed_path": None,
            "feed_exists": False,
            "feed_size_bytes": 0,
            "feed_keyword_count": 0,
            "bundled_count": len(BUNDLED_KEYWORDS),
            "last_modified": None,
        }
    exists = external_feed.exists()
    size = external_feed.stat().st_size if exists else 0
    mtime = external_feed.stat().st_mtime if exists else None
    keywords = _load_external_feed(external_feed)
    return {
        "feed_path": str(external_feed),
        "feed_exists": exists,
        "feed_size_bytes": size,
        "feed_keyword_count": len(keywords),
        "bundled_count": len(BUNDLED_KEYWORDS),
        "last_modified": mtime,
    }
