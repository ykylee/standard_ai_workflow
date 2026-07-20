# Beta v0.15.17 — release memory cycle close-out + v1.0.0 Break Point #1 해소 (2026-07-20)

> v1.0.0 진입 평가 (`workflow-source/core/v1_0_0_entry_evaluation.md`) 의 **Break Point #1** 해소.
> Panel 5 recent_releases + check_appendonly_memory_layout + check_quality_dashboard 4 fail 의
> 근본 원인인 `state.json` / TASK file 부재 / JSON escape 정합.
> 누적 smoke 24종, 회귀 0건.

## 1. 릴리스 요약

- v1.0.0_entry_evaluation.md 의 Break Point #1 (state.json / Panel 5 / appendonly_memory_layout / quality_dashboard 4 fail) 의 근본 원인 2건 동시 해소:
  - **TASK-2026-07-20-001.md 부재** → `check_appendonly_memory_layout` 의 daily-index → TASK file 부재 fail.
  - **state.json empty** → Panel 5 recent_releases.items_total = 0 + quality_dashboard recent_releases items_total >= 1 fail.
- v0.15.16 release 종합 commit (fc834d1) 의 TASK 정합 + state.json 재생성.
- 누적 smoke **24종 PASS**, 회귀 0건.
- v1.0.0 진입 평가의 Break Point #1 close-out.

## 2. 정정한 in-scope issue

### 2.1 TASK-2026-07-20-001.md 부재

- v0.15.16 release 종합 (fc834d1) 의 `backlog/2026-07-20.md` 가 `**TASK-2026-07-20-001**` link 를 가지지만, 실제 `backlog/tasks/TASK-2026-07-20-001.md` file 부재.
- `check_appendonly_memory_layout.py` 의 case 4 (daily index links) 에서 `**TASK-*` link 가 file 로 resolve 되지 않아 fail.
- **정정**: `backlog/tasks/TASK-2026-07-20-001.md` 신규 작성 (frontmatter 정공법: id / status / created_at / source_anchor / source_path / kind + 본문 description / implementation / outcome 3 section).

### 2.2 state.json empty / Panel 5 fail

- 2026-07-18 누수 진단 후 `state.json` reset → empty file (0 byte).
- Panel 5 recent_releases 의 items_total = 0 (state.json의 session.recent_done_items 부재).
- `check_quality_dashboard_v0_13_0.py` 의 case 1 (`recent_releases items_total >= 1`) fail.
- `check_appendonly_memory_layout.py` 의 case 3 (`[state_json] JSON parse fail`) fail.

### 2.3 maturity_matrix.json JSON escape 오류 (v0.15.16 highlight 추가 시)

- v0.15.16 release 종합 commit 의 maturity_matrix 갱신 시 highlight 본문 내 `\"` (Python str literal escape) 가 JSON string literal 의 raw quote 로 emit 되어 JSON parse fail.
- **정정**: line 91 의 raw quote 위치 12개 (`HARNESS_SPECS["grok-build"]` 등) 를 `\"` 로 escape.

## 3. deliverable (3개)

### 3.1 `ai-workflow/memory/active/backlog/tasks/TASK-2026-07-20-001.md` (신규)

- frontmatter 6 key 정공법 (`MEMORY_GOVERNANCE.md` §2 정합).
- 본문 description / implementation / outcome 3 section.
- `check_appendonly_memory_layout.py` 의 TASK file 부재 fail 해소.

### 3.2 `ai-workflow/memory/active/state.json` 재생성

- `workflow-source/scripts/generate_workflow_state.py` 자동 emit.
- `--project-profile-path docs/PROJECT_PROFILE.md` + `--daily-backlog-dir ai-workflow/memory/active/backlog` + `--tasks-dir ai-workflow/memory/active/backlog/tasks` + `--sessions-dir ai-workflow/memory/active/sessions` + `--latest-backlog-path ai-workflow/memory/active/backlog/2026-07-20.md` + `--workspace-root .` + `--output-path ai-workflow/memory/active/state.json`.
- `session.recent_done_items` 10개 정합 (v0.11.21 / v0.11.20 / v0.11.18 / v0.11.21 TASK 등).
- **smoke patch** (`check_appendonly_memory_layout.py`): path resolve 시 REPO_ROOT 기준도 시도 (state.json 의 path 가 repo-relative 일 때 정합).

### 3.3 `workflow-source/core/maturity_matrix.json` v0.15.16 + v0.15.17 highlight 추가

- v0.15.16: Grok Build 11번째 harness + cross-check discipline anchor 확장 (4 smoke 신규 + TST-WF-01 patch + housekeeping). **이전 commit (fc834d1) 의 maturity_matrix 갱신 누락분을 본 release 에서 정합**.
- v0.15.17: release memory cycle close-out (TASK-2026-07-20-001.md + state.json + Panel 5 정합).
- JSON escape 정정 (line 91 raw quote → `\"`).

## 4. 검증

- **Break Point #1 해소**: 4 fail 모두 close-out.
  - `check_appendonly_memory_layout.py` 6/6 PASS (case 1~6).
  - `check_quality_dashboard_v0_13_0.py` 12/12 PASS (전 case 1~12).
  - `check_drift_prevention_v0_11_23.py` 6/6 PASS (maturity JSON escape 정정).
  - `check_document_index_v0_15_16.py` 4/4 PASS (관련 정합).
- **Panel 1~8 dashboard 정합**:
  - Panel 1: guard_status `pass` + guard_cases `6/6` + maturity_last_updated `2026-07-20`.
  - Panel 5: items_total `10` (v0.15.17 추가 후 + 1, state.json 의 recent_done_items 정합).
  - Panel 2~8 정합 유지.
- **누적 smoke 24종 PASS** (24/24, 회귀 0):
  - drift_prevention 6/6 + harness_v0_15_9 4/4 + readme_cross_v0_15_12 4/4 + installation_usage_v0_15_14 4/4 + quickstart_v0_15_15 4/4 + sample_version_cross_v0_15_11 4/4 + document_index_v0_15_16 4/4 + code_index_v0_15_17 5/5 + release_md_v0_15_18 5/5 + memory_governance_cross_v0_15_19 5/5 + phase15_dashboard_panels 4/4 + smoke_trend_cross_v0_15_5 5/5 + telemetry_cross_v0_15_6 4/4 + memory_index_cross_v0_15_7 4/4 + maturity_distribution_cross_v0_15_8 4/4 + harness_apply_guide_v0_15_13 4/4 + refresh_maturity_v0_14_6 4/4 + refresh_maturity_v0_15_2 4/4 + refresh_maturity_v0_15_3 3/3 + deprecation_3rd_cycle_v0_15_4 3/3 + appendonly_memory_layout 6/6 + memory_lint 4/4 + audit_mkdocs_links 5/5 + quality_dashboard_v0_13_0 12/12.

## 5. v1.0.0 진입 평가 진행 상황

| Break Point | 상태 |
|---|---|
| **#1 state.json / Panel 5** | ✅ **CLOSED-OUT (v0.15.17)** |
| **#2 TST-WF-01 non_compliant 잔존** | ⏳ 다음 release (v0.15.18, historical 73 smoke `def test_case_*` wrapper 일괄 추가) |
| **#3 mypy strict 직접 verify 부재** | ⏳ venv 활성화 후 (CI 3-layer defense 정합으로 운영 risk 낮음) |

## 6. 다음 단계

- v0.15.18 — Break Point #2 해소: TST-WF-01 historical smoke 보강 (73 smoke × `def test_case_*` wrapper 일괄 추가).
- v0.15.19 — cross-panel final 정합.
- v0.15.20 — v1.0.0 pre-release final.
- **v1.0.0** — stable release.

---

release target: `v0.15.17-beta`
