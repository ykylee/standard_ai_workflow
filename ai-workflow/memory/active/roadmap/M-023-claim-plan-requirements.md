---
id: M-023
title: 주장 트리 계획 — requirements (A 계약 + B 브리지, 결정 D1~D5)
sdlc_phase: requirements
status: planned
order: 23
parallel_allowed:
  - M-007
deliverables:
  - docs/planning/claim-plan-requirements-2026-11.md
goals: [G2, G5]
---

# M-023 — 주장 트리 계획 — requirements

concept 종결([`M-022`](./M-022-claim-plan.md) →
[`concept 문서`](../../../../docs/planning/html-plan-absorption-review-2026-11.md) §10, 2026-11-12) 을 받는
requirements 단계. 소유자 결정 D1~D5(§7 기본값 전부)가 고정한 범위 위에서 요구 사항과 숫자를 확정한다:

- **먼저 잴 것 (concept §8)**: html-plan `pack.mjs` 를 격리 디렉터리에서 example · 뼈대로 실측(자리표시가
  규칙 3 오류인지, 한국어 STE 경고) · 옛 리더가 모르는 `- Claims:` 줄을 만났을 때의 동작 · 주장 길이 예산
  (이 저장소 완료 기준 길이 분포) · 응답 크기 상한.
- **확정할 것**: 필드 문법 · 린트 L1~L8 강도 · 게이트 문구 · verifier 묶음 형식 · export 매핑 · import 대조 ·
  닫힘 조건 · 응답 보관 경로 · state.json 반영 여부 · design 진입 조건.

## WBS

- **WBS-23.1** requirements 확정 — §8 미실측 실측 + A · B 요구 사항 · 숫자 · design 진입 조건 — 산출물:
  `docs/planning/claim-plan-requirements-2026-11.md`
