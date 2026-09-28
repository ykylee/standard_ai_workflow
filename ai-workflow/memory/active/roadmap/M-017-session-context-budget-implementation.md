---
id: M-017
title: 세션 시작 컨텍스트 예산 — implementation (출구 먼저, red 나중)
sdlc_phase: implementation
status: done
order: 17
parallel_allowed:
  - M-007
deliverables:
  - workflow-source/workflow_kit/common/context_budget.py
  - workflow-source/workflow_kit/tools/rollover_handoff_notes.py
  - workflow-source/tests/check_session_context_budget.py
  - docs/LOCAL_GATE.md
goals: [G2]
---

# M-017 — 세션 시작 컨텍스트 예산 — implementation

design ([`M-016`](./M-016-session-context-budget-design.md) → ADR-029 accepted,
[`session_context_budget_spec.md`](../../../../workflow-source/core/session_context_budget_spec.md))
을 구현한다. 순서는 스펙 §8 — **출구 먼저, red 나중** (지금 저장소는 네 예산 모두
초과라 검사를 먼저 켜면 만성 red 가 된다).

**종결 (2026-09-28)**: 스펙 §8 1~6 단계 완료 (TASK-2026-09-28-main-013). 필독 195.1KB →
111.5KB 실측. red 예산 셋 통과, 기준선 한 줄(warn)만 초과. 상한 값은 실측 후 유지
(Q2 재조정 판단 — 구현 결과 기록 참조).

## WBS

- **WBS-17.1** 구현 — 스펙 §8 여섯 단계를 한 task 로 (TASK-2026-09-28-main-013):
  1. 예산 모듈 + refresh-state warning (`context_budget.py`)
  2. D — `state.json.memory_entries` v2 포인터화
  3. A·B — `wk rollover-handoff-notes` + 표준 `Memory Update Paths`
  4. E — `CLAUDE.md` 운영 절 → `docs/LOCAL_GATE.md`
  5. 이관 실행 · 실측 · 상한 재조정 판단
  6. `check_session_context_budget` 이 저장소 red 활성
