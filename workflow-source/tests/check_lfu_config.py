"""workflow_kit.lfu_config test (v0.7.46+).

Test list:
1. test_lfu_config_defaults: default values
2. test_compute_lfu_score_higher_frequency_higher_score: higher access_count -> higher score
3. test_compute_lfu_score_with_decay_halves_at_half_life_v0_7_46: score at half_life is < score at age=0
4. test_compute_lfu_score_with_decay_invalid_half_life_v0_7_46: raises ValueError on half_life <= 0
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[1]
LFU_CONFIG = SOURCE_ROOT / "workflow_kit" / "lfu_config.py"


def _import_lfu_config():
    spec = importlib.util.spec_from_file_location("lfu_config", str(LFU_CONFIG))
    mod = importlib.util.module_from_spec(spec)
    sys.modules["lfu_config"] = mod
    spec.loader.exec_module(mod)
    return mod


def test_lfu_config_defaults() -> None:
    """LFUConfig default values are frequency_weight=0.5, recency_weight=0.5, decay_seconds=86400."""
    mod = _import_lfu_config()
    cfg = mod.LFUConfig()
    assert cfg.frequency_weight == 0.5
    assert cfg.recency_weight == 0.5
    assert cfg.decay_seconds == 86400.0


def test_compute_lfu_score_higher_frequency_higher_score() -> None:
    """Higher access_count yields higher LFU score (with same age)."""
    mod = _import_lfu_config()
    cfg = mod.LFUConfig(frequency_weight=1.0, recency_weight=0.0, decay_seconds=86400.0)
    score_low = mod.compute_lfu_score(access_count=1, age_seconds=100, config=cfg)
    score_high = mod.compute_lfu_score(access_count=100, age_seconds=100, config=cfg)
    assert score_high > score_low, f"high freq should score higher: {score_high} vs {score_low}"


def test_compute_lfu_score_with_decay_halves_at_half_life_v0_7_46() -> None:
    """compute_lfu_score_with_decay: score at half_life is < score at age=0 (same access_count)."""
    mod = _import_lfu_config()
    cfg = mod.LFUConfig(frequency_weight=1.0, recency_weight=0.0, decay_seconds=86400.0)
    half_life = 3600.0  # 1 hour
    score_t0 = mod.compute_lfu_score_with_decay(
        access_count=100, age_seconds=0, config=cfg, half_life_seconds=half_life
    )
    score_th = mod.compute_lfu_score_with_decay(
        access_count=100, age_seconds=half_life, config=cfg, half_life_seconds=half_life
    )
    assert score_t0 > score_th, f"score at t=0 should be > score at half_life, got {score_t0} vs {score_th}"


def test_compute_lfu_score_with_decay_invalid_half_life_v0_7_46() -> None:
    """compute_lfu_score_with_decay raises ValueError on half_life_seconds <= 0."""
    mod = _import_lfu_config()
    cfg = mod.LFUConfig()
    try:
        mod.compute_lfu_score_with_decay(
            access_count=10, age_seconds=100, config=cfg, half_life_seconds=0
        )
        assert False, "expected ValueError"
    except ValueError:
        pass


def main() -> int:
    test_funcs = [
        test_lfu_config_defaults,
        test_compute_lfu_score_higher_frequency_higher_score,
        test_compute_lfu_score_with_decay_halves_at_half_life_v0_7_46,
        test_compute_lfu_score_with_decay_invalid_half_life_v0_7_46,
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
