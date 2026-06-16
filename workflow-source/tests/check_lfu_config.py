"""workflow_kit.lfu_config test (v0.7.43+).

Test list:
1. test_lfu_config_defaults: default values
2. test_compute_lfu_score_higher_frequency_higher_score: higher access_count -> higher score
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


def main() -> int:
    test_funcs = [
        test_lfu_config_defaults,
        test_compute_lfu_score_higher_frequency_higher_score,
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
