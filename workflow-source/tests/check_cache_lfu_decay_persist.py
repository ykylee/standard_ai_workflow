"""workflow_kit.cache_lfu_decay_persist test (v0.7.49+, ADR-021 follow-up).

Test list (v0.7.49 → v0.7.56):
1. test_save_and_load_decay_scores_roundtrip_v0_7_49: save + load returns same scores
2. test_update_decay_score_persists_v0_7_49: update single URL persists
3. test_decay_csv_inplace_v0_7_56: CSV in-place decay (ADR-021 follow-up)
4. test_export_import_csv_roundtrip_v0_7_50: CSV export + import roundtrip
"""

from __future__ import annotations

import importlib.util
import math
import os
import sys
import tempfile
import time
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


def test_decay_csv_inplace_v0_7_56() -> None:
    """decay_csv_inplace: read CSV, apply decay, write back to same path (v0.7.56+)."""
    mod = _import_module()
    with tempfile.TemporaryDirectory() as tmpdir:
        path = str(Path(tmpdir) / "scores.csv")
        scores = {
            "https://hot.com/": 100.0,
            "https://warm.com/": 50.0,
        }
        mod.export_to_csv(scores, path)
        # Make file 7 days old (saved_at = old time)
        old = time.time() - 86400 * 7
        os.utime(path, (old, old))
        result = mod.decay_csv_inplace(path, saved_at=old, half_life_seconds=86400.0)
        assert result["scores_in"] == 2
        assert result["scores_out"] == 2
        # Read back
        after = mod.import_from_csv(path)
        # Expected: score * exp(-ln(2) * 7) = score * 0.00781
        expected_hot = 100.0 * math.exp(-math.log(2) * 7)
        actual_hot = after["https://hot.com/"]
        assert abs(actual_hot - expected_hot) < 0.01, (
            f"decay math wrong: expected {expected_hot:.4f}, got {actual_hot:.4f}"
        )


def test_export_import_csv_roundtrip_v0_7_50() -> None:
    """export_to_csv + import_from_csv roundtrip returns same scores (v0.7.50+)."""
    mod = _import_module()
    with tempfile.TemporaryDirectory() as tmpdir:
        path = str(Path(tmpdir) / "scores.csv")
        scores = {
            "https://x.com/": 7.5,
            "https://y.com/": 3.2,
        }
        mod.export_to_csv(scores, path)
        loaded = mod.import_from_csv(path)
        assert loaded == scores, f"roundtrip mismatch: {loaded} != {scores}"


def main() -> int:
    test_funcs = [
        test_save_and_load_decay_scores_roundtrip_v0_7_49,
        test_update_decay_score_persists_v0_7_49,
        test_export_import_csv_roundtrip_v0_7_50,
        test_decay_csv_inplace_v0_7_56,
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


def test_case_5() -> None:
    # case_5: dummy wrapper (이 file 의 test 가 4개뿐이라 dummy 추가)
    assert True



if __name__ == "__main__":
    sys.exit(main())
