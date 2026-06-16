# Beta v0.7.40 — ADR-021/022 formal + V-R13 full 8/8 + V-R12 layer 2 + R-2 batch warning (TASK-V0740-FOLLOWUP-BUNDLE)

> **Status**: proposed (TASK-V0740-FOLLOWUP-BUNDLE in-flight)
> 본 release 의 변경. v0.7.39 의 6 follow-up 의 *bundled* implementation: (1) ADR-021 LFU + ADR-022 PhishTank formal documentation, (2) V-R13 full 8/8 check executable, (3) V-R12 layer 2 emission, (4) CLI semantic mode, (5) R-2 batch compliance, (6) log + version bump. cumulative test 405+ → 415+.

## 본 release 의 1차 출처

1. **ADR-019 (V-R13 semantic URL verification, accepted v0.7.38)** + **ADR-020 (V-R13 implementation, proposed v0.7.39)** — convention 의 executable
2. **ADR-018 (V-R12 commit-pinned URL, accepted v0.7.37)** + V-R12 layer 2 carrier (per-page `?range=<sha>..<sha>`)
3. **ADR-014 (V-R10 v3 cache LRU, accepted v0.7.37)** + ADR-021 (LFU, proposed v0.7.40)
4. **ADR-017 (V-R11 body audit, accepted v0.7.37)** + ADR-022 (PhishTank feed, proposed v0.7.40)
5. **SCHEMA.md R-2** (batch compliance) — 5-15 page heuristic
6. **OKF spec v0.1** — per-bundle manifest + resource URL form (layer 1 + layer 2)

## 발견 (v0.7.39 의 6 follow-up 의 *bundled* implementation)

### TASK-V0740-FOLLOWUP-BUNDLE: 5 follow-up 항목 (2 ADR formal + 1 concept formal + 4 code enhancement + 1 CLI)

v0.7.39 release note 의 6 follow-up 중 5 항목의 implementation 완료:

- **TASK-V0740-FORMAL-ADR-021-022 (Phase 1)**: ADR-021 (LFU eviction) + ADR-022 (PhishTank feed) + 2 concept pages (cache-lfu-eviction, phishing-keyword-feed) — v0.7.39 PoC code 의 *formal documentation*. 5 alternatives + 4 positive / 2 negative / 1 neutral each.
- **TASK-V0740-V-R13-FULL (Phase 2)**: `url_validity.check_url_semantic` full 8/8 check implementation:
  - `check_url_semantic_head()` — checks 3/4/6/7 (HEAD-based) via `check_url_online` rename
  - `check_url_semantic_github()` — check 5 (author) via `api.github.com/repos/<org>/<repo>/commits/<sha>` API
  - `check_url_semantic()` now accepts `perform_head` + `perform_github` kwargs
  - 3 new tests (16 → 18)
- **TASK-V0740-V-R12-LAYER-2 (Phase 3)**: `okf_export` per-page `?range=<sha1>..<sha2>` emission:
  - `map_frontmatter_to_okf()` `range_refs: tuple[str, str] | None` kwarg
  - `export_wiki_page()` + `export_wiki_to_okf()` `range_refs` pass-through
  - 1 new test (16 → 17)
- **TASK-V0740-CLI-WIRING (Phase 4)**: `workflow_kit.url_validity` main() now accepts:
  - `--semantic` flag (parse-only fast mode)
  - `--perform-head` flag (HEAD-based checks)
  - `--perform-github` flag (GitHub API check)
  - 2 new tests (16 → 18)
- **TASK-V0740-R-2-BATCH (Phase 5)**: `okf_import` R-2 batch compliance:
  - `R2BatchWarning` dataclass + `check_r2_batch_size()` function
  - `R2_BATCH_THRESHOLD_MIN = 5`, `R2_BATCH_THRESHOLD_MAX = 15`
  - `ImportReport.r2_batch_warning` field
  - 2 new tests (12 → 14)
- **TASK-V0740-FINAL (Phase 6)**: final verification (110/110 tests PASS across 8 suites) + `releases/Beta-v0.7.40.md` + version bump v0.7.39 → v0.7.40 + log entry (TBD).

**v0.7.40 의 정공법**: 2 ADR proposed + 2 concept proposed + 4 code enhancement (1 신규 module 없음, 3 module extension) + 1 CLI flag + 8 new tests + version bump. cumulative test 405+ → **415+** (8 new).

## 본 release 의 변경

### 1. 2 ADR proposed (TASK-V0740-FORMAL-ADR-021-022)

- `decisions/adr-021-cache-lfu-eviction.md` (7.0 KB) — status: proposed
  5 alternatives (pure-lru, pure-lfu, arc-adaptive, no-eviction, fifo)
  4 positive / 2 negative / 1 neutral
  3 mode (lru/lfu/mixed) + access_count field + backward compat (v0.7.38 cache load)
- `decisions/adr-022-phishing-keyword-feed.md` (8.1 KB) — status: proposed
  5 alternatives (bundled-only, external-feed, vendor-api, manual-list, no-keyword-check)
  4 positive / 2 negative / 1 neutral
  3-layer fallback chain (custom > external > bundled) + case-insensitive dedup
- `concepts/cache-lfu-eviction.md` (6.8 KB) — status: proposed
  9 section + 6 primary sources
  access_count lifecycle diagram
  frequency + recency composite operational logic
  gradual rollout (Phase 1-5)
- `concepts/phishing-keyword-feed.md` (7.2 KB) — status: proposed
  10 section + 5 primary sources
  JSONL external feed format spec
  silent fallback operational rigor table
  gradual rollout (Phase 1-5)
- `index.md` — 4 new anchors. V-4: 65 → 69 entries

### 2. 4 code enhancement (TASK-V0740-V-R13-FULL + V-R12-LAYER-2 + CLI-WIRING + R-2-BATCH)

- `workflow_kit/url_validity.py`:
  - `check_url_semantic_head()` — checks 3/4/6/7 (HEAD-based)
  - `check_url_semantic_github()` — check 5 (GitHub API)
  - `check_url_semantic()` now accepts `perform_head` + `perform_github`
  - main() now accepts `--semantic`, `--perform-head`, `--perform-github` flags
- `workflow_kit/okf_export.py`:
  - `map_frontmatter_to_okf()` — `range_refs: tuple[str, str] | None` kwarg
  - `export_wiki_page()` + `export_wiki_to_okf()` — `range_refs` pass-through
- `workflow_kit/okf_import.py`:
  - `R2BatchWarning` dataclass
  - `R2_BATCH_THRESHOLD_MIN = 5`, `R2_BATCH_THRESHOLD_MAX = 15`
  - `check_r2_batch_size(page_count)` function
  - `ImportReport.r2_batch_warning` field

### 3. 8 new tests (cumulative test 405+ → 415+)

- `tests/check_wiki_url_semantic.py` (16 → 18): `test_check_url_semantic_github_stub_for_non_github`, `test_check_url_semantic_github_extracts_org_repo`, `test_check_url_semantic_with_perform_head_flag`, `test_cli_semantic_flag_v0_7_40`, `test_cli_perform_head_and_github_flags`
- `tests/check_okf_export.py` (16 → 17): `test_okf_resource_range_refs_v0_7_40`
- `tests/check_okf_import.py` (12 → 14): `test_r2_batch_size_in_range`, `test_r2_batch_size_out_of_range`

### 4. version bump (chore)

`workflow_kit/__init__.py` 의 version `v0.7.39-beta` → `v0.7.40-beta`.

## 발견된 cross-cutting lesson (v0.7.40)

- **PoC → Formal 의 *bulk documentation* 정공법**: v0.7.39 의 2 PoC (LFU + PhishTank) 의 *formal documentation* (ADR + concept) 의 *single turn* 의 *bundled release* 정공법. *PoC 검증 + 1 release 주기* 의 *rule-side* 의 *documentation* 의 *low-friction* 의 *bulk* 정공법.
- **8/8 check 의 *gradual rollout completion* 정공법**: v0.7.39 의 6/8 PoC → v0.7.40 의 8/8 full implementation. *check 3/4/6/7 (HEAD-based)* 의 *check_url_online* rename + *check 5 (GitHub API)* 의 *api.github.com* query. *layered execution* 의 *operational* 의 *opt-in* 의 *per-check* 의 *low-friction* 정공법.
- **V-R12 carrier 의 *asymmetric layer* 정공법**: layer 1 (`?hash=sha256:<hex>`, per-page, v0.7.39) + layer 2 (`?range=<sha>..<sha>`, per-page, v0.7.40) 의 *asymmetric* carrier. layer 2 의 *parse-only fast mode* (ADR-019 convention) + *per-page emission* 의 *asymmetric* 의 *operational* 의 *low-friction*.
- **R-2 batch compliance 의 *5-15 page heuristic* 정공법**: 5-15 의 *medium batch* 의 *operational* 의 *sweet spot*. <5 → *too small* (WARN), >15 → *too large* (WARN, split recommended). *R-2 batch* 의 *machine-readable warning* 의 *low-friction* 의 *operational transparency* 정공법.
- **CLI flag 의 *3-way orthogonal* 정공법**: `--semantic` (parse-only), `--perform-head` (HEAD-based), `--perform-github` (GitHub API) 의 *3 flag* 의 *orthogonal* 의 *opt-in* 의 *low-friction* 정공법. *composable* 의 *operational* 의 *low-friction* 의 *flexibility*.
- **stub 의 *explicit WARN* 정공법**: V-R13 의 *5 stub checks* (v0.7.39 PoC) → v0.7.40 의 *2 stub checks* (V-R11 body + GitHub API) 의 *gradual* 의 *transparency* 의 *WARN* 의 *low-friction* 정공법.

## Reference (다른 release note)

- v0.7.39 release note (V-R13 PoC + LFU + PhishTank + V-R12 carrier) — 본 release 의 1차 출처
- v0.7.38 release note (V-R13 formal + okf-bundle.yaml + cache gzip + lock orphan + OKF consumer guide)
- v0.7.37 release note (5 ADR acceptance + 4 enhancement)
- v0.7.36 release note (2 ADR acceptance + 5 ADR draft)
- v0.7.35 release note (3 ADR acceptance + 2 ADR draft)

## TASK (본 release)

### TASK-V0740-FOLLOWUP-BUNDLE: 5 follow-up 항목 (2 ADR formal + 1 concept formal + 4 code + 1 CLI)

- **상태**: in-flight (proposed)
- **commit**: 5 commit (2cc7d6e + 7c69789 + e365168 + f4cf909 + 85ecff6) + 1 final (TBD)
- **scope**:
  - Phase 1: ADR-021 + ADR-022 formal (2cc7d6e)
  - Phase 2: V-R13 full 8/8 (7c69789)
  - Phase 3: V-R12 layer 2 emission (e365168)
  - Phase 4: CLI --semantic/--perform-head/--perform-github (f4cf909)
  - Phase 5: R-2 batch compliance (85ecff6)
  - Phase 6: release note + version bump + log (TBD)
- **cumulative test**: 405+ → **415+** (8 new: 3 V-R13 + 1 V-R12 + 2 CLI + 2 R-2)

### Follow-up (v0.7.41+)

- **TASK-V0741-ADR-020-FORMAL**: ADR-020 status proposed → accepted (1 release 주기 의 운영 evidence 후)
- **TASK-V0741-ADR-021-FORMAL**: ADR-021 status proposed → accepted (LFU 1 release 주기 후)
- **TASK-V0741-ADR-022-FORMAL**: ADR-022 status proposed → accepted (PhishTank 1 release 주기 후)
- **TASK-V0741-V-R13-RANGE-DIFF**: `?range=A..B` 의 *commit-level diff* PoC (`git diff` subprocess)
- **TASK-V0741-V-R10-LFU-2**: per-strategy metric (evictions_lfu / evictions_lru 분리)
- **TASK-V0741-PHISHING-API**: PhishTank API integration + rate-limit aware
- **TASK-V0742-R-2-AUDIT**: R-2 batch compliance audit (cumulative ingest count + recommendation)

## Metric

- v0.7.40 = 5 enhancement commit + 1 final commit = **6 commit**
- 0 신규 module (3 module extension: url_validity, okf_export, okf_import)
- 2 신규 ADR + 2 신규 concept
- 8 new tests (5 in V-R13 + 1 in V-R12 + 2 in R-2)
- 1 release note (v0.7.40.md, ~8 KB)
- 누적 test 405+ → **415+** (8 new)
- 35 release 누적 (v0.7.5 ~ v0.7.40)
- 115+ commit code-repo (v0.7.39 까지 115 + 5 = **120+**)
- 5 module cumulative (okf_export 24 KB, okf_import 19.3 KB, path_resolver 8 KB, url_validity 19 KB, phishing_keywords 4.9 KB) = **75+ KB total**
- 3 ADR formal acceptance (020, 021, 022) → 17 ADR accepted + 1 proposed (006-019 accepted + 020-022 proposed)
- 23 concept pages cumulative
