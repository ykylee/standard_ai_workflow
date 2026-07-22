---
type: concept
status: active
last_ingested_from: internal (this page is the rule definition, not ingest of an external source)
r9_skip: true
verification_status: accepted_via_adr-021 (v0.7.41, formal documentation)
created: 2026-06-16
updated: 2026-06-16
---

# Cache LFU eviction — frequency + recency composite (V-R10 v3 follow-up)

## 본 page 의 1차 출처

1. **ADR-021 (cache LFU eviction, proposed v0.7.40)**: 본 page 와 1:1 매핑. *rule definition* + *implementation 정공법*.
2. **ADR-014 (V-R10 v3 cache LRU, accepted v0.7.37)**: 본 concept 의 *prerequisite* (LRU 의 *follow-up* 의 *frequency 차원* 보강).
3. **ADR-013 (V-R10 v2 cache, accepted v0.7.36)**: 24h disk + gzip + lock 의 *prerequisite*.
4. **ADR-015 (V-R10 v3 file lock, accepted v0.7.37)**: access_count update 시 lock 보호의 *prerequisite*.
5. **ADR-016 (GHA actions cache, accepted v0.7.37)**: *cross-PR* 의 *cache state* 의 *access_count* 의 *low-friction*.
6. **V-R10 (URL validity, ADR-010/012/013/014/015)**: cache 의 *prerequisite* layer.

## §1. ADR-021 의 *rule definition*

| # | 항목 | 값 |
|---|---|---|
| 1 | status | **accepted** — ADR-021 와 동시 promote (v0.7.41 formal acceptance, 2026-06-16). 본 concept 의 *rule definition* — *code-side* (v0.7.39 PoC) 의 *formal documentation* (v0.7.40 ADR + v0.7.41 acceptance). |
| 2 | EvictionStrategy | Literal['lru', 'lfu', 'mixed']. default `'mixed'` (LFU primary + LRU tie). |
| 3 | access_count | `CacheEntry.access_count: int = 0`. cache hit 시 increment. |
| 4 | sort key | `(access_count, timestamp)` for `lfu`/`mixed`. `(0, timestamp)` for `lru` (backward compat). |
| 5 | backward compat | v0.7.38 cache file 도 `access_count=0` default 로 load. |

## §2. 3 mode 의 *use case matrix*

| Mode | Sort key | Use case | Default? |
|---|---|---|---|
| `'lru'` | `(0, timestamp)` | v0.7.37 의 LRU-only. *recency* only. backward compat 의 *explicit* 선택. | no |
| `'lfu'` | `(access_count, timestamp)` | *frequency* primary + *recency* tie. high-frequency URL 의 *mid-life retention*. | no |
| `'mixed'` | `(access_count, timestamp)` | *LFU primary + LRU tie* (lfu 와 sort key 동일, 명시적 semantic). v0.7.39+ 의 standard. | **yes** |

## §3. access_count 의 lifecycle

```
+----------------------------------+
|  cache hit (check_url_with_cache)|
+----------------------------------+
              |
              v
+----------------------------------+
|  CacheEntry.url = url            |
|  CacheEntry.timestamp = old     |   <-- frozen dataclass → replace
|  CacheEntry.issues = old         |
|  CacheEntry.access_count = old+1 |
+----------------------------------+
              |
              v
+----------------------------------+
|  _save_cache(cache_file, cache,  |
|    eviction_strategy=mixed)      |
+----------------------------------+
              |
              v
+----------------------------------+
|  size > max_bytes or             |
|  len(entries) > max_entries ?    |
|    yes: _evict_key() sort        |
|         + min() victim           |
|    no: skip                      |
+----------------------------------+
              |
              v
+----------------------------------+
|  _evict_key(u) =                 |
|    (access_count, timestamp)     |   <-- lfu / mixed
|    (0, timestamp)                |   <-- lru (backward compat)
+----------------------------------+
```

## §4. *frequency 차원* 보강의 *operational* 정공법

- *recency-only* (LRU) 의 *limitation*:
  - high-frequency, low-recency URL (e.g. spec.md accessed 100x in 1 hour, then 0x for 23 hours) 의 *mid-life* eviction.
  - cache hit rate 의 *operational* 손해.
- *frequency-primary* (LFU) 의 *limitation*:
  - old high-frequency URL (3 days ago, 1000 hits) 의 *never-evict* → cache 가 *outdated* 상태로 가득 참.
- *composite* (mixed) 의 *low-friction*:
  - `(access_count, timestamp)` sort key.
  - *low access_count* 가 primary sort (low-frequency evict 먼저).
  - *same access_count* 시 *older timestamp* evict (recency tie).
  - *mid-life retention* 의 *cache hit rate* 보강 + *outdated high-frequency* 의 *eviction* 의 *operational* 의 *dual-axis* 의 *low-friction*.

## §5. *gradual rollout* 의 *operational cadence*

| Phase | scope | version |
|---|---|---|
| **1 (DONE — v0.7.37)** | ADR-014 (LRU). cache 의 *recency 차원* 의 *formal documentation*. | v0.7.37 |
| **2 (DONE — v0.7.39 PoC)** | EvictionStrategy literal + access_count field + 3 mode 의 *code-side* implementation + 2 tests. | v0.7.39 |
| **3 (DONE — v0.7.40 formal, 본 page)** | ADR-021 (proposed) + 본 concept page (proposed). 5 alternatives + 4 positive / 2 negative / 1 neutral. *formal documentation* 의 *code-side* 의 *rule-side* 정합. | v0.7.40 |
| **4 (v0.7.40+, 별도 turn)** | ADR-021 formal acceptance (1 release 주기 의 운영 evidence 후). | v0.7.40+ |
| **5 (v0.7.41+)** | per-strategy metric (evictions_lfu / evictions_lru 분리) + LFU threshold tuning. | v0.7.41+ |

## §6. *operational rigor*

- *deterministic* sort key: `(access_count, timestamp)` tuple 의 *Python builtin* 의 *stable sort*.
- *transparent* access_count field: `_save_cache` 의 *JSON* 의 *explicit field* — *machine-readable* 의 *low-friction* 의 *operational* 의 *audit-friendly*.
- *backward compat*: v0.7.38 cache file 도 `access_count=0` default 로 load. *operational* 의 *upgrade* 의 *low-friction*.
- *no CLI flag* — Python API 만. *operational* 의 *low-friction* 의 *boring* 의 default.

## §7. Compliance

- ADR-013 (V-R10 v2 cache) — cache 의 24h disk + gzip + lock + size cap 의 *prerequisite*
- ADR-014 (V-R10 v3 cache LRU) — LRU 의 *follow-up* 의 *frequency 차원* 보강
- ADR-015 (V-R10 v3 file lock) — access_count update 시 lock 보호
- ADR-016 (GHA actions cache) — *cross-PR* 의 *cache state* 의 *access_count* 의 *low-friction*

## §8. Follow-up 후보 (v0.7.41+)

1. **v0.7.41**: per-strategy metric — `evictions_lfu` / `evictions_lru` 분리 (cache_stats() extension)
2. **v0.7.41**: LFU threshold tuning — frequency-weighted + recency-weighted composite (decay factor)
3. **v0.7.42+**: ARC-adaptive 실험 (research-grade) — IBM 의 *Adaptive Replacement Cache*
4. **v0.7.42+**: per-strategy cache file (separate file per strategy) — *operational* 의 *compare* 의 *low-friction*
5. **v0.7.42+**: access_count 의 *temporal decay* — *old access_count* 의 *low weight* 의 *operational* 의 *recency* 의 *frequency* 의 *composite* 의 *low-friction*

## §9. Related

- [decisions/adr-021-cache-lfu-eviction.md](../decisions/adr-021-cache-lfu-eviction.md) — 본 concept 의 *formal documentation*
- [decisions/adr-014-v-r10-v3-cache-lru.md](../decisions/adr-014-v-r10-v3-cache-lru.md) — LRU 의 *prerequisite*
- [decisions/adr-013-v-r10-v2-cache.md](../decisions/adr-013-v-r10-v2-cache.md) — cache 의 *prerequisite*

## §10. Revision Log

| Date | Version | Change | Author |
|---|---|---|---|
| 2026-06-16 | 0.1.0 | 초안. ADR-021 (proposed) 와 동시. 9 section + 6 primary sources. access_count lifecycle + 3 mode + gradual rollout (Phase 1-5). | Sisyphus (orchestrator) |
| 2026-06-16 | 0.2.0 | **v0.7.41 release: status `proposed` → `active` + ADR-021 `proposed` → `accepted`.** 본 release 시점의 evidence (EvictionStrategy literal + access_count field + _save_cache/_load_cache round-trip + check_url_with_cache hit increment + 2 unit tests + v0.7.38 cache load backward compat). `v0.7.41 follow-up bundle` 의 Phase 1 (TASK-V0741-ADR-FORMAL). | Sisyphus (orchestrator) |
