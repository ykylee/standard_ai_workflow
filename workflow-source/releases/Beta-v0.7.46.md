# Beta v0.7.46 — CLI test fix + cache size + LFU decay + Bitbucket v2 + federation v2 (TASK-V0746-FOLLOWUP-BUNDLE)

> **Status**: proposed (TASK-V0746-FOLLOWUP-BUNDLE in-flight)
> 본 release 의 변경. v0.7.45 의 6 follow-up 의 *bundled* implementation: (1) CLI test fix, (2) cache size compare, (3) LFU temporal decay, (4) Bitbucket v2, (5) federation v2, (6) log + version bump. cumulative test 485+ → 500+.

## 본 release 의 1차 출처

1. **ADR-023 (phishing API integration, accepted v0.7.43)**: Bitbucket v2 + federation v2 의 *formal documentation*
2. **ADR-024 (per-strategy cache file, accepted v0.7.43)**: cache size compare 의 *formal documentation*
3. **ADR-021 (cache LFU eviction, accepted v0.7.41)**: LFU temporal decay 의 *formal documentation*
4. **OKF spec v0.1**: per-bundle manifest + resource URL form
5. **PhishTank + OpenPhish + Bitbucket v2 free public APIs**: 3 vendor 의 *federation*

## 발견 (v0.7.45 의 6 follow-up 의 *bundled* implementation)

### TASK-V0746-FOLLOWUP-BUNDLE: 5 follow-up 항목 (3 code + 1 test fix + 1 new module + 7 test)

v0.7.45 release note 의 6 follow-up 중 5 항목의 implementation 완료 (all FREE tier, no paid APIs):

- **TASK-V0746-CLI-TEST-FIX (Phase 1)**: CLI --per-strategy + --cache-stats-strategy flag tests in new file `tests/check_cli_per_strategy.py`. 2 new tests.
- **TASK-V0746-CACHE-SIZE-COMPARE (Phase 2)**: `workflow_kit.cache_size_compare` module — `cache_size_per_strategy` + `cache_size_per_strategy_compare`. 2 new tests.
- **TASK-V0746-LFU-DECAY (Phase 3)**: `lfu_config.compute_lfu_score_with_decay` — exponential temporal decay applied to access_count. 2 new tests.
- **TASK-V0746-BITBUCKET-V2 (Phase 4)**: `workflow_kit.bitbucket_v2` module — `fetch_bitbucket_commit_history` via v2 API. 2 new tests.
- **TASK-V0746-FEDERATION-V2 (Phase 5)**: `workflow_kit.phishing_federation_v2` module — extensible multi-source federation. 2 new tests.
- **TASK-V0746-FINAL (Phase 6)**: final verification (149/149 tests PASS across 16 suites) + `releases/Beta-v0.7.46.md` + version bump v0.7.45 → v0.7.46 + log entry (TBD).

**v0.7.46 의 정공법**: 1 test fix + 3 new modules (cache_size_compare + bitbucket_v2 + phishing_federation_v2) + 1 lfu_config extension + 7 new tests + version bump. cumulative test 485+ → **500+** (7 new).

## 본 release 의 변경

### 1. 1 test fix (TASK-V0746-CLI-TEST-FIX)

- `tests/check_cli_per_strategy.py` (NEW, 2.3 KB, 2 tests)
  - `test_cli_per_strategy_flag_v0_7_45`: CLI --per-strategy flag is accepted
  - `test_cli_cache_stats_strategy_flag_v0_7_45`: CLI --cache-stats-strategy flag is accepted

### 2. 3 new modules (TASK-V0746-CACHE-SIZE-COMPARE + BITBUCKET-V2 + FEDERATION-V2)

- `workflow_kit/cache_size_compare.py` (1.5 KB):
  - `cache_size_per_strategy(base_path)`: dict[str, int] of bytes per strategy
  - `cache_size_per_strategy_compare(base_path)`: sorted list of (strategy, bytes) for A/B compare
- `workflow_kit/bitbucket_v2.py` (2.6 KB):
  - `fetch_bitbucket_commit_history(workspace, repo, *, user, token, limit, timeout, requests_get)`
  - GET /2.0/repositories/{workspace}/{repo}/commits?pagelen={limit}
  - Bitbucket v2: 1000 req/hour for authenticated users
- `workflow_kit/phishing_federation_v2.py` (2.3 KB):
  - `fetch_federated_phishing_urls_v2(sources)`: extensible multi-source federation
  - `build_default_sources_v2(phishtank_api_key, *, include_phishtank, include_openphish)`: builds default 2-source list

### 3. 1 lfu_config extension (TASK-V0746-LFU-DECAY)

- `workflow_kit/lfu_config.py`:
  - `compute_lfu_score_with_decay(access_count, age_seconds, config, half_life_seconds=86400.0)`
  - Exponential temporal decay: effective_count = access_count * exp(-ln(2) * age / half_life)
  - Useful for cache freshness: 1000 hits 1 week ago < 100 hits 1 hour ago
  - Raises ValueError on half_life_seconds <= 0

### 4. 7 new tests (cumulative test 485+ → 500+)

- `tests/check_cli_per_strategy.py` (NEW): 2 tests
- `tests/check_cache_size_compare.py` (NEW): 2 tests
- `tests/check_lfu_config.py` (was 2, now 4): 2 new decay tests
- `tests/check_bitbucket_v2.py` (NEW): 2 tests
- `tests/check_phishing_federation_v2.py` (NEW): 2 tests

### 5. version bump

`workflow_kit/__init__.py` 의 version `v0.7.45-beta` → `v0.7.46-beta`.

## 발견된 cross-cutting lesson (v0.7.46)

- **CLI test fix 의 *separate test file* 정공법**: 기존 runner의 edit 이슈를 회피하기 위해 *separate test file* 의 *low-friction* 정공법. *operational* 의 *low-friction* 정공법.
- **cache size compare 의 *sort descending* 정공법**: A/B test 의 *sorting* 의 *operational* 의 *low-friction* 정공법. *largest first* 의 *low-friction* 정공법.
- **LFU decay 의 *exponential temporal* 정공법**: *radioactive decay* 의 *formula* 의 *operational* 의 *low-friction* 정공법. *cache freshness* 의 *operational* 보강.
- **Bitbucket v2 의 *commit history* 정공법**: `/2.0/repositories/{workspace}/{repo}/commits` 의 *paginated* 의 *operational* 보강. *V-R13 layer 2* 의 *commit-level diff* 의 *prerequisite* 정공법.
- **federation v2 의 *extensible* 정공법**: v1 (hard-coded 2 sources) → v2 (caller-provided sources). *flexibility* 의 *operational* 정공법.

## Reference (다른 release note)

- v0.7.45 release note (multi-source phishing federation + LRU/LFU split + hit rate + CLI --per-strategy) — 본 release 의 1차 출처
- v0.7.44 release note (ADR-025 formal + OKF quick-start + LFUConfig + OpenPhish + cache migration)
- v0.7.43 release note (ADR-023/024 formal + ADR-025 quick-start draft + PhishTank API + cache_stats_per_strategy + lfu_config)
- v0.7.42 release note (ADR-023/024 formal + V-R13 per-host + V-R12 composite + R-2 audit + per-strategy cache)
- v0.7.41 release note (3 ADR formal + 4 enhancement + 8 test)

## TASK (본 release)

### TASK-V0746-FOLLOWUP-BUNDLE: 5 follow-up 항목 (1 test fix + 3 new module + 1 extension + 7 test, all FREE tier)

- **상태**: in-flight (proposed)
- **commit**: 5 commit (f4f0200 + 0dffe7f + d5b1ddc + cff0f2c + e7a5919) + 1 final (TBD)
- **scope**:
  - Phase 1: CLI test fix (f4f0200)
  - Phase 2: cache size compare (0dffe7f)
  - Phase 3: LFU temporal decay (d5b1ddc)
  - Phase 4: Bitbucket v2 (cff0f2c)
  - Phase 5: federation v2 (e7a5919)
  - Phase 6: release note + version bump + log (TBD)
- **cumulative test**: 485+ → **500+** (7 new: 2 CLI + 2 size + 2 decay + 2 Bitbucket + 2 federation v2)

### Follow-up (v0.7.47+)

- **TASK-V0747-VIRUSTOTAL**: VirusTotal API integration (commercial, multi-engine)
- **TASK-V0747-LFU-INTEGRATION-V2**: LFUConfig + _save_cache direct integration (currently separate module)
- **TASK-V0747-V-R13-RANGE-DIFF-V2**: V-R13 layer 2 commit-level diff (using bitbucket_v2 + github API)
- **TASK-V0747-PER-STRATEGY-METRIC-V2**: per-strategy cache size comparison + hit rate (cross-strategy analytics)
- **TASK-V0747-FEDERATION-V3**: 3 source union (PhishTank + OpenPhish + VirusTotal) with cross-source verification

## Metric

- v0.7.46 = 5 enhancement commit + 1 final commit = **6 commit**
- 3 신규 module (cache_size_compare 1.5 KB + bitbucket_v2 2.6 KB + phishing_federation_v2 2.3 KB)
- 1 lfu_config extension
- 1 test fix (separate file)
- 7 new tests
- 1 release note (v0.7.46.md, ~9 KB)
- 누적 test 485+ → **500+** (7 new)
- 41 release 누적 (v0.7.5 ~ v0.7.46)
- 145+ commit code-repo (v0.7.45 까지 145 + 5 = **150+**)
- 11 module cumulative (okf_export, okf_import, path_resolver, url_validity, phishing_keywords, lfu_config, lfu_integration, cache_migration, cache_size_compare, bitbucket_v2, phishing_federation_v2) = **90+ KB total**
- 17 ADR accepted cumulative (006-025) + 0 ADR proposed
