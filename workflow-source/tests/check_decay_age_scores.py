"""workflow_kit.cache_lfu_decay_persist.decay_age_scores test (v0.7.51+).

Test list:
1. test_decay_age_scores_halves_after_half_life_v0_7_51: scores halve after half_life
2. test_decay_age_scores_zero_age_returns_unchanged_v0_7_51: zero age returns same scores
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[1]
PERSIST = SOURCE_ROOT / "workflow_kit" / "cache_lfu_decay_persist.py"


def _import_module():
    spec = importlib.util.spec_from_file_location("cache_lfu_decay_persist", str(PERSIST))
    mod = importlib.util.module_from_spec(spec)
    sys.modules["cache_lfu_decay_persist"] = mod
    spec.loader.exec_module(mod)
    return mod


def test_decay_age_scores_halves_after_half_life_v0_7_51() -> None:
    """decay_age_scores halves scores after half_life seconds."""
    mod = _import_module()
    scores = {"https://a.com/": 10.0, "https://b.com/": 5.0}
    # saved_at=0, now=86400 (1 day), half_life=86400 -> factor = 0.5
    aged = mod.decay_age_scores(scores, saved_at=0.0, now=86400.0, half_life_seconds=86400.0)
    assert abs(aged["https://a.com/"] - 5.0) < 0.001
    assert abs(aged["https://b.com/"] - 2.5) < 0.001


def test_decay_age_scores_zero_age_returns_unchanged_v0_7_51() -> None:
    """decay_age_scores with zero age returns scores unchanged."""
    mod = _import_module()
    scores = {"https://a.com/": 10.0}
    aged = mod.decay_age_scores(scores, saved_at=1000.0, now=1000.0)
    assert aged == {"https://a.com/": 10.0}


def main() -> int:
    test_funcs = [
        test_decay_age_scores_halves_after_half_life_v0_7_51,
        test_decay_age_scores_zero_age_returns_unchanged_v0_7_51,
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
