---
id: M-017
title: 세션 시작 컨텍스트 예산 — implementation (출구 먼저, red 나중)
sdlc_phase: implementation
status: planned
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

## WBS

- **WBS-17.1** 예산 모듈 + refresh-state warning — `context_budget.py` (예산 레코드 ·
  현재형 절 목록), `wk refresh-state` 초과 경고
- **WBS-17.2** D — `state.json.memory_entries` v2 포인터화 + test 갱신
- **WBS-17.3** A·B — `wk rollover-handoff-notes` + fixture test (무손실) + 표준 `Memory Update Paths`
- **WBS-17.4** E — `CLAUDE.md` 운영 절 → `docs/LOCAL_GATE.md`
- **WBS-17.5** 이관 실행 · 실측 · 상한 한 번 재조정 + `check_session_context_budget` 활성 (red)
