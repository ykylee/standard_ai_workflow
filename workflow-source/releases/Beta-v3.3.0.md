# Beta v3.3.0 — A2A 1.0 승인 Task (2026-11-24)

> **상태: 실환경 pilot용 pre-release.** GitHub Release는 prerelease로 표시하고 안정판 latest는 v2.1.0에 둔다.

## 변경

- 허브가 A2A(Agent2Agent) 1.0 서버가 됐다. Agent Card(`<공개 주소>/.well-known/agent-card.json`)와 JSON-RPC(`<공개 주소>/a2a`)를 Python·Go에서 제공한다.
- 승인 요청은 `AUTH_REQUIRED` Task다. 사람이 로그인해 승인하면 `COMPLETED`와 승인 아티팩트, 거절하면 `REJECTED`, 요청자가 거두면 `CANCELED`가 된다. `SendMessage`·`GetTask`·`ListTasks`·`CancelTask`를 지원한다.
- Task 상태는 권한이 아니다. 실행은 아티팩트의 `approval_id`로만 열리고, 그 승인은 계정 로그인으로만 만들어진다.
- `hub_client.py`에 `a2a send|get|list|cancel`을 넣고, `migrate request`가 A2A로 요청한다. `migrate import`는 A2A Task ID를 받는다.
- Go 확인 요청의 글자 수 제한이 바이트가 아니라 글자를 센다(Python과 같다).

## 검증

- 누적 smoke **358/358 PASS**
- `check_hub_a2a`(13)가 Python·Go 실프로세스를 같은 시나리오로 재고 응답을 대조한다. 되주입 5건을 잡는다.
- 공식 SDK 클라이언트(Python `a2a-sdk` 1.3.1, Go `a2a-go` v2.9.0)로 두 허브에 붙어 카드 해석·생성·조회·목록·취소·승인 아티팩트를 왕복했다(1회 실측, 상시 검사 아님).

## 운영 범위

- 평가용 pre-release다. 스트리밍·푸시 알림·HTTP+JSON·gRPC·에이전트 간 메시지·작업 배정은 아직 없다. 기존 MCP 승인·메시지 도구는 그대로 쓸 수 있다.
- `A2A-Version: 1.0`이 없는 요청은 `-32009`로 거절한다.
- DB 판 17 → 18 migration이 실행된다. 시작 전에 백업한다.

## Bidirectional link audit

_자동 emit (Phase 13 AC4+, 2026-11-24T14:35:39Z)_

- total wiki pages: **104**
- total memory entries: **30**
- symmetric links: **0**
- asymmetric count: **2**
- wiki pages with related memory: **0**
- memory entries with mentioned wiki: **2**
- is_symmetric: **False**

### Asymmetric links (advisory)

- `memory_only`: `MEM-2026-07-09-001` ↔ `topics/workflow-audit-2026-07-09.md`
- `memory_only`: `MEM-2026-08-10-001` ↔ `topics/memory-index-retrospective-2026.md`
