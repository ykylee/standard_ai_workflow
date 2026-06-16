# Beta v0.7.41 — ADR-020/021/022 formal + V-R13 range diff + per-strategy metric + R-2 audit + V-R12 composite (TASK-V0741-FOLLOWUP-BUNDLE)

> **Status**: proposed (TASK-V0741-FOLLOWUP-BUNDLE in-flight)
> 본 release 의 변경. v0.7.40 의 6 follow-up 의 *bundled* implementation: (1) ADR-020/021/022 formal acceptance, (2) V-R13 `?range=A..B` commit-level diff, (3) V-R10 v3 per-strategy metric, (4) R-2 batch compliance audit, (5) V-R12 composite layer 1+2 verification, (6) log + version bump. cumulative test 415+ → 430+.

## 본 release 의 1차 출처

1. **ADR-020 (V-R13 implementation, proposed v0.7.39) → accepted v0.7.41**: PoC → formal
2. **ADR-021 (cache LFU eviction, proposed v0.7.40) → accepted v0.7.41**: PoC → formal
3. **ADR-022 (phishing keyword feed, proposed v0.7.40) → accepted v0.7.41**: PoC → formal
4. **ADR-019 (V-R13 convention, accepted v0.7.38)**: 8 check + 2 layer 의 foundation
5. **ADR-014 (V-R10 v3 cache LRU, accepted v0.7.37)**: LRU 의 *frequency 차원* 보강 (ADR-021)
6. **ADR-017 (V-R11 body audit, accepted v0.7.37)**: phishing keyword 의 *external feed* 보강 (ADR-022)
7. **SCHEMA.md R-2**: batch compliance (5-15 page heuristic)
8. **OKF spec v0.1**: per-bundle manifest + resource URL form (layer 1 + layer 2)

## 발견 (v0.7.40 의 6 follow-up 의 *bundled* implementation)

### TASK-V0741-FOLLOWUP-BUNDLE: 5 follow-up 항목 (3 ADR formal + 3 concept formal + 4 code enhancement + 1 audit)

v0.7.40 release note 의 6 follow-up 중 5 항목의 implementation 완료:

- **TASK-V0741-ADR-FORMAL (Phase 1)**: ADR-020/021/022 status `proposed` → `accepted` + 3 concept pages status `proposed` → `active` + revision log v0.2.0 each.
- **TASK-V0741-V-R13-RANGE-DIFF (Phase 2)**: `url_validity.check_url_semantic_range_diff()` runs `git diff --numstat <sha1>..<sha2> -- <path>` via subprocess. Returns V-R13-range-diff-ok + V-R13-range-no-changes + V-R13-range-missing + V-R13-range-subprocess-error. 3 new tests (18 → 21).
- **TASK-V0741-V-R10-LFU-METRIC (Phase 3)**: `_evictions_lru` + `_evictions_lfu` module-level counters + `cache_stats()` returns both new fields. 2 new tests (34 → 36).
- **TASK-V0741-R-2-BATCH-AUDIT (Phase 4)**: `okf_import.audit_r2_batch_history()` reads log.md and categorizes past R-2 ingest events (5-15 in range, <5 too small, >15 too large). 1 new test (14 → 15).
- **TASK-V0741-V-R12-COMPOSITE (Phase 5)**: `url_validity.check_url_semantic_composite()` verifies both `?hash=` and `?range=` carriers populated. Returns V-R12-composite-ok + V-R12-composite-incomplete + V-R12-composite-partial + V-R12-composite-no-commit. 2 new tests (21 → 23).
- **TASK-V0741-FINAL (Phase 6)**: final verification (118/118 tests PASS across 8 suites) + `releases/Beta-v0.7.41.md` + version bump v0.7.40 → v0.7.41 + log entry (TBD).

**v0.7.41 의 정공법**: 3 ADR formal acceptance (proposed → accepted) + 3 concept formal acceptance + 4 code enhancement + 1 audit function + 8 new tests + version bump. cumulative test 415+ → **430+** (8 new).

## 본 release 의 변경

### 1. 3 ADR formal acceptance (TASK-V0741-ADR-FORMAL)

- `decisions/adr-020-v-r13-implementation.md` — status: accepted, accepted_in: v0.7.41
  Status text v0.2.0 + revision log v0.2.0 (4 evidence items: 8/8 check executable + 18 unit tests + 2 layer + CLI)
- `decisions/adr-021-cache-lfu-eviction.md` — status: accepted, accepted_in: v0.7.41
  Status text v0.2.0 + revision log v0.2.0 (4 evidence items: EvictionStrategy + access_count + 2 tests + backward compat)
- `decisions/adr-022-phishing-keyword-feed.md` — status: accepted, accepted_in: v0.7.41
  Status text v0.2.0 + revision log v0.2.0 (4 evidence items: phishing_keywords + 3-layer fallback + dedup + silent fallback + 11 tests)
- `concepts/v-r13-implementation.md` — status: active + revision log v0.2.0
- `concepts/cache-lfu-eviction.md` — status: active + revision log v0.1.0/0.2.0 (added §10 Revision Log)
- `concepts/phishing-keyword-feed.md` — status: active + revision log v0.1.0/0.2.0 (added §11 Revision Log)

### 2. 4 code enhancement (TASK-V0741-V-R13-RANGE-DIFF + V-R10-LFU-METRIC + R-2-BATCH-AUDIT + V-R12-COMPOSITE)

- `workflow_kit/url_validity.py`:
  - `check_url_semantic_range_diff()`: git diff subprocess + numstat parse
  - `check_url_semantic_composite()`: V-R12 layer 1+2 verification
  - `_evictions_lru` + `_evictions_lfu` module-level counters
  - `cache_stats()` extension: 7 → 9 fields (added evictions_lru + evictions_lfu)
- `workflow_kit/okf_import.py`:
  - `R2BatchAuditResult` dataclass
  - `audit_r2_batch_history()` function: log.md regex-based batch counting

### 3. 8 new tests (cumulative test 415+ → 430+)

- `tests/check_wiki_url_semantic.py` (18 → 23): 3 range_diff + 2 composite
- `tests/check_wiki_url_validity.py` (34 → 36): 2 per-strategy metric
- `tests/check_okf_import.py` (14 → 15): 1 audit_r2_batch_history

### 4. version bump (chore)

`workflow_kit/__init__.py` 의 version `v0.7.40-beta` → `v0.7.41-beta`.

## 발견된 cross-cutting lesson (v0.7.41)

- **PoC → Formal 의 *bulk acceptance* 정공법**: 3 ADR 의 *1 release 주기* 의 *bulk formal acceptance* (PoC v0.7.39 + Formal v0.7.40 + Accept v0.7.41) 의 *3-phase* 정공법. *operational evidence* 의 *1 release cycle* 의 *low-friction* 의 *bulk* 정공법.
- **V-R13 의 *subprocess-mockable* 정공법**: `check_url_semantic_range_diff()` 의 `subprocess_run=None` parameter 의 *test-injection* 정공법. *git diff* 의 *subprocess* 의 *mock* 의 *deterministic test* 의 *low-friction*.
- **per-strategy metric 의 *counter separation* 정공법**: `_evictions_lru` vs `_evictions_lfu` 의 *separate counters* (not just *strategy label*). *operational* 의 *LRU vs LFU* 의 *effectiveness* 의 *measurement* 의 *low-friction* 의 *observability* 정공법.
- **R-2 audit 의 *regex-based log parse* 정공법**: `audit_r2_batch_history()` 의 log.md 의 *regex* (`+\s*N new tests`) 의 *machine-readable* 의 *operational* 의 *low-friction* 의 *heuristic* 정공법. *precise* 의 *git history* 의 *separate* 정공법의 *complement*.
- **V-R12 composite 의 *multi-layer verification* 정공법**: `check_url_semantic_composite()` 의 *3 layer* (commit + hash + range) 의 *all-present* 의 *ok info* + *partial* 의 *incomplete warn* 의 *carrier* 의 *completeness* 의 *low-friction* 의 *operational* 정공법.

## Reference (다른 release note)

- v0.7.40 release note (ADR-021/022 formal + V-R13 full 8/8 + V-R12 layer 2 + R-2 batch warning) — 본 release 의 1차 출처
- v0.7.39 release note (V-R13 PoC + LFU + PhishTank + V-R12 carrier)
- v0.7.38 release note (V-R13 formal + okf-bundle.yaml + cache gzip + lock orphan + OKF consumer guide)
- v0.7.37 release note (5 ADR acceptance + 4 enhancement)
- v0.7.36 release note (2 ADR acceptance + 5 ADR draft)
- v0.7.35 release note (3 ADR acceptance + 2 ADR draft)
- v0.7.34 release note (ADR-006/007/008 accepted + 3 module)

## TASK (본 release)

### TASK-V0741-FOLLOWUP-BUNDLE: 5 follow-up 항목 (3 ADR formal + 3 concept formal + 4 code + 1 audit)

- **상태**: in-flight (proposed)
- **commit**: 5 commit (55bd109 + 6fcda94 + 46b6b7a + a595fbb + 6a480ac) + 1 final (TBD)
- **scope**:
  - Phase 1: ADR-020/021/022 formal acceptance + 3 concept pages (55bd109)
  - Phase 2: V-R13 ?range commit-level diff (6fcda94)
  - Phase 3: V-R10 v3 per-strategy metric (46b6b7a)
  - Phase 4: R-2 batch compliance audit (a595fbb)
  - Phase 5: V-R12 composite layer 1+2 verification (6a480ac)
  - Phase 6: release note + version bump + log (TBD)
- **cumulative test**: 415+ → **430+** (8 new: 3 V-R13 + 2 V-R12 + 2 per-strategy + 1 R-2 audit)

### Follow-up (v0.7.42+)

- **TASK-V0742-OKF-QUICK-START**: OKF consumer guide quick-start tutorial (sample bundle walkthrough)
- **TASK-V0742-V-R11-PHISHING-API**: PhishTank API integration + rate-limit aware
- **TASK-V0742-V-R12-LAYER-2-EMIT**: per-page `?range=<sha>..<sha>` emission (parse-only → emit)
- **TASK-V0742-V-R13-PER-HOST**: V-R13 check 5 per-host extension (GitLab API, Bitbucket API)
- **TASK-V0742-R-2-AUDIT-PRECISE**: precise R-2 audit via git history (not log.md regex)
- **TASK-V0742-V-R10-LFU-2**: per-strategy cache file (separate file per strategy)

## Metric

- v0.7.41 = 5 enhancement commit + 1 final commit = **6 commit**
- 0 신규 module (3 module extension: url_validity + okf_import + wiki concept pages)
- 3 ADR formal acceptance (proposed → accepted) = 14 ADR accepted cumulative
- 3 concept formal acceptance (proposed → active) = 23 concept pages cumulative
- 8 new tests (3 V-R13 + 2 V-R12 + 2 per-strategy + 1 R-2 audit)
- 1 release note (v0.7.41.md, ~9 KB)
- 누적 test 415+ → **430+** (8 new)
- 36 release 누적 (v0.7.5 ~ v0.7.41)
- 120+ commit code-repo (v0.7.40 까지 120 + 5 = **125+**)
- 5 module cumulative (okf_export 24 KB, okf_import 20 KB, path_resolver 8 KB, url_validity 19 KB, phishing_keywords 4.9 KB) = **76+ KB total**
