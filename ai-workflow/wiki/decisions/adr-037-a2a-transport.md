---
type: decision
status: accepted
adr_id: ADR-037
decided_at: 2026-11-24
alternatives_considered: [keep-mcp-inbox, sdk-server, replace-mcp-immediately, rest-or-grpc-binding]
related_pages: [decisions/adr-034-hub-orchestration, decisions/adr-035-go-runtime]
created: 2026-11-24
updated: 2026-11-25
r9_skip: true
---

# ADR-037: 허브의 승인 · 에이전트 통신을 A2A 1.0 으로 옮긴다

## Status

**Accepted** (2026-11-24, TASK-2026-11-24-main-016) — 소유자가 D1~D4 를 권장안대로 확정. 요구 · 설계: [`a2a-transition-2026-11.md`](../../../docs/planning/a2a-transition-2026-11.md).

## Context

- 허브 받은편지함은 자체 규약이라 다른 벤더의 에이전트가 붙을 수 없다. ADR-034 는 A2A 를 첫 판에서 뺐다.
- 승인에는 '사람이 봤다' 는 증거가 필요하다. A2A 는 상태 전이만으로는 권한이 아니라고 정한다(규격 §7.6.4) — 로그인 승인 기록과 방향이 같다.

## Decision

1. 허브가 A2A 1.0 서버다. JSON-RPC 바인딩 하나(`/a2a`)와 Agent Card(`<공개 주소>/.well-known/agent-card.json`)로 시작한다.
2. 승인 요청은 `AUTH_REQUIRED` Task 다. 승인하면 `COMPLETED` 와 `approval_id` 아티팩트, 거절하면 `REJECTED`, 거두면 `CANCELED`. 상태는 확인 요청에서 파생하고 따로 저장하지 않는다.
3. 실행 권한의 근거는 `approval_grant` 뿐이다. 사람의 계정 로그인으로만 열린다.
4. 신원은 HTTP Bearer 콜사인 토큰이다. 남의 Task 는 TaskNotFound 로 답한다.
5. 서버는 두 런타임에 표준 라이브러리로 직접 쓰고, 공식 SDK 는 상호운용 시험의 클라이언트로만 쓴다.
6. `A2A-Version` 이 없거나 `1.0` 이 아니면 `-32009` 다 (없는 경우는 규격에 없어 0.3 으로 본다).
7. 기존 MCP 통신 도구는 전환이 끝날 때까지 병행한다. 작업 배정은 중개 확장을 따로 설계한다.

8. (2026-11-25) 같은 프로젝트의 콜사인은 누구나 메시지를 주고받는다. 글은 자료이고 권한을 주지 않으며, 받은편지함과 다른 칸(`a2a_messages`)으로 전달하고 대기를 깨우지 않는다. 답은 Task당 한 번이다.
9. (2026-11-25) 스트림은 SSE이고 한 연결 50초에서 닫는다. 토큰을 다시 확인하며 흐른다.

10. (2026-11-25) 작업 배정의 A2A 이전은 미룬다 — 배정 · 오케스트레이터 · PC 중계의 실사용이 0건이다. 기존 MCP 통신 도구는 은퇴하지 않는다 — MCP 하네스의 입구이고 A2A 와 같은 함수를 쓴다. 재검토 조건은 설계 문서 §5.1.

## Consequences

- A2A 클라이언트(공식 Python `a2a-sdk` 1.3.1 · Go `a2a-go` v2.9.0)가 그대로 붙는다.
- 푸시 · HTTP+JSON · gRPC 는 아직 없다. 카드는 구현한 능력만 선언한다.
- 공개 허브에 새 입구가 생긴다 — 카드 밖은 콜사인 토큰이 있어야 한다.
