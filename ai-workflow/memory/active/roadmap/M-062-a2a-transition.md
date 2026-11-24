---
id: M-062
title: 허브 통신의 A2A 1.0 전환
sdlc_phase: implementation
status: in_progress
order: 62
parallel_allowed:
  - M-007
  - M-028
  - M-039
  - M-057
  - M-059
deliverables:
  - docs/planning/a2a-transition-2026-11.md
  - docs/HUB_OPERATIONS.md
goals: [G1, G3, G5]
---

# M-062 — 허브 통신의 A2A 1.0 전환

소유자 지시(2026-11-24): 승인 같은 에이전트 통신을 정규 A2A 로 구성한다. 요구 · 설계 초안과 열린 결정은
[`a2a-transition-2026-11.md`](../../../../docs/planning/a2a-transition-2026-11.md). 사람 로그인 승인 기록이 유일한 권한 근거라는
규칙은 그대로다 — A2A Task 상태는 권한이 아니다.

## WBS

- **WBS-62.1** 규격 조사, 요구·설계와 열린 결정 확정, ADR — 산출물: `a2a-transition-2026-11.md`
- **WBS-62.2** 승인 A2A — Agent Card, Task 생성·조회·취소, `hub_client.py` 연결, Python/Go parity
- **WBS-62.3** 알림·메시지 — 스트림 구독과 콜사인 간 메시지
- **WBS-62.4** 작업 배정 중개 확장과 기존 MCP 통신 도구의 은퇴 판단
