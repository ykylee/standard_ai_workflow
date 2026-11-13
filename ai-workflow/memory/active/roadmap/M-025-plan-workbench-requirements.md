---
id: M-025
title: 계획·진척 워크벤치 — requirements (웹 · 받은편지함 · 알림 층, 결정 W1~W5, 하네스 중립)
sdlc_phase: requirements
status: done
order: 25
parallel_allowed:
  - M-007
deliverables:
  - docs/planning/plan-workbench-requirements-2026-11.md
goals: [G2, G5]
---

# M-025 — 계획·진척 워크벤치 — requirements

concept 종결([`M-024`](./M-024-plan-workbench.md) →
[`concept 문서`](../../../../docs/planning/plan-workbench-review-2026-11.md) §10, 2026-11-12) 을 받는
requirements 단계. **[`M-023`](./M-023-claim-plan-requirements.md) 뒤에 연다** (W4) — 받은편지함 · `plan-import` 는
M-023 이 확정하는 안 A 필드와 응답 형식 위에 선다.

- **불변**: kit 에 Claude 전용 기능을 두지 않는다 · 웹 서버는 받은편지함만 쓴다 · 응답 = 데이터 · 접속 위치 무가정 · 항상 인증(viewer/approver) · bind 기본값은 loopback ·
  진척은 생성물과 verifier 판정에서만.
- **먼저 잴 것 (concept §9)**: 하네스별 프롬프트 직전 hook 의 존재 · 의미(W1 ② 조건), 받은편지함 커밋 흐름,
  같은 브랜치 두 세션의 import 원자성, 한글 Windows 에서 포트 · 브라우저 열기 · 경로, 경로 접두사 리버스 프록시 · 클라우드 포트 공유 뒤 쿠키 · 리다이렉트 (concept §11.6).
- **확정할 것**: 경로 · 응답 형식 · 토큰 · 본문 상한 · 열림 측정(W2) · 진척 화면 표시 규칙 · MCP 도구 이름 ·
  §11.1 명령 문구 · design 진입 조건.

**종결 (2026-11-13)**: 소유자 sign-off — Q1 · Q2 권고안대로 (requirements 문서 §13). 실측: 프롬프트 직전 hook 의 주입이 실측된 하네스는
Claude Code 하나 → W1 ② 는 지금 만들지 않는다 / 받은편지함은 다 쓴 뒤 공개 · import 는 잠금 아래 배타 이동 / 접두사 프록시 뒤에서는
상대 경로 + 쿠키 `Path` = 접두사. design 은 [`M-026`](./M-026-claim-plan-design.md) 착수 때 한 묶음으로 낼지 정한다 (R12-③).

## WBS

- **WBS-25.1** requirements 확정 — concept §9 미실측 실측 + 서버 · 응답 · 알림 · 진척 요구 사항 · design 진입 조건 —
  산출물: `docs/planning/plan-workbench-requirements-2026-11.md`
