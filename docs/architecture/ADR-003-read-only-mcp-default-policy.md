# ADR-003: Read-only MCP 우선 정책

- 문서 목적: standard_ai_workflow 의 MCP 서버가 read-only 우선 정책을 채택한 rationale 와 운영 impact 를 정식 기록.
- 범위: MCP bundle 13 종 도구의 read-only 정책, write-capable 도구 2종의 명시 선언, transport 우선순위, bootstrap 시 MCP 자동 emit, create_backlog_entry 의 draft-only 예외.
- 대상 독자: maintainer, Mavis/Mavis consumer, MCP 통합자.
- 상태: Accepted (v0.5.7, **v1.1.7 개정** — 도구 13종 현실 반영 + write 도구 hint 정정)
- 최종 수정일: 2026-09-01
- 관련 문서: [`../README.md`](./README.md), [`./ADR-001-source-state-knowledge-3-layer-separation.md`](./ADR-001-source-state-knowledge-3-layer-separation.md), [`./ADR-002-pydantic-v2-contract-v1-external-spec.md`](./ADR-002-pydantic-v2-contract-v1-external-spec.md), [`../../workflow-source/core/read_only_mcp_transport_promotion.md`](../../workflow-source/core/read_only_mcp_transport_promotion.md)

- **Status**: Accepted (v0.5.7 초판은 6+1 도구 기준; **v1.1.7 현재 bundle 은 13 도구**, jsonrpc-bridge / stdio-sdk 양 transport)
- **Date**: 2026-05-03 (v0.5.0 read-only MCP initial), updated 2026-05-15 (v0.5.7 read-only SDK candidate), 2026-06-01 (v0.5.7 stable), **2026-08-12 (v1.1.7 — TASK-2026-08-11-main-024: 13 도구 현실 반영, `readOnlyHint` 허위 정정)**
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

1. **bundle 의 default 는 read-only** (v1.1.7 현재 13 도구):
   - read-only 11: `latest_backlog`, `check_doc_links`, `check_doc_metadata`, `suggest_impacted_docs`, `check_quickstart_stale_links`, `create_backlog_entry`, `create_environment_record_stub`, `create_session_handoff_draft`, `summarize_git_history`, `assess_milestone_progress`, `smart_context_reader`
   - **write-capable 2 (v1.1.7 명시 선언)**: `apply_robust_patch` (대상 파일을 실제로 write, dry-run 입력 없음), `rotate_workflow_logs` (handoff 를 rewrite)
   - descriptor 의 `readOnlyHint` (MCP 2025-06-18 spec) 는 registry 의 `read_only` 선언에서 나온다. **v0.5.7~v1.1.6 은 전 도구에 true 를 하드코딩해 write 도구 2종까지 read-only 로 광고했다** — 하네스가 이 hint 로 auto-approve 할 수 있는 허위 주석이었고, 검사(`check_read_only_mcp_server`)조차 그 허위를 강제했다. v1.1.7 부터 write 도구는 `readOnlyHint=false` 이고, 검사가 registry 선언 ↔ `WRITE_CAPABLE_TOOL_NAMES` 사실 목록 ↔ descriptor 삼자 일치를 강제한다.
   - 서버 이름 `workflow_read_only_bundle` 은 유지한다 (config 호환) — "read-only **우선** bundle" 로 읽는다. write 도구 추가는 이 ADR 의 사실 목록 갱신을 요구한다.

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
   - `python3 -m workflow_kit.bootstrap_lib --enable-mcp` 가 하네스별 MCP config snippet emit (`.codex/mcp.toml`, `mcp.opencode.json`, `.gemini/mcp.json`, `.antigravity/mcp.json`, `.MiniMax/mcp.json`).
   - emit 시 tool descriptor 의 `transport_ready=false` 면 manual review only (자동 적용 안 함).
   - **2026-08-05 supersede**: `transport_ready` 는 능력·단계·정책 셋을 한 boolean 에 섞고 있어 판정이 불가능했다. 같은 정책이 이제 `apply_mode`(`active_ok` / `manual_review_only`)로 표현되고 승격 기준은 `core/read_only_mcp_transport_promotion.md` §6.1 이 실행 가능한 검사로 고정한다.

### Bundle 분리 (v1.1.8, TASK-2026-08-12-main-003)

"read_only" 라는 이름의 bundle 안에 write 도구 2종이 사는 긴장 (v1.1.7 개정에서
후속 후보로 남긴 것) 의 근본 정리. 서버가 **bundle 선택자**를 갖는다:

| bundle | 서버 이름 | 도구 | 용도 |
|---|---|---|---|
| `read-only` | `workflow_read_only_bundle` | 11 | 하네스 자동 노출용 — 이름이 정직하다 |
| `write` | `workflow_write_bundle` | 2 (`apply_robust_patch`, `rotate_workflow_logs`) | **명시 opt-in**, manual review 대상 |
| `all` | `workflow_read_only_bundle` | 13 | 구 표면 — v1.2.0 부터 명시 opt-in (서빙 시 notice) |

- jsonrpc bridge `--bundle` 플래그. bundle 밖 도구 호출은 tools/call 에서 거부.
- bootstrap 이 emit 하는 config: 기존 alias 는 `--bundle read-only` 로 좁혀지고,
  claude-code (`.mcp.json`) 와 MiniMax 는 `standardAiWorkflowWrite` entry 를 함께
  emit (MiniMax 는 `apply_mode: manual_review_only`). mavis 글로벌 merge 는
  read-only 만 자동 등록 — write 는 사용자가 손수 추가.
- `stdio-sdk` candidate 는 1st cycle 에서 bundle 미지원 (all 서빙) — 승격 기준과
  함께 후속.
- **deprecation 계획**: 1st cycle (v1.1.8) 기본 `all` + stderr 경고 → 2nd cycle
  기본 `read-only`. — ✅ **완결 (v1.2.0, TASK-2026-08-13-main-005)**: CLI
  `--bundle` 미지정 기본값이 `read-only` 가 됐다. `all` 은 명시 opt-in 으로
  계속 동작한다 (deprecation 경고 대신 구성 안내 notice). bootstrap 이 emit
  하는 config 는 v1.1.8 부터 이미 전부 명시 `--bundle` 이라 영향이 없다.
- 검사: `check_read_only_mcp_server` 가 read-only ∪ write == all + 교집합 0 +
  read-only 서버의 write 도구 호출 거부를 강제. `check_mcp_tool_descriptors`
  case 7 은 예시 config 의 tools 배열을 entry 의 bundle 기준으로 대조.

### MCP 표면과 `wk` CLI 표면의 관계 (v1.1.7 명시)

MCP bundle (`READ_ONLY_TOOL_SPECS`, 13 도구) 과 `wk` CLI (`COMMANDS`/`TOOL_MODULES`,
70+ 명령) 는 **의도적으로 별개의 표면**이다:

- `wk` 는 **소비자의 전체 창구**다 — 정본 §11 의 메모리 갱신 경로를 포함해 kit 의
  모든 운영 기능을 노출한다.
- MCP bundle 은 **하네스에 자동 노출해도 안전한 조회·초안 중심의 선별 부분집합**이다
  (read-only default + 명시 선언된 write 2종). `wk` 전체를 MCP 로 노출하는 것은
  이 ADR 의 read-only 우선 결정에 어긋난다.
- 두 레지스트리는 이름이 같은 기능을 공유 구현(`workflow_kit/common/*`)으로 부르되,
  표면 등재는 각자 결정한다. session-start / backlog-update / doc-sync / refresh-state
  는 **CLI 전용**이다 — 메모리 문서를 쓰는 경로라 MCP 자동 노출 대상이 아니다.
- 목록이 겹치는 지점의 파생물(설정 예시의 `tools` 배열 등)은 registry 에서
  파생하고 검사로 대조한다 (`check_mcp_tool_descriptors` case 7).

## Consequences

### Positive

- **에이전트 자율성 ↔ 안전성 균형**: read-only 는 정보를 제공하지만 변형을 일으키지 않음. Mavis 측 orchestrator 가 변형 결정을 명시적으로 내림.
- **위험 표면 축소**: MCP 서버가 read-only 면, sub-agent 가 손상된 MCP 응답을 보내도 사용자 데이터에 직접 영향 X.
- **취소 가능성**: write 가 명시적 orchestrator 정책 → 사용자/operator 가 쉽게 audit / undo 가능.
- **승격 경로 명확**: read-only 가 default 라 stdio-sdk 의 known connection-closed 회귀가 전체 시스템에 영향 X. opt-in 으로 격리.

### Negative / Trade-offs

- **자유도 낮음**: 일부 use case (e.g. autonomous task scheduling) 는 read-only 부족. 완화: orchestrator 측 write 정책으로 동일 효과 달성 가능.
- **`create_backlog_entry` 의 예외가 정책 복잡도**: draft 생성기라 실제 write 없음 (위치 재명시). 실제 write 는 사용자.
- **write-capable 2종이 bundle 이름과 긴장**: `apply_robust_patch` / `rotate_workflow_logs` 는 이름이 "read_only" 인 bundle 안의 write 도구다. 완화: descriptor 가 `readOnlyHint=false` 로 정직하게 광고하고, 하네스 측 승인 정책이 hint 를 근거로 작동한다. 근본 정리는 bundle 분리(후속 후보).
- **stdio-sdk 회귀가 opt-in 만**: 회귀 발견 시 stdio-sdk 가 promotion 기준을 통과하지 못해 default 가 안 됨. v0.6+ 후속 작업으로 default 전환 가능.

### 후속 결정의 인용

- **v0.5.7**: `read_only_mcp_sdk` 가 정식 SDK 호환 candidate 로 추가. connection-closed 회귀가 fix 되면 default 전환 가능 (`core/read_only_mcp_transport_promotion.md` 참조).
- **v0.5.8**: bootstrap 시 MCP config 자동 emit + read_only tool descriptor 자동 생성.
- **v0.5.10**: `transport_ready=false` 시 manual review only 정책. 자동 적용 금지.

## References

- `workflow_kit/server/read_only_registry.py` `READ_ONLY_TOOL_SPECS` (13 도구) + `WRITE_CAPABLE_TOOL_NAMES`
- `workflow_kit/server/read_only_registry.py` — read-only tool registry
- `workflow_kit/server/read_only_entrypoint.py` — entrypoint
- `workflow_kit/server/read_only_jsonrpc.py` — JSON-RPC draft bridge
- `workflow_kit/server/read_only_mcp_sdk.py` — 공식 MCP SDK candidate
- `workflow-source/core/read_only_mcp_transport_promotion.md` — transport 승격 기준
- `workflow-source/tests/check_read_only_*.py` — read-only 회귀 test (readOnlyHint ↔ registry ↔ 사실 목록 삼자 일치 포함)
