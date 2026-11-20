---
id: M-033
title: 2.0 허브 — implementation 1: 허브 코어 (서버 · SQLite · 프로젝트 · 콜사인 · task · 이력 · 원격 MCP 골격)
sdlc_phase: implementation
status: planned
order: 33
parallel_allowed:
  - M-007
  - M-028
deliverables:
  - workflow-source/workflow_kit/hub/
goals: [G1, G2]
---

# M-033 — 2.0 허브 — implementation 1: 허브 코어 (서버 · SQLite · 프로젝트 · 콜사인 · task · 이력 · 원격 MCP 골격)

2.0.0 로드맵 (소유자 2026-11-20: 2.0.0 = M-033~M-039 전부, 1.x 는 결함 수리만 병행 — M-007 parallel_allowed). 개념 · 결정 정본은 [`M-030`](./M-030-workflow-hub.md) · `docs/planning/workflow-hub-review-2026-11.md`.

표준 라이브러리 HTTP + SQLite 허브와 원격 MCP 골격. kit 판정 함수를 같은 프로세스에서 부른다 (H2).

## WBS

- **WBS-33.1** 서버 · SQLite · 이관 · 백업 (파일 복사) — 산출물: workflow_kit/hub/
- **WBS-33.2** 프로젝트 등록 (git 주소 정규화 · 별칭) · 콜사인 등록 · 토큰 — 산출물: workflow_kit/hub/
- **WBS-33.3** task CRUD · 이력 · version 409 · 맡기 — 산출물: workflow_kit/hub/
- **WBS-33.4** 원격 MCP 골격 — 부트스트랩 묶음 · 인증 경계 — 산출물: workflow_kit/hub/mcp
