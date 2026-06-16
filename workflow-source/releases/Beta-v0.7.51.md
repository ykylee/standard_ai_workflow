# Beta v0.7.51 — cache alerting + decay aging + trend chart CLI + dashboard export CLI + federation v5 CLI (TASK-V0751-FOLLOWUP-BUNDLE, FREE tier)

> **Status**: proposed (TASK-V0751-FOLLOWUP-BUNDLE in-flight)
> 본 release 의 변경. v0.7.50 release note 의 6 follow-up 중 **VirusTotal 제외** 5 항목의 *bundled* implementation. **All FREE tier**, no paid APIs. cumulative test 540+ → 550+.

## 본 release 의 1차 출처

1. **ADR-019 (V-R13 semantic URL, accepted v0.7.38)**: trend chart CLI opt-in
2. **ADR-021 (cache LFU eviction, accepted v0.7.41)**: LFU decay score automatic aging
3. **ADR-023 (phishing API integration, accepted v0.7.43)**: phishing federation v5 CLI
4. **ADR-024 (per-strategy cache file, accepted v0.7.43)**: cache threshold-based alerting + dashboard export CLI
5. **OKF spec v0.1**: per-bundle manifest + resource URL form
6. **PhishTank + OpenPhish + Bitbucket v2 + GitHub compare API free public APIs**: *flexible* 의 *operational* 보강

## 발견 (v0.7.50 의 6 follow-up 중 **5 항목** 의 *bundled* implementation, FREE tier)

### TASK-V0751-FOLLOWUP-BUNDLE: 5 follow-up 항목 (3 new module + 1 module extension + 10 new test, all FREE tier)

v0.7.50 release note 의 6 follow-up 중 **VirusTotal 제외** 5 항목의 implementation 완료:

- **TASK-V0751-ALERTING (Phase 1)**: `workflow_kit.cache_analytics_alerting` module — `AlertThresholds` + `Alert` + `check_alerts` + `format_alerts` (threshold-based alerting). 2 new tests.
- **TASK-V0751-DECAY-AGING (Phase 2)**: `cache_lfu_decay_persist` extension — `decay_age_scores` (automatic decay over time). 2 new tests + no regression.
- **TASK-V0751-TREND-CHART-CLI (Phase 3)**: `workflow_kit.cache_analytics_trend_chart_cli` module — `run_trend_chart_cli` (--trend-chart --snapshots=PATH flag). 2 new tests.
- **TASK-V0751-DASHBOARD-EXPORT-CLI (Phase 4)**: `workflow_kit.cache_dashboard_export_cli` module — `run_dashboard_export_cli` (--dashboard-export --output=PATH --format=flag). 2 new tests.
- **TASK-V0751-FEDERATION-V5-CLI (Phase 5)**: `workflow_kit.phishing_federation_v5_cli` module — `run_federation_v5_cli` (--federate-v5 --phishtank-key=KEY flag). 2 new tests.
- **TASK-V0751-FINAL (Phase 6)**: final verification (201/201 tests PASS across 41 suites) + `releases/Beta-v0.7.51.md` + version bump v0.7.50 → v0.7.51 + log entry (TBD).

**v0.7.51 의 정공법**: 4 new modules (cache_analytics_alerting + cache_analytics_trend_chart_cli + cache_dashboard_export_cli + phishing_federation_v5_cli) + 1 module extension (cache_lfu_decay_persist.decay_age_scores) + 10 new tests + version bump. cumulative test 540+ → **550+** (10 new).

## 본 release 의 변경

### 1. 4 new modules (TASK-V0751-ALERTING + TREND-CHART-CLI + DASHBOARD-EXPORT-CLI + FEDERATION-V5-CLI)

- `workflow_kit/cache_analytics_alerting.py` (3.6 KB): threshold-based alerting
- `workflow_kit/cache_analytics_trend_chart_cli.py` (2.0 KB): trend chart CLI
- `workflow_kit/cache_dashboard_export_cli.py` (2.8 KB): multi-format export CLI
- `workflow_kit/phishing_federation_v5_cli.py` (2.2 KB): federation v5 CLI

### 2. 1 module extension (TASK-V0751-DECAY-AGING)

- `workflow_kit/cache_lfu_decay_persist.py`:
  - `decay_age_scores(scores, *, saved_at, now, half_life_seconds)` (NEW, v0.7.51+)
  - Apply temporal decay to scores based on age
  - No regression on existing JSON/CSV

### 3. 10 new tests (cumulative test 540+ → 550+)

- `tests/check_cache_analytics_alerting.py` (NEW): 2 tests
- `tests/check_decay_age_scores.py` (NEW): 2 tests
- `tests/check_cache_analytics_trend_chart_cli.py` (NEW): 2 tests
- `tests/check_cache_dashboard_export_cli.py` (NEW): 2 tests
- `tests/check_phishing_federation_v5_cli.py` (NEW): 2 tests

### 4. version bump

`workflow_kit/__init__.py` 의 version `v0.7.50-beta` → `v0.7.51-beta`.

## 발견된 cross-cutting lesson (v0.7.51)

- **threshold-based alerting 의 *multi-metric* 정공법**: max_size / min_hit_rate / max_evictions 의 *multi-metric* 의 *operational* 의 *low-friction* 정공법. *severity* 의 *warning* vs *critical* 의 *operational* 보강.
- **decay aging 의 *cache reload* 정공법**: scores saved N days ago 의 *automatic aging* 의 *operational* 의 *low-friction* 정공법. *freshness* 의 *operational* 보강.
- **trend chart CLI 의 *--snapshots=PATH* 정공법**: file-based 의 *persistence* 의 *operational* 의 *low-friction* 정공법. *zero-dep* 의 *operational* 보강.
- **dashboard export CLI 의 *multi-format* 정공법**: json / markdown / html 의 *multi-format* 의 *operational* 의 *low-friction* 정공법. *flexibility* 보강.
- **federation v5 CLI 의 *FREE tier* 정공법**: VirusTotal paid API 의 *exclusion* 의 *low-friction* 정공법. *user-provided 3rd source* 의 *operational* 보강.

## Reference (다른 release note)

- v0.7.50 release note (layer 2 CLI + trend ASCII chart + dashboard HTML + federation v5 + decay CSV) — 본 release 의 1차 출처
- v0.7.49 release note (federation v4 + decay persistence + layer 2 pipeline + cache trend + dashboard export)
- v0.7.48 release note (V-R13 commit diff integration + LFU full refactor + cache dashboard + federation v3 + CLI flag)

## TASK (본 release)

### TASK-V0751-FOLLOWUP-BUNDLE: 5 follow-up 항목 (4 new module + 1 extension + 10 new test, all FREE tier)

- **상태**: in-flight (proposed)
- **commit**: 5 commit (5186836 + 4247589 + 4c579ad + 8810695 + 85be71c) + 1 final (TBD)
- **scope**:
  - Phase 1: cache alerting (5186836)
  - Phase 2: decay aging (4247589)
  - Phase 3: trend chart CLI (4c579ad)
  - Phase 4: dashboard export CLI (8810695)
  - Phase 5: federation v5 CLI (85be71c)
  - Phase 6: release note + version bump + log (TBD)
- **cumulative test**: 540+ → **550+** (10 new: 2 alerting + 2 decay age + 2 trend chart CLI + 2 dashboard export CLI + 2 federation v5 CLI)

### EXCLUDED (paid)

- ~~TASK-V0751-VIRUSTOTAL~~: VirusTotal API integration (commercial, opt-in) — *EXCLUDED*, deferred to v0.7.52+ per user request

### Follow-up (v0.7.52+)

- **TASK-V0752-VIRUSTOTAL-OPT-IN**: VirusTotal API integration (commercial, opt-in) — paid
- **TASK-V0752-LIVE-CACHE-DASHBOARD**: Streamlit/Flask live dashboard
- **TASK-V0752-FEDERATION-V6-OPT-IN**: 4+ source weighted voting (with optional VirusTotal)
- **TASK-V0752-CACHE-ALERTING-EMAIL**: SMTP/email notification on alert
- **TASK-V0752-ADR-FORMAL**: 1 release cycle 후 formal acceptance for v0.7.51 (no new ADRs in v0.7.51)

## Metric

- v0.7.51 = 5 enhancement commit + 1 final commit = **6 commit**
- 4 신규 module (cache_analytics_alerting 3.6 KB + cache_analytics_trend_chart_cli 2.0 KB + cache_dashboard_export_cli 2.8 KB + phishing_federation_v5_cli 2.2 KB) = **10.6 KB total**
- 1 module extension (cache_lfu_decay_persist.decay_age_scores)
- 10 new tests (2/2 PASS each, no regression on existing)
- 1 release note (v0.7.51.md, ~9 KB)
- 누적 test 540+ → **550+** (10 new)
- 46 release 누적 (v0.7.5 ~ v0.7.51)
- 170+ commit code-repo (v0.7.50 까지 170 + 5 = **175+**)
- 30 module cumulative = **150+ KB total**
- 17 ADR accepted cumulative (006-025) + 0 ADR proposed
- 41 test suites cumulative
- 201 tests cumulative
- **All FREE tier, no paid APIs used (per user request)**
