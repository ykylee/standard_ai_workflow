"""workflow_kit.lfu_config — V-R10 v3 LFU tuning config (v0.7.43+).

ADR-021 follow-up: LFU eviction strategy 의 *tuning* 의 *operational* 보강.
- frequency_weight: 0.0 (no frequency) to 1.0 (frequency only)
- recency_weight: 0.0 (no recency) to 1.0 (recency only)
- decay_seconds: time constant for access_count decay (default 86400 = 1 day)

Composite score = frequency_weight * (access_count / decay_factor) + recency_weight * (1 / age)
Lower composite score = more likely to evict.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LFUConfig:
    """LFU tuning config (v0.7.43+, ADR-021 follow-up)."""

    frequency_weight: float = 0.5
    recency_weight: float = 0.5
    decay_seconds: float = 86400.0


def compute_lfu_score(
    access_count: int,
    age_seconds: float,
    config: LFUConfig | None = None,
) -> float:
    """Compute LFU composite score (v0.7.43+, ADR-021 follow-up).

    Returns the higher-is-better composite score. Eviction logic should pick the
    entry with the LOWEST score.

    Args:
        access_count: number of cache hits
        age_seconds: time since entry creation
        config: LFUConfig (default: LFUConfig())
    """
    cfg = config or LFUConfig()
    decay_factor = max(1.0, age_seconds / cfg.decay_seconds)
    freq_score = access_count / decay_factor
    recency_score = 1.0 / max(1.0, age_seconds)
    return cfg.frequency_weight * freq_score + cfg.recency_weight * recency_score
