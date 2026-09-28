---
id: M-016
title: 세션 시작 컨텍스트 예산 — design (ADR-029 + core 스펙 절)
sdlc_phase: design
status: done
order: 16
parallel_allowed:
  - M-007
deliverables:
  - ai-workflow/wiki/decisions/adr-029-session-context-budget.md
  - workflow-source/core/session_context_budget_spec.md
goals: [G2]
---

# M-016 — 세션 시작 컨텍스트 예산 — design

requirements sign-off ([`M-015`](./M-015-session-context-budget-requirements.md) →
[`requirements 문서`](../../../../docs/planning/session-context-budget-requirements-2026-09.md)
§9, 2026-09-28) 를 받는 design 단계. sign-off 가 고정한 범위(A+B+D+E, C warn) ·
상한 값 · 강도 위에서 남은 설계 결정을 ADR 로 내린다:

- **ADR-029 결정 대상** (requirements §7):
  - 예산 상수의 정본 모듈 위치와 그것을 읽는 검사
  - §5 누적형 이관 도구의 CLI (`wk` 명령 이름 · 인자 · dry-run 기본)
  - §5 현재형 절 **이름 목록**의 정본 위치
  - `state.json.memory_entries` 포인터 스키마와 버전 이행
  - `CLAUDE.md` 운영 절의 이관 대상 문서 경로
- **core 스펙 절**: 예산 · 출구 · '잃지 않음' 판정(R4)의 kit 표준 문서화.
- **불변**: R0 — 이관은 삭제가 아니다 · `state.json` 은 생성기로만 · 생성 블록 불가침 ·
  push 게이트 전량 2축.

**종결 (2026-09-28)**: 소유자 승인 — ADR-029 accepted, core 스펙 draft. 구현은
[`M-017`](./M-017-session-context-budget-implementation.md) 으로 이어진다.

## WBS

- **WBS-16.1** design 확정 — ADR-029 + `session_context_budget_spec.md` — 산출물:
  `ai-workflow/wiki/decisions/adr-029-session-context-budget.md`,
  `workflow-source/core/session_context_budget_spec.md`
