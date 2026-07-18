# ADR-003: Read-only MCP 우선 정책

- 문서 목적: standard_ai_workflow 의 MCP 서버가 read-only 우선 정책을 채택한 rationale 와 운영 impact 를 정식 기록.
- 범위: MCP 서버 6+1 종의 read-only 정책, transport 우선순위, bootstrap 시 MCP 자동 emit, create_backlog_entry 의 draft-only 예외.
- 대상 독자: maintainer, Mavis/Mavis consumer, MCP 통합자.
- 상태: Accepted (v0.5.7)
- 최종 수정일: 2026-07-18
- 관련 문서: [`../README.md`](../README.md), [`./ADR-001-source-state-knowledge-3-layer-separation.md`](./ADR-001-source-state-knowledge-3-layer-separation.md), [`./ADR-002-pydantic-v2-contract-v1-external-spec.md`](./ADR-002-pydantic-v2-contract-v1-external-spec.md), [`../../workflow-source/core/read_only_mcp_transport_promotion.md`](../../workflow-source/core/read_only_mcp_transport_promotion.md)

- **Status**: Accepted (v0.5.7, 6+1 MCP 서버 + jsonrpc-bridge / stdio-sdk 양 transport)
- **Date**: 2026-05-03 (v0.5.0 read-only MCP initial), updated 2026-05-15 (v0.5.7 read-only SDK candidate), 2026-06-01 (v0.5.7 stable)
- **Supersedes**: —
- **Superseded by**: —

## Context

`standard_ai_workflow` 의 MCP 서버는 두 가지 방향으로 발전 가능했다:

1. **양방향 (read-write)**: orchestrator 가 sub-agent / 외부 시스템에 write 명령을 내릴 수 있음. 자유도 높음.
2. **읽기 전용 (read-only)**: 외부 시스템의 상태를 조회만 가능. write 는 orchestrator 측 정책으로 강제.

Agent 자율성 vs 안전성 사이의 균형이 핵심 질문이었다. v0.5.0 의 read-only MCP bundle 이 이미 default 였으나, 후속 릴리스에서 write 권한을 추가해야 하는지에 대한 명확한 정책 결정이 없었음.

## Decision

**모든 MCP 서버는 default read-only** 이다. write 작업은 orchestrator 측 정책으로 명시적으로 처리한다.

### 구체적 결정

1. **MCP 서버 6+1 종 default 가 read-only**:
   - `latest_backlog`, `check_doc_links`, `check_doc_metadata`, `suggest_impacted_docs`, `check_quickstart_stale_links`, `create_backlog_entry` (v0.5.0~)
   - `read_only_mcp_sdk` (v0.5.7 SDK candidate)
   - 모든 tool 의 descriptor 가 `readOnlyHint=true` (MCP 2025-06-18 spec) 또는 equivalent.

2. **`create_backlog_entry` 의 의도적 예외**:
   - v0.5.0 부터 read-only 우선 정책의 **유일한 의도적 write tool**.
   - "backlog entry draft" 만 생성. 실제 `ai-workflow/memory/backlog/` 에 write 하지 않음.
   - 사용자가 직접 검토 후 commit. orchestrator 가 자동 commit 안 함.
   - 정책: write 도구라기 보단 **draft 생성기**에 가까움. 운영 정책으로 명시.

3. **Transport 우선순위**:
   - default: `jsonrpc-bridge` (안정, draft fixture). 항상 사용 가능.
   - opt-in: `stdio-sdk` (공식 `mcp[cli]>=1.0`). 실험적, 알려진 connection-closed 회귀 있음.
   - 정식 default 전환 기준: `core/read_only_mcp_transport_promotion.md` 가 명시.

4. **Bootstrap 시 MCP 자동 emit**:
   - `python3 -m bootstrap_lib --enable-mcp` 가 하네스별 MCP config snippet emit (`.codex/mcp.toml`, `mcp.opencode.json`, `.gemini/mcp.json`, `.antigravity/mcp.json`, `.MiniMax/mcp.json`).
   - emit 시 tool descriptor 의 `transport_ready=false` 면 manual review only (자동 적용 안 함).

## Consequences

### Positive

- **에이전트 자율성 ↔ 안전성 균형**: read-only 는 정보를 제공하지만 변형을 일으키지 않음. Mavis 측 orchestrator 가 변형 결정을 명시적으로 내림.
- **위험 표면 축소**: MCP 서버가 read-only 면, sub-agent 가 손상된 MCP 응답을 보내도 사용자 데이터에 직접 영향 X.
- **취소 가능성**: write 가 명시적 orchestrator 정책 → 사용자/operator 가 쉽게 audit / undo 가능.
- **승격 경로 명확**: read-only 가 default 라 stdio-sdk 의 known connection-closed 회귀가 전체 시스템에 영향 X. opt-in 으로 격리.

### Negative / Trade-offs

- **자유도 낮음**: 일부 use case (e.g. autonomous task scheduling) 는 read-only 부족. 완화: orchestrator 측 write 정책으로 동일 효과 달성 가능.
- **`create_backlog_entry` 의 예외가 정책 복잡도**: 단일 write tool 이 있어 ADR 본문이 모순처럼 보일 수 있음. 완화: "draft 생성기" 로 위치 재명시. 실제 write 는 사용자.
- **stdio-sdk 회귀가 opt-in 만**: 회귀 발견 시 stdio-sdk 가 promotion 기준을 통과하지 못해 default 가 안 됨. v0.6+ 후속 작업으로 default 전환 가능.

### 후속 결정의 인용

- **v0.5.7**: `read_only_mcp_sdk` 가 정식 SDK 호환 candidate 로 추가. connection-closed 회귀가 fix 되면 default 전환 가능 (`core/read_only_mcp_transport_promotion.md` 참조).
- **v0.5.8**: bootstrap 시 MCP config 자동 emit + read_only tool descriptor 자동 생성.
- **v0.5.10**: `transport_ready=false` 시 manual review only 정책. 자동 적용 금지.

## References

- `workflow-source/mcp_servers/` — 6+1 read-only MCP 서버
- `workflow_kit/server/read_only_registry.py` — read-only tool registry
- `workflow_kit/server/read_only_entrypoint.py` — entrypoint
- `workflow_kit/server/read_only_jsonrpc.py` — JSON-RPC draft bridge
- `workflow_kit/server/read_only_mcp_sdk.py` — 공식 MCP SDK candidate
- `workflow-source/core/read_only_mcp_transport_promotion.md` — transport 승격 기준
- `workflow-source/tests/check_read_only_*.py` — 6 종의 read-only 회귀 test
