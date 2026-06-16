# Beta v0.7.52 — Retrospective Consolidation 통합본 (2026-06-16)

> v0.7.6 (D: run_all_checks + E: workflow_kit.metadata) 의 *후속* retrospective cleanup release.
> 6 release (v0.7.46~v0.7.51) 사이 누적된 wrapper-of-wrapper 를 4 phase 로 정리.

## 핵심 추가 (1 cleanup 통합본, 4 commit)

### Retrospective consolidation (4 phase)

Per overkill audit (v0.7.46-v0.7.51), 6 release 의 *feature module* 22 개 / test 52 개가 wrapper-of-wrapper 패턴으로 부풀어 있음. 4 phase cleanup 으로 30 module → 19 module, 201 test → 182 test, ~10 KB / ~2,150 LOC 제거.

#### Phase 1 — `081b72c`: phishing_federation v2/v3/v4/v5 → 1 module

```python
# Created: workflow_kit/phishing_federation.py (was v4, +v5's 3rd source, +v3's min_source_count)
# Renamed: tests/check_phishing_federation_v4.py → check_phishing_federation.py (4 tests, +1 from v3)
# DELETED: phishing_federation_v2.py, v3.py, v5.py + 3 test files (-602 LOC)
```

#### Phase 2 — `87f77bd`: cache_dashboard_export → cache_dashboard inline

```python
# Inlined export_dashboard_json/markdown/html + write_dashboard into cache_dashboard.py
#   as render_dashboard(cache, format=...) + write_dashboard(..., format=...)
# DELETED: cache_dashboard_export.py + 2 test files
# Net: -316 LOC, format= param 으로 caller surface 는 유지
```

#### Phase 3 — `25c7c1a`: v_r13 integration + layer2 pipeline → v_r13_commit_diff

```python
# Inlined parse_range_from_url, check_url_semantic_with_commit_diff,
#   format_commit_diff_summary, PipelineResult dataclass, run_layer2_pipeline
#   into v_r13_commit_diff.py
# DELETED: v_r13_commit_diff_integration.py, v_r13_layer2_pipeline.py + 2 test files
# Consolidated: check_v_r13_commit_diff.py → 6 tests (was 2, +1 from integration, +3 from pipeline)
# Net: -461 LOC
```

#### Phase 4 — `71bf15d`: 6 CLI module → 1 dispatcher (registry pattern)

```python
# Created: workflow_kit/workflow_kit_cli.py with @register("name") decorator registry
#   (subcommand: cache-dashboard, dashboard-export, trend-chart, alert, layer2, federate)
# DELETED: cache_dashboard_cli.py, v_r13_layer2_cli.py,
#   cache_analytics_trend_chart_cli.py, cache_dashboard_export_cli.py,
#   phishing_federation_v5_cli.py, cache_analytics_alerting_cli.py + 6 test files
# Created: tests/check_workflow_kit_cli.py (6 tests, dispatcher edge cases)
# Net: -860 LOC, +253 LOC dispatcher
```

**Registry pattern 정공법** — `@register("name")` decorator 가 `COMMANDS: dict` 에 자동 등록, `_print_usage()` 가 `sorted(COMMANDS)` 로 command list auto-generate. 새 subcommand 추가 = 1 함수 + decorator + 끝. argparse 미사용 (zero-dep 정책).

**Inline vs dispatcher 선택 기준**:
- Internal logic / 데이터 처리 module → **inline** (caller 단순화)
- User-facing CLI entry point → **dispatcher + registry** (command surface 유지)

### Module census (v0.7.52 final)

19 modules. 12 real (load-bearing) / 7 persistence-wrapper.

| # | Module | Size | Role |
|---|---|---|---|
| 1 | okf_export | 35 KB | OKF spec export |
| 2 | okf_import | 30 KB | OKF spec import |
| 3 | url_validity | 50 KB | V-R10 + V-R13 semantic URL checks + cache |
| 4 | path_resolver | 10 KB | in-repo path → URL |
| 5 | phishing_keywords | 12 KB | PhishTank + OpenPhish + bundled feed |
| 6 | lfu_config | 3 KB | LFU temporal decay math |
| 7 | lfu_integration | 3 KB | LFUConfig + _save_cache wrap |
| 8 | cache_migration | 6 KB | migrate v0.7.41 → per-strategy |
| 9 | cache_size_compare | 4 KB | per-strategy size + eviction |
| 10 | cache_lfu_decay | 6 KB | decay score wrap + full refactor |
| 11 | cache_lfu_decay_persist | 6 KB | JSON + CSV persistence + aging |
| 12 | cache_analytics | 4 KB | per-strategy rollup |
| 13 | cache_analytics_diff | 1.5 KB | snapshot compare |
| 14 | cache_analytics_alerting | 3.6 KB | threshold alerting |
| 15 | cache_analytics_trend | 3.6 KB | snapshot persistence + trend |
| 16 | cache_analytics_trend_chart | 2 KB | ASCII chart |
| 17 | cache_dashboard | 6 KB | text/JSON/Markdown/HTML formats |
| 18 | bitbucket_v2 | 2.6 KB | cross-vendor commit API |
| 19 | v_r13_commit_diff | 8 KB | cross-vendor diff + integration + pipeline |

## 검증

- **Smoke 회귀 0**: 19 module import OK, 6 dispatcher command (alert / cache-dashboard / dashboard-export / federate / layer2 / trend-chart) 전부 registry 등록
- **Dispatcher edge case 4종 PASS**:
  - `no-args` → rc=2 (usage)
  - `unknown-command` → rc=2 (usage)
  - `layer2 no-url` → rc=2 (URL required)
  - `cache-dashboard no-arg` → rc=0 (default cache path)
- **Cumulative tests**: 201 → 182 (-19, wrapper-test 정합)
- **Cumulative LOC**: ~150 KB → ~140 KB (-10 KB)
- **Preserved untouched**: 17 ADR accepted (006-025), 26 concept page, core module 5 (url_validity / okf_export / okf_import / path_resolver / phishing_keywords)

## Commit

| Hash | Subject |
|---|---|
| `081b72c` | refactor(v0.7.52): remove v2/v3/v4/v5 federation module + test files |
| `87f77bd` | refactor(v0.7.52): consolidate cache_dashboard_export into cache_dashboard module |
| `25c7c1a` | refactor(v0.7.52): inline v_r13_commit_diff_integration + v_r13_layer2_pipeline into v_r13_commit_diff (6/6 PASS) |
| `71bf15d` | refactor(v0.7.52): collapse 6 CLI modules into workflow_kit_cli dispatcher (6/6 PASS) |
| `ee63739` | docs(v0.7.52): log entry for retrospective consolidation cleanup |
| `chore(v0.7.52)` | version bump 0.7.6 → 0.7.52 + release note (본 commit) |

## 다음 (v0.7.53 / v0.8.0 후보)

- **다음 feature**: workflow_kit 의 *core 5 module* (url_validity / okf_export / okf_import / path_resolver / phishing_keywords) 의 정합성 audit 2차 (v0.7.52 = *wrapper* cleanup, v0.7.53+ = *core* audit)
- **CLI dispatcher 확장**: workflow_kit_cli 에 `--command=okf-export / --command=okf-import` 추가 (현재 CLI 6 subcommand 는 cache/analytics/V-R13 만, OKF 는 미통합)
- **OKF consumer guide 활성화**: docs/OKF_CONSUMER_GUIDE.md (v0.7.6~v0.7.52 통합) 의 GitHub Pages 또는 별도 consumer repo publish

## Reference

- [v0.7.6 release note](Beta-v0.7.6.md) (직전, D + E 2 follow-up)
- [v0.7.5 release note](Beta-v0.7.5.md) (Extension audit + Wiki 운영 자동화)
- [v0.7.6 consumer guide](../../docs/OKF_CONSUMER_GUIDE.md) (D + E 의 follow-up)
- [v0.7.6 quickstart](../../docs/OKF_CONSUMER_QUICKSTART.md) (5 section tutorial)
- [ai-workflow/wiki/log.md §2026-06-16 v0.7.52 retrospective](../../ai-workflow/wiki/log.md) (retrospective log)
- tests/check_workflow_kit_cli.py (6 dispatcher tests)
- workflow-source/workflow_kit/workflow_kit_cli.py (registry dispatcher, 253 line)
