---
id: M-003
title: refresh-state 통합 + session-start 배선
sdlc_phase: implementation
status: done
order: 3
parallel_allowed: []
deliverables:
  - workflow-source/tests/check_roadmap_wiring.py
---

# M-003 — refresh-state 통합 + session-start 배선

`wk refresh-state` 가 `roadmap_state.json` 을 state.json 과 함께 재생성하고
(별도 명령 없음 — 진입점이 둘로 갈리면 `--help` 도 갈린다), session-start 가
현재 마일스톤·SDLC 단계·다음 WBS 후보를 보고한다. 데모 휴리스틱
`milestones.py` 는 함수까지 은퇴하고 MCP `assess_milestone_progress` 를 새
정본으로 교체한다.

## WBS

- **WBS-3.1** refresh-state 통합 (roadmap_state 동시 재생성)
- **WBS-3.2** session-start 보고 + SDLC 단계 산출물 권고
- **WBS-3.3** milestones.py 은퇴 + MCP 도구 정본 교체
