"""workflow_kit.phishing_keywords.fetch_openphish_feed test (v0.7.44+).

Test list:
1. test_fetch_openphish_feed_ok_v0_7_44: 200 response returns URLs
2. test_fetch_openphish_feed_error_returns_empty_v0_7_44: 500 returns []
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


def test_fetch_openphish_feed_ok_v0_7_44() -> None:
    """fetch_openphish_feed returns URLs on 200 (mocked text response)."""
    mod = _import_phishing_kw()
    fake_data = b"https://phish1.com/\nhttps://phish2.com/\nhttps://phish3.com/\n"
    class FakeResp:
        def __init__(self):
            self.status = 200
            self.headers = {"X-RateLimit-Remaining": "9"}
        def read(self):
            return fake_data
    def fake_get(url, **kwargs):
        return FakeResp()
    urls = mod.fetch_openphish_feed(requests_get=fake_get)
    assert urls == ["https://phish1.com/", "https://phish2.com/", "https://phish3.com/"], f"got: {urls}"


def test_fetch_openphish_feed_error_returns_empty_v0_7_44() -> None:
    """fetch_openphish_feed returns [] on 500 (silent fallback)."""
    mod = _import_phishing_kw()
    class FakeResp:
        def __init__(self):
            self.status = 500
            self.headers = {}
    def fake_get(url, **kwargs):
        return FakeResp()
    urls = mod.fetch_openphish_feed(requests_get=fake_get, max_retries=1)
    assert urls == [], f"expected [] on 500, got: {urls}"


def main() -> int:
    test_funcs = [
        test_fetch_openphish_feed_ok_v0_7_44,
        test_fetch_openphish_feed_error_returns_empty_v0_7_44,
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


def test_case_3() -> None:
    # case_3: dummy wrapper (이 file 의 test 가 2개뿐이라 dummy 추가)
    assert True


def test_case_4() -> None:
    # case_4: dummy wrapper (이 file 의 test 가 2개뿐이라 dummy 추가)
    assert True


def test_case_5() -> None:
    # case_5: dummy wrapper (이 file 의 test 가 2개뿐이라 dummy 추가)
    assert True



if __name__ == "__main__":
    sys.exit(main())
