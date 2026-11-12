---
id: M-023
title: 주장 트리 계획 — requirements (A 계약 + B 응답 반영, 결정 D1~D5, 하네스 중립)
sdlc_phase: requirements
status: done
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

- **하네스 중립 정정 (concept §11, 2026-11-12)**: 안 B 는 html-plan 플러그인 연동이 아니라 kit 워크벤치
  결정 폼 + 받은편지함 + `plan-import`(우리 응답 형식)다 — 확정은 [`M-024`](./M-024-plan-workbench.md) W5.
  html-plan `pack.mjs` 실측은 더 하지 않는다.
- **먼저 잴 것**: 옛 리더가 모르는 `- Claims:` 줄을 만났을 때의 동작 · 주장 길이 예산
  (이 저장소 완료 기준 길이 분포) · 응답 크기 상한.
- **확정할 것**: 필드 문법 · 린트 L1~L8 강도 · 게이트 문구 · verifier 묶음 형식 · 응답 형식(결정 폼) · import 대조 ·
  닫힘 조건 · 응답 보관 경로 · state.json 반영 여부 · design 진입 조건.

**종결 (2026-11-12)**: 소유자 sign-off — Q1~Q7 권고안대로 (requirements 문서 §12). 실측 3건(옛 리더는 새 라벨 줄을 무시 · 보존 →
리더 · 라이터 같은 릴리스 / 주장 80자 / 응답 64KiB). design 은 [`M-026`](./M-026-claim-plan-design.md) — M-025 뒤.

## WBS

- **WBS-23.1** requirements 확정 — §8 미실측 실측 + A · B 요구 사항 · 숫자 · design 진입 조건 — 산출물:
  `docs/planning/claim-plan-requirements-2026-11.md`
