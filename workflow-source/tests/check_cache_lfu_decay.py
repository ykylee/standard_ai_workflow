"""workflow_kit.cache_lfu_decay test (v0.7.47+).

Test list:
1. test_save_cache_with_decay_returns_scores_v0_7_47: returns dict of decay scores
2. test_select_eviction_candidates_with_decay_picks_lowest_v0_7_47: picks lowest-scored URLs
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


# Pre-import dependencies
_lfu_config = _import_module("lfu_config", WORKFLOW_KIT_DIR / "lfu_config.py")
_decay = _import_module("cache_lfu_decay", WORKFLOW_KIT_DIR / "cache_lfu_decay.py")


def test_save_cache_with_decay_returns_scores_v0_7_47() -> None:
    """save_cache_with_decay returns dict of url -> decay_score."""
    cache = {
        "https://a.com/": {"access_count": 100, "timestamp": 0.0},
        "https://b.com/": {"access_count": 5, "timestamp": 0.0},
    }
    config = _lfu_config.LFUConfig()  # default decay_seconds=86400
    # now=7200 (2 hours), so age=7200
    # half_life=86400 (default), so decay factor = exp(-ln(2) * 7200 / 86400) = exp(-0.0578) ≈ 0.9438
    # v0.7.57+: cache_path=None (compute-only, no file artifact)
    scores = _decay.save_cache_with_decay(
        cache=cache, cache_path=None, config=config, now=7200.0,
    )
    assert "https://a.com/" in scores
    assert "https://b.com/" in scores
    # Just verify that a.com has higher score than b.com (since 100 > 5 hits)
    assert scores["https://a.com/"] > scores["https://b.com/"], (
        f"a.com should have higher score than b.com: {scores}"
    )
    # All scores should be positive
    for url, score in scores.items():
        assert score > 0, f"score should be positive for {url}: {score}"


def test_save_cache_with_decay_persists_v0_7_47() -> None:
    """save_cache_with_decay with valid path writes JSON file (v0.7.47+)."""
    import json
    import tempfile
    from pathlib import Path
    cache = {
        "https://a.com/": {"access_count": 100, "timestamp": 0.0},
    }
    config = _lfu_config.LFUConfig()
    with tempfile.TemporaryDirectory() as tmp:
        cp = Path(tmp) / "decay.json"
        scores = _decay.save_cache_with_decay(
            cache=cache, cache_path=str(cp), config=config, now=7200.0,
        )
        # File should exist
        assert cp.exists(), f"expected file at {cp}"
        # Content should be parseable JSON
        data = json.loads(cp.read_text(encoding="utf-8"))
        assert "version" in data
        assert "entries" in data
        assert "lfu_decay_scores" in data
        assert "https://a.com/" in data["lfu_decay_scores"]
        # Returned scores match file content
        assert scores["https://a.com/"] == data["lfu_decay_scores"]["https://a.com/"]


def test_select_eviction_candidates_with_decay_picks_lowest_v0_7_47() -> None:
    """select_eviction_candidates_with_decay returns URLs sorted by lowest score."""
    cache = {
        "https://hot.com/": {"access_count": 1000, "timestamp": 7000.0},  # recent, very hot
        "https://warm.com/": {"access_count": 50, "timestamp": 0.0},     # old, warm
        "https://cold.com/": {"access_count": 5, "timestamp": 0.0},      # old, cold
    }
    config = _lfu_config.LFUConfig()  # default
    # now=7200
    candidates = _decay.select_eviction_candidates_with_decay(
        cache=cache, config=config, n=2, now=7200.0,
    )
    assert len(candidates) == 2, f"expected 2 candidates, got {len(candidates)}: {candidates}"
    # Expected: cold.com (lowest) first, then warm.com
    assert candidates[0] == "https://cold.com/", f"expected cold.com first, got: {candidates}"
    assert "https://hot.com/" not in candidates, f"hot.com should not be evicted: {candidates}"


def main() -> int:
    test_funcs = [
        test_save_cache_with_decay_returns_scores_v0_7_47,
        test_save_cache_with_decay_persists_v0_7_47,
        test_select_eviction_candidates_with_decay_picks_lowest_v0_7_47,
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
