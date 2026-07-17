# Beta v0.15.0 — ⚠️ BREAKING: 2nd deprecation cycle 종결 (`work_backlog.md.bak` 완전 drop) (2026-07-16)

> **Phase 14 ADR-003 deprecation cycle 의 최종 cycle (v0.15.0).**
> 본 release 는 **breaking change** — `.bak` drop + silent fallback 완전 disable.
> SemVer 표기: minor (commit message 의 BREAKING CHANGE 명시).

## ⚠️ Breaking change 요약

pre-v0.15.0 caller 중 **`legacy_memory` kwarg / `--legacy-memory` flag / silent fallback 사용 caller** 는 v0.15.0 부터 **자동 fallback 불가**.

세 가지 migration 가이드 (택일):

1. **`legacy_memory=True` 또는 `--legacy-memory` 명시** (legacy fallback 의도 표시).
2. **explicit `session_handoff_path` / `work_backlog_index_path` 명시** (1st cycle 정공법).
3. **`.bak` 미존재 정공법 (v0.15.0+ 권장)** — 신규 layout 사용.

## 1. 배경 — deprecation timeline 종결

| 버전 | 상태 | 시점 |
|---|---|---|
| v0.14.0 | 1st cycle 시작 | ✅ closed |
| v0.14.1 | 1st cycle 종결 | ✅ closed |
| v0.14.5 | 2nd cycle 시작 | ✅ closed |
| **v0.15.0** | **2nd cycle 종결 (`.bak` drop)** | **← 본 release** |

총 4 release 에 걸친 deprecation 운영 안정화 cycle 종결.

## 2. 핵심 변경 (6 deliverable)

### 2.1 `work_backlog.md.bak` 완전 drop

`git rm ai-workflow/memory/active/work_backlog.md.bak` (5.7 MB / 58,389 bytes / 330 line).
v0.14.0 migration 에서 백업으로 보존했지만, v0.15.0 release 시점에 silent fallback 정공법 완전 disable.

### 2.2 자동 정합 (code 변화 최소)

`cache.py:refresh_workflow_state_cache` 의 `legacy_bak.exists()` 분기가 False 반환 시 deprecation_warnings emit 안 됨. silent fallback 자동 disable. **코드 자체 변경 ❌** — docstring 만 갱신 (deprecation cycle complete 명시).

### 2.3 maturity_matrix 정합

- `deprecation_cycle_stage: 'v0.14.5'` → **`'v0.15.0'`** 갱신.
- `recent_done_items` 에 v0.15.0 line 추가 (breaking change marker).

### 2.4 Panel 7 dashboard 자동 정합 (file state 기반)

`collect_deprecation_cycle_progress` 가 `bak + legacy` 모두 부재 자동 detect → `stage: v0.15.0` (complete) 표시.

timeline `current` marker 가 v0.15.0 으로 자동 이동 (`declared_stage='v0.15.0'` 기반).

### 2.5 snapshot regen

`ai-workflow/dashboard/snapshot.md` + `snapshot.html` 모두 Panel 7 정합 emit:

- `stage: v0.15.0` + `declared_stage: v0.15.0` + `bak_present: False` + `legacy_present: False` + `next_release: (complete)` + timeline 4 row 모두 + `current` marker at v0.15.0.

### 2.6 cache.py docstring 갱신 (behavior 정합)

`deprecation_warnings` block 의 docstring 만 갱신. v0.15.0 cycle complete 의미.
코드 분기 자체는 유지 — `.bak` 부재 시 자동 no-op.

## 3. Migration 가이드 (caller 별)

### Case A: `refresh_workflow_state_cache` 직접 호출

```python
# pre-v0.15.0 (silent fallback 의존) — ⚠️ v0.15.0 부터 자동 fallback 불가
refresh_workflow_state_cache(project_profile_path=...)

# v0.15.0+ 권장 — explicit path
refresh_workflow_state_cache(
    project_profile_path=...,
    session_handoff_path=Path("ai-workflow/memory/active/session_handoff.md"),
    work_backlog_index_path=Path("ai-workflow/memory/active/backlog"),  # directory path
)
```

### Case B: `generate_workflow_state.py` CLI 호출

```bash
# pre-v0.15.0 — ⚠️ v0.15.0 부터 silent fallback 불가
python3 generate_workflow_state.py --project-profile-path docs/PROJECT_PROFILE.md ...

# v0.15.0+ 권장 — 명시 path
python3 generate_workflow_state.py \
  --project-profile-path docs/PROJECT_PROFILE.md \
  --session-handoff-path ai-workflow/memory/active/session_handoff.md \
  --work-backlog-index-path ai-workflow/memory/active/backlog
```

### Case C: legacy fallback 의도적 유지 시

```bash
# opt-in 명시 — deprecation_warnings 정상 emit
python3 generate_workflow_state.py --legacy-memory ...
```

## 4. 검증 (10 smoke 모두 PASS, 회귀 ❌)

- drift_prevention 6/6
- memory_lint 4/4
- memory_freeze_lint
- **appendonly_memory_layout 6/6 + WARN 0** (`.bak` drop 후 WARNINGS 빈 list)
- git_history_summarizer 5/5
- smart_context_reader 5/5
- apply_robust_patch 5/5
- **phase15_dashboard_panels 4/4** (Panel 7 `stage=v0.15.0` 자동 정합)
- deprecation_cycle_v0_14_5 4/4
- refresh_maturity_v0_14_6 4/4

- 누적 smoke **260+ PASS** (회귀 ❌)

## 5. 의의

- Phase 14 (Append-only Memory Layout v1.0) 의 *4 cycle deprecation 운영 안정화* 정식 종결.
- `work_backlog.md.bak` 5.7 MB 영구 제거로 repo size 감소.
- silent fallback 완전 disable → caller 가 *명시* 해야 동작 → contract 명확성 회복.
- Panel 7 dashboard 가 *file state 기반* 으로 stage 자동 정합 → 2nd cycle 종결 표시.

## 6. 일일 backlog (SSOT)

- [`ai-workflow/memory/release/v0.15.0/backlog/2026-07-16.md`](../ai-workflow/memory/release/v0.15.0/backlog/2026-07-16.md)

## 7. 다음 step

- Phase 15 dashboard 의 추가 panel 확장 또는 후속 cycle 운영 안정화 (별도 release).
- caller 의 breaking change 대응 — migration case A/B/C 적용 권장.

---

⚠️ **Downstream consumer 공지**: 본 release 는 breaking change. 위 migration 가이드 §3 을 *반드시* 확인하고 v0.15.0 으로 upgrade 하시기 바랍니다.

release URL: <https://github.com/ykylee/standard_ai_workflow/releases/tag/v0.15.0-beta>