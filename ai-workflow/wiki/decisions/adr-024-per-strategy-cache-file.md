---
type: decision
status: proposed
adr_id: ADR-024
decided_at: 2026-06-16
alternatives_considered: [single-file, per-strategy-file, hybrid-strategy-prefix, no-eviction, external-cache]
related_pages: [concepts/per-strategy-cache-file, decisions/adr-013-v-r10-v2-cache, decisions/adr-014-v-r10-v3-cache-lru, decisions/adr-021-cache-lfu-eviction, decisions/adr-015-v-r10-v3-file-lock, decisions/adr-016-gha-actions-cache, concepts/v-r10-url-validity-lint, patterns/wiki-stub-emit]
created: 2026-06-16
updated: 2026-06-16
r9_skip: true
---

# ADR-024: V-R10 v3 per-strategy cache file (separate file per eviction strategy)

## Status

**Proposed** (2026-06-16, v0.7.42 draft). 본 ADR 은 ADR-021 (LFU eviction strategy) 의 *follow-up* 의 *per-strategy file* 의 *operational* 보강. ADR-014 (LRU-only) 의 *single-file* 의 *limitation* (mixed strategy 의 *operational* 의 *low-friction* 의 *limitation*) 을 *per-strategy file* 의 *isolation* 으로 해결. v0.7.41 release 시점에 *code-side* 미구현 — 본 ADR 의 *formal documentation* 의 *rule-side*.

본 ADR acceptance 는 v0.7.42 release note + 1 release 주기 의 운영 evidence 후 별도 turn 에서 status `proposed` → `accepted`.

## Context

ADR-021 (v0.7.41, accepted) 의 *single cache file* 의 *limitation*:
- *mixed* strategy (default) 의 *LRU* vs *LFU* 의 *compare* 의 *operational* 의 *difficulty*: *single file* 의 *cross-strategy* 의 *compare* 의 *operational* 의 *friction*.
- *per-strategy metric* (v0.7.41 의 *evictions_lru* + *evictions_lfu* counters) 의 *single file* 의 *cross-strategy interference* 의 *operational* 의 *limitation*.
- *strategy switch* 의 *operational* 의 *residual state* 의 *friction*.

본 release (v0.7.42 draft):
- *Per-strategy cache file* 의 *isolation* 의 *operational* 의 *low-friction*.
- *Strategy switch* 의 *clean reset* 의 *operational* 의 *low-friction*.
- *Cross-strategy compare* 의 *operational* 의 *low-friction*.

본 release 의 *code-side* 구현은 v0.7.42+ 별도 turn (본 release 의 *formal documentation* 만, code 변경 없음).

## Decision

### §1. Per-strategy cache file naming (v0.7.42+)

| Strategy | File path | Use case |
|---|---|---|
| `'lru'` | `~/.workflow_kit/url_validity_cache_lru.json` | v0.7.37+ 의 *LRU-only* 의 *backward compat* |
| `'lfu'` | `~/.workflow_kit/url_validity_cache_lfu.json` | v0.7.41+ 의 *LFU-only* 의 *operational* 보강 |
| `'mixed'` | `~/.workflow_kit/url_validity_cache_mixed.json` | v0.7.42+ 의 *mixed* 의 *default* 의 *operational* 의 *low-friction* |

```python
# Pseudo-code (v0.7.42+)
def cache_file_for_strategy(base_path: Path, strategy: str) -> Path:
    """Return per-strategy cache file path."""
    if strategy == "lru":
        return base_path.with_name(base_path.stem + "_lru" + base_path.suffix)
    elif strategy == "lfu":
        return base_path.with_name(base_path.stem + "_lfu" + base_path.suffix)
    else:  # mixed
        return base_path.with_name(base_path.stem + "_mixed" + base_path.suffix)
```

### §2. Strategy switch 의 *clean reset*

- *Strategy switch* (e.g. `'lru'` → `'mixed'`) 시 *old file* 의 *delete* 의 *operational* 의 *low-friction*:
  - *Cross-strategy interference* 의 *operational* 의 *prevent*.
  - *Cross-strategy contamination* 의 *operational* 의 *prevent*.

### §3. Backward compat

- *v0.7.41 이전* 의 *single file* (`url_validity_cache.json`) 의 *load* 의 *operational* 의 *low-friction*.
- *v0.7.42+* 의 *first run* 시 *single file* 의 *detect* → *per-strategy file* 의 *migrate* 의 *operational* 의 *low-friction*.
- *Migration* 시 *single file* 의 *delete* 의 *operational* 의 *low-friction* (WARN emitted).

### §4. Cross-strategy compare 의 *operational* 정공법

- *A/B test* 의 *operational* 의 *low-friction*:
  - *Single run* 의 *3 file* 의 *parallel* 의 *compare* 의 *operational* 의 *low-friction*.
  - *Hit rate* 의 *3 strategy* 의 *cross-strategy* 의 *compare*.
- *Operational metric* 의 *per-strategy* 의 *cache_stats()* 의 *3 separate* 의 *return*.

```python
# Pseudo-code (v0.7.42+)
def cache_stats_per_strategy(cache_dir: Path) -> dict[str, dict]:
    """Return per-strategy cache stats."""
    return {
        "lru": cache_stats(cache_file=cache_dir / "url_validity_cache_lru.json"),
        "lfu": cache_stats(cache_file=cache_dir / "url_validity_cache_lfu.json"),
        "mixed": cache_stats(cache_file=cache_dir / "url_validity_cache_mixed.json"),
    }
```

### §5. GHA cache *cross-PR* 의 *operational* 정공법

- *Per-strategy file* 의 *separate* 의 *operational* 의 *low-friction*:
  - *GHA cache key* 의 *per-strategy* 의 *cache* 의 *operational* 의 *low-friction*.
  - *LRU strategy* 의 *miss* 가 *LFU strategy* 의 *hit* 의 *operational* 의 *prevent*.

### §6. *gradual rollout* 의 *operational cadence* (v0.7.42+)

| Phase | scope | version |
|---|---|---|
| **1 (DONE — v0.7.37)** | ADR-014 LRU-only + single file | v0.7.37 |
| **2 (DONE — v0.7.39)** | ADR-021 LFU + mixed strategy (single file) | v0.7.39 |
| **3 (DONE — v0.7.41)** | ADR-021 formal acceptance + per-strategy counters | v0.7.41 |
| **4 (DONE — v0.7.42, 본 release)** | ADR-024 + concept page (formal documentation) | v0.7.42 |
| **5 (v0.7.42+)** | Per-strategy cache file implementation (code-side) | v0.7.42+ |
| **6 (v0.7.43+)** | Cross-strategy compare (cache_stats_per_strategy) | v0.7.43+ |
| **7 (v0.7.44+)** | ADR-024 formal acceptance (1 release 주기 의 운영 evidence 후) | v0.7.44+ |

## Alternatives Considered

### A1. single-file (status quo, ADR-021)
v0.7.41 의 *single file* 의 *mixed strategy* 의 *eviction*. 장점: simplest. 단점: *cross-strategy compare* 의 *operational* 의 *difficulty*. **rejected** — *per-strategy file* 의 *operational* 의 *low-friction* 의 *isolation* 의 *follow-up*.

### A2. per-strategy-file (chosen)
*3 separate file* (`_lru.json` + `_lfu.json` + `_mixed.json`). 장점: *cross-strategy compare* 의 *operational* 의 *low-friction* 의 *isolation* 의 *clean reset*. 단점: *3 file* 의 *operational* 의 *friction* (cache directory 의 *3 file*). **chosen** — *operational* 의 *low-friction* 의 *isolation* 의 *follow-up*.

### A3. hybrid-strategy-prefix
*1 file* 의 *strategy-prefixed key* 의 *mixed*. 장점: *single file* 의 *operational* 의 *low-friction*. 단점: *strategy switch* 의 *operational* 의 *residual* 의 *friction*. **rejected** — *per-strategy file* 의 *isolation* 의 *operational* 의 *low-friction* 의 *follow-up*.

### A4. no-eviction
*size cap* 없음. 장점: 0 implementation. 단점: ADR-014 의 *size cap* 의 *operational* 의 *bounded* 의 *low-friction* 의 *limitation*. **rejected** — ADR-014 의 *size cap* 의 *operational* 의 *bounded* 의 *low-friction* 의 *follow-up*.

### A5. external-cache (e.g. Redis)
*Redis* 의 *distributed cache*. 장점: *cross-process* 의 *shared state*. 단점: *operational* 의 *dependency* (Redis server) + *network* + *complexity*. **rejected** — *operational* 의 *low-friction* 의 *disk-based* 의 *operational* 의 *low-friction* 의 *follow-up*.

## Positive Consequences

- *Per-strategy isolation* 의 *operational* 의 *low-friction* 의 *cross-strategy compare*.
- *Strategy switch* 의 *clean reset* 의 *operational* 의 *low-friction* 의 *residual state* 의 *prevent*.
- *Per-strategy metric* 의 *operational* 의 *low-friction* 의 *observability*.
- *A/B test* 의 *operational* 의 *low-friction* 의 *cross-strategy* 의 *compare*.
- *GHA cache* 의 *per-strategy* 의 *isolation* 의 *operational* 의 *low-friction*.

## Negative Consequences

- *3 file* 의 *operational* 의 *friction* (cache directory 의 *3 file*).
- *Single strategy 사용* 의 *2 unused file* 의 *operational* 의 *low-friction* 의 *minor disk waste*.
- *Migration* 의 *single file* → *3 file* 의 *operational* 의 *friction* (v0.7.42+ 의 *first run*).

## Neutral Consequences

- *GHA cache* 의 *per-strategy key* 의 *operational* 의 *low-friction* 의 *operational* 의 *low-friction* 의 *low-friction* 의 *low-friction* — *flexibility* 의 *operational* 의 *low-friction*.

## Compliance

- ADR-013 (V-R10 v2 cache) — *24h TTL* 의 *cache* 의 *prerequisite*
- ADR-014 (V-R10 v3 cache LRU) — *LRU* 의 *prerequisite* + *per-strategy* 의 *follow-up*
- ADR-021 (cache LFU eviction) — *LFU* 의 *prerequisite* + *per-strategy file* 의 *follow-up*
- ADR-015 (V-R10 v3 file lock) — *lock* 의 *per-strategy* 의 *follow-up* 의 *operational* 의 *low-friction*
- ADR-016 (GHA actions cache) — *cross-PR* 의 *per-strategy* 의 *follow-up* 의 *operational* 의 *low-friction*

## Follow-up

1. **v0.7.42+**: Per-strategy cache file implementation (code-side, *cache_file_for_strategy()* helper)
2. **v0.7.43+**: Cross-strategy compare (`cache_stats_per_strategy()` function)
3. **v0.7.44+**: ADR-024 formal acceptance (1 release 주기 의 운영 evidence 후)
4. **v0.7.45+**: *Per-host* 의 *per-strategy* 의 *follow-up* 의 *operational* 의 *low-friction* (cross-strategy + per-host)

## Revision Log

| Date | Version | Change | Author |
|---|---|---|---|
| 2026-06-16 | 0.1.0 | 초안. ADR-021 (single file) 의 *per-strategy file* follow-up. 5 alternatives (single, per-strategy, hybrid, no-eviction, external). 4 positive / 2 negative / 1 neutral. 6 section + 8 primary sources. 7 phase 의 *gradual rollout*. | Sisyphus (orchestrator) |
