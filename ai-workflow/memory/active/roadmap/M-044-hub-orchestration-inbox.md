---
id: M-044
title: 허브 오케스트레이션 — implementation 1 (세션 · 받은편지함 · 편승 · 대기 · 수신 확인)
sdlc_phase: implementation
status: done
order: 44
parallel_allowed:
  - M-007
  - M-028
  - M-039
deliverables:
  - workflow-source/workflow_kit/hub/orchestration.py
  - workflow-source/tests/check_hub_orch.py
goals: [G1, G5]
---

# M-044 — 허브 오케스트레이션 implementation 1

계약 정본: `workflow-source/core/hub_orchestration_spec.md` (ADR-034 accepted). 중계 없이 원격 MCP 만으로 전달이 닫히는 첫 판 —
세션이 등록되고, 받은편지함 메시지가 허브 도구 응답에 실려 가고(편승), 일 없는 세션은 대기 도구에서 깨고, 수신 확인으로 닫힌다.
배정 · 오케스트레이터 lease · 정지 스위치는 M-045, 중계는 M-046.

**종결 (2026-11-22)**: TASK-2026-11-22-main-009 — check_hub_orch 10/10 · 되주입 12/12.

## WBS

- **WBS-44.1** DB 판 11 · 세션 (등록 · 이어 붙임 · `session` 인자 · 상태 5값 · 수정 · 목록) · 받은편지함 (편승 · 실림≠소비 재전달 · 10분 미확인 · 수신 확인 · 목록) · 대기 도구 비동기 경로 — 산출물: `hub/orchestration.py` · `hub/tools.py` · `hub/app.py` · `tests/check_hub_orch.py`
