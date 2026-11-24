# 허브 통신의 A2A 1.0 전환 — concept · 요구 · 설계 초안

- 문서 목적: 승인과 에이전트 통신을 표준 A2A(Agent2Agent) 1.0 으로 옮기는 범위 · 요구 · 계약 · 열린 결정을 정한다.
- 범위: 허브 A2A 서버(Python · Go), 승인 Task, 에이전트 간 메시지, 작업 배정. MCP 의 기억 · 지식 · task 도구는 대상이 아니다.
- 대상 독자: 소유자, 허브 구현자
- 상태: draft
- 최종 수정일: 2026-11-24
- 관련 문서: `../../workflow-source/core/hub_orchestration_spec.md`, `../../workflow-source/core/hub_spec.md`, `./plan-workbench-review-2026-11.md`

## 1. 배경

- 소유자 지시(2026-11-24): 승인 같은 에이전트 통신을 정규 A2A 로 구성한다.
- 현재 허브의 받은편지함은 자체 규약이다. Agent Card · A2A Task · A2A 바인딩이 없다.
- 2026-11 워크벤치 검토는 A2A 를 보류하며 재검토 조건으로 "task 를 A2A Task 로, 열린 결정을 중단 상태로 사상" 을 남겼다.

## 2. 확인한 규격 (1차 출처, 2026-11-24)

출처: `a2a.proto` (package `lf.a2a.v1`), <https://a2a-protocol.org/latest/specification/>, a2a-go · a2a-python 저장소.

| 항목 | 값 |
|---|---|
| 판 | 규격 페이지 1.0.0, GitHub 릴리스 v1.0.1 — 협상값은 `1.0` |
| JSON-RPC 메서드 | `SendMessage` · `GetTask` · `ListTasks` · `CancelTask` · `SubscribeToTask` · `SendStreamingMessage` 외 |
| 중단 상태 | `TASK_STATE_INPUT_REQUIRED` · `TASK_STATE_AUTH_REQUIRED` |
| 종료 상태 | `COMPLETED` · `FAILED` · `CANCELED` · `REJECTED` |
| 오류 | -32001 TaskNotFound … -32009 VersionNotSupported |
| SDK | Go `github.com/a2aproject/a2a-go/v2` v2.9.0 (Go 1.26, gRPC · protobuf · OpenTelemetry 의존), Python `a2a-sdk` v1.3.1 (pydantic · protobuf 의존) |

규격이 정하지 않았거나 엇갈린 것:

- `A2A-Version` 헤더가 **없을 때** (빈 값은 0.3 으로 정해져 있다).
- `AUTH_REQUIRED` → `COMPLETED` / `REJECTED` 전이표가 없다. 금지 문구도 찾지 못했다.
- HTTP+JSON 의 `:subscribe` 동사(proto GET, 본문 POST)와 오류 본문 형식. JSON-RPC 에는 걸리지 않는다.
- 적합성 시험 도구(TCK)의 실행법은 확인하지 못했다.

## 3. 요구

- **RA1** 허브는 Agent Card 를 낸다. 공개 주소가 하위 경로(`…/workflow`)이므로 `<공개 주소>/.well-known/agent-card.json` 에 두고 클라이언트에는 카드 주소를 직접 준다. 도메인 뿌리의 카드는 프록시 소유자의 몫이다.
- **RA2** 신원은 HTTP Bearer 콜사인 토큰이다. 메시지 본문의 신원 주장은 쓰지 않는다.
- **RA3** 승인 요청은 `SendMessage` 로 만들고 Task 는 `AUTH_REQUIRED` 가 된다. 상태 메시지에 승인 화면 주소와 허브가 계산한 실행 요약을 싣는다.
- **RA4** 승인은 사람의 계정 로그인으로만 한다. Task 상태는 권한이 아니며 `approval_grant` 가 유일한 근거다 (규격 §7.6.4 와 같은 방향).
- **RA5** 승인이면 `COMPLETED` 와 `approval_id` 를 담은 data 아티팩트, 거절이면 `REJECTED`, 요청자가 취소하면 `CANCELED` 다. 만료는 승인 기록에만 반영한다.
- **RA6** 남의 Task 는 존재 여부를 드러내지 않고 TaskNotFound 로 답한다.
- **RA7** Python 과 Go 가 같은 입력에 같은 응답을 낸다. 공식 SDK 클라이언트를 외부 증인으로 쓴다.
- **RA8** 하네스가 A2A 를 직접 말하지 못해도 `hub_client.py` 로 쓸 수 있다.

## 4. 설계 초안

- 바인딩: **JSON-RPC 하나**부터 (`<공개 주소>/a2a`). 카드의 `supportedInterfaces` 에 `JSONRPC` · `1.0` 만 선언한다. streaming · pushNotifications 는 구현 전까지 false.
- 구현: 서버는 표준 라이브러리로 두 런타임에 직접 쓴다 — 필요한 표면이 작고, SDK 는 허브에 없던 gRPC · protobuf · OpenTelemetry 의존을 들인다. SDK 는 시험에서 클라이언트로만 쓴다.
- 판 협상: `1.0` 만 받는다. 없거나 비면 0.3 으로 보고 `-32009`.
- 확장: 실행 승인은 `https://github.com/ykylee/standard_ai_workflow/a2a/ext/execution-approval/v1` 로 선언하고 data part 에 `action` 을 싣는다. required 는 false.
- 저장: 새 표 `a2a_task` (id · context_id · project · 요청 콜사인 · 종류 · 참조 · 상태 · 시각). 승인 Task 는 `approval_grant` / 확인 요청을 참조하고 상태를 거기서 파생한다 — 상태를 두 벌 두지 않는다.
- 멱등: 같은 콜사인의 같은 `messageId` 는 같은 Task 를 돌려준다.

| 단계 | 내용 |
|---|---|
| A1 승인 | Agent Card, `SendMessage` · `GetTask` · `ListTasks` · `CancelTask`, `hub_client.py a2a …` |
| A2 알림 · 메시지 | `SubscribeToTask` · `SendStreamingMessage`, 콜사인 앞 메시지 |
| A3 배정 | 허브가 중개하는 배정 확장. PC 세션은 A2A 서버가 아니라 허브에서 가져가므로 표준만으로는 방향이 맞지 않는다 |
| A4 정리 | 기존 MCP 통신 도구의 은퇴 판단 |

## 5. 열린 결정

- **D1** 기존 MCP 승인 · 메시지 도구: 기본값 A4 까지 병행 (같은 저장소를 쓴다) / 즉시 대체.
- **D2** 서버 구현: 기본값 표준 라이브러리 직접 + SDK 는 시험 증인 / SDK 서버 채택.
- **D3** 승인 완료 상태: 기본값 `COMPLETED` + `approval_id` 아티팩트 / 실행 자체를 Task 로 이어 `WORKING` 을 거침.
- **D4** 판 번호: 기본값 3.3.0.

## 6. 위험

- 규격 빈칸(§2)을 허브가 정한 것은 카드 문서에 적고, SDK 클라이언트 왕복으로 상호운용을 잰다.
- 하네스(Claude Code · Codex)가 A2A 를 직접 지원하는지 확인하지 않았다.
- 익명 등록이 열린 공개 허브에 새 표면이 생긴다 — A2A 는 콜사인 토큰 없이는 카드만 낸다.
