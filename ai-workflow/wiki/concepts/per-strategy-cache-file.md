---
type: concept
status: proposed
last_ingested_from: internal (this page is the rule definition, not ingest of an external source)
r9_skip: true
verification_status: pending_via_adr-024 (proposed, v0.7.42 draft)
related_pages: [decisions/adr-024-per-strategy-cache-file, decisions/adr-013-v-r10-v2-cache, decisions/adr-014-v-r10-v3-cache-lru, decisions/adr-021-cache-lfu-eviction, decisions/adr-015-v-r10-v3-file-lock, decisions/adr-016-gha-actions-cache, concepts/v-r10-url-validity-lint, patterns/wiki-stub-emit]
created: 2026-06-16
updated: 2026-06-16
---

# Per-strategy cache file — V-R10 v3 cache isolation per eviction strategy (ADR-024, v0.7.42 draft)

## 본 page 의 1차 출처

1. **ADR-024 (per-strategy cache file, proposed v0.7.42)**: 본 page 와 1:1 매핑. *rule definition* + *implementation 정공법*.
2. **ADR-021 (cache LFU eviction, accepted v0.7.41)**: *single file* 의 *prerequisite* + *per-strategy file* 의 *follow-up* 의 *operational* 보강.
3. **ADR-014 (V-R10 v3 cache LRU, accepted v0.7.37)**: *LRU* 의 *prerequisite*.
4. **ADR-013 (V-R10 v2 cache, accepted v0.7.36)**: cache 의 *prerequisite*.
5. **ADR-015 (V-R10 v3 file lock, accepted v0.7.37)**: *lock* 의 *per-strategy* 의 *follow-up*.
6. **ADR-016 (GHA actions cache, accepted v0.7.37)**: *cross-PR* 의 *per-strategy* 의 *follow-up*.
7. **V-R10 (URL validity, ADR-010/012/013/014/015)**: cache 의 *prerequisite* layer.
8. **patterns/wiki-stub-emit**: *stub* 의 *operational* 의 *low-friction* 의 *pattern*.

## §1. ADR-024 의 *rule definition*

| # | 항목 | 값 |
|---|---|---|
| 1 | status | **proposed** — ADR-024 와 동시 (v0.7.42 draft, 2026-06-16). 본 concept 의 *rule definition* — *code-side* (v0.7.42+ 예정) 의 *formal documentation*. |
| 2 | per-strategy file | `_lru.json` + `_lfu.json` + `_mixed.json` (3 separate file). |
| 3 | base path | `~/.workflow_kit/url_validity_cache.json` 의 *stem + suffix* 의 *strategy suffix* 의 *operational* 의 *low-friction* 의 *follow-up*. |
| 4 | strategy switch | *Strategy switch* 시 *old file* 의 *delete* (clean reset). |
| 5 | backward compat | v0.7.41 이전 의 *single file* 의 *detect* → *per-strategy file* 의 *migrate* (WARN). |
| 6 | cross-strategy compare | *A/B test* 의 *operational* 의 *low-friction* 의 *isolation*. |

## §2. Per-strategy file naming matrix

| Strategy | File path | Default? | Use case |
|---|---|---|---|
| `'lru'` | `~/.workflow_kit/url_validity_cache_lru.json` | no (legacy) | v0.7.37+ 의 *LRU-only* 의 *backward compat* |
| `'lfu'` | `~/.workflow_kit/url_validity_cache_lfu.json` | no (explicit) | v0.7.41+ 의 *LFU-only* 의 *operational* 보강 |
| `'mixed'` | `~/.workflow_kit/url_validity_cache_mixed.json` | **yes** (v0.7.42+) | v0.7.42+ 의 *mixed* 의 *default* 의 *operational* 의 *low-friction* |

## §3. *operational* 의 *isolation* 의 *operational* 의 *low-friction*

- *Cross-strategy interference* 의 *operational* 의 *prevent* — *LRU strategy* 의 *eviction* 의 *LFU strategy* 의 *entries* 의 *prevent*.
- *Cross-strategy contamination* 의 *operational* 의 *prevent* — *strategy switch* 의 *residual state* 의 *prevent*.
- *Per-strategy metric* 의 *operational* 의 *low-friction* — *cache_stats()* 의 *3 separate* 의 *return* 의 *observability*.

## §4. *gradual rollout* 의 *operational cadence*

| Phase | scope | version |
|---|---|---|
| **1 (DONE — v0.7.37)** | ADR-014 LRU-only + single file | v0.7.37 |
| **2 (DONE — v0.7.39)** | ADR-021 LFU + mixed strategy (single file) | v0.7.39 |
| **3 (DONE — v0.7.41)** | ADR-021 formal acceptance + per-strategy counters | v0.7.41 |
| **4 (DONE — v0.7.42, 본 page)** | ADR-024 + concept page (formal documentation) | v0.7.42 |
| **5 (v0.7.42+)** | Per-strategy cache file implementation (code-side) | v0.7.42+ |
| **6 (v0.7.43+)** | Cross-strategy compare (`cache_stats_per_strategy()`) | v0.7.43+ |
| **7 (v0.7.44+)** | ADR-024 formal acceptance (1 release 주기 의 운영 evidence 후) | v0.7.44+ |

## §5. *Strategy switch* 의 *clean reset* 의 *operational* 정공법

```python
# Pseudo-code (v0.7.42+)
def switch_strategy(new_strategy: str, cache_dir: Path = DEFAULT_CACHE_DIR) -> None:
    """Switch eviction strategy with clean reset."""
    import sys
    old_strategy = current_strategy()  # get current strategy from global
    if old_strategy != new_strategy:
        # Delete old strategy file
        old_file = cache_file_for_strategy(cache_dir / "url_validity_cache.json", old_strategy)
        if old_file.exists():
            old_file.unlink()
            print(f"WARN: deleted old strategy file: {old_file}", file=sys.stderr)
    # Set new strategy
    set_current_strategy(new_strategy)
```

## §6. *Cross-strategy compare* 의 *operational* 정공법

```python
# Pseudo-code (v0.7.43+)
def cache_stats_per_strategy(cache_dir: Path = DEFAULT_CACHE_DIR) -> dict[str, dict]:
    """Return per-strategy cache stats for A/B comparison."""
    return {
        "lru": cache_stats(cache_file=cache_file_for_strategy(cache_dir / "url_validity_cache.json", "lru")),
        "lfu": cache_stats(cache_file=cache_file_for_strategy(cache_dir / "url_validity_cache.json", "lfu")),
        "mixed": cache_stats(cache_file=cache_file_for_strategy(cache_dir / "url_validity_cache.json", "mixed")),
    }
```

## §7. *Backward compat* 의 *operational* 정공법

- v0.7.41 이전 의 *single file* (`url_validity_cache.json`) 의 *first run* 시 *detect* → *per-strategy file* 의 *migrate*:
  ```python
  # Pseudo-code (v0.7.42+)
  if base_file.exists() and not mixed_file.exists():
      print("WARN: migrating single cache file to per-strategy format", file=sys.stderr)
      # Load single file, save to mixed file
      entries = _load_cache(base_file)
      _save_cache(mixed_file, entries, eviction_strategy="mixed")
      base_file.unlink()
  ```

## §8. *GHA cache* 의 *per-strategy key* 의 *operational* 정공법

```yaml
# .github/workflows/okf-validate.yml (v0.7.42+)
- uses: actions/cache@v4
  with:
    path: ~/.workflow_kit/url_validity_cache_*.json  # glob all per-strategy files
    key: url-validity-cache-${{ strategy }}-${{ hashFiles('**/*.md') }}
```

## §9. *operational rigor*

- *deterministic* file naming: `<stem>_<strategy><suffix>` — *deterministic* 의 *operational* 의 *low-friction*.
- *crash-free* migration: WARN on first run, no data loss.
- *audit-friendly*: per-strategy file 의 *operational* 의 *low-friction* 의 *audit* — *eviction* 의 *strategy* 의 *audit*.
- *GHA cache* 의 *per-strategy key* 의 *operational* 의 *low-friction* 의 *cross-PR* 의 *isolation*.

## §10. Compliance

- ADR-013 (V-R10 v2 cache) — *24h TTL* 의 *cache* 의 *prerequisite*
- ADR-014 (V-R10 v3 cache LRU) — *LRU* 의 *prerequisite*
- ADR-021 (cache LFU eviction) — *LFU* 의 *prerequisite* + *per-strategy file* 의 *follow-up*
- ADR-015 (V-R10 v3 file lock) — *lock* 의 *per-strategy* 의 *follow-up*
- ADR-016 (GHA actions cache) — *cross-PR* 의 *per-strategy* 의 *follow-up*

## §11. Follow-up 후보 (v0.7.42+)

1. **v0.7.42+**: Per-strategy cache file implementation (code-side, `cache_file_for_strategy()` helper)
2. **v0.7.43+**: Cross-strategy compare (`cache_stats_per_strategy()` function)
3. **v0.7.44+**: ADR-024 formal acceptance (1 release 주기 의 운영 evidence 후)
4. **v0.7.45+**: *Per-host* 의 *per-strategy* 의 *follow-up* 의 *operational* 의 *low-friction*

## §12. Related

- [decisions/adr-024-per-strategy-cache-file.md](../decisions/adr-024-per-strategy-cache-file.md) — 본 concept 의 *formal documentation*
- [decisions/adr-021-cache-lfu-eviction.md](../decisions/adr-021-cache-lfu-eviction.md) — *single file* 의 *prerequisite*
- [decisions/adr-014-v-r10-v3-cache-lru.md](../decisions/adr-014-v-r10-v3-cache-lru.md) — *LRU* 의 *prerequisite*

## §13. Revision Log

| Date | Version | Change | Author |
|---|---|---|---|
| 2026-06-16 | 0.1.0 | 초안. ADR-024 (proposed) 와 동시. 13 section + 8 primary sources. 3 strategy 의 *file naming matrix* + strategy switch clean reset + cross-strategy compare + backward compat migration. 7 phase 의 *gradual rollout*. | Sisyphus (orchestrator) |
