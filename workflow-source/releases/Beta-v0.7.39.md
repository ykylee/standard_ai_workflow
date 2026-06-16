# Beta v0.7.39 — V-R13 PoC executable + LFU cache + PhishTank feed + V-R12 carrier (TASK-V0739-FOLLOWUP-BUNDLE)

> **Status**: proposed (TASK-V0739-FOLLOWUP-BUNDLE in-flight)
> 본 release 의 변경. v0.7.38 의 6 follow-up 의 *bundled* implementation: (1) ADR-020 V-R13 PoC ADR + concept, (2) `check_url_semantic()` PoC, (3) LFU cache eviction, (4) PhishTank feed module, (5) V-R12 SHA256 in URL carrier, (6) log + version bump. cumulative test 384+ → 405+.

## 본 release 의 1차 출처

1. **ADR-019 (V-R13 semantic URL verification, accepted v0.7.38)** + **ADR-020 (V-R13 PoC implementation, proposed v0.7.39)** — convention 의 executable implementation
2. **ADR-014 (V-R10 v3 cache LRU, accepted v0.7.38)** + ADR-021 follow-up (LFU eviction, ad-hoc) — LFU cache strategy
3. **ADR-017 (V-R11 body audit, accepted v0.7.38)** + ADR-022 follow-up (PhishTank feed, ad-hoc) — external keyword feed
4. **ADR-018 (V-R12 commit-pinned URL, accepted v0.7.38)** + V-R12 carrier — per-page `?hash=sha256:...` URL emission
5. **OKF spec v0.1** (GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md) — per-bundle manifest + resource URL form
6. **concept v-r13-semantic-url-verification + v-r13-implementation** (proposed) — 8 check + 2 layer 의 *rule* + *implementation* 의 정합

## 발견 (v0.7.38 의 6 follow-up 의 *bundled* implementation)

### TASK-V0739-FOLLOWUP-BUNDLE: 5 follow-up 항목 (1 ADR + 1 concept + 4 code enhancement)

v0.7.38 release note 의 6 follow-up 중 5 항목의 implementation 완료 (1 항목은 R-2 batch 로 v0.7.40+):

- **TASK-V0739-V-R13-POC-ADR (Phase 1)**: ADR-020 V-R13 PoC implementation ADR (proposed) + concept v-r13-implementation (proposed) — 8 check 의 PoC strategy + 5 alternatives + 4 positive / 2 negative / 1 neutral + 11 section + 6 primary sources. ADR-019 convention 의 executable 의 *gradual rollout* 의 *PoC 단계* 정공법.
- **TASK-V0739-V-R13-POC-IMPL (Phase 2)**: `url_validity.check_url_semantic()` + `SemanticUrlParts` + `parse_semantic_url()` + `validate_semantic_url()` 신규. 6/8 check executable (commit_sha, content_hash, range, no-content-hash, no-commit-sha, range-not-chronological), 2/8 stub (V-R11 body + GitHub API 위임) with explicit WARN transparency. 2 layer query param parsing.
- **TASK-V0739-LFU-EVICTION (Phase 3)**: `EvictionStrategy = Literal['lru', 'lfu', 'mixed']` (default 'mixed' = LFU primary + LRU tie). `CacheEntry.access_count` field + `_save_cache` 의 `eviction_strategy` parameter + `check_url_with_cache` 의 access_count hit increment.
- **TASK-V0739-PHISHING-FEED (Phase 4)**: `phishing_keywords` module 신규 — `BUNDLED_KEYWORDS` (8 baseline) + `load_phishing_keywords(custom, external_feed)` fallback chain (custom > external > bundled) + case-insensitive dedup + JSONL external feed parser. 11 tests.
- **TASK-V0739-V-R12-CARRIER (Phase 5)**: `okf_export` per-page `?hash=sha256:...` emission. `map_frontmatter_to_okf` 의 `content_hash` kwarg → resource URL 에 `?hash=` append. `export_wiki_page` 의 `content_hash='auto'` mode 가 full page text 의 SHA256 자동 계산. Bug fix: `export_wiki_to_okf` 의 missing `exported += ex` (counter 0).
- **TASK-V0739-FINAL (Phase 6)**: 본 release note + version bump v0.7.38 → v0.7.39 + log entry (TBD commit).

**v0.7.39 의 정공법**: 1 ADR proposed + 1 concept proposed + 4 code enhancement (1 신규 module + 3 module extension) + 4 new test files (28 new tests) + 1 bug fix + version bump. cumulative test 384+ → **405+** (28 new).

## 본 release 의 변경

### 1. 1 ADR proposed (TASK-V0739-V-R13-POC-ADR)

- `decisions/adr-020-v-r13-implementation.md` (8.4 KB) — status: proposed, 5 alternatives (semantic-only, hash-only, range-only, external-service, manual), 4 positive / 2 negative / 1 neutral, 6/8 check executable + 2/8 stub. 1:1 link with concept page.
- `concepts/v-r13-implementation.md` (8.0 KB) — status: proposed, 11 section + 6 primary sources, mode matrix (fast/medium/strict), gradual rollout (Phase 1-4).
- `index.md` — 2 new anchors (v-r13-implementation + adr-020-v-r13-implementation). V-4: 63 → 65 entries.

### 2. 4 code enhancement (TASK-V0739-V-R13-POC-IMPL + LFU + PHISHING + V-R12-CARRIER)

- `workflow_kit/url_validity.py`:
  - `SemanticUrlParts` dataclass (4 fields: commit_sha, content_hash, range_start, range_end)
  - `parse_semantic_url()` — pure parse of 4 layer parts from URL
  - `validate_semantic_url()` — 6/8 check + 5 stub WARN
  - `check_url_semantic()` — main entry point (default fast mode, `perform_head` opt-in)
  - `EvictionStrategy` Literal type
  - `_save_cache()` — `eviction_strategy` parameter + `_evict_key()` helper
  - `_load_cache()` — reads `access_count` (default 0)
  - `CacheEntry.access_count` field
  - `check_url_with_cache()` — `eviction_strategy` parameter + access_count increment on hit
- `workflow_kit/phishing_keywords.py` (4.9 KB 신규 module):
  - `BUNDLED_KEYWORDS` (8 baseline extracted from url_validity)
  - `bundled_keywords()` immutable accessor
  - `load_phishing_keywords(external_feed, custom)` fallback chain with case-insensitive dedup
  - `_load_external_feed()` JSONL parser (malformed lines skipped, missing file = silent fallback)
  - `phishing_feed_update_status()` diagnostic
- `workflow_kit/okf_export.py`:
  - `map_frontmatter_to_okf()` — `content_hash` kwarg → resource URL `?hash=` append
  - `export_wiki_page()` — `content_hash='auto'` mode for full page text SHA256
  - `export_wiki_to_okf()` — `content_hash` kwarg pass-through
  - **Bug fix**: missing `exported += ex` in `export_wiki_to_okf` loop (exported count was always 0)

### 3. 4 new test files (28 new tests)

- `tests/check_wiki_url_semantic.py` (13 tests): parse full/minimal/no-commit/invalid-hash/range/invalid-range, validate all-layers/no-commit-sha/no-content-hash/range-not-chronological, check_url_semantic fast/stub/V-R10-coexist
- `tests/check_phishing_keywords.py` (11 tests): bundled, default load, custom override, external feed, dedup, missing file, malformed lines, status (no feed + existing feed), case-insensitive, empty custom
- `tests/check_okf_export.py` (1 new): `test_okf_resource_content_hash_v0_7_39` — per-page `?hash=sha256:...` emission
- `tests/check_wiki_url_validity.py` (2 new): `test_cache_lfu_eviction_strategy`, `test_cache_lru_still_works_with_strategy_param`

### 4. version bump (chore)

`workflow_kit/__init__.py` 의 version `v0.7.38-beta` → `v0.7.39-beta`.

## 발견된 cross-cutting lesson (v0.7.39)

- **ADR-019 convention 의 *executable* 의 *gradual rollout* 정공법**: Phase 1 (v0.7.38, convention formal) → Phase 2 (v0.7.39, 6/8 check executable PoC) → Phase 3 (v0.7.40+, 8/8 check + 2 layer query param full). *PoC 단계* 의 *low-friction* 정공법 — *convention* 의 *enforcement* 의 *operational* 의 *low-friction*.
- **fallback chain 의 *layered authority* 정공법**: phishing_keywords 의 `custom > external > bundled` 의 *priority* + case-insensitive dedup + silent fallback (missing file, malformed lines). *single source of truth* 의 *multi-source* 의 *robust* 정공법.
- **LFU vs LRU 의 *mixed* 의 *default* 정공법**: EvictionStrategy = Literal['lru', 'lfu', 'mixed'] with default 'mixed' = LFU primary + LRU tie. *access_count* 의 *frequency* 의 *operational cadence* + *timestamp* 의 *recency* 의 *dual-axis* 의 *composite* 의 *default* 의 *low-friction*.
- **V-R12 layer 1 의 *URL-form carrier* 의 *auto-compute* 정공법**: `content_hash='auto'` mode 가 full page text 의 SHA256 자동 계산 → `?hash=sha256:<64hex>` 의 query param. *per-page byte-level integrity* 의 *machine-readable carrier* 의 *opt-in* 의 *low-friction* 정공법.
- **stub 의 *transparency* 정공법**: V-R13 의 check 3, 5 의 *not-implemented* WARN (silent fail 의 *anti-pattern* 회피). *gradual rollout* 의 *operational transparency* 의 *operational rigor*.
- **importlib 의 `sys.modules` 등록의 *bug resilience* 정공법**: `okf_export` 의 lazy import (`from workflow_kit.path_resolver import ...`) 가 `sys.modules['workflow_kit.path_resolver']` 등록 후에 정상 동작. test 의 lambda mock 의 *scope* 의 *low-friction*.

## Reference (다른 release note)

- v0.7.38 release note (V-R13 formal + okf-bundle.yaml + cache gzip + lock orphan + OKF consumer guide) — 본 release 의 1차 출처
- v0.7.37 release note (5 ADR acceptance + 4 enhancement)
- v0.7.36 release note (2 ADR acceptance + 5 ADR draft)
- v0.7.35 release note (3 ADR acceptance + 2 ADR draft)
- v0.7.34 release note (ADR-006/007/008 accepted + 3 module)

## TASK (본 release)

### TASK-V0739-FOLLOWUP-BUNDLE: 5 follow-up 항목 (1 ADR + 1 concept + 4 code)

- **상태**: in-flight (proposed)
- **commit**: 5 commit (ea01e42 + 563ac5c + eab4d2e + e1904fd + dd8c177) + 1 final (TBD)
- **scope**:
  - Phase 1: ADR-020 V-R13 PoC ADR (ea01e42)
  - Phase 2: check_url_semantic() PoC (563ac5c)
  - Phase 3: LFU eviction (eab4d2e)
  - Phase 4: phishing_keywords module (e1904fd)
  - Phase 5: V-R12 carrier (dd8c177)
  - Phase 6: release note + version bump + log (TBD)
- **cumulative test**: 384+ → **405+** (28 new: 13 V-R13 + 11 phishing + 2 LFU + 1 V-R12 + 1 bug fix + 0 from phase 1 wiki + 0 from phase 6 release)

### Follow-up (v0.7.40+)

- **TASK-V0740-V-R13-FULL**: 8/8 check executable (content_type via HEAD, author via GitHub API) + `?range=A..B` commit-level diff
- **TASK-V0740-ADR-020-FORMAL**: ADR-020 status proposed → accepted (PoC 운영 evidence 후)
- **TASK-V0740-V-R12-LAYER-2**: per-page `?range=<sha>..<sha>` emission (V-R12 layer 2 carrier)
- **TASK-V0740-CACHE-LFU-2**: LFU eviction threshold tuning (frequency-weighted + recency-weighted composite)
- **TASK-V0740-PHISHING-FEED-UPDATE**: external feed 의 auto-update mechanism (PhishTank API integration, rate-limit aware)
- **TASK-V0741-R-2-BATCH**: 5-15 page ingest 동시 갱신 + cumulative count warning (R-2 batch compliance)

## Metric

- v0.7.39 = 5 enhancement commit + 1 final commit = **6 commit**
- 1 신규 module (phishing_keywords, 4.9 KB)
- 4 module enhancement (url_validity, okf_export)
- 4 신규 test files (28 new tests)
- 1 bug fix (exported counter)
- 2 신규 wiki pages (ADR-020 + v-r13-implementation)
- 1 release note (v0.7.39.md, ~8 KB)
- 누적 test 384+ → **405+** (28 new)
- 34 release 누적 (v0.7.5 ~ v0.7.39)
- 110+ commit code-repo (v0.7.38 까지 110 + 5 = **115+**)
- 5 module cumulative (okf_export 24 KB, okf_import 19.3 KB, path_resolver 8 KB, url_validity 18 KB, phishing_keywords 4.9 KB) = **74+ KB total**
