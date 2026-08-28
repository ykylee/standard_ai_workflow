---
id: M-009
title: 계층별 회귀 실행 계약 — requirements (WATCHES 보급 + 선언 메타 검증)
sdlc_phase: requirements
status: done
order: 9
parallel_allowed:
  - M-007
deliverables:
  - docs/planning/test-impact-tiering-requirements-2026-08.md
---

# M-009 — 계층별 회귀 실행 계약 — requirements

concept 검토([`M-008`](./M-008-test-impact-tiering.md) →
[`test-impact-tiering-review-2026-08.md`](../../../../docs/planning/test-impact-tiering-review-2026-08.md))
의 소유자 결정 **C안** (2026-08-28) 을 받는 requirements 단계:

- **B 범위**: `WATCHES` 보급을 "커밋 전 관련 검사를 사람 대신 선언이 고르는
  수준" 까지 — 보급 대상 판정 기준과 CLAUDE.md 커밋 전 단계 갱신 요건.
- **C 범위**: 선언이 실제 입력 표면과 맞는지 재는 **메타 검증** 의 요구사항 —
  좁은 선언(조용히 안 도는 검사)을 잡는 것이 목적, 넓은 선언은 성능 문제일
  뿐이므로 경고까지만.
- **불변 조건**: push 게이트 전량 2축은 축소하지 않는다 (concept §5 ⛔,
  main-004 기각 재확인). CI 도 계속 2축 전량.
- **선행 실측**: 보급 확대의 이득(시간 + 선택 실수)을 requirements 문서가
  근거 실측으로 든다 — 실측 없이 요구사항을 확정하지 않는다.

**종결 (2026-08-28)**: 소유자 sign-off — R1~R6 승인, 미결 3곳(R1.3·R3.3·R4.2)
권고안대로 확정 (산출물의 sign-off 기록 절). design 단계는
[`M-010`](./M-010-test-impact-design.md) 으로 이어진다.

## WBS

- **WBS-9.1** requirements 확정 — 보급 판정 기준 · 메타 검증 요구사항 ·
  이득 근거 실측 · 다음 단계(design) 진입 조건 — 산출물:
  `docs/planning/test-impact-tiering-requirements-2026-08.md`
