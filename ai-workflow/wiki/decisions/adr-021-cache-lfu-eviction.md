---
type: decision
status: proposed
adr_id: ADR-021
decided_at: 2026-06-16
alternatives_considered: [pure-lru, pure-lfu, arc-adaptive, no-eviction, fifo]
related_pages: [concepts/cache-lfu-eviction, decisions/adr-013-v-r10-v2-cache, decisions/adr-014-v-r10-v3-cache-lru, decisions/adr-015-v-r10-v3-file-lock, decisions/adr-016-gha-actions-cache, concepts/v-r10-url-validity-lint, patterns/wiki-stub-emit]
created: 2026-06-16
updated: 2026-06-16
r9_skip: true
---

# ADR-021: V-R10 cache LFU eviction strategy (frequency + recency composite)

## Status

**Proposed** (2026-06-16, v0.7.40 formal ADR). 본 ADR 은 ADR-014 (LRU cache cap) 의 *frequency 차원* follow-up + v0.7.39 의 *PoC implementation* 의 *formal documentation*. ADR-014 의 *LRU-only* 의 limitation (frequency-blind) 을 *mixed* strategy 로 보강. v0.7.39 release 시점에 *code-side* 구현 완료 (EvictionStrategy literal + access_count + 2 tests). 본 ADR 은 그 *code-side* 의 *formal documentation* 의 *rule-side*.

본 ADR acceptance 는 v0.7.40 release note + 1 release 주기 의 운영 evidence 후 별도 turn 에서 status `proposed` → `accepted`.

## Context

ADR-014 (v0.7.37, accepted) 의 *LRU-only* eviction 의 *limitation*:
- **LRU (Least Recently Used)**: oldest `timestamp` evict. *recency* 만 고려.
- *Limitation*: high-frequency, low-recency URL (e.g. spec.md accessed 100x in 1 hour, then 0x for 23 hours) 의 *mid-life* eviction. *frequency* 가 무시됨.

본 release (v0.7.39 PoC, v0.7.40 formal):
- `EvictionStrategy = Literal['lru', 'lfu', 'mixed']` (default `'mixed'`)
- `CacheEntry.access_count` field (per-entry hit count)
- `_save_cache` 의 `eviction_strategy` parameter + `_evict_key()` helper
- `check_url_with_cache` 의 access_count hit increment
- 2 tests: `test_cache_lfu_eviction_strategy` (LFU evicts lowest access_count), `test_cache_lru_still_works_with_strategy_param` (backward compat)

본 release (v0.7.40 formal):
- 본 ADR formal documentation
- concept page formalization
- 운영 evidence (v0.7.40 의 1 release 주기 = 1 turn) 후 formal acceptance

## Decision

### §1. EvictionStrategy 의 3 mode

| Mode | Sort key | Use case |
|---|---|---|
| `'lru'` | `(0, timestamp)` | 기존 v0.7.37 의 LRU-only. *recency* only. backward compat. |
| `'lfu'` | `(access_count, timestamp)` | *frequency* primary + *recency* tie. *high-frequency* URL 의 *mid-life retention*. |
| `'mixed'` | `(access_count, timestamp)` | default. v0.7.39+ 의 standard. *frequency* primary + *recency* tie (LFU 와 동일 sort key, 명시적 semantic). |

`_evict_key()` helper:
```python
def _evict_key(u: str) -> tuple:
    e = entries[u]
    if eviction_strategy == "lru":
        return (0, e.timestamp)
    else:  # lfu or mixed
        return (e.access_count, e.timestamp)
```

### §2. access_count 의 lifecycle

- `CacheEntry` 의 immutable field: `access_count: int = 0`
- `check_url_with_cache` 의 cache hit 시 increment:
  ```python
  entry = cache[url]
  cache[url] = CacheEntry(url=entry.url, timestamp=entry.timestamp, issues=entry.issues, access_count=entry.access_count + 1)
  ```
- `_load_cache` 의 backward compat: `int(data.get("access_count", 0))` (이전 cache file 도 load)
- `_save_cache` 의 emit: `"access_count": entry.access_count`

### §3. backward compat

- v0.7.38 (이전 release) 의 cache file 도 `access_count=0` 으로 load 가능.
- `eviction_strategy="mixed"` 의 default 가 v0.7.39+ 이지만, *explicit* `eviction_strategy="lru"` 시 v0.7.38 과 *byte-identical* eviction behavior.
- `check_url_with_cache` 의 signature 에 `eviction_strategy` 가 default `mixed` 로 추가 — 기존 caller 는 영향 없음 (new param).

### §4. 운영 evidence (v0.7.40 release 시점)

- cumulative test 405+ → 405+ (no new test, 2 existing)
- 1 commit (formal documentation 만, code 변경 없음)
- V-1 / V-4 PASS (2 new wiki page + 2 new anchor)
- LRU compatibility test (`test_cache_lru_still_works_with_strategy_param`) 가 *byte-identical* behavior 검증

## Alternatives Considered

### A1. pure-lru (status quo)
v0.7.38 의 LRU-only. 장점: simplest. 단점: *frequency* 무시 → high-frequency, low-recency 의 *mid-life eviction* 의 *operational* 손해. **rejected** — ADR-014 의 *LRU* 의 limitation 의 *follow-up* 의 *low-friction* 의 *frequency* 의 보강.

### A2. pure-lfu
access_count 만. 장점: high-frequency 보존. 단점: *old high-frequency* URL (3 days ago, 1000 hits) 의 *never-evict* → cache 가 *outdated* 상태로 가득 참. **rejected** — *operational* 의 *cache freshness* 의 *stale data* 의 위험.

### A3. arc-adaptive (Adaptive Replacement Cache)
IBM 의 ARC: LRU + LFU 의 *self-tuning* 의 ratio 조정. 장점: 이론적으로 optimal. 단점: 구현 복잡도 + 운영 tuning 필요. **rejected** — *operational* 의 *low-friction* 의 *boring* 의 *default* 의 *low-friction* (LRU + LFU 의 *composite* 의 *simple* 의 default).

### A4. no-eviction
size cap 없음. 장점: 0 implementation. 단점: 10MB cap 의 *exceed* 시 무한 누적. **rejected** — ADR-014 의 size cap 의 *operational* 의 *bounded* 의 *low-friction*.

### A5. fifo (First In First Out)
insertion order 만. 장점: simplest. 단점: *recency* + *frequency* 모두 무시. **rejected** — LRU 의 *recency* 의 *low-friction* 의 *frequency* 의 *operational* 의 보강.

## Positive Consequences

- 1 module (url_validity) 의 EvictionStrategy + access_count 의 *frequency 차원* 보강.
- high-frequency URL 의 *mid-life retention* 의 *operational* 의 *cache hit rate* 의 보강.
- 3 mode 의 *flexibility* (`lru` for backward compat, `lfu` for explicit, `mixed` for default).
- backward compat: v0.7.38 cache file 도 load (`access_count=0` default).
- *composite* sort key (`access_count, timestamp`) 의 *deterministic* + *transparent*.

## Negative Consequences

- *cache size 의 1-2% 증가* (access_count field 추가).
- *read latency 의 minor increase* (cache hit 시 access_count update + re-save).
- *LFU mode* 의 *old high-frequency* 의 *never-evict* 위험 — *mixed* mode default 의 *timestamp tie* 으로 mitigation.
- *GHA cache* 의 *cross-PR* 의 *access_count reset* — 본 환경의 low-friction 의 *operational*.

## Neutral Consequences

- *CLI flag 미추가* — `eviction_strategy` 는 Python API 만. *operational* 의 *low-friction*.
- *metric* 의 *evictions_lfu vs evictions_lru* 분리 미수집 — v0.7.41+ ADR-021 follow-up.
- *per-strategy cache* (separate cache file per strategy) 미수행 — *operational* 의 *single file* 의 *low-friction*.

## Compliance

- ADR-013 (V-R10 v2 cache) — cache 의 24h disk + gzip + lock + size cap 의 *prerequisite*
- ADR-014 (V-R10 v3 cache LRU) — LRU 의 *follow-up* 의 *frequency 차원* 보강
- ADR-015 (V-R10 v3 file lock) — access_count update 시 lock 보호
- ADR-016 (GHA actions cache) — *cross-PR* 의 *cache state* 의 *access_count* 의 *low-friction*

## Follow-up

1. **v0.7.40**: ADR-021 formal acceptance (운영 evidence 후)
2. **v0.7.41+**: per-strategy metric (evictions_lfu / evictions_lru 분리)
3. **v0.7.41+**: LFU threshold tuning (frequency-weighted + recency-weighted composite)
4. **v0.7.42+**: ARC-adaptive 실험 (research-grade)
5. **v0.7.42+**: per-strategy cache file (separate file per strategy)

## Revision Log

| Date | Version | Change | Author |
|---|---|---|---|
| 2026-06-16 | 0.1.0 | 초안. ADR-014 (LRU) 의 *frequency 차원* follow-up. v0.7.39 PoC 의 *formal documentation*. 5 alternatives + 4 positive / 2 negative / 1 neutral. 3 mode (lru/lfu/mixed) + access_count field + backward compat (v0.7.38 cache load). | Sisyphus (orchestrator) |
