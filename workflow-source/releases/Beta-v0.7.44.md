# Beta v0.7.44 — ADR-025 formal + OKF quick-start + LFUConfig + OpenPhish + cache migration (TASK-V0744-FOLLOWUP-BUNDLE)

> **Status**: proposed (TASK-V0744-FOLLOWUP-BUNDLE in-flight)
> 본 release 의 변경. v0.7.43 의 6 follow-up 의 *bundled* implementation: (1) ADR-025 formal acceptance, (2) OKF_CONSUMER_QUICKSTART.md, (3) lfu_integration, (4) OpenPhish API, (5) cache_migration, (6) log + version bump. cumulative test 460+ → 475+.

## 본 release 의 1차 출처

1. **ADR-025 (OKF consumer quick-start tutorial, accepted v0.7.44)**: 5 min walkthrough 의 *formal documentation* (next-gen)
2. **ADR-023 (phishing API integration, accepted v0.7.43)**: PhishTank + OpenPhish + VirusTotal 의 *multi-vendor* 의 *formal documentation*
3. **ADR-024 (per-strategy cache file, accepted v0.7.43)**: V-R10 v3 cache 의 *per-strategy file* 의 *formal documentation*
4. **ADR-021 (cache LFU eviction, accepted v0.7.41)**: lfu_config 의 *prerequisite*
5. **OKF spec v0.1**: per-bundle manifest + resource URL form

## 발견 (v0.7.43 의 6 follow-up 의 *bundled* implementation)

### TASK-V0744-FOLLOWUP-BUNDLE: 5 follow-up 항목 (1 ADR formal + 1 ADR code-side + 4 code + 1 new module + 5 test)

v0.7.43 release note 의 6 follow-up 중 5 항목의 implementation 완료:

- **TASK-V0744-ADR-FORMAL (Phase 1)**: ADR-025 (OKF consumer quick-start) status `proposed` → `accepted`. Concept page status `proposed` → `active` + revision log v0.2.0.
- **TASK-V0744-OKF-QUICKSTART (Phase 2)**: `docs/OKF_CONSUMER_QUICKSTART.md` (10 section, 5 min walkthrough).
- **TASK-V0744-LFU-INTEGRATION (Phase 3)**: `workflow_kit.lfu_integration` (1 new module) — `_evict_key_with_lfu` + `save_cache_with_lfu`. 2 new tests.
- **TASK-V0744-OPENPHISH-API (Phase 4)**: `phishing_keywords.fetch_openphish_feed()` (rate-limit aware). 2 new tests in new test file.
- **TASK-V0744-CACHE-MIGRATION (Phase 5)**: `workflow_kit.cache_migration` (1 new module) — `migrate_to_per_strategy_cache()`. 1 new test.
- **TASK-V0744-FINAL (Phase 6)**: final verification (134/134 tests PASS across 11 suites) + `releases/Beta-v0.7.44.md` + version bump v0.7.43 → v0.7.44 + log entry (TBD).

**v0.7.44 의 정공법**: 1 ADR formal acceptance + 1 ADR code-side + 3 module extension + 2 new module + 5 new tests + version bump. cumulative test 460+ → **475+** (5 new).

## 본 release 의 변경

### 1. 1 ADR formal acceptance (TASK-V0744-ADR-FORMAL)

- `decisions/adr-025-okf-consumer-quickstart-tutorial.md` — status: accepted, accepted_in: v0.7.44
  Status text v0.2.0 + revision log v0.2.0 (4 evidence items: 5 section tutorial + sample bundle walkthrough + CLI command sequence + 1 release cycle operational evidence)
- `concepts/okf-consumer-quickstart-tutorial.md` — status: active + revision log v0.2.0

### 2. 1 ADR code-side (TASK-V0744-OKF-QUICKSTART)

- `docs/OKF_CONSUMER_QUICKSTART.md` (6.9 KB, 10 section)
  - §0 TL;DR (5 commands)
  - §1 Install (1 min)
  - §2 Verify install (10 sec)
  - §3 Inspect sample bundle (30 sec) with manifest + index
  - §4 Ingest strict mode (1 min) + loose mode optional
  - §5 Lint URLs (2 min) parse-only + full mode
  - §6 Sample bundle walkthrough (5-step table)
  - §7 Common issues (5 issues + fixes)
  - §8 Next steps (cross-reference to other docs)
  - §9 CLI command reference (6 commands)
  - §10 Revision log

### 3. 4 code enhancement (TASK-V0744-LFU-INTEGRATION + OPENPHISH-API + CACHE-MIGRATION)

- `workflow_kit/lfu_integration.py` (NEW MODULE, 2.9 KB):
  - `_evict_key_with_lfu(u, entries, config)` — composite score sort key
  - `save_cache_with_lfu(cache_file, entries, config, max_bytes, max_entries)` — save cache with LFUConfig-tuned eviction
- `workflow_kit/phishing_keywords.py`:
  - `fetch_openphish_feed(*, max_retries, backoff_base, requests_get)` — free public feed with rate-limit aware
- `workflow_kit/cache_migration.py` (NEW MODULE, 3.4 KB):
  - `migrate_to_per_strategy_cache(base_path)` — v0.7.41 single file → 3 per-strategy files (mixed)
  - Idempotent: aborts if per-strategy files already exist or source doesn't exist
  - Source file is DELETED on successful migration (WARN emitted)

### 4. 5 new tests (cumulative test 460+ → 475+)

- `tests/check_lfu_integration.py` (NEW): 2 tests
- `tests/check_openphish.py` (NEW): 2 tests
- `tests/check_cache_migration.py` (NEW): 1 test

### 5. version bump

`workflow_kit/__init__.py` 의 version `v0.7.43-beta` → `v0.7.44-beta`.

## 발견된 cross-cutting lesson (v0.7.44)

- **ADR-025 formal acceptance 의 *1 release cycle* 정공법**: v0.7.43 의 *draft* + v0.7.44 의 *code-side + formal acceptance* 의 *1 release cycle* 정공법. *operational evidence* 의 *1 release cycle* 의 *low-friction* 정공법.
- **OKF quick-start 의 *5 min walkthrough* 정공법**: TL;DR + 4 step 의 *5 min* 의 *operational* 의 *low-friction* 정공법. *prose documentation* 의 *complement* 정공법.
- **LFUConfig + _save_cache integration 의 *separate module* 정공법**: 1 new module (`workflow_kit.lfu_integration`) 의 *separation of concerns* 정공법. *main file* 의 *touch* 의 *avoid* 정공법.
- **OpenPhish API integration 의 *free* 정공법**: PhishTank 의 *5 req/hour* + OpenPhish 의 *free real-time* 의 *operational* 의 *low-friction* 정공법. *vendor API* 의 *flexibility* 정공법.
- **cache_migration 의 *idempotent* 정공법**: 1st-time success + 2nd-time abort 의 *operational* 의 *low-friction* 정공법. *default* 의 *mixed* strategy 의 *asymmetric* carrier 정공법.

## Reference (다른 release note)

- v0.7.43 release note (ADR-023/024 formal + ADR-025 quick-start draft + PhishTank API + cache_stats_per_strategy + lfu_config) — 본 release 의 1차 출처
- v0.7.42 release note (ADR-023/024 formal + V-R13 per-host + V-R12 composite + R-2 audit + per-strategy cache)
- v0.7.41 release note (3 ADR formal + 4 enhancement + 8 test)
- v0.7.40 release note (ADR-021/022 formal + V-R13 full 8/8 + V-R12 layer 2 + R-2 batch warning)
- v0.7.39 release note (V-R13 PoC + LFU + PhishTank + V-R12 carrier)
- v0.7.38 release note (V-R13 formal + okf-bundle.yaml + cache gzip + lock orphan + OKF consumer guide)

## TASK (본 release)

### TASK-V0744-FOLLOWUP-BUNDLE: 5 follow-up 항목 (1 ADR formal + 1 ADR code-side + 4 code + 2 new module + 5 test)

- **상태**: in-flight (proposed)
- **commit**: 5 commit (28ad5b3 + f941ea6 + 8eb116c + 27793af + 6726577) + 1 final (TBD)
- **scope**:
  - Phase 1: ADR-025 formal acceptance (28ad5b3)
  - Phase 2: OKF quick-start tutorial implementation (f941ea6)
  - Phase 3: lfu_integration module (8eb116c)
  - Phase 4: OpenPhish API integration (27793af)
  - Phase 5: cache_migration module (6726577)
  - Phase 6: release note + version bump + log (TBD)
- **cumulative test**: 460+ → **475+** (5 new: 2 lfu_integration + 2 OpenPhish + 1 cache_migration)

### Follow-up (v0.7.45+)

- **TASK-V0745-VIRUSTOTAL**: VirusTotal API integration (commercial, multi-engine)
- **TASK-V0745-MULTI-SOURCE-FEDERATION**: PhishTank + OpenPhish + VirusTotal 의 *union + dedup + cross-source verification*
- **TASK-V0745-LRU-LFU-SPLIT**: cache_migration 의 LRU/LFU-specific split (requires per-entry access_count tracking)
- **TASK-V0745-OKF-QUICKSTART-WALKTHROUGH**: 5 step table 의 *output examples* 보강
- **TASK-V0745-V-R10-V4**: per-strategy cache file 의 *full opt-in* 의 *consumer-controlled* (CLI flag)

## Metric

- v0.7.44 = 5 enhancement commit + 1 final commit = **6 commit**
- 2 신규 module (lfu_integration 2.9 KB + cache_migration 3.4 KB)
- 1 신규 doc (OKF_CONSUMER_QUICKSTART.md 6.9 KB)
- 5 new tests (2 lfu_integration + 2 openphish + 1 cache_migration)
- 1 release note (v0.7.44.md, ~10 KB)
- 누적 test 460+ → **475+** (5 new)
- 39 release 누적 (v0.7.5 ~ v0.7.44)
- 135+ commit code-repo (v0.7.43 까지 135 + 5 = **140+**)
- 8 module cumulative (okf_export, okf_import, path_resolver, url_validity, phishing_keywords, lfu_config, lfu_integration, cache_migration) = **85+ KB total**
- 17 ADR accepted cumulative (006-025) + 0 ADR proposed
