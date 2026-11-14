---
id: M-029
title: 계획·진척 워크벤치 — implementation (이월 정리 · 서버 · 화면 · MCP · 검사)
sdlc_phase: implementation
status: in_progress
order: 29
parallel_allowed:
  - M-007
  - M-028
deliverables:
  - workflow-source/workflow_kit/workbench/server.py
  - workflow-source/workflow_kit/tools/workbench.py
goals: [G2, G5]
---

# M-029 — 계획·진척 워크벤치 — implementation

design 승인 ([`M-027`](./M-027-plan-workbench-design.md) → ADR-032 accepted 2026-11-13, 계약은
`workflow-source/core/plan_workbench_spec.md`) 을 받는 구현 단계. ADR-032 결정 23 대로 **두 단계**로 낸다.

- **불변**: 스펙 §1. 서버가 쓰는 워크플로우 상태는 받은편지함 하나다.
- **실물 측정은 게이트 밖**: 서버의 경로 · 쿠키 코드를 바꾸면 requirements §1.4 의 절차(nginx · Caddy docker + 실제 브라우저)를 다시 돌린다.
- **Windows(NTFS)**: 포트 bind · 토큰 파일 모드 · 콘솔 인코딩은 구현 뒤 Windows 호스트에서 잰다 — M-028 의 WBS-28.3 과 같은 호스트 · 같은 세션.

## WBS

- **WBS-29.1** ① 이월 정리 — `plan_responses.inbox_census` 와 호출자 전환(결정 16) · `plan-import` 의 `pending_responses` / `remaining_after`(결정 17) ·
  우회 검출의 받은편지함 행과 `plan-status` warnings(결정 18) · 정리 거리 일곱(결정 24) · 게이트의 배치 warnings(결정 25) · `claim_plan_spec` §4 · §10 반영
- **WBS-29.2** ② 서버 · 화면 · MCP `plan_inbox` · `plan_import` · 정본 §11.1 · 스킬 `workbench` · 검사 넷
  (`check_workbench_auth` · `check_workbench_proxy` · `check_workbench_write` · `check_workbench_views`)
