---
id: M-046
title: 허브 오케스트레이션 — implementation 3 (PC 중계 — 등록 · 허용 목록 · 세션 요청/승인 · 어댑터 · 로컬 웹)
sdlc_phase: implementation
status: done
order: 46
parallel_allowed:
  - M-007
  - M-028
  - M-039
deliverables:
  - workflow-source/workflow_kit/relay/runner.py
  - workflow-source/tests/check_hub_relay.py
goals: [G1, G5]
---

# M-046 — 허브 오케스트레이션 implementation 3 (PC 중계)

계약 정본: `workflow-source/core/hub_orchestration_spec.md` §9 · §10 (ADR-034). PC 마다 하나 뜨는 중계가 중앙 허브로 나가는
연결만 열어 승인된 세션 요청 · 메시지를 가져오고, 허용 목록 안에서 하네스 세션을 띄우고 · 넣고 · 멈춘다.

**종결 (2026-11-22)**: TASK-2026-11-22-main-011 (중계 본체, check_hub_relay · 되주입 13/13) · main-013 (실제 어댑터 실측 — Claude · Codex 전 과정, 로컬 화면). 후속 main-014.

## WBS

- **WBS-46.2** 허브 쪽 중계 API(판 12 · 등록 · 긴 폴링 · 결과 · 세션 요청/승인 · 세션 잇기) + 중계 패키지(`hub relay` · 허용 목록 · 어댑터 · 게이트 검사) — 옛 46.1 을 합침 — 산출물: `hub/relay.py` · `workflow_kit/relay/` · `tests/check_hub_relay.py`
- **WBS-46.3** 로컬 웹 화면 · 실제 하네스 어댑터 실측 (게이트 밖) — 산출물: `workflow_kit/relay/ui.py` · 요구 문서 실측 절
