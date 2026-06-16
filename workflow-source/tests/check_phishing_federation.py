"""workflow_kit.phishing_keywords.fetch_federated_phishing_urls test (v0.7.45+).

Test list:
1. test_fetch_federated_phishing_urls_dedups_v0_7_45: PhishTank + OpenPhish union + dedup
2. test_fetch_federated_phishing_urls_handles_api_failure_v0_7_45: API failure -> silent fallback
"""

from __future__ import annotations

import importlib.util
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


def test_fetch_federated_phishing_urls_dedups_v0_7_45() -> None:
    """fetch_federated_phishing_urls returns deduped union (PhishTank + OpenPhish)."""
    mod = _import_phishing_kw()
    # Mock PhishTank response
    class FakePTResp:
        def __init__(self):
            self.status = 200
            self.headers = {}
        def read(self):
            return b'[{"url": "https://phish-A.com/"}, {"url": "https://phish-B.com/"}]'
    # Mock OpenPhish response
    class FakeOPResp:
        def __init__(self):
            self.status = 200
            self.headers = {}
        def read(self):
            return b"https://phish-B.com/\nhttps://phish-C.com/\n"  # phish-B.com is a duplicate
    urls = mod.fetch_federated_phishing_urls(
        phishtank_api_key="dummy_key",
        requests_get_pt=lambda url, **kwargs: FakePTResp(),
        requests_get_op=lambda url, **kwargs: FakeOPResp(),
    )
    # Expected: 3 unique URLs (A, B, C), sorted, case-normalized
    assert "https://phish-a.com/" in urls, f"phish-A should be in result: {urls}"
    assert "https://phish-b.com/" in urls, f"phish-B should be in result (deduped): {urls}"
    assert "https://phish-c.com/" in urls, f"phish-C should be in result: {urls}"
    assert len(urls) == 3, f"expected 3 unique URLs (dedup), got {len(urls)}: {urls}"
    # Verify sorted
    assert urls == sorted(urls), f"urls should be sorted: {urls}"


def test_fetch_federated_phishing_urls_handles_api_failure_v0_7_45() -> None:
    """fetch_federated_phishing_urls returns empty list on API failure (silent fallback)."""
    mod = _import_phishing_kw()
    def fail_get(url, **kwargs):
        raise OSError("network down")
    urls = mod.fetch_federated_phishing_urls(
        phishtank_api_key="dummy_key",
        requests_get_pt=fail_get,
        requests_get_op=fail_get,
    )
    assert urls == [], f"expected [] on API failure, got: {urls}"


def main() -> int:
    test_funcs = [
        test_fetch_federated_phishing_urls_dedups_v0_7_45,
        test_fetch_federated_phishing_urls_handles_api_failure_v0_7_45,
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
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
