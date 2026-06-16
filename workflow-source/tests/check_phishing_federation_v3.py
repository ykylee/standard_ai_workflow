"""workflow_kit.phishing_federation_v3 test (v0.7.48+).

Test list:
1. test_fetch_federated_phishing_urls_v3_cross_source_v0_7_48: only URLs in >= 2 sources returned
2. test_fetch_federated_phishing_urls_v3_with_min_v0_7_48: flat list with configurable min
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[1]
FEDERATION_V3 = SOURCE_ROOT / "workflow_kit" / "phishing_federation_v3.py"


def _import_module():
    spec = importlib.util.spec_from_file_location("phishing_federation_v3", str(FEDERATION_V3))
    mod = importlib.util.module_from_spec(spec)
    sys.modules["phishing_federation_v3"] = mod
    spec.loader.exec_module(mod)
    return mod


def test_fetch_federated_phishing_urls_v3_cross_source_v0_7_48() -> None:
    """fetch_federated_phishing_urls_v3 only returns URLs in >= 2 sources."""
    mod = _import_module()
    def src1():
        return ["https://a.com/", "https://b.com/", "https://c.com/"]
    def src2():
        return ["https://a.com/", "https://b.com/", "https://d.com/"]  # a, b in 2 sources
    def src3():
        return ["https://a.com/", "https://e.com/"]  # a in 3 sources
    result = mod.fetch_federated_phishing_urls_v3([src1, src2, src3], min_source_count=2)
    # a.com in 3 sources, b.com in 2 sources, c/d/e in 1 source only
    assert "https://a.com/" in result
    assert "https://b.com/" in result
    assert "https://c.com/" not in result, f"c.com only in 1 source: {result}"
    assert "https://d.com/" not in result, f"d.com only in 1 source: {result}"
    assert "https://e.com/" not in result, f"e.com only in 1 source: {result}"
    # Sorted by source count desc: a.com first (3), b.com second (2)
    urls = list(result.keys())
    assert urls[0] == "https://a.com/"
    assert urls[1] == "https://b.com/"


def test_fetch_federated_phishing_urls_v3_with_min_v0_7_48() -> None:
    """fetch_federated_phishing_urls_v3_with_min returns flat sorted list."""
    mod = _import_module()
    def src1():
        return ["https://x.com/"]
    def src2():
        return ["https://x.com/", "https://y.com/"]
    def src3():
        return ["https://x.com/"]
    # min=2: x.com in 3 sources -> in. y.com in 1 source -> out.
    urls = mod.fetch_federated_phishing_urls_v3_with_min([src1, src2, src3], min_source_count=2)
    assert urls == ["https://x.com/"], f"unexpected: {urls}"


def main() -> int:
    test_funcs = [
        test_fetch_federated_phishing_urls_v3_cross_source_v0_7_48,
        test_fetch_federated_phishing_urls_v3_with_min_v0_7_48,
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
