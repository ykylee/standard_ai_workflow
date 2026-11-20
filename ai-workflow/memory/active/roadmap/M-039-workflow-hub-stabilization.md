---
id: M-039
title: 2.0 허브 — stabilization (하네스 실측 · 이 저장소 전환 · arcturus 이전)
sdlc_phase: stabilization
status: planned
order: 39
parallel_allowed:
  - M-007
  - M-028
deliverables:
  - docs/planning/workflow-hub-requirements-2026-11.md
goals: [G1, G2]
---

# M-039 — 2.0 허브 — stabilization (하네스 실측 · 이 저장소 전환 · arcturus 이전)

2.0.0 로드맵 (소유자 2026-11-20: 2.0.0 = M-033~M-039 전부, 1.x 는 결함 수리만 병행 — M-007 parallel_allowed). 개념 · 결정 정본은 [`M-030`](./M-030-workflow-hub.md) · `docs/planning/workflow-hub-review-2026-11.md`.

하네스별 원격 MCP 실측, 이 저장소를 2.0 으로 전환 (자기 적용), arcturus 의 task · handoff 를 kit 허브로 (D7).

## WBS

- **WBS-39.1** 하네스별 실측 — 원격 MCP · 부트스트랩 · 세션 시작 확인 (Linux · macOS · Windows) — 산출물: 실측 기록
- **WBS-39.2** 이 저장소 2.0 전환 (자기 적용) — 산출물: 전환 기록
- **WBS-39.3** arcturus-port 이전 — task · handoff · 지침 (위키 · 실측 화면은 arcturus 에) — 산출물: 이전 기록
