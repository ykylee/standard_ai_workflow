"""workflow_kit.phishing_federation_v2 test (v0.7.46+).

Test list:
1. test_fetch_federated_phishing_urls_v2_dedups_v0_7_46: 3-source federation dedups + sorts
2. test_build_default_sources_v2_returns_callables_v0_7_46: builds PhishTank + OpenPhish sources
"""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_KIT_DIR = SOURCE_ROOT / "workflow_kit"

# Register workflow_kit as a package for cross-module imports
workflow_kit_pkg = types.ModuleType("workflow_kit")
workflow_kit_pkg.__path__ = [str(WORKFLOW_KIT_DIR)]
sys.modules["workflow_kit"] = workflow_kit_pkg


def _import_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(f"workflow_kit.{name}", str(path))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[f"workflow_kit.{name}"] = mod
    spec.loader.exec_module(mod)
    return mod


# Import phishing_keywords so federation_v2 can import it
_phishing_keywords = _import_module("phishing_keywords", WORKFLOW_KIT_DIR / "phishing_keywords.py")
_federation_v2 = _import_module(
    "phishing_federation_v2", WORKFLOW_KIT_DIR / "phishing_federation_v2.py"
)


def test_fetch_federated_phishing_urls_v2_dedups_v0_7_46() -> None:
    """fetch_federated_phishing_urls_v2 dedups + sorts from 3 sources."""
    def src1():
        return ["https://phish-A.com/", "https://phish-B.com/"]
    def src2():
        return ["https://phish-B.com/", "https://phish-C.com/"]  # B is duplicate
    def src3():
        return ["https://phish-D.com/"]
    urls = _federation_v2.fetch_federated_phishing_urls_v2([src1, src2, src3])
    # Expected: 4 unique URLs (A, B, C, D), sorted
    assert "https://phish-a.com/" in urls
    assert "https://phish-b.com/" in urls
    assert "https://phish-c.com/" in urls
    assert "https://phish-d.com/" in urls
    assert len(urls) == 4, f"expected 4 unique URLs, got {len(urls)}: {urls}"
    assert urls == sorted(urls), f"urls should be sorted: {urls}"


def test_build_default_sources_v2_returns_callables_v0_7_46() -> None:
    """build_default_sources_v2 returns 2 callables (PhishTank + OpenPhish)."""
    sources = _federation_v2.build_default_sources_v2(phishtank_api_key="dummy_key")
    assert len(sources) == 2, f"expected 2 sources, got {len(sources)}"
    # Each source should be a callable
    for s in sources:
        assert callable(s), f"source should be callable: {s}"


def main() -> int:
    test_funcs = [
        test_fetch_federated_phishing_urls_v2_dedups_v0_7_46,
        test_build_default_sources_v2_returns_callables_v0_7_46,
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
