"""workflow_kit.phishing_federation_v5 test (v0.7.50+).

Test list:
1. test_fetch_federated_phishing_urls_v5_three_sources_v0_7_50: 3 source weighted voting works
2. test_build_default_sources_v5_includes_third_v0_7_50: builds 3 sources when third provided
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

FEDERATION_V5 = SOURCE_ROOT / "workflow_kit" / "phishing_federation_v5.py"


def _import_module():
    spec = importlib.util.spec_from_file_location("phishing_federation_v5", str(FEDERATION_V5))
    mod = importlib.util.module_from_spec(spec)
    sys.modules["phishing_federation_v5"] = mod
    spec.loader.exec_module(mod)
    return mod


def test_fetch_federated_phishing_urls_v5_three_sources_v0_7_50() -> None:
    """fetch_federated_phishing_urls_v5 with 3 sources returns weighted results."""
    mod = _import_module()
    def src1():
        return ["https://a.com/", "https://b.com/"]
    def src2():
        return ["https://a.com/", "https://c.com/"]
    def src3():
        return ["https://a.com/"]  # a in 3 sources
    # weights: 1.0, 0.8, 0.9
    result = mod.fetch_federated_phishing_urls_v5([
        (src1, 1.0),
        (src2, 0.8),
        (src3, 0.9),
    ])
    by_url = {url: conf for url, conf, _ in result}
    assert abs(by_url["https://a.com/"] - 2.7) < 0.001
    assert by_url["https://b.com/"] == 1.0
    assert by_url["https://c.com/"] == 0.8
    assert result[0][0] == "https://a.com/"


def test_build_default_sources_v5_includes_third_v0_7_50() -> None:
    """build_default_sources_v5 returns 3 sources when third_source provided."""
    mod = _import_module()
    def third():
        return ["https://x.com/"]
    sources = mod.build_default_sources_v5(
        phishtank_api_key="dummy_key",
        third_source=third,
        third_weight=0.9,
    )
    assert len(sources) == 3, f"expected 3 sources, got {len(sources)}"
    for src, weight in sources:
        assert callable(src)
        assert isinstance(weight, float)


def main() -> int:
    test_funcs = [
        test_fetch_federated_phishing_urls_v5_three_sources_v0_7_50,
        test_build_default_sources_v5_includes_third_v0_7_50,
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
