---
id: M-015
title: 세션 시작 컨텍스트 예산 — requirements (출구 + 예산)
sdlc_phase: requirements
status: done
order: 15
parallel_allowed:
  - M-007
deliverables:
  - docs/planning/session-context-budget-requirements-2026-09.md
goals: [G2]
---

# M-015 — 세션 시작 컨텍스트 예산 — requirements

concept 검토([`M-013`](./M-013-session-context-budget.md) →
[`session-context-budget-review-2026-09.md`](../../../../docs/planning/session-context-budget-review-2026-09.md))
의 소유자 결정 **③ 출구 + 예산** (2026-09-28) 을 받는 requirements 단계:

- **출구 범위**: 이관 후보 A(§5 규칙 블록 → memory_index 승격 / sessions) ·
  B(완료 기록 → sessions) · C(§1 기준선 줄 바이트 상한) · D(`state.json`
  `memory_entries` 를 포인터로) · E(`CLAUDE.md` 게이트 장문 이관) 중 이번 범위.
- **예산**: 섹션별 **바이트** 상한 값과 강도(warn / red). 넘치면 **출구를 가리킨다**
  — '넘쳤다 → 이 명령으로 옮겨라'.
- **불변 조건**: 이관은 삭제가 아니다 · `state.json` 은 생성기로만 · 생성 블록
  (`check_standard_single_source`) 은 건드리지 않는다.
- **잃지 않았음을 재는 수단**: 이관 뒤 다음 세션이 필요한 것을 잃지 않았는지의 판정을
  완료 기준에 넣는다 (concept 전제 3 · §7).

**종결 (2026-09-28)**: 소유자 sign-off — Q1~Q5 권고안대로 (산출물 §9). design 단계는
[`M-016`](./M-016-session-context-budget-design.md) 으로 이어진다.

## WBS

- **WBS-15.1** requirements 확정 — 출구 범위 · 섹션별 바이트 상한 · 게이트 강도 ·
  '잃지 않음' 판정 · session-start 절차의 원문 읽기 범위 · 다음 단계(design) 진입
  조건 — 산출물: `docs/planning/session-context-budget-requirements-2026-09.md`
