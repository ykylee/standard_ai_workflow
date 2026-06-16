# Beta v0.7.38 — V-R13 formal acceptance + okf-bundle.yaml + cache gzip + lock orphan cleanup + OKF consumer guide (TASK-V0738-FOLLOWUP-BUNDLE)

> **Status**: proposed (TASK-V0738-FOLLOWUP-BUNDLE in-flight)
> 본 release 의 변경. v0.7.37 의 6 follow-up 항목: (1) ADR-019 V-R13 formal acceptance, (2) OKF consumer guide 신규, (3) okf-bundle.yaml per-bundle manifest emit, (4) cache gzip compression, (5) lock file orphan cleanup, (6) log + version bump. cumulative test 380+.

## 본 release 의 1차 출처

1. **ADR-019 V-R13 semantic URL verification** (proposed → **accepted**) — 8 semantic check + 2 layer (`?hash` + `?range`) 의 *convention* 채택
2. **okf-bundle.yaml** (v0.7.38+ 신규) — per-bundle manifest: `vcs_commit` + `vcs_ref` + `integrity_hash` (SHA256) + `page_count` + `generated_at` + `generator`
3. **cache gzip** (ADR-014 v3 follow-up) — uncompressed > 4KB 시 gzip emit, `_load_cache` auto-detect via magic bytes
4. **lock orphan cleanup** (ADR-015 v3 follow-up) — mtime > 24h 인 stale lock file 자동 제거 (process died holding lock 케이스)
5. **OKF consumer guide** (`docs/OKF_CONSUMER_GUIDE.md` 신규) — 외부 consumer 의 12-section 가이드 (write / validate / ingest)
6. **version bump** (v0.7.37 → v0.7.38)

## 발견 (v0.7.37 의 6 follow-up 항목)

### TASK-V0738-FOLLOWUP-BUNDLE: 6 follow-up 항목 (1 ADR formal + 1 doc + 4 code enhancement)

v0.7.37 release 시점의 deferred 6 follow-up 항목의 evidence 가 v0.7.38 release 시점부터 모두 충족:

- **TASK-V0738-V-R13-FORMAL (Phase 1)**: ADR-019 status `proposed` → `accepted`. `accepted_in: v0.7.38` + 4 evidence items (8 check convention + 2 layer convention + okf-bundle.yaml + per-page vcs_commit)
- **TASK-V0738-OKF-CONSUMER-DOCS (Phase 2)**: `docs/OKF_CONSUMER_GUIDE.md` (12 KB) — 외부 consumer 가이드. 13 section (write / validate / ingest / V-R10 / V-R11 / V-R12 / V-R13 / CI / troubleshooting / compliance / related)
- **TASK-V0738-MANIFEST (Phase 3)**: `okf_export.py` `export_wiki_to_okf()` now emits `okf-bundle.yaml`. integrity_hash = SHA256 of all page bytes, sorted by relative path. 2 new tests (manifest emit + escape hatch `emit_manifest=False`).
- **TASK-V0738-CACHE-GZIP (Phase 4)**: `_save_cache` 가 uncompressed > 4KB 시 gzip emit. `_load_cache` magic bytes (1f 8b) auto-detect. 1 new test (roundtrip).
- **TASK-V0738-LOCK-STALE-CLEANUP (Phase 5)**: `_CacheLock(stale_seconds=...)` parameter (default 24h). mtime > stale 시 stale lock file 자동 제거. 1 new test (stale cleanup).
- **TASK-V0738-FINAL (Phase 6)**: 본 release note + version bump + log entry.

**v0.7.38 의 정공법**: 1 ADR formal acceptance + 1 신규 doc + 3 module enhancement + 4 new test + version bump v0.7.37 → v0.7.38.

## 본 release 의 변경

### 1. 1 ADR formal acceptance (TASK-V0738-V-R13-FORMAL)

- `decisions/adr-019-v-r13-semantic-url-verification.md` — status text v0.2.0 + revision log v0.2.0 (4 evidence items)
- `concepts/v-r13-semantic-url-verification.md` — status notice v0.2.0 (active) + revision log v0.2.0

### 2. 1 신규 doc (TASK-V0738-OKF-CONSUMER-DOCS)

- `docs/OKF_CONSUMER_GUIDE.md` (12 KB) — 외부 OKF bundle consumer 가이드. 13 section + 1차 출처 (OKF spec v0.1 + 6 ADR + 4 wiki concept).

### 3. 4 code enhancement (TASK-V0738-MANIFEST + CACHE-GZIP + LOCK-STALE-CLEANUP)

- `workflow_kit/okf_export.py`: `export_wiki_to_okf()` 의 `vcs_commit` + `vcs_ref` + `emit_manifest` parameters + `_write_bundle_manifest()` + `_compute_bundle_integrity_hash()`
- `workflow_kit/url_validity.py`:
  - `_save_cache()`: gzip emit when uncompressed > 4KB
  - `_load_cache()`: gzip magic bytes (1f 8b) auto-detect + decompress
  - `_CacheLock.__init__()`: `stale_seconds` parameter (default 24h)
  - `_CacheLock.__enter__()`: `_maybe_cleanup_stale_lock()` call
  - `_CacheLock._maybe_cleanup_stale_lock()`: mtime check + remove stale file

### 4. 4 new test (cumulative test 380+ → 384+)

- `test_okf_bundle_manifest_emits_v0_7_38` (okf_export, 13 → 15)
- `test_okf_bundle_manifest_skip_emit` (okf_export, 15)
- `test_cache_gzip_compression_roundtrip` (url_validity, 31 → 32)
- `test_file_lock_stale_cleanup` (url_validity, 32)

### 5. version bump (chore)

`workflow_kit/__init__.py` 의 version `v0.7.37-beta` → `v0.7.38-beta`.

## 발견된 cross-cutting lesson (v0.7.38)

- **ADR formal acceptance 의 *bulk + sub-bundle* 정공법**: 1 turn 의 *formal acceptance bundle* (1 ADR + 4 enhancement + 1 doc + 4 test) 의 운영 헌법. v0.7.37 의 5 ADR bulk acceptance 와 *동일 패턴* — *low-friction* 의 *scale* 검증.
- **okf-bundle.yaml 의 *per-bundle manifest* 가 *V-R13 convention* 의 foundation**: ADR-019 의 *convention* (8 check + 2 layer) 의 *machine-readable carrier* 가 *okf-bundle.yaml*. *consumer* 가 *per-bundle* manifest 의 `integrity_hash` + `vcs_commit` 으로 *byte-level integrity* + *commit pinning* 즉시 검증 가능.
- **gzip + magic-byte auto-detect 의 *transparent migration* 정공법**: 4KB threshold + plain JSON fallback (4KB 이하) + magic bytes (1f 8b) auto-detect 로 *read-backward-compat* (이전 cache file 도 load 가능). *on-disk format migration* 의 *low-friction* 패턴.
- **lock orphan cleanup 의 *time-based heuristic* 정공법**: 24h threshold (default) + mtime check. *process-level* flock 의 *kernel-level cleanup* 이 *self-healing* 으로 보완. *crash-safe* 의 *operational rigor*.
- **OKF consumer guide 의 *external readability* 정공법**: 1차 출처 (OKF spec + ADR + wiki) 의 *3-layer citation* 으로 *external consumer* 가 *우리 ADR 의 *rationale* 까지 verify 가능. *operational transparency* 의 *low-friction* 의 *external* 차원.
- **6 follow-up 항목의 *one bundle* 정공법**: 1 ADR acceptance + 1 doc + 4 code enhancement + 4 test + version bump. *release cycle* 의 *efficiency* 가 *individual turn* 의 *operational friction* 의 *function* 이 아니라 *bundled release* 의 *function*.

## Reference (다른 release note)

- v0.7.37 release note (5 ADR acceptance, 본 release 의 *ADR-019 acceptance* + *6 follow-up* 의 1차 출처)
- v0.7.36 release note (2 ADR acceptance + 5 ADR draft)
- v0.7.35 release note (3 ADR acceptance + 2 ADR draft)
- v0.7.34 release note (ADR-006/007/008 accepted + 3 module)
- v0.7.33 release note (ADR-006 채택 + 5 page PoC)

## TASK (본 release)

### TASK-V0738-FOLLOWUP-BUNDLE: 6 follow-up 항목 (1 ADR + 1 doc + 4 code)

- **상태**: in-flight (proposed)
- **commit**: 5 commit (e17609e + a2f8f72 + c3a0f24 + 2e1a541 + 9f622d3) + 1 final (TBD)
- **scope**:
  - Phase 1: ADR-019 formal acceptance (e17609e)
  - Phase 2: OKF consumer guide (a2f8f72)
  - Phase 3: okf-bundle.yaml emit (c3a0f24)
  - Phase 4: cache gzip (2e1a541)
  - Phase 5: lock stale cleanup (9f622d3)
  - Phase 6: release note + version bump + log (TBD)
- **cumulative test**: 380+ → 384+ (4 new test)

### Follow-up (v0.7.39+)

- **TASK-V0739-V-R13-POC**: `check_url_semantic()` PoC — 8 check implementation + 2 layer query param parsing
- **TASK-V0739-OKF-CONSUMER-CI**: 외부 OKF bundle 의 CI integration (auto-import + lint + export roundtrip)
- **TASK-V0740-V-VERSION-V2**: per-page version (V-Version v2) + vendor extension version policy
- **TASK-V0740-CACHE-LFU**: LFU eviction strategy (LRU 의 *frequency* 차원) + mixed LRU+LFU policy
- **TASK-V0741-V-R11-DYNAMIC**: dynamic content audit (Playwright) + phishing keyword list update (PhishTank feed)
- **TASK-V0742-V-R12-INTEGRITY**: SHA256 integrity hash in URL (ADR-019 layer 1 의 *carrier* in URL form)
- **TASK-V0743-R-2-BATCH**: R-2 batch compliance — 5+ page ingest 동시 갱신 + cumulative count warning

## Metric

- v0.7.38 = 5 enhancement commit + 1 final commit = **6 commit**
- 0 신규 module (4 enhancement of existing module)
- 4 신규 test (1 ADR acceptance + 1 doc + 4 code + 4 test)
- 1 ADR formal acceptance (status/accepted_in/related_pages 갱신) = ~13 lines wiki
- 1 신규 doc (OKF consumer guide, 12 KB)
- 1 release note (v0.7.38.md, ~10 KB)
- 누적 test 380+ → **384+** (4 new)
- 33 release 누적 (v0.7.5~v0.7.38)
- 105+ commit code-repo (v0.7.37 까지 105 + 5 = **110+**)
- wheel + sdist 빌드 + gh release + verify (read-only)
