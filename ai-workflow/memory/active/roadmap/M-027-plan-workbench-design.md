---
id: M-027
title: 계획·진척 워크벤치 — design (ADR-032 + core 스펙)
sdlc_phase: design
status: planned
order: 27
parallel_allowed:
  - M-007
deliverables:
  - ai-workflow/wiki/decisions/adr-032-plan-workbench.md
  - workflow-source/core/plan_workbench_spec.md
goals: [G2, G5]
---

# M-027 — 계획·진척 워크벤치 — design

requirements sign-off ([`M-025`](./M-025-plan-workbench-requirements.md) →
[`requirements 문서`](../../../../docs/planning/plan-workbench-requirements-2026-11.md) §13, 2026-11-13) 를 받는 design 단계.
소유자 결정(2026-11-13): design 은 **ADR 둘로 순차** — [`M-026`](./M-026-claim-plan-design.md) 의 ADR-031 이 응답 형식 · 받은편지함 ·
`plan-import` 계약을 먼저 정하고, 이 마일스톤의 ADR-032 가 그 계약을 **소비**한다. **M-026 뒤에 연다.**

- **ADR-032 결정 대상**: 서버 모듈 배치와 CLI 등록 · 토큰 설정의 형태 · 세션 표 · 화면 렌더러(주장 트리 · 결정 폼 · 진척) ·
  내장 정적 자원 · `.workbench/` 와 받은편지함의 git 무시 수단 · MCP 도구 2개 · §11.1 문구와 스킬 · 검사 구성.
- **먼저 잴 것 (requirements R11)**: nginx · Caddy 실물(docker) + 실제 브라우저에서 쿠키 `Path` · `SameSite` · 리다이렉트
  (소유자 결정 2026-11-13: docker 로 잰다).
- **재지 않는 것 (소유자 결정 2026-11-13)**: Codex `UserPromptSubmit` 출력의 모델 주입 — hook 알림 층(W1 ②)은 보류로 두고
  당겨 오기(①)만 설계한다. 나중에 별도 task 로 재고 더할 수 있다.
- **ADR-031 이 넘긴 것**: MCP 도구 `plan_inbox` · `plan_import` (결정 23) · 응답 파일의 줄바꿈을 LF 로 고치는 쓰는 쪽 의무 (결정 25) ·
  번호는 `received_at` 의 epoch 마이크로초이고 접미사를 통틀어 유일 (결정 13 · 24 — 워크벤치 requirements R5.3-7 의 카운터를 대체).
- **불변**: requirements R0.

## WBS

- **WBS-27.1** design 확정 — ADR-032 + core 스펙 — 산출물: `ai-workflow/wiki/decisions/adr-032-plan-workbench.md`,
  `workflow-source/core/plan_workbench_spec.md`
