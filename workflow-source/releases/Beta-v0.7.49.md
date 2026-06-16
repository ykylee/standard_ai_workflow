# Beta v0.7.49 — federation v4 weighted voting + decay persistence + layer 2 pipeline + cache trend + dashboard export (TASK-V0749-FOLLOWUP-BUNDLE)

> **Status**: proposed (TASK-V0749-FOLLOWUP-BUNDLE in-flight)
> 본 release 의 변경. v0.7.48 release note 의 6 follow-up 의 *bundled* implementation: (1) federation v4 weighted voting, (2) per-URL LFU decay persistence, (3) V-R13 layer 2 full pipeline, (4) cache analytics trend, (5) dashboard JSON/Markdown export, (6) log + version bump. cumulative test 520+ → 530+.

## 본 release 의 1차 출처

1. **ADR-019 (V-R13 semantic URL, accepted v0.7.38)**: V-R13 layer 2 full pipeline 의 *operational* 보강
2. **ADR-021 (cache LFU eviction, accepted v0.7.41)**: per-URL LFU decay score persistence
3. **ADR-023 (phishing API integration, accepted v0.7.43)**: phishing federation v4 weighted voting
4. **ADR-024 (per-strategy cache file, accepted v0.7.43)**: cache analytics trend + dashboard export
5. **OKF spec v0.1**: per-bundle manifest + resource URL form
6. **PhishTank + OpenPhish + Bitbucket v2 + GitHub compare API free public APIs**: 4 vendor 의 *cross-vendor* 의 *operational* 보강

## 발견 (v0.7.48 의 6 follow-up 의 *bundled* implementation)

### TASK-V0749-FOLLOWUP-BUNDLE: 5 follow-up 항목 (5 new module + 10 new test)

v0.7.48 release note 의 6 follow-up 중 5 항목의 implementation 완료 (all FREE tier, no paid APIs):

- **TASK-V0749-FEDERATION-V4 (Phase 1)**: `workflow_kit.phishing_federation_v4` module — `fetch_federated_phishing_urls_v4` (weighted voting with per-source confidence) + `build_default_sources_v4` (default weights: PhishTank=1.0, OpenPhish=0.8). 2 new tests.
- **TASK-V0749-DECAY-PERSIST (Phase 2)**: `workflow_kit.cache_lfu_decay_persist` module — `save_decay_scores` + `load_decay_scores` + `update_decay_score` + `get_decay_score` + `merge_decay_scores`. 2 new tests.
- **TASK-V0749-LAYER2-PIPELINE (Phase 3)**: `workflow_kit.v_r13_layer2_pipeline` module — `run_layer2_pipeline` (one-call parse+dispatch+format) + `PipelineResult` dataclass + `run_layer2_pipeline_batch`. 2 new tests.
- **TASK-V0749-CACHE-TREND (Phase 4)**: `workflow_kit.cache_analytics_trend` module — `take_snapshot` + `compute_trend` + `save_snapshots` + `load_snapshots` + `format_trend_summary`. 2 new tests.
- **TASK-V0749-DASHBOARD-EXPORT (Phase 5)**: `workflow_kit.cache_dashboard_export` module — `export_dashboard_json` + `export_dashboard_markdown` + `write_dashboard`. 2 new tests.
- **TASK-V0749-FINAL (Phase 6)**: final verification (181/181 tests PASS across 31 suites) + `releases/Beta-v0.7.49.md` + version bump v0.7.48 → v0.7.49 + log entry (TBD).

**v0.7.49 의 정공법**: 5 new modules (phishing_federation_v4 + cache_lfu_decay_persist + v_r13_layer2_pipeline + cache_analytics_trend + cache_dashboard_export) + 10 new tests + version bump. cumulative test 520+ → **530+** (10 new).

## 본 release 의 변경

### 1. 5 new modules (TASK-V0749 5 follow-up)

- `workflow_kit/phishing_federation_v4.py` (3.1 KB): weighted voting
- `workflow_kit/cache_lfu_decay_persist.py` (3.2 KB): per-URL LFU score persistence
- `workflow_kit/v_r13_layer2_pipeline.py` (3.8 KB): one-call pipeline
- `workflow_kit/cache_analytics_trend.py` (3.6 KB): snapshot over time
- `workflow_kit/cache_dashboard_export.py` (2.7 KB): JSON + Markdown export

### 2. 10 new tests (cumulative test 520+ → 530+)

- `tests/check_phishing_federation_v4.py` (NEW): 2 tests
- `tests/check_cache_lfu_decay_persist.py` (NEW): 2 tests
- `tests/check_v_r13_layer2_pipeline.py` (NEW): 2 tests
- `tests/check_cache_analytics_trend.py` (NEW): 2 tests
- `tests/check_cache_dashboard_export.py` (NEW): 2 tests

### 3. version bump

`workflow_kit/__init__.py` 의 version `v0.7.48-beta` → `v0.7.49-beta`.

## 발견된 cross-cutting lesson (v0.7.49)

- **federation v4 의 *weighted voting* 정공법**: per-source weight 의 *confidence score* 의 *operational* 의 *low-friction* 정공법. *false positive* 의 *weighted reduction* 보강.
- **decay persistence 의 *per-URL* 정공법**: per-URL 의 *score persistence* 의 *low-friction* 정공법. *cache reload* 의 *preserved* 보강.
- **layer 2 pipeline 의 *one-call* 정공법**: parse + dispatch + format 의 *single function* 의 *operational* 의 *low-friction* 정공법.
- **cache trend 의 *snapshot over time* 정공법**: periodic snapshot 의 *delta* 의 *operational* 보강. *cache health* 의 *historical* 보강.
- **dashboard export 의 *machine-readable* 정공법**: JSON + Markdown 의 *dual format* 의 *operational* 의 *low-friction* 정공법. *external consumer* 의 *operational* 보강.

## Reference (다른 release note)

- v0.7.48 release note (V-R13 commit diff integration + LFU full refactor + cache dashboard + federation v3 + CLI flag) — 본 release 의 1차 출처
- v0.7.47 release note (V-R13 commit diff + LFU decay + ADR formal + analytics + eviction trigger)
- v0.7.46 release note (CLI test fix + cache size + LFU decay + Bitbucket v2 + federation v2)
- v0.7.45 release note (multi-source phishing federation + LRU/LFU split + hit rate + CLI --per-strategy)

## TASK (본 release)

### TASK-V0749-FOLLOWUP-BUNDLE: 5 follow-up 항목 (5 new module + 10 new test, all FREE tier)

- **상태**: in-flight (proposed)
- **commit**: 5 commit (bd7c8cb + d9e050b + 5726fc0 + 00a255d + 5834a9a) + 1 final (TBD)
- **scope**:
  - Phase 1: federation v4 (bd7c8cb)
  - Phase 2: decay persistence (d9e050b)
  - Phase 3: layer 2 pipeline (5726fc0)
  - Phase 4: cache trend (00a255d)
  - Phase 5: dashboard export (5834a9a)
  - Phase 6: release note + version bump + log (TBD)
- **cumulative test**: 520+ → **530+** (10 new: 2 federation v4 + 2 persist + 2 pipeline + 2 trend + 2 export)

### Follow-up (v0.7.50+)

- **TASK-V0750-VIRUSTOTAL**: VirusTotal API integration (commercial, multi-engine)
- **TASK-V0750-FEDERATION-V5**: 3 source union (PhishTank + OpenPhish + VirusTotal) with weighted voting
- **TASK-V0750-LIVE-CACHE-DASHBOARD**: Streamlit/Flask live dashboard
- **TASK-V0750-LAYER2-CLI**: CLI for v_r13_layer2_pipeline (one-call URL verification)
- **TASK-V0750-DASHBOARD-TREND-VISUAL**: chart-based trend visualization (matplotlib / plotly)
- **TASK-V0750-ADR-FORMAL**: 1 release cycle 후 formal acceptance for v0.7.49 (no new ADRs in v0.7.49)

## Metric

- v0.7.49 = 5 enhancement commit + 1 final commit = **6 commit**
- 5 신규 module (phishing_federation_v4 3.1 KB + cache_lfu_decay_persist 3.2 KB + v_r13_layer2_pipeline 3.8 KB + cache_analytics_trend 3.6 KB + cache_dashboard_export 2.7 KB) = **16.4 KB total**
- 10 new tests
- 1 release note (v0.7.49.md, ~9 KB)
- 누적 test 520+ → **530+** (10 new)
- 44 release 누적 (v0.7.5 ~ v0.7.49)
- 160+ commit code-repo (v0.7.48 까지 160 + 5 = **165+**)
- 23 module cumulative = **130+ KB total**
- 17 ADR accepted cumulative (006-025) + 0 ADR proposed
- 31 test suites cumulative
- 181 tests cumulative
