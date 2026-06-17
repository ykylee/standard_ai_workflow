"""workflow_kit.phishing_keywords test (v0.7.60, 5 module audit 4차).

V-R11 phishing keyword list + ADR-023 federated feed (PhishTank + OpenPhish) coverage.

Test list (8):
1-2.  bundled_keywords + load_phishing_keywords fallback chain
3-4.  external feed (JSONL) load + dedup
5-6.  phishing_feed_update_status (file present / missing)
7-8.  fetch_phishtank / fetch_openphish empty-on-error (offline-safe)
"""
from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[1]
PHISHING_KEYWORDS = SOURCE_ROOT / "workflow_kit" / "phishing_keywords.py"


def _import_phishing_keywords():
    spec = importlib.util.spec_from_file_location(
        "workflow_kit.phishing_keywords", str(PHISHING_KEYWORDS)
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["workflow_kit.phishing_keywords"] = mod
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# Test 1-2: bundled + load
# ---------------------------------------------------------------------------
def test_bundled_keywords_v0_7_60() -> None:
    """bundled_keywords returns 8 baseline keywords (V-R11 v0.7.37+, ADR-017) (v0.7.60+)."""
    mod = _import_phishing_keywords()
    keywords = mod.bundled_keywords()
    assert isinstance(keywords, tuple)
    assert len(keywords) == 8
    # All lowercase, non-empty
    for kw in keywords:
        assert isinstance(kw, str)
        assert kw == kw.lower()
        assert kw.strip() == kw
    # BUNDLED_KEYWORDS constant is the same tuple
    assert mod.BUNDLED_KEYWORDS == keywords


def test_load_phishing_keywords_no_args_v0_7_60() -> None:
    """load_phishing_keywords() with no args returns bundled (v0.7.60+)."""
    mod = _import_phishing_keywords()
    keywords = mod.load_phishing_keywords()
    assert keywords == mod.bundled_keywords()
    # Custom iterable
    custom_kws = mod.load_phishing_keywords(custom=["Phish123", "phish123", "  valid  "])
    assert "phish123" in custom_kws
    assert "valid" in custom_kws
    # Bundled still present (fallback)
    for bundled_kw in mod.bundled_keywords():
        assert bundled_kw in custom_kws


# ---------------------------------------------------------------------------
# Test 3-4: external feed (JSONL) + dedup
# ---------------------------------------------------------------------------
def test_load_external_feed_jsonl_v0_7_60() -> None:
    """_load_external_feed reads JSONL with `keyword` field (v0.7.60+)."""
    mod = _import_phishing_keywords()
    with tempfile.TemporaryDirectory() as tmp:
        feed_path = Path(tmp) / "feed.jsonl"
        # 3 entries: 2 valid, 1 missing keyword
        feed_path.write_text(
            json.dumps({"keyword": "ScamA"}) + "\n"
            + json.dumps({"keyword": "scama", "extra": "ignored"}) + "\n"  # dup (case-insensitive)
            + json.dumps({"other": "field"}) + "\n"  # missing keyword
            + json.dumps({"keyword": "ScamB"}) + "\n",
            encoding="utf-8",
        )
        result = mod._load_external_feed(feed_path)
        assert "scama" in result
        assert "scamb" in result
        # missing keyword field is silently skipped
        assert len([k for k in result if k not in mod.bundled_keywords()]) == 2


def test_load_phishing_keywords_with_external_dedup_v0_7_60() -> None:
    """load_phishing_keywords dedupes custom + external + bundled (v0.7.60+)."""
    mod = _import_phishing_keywords()
    with tempfile.TemporaryDirectory() as tmp:
        feed_path = Path(tmp) / "ext.jsonl"
        feed_path.write_text(
            json.dumps({"keyword": "CustomExt1"}) + "\n"
            + json.dumps({"keyword": "bundled_keyword_1"}) + "\n",  # collides with bundled
            encoding="utf-8",
        )
        keywords = mod.load_phishing_keywords(
            external_feed=feed_path, custom=["CustomInCode1", "customext1"]
        )
        # custom > external > bundled order, but deduped (first occurrence)
        assert "customincode1" in keywords
        assert "customext1" in keywords
        assert "customext1" in keywords
        # bundled_keyword_1 is from external, comes after custom, but before bundled
        ext_idx = keywords.index("customext1")
        assert "customincode1" in keywords[:ext_idx + 1]


# ---------------------------------------------------------------------------
# Test 5-6: phishing_feed_update_status
# ---------------------------------------------------------------------------
def test_feed_status_no_path_v0_7_60() -> None:
    """phishing_feed_update_status(None) returns bundled-only diagnostic (v0.7.60+)."""
    mod = _import_phishing_keywords()
    status = mod.phishing_feed_update_status()
    assert status["feed_path"] is None
    assert status["feed_exists"] is False
    assert status["feed_size_bytes"] == 0
    assert status["feed_keyword_count"] == 0
    assert status["bundled_count"] == 8
    assert status["last_modified"] is None


def test_feed_status_with_file_v0_7_60() -> None:
    """phishing_feed_update_status with existing JSONL file reports size + count (v0.7.60+)."""
    mod = _import_phishing_keywords()
    with tempfile.TemporaryDirectory() as tmp:
        feed_path = Path(tmp) / "feed.jsonl"
        feed_path.write_text(
            json.dumps({"keyword": "K1"}) + "\n"
            + json.dumps({"keyword": "K2"}) + "\n",
            encoding="utf-8",
        )
        status = mod.phishing_feed_update_status(feed_path)
        assert status["feed_path"] == str(feed_path)
        assert status["feed_exists"] is True
        assert status["feed_size_bytes"] > 0
        assert status["feed_keyword_count"] == 2
        assert status["bundled_count"] == 8
        assert status["last_modified"] is not None


# ---------------------------------------------------------------------------
# Test 7-8: fetch functions (offline-safe, no network)
# ---------------------------------------------------------------------------
def test_fetch_phishtank_empty_on_error_v0_7_60() -> None:
    """fetch_phishtank_feed returns [] on network error (offline-safe, no exception) (v0.7.60+)."""
    mod = _import_phishing_keywords()
    # Use a clearly invalid API key + unreachable scenario. Should return [] without raising.
    result = mod.fetch_phishtank_feed(api_key="invalid_key_for_test")
    assert isinstance(result, list)
    # Network unavailable in test env → empty list
    assert result == []


def test_fetch_openphish_empty_on_error_v0_7_60() -> None:
    """fetch_openphish_feed returns [] on network error (offline-safe) (v0.7.60+).

    v0.8.11 fix: original test assumed offline test env. CI/dev may have network
    (returns 300+ real URLs). Mock `requests_get` to raise OSError → function
    returns []. Verifies the offline-safe fallback chain, not "no network available".
    """
    mod = _import_phishing_keywords()

    def _failing_requests_get(url: str, **kwargs: object) -> object:
        raise OSError("simulated network error for offline test")

    result = mod.fetch_openphish_feed(requests_get=_failing_requests_get)
    assert isinstance(result, list)
    assert result == []


def main() -> int:
    test_funcs = [
        test_bundled_keywords_v0_7_60,
        test_load_phishing_keywords_no_args_v0_7_60,
        test_load_external_feed_jsonl_v0_7_60,
        test_load_phishing_keywords_with_external_dedup_v0_7_60,
        test_feed_status_no_path_v0_7_60,
        test_feed_status_with_file_v0_7_60,
        test_fetch_phishtank_empty_on_error_v0_7_60,
        test_fetch_openphish_empty_on_error_v0_7_60,
    ]
    failed: list[str] = []
    for fn in test_funcs:
        name = fn.__name__
        try:
            fn()
            print(f"  PASS  {name}")
        except Exception as e:
            print(f"  FAIL  {name}: {type(e).__name__}: {e}")
            failed.append(name)
    print(f"\n{len(test_funcs) - len(failed)}/{len(test_funcs)} tests passed.")
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
