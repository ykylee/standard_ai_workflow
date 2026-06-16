# Beta v0.7.50 — layer 2 CLI + trend ASCII chart + dashboard HTML + federation v5 + decay CSV (TASK-V0750-FOLLOWUP-BUNDLE)

> **Status**: proposed (TASK-V0750-FOLLOWUP-BUNDLE in-flight)
> 본 release 의 변경. v0.7.49 release note 의 6 follow-up 의 *bundled* implementation: (1) layer 2 CLI, (2) trend ASCII chart, (3) dashboard HTML, (4) federation v5 (3 source weighted), (5) decay CSV cross-process, (6) log + version bump. cumulative test 530+ → 540+.

## 본 release 의 1차 출처

1. **ADR-019 (V-R13 semantic URL, accepted v0.7.38)**: V-R13 layer 2 CLI opt-in
2. **ADR-021 (cache LFU eviction, accepted v0.7.41)**: LFU decay CSV cross-process
3. **ADR-023 (phishing API integration, accepted v0.7.43)**: phishing federation v5 (3 source)
4. **ADR-024 (per-strategy cache file, accepted v0.7.43)**: cache trend ASCII chart + dashboard HTML
5. **OKF spec v0.1**: per-bundle manifest + resource URL form
6. **PhishTank + OpenPhish + Bitbucket v2 + GitHub compare API + 3rd source (e.g. URLhaus) free public APIs**: *flexible* 의 *operational* 보강

## 발견 (v0.7.49 의 6 follow-up 의 *bundled* implementation)

### TASK-V0750-FOLLOWUP-BUNDLE: 5 follow-up 항목 (3 new module + 2 module extension + 10 new test)

v0.7.49 release note 의 6 follow-up 중 5 항목의 implementation 완료 (all FREE tier, no paid APIs):

- **TASK-V0750-LAYER2-CLI (Phase 1)**: `workflow_kit.v_r13_layer2_cli` module — `run_layer2_cli` (one-call URL verification with --layer2 URL flag). 2 new tests.
- **TASK-V0750-TREND-CHART (Phase 2)**: `workflow_kit.cache_analytics_trend_chart` module — `render_trend_chart_ascii` (zero-dep ASCII bar chart). 2 new tests.
- **TASK-V0750-DASHBOARD-HTML (Phase 3)**: `cache_dashboard_export` extension — `export_dashboard_html` + `write_dashboard(..., format='html')`. 2 new tests.
- **TASK-V0750-FEDERATION-V5 (Phase 4)**: `workflow_kit.phishing_federation_v5` module — 3 source weighted voting (user-provided 3rd source, FREE-tier friendly). 2 new tests.
- **TASK-V0750-DECAY-CSV (Phase 5)**: `cache_lfu_decay_persist` extension — `export_to_csv` + `import_from_csv` (cross-process spreadsheet-friendly). 2 new tests.
- **TASK-V0750-FINAL (Phase 6)**: final verification (191/191 tests PASS across 36 suites) + `releases/Beta-v0.7.50.md` + version bump v0.7.49 → v0.7.50 + log entry (TBD).

**v0.7.50 의 정공법**: 3 new modules (v_r13_layer2_cli + cache_analytics_trend_chart + phishing_federation_v5) + 2 module extensions (cache_dashboard_export + cache_lfu_decay_persist) + 10 new tests + version bump. cumulative test 530+ → **540+** (10 new).

## 본 release 의 변경

### 1. 3 new modules (TASK-V0750-LAYER2-CLI + TREND-CHART + FEDERATION-V5)

- `workflow_kit/v_r13_layer2_cli.py` (1.9 KB): one-call URL verification CLI
- `workflow_kit/cache_analytics_trend_chart.py` (2.0 KB): zero-dep ASCII bar chart
- `workflow_kit/phishing_federation_v5.py` (4.0 KB): 3 source weighted voting

### 2. 2 module extensions (TASK-V0750-DASHBOARD-HTML + DECAY-CSV)

- `workflow_kit/cache_dashboard_export.py`:
  - `export_dashboard_html(cache) -> str` (NEW, v0.7.50+)
  - `write_dashboard(..., format='html')` (NEW format support)
  - No regression on existing json/markdown
- `workflow_kit/cache_lfu_decay_persist.py`:
  - `export_to_csv(scores, path) -> None` (NEW, v0.7.50+)
  - `import_from_csv(path) -> dict[str, float]` (NEW, v0.7.50+)
  - No regression on existing JSON

### 3. 10 new tests (cumulative test 530+ → 540+)

- `tests/check_v_r13_layer2_cli.py` (NEW): 2 tests
- `tests/check_cache_analytics_trend_chart.py` (NEW): 2 tests
- `tests/check_cache_dashboard_export_html.py` (NEW): 2 tests
- `tests/check_phishing_federation_v5.py` (NEW): 2 tests
- `tests/check_cache_lfu_decay_persist_csv.py` (NEW): 2 tests

### 4. version bump

`workflow_kit/__init__.py` 의 version `v0.7.49-beta` → `v0.7.50-beta`.

## 발견된 cross-cutting lesson (v0.7.50)

- **layer 2 CLI 의 *one-call* 정공법**: v_r13_layer2_pipeline 의 *CLI surface* 의 *low-friction* 정공법. *operational* 의 *simplicity* 보강.
- **ASCII chart 의 *zero-dependency* 정공법**: matplotlib / plotly 의 *dependency* 의 *operational* 보강. text-based 의 *low-friction* 정공법.
- **dashboard HTML 의 *self-contained* 정공법**: external CSS / JS 의 *dependency* 의 *operational* 보강. inline-style 의 *low-friction* 정공법.
- **federation v5 의 *user-provided 3rd source* 정공법**: VirusTotal paid API 의 *commercial* 의 *low-friction* 정공법. *FREE tier* 의 *flexibility* 보강.
- **CSV export/import 의 *spreadsheet-compatible* 정공법**: JSON 의 *operational* 의 *low-friction* 정공법. BI tool / Excel / Google Sheets 의 *operational* 보강.

## Reference (다른 release note)

- v0.7.49 release note (federation v4 + decay persistence + layer 2 pipeline + cache trend + dashboard export) — 본 release 의 1차 출처
- v0.7.48 release note (V-R13 commit diff integration + LFU full refactor + cache dashboard + federation v3 + CLI flag)
- v0.7.47 release note (V-R13 commit diff + LFU decay + ADR formal + analytics + eviction trigger)

## TASK (본 release)

### TASK-V0750-FOLLOWUP-BUNDLE: 5 follow-up 항목 (3 new module + 2 extension + 10 new test, all FREE tier)

- **상태**: in-flight (proposed)
- **commit**: 5 commit (5b6c6f6 + 7e41eaa + 24939df + 5057e77 + 17e9da9) + 1 final (TBD)
- **scope**:
  - Phase 1: layer 2 CLI (5b6c6f6)
  - Phase 2: trend ASCII chart (7e41eaa)
  - Phase 3: dashboard HTML (24939df)
  - Phase 4: federation v5 (5057e77)
  - Phase 5: decay CSV (17e9da9)
  - Phase 6: release note + version bump + log (TBD)
- **cumulative test**: 530+ → **540+** (10 new: 2 layer 2 CLI + 2 trend chart + 2 HTML export + 2 federation v5 + 2 decay CSV)

### Follow-up (v0.7.51+)

- **TASK-V0751-VIRUSTOTAL**: VirusTotal API integration (commercial, multi-engine, opt-in)
- **TASK-V0751-LIVE-CACHE-DASHBOARD**: Streamlit/Flask live dashboard
- **TASK-V0751-CACHE-ANALYTICS-ALERTING**: threshold-based alerting (size, hit_rate, evictions)
- **TASK-V0751-FEDERATION-V6**: 4+ source weighted voting (with VirusTotal)
- **TASK-V0751-DECAY-SCORE-AGING**: automatic decay score aging (decay over time)
- **TASK-V0751-ADR-FORMAL**: 1 release cycle 후 formal acceptance for v0.7.50 (no new ADRs in v0.7.50)

## Metric

- v0.7.50 = 5 enhancement commit + 1 final commit = **6 commit**
- 3 신규 module (v_r13_layer2_cli 1.9 KB + cache_analytics_trend_chart 2.0 KB + phishing_federation_v5 4.0 KB) = **7.9 KB total**
- 2 module extension (cache_dashboard_export HTML + cache_lfu_decay_persist CSV)
- 10 new tests (2/2 PASS each, no regression on existing)
- 1 release note (v0.7.50.md, ~9 KB)
- 누적 test 530+ → **540+** (10 new)
- 45 release 누적 (v0.7.5 ~ v0.7.50)
- 165+ commit code-repo (v0.7.49 까지 165 + 5 = **170+**)
- 26 module cumulative = **140+ KB total**
- 17 ADR accepted cumulative (006-025) + 0 ADR proposed
- 36 test suites cumulative
- 191 tests cumulative
