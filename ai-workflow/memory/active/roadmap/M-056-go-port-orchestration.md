---
id: M-056
title: 2.x 전면 Go 전환 — implementation S2-c (세션 · 받은편지함 · 오케스트레이션)
sdlc_phase: implementation
status: done
order: 56
parallel_allowed:
  - M-007
  - M-028
  - M-039
deliverables:
  - hub-go/internal/store/
  - hub-go/internal/tools/
  - workflow-source/tests/check_hub_core.py
goals: [G1, G3, G5]
---

# M-056 — S2-c 세션 · 받은편지함 · 오케스트레이션

설계 정본: [`hub_go_spec.md`](../../../../workflow-source/core/hub_go_spec.md) §2 · §5.3 · §5.4 · §8, 계약 정본: [`hub_orchestration_spec.md`](../../../../workflow-source/core/hub_orchestration_spec.md). Python 허브의 세션 등록/종료, 받은편지함, 보고, 오케스트레이터 lease와 배정 도구를 Go 판에 구현한다. 기존 74개 도구 스키마와 HTTP/MCP 경계는 유지하고, 해당 도구의 Go 501 응답을 없앤다.

## WBS

- **WBS-56.1** 세션 · 받은편지함 저장 계층과 도구 구현 (`hub_session_start/update/list/end`, `hub_wait`, `hub_inbox_ack/list`, `hub_report`) — Go 단위 검사로 권한·상태 전이를 고정한다.
- **WBS-56.2** 오케스트레이터 lease · 배정 도구 구현 (`hub_orch_declare/transfer/release/halt/assign/recall/message`, 세션/중지 요청, 승인) — Go 단위 검사로 권한·lease·승인 전이를 고정한다.
- **WBS-56.3** `check_hub_core` 에 세션 · 오케스트레이션 실사용 흐름을 추가하고 Python/Go 적합성 모두 통과시킨다.

## 완료 기록

- 2026-11-23: WBS-56.1~56.3 완료. 세션/인박스 저장 계층, lease·배정·승인 도구 및 case 11 실사용 검증을 Go에 포팅했다.
- 검증: `go test ./...`, `go vet ./...`, `WORKFLOW_HUB_IMPL=both python3 workflow-source/tests/check_hub_core.py` (20/20).
