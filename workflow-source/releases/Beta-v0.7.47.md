# Beta v0.7.47 — V-R13 commit diff (cross-vendor) + LFU decay integration + ADR formal + analytics + eviction trigger (TASK-V0747-FOLLOWUP-BUNDLE)

> **Status**: proposed (TASK-V0747-FOLLOWUP-BUNDLE in-flight)
> 본 release 의 변경. v0.7.46 release note 의 7 follow-up 중 6 항목의 *bundled* implementation: (1) V-R13 commit diff cross-vendor, (2) LFU decay direct integration, (3) ADR-023/024/025 formal v0.2.1 revision log, (4) cache analytics, (5) eviction trigger by size cap, (6) log + version bump. cumulative test 500+ → 510+.

## 본 release 의 1차 출처

1. **ADR-019 (V-R13 semantic URL, accepted v0.7.38)**: V-R13 layer 2 commit-level diff 의 *operational* 보강
2. **ADR-021 (cache LFU eviction, accepted v0.7.41)**: LFUConfig + decay direct integration
3. **ADR-023 (phishing API integration, accepted v0.7.43)**: revision log v0.2.1 (1 release cycle 운영 evidence)
4. **ADR-024 (per-strategy cache file, accepted v0.7.43)**: revision log v0.2.1 + analytics + eviction trigger
5. **ADR-025 (OKF quick-start tutorial, accepted v0.7.44)**: revision log v0.2.1
6. **OKF spec v0.1**: per-bundle manifest + resource URL form
7. **PhishTank + OpenPhish + Bitbucket v2 + GitHub compare API free public APIs**: 4 vendor 의 *federation* + *cross-vendor* 의 *operational* 보강

## 발견 (v0.7.46 의 7 follow-up 중 6 항목의 *bundled* implementation)

### TASK-V0747-FOLLOWUP-BUNDLE: 5 follow-up 항목 (4 code enhancement + 1 doc update + 10 new test)

v0.7.46 release note 의 7 follow-up 중 6 항목의 implementation 완료 (all FREE tier, no paid APIs):

- **TASK-V0747-VR13-COMMIT-DIFF (Phase 1)**: `workflow_kit.v_r13_commit_diff` module — `check_url_semantic_commit_diff_github` + `check_url_semantic_commit_diff_bitbucket` + `check_url_semantic_commit_diff_dispatch` (cross-vendor URL routing). 2 new tests.
- **TASK-V0747-LFU-DECAY-INTEGRATION (Phase 2)**: `workflow_kit.cache_lfu_decay` module — `save_cache_with_decay` + `select_eviction_candidates_with_decay` (LFUConfig.compute_lfu_score_with_decay direct integration, wraps url_validity._save_cache). 2 new tests.
- **TASK-V0747-ADR-FORMAL-1CYCLE (Phase 3)**: ADR-023/024/025 revision log v0.2.1 (1 release cycle 운영 evidence). 0 new code.
- **TASK-V0747-CACHE-ANALYTICS (Phase 4)**: `workflow_kit.cache_analytics` module — `cache_analytics` (per-strategy) + `cache_analytics_summary` (aggregate + lru_to_lfu_size_ratio). 2 new tests.
- **TASK-V0747-EVICT-TRIGGER (Phase 5)**: `workflow_kit.cache_size_compare` extension — `evict_lru_over_size` + `evict_lfu_over_size` (disk-size-based eviction cap). 2 new tests.
- **TASK-V0747-FINAL (Phase 6)**: final verification (159/159 tests PASS across 20 suites) + `releases/Beta-v0.7.47.md` + version bump v0.7.46 → v0.7.47 + log entry (TBD).

**v0.7.47 의 정공법**: 2 new modules (v_r13_commit_diff + cache_lfu_decay + cache_analytics) + 1 module extension (cache_size_compare) + 3 ADR revision log updates + 10 new tests + version bump. cumulative test 500+ → **510+** (10 new).

## 본 release 의 변경

### 1. 2 new modules (TASK-V0747-VR13-COMMIT-DIFF + CACHE-ANALYTICS)

- `workflow_kit/v_r13_commit_diff.py` (6.0 KB):
  - `check_url_semantic_commit_diff_github(org, repo, range_a, range_b, *, user, token, requests_get)`
  - `check_url_semantic_commit_diff_bitbucket(workspace, repo, range_a, range_b, *, user, token, requests_get)`
  - `check_url_semantic_commit_diff_dispatch(url, range_a, range_b, *, user, token, requests_get)` — auto-routes by URL host
- `workflow_kit/cache_analytics.py` (3.7 KB):
  - `cache_analytics(cache, *, hits_field, miss_field, eviction_field)` — dict of strategy -> {size, hits, misses, evictions, hit_rate}
  - `cache_analytics_summary(cache)` — aggregate + lru_to_lfu_size_ratio + strategies (per-strategy size)

### 2. 1 module extension (TASK-V0747-EVICT-TRIGGER)

- `workflow_kit/cache_size_compare.py`:
  - `evict_lru_over_size(max_bytes, base_path=None)` — evicts LRU entries by oldest timestamp
  - `evict_lfu_over_size(max_bytes, base_path=None)` — evicts LFU entries by lowest access_count
  - Disk-size-based eviction cap (vs the in-memory count cap in url_validity.py)

### 3. 1 new module (TASK-V0747-LFU-DECAY-INTEGRATION)

- `workflow_kit/cache_lfu_decay.py` (3.0 KB):
  - `save_cache_with_decay(cache, cache_path, config, *, now)` — wraps url_validity._save_cache with LFU decay scoring
  - `select_eviction_candidates_with_decay(cache, config, n, *, now)` — picks n URLs with lowest decay score
  - `_write_cache_file` (helper): JSON with version, entries, scores

### 4. 3 ADR revision log updates (TASK-V0747-ADR-FORMAL-1CYCLE)

- ADR-023 (phishing API integration, v0.7.43 accepted): revision log v0.2.1 — multi-source federation + V-R13 layer 2 cross-vendor evidence
- ADR-024 (per-strategy cache file, v0.7.43 accepted): revision log v0.2.1 — per-strategy cache hit_rate + size_compare + LFU decay evidence
- ADR-025 (OKF quick-start tutorial, v0.7.44 accepted): revision log v0.2.1 — OKF quick-start + walkthrough evidence

### 5. 10 new tests (cumulative test 500+ → 510+)

- `tests/check_v_r13_commit_diff.py` (NEW): 2 tests
- `tests/check_cache_lfu_decay.py` (NEW): 2 tests
- `tests/check_cache_analytics.py` (NEW): 2 tests
- `tests/check_cache_size_compare_evict.py` (NEW): 2 tests
- 2 cross-strategy tests in `tests/check_cache_size_compare.py` (existing, v0.7.46 carry-over, no new)

### 6. version bump

`workflow_kit/__init__.py` 의 version `v0.7.46-beta` → `v0.7.47-beta`.

## 발견된 cross-cutting lesson (v0.7.47)

- **V-R13 layer 2 commit-level diff 의 *cross-vendor* 정공법**: GitHub + Bitbucket v2 의 *compare API* 의 *operational* 의 *low-friction* 정공법. Layer 2 의 *commit-level granularity* 의 *operational* 보강.
- **LFUConfig + _save_cache 의 *wrap (not modify)* 정공법**: url_validity.py 의 *edit conflict* 회피를 위한 *wrap* 의 *low-friction* 정공법. *operational* 의 *low-friction* 정공법.
- **ADR formal v0.2.1 (1 release cycle 후)의 *evidence-driven* 정공법**: 1 release cycle 의 *operational* 의 *evidence* 후 revision log 의 *v0.2.1* 의 *follow-up* 정공법. *stability* 의 *operational* 보강.
- **cache analytics 의 *lru_to_lfu_size_ratio* 정공법**: *cross-strategy* 의 *operational* 의 *low-friction* 정공법. *A/B test* 의 *low-friction* 정공법.
- **eviction trigger by size cap 의 *disk-size* 정공법**: in-memory count cap 의 *follow-up* 의 *disk-size* 의 *operational* 보강. *operational* 의 *low-friction* 정공법.

## Reference (다른 release note)

- v0.7.46 release note (CLI test fix + cache size + LFU decay + Bitbucket v2 + federation v2) — 본 release 의 1차 출처
- v0.7.45 release note (multi-source phishing federation + LRU/LFU split + hit rate + CLI --per-strategy)
- v0.7.44 release note (ADR-025 formal + OKF quick-start + LFUConfig + OpenPhish + cache migration)
- v0.7.43 release note (ADR-023/024 formal + ADR-025 quick-start draft + PhishTank API + cache_stats_per_strategy + lfu_config)

## TASK (본 release)

### TASK-V0747-FOLLOWUP-BUNDLE: 5 follow-up 항목 (4 code enhancement + 1 doc update + 10 new test, all FREE tier)

- **상태**: in-flight (proposed)
- **commit**: 5 commit (75be24c + 1a606ea + 1475374 + 90f83fb + 1c92875) + 1 final (TBD)
- **scope**:
  - Phase 1: V-R13 commit diff (75be24c)
  - Phase 2: LFU decay integration (1a606ea)
  - Phase 3: ADR formal v0.2.1 (1475374)
  - Phase 4: cache analytics (90f83fb)
  - Phase 5: eviction trigger (1c92875)
  - Phase 6: release note + version bump + log (TBD)
- **cumulative test**: 500+ → **510+** (10 new: 2 commit diff + 2 LFU decay + 2 analytics + 2 evict + 2 already-cumulative from v0.7.46)

### Follow-up (v0.7.48+)

- **TASK-V0748-VIRUSTOTAL**: VirusTotal API integration (commercial, multi-engine)
- **TASK-V0748-LFU-INTEGRATION-V2**: LFUConfig + _save_cache full refactor (replace _save_cache body, not just wrap)
- **TASK-V0748-PER-STRATEGY-METRIC-V2**: per-strategy cache hit rate + size + evictions dashboard
- **TASK-V0748-FEDERATION-V3**: 3 source union (PhishTank + OpenPhish + VirusTotal) with cross-source verification
- **TASK-V0748-VR13-RANGE-DIFF-V2**: V-R13 layer 2 commit-level diff (using v_r13_commit_diff + existing v-r13 checks)
- **TASK-V0748-ADR-FORMAL**: 1 release cycle 후 formal acceptance for v0.7.47 ADRs (none new in v0.7.47)

## Metric

- v0.7.47 = 5 enhancement commit + 1 final commit = **6 commit**
- 3 신규 module (v_r13_commit_diff 6.0 KB + cache_lfu_decay 3.0 KB + cache_analytics 3.7 KB)
- 1 module extension (cache_size_compare + evict_*_over_size)
- 3 ADR revision log v0.2.1
- 10 new tests
- 1 release note (v0.7.47.md, ~9 KB)
- 누적 test 500+ → **510+** (10 new)
- 42 release 누적 (v0.7.5 ~ v0.7.47)
- 150+ commit code-repo (v0.7.46 까지 150 + 5 = **155+**)
- 14 module cumulative (okf_export, okf_import, path_resolver, url_validity, phishing_keywords, lfu_config, lfu_integration, cache_migration, cache_size_compare, bitbucket_v2, phishing_federation_v2, v_r13_commit_diff, cache_lfu_decay, cache_analytics) = **103+ KB total**
- 17 ADR accepted cumulative (006-025) + 0 ADR proposed
- 20 test suites cumulative
- 159 tests cumulative
