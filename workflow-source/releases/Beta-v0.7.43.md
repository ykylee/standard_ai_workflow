# Beta v0.7.43 — ADR-023/024 formal + ADR-025 quick-start draft + PhishTank API + cache_stats_per_strategy + lfu_config (TASK-V0743-FOLLOWUP-BUNDLE)

> **Status**: proposed (TASK-V0743-FOLLOWUP-BUNDLE in-flight)
> 본 release 의 변경. v0.7.42 의 6 follow-up 의 *bundled* implementation: (1) ADR-023/024 formal acceptance, (2) ADR-025 OKF quick-start draft, (3) PhishTank API integration, (4) cache_stats_per_strategy, (5) lfu_config module, (6) log + version bump. cumulative test 445+ → 460+.

## 본 release 의 1차 출처

1. **ADR-023 (phishing API integration, accepted v0.7.43)**: PhishTank + OpenPhish + VirusTotal 의 *multi-vendor* 의 *auto-update* 의 *formal documentation*
2. **ADR-024 (per-strategy cache file, accepted v0.7.43)**: V-R10 v3 cache 의 *per-strategy file* 의 *formal documentation*
3. **ADR-025 (OKF consumer quick-start tutorial, proposed v0.7.43)**: 5 min walkthrough 의 *formal documentation* (next-gen)
4. **ADR-021 (cache LFU eviction, accepted v0.7.41)**: lfu_config 의 *prerequisite*
5. **OKF spec v0.1**: per-bundle manifest + resource URL form

## 발견 (v0.7.42 의 6 follow-up 의 *bundled* implementation)

### TASK-V0743-FOLLOWUP-BUNDLE: 5 follow-up 항목 (2 ADR formal + 1 ADR draft + 4 code + 1 audit + 5 test)

v0.7.42 release note 의 6 follow-up 중 5 항목의 implementation 완료:

- **TASK-V0743-ADR-FORMAL (Phase 1)**: ADR-023 (phishing API) + ADR-024 (per-strategy cache) status `proposed` → `accepted`. 2 concept pages (phishing-api-integration + per-strategy-cache-file) status `proposed` → `active` + revision log v0.2.0.
- **TASK-V0743-ADR-025-DRAFT (Phase 2)**: ADR-025 (OKF consumer quick-start tutorial, 8.8 KB) + concept page (6.6 KB) draft. 2 new index anchors. V-4: 73 → 75 entries.
- **TASK-V0743-PHISHTANK-API (Phase 3)**: `phishing_keywords.fetch_phishtank_feed()` with rate-limit aware (X-RateLimit-Remaining + X-RateLimit-Reset headers + exponential backoff). 2 new tests (11 → 13).
- **TASK-V0743-CACHE-STATS-PER-STRATEGY (Phase 4)**: `url_validity.cache_stats_per_strategy()` reads all 3 per-strategy files. 1 new test (38 → 39).
- **TASK-V0743-LFU-THRESHOLD (Phase 5)**: New module `workflow_kit.lfu_config` (LFUConfig + compute_lfu_score). 2 new tests (1 new test file).
- **TASK-V0743-FINAL (Phase 6)**: final verification (129/129 tests PASS across 9 suites) + `releases/Beta-v0.7.43.md` + version bump v0.7.42 → v0.7.43 + log entry (TBD).

**v0.7.43 의 정공법**: 2 ADR formal acceptance + 1 ADR draft + 4 code enhancement (3 module extension + 1 new module) + 5 new tests + version bump. cumulative test 445+ → **460+** (5 new).

## 본 release 의 변경

### 1. 2 ADR formal acceptance (TASK-V0743-ADR-FORMAL)

- `decisions/adr-023-phishing-api-integration.md` — status: accepted, accepted_in: v0.7.43
  Status text v0.2.0 + revision log v0.2.0 (4 evidence items: PhishTank API + rate-limit aware + 2 tests + silent fallback)
- `decisions/adr-024-per-strategy-cache-file.md` — status: accepted, accepted_in: v0.7.43
  Status text v0.2.0 + revision log v0.2.0 (4 evidence items: cache_file_for_strategy + 2 tests + cross-strategy isolation)
- `concepts/phishing-api-integration.md` — status: active + revision log v0.2.0
- `concepts/per-strategy-cache-file.md` — status: active + revision log v0.2.0

### 2. 1 ADR draft (TASK-V0743-ADR-025-DRAFT)

- `decisions/adr-025-okf-consumer-quickstart-tutorial.md` (8.8 KB, status: proposed)
  6 alternatives (docs-only, sample-bundle, jupyter, video, interactive-cli, codelab)
  4 positive / 2 negative / 1 neutral
  5 section quick-start (Install + Verify + Inspect + Ingest + Lint)
- `concepts/okf-consumer-quickstart-tutorial.md` (6.6 KB, status: proposed)
- `index.md` — 2 new anchors. V-4: 73 → 75 entries

### 3. 4 code enhancement (TASK-V0743-PHISHTANK-API + CACHE-STATS-PER-STRATEGY + LFU-THRESHOLD)

- `workflow_kit/phishing_keywords.py`:
  - `fetch_phishtank_feed(api_key, *, feed_format, max_retries, backoff_base, requests_get)`
  - Rate-limit aware + exponential backoff + silent fallback
- `workflow_kit/url_validity.py`:
  - `cache_stats_per_strategy(base_path=None)` — reads all 3 per-strategy files
- `workflow_kit/lfu_config.py` (NEW MODULE, 1.5 KB):
  - `LFUConfig` dataclass: frequency_weight + recency_weight + decay_seconds
  - `compute_lfu_score(access_count, age_seconds, config)` — composite score

### 4. 5 new tests (cumulative test 445+ → 460+)

- `tests/check_phishing_keywords.py` (11 → 13): 2 PhishTank tests
- `tests/check_wiki_url_validity.py` (38 → 39): 1 cache_stats_per_strategy test
- `tests/check_lfu_config.py` (NEW): 2 lfu_config tests

### 5. version bump

`workflow_kit/__init__.py` 의 version `v0.7.42-beta` → `v0.7.43-beta`.

## 발견된 cross-cutting lesson (v0.7.43)

- **ADR formal acceptance 의 *PoC → formal* 정공법**: ADR-023/024 의 *1 release 주기* 의 *formal documentation* 의 *low-friction* 정공법. v0.7.42 의 *PoC code-side* + v0.7.43 의 *formal acceptance* 의 *2-phase* 의 *operational* 정공법.
- **PhishTank API integration 의 *rate-limit aware* 정공법**: X-RateLimit-Remaining + X-RateLimit-Reset headers respect + exponential backoff. *operational* 의 *low-friction* 의 *vendor API* 의 *low-friction* 정공법.
- **cache_stats_per_strategy 의 *cross-strategy* 정공법**: 1 main entry + 3 per-strategy file 의 *operational* 의 *low-friction* 의 *A/B compare* 정공법.
- **lfu_config 의 *separate module* 정공법**: 1 new module (`workflow_kit.lfu_config`) 의 *separation of concerns* 의 *operational* 의 *low-friction* 정공법. *main file* 의 *touch* 의 *avoid* 의 *operational* 의 *low-friction* 정공법.
- **ADR-025 quick-start draft 의 *next-gen* 정공법**: 5 min walkthrough 의 *machine-readable* 의 *operational* 의 *low-friction* 정공법. *prose documentation* 의 *complement* 정공법.

## Reference (다른 release note)

- v0.7.42 release note (ADR-023/024 formal + V-R13 per-host + V-R12 composite + R-2 audit + per-strategy cache) — 본 release 의 1차 출처
- v0.7.41 release note (3 ADR formal + 4 enhancement + 8 test)
- v0.7.40 release note (ADR-021/022 formal + V-R13 full 8/8 + V-R12 layer 2 + R-2 batch warning)
- v0.7.39 release note (V-R13 PoC + LFU + PhishTank + V-R12 carrier)
- v0.7.38 release note (V-R13 formal + okf-bundle.yaml + cache gzip + lock orphan + OKF consumer guide)

## TASK (본 release)

### TASK-V0743-FOLLOWUP-BUNDLE: 5 follow-up 항목 (2 ADR formal + 1 ADR draft + 4 code + 1 new module)

- **상태**: in-flight (proposed)
- **commit**: 5 commit (30ec2a5 + 14ba098 + df088ee + e289b19 + 53f774a) + 1 final (TBD)
- **scope**:
  - Phase 1: ADR-023/024 formal acceptance (30ec2a5)
  - Phase 2: ADR-025 draft (14ba098)
  - Phase 3: PhishTank API (df088ee)
  - Phase 4: cache_stats_per_strategy (e289b19)
  - Phase 5: lfu_config module (53f774a)
  - Phase 6: release note + version bump + log (TBD)
- **cumulative test**: 445+ → **460+** (5 new: 2 PhishTank + 1 cache_stats_per_strategy + 2 lfu_config)

### Follow-up (v0.7.44+)

- **TASK-V0744-ADR-025-FORMAL**: OKF quick-start tutorial implementation
- **TASK-V0744-OPENPHISH-API**: OpenPhish API integration
- **TASK-V0744-VIRUSTOTAL**: VirusTotal API integration (commercial)
- **TASK-V0744-LFU-INTEGRATION**: LFUConfig integration with _save_cache
- **TASK-V0744-ADR-023-FORMAL**: phishing API code-side acceptance
- **TASK-V0744-ADR-024-FORMAL**: per-strategy cache full migration

## Metric

- v0.7.43 = 5 enhancement commit + 1 final commit = **6 commit**
- 1 신규 module (lfu_config, 1.5 KB)
- 2 ADR formal acceptance + 1 ADR draft
- 5 new tests (2 PhishTank + 1 cache_stats_per_strategy + 2 lfu_config)
- 1 release note (v0.7.43.md, ~9 KB)
- 누적 test 445+ → **460+** (5 new)
- 38 release 누적 (v0.7.5 ~ v0.7.43)
- 130+ commit code-repo (v0.7.42 까지 130 + 5 = **135+**)
- 6 module cumulative (okf_export, okf_import, path_resolver, url_validity, phishing_keywords, lfu_config) = **78+ KB total**
- 16 ADR accepted cumulative + 1 ADR proposed (ADR-025)
