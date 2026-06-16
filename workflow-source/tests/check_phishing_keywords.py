"""workflow_kit.phishing_keywords module test (v0.7.39+, V-R11 v2 PoC).

Test list:
1. test_bundled_returns_8_keywords: bundled baseline has 8 keywords
2. test_load_default_returns_bundled: load_phishing_keywords() (no args) = bundled
3. test_load_custom_overrides_and_dedups: custom list takes priority, dedup against bundled
4. test_load_external_feed_appended: external feed (JSONL) appended after custom
5. test_load_external_feed_dedup_against_bundled: external feed keywords matching bundled are deduped
6. test_load_external_feed_nonexistent_silent_fallback: missing file = bundled only
7. test_load_external_feed_malformed_lines_skipped: malformed JSONL lines skipped
8. test_phishing_feed_update_status_no_feed: status with no feed
9. test_phishing_feed_update_status_existing_feed: status with existing feed (size, count, mtime)
10. test_bundled_case_insensitive_dedup: case variations deduped
11. test_empty_custom_returns_bundled: custom=[] still works
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[1]
PHISHING_KW = SOURCE_ROOT / "workflow_kit" / "phishing_keywords.py"


def _import_phishing_kw():
    spec = importlib.util.spec_from_file_location("phishing_keywords", str(PHISHING_KW))
    mod = importlib.util.module_from_spec(spec)
    sys.modules["phishing_keywords"] = mod
    spec.loader.exec_module(mod)
    return mod


# --- Test 1: bundled baseline ---


def test_bundled_returns_8_keywords() -> None:
    mod = _import_phishing_kw()
    kws = mod.bundled_keywords()
    assert len(kws) == 8, f"expected 8 bundled, got {len(kws)}: {kws}"
    assert "verify your account" in kws


# --- Test 2: default load = bundled ---


def test_load_default_returns_bundled() -> None:
    mod = _import_phishing_kw()
    kws = mod.load_phishing_keywords()
    assert len(kws) == 8, f"expected 8 default, got {len(kws)}: {kws}"
    assert set(kws) == set(mod.bundled_keywords())


# --- Test 3: custom override + dedup ---


def test_load_custom_overrides_and_dedups() -> None:
    mod = _import_phishing_kw()
    # 'verify your account' is in bundled; 'my new kw' is custom
    kws = mod.load_phishing_keywords(custom=["my new kw", "verify your account"])
    assert "my new kw" in kws, f"custom not added: {kws}"
    # 'verify your account' should appear once (dedup)
    assert kws.count("verify your account") == 1, f"not deduped: {kws}"
    # custom should come first
    assert kws[0] == "my new kw", f"custom not first: {kws}"


# --- Test 4: external feed appended ---


def test_load_external_feed_appended() -> None:
    mod = _import_phishing_kw()
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        feed = Path(tmpdir) / "feed.jsonl"
        feed.write_text(
            json.dumps({"keyword": "phish-feed-1", "source": "test"}) + "\n"
            + json.dumps({"keyword": "phish-feed-2", "source": "test"}) + "\n"
        )
        kws = mod.load_phishing_keywords(external_feed=feed)
        assert "phish-feed-1" in kws, f"feed-1 missing: {kws}"
        assert "phish-feed-2" in kws, f"feed-2 missing: {kws}"
        # Feed should be AFTER custom but BEFORE bundled (or after bundled if no custom)
        # Default order: custom > external > bundled. No custom here, so external comes first.
        assert kws[0] == "phish-feed-1", f"external not first: {kws}"


# --- Test 5: external feed dedup against bundled ---


def test_load_external_feed_dedup_against_bundled() -> None:
    mod = _import_phishing_kw()
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        feed = Path(tmpdir) / "feed.jsonl"
        # 'verify your account' is in bundled; 'new-from-feed' is new
        feed.write_text(
            json.dumps({"keyword": "verify your account"}) + "\n"
            + json.dumps({"keyword": "new-from-feed"}) + "\n"
        )
        kws = mod.load_phishing_keywords(external_feed=feed)
        # Bundled 'verify your account' should be deduped (first occurrence wins — external first)
        assert kws.count("verify your account") == 1
        assert "new-from-feed" in kws


# --- Test 6: missing feed file = silent fallback ---


def test_load_external_feed_nonexistent_silent_fallback() -> None:
    mod = _import_phishing_kw()
    kws = mod.load_phishing_keywords(external_feed=Path("/nonexistent/feed.jsonl"))
    # No error, fallback to bundled
    assert len(kws) == 8, f"expected 8 (bundled fallback), got {len(kws)}: {kws}"


# --- Test 7: malformed lines skipped ---


def test_load_external_feed_malformed_lines_skipped() -> None:
    mod = _import_phishing_kw()
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        feed = Path(tmpdir) / "feed.jsonl"
        feed.write_text(
            "{not valid json\n"
            + json.dumps({"keyword": "good-1"}) + "\n"
            + "also bad\n"
            + json.dumps({"keyword": "good-2"}) + "\n"
        )
        kws = mod.load_phishing_keywords(external_feed=feed)
        assert "good-1" in kws
        assert "good-2" in kws
        # Should not crash


# --- Test 8: status with no feed ---


def test_phishing_feed_update_status_no_feed() -> None:
    mod = _import_phishing_kw()
    status = mod.phishing_feed_update_status()
    assert status["feed_path"] is None
    assert status["feed_exists"] is False
    assert status["feed_keyword_count"] == 0
    assert status["bundled_count"] == 8
    assert status["last_modified"] is None


# --- Test 9: status with existing feed ---


def test_phishing_feed_update_status_existing_feed() -> None:
    mod = _import_phishing_kw()
    import tempfile
    import time
    with tempfile.TemporaryDirectory() as tmpdir:
        feed = Path(tmpdir) / "feed.jsonl"
        feed.write_text(
            json.dumps({"keyword": "a"}) + "\n"
            + json.dumps({"keyword": "b"}) + "\n"
        )
        status = mod.phishing_feed_update_status(external_feed=feed)
        assert status["feed_exists"] is True
        assert status["feed_keyword_count"] == 2
        assert status["feed_size_bytes"] > 0
        assert status["last_modified"] is not None
        assert abs(status["last_modified"] - time.time()) < 10


# --- Test 10: case-insensitive dedup ---


def test_bundled_case_insensitive_dedup() -> None:
    mod = _import_phishing_kw()
    kws = mod.load_phishing_keywords(custom=["VERIFY YOUR ACCOUNT", "new kw"])
    # 'verify your account' (bundled, lowercased) and 'verify your account' (custom, lowercased) deduped
    assert kws.count("verify your account") == 1, f"not case-deduped: {kws}"
    assert "new kw" in kws


# --- Test 11: empty custom ---


def test_empty_custom_returns_bundled() -> None:
    mod = _import_phishing_kw()
    kws = mod.load_phishing_keywords(custom=[])
    assert len(kws) == 8, f"empty custom should still return bundled, got {len(kws)}"


def main() -> int:
    test_funcs = [
        test_bundled_returns_8_keywords,
        test_load_default_returns_bundled,
        test_load_custom_overrides_and_dedups,
        test_load_external_feed_appended,
        test_load_external_feed_dedup_against_bundled,
        test_load_external_feed_nonexistent_silent_fallback,
        test_load_external_feed_malformed_lines_skipped,
        test_phishing_feed_update_status_no_feed,
        test_phishing_feed_update_status_existing_feed,
        test_bundled_case_insensitive_dedup,
        test_empty_custom_returns_bundled,
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
    total = len(test_funcs)
    passed = total - len(failed)
    print(f"\n{passed}/{total} tests passed.")
    if failed:
        print(f"\n{len(failed)} tests failed:")
        for name in failed:
            print(f"  - {name}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
