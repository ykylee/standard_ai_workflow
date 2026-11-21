---
id: M-038
title: 2.0 허브 — implementation 6: 1.x 전환 · 1.x 유지보수 판
sdlc_phase: implementation
status: in_progress
order: 38
parallel_allowed:
  - M-007
  - M-028
  - M-037
deliverables:
  - workflow-source/workflow_kit/hub/
goals: [G3, G4]
---

# M-038 — 2.0 허브 — implementation 6: 1.x 전환 · 1.x 유지보수 판

2.0.0 로드맵 (소유자 2026-11-20: 2.0.0 = M-033~M-039 전부, 1.x 는 결함 수리만 병행 — M-007 parallel_allowed). 개념 · 결정 정본은 [`M-030`](./M-030-workflow-hub.md) · `docs/planning/workflow-hub-review-2026-11.md`.

1.x 프로젝트는 첫 2.0 부트스트랩에서 전환 (H13). 1.x 유지보수 판은 '허브로 옮김' 표식에서 쓰기를 거절하고 2.0 을 안내.

## WBS

- **WBS-38.1** 1.x 감지 · 전환 계획 · 들여오기 (branch → 콜사인 · 보관 기록 매핑) — 산출물: workflow_kit/hub/
- **WBS-38.2** git 쪽 '허브로 옮김' 표식 · 되돌리기 — 산출물: workflow_kit/hub/
- **WBS-38.3** 1.x 유지보수 판 — 표식 거절 · session-start 2.0 안내 · deprecation (G4) — 산출물: 1.x 릴리스 노트
