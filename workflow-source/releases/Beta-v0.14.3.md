# Beta v0.14.3 — Phase 15 dashboard 신규 Panel 6/7/8 (2026-07-16)

> **Phase 15 kickoff.** Quality Dashboard 의 panel 5 종 → **8 종** 으로 확장.
> Phase 14 north-star metric + ADR-003 deprecation cycle progress + telemetry 통합.
> breaking change ❌.

## 1. 핵심 변경 (3 신규 panel)

### 1.1 Panel 6 — `multi_agent_concurrent_write_conflict`

Phase 14 의 north-star metric. v0.14.0+ append-only layout 의 structural 정합성 검증 — sub-agent 2개+ 동시 fan-out 시 mutable 공유 파일의 3-way merge conflict / overwrite race 가 working tree 에 잔존하는지 자동 check.

- 측정원: `ai-workflow/memory/active/` 하위 working tree 의 git merge conflict marker (`<<<<<<<`) 검출.
- 정합: `conflict_count: 0` + `status: 'pass'`.
- `dashboard_data.collect_multi_agent_concurrent_write_conflict()` 신규.
- `_render_panel_6()` markdown render — north_star / conflict_count / threshold / status / locations.

### 1.2 Panel 7 — `deprecation_cycle_progress`

ADR-003 deprecation cycle 의 정공법 진행 상태 시각화. 4 release version 별 stage 명시:

- `v0.14.0`: 1st cycle 시작 (silent fallback).
- `v0.14.1`: 1st cycle 종결 (warning stage).
- `v0.14.5`: 2nd cycle 시작 (`--legacy-memory` opt-out flag).
- `v0.15.0`: 2nd cycle 종결 (`.bak` drop 예정).

`collect_deprecation_cycle_progress()` 신규 — `maturity_matrix.deprecation_cycle_stage` + file state (`bak_present` / `legacy_present`) 동적 stage 표시.

### 1.3 Panel 8 — `telemetry_dashboard`

wiki log ingest/query/release 분포 + memory index hit rate 통합 panel:

- `phase_15_north_star` / `entries_total` / `telemetry_events_total`.
- `queries` / `hits` / `hit_rate` (memory index BM25 stdlib fallback 정합).
- `by_merge_state` / `by_source` 2 table.

`_render_panel_8()` markdown render.

## 2. 누적 정합

- `dashboard_data.py` 286 lines 확장 (panel 3종 + collect 함수 3종 + render 함수 3종).
- `tests/check_phase15_dashboard_panels.py` 152 lines 신규 — 4 case (Panel 6 conflict / Panel 7 deprecation / Panel 8 telemetry / cross-panel regen). **4/4 PASS**.

## 3. 검증

- 누적 smoke **260+ PASS** (회귀 ❌)
- drift_prevention 6/6 · memory_lint 4/4 · memory_freeze_lint · appendonly_memory_layout 6/6 + WARN 1 · git_history_summarizer 5/5 · smart_context_reader 5/5 · apply_robust_patch 5/5 · **phase15_dashboard_panels 4/4** · deprecation_cycle_v0_14_5 4/4 · refresh_maturity_v0_14_6 4/4

## 4. 일일 backlog (SSOT)

- [`ai-workflow/memory/release/v0.14.3/backlog/2026-07-16.md`](../ai-workflow/memory/release/v0.14.3/backlog/2026-07-16.md)

## 5. 다음 step

- 2nd deprecation cycle 진입 (`--legacy-memory` flag) → **v0.14.5**.
- HTML renderer Panel 6/7/8 + git reflog 통합 → **v0.14.7**.

---

release URL: <https://github.com/ykylee/standard_ai_workflow/releases/tag/v0.14.3-beta>