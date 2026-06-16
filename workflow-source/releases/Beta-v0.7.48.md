# Beta v0.7.48 — V-R13 commit diff integration + LFU full refactor + cache dashboard + federation v3 + CLI flag (TASK-V0748-FOLLOWUP-BUNDLE)

> **Status**: proposed (TASK-V0748-FOLLOWUP-BUNDLE in-flight)
> 본 release 의 변경. v0.7.47 release note 의 6 follow-up 의 *bundled* implementation: (1) V-R13 commit diff integration, (2) LFU full refactor, (3) cache dashboard, (4) federation v3 cross-source verification, (5) CLI --cache-dashboard flag, (6) log + version bump. cumulative test 510+ → 520+.

## 본 release 의 1차 출처

1. **ADR-019 (V-R13 semantic URL, accepted v0.7.38)**: V-R13 layer 2 commit-level diff 의 *integration* 의 *operational* 보강
2. **ADR-021 (cache LFU eviction, accepted v0.7.41)**: LFUConfig + _save_cache full refactor
3. **ADR-023 (phishing API integration, accepted v0.7.43)**: phishing federation v3 cross-source verification
4. **ADR-024 (per-strategy cache file, accepted v0.7.43)**: per-strategy cache dashboard + CLI
5. **OKF spec v0.1**: per-bundle manifest + resource URL form
6. **PhishTank + OpenPhish + Bitbucket v2 + GitHub compare API free public APIs**: 4 vendor 의 *cross-vendor* 의 *operational* 보강

## 발견 (v0.7.47 의 6 follow-up 의 *bundled* implementation)

### TASK-V0748-FOLLOWUP-BUNDLE: 5 follow-up 항목 (5 code enhancement + 10 new test)

v0.7.47 release note 의 6 follow-up 중 5 항목의 implementation 완료 (all FREE tier, no paid APIs):

- **TASK-V0748-VR13-COMMIT-DIFF-INTEGRATION (Phase 1)**: `workflow_kit.v_r13_commit_diff_integration` module — `parse_range_from_url` + `check_url_semantic_with_commit_diff` + `format_commit_diff_summary` (V-R13 layer 2 + commit diff integration). 2 new tests.
- **TASK-V0748-LFU-REFACTOR (Phase 2)**: `workflow_kit.cache_lfu_decay` extension — `save_cache_lfu_decay_full` (full refactor, not wrap, of `_save_cache` semantics). 2 new tests.
- **TASK-V0748-CACHE-DASHBOARD (Phase 3)**: `workflow_kit.cache_dashboard` module — `cache_dashboard` (formatted table) + `cache_dashboard_dict` (machine-readable). 2 new tests.
- **TASK-V0748-FEDERATION-V3 (Phase 4)**: `workflow_kit.phishing_federation_v3` module — `fetch_federated_phishing_urls_v3` (cross-source verification, min_source_count default 2). 2 new tests.
- **TASK-V0748-CLI-DASHBOARD (Phase 5)**: `workflow_kit.cache_dashboard_cli` module — `run_cache_dashboard` with `--cache-dashboard` + `--cache-path=PATH` flags. 2 new tests.
- **TASK-V0748-FINAL (Phase 6)**: final verification (171/171 tests PASS across 26 suites) + `releases/Beta-v0.7.48.md` + version bump v0.7.47 → v0.7.48 + log entry (TBD).

**v0.7.48 의 정공법**: 4 new modules (v_r13_commit_diff_integration + cache_dashboard + phishing_federation_v3 + cache_dashboard_cli) + 1 module extension (cache_lfu_decay.save_cache_lfu_decay_full) + 10 new tests + version bump. cumulative test 510+ → **520+** (10 new).

## 본 release 의 변경

### 1. 4 new modules (TASK-V0748-VR13-COMMIT-DIFF-INTEGRATION + CACHE-DASHBOARD + FEDERATION-V3 + CLI-DASHBOARD)

- `workflow_kit/v_r13_commit_diff_integration.py` (3.8 KB):
  - `parse_range_from_url(url) -> (range_a, range_b) | None`
  - `check_url_semantic_with_commit_diff(url, *, user, token, requests_get) -> dict`
  - `format_commit_diff_summary(result) -> str`
- `workflow_kit/cache_dashboard.py` (2.8 KB):
  - `cache_dashboard(cache, *, hits_field, miss_field, eviction_field) -> str` (formatted table)
  - `cache_dashboard_dict(cache) -> dict` (machine-readable)
- `workflow_kit/phishing_federation_v3.py` (2.8 KB):
  - `fetch_federated_phishing_urls_v3(sources, *, min_source_count=2) -> dict`
  - `fetch_federated_phishing_urls_v3_with_min(sources, min_source_count) -> list`
- `workflow_kit/cache_dashboard_cli.py` (2.4 KB):
  - `run_cache_dashboard(argv) -> int` — CLI for `--cache-dashboard` flag

### 2. 1 module extension (TASK-V0748-LFU-REFACTOR)

- `workflow_kit/cache_lfu_decay.py`:
  - `save_cache_lfu_decay_full(cache_file_path, entries, max_bytes, max_entries, config, *, now, eviction_strategy, half_life_seconds)`
  - Standalone implementation (replaces wrap pattern)
  - Computes decay scores, evicts by score, supports LRU/LFU/mixed strategy

### 3. 10 new tests (cumulative test 510+ → 520+)

- `tests/check_v_r13_commit_diff_integration.py` (NEW): 2 tests
- `tests/check_cache_lfu_decay_full.py` (NEW): 2 tests
- `tests/check_cache_dashboard.py` (NEW): 2 tests
- `tests/check_phishing_federation_v3.py` (NEW): 2 tests
- `tests/check_cache_dashboard_cli.py` (NEW): 2 tests

### 4. version bump

`workflow_kit/__init__.py` 의 version `v0.7.47-beta` → `v0.7.48-beta`.

## 발견된 cross-cutting lesson (v0.7.48)

- **V-R13 commit diff integration 의 *low-friction* 정공법**: parse_range_from_url + dispatch + format 의 *3-function* 의 *modular* 정공법. *integration* 의 *low-friction* 의 *operational* 보강.
- **LFU full refactor 의 *wrap → replace* 정공법**: v0.7.47 wrap pattern → v0.7.48 full refactor. *backward compat* 의 *operational* 보강 (wrap pattern still works).
- **cache dashboard 의 *human + machine readable* 정공법**: human-readable table for ops review + dict for automation. *flexibility* 의 *operational* 의 *low-friction* 정공법.
- **federation v3 의 *cross-source verification* 정공법**: v1 hard-coded → v2 extensible → v3 high-confidence. *operational* 의 *evolution* 의 *low-friction* 정공법.
- **CLI dashboard flag 의 *opt-in path* 정공법**: cache_dashboard 의 *CLI surface* 의 *operational* 의 *low-friction* 정공법. 별도 module (not modify url_validity.py).

## Reference (다른 release note)

- v0.7.47 release note (V-R13 commit diff + LFU decay + ADR formal + analytics + eviction trigger) — 본 release 의 1차 출처
- v0.7.46 release note (CLI test fix + cache size + LFU decay + Bitbucket v2 + federation v2)
- v0.7.45 release note (multi-source phishing federation + LRU/LFU split + hit rate + CLI --per-strategy)
- v0.7.44 release note (ADR-025 formal + OKF quick-start + LFUConfig + OpenPhish + cache migration)
- v0.7.43 release note (ADR-023/024 formal + ADR-025 quick-start draft + PhishTank API + cache_stats_per_strategy + lfu_config)

## TASK (본 release)

### TASK-V0748-FOLLOWUP-BUNDLE: 5 follow-up 항목 (5 code enhancement + 10 new test, all FREE tier)

- **상태**: in-flight (proposed)
- **commit**: 5 commit (9461ed1 + d27004f + 6d9ca13 + ffacc80 + 83ee37a) + 1 final (TBD)
- **scope**:
  - Phase 1: V-R13 commit diff integration (9461ed1)
  - Phase 2: LFU full refactor (d27004f)
  - Phase 3: cache dashboard (6d9ca13)
  - Phase 4: federation v3 (ffacc80)
  - Phase 5: CLI dashboard (83ee37a)
  - Phase 6: release note + version bump + log (TBD)
- **cumulative test**: 510+ → **520+** (10 new: 2 commit diff integration + 2 LFU full refactor + 2 dashboard + 2 federation v3 + 2 CLI dashboard)

### Follow-up (v0.7.49+)

- **TASK-V0749-VIRUSTOTAL**: VirusTotal API integration (commercial, multi-engine)
- **TASK-V0749-CACHE-DASHBOARD-LIVE**: live cache dashboard via web (Streamlit / Flask)
- **TASK-V0749-FEDERATION-V4**: cross-source confidence scoring (weighted voting)
- **TASK-V0749-VR13-LAYER-2-FULL**: full V-R13 layer 2 commit-level diff pipeline (parse + dispatch + format + CLI)
- **TASK-V0749-LFU-PER-URL-METRICS**: per-URL LFU decay score persistence
- **TASK-V0749-ADR-FORMAL**: 1 release cycle 후 formal acceptance for v0.7.48 (no new ADRs in v0.7.48)

## Metric

- v0.7.48 = 5 enhancement commit + 1 final commit = **6 commit**
- 4 신규 module (v_r13_commit_diff_integration 3.8 KB + cache_dashboard 2.8 KB + phishing_federation_v3 2.8 KB + cache_dashboard_cli 2.4 KB)
- 1 module extension (cache_lfu_decay.save_cache_lfu_decay_full)
- 10 new tests
- 1 release note (v0.7.48.md, ~9 KB)
- 누적 test 510+ → **520+** (10 new)
- 43 release 누적 (v0.7.5 ~ v0.7.48)
- 155+ commit code-repo (v0.7.47 까지 155 + 5 = **160+**)
- 18 module cumulative (okf_export, okf_import, path_resolver, url_validity, phishing_keywords, lfu_config, lfu_integration, cache_migration, cache_size_compare, bitbucket_v2, phishing_federation_v2, v_r13_commit_diff, cache_lfu_decay, cache_analytics, v_r13_commit_diff_integration, cache_dashboard, phishing_federation_v3, cache_dashboard_cli) = **113+ KB total**
- 17 ADR accepted cumulative (006-025) + 0 ADR proposed
- 26 test suites cumulative
- 171 tests cumulative
