---
id: M-048
title: 허브 오케스트레이션 — 안정화 · 2.1.0 발행
sdlc_phase: stabilization
status: in_progress
order: 48
parallel_allowed:
  - M-007
  - M-028
  - M-039
deliverables:
  - editors/vscode/package.json
  - workflow-source/releases/
goals: [G1, G3, G5]
---

# M-048 — 허브 오케스트레이션 안정화 · 2.1.0 발행

2.1 축(M-041~M-047) 을 묶어 내기 전의 안정화. 계약 정본은 `workflow-source/core/hub_orchestration_spec.md` · ADR-034.
소유자 2026-11-22: 139차 권고안대로 — main-014(Codex 커밋 경로) 결정 'A 실측 → 안 되면 B' 를 먼저, 이어 VS Code 실측 · `.vsix`, 전량 게이트는 발행 직전.

## WBS

- **WBS-48.1** VS Code 확장 실제 로드 실측 (내려받은 VS Code · xvfb — 활성화 · 명령 · webview · 상태 표시줄) · `.vsix` 패키징 — 산출물: `editors/vscode/package.json`
- **WBS-48.2** 2.1 진입 지침 판 점검 — main-014 후속(sandbox 로 push 못 하는 일하는 세션의 세션 끝 문구) — 산출물: `workflow-source/core/hub_workflow_standard.md`
- **WBS-48.3** 전량 게이트 · 2.1.0 릴리스 노트 · 발행 — 산출물: `workflow-source/releases/`
