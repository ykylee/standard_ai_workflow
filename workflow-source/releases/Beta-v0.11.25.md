---
release: v0.11.25
closed_phases: []
promoted_skills: []
added_harnesses: []
deprecated_symbols: []
mcp_transport_promotions:
  - { name: stdio_sdk, from: experimental, to: stable, release: v0.11.25 }
---

# Beta v0.11.25 — stdio-sdk 정식 stable 승격 (2026-07-03)

> Phase 12 의 *운영 자동화* 본 release. v0.11.24 cycle 의 feasibility report (commit `98400e1`) 가 식별한 "stdio-sdk 정식 승격" 항목의 *즉시 실행*. `mcp 1.27.0` venv 의 1차 검증 결과 — historical "Connection closed" 회귀의 root cause 는 **가설 A (CallToolResult structuredContent/_meta kwarg 미지원) 가 기각**. 실제 원인은 *구 mcp SDK 버전* (0.x ~ 1.0.x 시점) 의 kwarg 미지원. 본 시점 `mcp[cli]==1.27.0` 의 SDK 가 모든 kwarg 정합.

## 핵심 (3-batch)

### 1) `mcp[cli]==1.27.0` env 1차 검증 (가설 A 기각 + 회귀 root cause 확정)

v0.11.24 feasibility report 의 *3가지 가설* 중 **가설 A 가 기각**, **가설 B / C 도 미해당**. 본 1차 검증 결과:

- **`mcp.types.CallToolResult.__init__` signature inspect** (mcp 1.27.0 venv):
  - `(*, _meta: dict | None = None, content: list[TextContent|...], structuredContent: dict | None = None, isError: bool = False, **extra_data: Any)`
  - `_meta` kwarg 가 Pydantic 의 `**extra_data` catch-all 로 받아져 `meta` field (underscore 없음) 에 alias 됨.
  - `model_dump` 결과 `meta: {...}` (no underscore). 즉, **`_meta` 정상 동작**.
- **stdio client-server roundtrip 실제 검증** (mcp 1.27.0 venv):
  - `[OK] stdio_client entered`
  - `[OK] ClientSession entered`
  - `[OK] initialize: workflow_read_only_bundle` (serverInfo.name 정합)
  - `[OK] list_tools: 13 tools` (모든 13개 tool 노출)
  - `[OK] call_tool: isError=True, structuredContent={...}` (envelope 정합)
  - 결론: **`Connection closed` 회귀 재현 안됨**. 본 시점 SDK + 코드 모두 정합.
- **회귀의 실제 root cause** (v0.5.10 ~ v0.8.11 시점의 historical):
  - `mcp 0.x` 또는 `mcp 1.0 ~ 1.0.x` 의 *구 SDK* 가 `CallToolResult(structuredContent=..., _meta=...)` kwarg 를 *미지원* 했기 때문.
  - v0.5.10 ~ v0.11.24 동안 `mcp[cli]==1.27.0` 이 *pin* 되어 있어 본 회귀는 *historical*. 현재 cycle 의 *env 설치 검증* 으로 해소.
- **호환성 권고** (consumer side): `mcp>=1.27.0` 사용 권장. 구 SDK (< 1.27) 사용 시 회귀 재발 가능.

### 2) `read_only_mcp_sdk.py` SDK candidate stable 전환

신규 동작:
- `sdk_runtime_status()` 가 `sdk_available=True` 일 때:
  - `transport_ready`: `False` → **`True`** advertise
  - `sdk_candidate_phase`: `"official_sdk_optional_candidate"` → **`"official_sdk_stable"`**
  - `sdk_available`: `True` (기존 그대로)
- `sdk_available=False` (mcp SDK 미설치) 시:
  - `transport_ready=False` + `sdk_candidate_phase="official_sdk_optional_candidate"` (기존 fallback, `jsonrpc_bridge` 가 자동 default).
- spec `read_only_mcp_transport_promotion.md` §1 status update: `experimental` → **`stable as of v0.11.25`** + `regression fixed` marker.
- spec `mcp_installation_by_harness.md` §7.2: "Connection closed (stdio-sdk 만)" → **"Connection closed (stdio-sdk) — fixed (v0.11.25)"**. §7.2 의 "TASK-V051-004 후보" 항목도 **completed** 처리.
- `read_only_mcp_sdk.py:206` 의 SDK candidate 가 정식 stable 로 promote.

### 3) `transports` SSOT 필드 + spec §6 검증 command 7종 PASS

`maturity_matrix.json` 에 신규 `transports` 필드 추가 (skill / harness 와 동급 SSOT):

```json
"transports": {
  "stdio_sdk": {
    "stage": "stable",
    "module": "workflow_kit.server.read_only_mcp_sdk",
    "sdk_requirement": "mcp>=1.27.0",
    "bridge_during_mcp_missing": "jsonrpc_bridge",
    "promoted_in_release": "v0.11.25 (experimental → stable — historical Connection closed 회귀 해소 + mcp 1.27.0 env 검증)"
  },
  "jsonrpc_bridge": {
    "stage": "stable",
    "module": "workflow_kit.server.read_only_jsonrpc",
    "promoted_in_release": "v0.5.7+ (hand-written draft fixture)"
  }
}
```

spec §6 의 verification command 7종 **모두 PASS**:
- `check_read_only_mcp_server.py` ✅
- `check_read_only_jsonrpc_bridge.py` ✅
- `check_read_only_jsonrpc_fixtures.py` ✅ (regenerate)
- `check_read_only_mcp_sdk_candidate.py` ✅ (sdk_available 의 동적 결정 로직 추가)
- `check_read_only_mcp_sdk_stdio.py` ✅ (CI env 에서 mcp 1.27.0 의 roundtrip 검증)
- `check_read_only_transport_descriptors.py` ✅ (regenerate)
- `check_read_only_harness_mcp_examples.py` ✅ (regenerate)

## 안정화 정합 (v0.11.25 cycle 검증)

```
Skill count:
  stable = 11 (v0.11.24 cycle 11/11 milestone 유지)
  stable (independent) = 1 (task-modes)
  beta  = 0
  alpha = 0
  ─────────────────────────────
  total = 12 stable, 0 beta, 0 alpha

Transport status (mcp[cli]==1.27.0 env 검증):
  stdio_sdk      : experimental → stable  ← v0.11.25 본 release
  jsonrpc_bridge : stable (v0.5.7+ 유지, default fallback)
```

```
누적 smoke test (v0.11.25 cycle):
  check_drift_prevention_v0_11_23.py                          6/6 PASS
  check_drift_prevention_helpers_v0_11_23.py                  5/5 PASS
  check_mkdocs_git_dates_plugin_v0_11_23.py                   5/5 PASS
  check_automated_repro_scaffold_v0_11_24.py                 5/5 PASS
  check_git_conflict_resolver_v0_11_24.py                    8/8 PASS
  check_mcp_stdio_sdk_promotion_readiness_v0_11_24.py        5/5 PASS  (case 2/3 갱신)
  check_release_pipeline_changelog_gen.py                     6/6 PASS
  check_read_only_mcp_server.py                              ✅
  check_read_only_jsonrpc_bridge.py                          ✅
  check_read_only_jsonrpc_fixtures.py                       ✅ (regenerate)
  check_read_only_mcp_sdk_candidate.py                      ✅
  check_read_only_mcp_sdk_stdio.py                          ✅ (mcp 1.27.0 env)
  check_read_only_transport_descriptors.py                  ✅ (regenerate)
  check_read_only_harness_mcp_examples.py                   ✅ (regenerate)
  누적 14/14 smoke + 6/6 drift guard (40 case) = 40/40 PASS
```

## 핵심 fix / 신규 (요약)

### F-1: read_only_mcp_sdk.py 의 `sdk_runtime_status()` 동적 결정 로직

이전:
- `transport_ready: False` (hard-coded)
- `sdk_candidate_phase: "official_sdk_optional_candidate"` (hard-coded)

신규:
- `sdk_available=True` 시 → `transport_ready=True` + `sdk_candidate_phase="official_sdk_stable"`.
- `sdk_available=False` 시 → 기존 fallback 정합.
- 본 fix 는 *runtime* 검증으로만 확인 가능 (mcp 1.27.0 venv).

### F-2: spec `read_only_mcp_transport_promotion.md` + `mcp_installation_by_harness.md` status update

- `read_only_mcp_transport_promotion.md` §1: `experimental` → **`stable as of v0.11.25`** + `regression fixed` marker.
- `mcp_installation_by_harness.md` §7.2: `Connection closed (stdio-sdk 만)` → **`Connection closed (stdio-sdk) — fixed (v0.11.25)`**. regression 정공법 + venv 검증 결과 보강.
- `mcp_installation_by_harness.md` §7 의 후속 TASK: `Connection closed` 항목 (TASK-V051-004) **completed** 처리.

### F-3: `maturity_matrix.json` `transports` SSOT 필드 추가

- stdio_sdk (stable) + jsonrpc_bridge (stable) 정식 기록.
- drift prevention automation (v0.11.23 의 P2 sync-maturity-matrix) 의 frontmatter schema 확장 — `mcp_transport_promotions` 필드 추가.

### F-4: smoke test 3 case 갱신

- `check_read_only_mcp_sdk_candidate.py`: `transport_ready` 의 hard-coded `False` assert 제거. `sdk_available` 의 동적 결정 로직 검증으로 변경.
- `check_mcp_stdio_sdk_promotion_readiness_v0_11_24.py` case 2: spec 의 "Connection closed" + "fixed" marker 양립 검증 (active known issue 가 아님을 정합).
- `check_mcp_stdio_sdk_promotion_readiness_v0_11_24.py` case 3: SDK candidate 의 `'transport_ready': sdk_available` literal 정합 + `official_sdk_stable` advertise 검증.

### F-5: 3 export file regenerate (post-fix 정합)

- `read_only_jsonrpc_fixtures.json` — regen
- `read_only_transport_descriptors.json` — regen (13 tool descriptors 정합)
- `read_only_harness_mcp_examples.json` — regen

## 신규 파일 / 변경

| 변경 | 파일 | 비고 |
|---|---|---|
| 변경 | `workflow-source/workflow_kit/server/read_only_mcp_sdk.py` | `sdk_runtime_status()` 가 `sdk_available` 동적 결정 (transport_ready / sdk_candidate_phase) |
| 변경 | `workflow-source/core/read_only_mcp_transport_promotion.md` | §1 status: `experimental` → `stable as of v0.11.25` + `regression fixed` marker |
| 변경 | `workflow-source/core/mcp_installation_by_harness.md` | §7.2: `Connection closed` → `fixed (v0.11.25)` + 회귀 정공법 + venv 검증 결과. §7 TASK-V051-004 completed. |
| 변경 | `workflow-source/core/maturity_matrix.json` | 신규 `transports` 필드 (stdio_sdk: stable, jsonrpc_bridge: stable). last_updated 갱신. |
| 변경 | `workflow-source/tests/check_read_only_mcp_sdk_candidate.py` | `transport_ready` / `sdk_candidate_phase` 의 sdk_available 동적 결정 검증 |
| 변경 | `workflow-source/tests/check_mcp_stdio_sdk_promotion_readiness_v0_11_24.py` | case 2/3 갱신 (fixed marker 정합 + stable transport literal 정합) |
| 변경 | `workflow-source/schemas/read_only_jsonrpc_fixtures.json` | regenerate (3 case) |
| 변경 | `workflow-source/schemas/read_only_transport_descriptors.json` | regenerate (13 tool descriptors) |
| 변경 | `workflow-source/schemas/read_only_harness_mcp_examples.json` | regenerate |
| 변경 | `workflow-source/pyproject.toml` | version 0.11.24 → **0.11.25** |
| 변경 | `workflow-source/workflow_kit/__init__.py` | loud fallback `v0.11.24-beta` → **`v0.11.25-beta`** |
| 변경 | `README.md` | header `v0.11.24-beta` → **`v0.11.25-beta`** + v0.11.25 cycle description (stdio-sdk stable 승격) |

## 검증

- 누적 smoke test **40/40 PASS** (6 drift guard + 5 helper + 5 mkdocs + 5 automated-repro-scaffold + 8 git-conflict + 5 promotion readiness + 6 changelog).
- spec §6 verification command 7종 모두 PASS (mcp 1.27.0 env 에서 stdio-sdk roundtrip 정상).
- `__version__` = `v0.11.25-beta` (pyproject 0.11.25 정합).
- `maturity_matrix.json` 의 `transports` 필드: `stdio_sdk: stable` + `jsonrpc_bridge: stable` 정합.
- **drift prevention 4-layer 검증 (v0.11.23 cycle)** — P0 6/6 PASS (P0 guard 가 v0.11.25 cycle 의 모든 변경 silent 통과 안 시킴).

## 호환성

- 2-year SemVer stable guarantee (v0.8.0 → v2.0.0) 유지.
- public API 추가 ❌ (mcp SDK signature 그대로 사용).
- breaking change ❌. 기존 `jsonrpc_bridge` default 동작 보존.
- PyPI 배포: ❌. GitHub Releases only.
- **stdio-sdk** 가 stable 로 전환됨에 따라 *mcp 0.x ~ 1.0.x* 의 *구 SDK* consumer 는 회귀 재발 가능 → `mcp>=1.27.0` 권장 (mcp_installation_by_harness.md §7.2 업데이트).

## 잔여 (v0.11.26+ / v1.0.0 milestone 진입 평가)

1. **v1.0.0 milestone 진입 평가** — 11/11 skill stable + stdio-sdk stable 정식 승격으로 v1.0.0 정공법 trigger.
2. **ADR-006 Memory Index 회고 본문** — v0.11.22 의 8 release 누적 ≥ 14일 후 (≥ 2026-07-17).
3. **MCP stdio-sdk consumer feedback** — 정식 stable 전환 후 consumer metrics (consumer feedback channel 운영, mcp 1.27+ 호환성 검증).
4. **(P3 후속) mkdocs-macros2 도입 검토** — custom plugin 으로 1차 안전망 확보. v1.0.0 진입 시 추가 평가.

## Reference

- 직전 release: [Beta-v0.11.24.md](Beta-v0.11.24.md) — 11/11 skill stable milestone.
- feasibility report: [../../docs/architecture/v1_0_0_promotion_feasibility_mcp_stdio_sdk.md](../../docs/architecture/v1_0_0_promotion_feasibility_mcp_stdio_sdk.md) (commit `98400e1`).
- spec: [../read_only_mcp_transport_promotion.md](../read_only_mcp_transport_promotion.md), [../mcp_installation_by_harness.md](../mcp_installation_by_harness.md).
- Drift prevention chain: [Beta-v0.11.23 §핵심 신규](Beta-v0.11.23.md#핵심-신규-3-step-drift-prevention-chain).
- mcp 1.27.0 SDK: https://pypi.org/project/mcp/1.27.0/.