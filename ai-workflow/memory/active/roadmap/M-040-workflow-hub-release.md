---
id: M-040
title: 2.0.0 발행 · 1.x 유지보수 줄 분기
sdlc_phase: release
status: planned
order: 40
parallel_allowed:
  - M-007
  - M-028
deliverables:
  - workflow-source/releases/
goals: [G3, G4]
---

# M-040 — 2.0.0 발행 · 1.x 유지보수 줄 분기

2.0.0 로드맵 (소유자 2026-11-20: 2.0.0 = M-033~M-039 전부, 1.x 는 결함 수리만 병행 — M-007 parallel_allowed). 개념 · 결정 정본은 [`M-030`](./M-030-workflow-hub.md) · `docs/planning/workflow-hub-review-2026-11.md`.

2.0.0 발행. 1.x 는 유지보수 줄(결함 수리만)로 분기한다.

## WBS

- **WBS-40.1** 2.0.0 릴리스 노트 · 배포 산출물 · 전환 안내 — 산출물: workflow-source/releases/
- **WBS-40.2** 1.x 유지보수 줄 분기 · 마지막 1.x 판 deprecation 안내 — 산출물: 1.x 브랜치 · 릴리스 노트
