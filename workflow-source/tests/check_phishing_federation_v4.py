"""workflow_kit.phishing_federation_v4 test (v0.7.49+).

Test list:
1. test_fetch_federated_phishing_urls_v4_weighted_v0_7_49: weights sum correctly per URL
2. test_fetch_federated_phishing_urls_v4_min_confidence_v0_7_49: filters by min_confidence
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[1]
FEDERATION_V4 = SOURCE_ROOT / "workflow_kit" / "phishing_federation_v4.py"


def _import_module():
    spec = importlib.util.spec_from_file_location("phishing_federation_v4", str(FEDERATION_V4))
    mod = importlib.util.module_from_spec(spec)
    sys.modules["phishing_federation_v4"] = mod
    spec.loader.exec_module(mod)
    return mod


def test_fetch_federated_phishing_urls_v4_weighted_v0_7_49() -> None:
    """fetch_federated_phishing_urls_v4 sums weights per URL."""
    mod = _import_module()
    def src1():
        return ["https://a.com/", "https://b.com/"]
    def src2():
        return ["https://a.com/", "https://c.com/"]  # a in 2 sources
    def src3():
        return ["https://a.com/"]  # a in 3 sources
    # weights: src1=1.0, src2=0.5, src3=0.8
    result = mod.fetch_federated_phishing_urls_v4([
        (src1, 1.0),
        (src2, 0.5),
        (src3, 0.8),
    ])
    # a.com: 1.0 + 0.5 + 0.8 = 2.3
    # b.com: 1.0
    # c.com: 0.5
    by_url = {url: conf for url, conf, _ in result}
    assert abs(by_url["https://a.com/"] - 2.3) < 0.001
    assert by_url["https://b.com/"] == 1.0
    assert by_url["https://c.com/"] == 0.5
    # Sorted by confidence desc: a (2.3), b (1.0), c (0.5)
    assert result[0][0] == "https://a.com/"
    assert result[-1][0] == "https://c.com/"


def test_fetch_federated_phishing_urls_v4_min_confidence_v0_7_49() -> None:
    """fetch_federated_phishing_urls_v4 filters by min_confidence threshold."""
    mod = _import_module()
    def src1():
        return ["https://low.com/", "https://high.com/"]
    def src2():
        return ["https://high.com/"]
    result = mod.fetch_federated_phishing_urls_v4([
        (src1, 0.5),
        (src2, 0.5),
    ], min_confidence=0.6)
    # low.com: 0.5 (filtered out)
    # high.com: 1.0 (kept)
    urls = [r[0] for r in result]
    assert "https://low.com/" not in urls
    assert "https://high.com/" in urls


def main() -> int:
    test_funcs = [
        test_fetch_federated_phishing_urls_v4_weighted_v0_7_49,
        test_fetch_federated_phishing_urls_v4_min_confidence_v0_7_49,
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
