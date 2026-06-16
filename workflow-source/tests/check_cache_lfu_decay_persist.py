"""workflow_kit.cache_lfu_decay_persist test (v0.7.49+).

Test list:
1. test_save_and_load_decay_scores_roundtrip_v0_7_49: save + load returns same scores
2. test_update_decay_score_persists_v0_7_49: update single URL persists
"""

from __future__ import annotations

import importlib.util
import sys
import tempfile
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[1]
PERSIST = SOURCE_ROOT / "workflow_kit" / "cache_lfu_decay_persist.py"


def _import_module():
    spec = importlib.util.spec_from_file_location("cache_lfu_decay_persist", str(PERSIST))
    mod = importlib.util.module_from_spec(spec)
    sys.modules["cache_lfu_decay_persist"] = mod
    spec.loader.exec_module(mod)
    return mod


def test_save_and_load_decay_scores_roundtrip_v0_7_49() -> None:
    """save_decay_scores + load_decay_scores roundtrip returns same scores."""
    mod = _import_module()
    with tempfile.TemporaryDirectory() as tmpdir:
        path = str(Path(tmpdir) / "scores.json")
        scores = {
            "https://a.com/": 10.5,
            "https://b.com/": 5.2,
            "https://c.com/": 0.0,
        }
        mod.save_decay_scores(scores, path)
        loaded = mod.load_decay_scores(path)
        assert loaded == scores, f"roundtrip mismatch: {loaded} != {scores}"


def test_update_decay_score_persists_v0_7_49() -> None:
    """update_decay_score updates single URL + persists to disk."""
    mod = _import_module()
    with tempfile.TemporaryDirectory() as tmpdir:
        path = str(Path(tmpdir) / "scores.json")
        scores: dict[str, float] = {"https://a.com/": 5.0}
        mod.update_decay_score(scores, "https://b.com/", 10.0, path)
        # Re-load from disk to verify persistence
        loaded = mod.load_decay_scores(path)
        assert loaded == {"https://a.com/": 5.0, "https://b.com/": 10.0}
        assert mod.get_decay_score(loaded, "https://c.com/", default=-1.0) == -1.0


def main() -> int:
    test_funcs = [
        test_save_and_load_decay_scores_roundtrip_v0_7_49,
        test_update_decay_score_persists_v0_7_49,
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
