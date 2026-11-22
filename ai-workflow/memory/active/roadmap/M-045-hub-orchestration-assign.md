---
id: M-045
title: 허브 오케스트레이션 — implementation 2 (오케스트레이터 lease · 배정 · 보고 · 정지 · 진입 규칙)
sdlc_phase: implementation
status: done
order: 45
parallel_allowed:
  - M-007
  - M-028
  - M-039
deliverables:
  - workflow-source/tests/check_hub_orch_assign.py
goals: [G1, G5]
---

# M-045 — 허브 오케스트레이션 implementation 2

계약 정본: `workflow-source/core/hub_orchestration_spec.md` §5 · §7.2 · §7.4 · §8 · §11 (ADR-034). 사람이 지정한 오케스트레이터 세션이
task 를 세션에 배정하고, 받은 세션이 수락(= 2.0 맡기)·거절하고, 보고하고, 회수 · 미확인 · 세션 끝 · 24시간 진척 없음이면 되돌아온다.
owner 는 정지 스위치를 쥔다. 진입 영역에 받은편지함 규칙. 세션 요청 · 승인은 실행 주체(중계)와 함께 M-046.

**종결 (2026-11-22)**: TASK-2026-11-22-main-010 — check_hub_orch_assign 9/9 · 되주입 16/16.

## WBS

- **WBS-45.1** lease (지정 · 인계 · 해제 · 만료) · 배정 상태 기계 (배정 · 수락=맡기 · 거절 · 미확인 · 회수 · 세션 끝 · 24시간 · 보고) · 정지 스위치 · 진입 규칙 절 — 산출물: `hub/orchestration.py` · `hub/tools.py` · `core/hub_workflow_standard.md` · `tests/check_hub_orch_assign.py`
