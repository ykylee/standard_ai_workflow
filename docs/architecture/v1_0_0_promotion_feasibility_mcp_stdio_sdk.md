# MCP stdio-sdk Promotion Feasibility Report (v0.11.24 review)

- 문서 목적: `workflow_kit.server.read_only_mcp_sdk` 의 정식 승격 feasibility 평가. 승격 시 blocker / 권고 작업 / 우선순위.
- 범위: stdio-sdk 의 `Connection closed` 회귀 원인 추적 + fix scope + promotion readiness 검증 + 의존성.
- 대상 독자: MCP server maintainer, v1.0.0 milestone reviewer, release manager.
- 상태: **review (2026-07-03)**
- 최종 수정일: 2026-07-09
- 관련 문서: [`./read_only_mcp_transport_promotion.md`](./read_only_mcp_transport_promotion.md), [`./mcp_installation_by_harness.md`](./mcp_installation_by_harness.md), [`../tests/check_mcp_stdio_sdk_promotion_readiness_v0_11_24.py`](../tests/check_mcp_stdio_sdk_promotion_readiness_v0_11_24.py), [`../ADR-007-deprecation-3rd-cycle-candidates.md`](../ADR-007-deprecation-3rd-cycle-candidates.md)

## 1. 결론 (TL;DR)

**stdio-sdk 정식 승격은 *본 시점* (v0.11.24) 권고하지 않음.** 주 사유:
1. **`Connection closed` 회귀 fix 가 미완** — known regression 으로 carry-forward, 4 cycle (v0.5.10 ~ v0.11.24) 동안 미해결.
2. **`CallToolResult` API mismatch 가능성** — `structuredContent` / `_meta` kwarg 가 `mcp 1.27.0` 의 `CallToolResult` signature 와 정합되지 않을 수 있음 (이 가설 1차 검증).
3. **mcp SDK env 의존성** — v0.11.24 시점 환경에서 PEP 668 로 `pip install mcp` 불가. CI 시 `apt install` 또는 venv 우회 필요.
4. **`validate_input=False` workaround** — SDK decorator 의 Pydantic 자동 schema validation bypass. fix 후 `validate_input=True` 로 정합 가능 여부 확인 필요.

**권고**: v0.11.25+ 의 별도 release cycle 에서 stdio-sdk *fix 1차 시도* — v1.0.0 milestone 진입 평가 (ADR-007) 와 *별도* 트랙. 본 release 에서 정식 승격 *불가* 로 마크.

## 2. 회귀 패턴 분석 (Connection closed)

### 2.1 회귀의 표면 증상

- `mcp_installation_by_harness.md` §7.2 명시: "현재 `check_read_only_mcp_sdk_stdio.py` 가 `Connection closed` 로 fail".
- smoke test 가 *skip* (env 에 mcp SDK 미설치로 실제 검증 불가).
- `tools/list` 가 비어 있음 — §7.3 별도 패턴.

### 2.2 회귀의 가설 root cause

`workflow_kit/server/read_only_mcp_sdk.py` 의 `_call_tool_result_for_payload` (line 88-98):

```python
def _call_tool_result_for_payload(sdk_types: Any, name: str, payload: dict[str, Any]) -> Any:
    return sdk_types.CallToolResult(
        content=[_text_content_from_payload(sdk_types, name, payload)],
        structuredContent=payload,
        isError=payload.get("status") == "error",
        _meta={
            "transport_ready": False,
            "sdk_candidate_phase": "official_sdk_optional_candidate",
            "tool": name,
        },
    )
```

**가설 A (1순위)**: `mcp 1.27.0` 의 `CallToolResult` constructor 가 `structuredContent` / `_meta` kwarg 를 *accept 하지 않음*.
- MCP 2025-06-18 spec 에서 `structuredContent` 와 `_meta` 가 신규 도입됐지만, `mcp 1.27.0` (2025-04 시점 추정) 의 SDK 는 본 kwarg 가 없을 가능성.
- 결과: `TypeError: unexpected keyword argument 'structuredContent'` → unhandled exception → `stdio_server` async context 가 close → client 측 "Connection closed".

**가설 B (2순위)**: `validate_input=False` 가 *본인 schema 와 SDK decorator 의 input validation* 미스매치 때문에 강제된 것. SDK 가 자동 생성한 JSON Schema 가 우리 Pydantic 의 `model_json_schema()` 와 *다른 dialect* (예: `anyOf` vs `oneOf`, `additionalProperties` 누락). 결과: SDK 가 첫 tool call 시 schema 불일치로 reject → "Connection closed".

**가설 C (3순위)**: `run_stdio_server` (line 132-147) 의 `server.run()` await 가 asyncio cancellation 을 미처리. client disconnect 시 `BrokenPipeError` / `ConnectionResetError` 가 propagate → "Connection closed".

**1차 fix 후속**: 본 cycle (v0.11.25+) 에서 가설 A 부터 검증 — `mcp 1.27.0` 의 `CallToolResult.__init__` signature 직접 inspect (CI 의 별도 python invocation). fix:

```python
# 가능 fix 1: structuredContent / _meta 미지원 시 fallback
if hasattr(sdk_types.CallToolResult, "__dataclass_fields__") and "structuredContent" in sdk_types.CallToolResult.__dataclass_fields__:
    return sdk_types.CallToolResult(content=..., structuredContent=payload, isError=..., _meta={...})
else:
    # older SDK: content 안에 structured data embed
    text_with_struct = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return sdk_types.CallToolResult(content=[sdk_types.TextContent(type="text", text=text_with_struct)], isError=...)
```

## 3. 코드 audit (2026-07-03 시점)

### 3.1 후보 코드 본문 (206 line)

| 라인 | 항목 | 비고 |
|---|---|---|
| 25-30 | `SDK_IMPORT_TARGETS` tuple | `mcp.types`, `mcp.server.stdio`, `mcp.server.lowlevel`, `mcp.server.models` |
| 50-76 | `sdk_runtime_status()` | descriptor 정합 검증, `sdk_available`, `transport_ready=False` advertise |
| 79-85 | `_text_content_from_payload()` | `smart_context_reader` 분기 (text serialization) |
| 88-98 | `_call_tool_result_for_payload()` | **가설 A — `structuredContent` / `_meta` kwarg** |
| 101-129 | `build_lowlevel_server()` | `validate_input=False` (가설 B) |
| 132-147 | `run_stdio_server()` | `server.run(...)` await, asyncio 미처리 (가설 C) |
| 150-162 | `parse_args()` | `--print-sdk-runtime` / `--stdio-sdk` |
| 165-202 | `main()` | sdk_available 체크, asyncio.run() |

### 3.2 SDK version 정합

- pyproject.toml: `mcp-sdk = ["mcp[cli]>=1.0", ...]`
- requirements-dev.txt: `mcp[cli]==1.27.0` (pin)
- candidate code: `structuredContent` / `_meta` 사용 — **MCP 2025-06-18 spec 이후의 feature**.

**불일치 가능성**:
- mcp 1.27.0 의 release date 가 2025-04 추정 (search-by-version) — MCP 2025-03-26 spec 시점.
- `structuredContent` 는 MCP 2025-06-18 spec 신규. 1.27.0 에 포함 여부 *불확실*.
- `_meta` 도 MCP 2025-06-18 spec 신규. 마찬가지.

→ **1차 fix 후속**: mcp SDK 의 CHANGELOG / source inspect 로 `CallToolResult` 의 실제 field 검증. 가능 시 mcp SDK version *upgrade* 또는 kwarg *drop*.

### 3.3 비교 — JSON-RPC bridge (stable, draft)

| 항목 | stdio-sdk (experimental) | jsonrpc-bridge (stable) |
|---|---|---|
| Layer | official SDK lowlevel | hand-written draft fixture |
| `validate_input` | disabled (workaround) | N/A — direct JSON-RPC |
| `structuredContent` | attempted (가설 A 원인) | N/A — JSON envelope 안에서 직접 보존 |
| error envelope | `isError=True` + `error_code` in structuredContent | JSON-RPC `error.code` / `error.message` / `error.data` |
| `Connection closed` | **현재 fail** (가설 A/B/C) | never observed (smoke 6/6 PASS) |
| 1차 도입 (release note) | v0.8.10~v0.8.11 (experimental 박힘) | v0.5.7+ (stable default) |

JSON-RPC bridge 가 stable 한 이유는 **spec §4 의 12 계약**을 hand-written 으로 직접 충족했기 때문. stdio-sdk 는 *SDK surface* 가 spec §4 와 1:1 mapping 되지 않아 회귀 발생.

## 4. Promotion blockers (우선순위)

| # | Blocker | 우선순위 | Effort (추정) |
|---|---|---|---|
| 1 | **mcp SDK env 설치** (PEP 668 — venv 또는 pip --break-system-packages) | **P0** | small (env config) |
| 2 | **`Connection closed` 원인 fix** (가설 A 부터 검증 + fix) | **P0** | medium (1-2 release cycle) |
| 3 | **`validate_input=True` 복귀** (Pydantic schema 와 SDK 자동 schema 정합 검증) | P1 | small |
| 4 | **stdio_sdk smoke test 가 env 에서 PASS** (CI 환경 정합) | P0 | small (smoke 자체는 이미 존재) |
| 5 | **read-only input schema Pydantic v2 전면 적용** (현재 `inputSchema` 가 SDK 자동 생성) | P1 | medium |
| 6 | **descriptor `_meta` 의 `transport_ready` flip** (spec §5 의 `transport_ready` 가 promotion 시 `true` 로) | P0 | trivial |
| 7 | **5개 하네스별 실제 smoke** (TASK-V051-005) | P2 | medium |
| 8 | **pip install 한 줄 임포트 검증** (TASK-V051-006) | P3 | small |
| 9 | **CHANGELOG entry (auto-gen 으로 충분)** | trivial | trivial |
| 10 | **Release note (`releases/Beta-v0.X.Y.md`)** + **drift-prevention sync-maturity-matrix 적용** | trivial | trivial |

## 5. Promotion roadmap (v0.11.25 ~ v0.11.X)

### Phase A: 환경 정합 + 회귀 fix (v0.11.25, 1 cycle)

1. CI 의 `mcp-sdk` extra 설치 보장 (가상 환경 또는 apt fallback).
2. `mcp 1.27.0` 의 `CallToolResult.__init__` signature inspect (가설 A 검증).
3. 가설 A confirmed → `_call_tool_result_for_payload()` 에 version-adaptive fallback 추가.
4. `check_read_only_mcp_sdk_stdio.py` 가 CI 에서 PASS.
5. spec §1 의 "Connection closed" marker → "fixed (v0.X.Y)" 또는 status 갱신.

### Phase B: 안정화 + 정합 audit (v0.11.X, 1 cycle)

1. `validate_input=True` 복귀 시도 + Pydantic schema 와 SDK schema 의 mismatch 검증.
2. `read_only_input_schema` Pydantic v2 전면 적용 — 모든 tool 의 input 이 `BaseModel` 정합.
3. 5개 하네스별 (Codex / OpenCode / Claude / MiniMax / Antigravity 등) 실제 MCP config + stdio-sdk 연결 검증.
4. consumer 1+ month 운영 데이터 누적.

### Phase C: 정식 승격 (v1.0.0 milestone 진입 평가 시점)

1. `promotion_readiness` smoke 5 case 모두 PASS.
2. spec §6 의 verification command 7종 모두 PASS.
3. `transport_ready: true` advertise (descriptor).
4. `maturity_matrix.json` 의 MCP servers 항목 갱신 (8 stable + 4 beta → 8 stable + 4 stable 또는 12 stable).
5. **본 release 의 release note (`Beta-v0.X.Y.md`)** 에 stdio-sdk stable 승격 정식 기록 + ADR 후속 (또는 ADR-008 placeholder).

### Phase D: ADR 후속

- ADR-008 (또는 ADR-007 의 후속) 으로 stdio-sdk 정식 승격 의 retrospective 작성 — fix 의 root cause / fix 의 scope / consumer 영향.
- 본 feasibility report 가 ADR 의 *Context* 섹션 anchor.

## 6. Effort / Risk 평가

### 6.1 Effort

| 항목 | LoC | Risk |
|---|---|---|
| Phase A | ~100-200 LOC (fix + fallback + smoke 환경 보강) | **medium** — 가설 A 가 wrong 일 경우 추가 investigation |
| Phase B | ~200-500 LOC (schema 정합 + harness smoke + Pydantic v2 input) | medium-high |
| Phase C | ~50 LOC (descriptor 갱신 + release note) | low |
| Phase D | ~100-200 LOC (ADR) | low |

**총 estimated effort**: ~500-1000 LOC, 2-3 release cycle.

### 6.2 Risk

- **mcp SDK 의 *breaking change* 가능성** — MCP 2025-06-18 spec 도입 이후 SDK 가 *major version* 으로 변경 가능. 본 작업의 fix 가 다음 major 에서 재작업 필요 가능.
- **consumer 영향의 *불확실성*** — stdio-sdk 가 stable 로 전환되면 consumer 가 jsonrpc-bridge 에서 *마이그레이션* 필요. consumer metrics 로 사전 경고 가능 (consumer feedback channel 운영).
- **harness-specific SDK 차이** — Codex / OpenCode / Claude 등 *각 harness* 의 MCP client 가 *다른* MCP spec 준수 수준. SDK 호환이 harness 별로 *break* 가능.

### 6.3 대안 (skip stdio-sdk, jsonrpc-bridge 만 stable)

stdio-sdk 정식 승격을 *skip* 하고 v1.0.0 milestone 진입 가능:
- **장점**: jsonrpc-bridge 가 이미 stable. MCP spec *대부분* 충족 (12 계약). consumer 영향 ❌. v1.0.0 진입 평가 즉시 가능.
- **단점**: 정식 MCP SDK 호환 *부재* — 일부 harness (공식 mcp-cli 기반) 가 stdio-sdk 사용 시 *fallback* 또는 별도 wrapping 필요.
- **권고**: jsonrpc-bridge 만 stable 로 v1.0.0 진입 + stdio-sdk 는 *post-v1.0.0* 후속 작업 (별도 TASK-V051-004 후속).

## 7. 즉시 실행 가능 (P0, 30분 이내)

1. **CI env 정합**: `.github/workflows/mcp_sdk_smoke.yml` (신규) — `mcp[cli]==1.27.0` 설치 + `check_read_only_mcp_sdk_stdio.py` CI step.
2. **Connection closed 원인 *1차 검증*** — `python -c "import mcp.types; help(mcp.types.CallToolResult)"` 로 mcp 1.27.0 의 signature 확인.
3. **fix 시도 (가설 A)**: `_call_tool_result_for_payload()` 에 version-adaptive fallback 추가 + smoke test.
4. **descriptor `_meta.transport_ready` 의 promotion 후 값** — `transport_ready: True` (promoted) vs `False` (current).

## 8. 결론 (재확인)

**stdio-sdk 정식 승격은 v0.11.25+ 별도 release cycle 에서 점진적으로**. v1.0.0 milestone 진입 시 본 항목은 *optional* — jsonrpc-bridge 만 stable 로 v1.0.0 진입 가능. stdio-sdk 의 정식 승격은 *post-v1.0.0* 또는 별도 TASK-V051-004 후속.

## Reference

- spec: [`./read_only_mcp_transport_promotion.md`](./read_only_mcp_transport_promotion.md)
- harness 별 설치: [`./mcp_installation_by_harness.md`](./mcp_installation_by_harness.md) §7.2-§7.3
- promotion readiness smoke: [`../tests/check_mcp_stdio_sdk_promotion_readiness_v0_11_24.py`](../tests/check_mcp_stdio_sdk_promotion_readiness_v0_11_24.py)
- ADR-007 placeholder: [`../ADR-007-deprecation-3rd-cycle-candidates.md`](../ADR-007-deprecation-3rd-cycle-candidates.md)
- SDK candidate: [`../../workflow-source/workflow_kit/server/read_only_mcp_sdk.py`](../../workflow-source/workflow_kit/server/read_only_mcp_sdk.py)
- JSON-RPC bridge (stable): [`../../workflow-source/workflow_kit/server/read_only_jsonrpc.py`](../../workflow-source/workflow_kit/server/read_only_jsonrpc.py)
- MCP v1 server wrapper: [`../../workflow-source/workflow_kit/server/mcp_v1_server.py`](../../workflow-source/workflow_kit/server/mcp_v1_server.py)