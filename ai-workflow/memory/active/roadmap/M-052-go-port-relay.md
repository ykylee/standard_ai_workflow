---
id: M-052
title: 2.x 전면 Go 전환 — implementation S1 (PC 중계 Go 판)
sdlc_phase: implementation
status: in_progress
order: 52
parallel_allowed:
  - M-007
  - M-028
  - M-039
deliverables:
  - hub-go/go.mod
  - hub-go/internal/relay/
goals: [G1, G5]
---

# M-052 — S1 PC 중계 Go 판

설계 정본: [`hub_go_spec.md`](../../../../workflow-source/core/hub_go_spec.md) §6 · §7 · §8 (S1 완료 기준). ADR-035.

## WBS

- **WBS-52.1** `hub-go/` 모듈 뼈대 · `cmd/workflow-hub` · `check_go_build` (vet · test · 6 대상 빌드, Go 없으면 미측정) — 산출물: `hub-go/go.mod`
- **WBS-52.2** 중계 Go 판 — CLI · 설정 형식 동일 · 긴 폴링 · 어댑터 claude-code · codex · fake · 로컬 화면 — 산출물: `hub-go/internal/relay/`
- **WBS-52.3** `check_hub_relay` 구현 스위치(`WORKFLOW_RELAY_IMPL`) · 실제 어댑터 실측(Claude Code · Codex) — 산출물: `workflow-source/tests/check_hub_relay.py`
