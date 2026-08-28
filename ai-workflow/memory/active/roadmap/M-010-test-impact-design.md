---
id: M-010
title: 계층별 회귀 실행 계약 — design (ADR-028 + core 스펙 절)
sdlc_phase: design
status: planned
order: 10
parallel_allowed:
  - M-007
deliverables:
  - ai-workflow/wiki/decisions/adr-028-test-impact-meta-validation.md
  - workflow-source/core/test_impact_tiering_spec.md
---

# M-010 — 계층별 회귀 실행 계약 — design

requirements sign-off ([`M-009`](./M-009-test-impact-requirements.md) →
[`requirements 문서`](../../../../docs/planning/test-impact-tiering-requirements-2026-08.md)
sign-off 기록 절, 2026-08-28) 를 받는 design 단계. sign-off 가 형태를 고정한
것 위에서 남은 설계 결정을 ADR 로 내린다:

- **ADR-028 결정 대상**:
  - R3.2 메타 검증 **채취 방식** (Python audit hook / `open` 계측 / OS 레벨
    트레이스 중 택1 — 실측 근거 필수)
  - R1.3 전역 선언의 **이름 리터럴 최종 확정** (형태는 sign-off 로 고정:
    근거 문자열 필수인 파일 내 선언)
  - R3.3 전수/순환 **판정 기준 수치** (실측으로)
- **core 스펙 절**: `WATCHES` idiom · R1 분류 계약 · 3단 계층 계약의 kit
  표준 문서화 (R6 — 문서 위치·runner 노출 범위 포함).
- **불변**: R0 — push 게이트 전량 2축 축소 금지. design 산출물의 어떤 결정도
  게이트 경로의 검사 개수를 줄이지 않는다.

구현(M-011 예정)은 design 산출물이 채워지기 전에 열지 않는다 (SDLC 온보딩
기본 순서).

## WBS

- **WBS-10.1** ADR-028 작성 — 채취 방식 실측 비교 + 전역 선언 리터럴 +
  전수/순환 기준 — 산출물: `adr-028-test-impact-meta-validation.md`
- **WBS-10.2** core 스펙 절 초안 — 분류 계약·계층 계약의 kit 표준화 —
  산출물: `test_impact_tiering_spec.md`
