---
id: M-036
title: 2.0 허브 — implementation 4: 위키 · memory_index · 들여오기/내보내기 · 오프라인
sdlc_phase: implementation
status: in_progress
order: 36
parallel_allowed:
  - M-007
  - M-028
  - M-035
deliverables:
  - workflow-source/workflow_kit/hub/
goals: [G2, G5]
---

# M-036 — 2.0 허브 — implementation 4: 위키 · memory_index · 들여오기/내보내기 · 오프라인

2.0.0 로드맵 (소유자 2026-11-20: 2.0.0 = M-033~M-039 전부, 1.x 는 결함 수리만 병행 — M-007 parallel_allowed). 개념 · 결정 정본은 [`M-030`](./M-030-workflow-hub.md) · `docs/planning/workflow-hub-review-2026-11.md`.

위키 정본 = 허브 (E1~E6), OKF 운반, git 내보내기 (D6), 로컬 보낼편지함 (D4).

## WBS

- **WBS-36.1** 위키 페이지 · ingest 묶음 · index/log 생성 · lint (E2) — 산출물: workflow_kit/hub/
- **WBS-36.2** memory_index · 양방향 링크 (E5) · 저장소 참조 sha · 미측정 표시 (E3) — 산출물: workflow_kit/hub/
- **WBS-36.3** 들여오기 · 내보내기 (OKF · git 스냅샷) · 오프라인 보낼편지함 (선택 클라이언트) — 산출물: workflow_kit/hub/
