---
id: M-035
title: 2.0 허브 — implementation 3: 콜사인별 기억 · 로드맵 · 판정
sdlc_phase: implementation
status: planned
order: 35
parallel_allowed:
  - M-007
  - M-028
deliverables:
  - workflow-source/workflow_kit/hub/
goals: [G2, G5]
---

# M-035 — 2.0 허브 — implementation 3: 콜사인별 기억 · 로드맵 · 판정

2.0.0 로드맵 (소유자 2026-11-20: 2.0.0 = M-033~M-039 전부, 1.x 는 결함 수리만 병행 — M-007 parallel_allowed). 개념 · 결정 정본은 [`M-030`](./M-030-workflow-hub.md) · `docs/planning/workflow-hub-review-2026-11.md`.

handoff · state · 작업 이력은 콜사인별 (H8), 로드맵은 허브 (D8), done 게이트 · 계획 린트 · 결정 응답은 kit 판정.

## WBS

- **WBS-35.1** 콜사인별 handoff · state · 세션 기록 · 콜사인 보관 (G1 · G2) — 산출물: workflow_kit/hub/
- **WBS-35.2** 로드맵 · 마일스톤 · WBS · 진척 파생 (D8) — 산출물: workflow_kit/hub/
- **WBS-35.3** 계획 린트 · done 게이트 · 결정 응답 (plan-response/1) — 산출물: workflow_kit/hub/
