---
release: v0.13.0
closed_phases: []
promoted_skills: []
added_harnesses: []
deprecated_symbols: []
phase_13_sub_milestones:
  - { name: v0.13.0, scope: "5 panel data + CLI --json", status: shipped }
  - { name: v0.13.1, scope: "drift guard inline + release post-emit", status: shipped }
  - { name: v0.13.2, scope: "정적 HTML dashboard renderer", status: shipped }
---

# Beta v0.13.0 — Quality Dashboard (Phase 13 sub-milestone 1) (2026-07-09)

> Phase 13 (Operational Intelligence v1.0) 의 sub-milestone 3개 (v0.13.0 / v0.13.1 / v0.13.2) 일괄 구현.
> 본 release 는 **Quality Dashboard** 의 *1st deliverable* — 5 panel 운영 metric (drift prevention
> / maturity distribution / memory_index utilization / smoke trend / recent release cycle) 을
> 단일 surface 로 통합. release pipeline 과 inline drift guard 실행을 통해 *자가 인식 /
> 자가 문서화 / 자가 복구* 의 foundation 을 확립.

## 핵심 (3 sub-milestone)

### 1) v0.13.0 — 5 panel data collector + CLI `--json` (sub-milestone 1)

신규 module `workflow_kit.common.dashboard_data` 가 5 panel 의 운영 metric 을 단일 dict 로 emit:

- **Panel 1 — Drift Prevention Status**: maturity_matrix.json freshness + harness supported count + HEAD commit date delta. north-star metric `silent_failing_cycles_count` (Phase 13 AC1).
- **Panel 2 — Maturity Distribution**: skill (12 stable) / mcp_tools (8 stable + 4 beta) / harness (10 supported) / milestone (11 done + 1 in_progress) 분포.
- **Panel 3 — Memory Index Utilization**: 7 entry + cue_anchor frequency + cumulative timeline. `retrieval_hit_rate` telemetry 는 Phase 13 AC2 후속.
- **Panel 4 — Smoke Trend**: 누적 smoke count (40/40) + recent 5 release 의 smoke trend (semver-natural sort — `Beta-v0.9.6` vs `Beta-v0.10.0` lexicographic 함정 회피).
- **Panel 5 — Recent Release Cycle**: state.json.session.recent_done_items 의 상위 10 timeline.

CLI: `python -m workflow_kit.workflow_kit_cli --command=dashboard --format=json`

### 2) v0.13.1 — drift guard inline + release post-emit (sub-milestone 2)

**F-1: Inline drift guard 실행** — `run_drift_prevention_guard_inline` 가 `check_drift_prevention_v0_11_23.py` 를 subprocess 로 호출, 6 case 의 PASS/FAIL 을 parse 한 뒤 `guard_status='pass'|'fail'|'error'` emit. 기존 `guard_status='unknown'` marker 폐기. 6/6 PASS 시 40ms 내 inline 실행 완료.

**F-2: Release post-emit hook** — `tools/release_pipeline.py` 의 `cmd_release` 의 `gh release create` 성공 후 자동 dashboard markdown emit. `--skip-dashboard-emit` 으로 skip, `--dashboard-output=PATH` 로 경로 override. emit 실패는 warning 만 — release 자체는 성공.

### 3) v0.13.2 — 정적 HTML dashboard renderer (sub-milestone 3)

**F-3: render_dashboard_html(snapshot) -> str** — single self-contained HTML page. Chart.js CDN (jsdelivr, MIT) + 5 panel widget (stacked bar / line / list). `prefers-color-scheme: dark` 자동 인식. JS off 시 static fallback 그대로 표시.

**F-4: CLI `--format=html` + `--publish`** — `--publish` 시 `docs/dashboard/index.html` 추가 copy (GitHub Pages source). release 후 자동 emit 시 동일 hook 사용.

## 신규 파일 / 변경

| 변경 | 파일 | 비고 |
|---|---|---|
| 신규 | `workflow-source/workflow_kit/common/dashboard_data.py` | 5 collector + snapshot aggregator + markdown/HTML renderer + inline drift guard executor (~1275 line) |
| 수정 | `workflow-source/workflow_kit/workflow_kit_cli.py` | `cmd_dashboard` 등록 + `--format=json\|markdown\|html` + `--publish` + `--inline-guard` (+84 line) |
| 수정 | `workflow-source/tools/release_pipeline.py` | `_emit_dashboard_post_release` hook + `--skip-dashboard-emit` + `--dashboard-output` (+123 line) |
| 신규 | `workflow-source/tests/check_quality_dashboard_v0_13_0.py` | 10 case smoke (5 v0.13.0 + 2 v0.13.1 + 3 v0.13.2) |
| 신규 | `workflow-source/core/quality_dashboard_spec.md` | 15 section spec (panel shape + AC + edge + 호환성) |
| 신규 | `workflow-source/tools/release_v0_13_0.py` | v0.13.0 release automation wrapper (8 step) |
| 신규 | `workflow-source/tools/fix_readme_for_release.py` | README header auto-fix tool (reusable) |
| 신규 | `ai-workflow/dashboard/.gitkeep` | dashboard markdown emit target landing zone |
| 신규 | `docs/dashboard/.gitkeep` | GitHub Pages publish source landing zone |
| 변경 | `workflow-source/pyproject.toml` | version 0.11.25 → 0.13.0 |
| 변경 | `workflow-source/workflow_kit/__init__.py` | loud fallback `v0.11.23-beta` → `v0.13.0-beta` |
| 변경 | `README.md` | header version + date + package + latest tag 갱신 |
| 신규 (auto-emit) | `ai-workflow/dashboard/snapshot.md` | release 후 dashboard markdown snapshot |
| 신규 (--publish) | `docs/dashboard/index.html` | GitHub Pages publish source |

## 검증

- 누적 smoke test **41/41 PASS** (40 v0.11.25 baseline + 1 신규 `check_quality_dashboard_v0_13_0.py` 10/10 case).
- drift prevention 6/6 PASS 유지 (README case_4 정합 확인).
- dashboard smoke 10/10 PASS (snapshot shape / CLI json / CLI md / invalid format / output file / inline guard / release_pipeline emit / HTML render / CLI html / CLI html --publish).
- README version header (`v0.13.0-beta`) ↔ pyproject (`0.13.0`) 정합.
- `__version__` = `v0.13.0-beta` (pyproject 0.13.0 정합).
- `maturity_matrix.json` `last_updated` 2026-07-09 유지.
- inline drift guard 6 case 40ms 내 PASS (`guard_runtime_ms ≈ 40`).

## 호환성

- **Public API 추가 ❌** — `workflow_kit.common.dashboard_data` 는 internal module. 2-year SemVer stable guarantee (v0.8.0 → v2.0.0) 유지.
- **신규 dependency ❌** — 표준 library 만 사용. Chart.js CDN (jsdelivr, MIT) 만 external 이며 `--format=html` 사용 시에만 fetch.
- **read-only except emit** — 모든 collector / renderer / inline guard 는 read-only. file write 는 `_emit_dashboard_post_release` 와 `--output` / `--publish` 의 *명시적 호출* 시에만.
- **drift prevention 6/6 PASS 유지** — inline guard 의 결과가 0 error 정합.
- **breaking change ❌**.
- **PyPI 배포: ❌** (GitHub Releases only, 정공법 유지).

## 산출물 (현 release snapshot)

- `drift_prevention.silent_failing_cycles_count = 0` (Phase 13 AC1 north-star 정합)
- `maturity_distribution.skills.stable = 12` / `mcp_tools.stable = 8` / `mcp_tools.beta = 4`
- `memory_index_utilization.entries_total = 7` (MEM-2026-07-09-001~007)
- `smoke_trend.cumulative_pass = 40 / cumulative_total = 40` (Beta-v0.11.25 정합)
- `recent_releases.items_total = 60`

## 잔여 (v0.13.3+ / Phase 13 AC2 follow-up)

1. **memory_index telemetry** (Phase 13 AC2) — opt-in retrieval 호출 횟수 측정을 `memory_index/retrieval_log.jsonl` 에 append → dashboard 가 tail 분석. 본 release 는 `retrieval_hit_rate` marker 만 emit.
2. **GitHub Pages auto-publish workflow** — `.github/workflows/dashboard-publish.yml` 신규. release 시 자동 `--publish` → GitHub Pages deploy.
3. **ADR-006 retrospective full review** — Phase 13 kick-off 와 함께 ADR-005 의 실사용 30일 retrospective 자리 박기 (scheduled 2026-07-16).

## Reference

- 직전 release: [Beta-v0.11.25.md](Beta-v0.11.25.md) — stdio-sdk 정식 stable 승격.
- 설계 가이드: [`../ai-workflow/wiki/topics/quality-dashboard-implementation-guide.md`](../ai-workflow/wiki/topics/quality-dashboard-implementation-guide.md)
- north-star metric: [`../ai-workflow/wiki/topics/phase-13-definition-north-star.md`](../ai-workflow/wiki/topics/phase-13-definition-north-star.md)
- 구현 spec: [`../core/quality_dashboard_spec.md`](../core/quality_dashboard_spec.md)
- audit baseline: commit `c966ca2` (2026-07-09 audit 후보 10건 일괄 해소, P2-3 후보 도출)
- 새 file: `tests/check_quality_dashboard_v0_13_0.py` (10/10 PASS)
- 새 file: `tools/fix_readme_for_release.py` (재사용 가능, 향후 release 자동화)