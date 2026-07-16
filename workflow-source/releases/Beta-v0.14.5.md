# Beta v0.14.5 — 2nd deprecation cycle 시작 (`--legacy-memory` flag) (2026-07-16)

> **Phase 14 ADR-003 의 2nd cycle 진입.** breaking change ❌ (다음 v0.15.0 에서 breaking).
> release 의 deprecation timeline 정공법 적용 — silent fallback 의 2 cycle 운영.

## 1. 배경 — deprecation timeline

- v0.14.0: 1st cycle 시작 (silent fallback) ✅
- v0.14.1: 1st cycle 종결 (warning stage) ✅
- **v0.14.5: 2nd cycle 시작 (`--legacy-memory` opt-out flag)** ← 본 release
- v0.15.0: 2nd cycle 종결 (`.bak` drop, breaking)

## 2. 핵심 변경 (3 deliverable)

### 2.1 `cache.py:refresh_workflow_state_cache` 신규 kwarg

```python
def refresh_workflow_state_cache(
    *,
    project_profile_path: Path,
    ...
    legacy_memory: bool | None = None,  # v0.14.5+ 2nd cycle
):
    legacy_memory_effective = legacy_memory if legacy_memory is not None else True
```

- `legacy_memory=None` (default) → True: 1st cycle silent fallback 정합 (backward compat).
- `legacy_memory=True` (explicit opt-in) → 1st cycle 동작.
- `legacy_memory=False` (explicit opt-out) → **2nd cycle strict**: branch_dir 하위 legacy path 자동 resolve 무효. caller 가 명시한 path 만 resolve.

### 2.2 deprecation_warnings 2 cycle 동시 emit

- `legacy_bak` 존재 + `legacy_memory_effective=True` → `1st cycle 종결 (warning stage)` + DEPRECATION WARNING v0.14.1 메시지.
- `legacy_bak` 존재 + `legacy_memory_effective=False` → `2nd cycle 진행 (strict opt-out)` + DEPRECATION ALERT v0.14.5 메시지 (silent fallback 무효, v0.15.0 drop 예정).
- `legacy_present` (구 `work_backlog.md`) + bak 부재 → DEPRECATION NOTICE (migration 미완료).

return dict 에 `deprecation_cycle` + `legacy_memory` 2 field 신규 (Panel 7 dashboard 정합).

### 2.3 `generate_workflow_state.py` CLI flag

`--legacy-memory` / `--no-legacy-memory` (argparse BooleanOptionalAction).

default None → cache.py 의 `legacy_memory if legacy_memory is not None else True` 로 True 처리 (backward compat).

### 2.4 maturity_matrix 정합

신규 top-level field `deprecation_cycle_stage: 'v0.14.5'` 추가. v0.15.0 release 시 `'v0.15.0'` 으로 update 만 하면 Panel 7 자동 표시 변경.

### 2.5 Panel 7 dashboard 동적 stage 표시

`collect_deprecation_cycle_progress` 가 `maturity_matrix.deprecation_cycle_stage` read → `declared_stage` field + `stage` field 동적 결정.

snapshot.md Panel 7:
- `stage: v0.14.5` + `declared_stage: v0.14.5` + `next_release: v0.15.0` + timeline 4 entry.

## 3. 신규 smoke `tests/check_deprecation_cycle_v0_14_5.py` 4/4 PASS

- case_1: `--legacy-memory` 명시 + `.bak` 존재 → 정상 refresh.
- case_2: default (None → True) + `.bak` 존재 → 정상 refresh (backward compat).
- case_3: `.bak` 부재 시 정상 refresh.
- case_4: `--no-legacy-memory` 명시 시 strict opt-out.

기존 phase15_dashboard_panels smoke 정합: case_2_panel_7_deprecation 가 `declared_stage` 기반으로 stage 검증 (v0.14.1 hard-coded → 동적).

## 4. 검증

- 누적 smoke **260+ PASS** (회귀 ❌)
- drift_prevention 6/6 · memory_lint 4/4 · memory_freeze_lint · appendonly_memory_layout 6/6 + WARN 1 · git_history_summarizer 5/5 · smart_context_reader 5/5 · apply_robust_patch 5/5 · phase15_dashboard_panels 4/4 · **deprecation_cycle_v0_14_5 4/4** · refresh_maturity_v0_14_6 4/4

## 5. 일일 backlog (SSOT)

- [`ai-workflow/memory/release/v0.14.5/backlog/2026-07-16.md`](../ai-workflow/memory/release/v0.14.5/backlog/2026-07-16.md)

## 6. 다음 step

- `refresh-maturity` dispatcher + `cmd_release` auto-wire → **v0.14.6**.
- HTML renderer Panel 6/7/8 + git reflog 통합 → **v0.14.7**.
- 2nd deprecation cycle 종결 (`.bak` drop, ⚠️ BREAKING) → **v0.15.0**.

---

release URL: <https://github.com/ykylee/standard_ai_workflow/releases/tag/v0.14.5-beta>