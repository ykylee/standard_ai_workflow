---
id: M-053
title: 허브(/ui/) · PC 중계 화면 UI/UX 완성 — 오케스트레이션 판 · 워크벤치식 결정 UX · 중계 무깜빡임 화면
sdlc_phase: implementation
status: done
order: 53
parallel_allowed:
  - M-007
  - M-028
  - M-039
deliverables:
  - workflow-source/workflow_kit/hub/ui.py
  - workflow-source/workflow_kit/hub/static/hub.js
  - workflow-source/workflow_kit/relay/ui.py
  - hub-go/internal/relay/ui.go
goals: [G2, G3, G5]
---

# M-053 — 허브(/ui/) · PC 중계 화면 UI/UX 완성

설계 정본: [`hub_orchestration_spec.md`](../../../../workflow-source/core/hub_orchestration_spec.md) §10 · [`hub_spec.md`](../../../../workflow-source/core/hub_spec.md) §4.6~4.7 · [`plan_workbench_spec.md`](../../../../workflow-source/core/plan_workbench_spec.md) §4~6 (ADR-032 · ADR-033 · ADR-034). S2(허브 Go 판 이식) 전에 중앙 `/ui/` 와 PC 중계 로컬 화면(Python · Go)의 UI/UX 및 HTTP 계약을 확정·구현한다.

## WBS

- **WBS-53.1** 중앙 허브 `/ui/` 2.1 오케스트레이션 판(세션 5상태·unknown · 배정·미전달 · 승인 대기 결정 · 정지 스위치 · lease · 중계 초대/거두기) · 로드맵 화면 · 1.x 워크벤치 UX 복원(상단 KPI · 주장 트리 · 라디오 카드 결정 · `opened` 자동 감지 · `dirty` 보호 자동 새로고침 · 좁은 폭 열 보존) — 산출물: `workflow-source/workflow_kit/hub/ui.py`
- **WBS-53.2** PC 중계 로컬 화면(`127.0.0.1`, Python + Go 동시) 무깜빡임 `fetch('/api/state')` 갱신 · 로컬 허용 경로(`path`)/가동 세션 수/하네스 표시 · 중앙 허브 딥링크 · 로컬 개별 세션 강제 종료(`POST /api/sessions/{req}/stop`) — 산출물: `hub-go/internal/relay/ui.go`
