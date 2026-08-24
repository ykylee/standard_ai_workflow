# Read-Only MCP Transport Promotion Spec

- 문서 목적: read-only JSON-RPC draft bridge 를 정식 MCP SDK transport 로 승격할 때 유지할 계약과 바뀔 수 있는 envelope 를 분리한다.
- 범위: descriptor 단일 출처, JSON-RPC fixture 기준선, SDK 승격 시 유지/변경 필드, 검증 경로
- 대상 독자: MCP server 구현자, 하네스 적용 담당자, AI workflow 설계자
- 상태: draft
- 최종 수정일: 2026-08-24
- 관련 문서: `./prototype_promotion_scope.md`, `../mcp_servers/read_only_bundle.md`, `../schemas/README.md`, `../workflow_kit/README.md`

## 1. 목적

현재 read-only bundle 은 정식 MCP SDK server 가 아니라 아래 세 계층으로 나뉜 draft 상태다.

- registry: `workflow_kit/server/read_only_registry.py`
- direct-call entrypoint: `workflow_kit/server/read_only_entrypoint.py`
- JSON-RPC draft bridge: `workflow_kit/server/read_only_jsonrpc.py` (**stable default**, v0.5.7+)
- optional official SDK candidate: `workflow_kit/server/read_only_mcp_sdk.py` (**stable as of v0.11.25**, regression fixed)

> **Transport status (v0.11.25)**: `jsonrpc-bridge` is the stable default with `tools/list` / `tools/call` round-trip working. `stdio-sdk` is **officially stable as of v0.11.25** — mcp 1.27.0 `CallToolResult(_meta=..., structuredContent=...)` API validated. spec §6's 7 verification commands all PASS. Detail: [`./mcp_installation_by_harness.md`](./mcp_installation_by_harness.md) §7.2 (regression marked fixed)

이 문서는 정식 MCP SDK transport 를 붙일 때 draft bridge 전체를 그대로 “완성품”으로 오해하지 않도록, 유지해야 할 계약과 교체 가능한 envelope 를 분리한다.

## 1.3 세 축 (2026-08-05 정정)

`transport_ready` 는 **한 boolean 으로 서로 다른 질문 셋에 답하고 있었다.** 그래서
"무엇이 참이면 true 인가" 를 이 문서가 끝내 적지 못했고, 조건 없는 플래그는 영원히
false 였다.

| 자리 | 값 | 실제로 답하던 질문 |
| --- | --- | --- |
| `read_only_mcp_sdk.sdk_runtime_status()` | `sdk_available` (동적) | `mcp` 를 import 할 수 있나 — **런타임 능력** |
| `read_only_mcp_sdk` tool-call `_meta` | `False` (하드코딩) | — (같은 파일이 자기모순이었다) |
| `read_only_jsonrpc` `_meta` | `False` (하드코딩) | 나는 draft bridge 다 — **구현 단계** |
| `read_only_registry` ×4 | `False` (상수) | (registry 는 어느 transport 가 자기를 서빙할지 **모른다**) |
| 하네스 예시 / `scaffold_harness` | `false` | 활성 설정으로 붙이지 마라 — **정책** |

축을 셋으로 나눈다. 각 축은 **답할 자격이 있는 자리** 에서만 계산한다.

| 축 | 이름 | 누가 답하는가 | 어휘 |
| --- | --- | --- | --- |
| 런타임 능력 | `sdk_available` | `read_only_mcp_sdk` 가 자기 프로세스에서 | `true` / `false` |
| 구현 단계 | `transport_phase` | 각 transport 모듈이 자기 것을 선언 | `jsonrpc_draft` / `official_sdk` |
| 정책 | `apply_mode` | `bootstrap_lib.mcp.MCP_BRIDGE_APPLY_MODE` | `active_ok` / `manual_review_only` |

**registry 는 이 셋 중 어느 것도 선언하지 않는다.** registry 는 *도구* 를 기술하지
*transport* 를 모른다. `build_transport_tool_descriptors()` 의 `transport_ready` 는
**deprecated** 이며, 소비자는 읽지 말 것 — 제거 대상이다(§6.2).

## 2. 단일 출처

아래 값은 SDK transport 로 승격해도 registry 를 단일 출처로 유지한다.

- tool 이름
- tool 설명
- input schema
- output schema
- `annotations.readOnlyHint`
- `descriptor_target`

`transport_ready` 는 이 목록에서 **제외한다** (2026-08-05). registry 가 답할 수 없는
값을 registry 의 단일 출처로 두고 있었다 — 그것이 이 플래그가 상수로 굳은 원인이다.

현재 descriptor export 는 [../schemas/read_only_transport_descriptors.json](../schemas/read_only_transport_descriptors.json) 이고, 하네스 설정 검토용 draft 는 [../schemas/read_only_harness_mcp_examples.json](../schemas/read_only_harness_mcp_examples.json) 이다.

## 3. Fixture 기준선

SDK 승격 전 비교 기준선은 [../schemas/read_only_jsonrpc_fixtures.json](../schemas/read_only_jsonrpc_fixtures.json) 이다.

현재 fixture 는 아래 request/response 를 고정한다.

- `initialize`
- `initialize_with_supported_capabilities`
- `initialize_invalid_capabilities`
- `initialize_invalid_tools_list_changed`
- `initialize_invalid_roots_capability`
- `notification_initialized_no_response`
- `notification_unknown_no_response`
- `notification_with_id_invalid_request`
- `tools_list`
- `latest_backlog_call_success`
- `check_doc_metadata_call_schema_error`
- `unknown_method`
- `invalid_boolean_id`
- `malformed_json_parse_error`
- `non_object_invalid_request`

현재 fixture 는 아래 stdio session sequence 도 고정한다.

- `stdio_session_requires_initialize`
- `stdio_session_rejects_second_initialize`

이 fixture 는 실제 MCP client 호환성 보장이 아니라, draft bridge 의 envelope 변화가 의도된 것인지 확인하기 위한 diff 기준선이다.

## 4. 유지할 계약

SDK transport 로 승격할 때도 아래 계약은 유지해야 한다.

- `tools/list` 계열 응답은 registry descriptor 의 tool 목록과 같은 순서를 유지한다.
- tool descriptor 의 `inputSchema` 와 `outputSchema` 는 runtime contract 생성 결과를 사용한다.
- 읽기 전용 tool 은 `annotations.readOnlyHint: true` 를 유지한다.
- 성공한 tool call 은 원래 tool output payload 를 구조화 결과로 보존한다.
- 실패한 tool call 은 원래 entrypoint error payload 의 `error_code`, `warnings`, `source_context` 를 잃지 않는다.
- `initialize` 입력은 draft bridge 단계에서도 object `params` 와 object `capabilities` 경계를 유지한다.
- `initialize` 의 `capabilities.tools`, `capabilities.roots`, `capabilities.sampling`, `capabilities.elicitation`, `capabilities.experimental` 는 있으면 object 여야 한다.
- `capabilities.tools.listChanged`, `capabilities.roots.listChanged` 는 있으면 boolean 이어야 한다.
- `notifications/*` request 는 `id` 가 없을 때만 draft bridge 단계에서 응답 없이 무시한다.
- JSON-RPC `id` 는 있으면 string, number, null 중 하나여야 하고 boolean/object/array 는 허용하지 않는다.
- `--stdio-lines` session 에서는 `initialize` 성공 전 `tools/list`, `tools/call` 을 허용하지 않는다.
- `--stdio-lines` session 에서는 `initialize` 를 한 번만 허용한다.
- 하네스 예시의 `apply_mode` 는 §6 의 승격 기준을 통과한 bridge 에만 `active_ok` 다.
  (이전 문구: "`transport_ready=false` 인 동안 `manual_review_only` 를 유지한다" —
  그 조건은 §1.3 대로 판정 불가였다.)

## 5. 바뀔 수 있는 envelope

정식 MCP SDK transport 로 바뀌면 아래 envelope 는 달라질 수 있다.

- JSON-RPC top-level `id` 처리
- parse error 와 invalid request 의 세부 `data` 필드
- SDK 초기화 응답의 capability 상세 필드
- initialize 입력에서 capability 내부 세부 필드 중 draft bridge 가 아직 검증하지 않는 나머지 필드
- tool call result 의 `content` wrapper 형식
- tool call error 의 JSON-RPC error code 와 message
- notification 처리 방식
- JSON-RPC request/notification lifecycle 세부 처리
- stdio session 상태 저장 방식과 handshake 세부 순서
- stdio framing 방식

이 항목이 바뀌더라도 4장의 유지 계약이 깨지지 않으면 정상적인 승격 변경으로 볼 수 있다.

## 6. 승격 전 검증

SDK transport 를 붙이기 전에는 아래 검증을 먼저 통과해야 한다.

```bash
python3 tests/check_read_only_mcp_server.py
python3 tests/check_read_only_jsonrpc_bridge.py
python3 tests/check_read_only_jsonrpc_fixtures.py
python3 tests/check_read_only_mcp_sdk_candidate.py
python3 tests/check_read_only_mcp_sdk_stdio.py
python3 tests/check_read_only_transport_descriptors.py
python3 tests/check_read_only_harness_mcp_examples.py
```

승격 구현 후에는 fixture diff 를 보고 envelope 변경이 5장의 허용 범위인지 확인한다.

### 6.1 `apply_mode = active_ok` 승격 기준 (2026-08-05 신설)

정책 축의 승격 조건이다. **선언만으로는 승격되지 않는다** —
[`../tests/check_mcp_apply_mode_criterion.py`](../tests/check_mcp_apply_mode_criterion.py)
가 아래를 실제로 실행해 증명을 요구하고, 미달이면 red 다.

1. **공식 MCP 클라이언트 왕복.** `mcp` SDK 의 `ClientSession` 으로 `initialize` →
   `tools/list` → `tools/call` 이 성공한다. 손수 만든 JSON-RPC 로는 안 된다 —
   `check_bootstrap_mcp_roundtrip.py` 는 stdin/stdout 에 JSON 을 직접 쓰므로 *우리
   구현끼리의 대화* 이고, 하네스 호환성을 증명하지 못한다.
2. **emit 되는 command 로 뜬다.** bootstrap 이 실제로 내보내는 `command`/`args`/`env`
   그대로, 그리고 **`mcp` extra 가 없는 인터프리터** 에서 뜬다. 하네스가 spawn 하는
   것은 `python3` 이고 거기에 SDK 가 있다는 보장이 없다.

측정 방식과 한계는 검사 파일의 docstring 이 정본이다(요약: `import mcp` 가 실패하는
shim 을 `PYTHONPATH` 앞에 붙여 extra 없는 환경을 재현한다. `mcp` 하나만 가리므로 다른
optional dep 의존은 못 잡는다). `mcp` SDK 가 없으면 이 검사는 **skip 이 아니라 fail**
이다 — 안 잰 것은 통과가 아니다.

**현재 판정 (2026-08-05 실측)**

| bridge | `transport_phase` | 기준 1·2 | `apply_mode` |
| --- | --- | --- | --- |
| `jsonrpc-bridge` | `jsonrpc_draft` | ✅ `tools/list` 13종 + `tools/call` 성공 | **`active_ok`** |
| `stdio-sdk` | `official_sdk` | ❌ `McpError: Connection closed` (SDK 부재) | `manual_review_only` |

`stdio-sdk` 가 `manual_review_only` 인 것은 **성숙도가 아니라 의존성** 때문이다.
`mcp` extra 가 보장된 환경에서는 `--mcp-bridge stdio-sdk` 로 쓸 수 있다.

이름이 오해를 부른다는 점을 다시 적어 둔다: **두 transport 모두 공식 MCP 프로토콜을
말한다.** `jsonrpc-bridge` 라는 이름과 `transport_ready: false` 라는 옛 자기 선언이
"MCP 가 아니다" 로 읽혔을 뿐이다.

### 6.2 `transport_ready` 제거 (2026-08-05 완료)

`transport_ready` 는 §1.3 대로 능력·단계·정책 셋을 한 boolean 에 섞고 있었다.
**제거를 마쳤고**, 각 축은 답할 자격이 있는 자리에서만 나온다.

| 자리 | 이전 | 현재 |
| --- | --- | --- |
| `read_only_registry` (×4) | `transport_ready: false` 상수 | **없음** — registry 는 transport 를 모른다 |
| `read_only_jsonrpc` `_meta` | `transport_ready: false` + `bridge_phase` | `transport_phase: "jsonrpc_draft"` (둘을 하나로) |
| `read_only_mcp_sdk` status | `transport_ready: sdk_available` | `sdk_available` + `transport_phase: "official_sdk"` |
| `read_only_mcp_sdk` tool-call `_meta` | `transport_ready: false` (자기모순) | `transport_phase: "official_sdk"` |
| 하네스 예시 / bootstrap 산출물 | `transport_ready=false` | `transport_phase` + `apply_mode` |

재생성한 커밋 산출물: `read_only_transport_descriptors.json`(14곳),
`read_only_jsonrpc_fixtures.json`(34곳), `read_only_harness_mcp_examples.json`(3곳).

**소비자 영향**: `_meta.transport_ready` 를 읽던 코드는 §1.3 의 세 축 중 무엇을
원했는지에 따라 `transport_phase`(단계) 또는 `apply_mode`(정책)로 옮긴다.
런타임에 SDK 가 있는지 알고 싶었다면 `sdk_runtime_status()["sdk_available"]` 이다.

`docs/architecture/ADR-003` 의 "`transport_ready=false` 면 manual review only" 정책은
같은 뜻의 `apply_mode` 로 승계됐다 (그 ADR 에 supersede 를 표시해 뒀다).

## 7. 다음에 읽을 문서

- 승격 범위 문서: [./prototype_promotion_scope.md](./prototype_promotion_scope.md)
- read-only MCP bundle: [../mcp_servers/read_only_bundle.md](../mcp_servers/read_only_bundle.md)
- schema 허브: [../schemas/README.md](../schemas/README.md)
- package 루트: [../workflow_kit/README.md](../workflow_kit/README.md)
