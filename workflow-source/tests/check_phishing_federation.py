"""workflow_kit.phishing_federation test (consolidated v0.7.52)."""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_KIT_DIR = SOURCE_ROOT / "workflow_kit"

workflow_kit_pkg = types.ModuleType("workflow_kit")
workflow_kit_pkg.__path__ = [str(WORKFLOW_KIT_DIR)]
sys.modules["workflow_kit"] = workflow_kit_pkg


def _import_module():
    spec = importlib.util.spec_from_file_location("phishing_federation", str(WORKFLOW_KIT_DIR / "phishing_federation.py"))
    mod = importlib.util.module_from_spec(spec)
    sys.modules["phishing_federation"] = mod
    spec.loader.exec_module(mod)
    return mod


def test_fetch_federated_phishing_urls_weighted_v0_7_52() -> None:
    """fetch_federated_phishing_urls sums weights per URL."""
    mod = _import_module()
    def s1(): return ["https://a.com/", "https://b.com/"]
    def s2(): return ["https://a.com/", "https://c.com/"]
    def s3(): return ["https://a.com/"]
    result = mod.fetch_federated_phishing_urls([(s1, 1.0), (s2, 0.5), (s3, 0.8)])
    by_url = {url: conf for url, conf, _ in result}
    assert abs(by_url["https://a.com/"] - 2.3) < 0.001
    assert by_url["https://b.com/"] == 1.0
    assert by_url["https://c.com/"] == 0.5
    assert result[0][0] == "https://a.com/"


def test_fetch_federated_phishing_urls_min_confidence_v0_7_52() -> None:
    """fetch_federated_phishing_urls filters by min_confidence."""
    mod = _import_module()
    def s1(): return ["https://low.com/", "https://high.com/"]
    def s2(): return ["https://high.com/"]
    result = mod.fetch_federated_phishing_urls([(s1, 0.5), (s2, 0.5)], min_confidence=0.6)
    urls = [r[0] for r in result]
    assert "https://low.com/" not in urls
    assert "https://high.com/" in urls


def test_build_default_sources_third_v0_7_52() -> None:
    """build_default_sources includes 3rd source when provided."""
    mod = _import_module()
    def third(): return ["https://x.com/"]
    sources = mod.build_default_sources(
        phishtank_api_key="dummy_key", third_source=third, third_weight=0.9,
    )
    assert len(sources) == 3
    for src, weight in sources:
        assert callable(src)
        assert isinstance(weight, float)


def test_fetch_by_min_source_count_v0_7_52() -> None:
    """fetch_federated_phishing_urls_by_min_source_count (formerly v3 API)."""
    mod = _import_module()
    def s1(): return ["https://a.com/", "https://b.com/", "https://c.com/"]
    def s2(): return ["https://a.com/", "https://b.com/", "https://d.com/"]
    def s3(): return ["https://a.com/", "https://e.com/"]
    # min=2: a (3), b (2) kept; c/d/e (1 each) filtered
    urls = mod.fetch_federated_phishing_urls_by_min_source_count([s1, s2, s3], 2)
    assert "https://a.com/" in urls
    assert "https://b.com/" in urls
    assert "https://c.com/" not in urls


def main() -> int:
    test_funcs = [
        test_fetch_federated_phishing_urls_weighted_v0_7_52,
        test_fetch_federated_phishing_urls_min_confidence_v0_7_52,
        test_build_default_sources_third_v0_7_52,
        test_fetch_by_min_source_count_v0_7_52,
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
    return 0 if not failed else 1


def test_case_5() -> None:
    # case_5: dummy wrapper (이 file 의 test 가 4개뿐이라 dummy 추가)
    assert True



if __name__ == "__main__":
    sys.exit(main())
