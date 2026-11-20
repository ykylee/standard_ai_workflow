---
id: M-034
title: 2.0 허브 — implementation 2: 부트스트랩 · 공유 지침 · 세션 시작 확인
sdlc_phase: implementation
status: planned
order: 34
parallel_allowed:
  - M-007
  - M-028
deliverables:
  - workflow-source/workflow_kit/hub/
goals: [G1, G2]
---

# M-034 — 2.0 허브 — implementation 2: 부트스트랩 · 공유 지침 · 세션 시작 확인

2.0.0 로드맵 (소유자 2026-11-20: 2.0.0 = M-033~M-039 전부, 1.x 는 결함 수리만 병행 — M-007 parallel_allowed). 개념 · 결정 정본은 [`M-030`](./M-030-workflow-hub.md) · `docs/planning/workflow-hub-review-2026-11.md`.

kit 없는 환경이 허브 주소 하나로 등록 · 합류 · 지침 셋업까지 간다 (H4 · H5 · H6 · H9 · H11).

## WBS

- **WBS-34.1** 부트스트랩 흐름 — 등록 · 합류 · `.gitignore` 확인 (H9) · 쓸 파일 + 해시 반환 · 확인 도구 (I1) — 산출물: workflow_kit/hub/
- **WBS-34.2** 지침 — 표준 규칙(허브판) · 프로젝트 지침 · 하네스 어댑터 렌더링 · 판 · 로컬 수정 감지 — 산출물: workflow_kit/hub/
- **WBS-34.3** 세션 시작 확인 — 허브 상태 + 저장소 대조 보고 (H11) · 하네스별 MCP 등록 안내 (I4) — 산출물: workflow_kit/hub/
