---
id: M-040
title: 2.0.0-beta 발행 · 1.x 유지보수 줄 분기
sdlc_phase: release
status: planned
order: 40
parallel_allowed:
  - M-007
  - M-028
  - M-038
  - M-039
deliverables:
  - workflow-source/releases/
goals: [G3, G4]
---

# M-040 — 2.0.0-beta 발행 · 1.x 유지보수 줄 분기

2.0.0 로드맵 (소유자 2026-11-20: 2.0.0 = M-033~M-039 전부, 1.x 는 결함 수리만 병행 — M-007 parallel_allowed). 개념 · 결정 정본은 [`M-030`](./M-030-workflow-hub.md) · `docs/planning/workflow-hub-review-2026-11.md`.

2.0.0 발행. 1.x 는 유지보수 줄(결함 수리만)로 분기한다.

**발행 범위 재정 (소유자 2026-11-21)** — 첫 2.0 판은 **`2.0.0-beta`**. 발행 조건에서 뺀 것:
- WBS-39.3 arcturus 이전 — 요구 R15.4 ('2.0 뒤, 발행 조건 아님') 를 따른다.
- WBS-39.1 의 macOS · Windows · 대화형 실측(main-013), WBS-39.2 의 이 저장소 표식 전환(상시 허브 위치 결정 뒤) — 발행 뒤.
- M-038 WBS-38.3 의 1.x 안내판(main-011)은 이 발행과 **같은 때** 낸다 (R16.4).
그래서 M-038 · M-039 는 `parallel_allowed` — 남은 몫이 이 발행과 함께 또는 뒤에 닫힌다. 2.0 계약의 보장 기간은 beta 를 벗는 stable 선언 때 정한다 (PURPOSE G3 2.0판).

## WBS

- **WBS-40.1** 2.0.0 릴리스 노트 · 배포 산출물 · 전환 안내 — 산출물: workflow-source/releases/
- **WBS-40.2** 1.x 유지보수 줄 분기 · 마지막 1.x 판 deprecation 안내 — 산출물: 1.x 브랜치 · 릴리스 노트
