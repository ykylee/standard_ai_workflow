# Architecture Documentation

- 문서 목적: Standard AI Workflow의 시스템 구조와 핵심 설계 원칙을 영구 지식으로 정리한다.
- 범위: 시스템 구조, 컴포넌트 명세, 설계 결정 기록 (ADR)
- 대상 독자: 개발자, 설계자, 아키텍처 리뷰어
- 상태: stable (v0.11.22-beta 기준)
- 최종 수정일: 2026-07-03
- 관련 문서: [../PROJECT_PROFILE.md](../PROJECT_PROFILE.md), [../CODE_INDEX.md](../CODE_INDEX.md), [../INSTALLATION_AND_USAGE.md](../INSTALLATION_AND_USAGE.md), [../../workflow-source/core/workflow_agent_topology.md](../../workflow-source/core/workflow_agent_topology.md)

> v0.11.22-beta 기준. ADR 6종 (001~006) + Memora 평가 + 3-layer 컴포넌트 명세 + ADR 백로그 포함. Phase 12 in_progress 본문은 [`../../workflow-source/core/project_status_assessment.md`](../../workflow-source/core/project_status_assessment.md) 참조.

## 1. 시스템 구조 (현재 v0.11.22-beta 기준)

저장소는 **3-layer 분리** 구조를 따른다 (v0.5.2 commit `96431f1 refactor(workflow): separate source from runtime layer`):

1. **`workflow-source/`** — 원본 소스. 모든 편집의 source-of-truth.
   - `workflow_kit/` (Python 패키지), `bootstrap_lib/` (Python 패키지), `skills/`, `mcp_servers/`, `scripts/`, `tools/`, `tests/`, `core/`, `templates/`, `harnesses/`, `examples/`, `releases/`
2. **`ai-workflow/`** — runtime/state 레이어. `bootstrap --adoption-mode existing` 으로 생성. `.gitignore` 로 일부 제외 (워크플로우 state 는 자유롭게 갱신 가능).
3. **`docs/`** — 영구 지식 베이스. PR 리뷰 거쳐 `main` 머지.

상세 코드베이스 구조: [`../CODE_INDEX.md`](../CODE_INDEX.md). 디렉토리 단위 컴포넌트 설명: [`../../workflow-source/workflow_kit/README.md`](../../workflow-source/workflow_kit/README.md).

## 2. 핵심 설계 원칙

### 2.1. Source-of-Truth 분리
- **`workflow-source/`** = 원본. 모든 skill/MCP/template 의 SSOT. PR 리뷰 필요.
- **`ai-workflow/memory/`** = 워크플로우 state. 자유롭게 갱신 (handoff, backlog, state cache).
- **`docs/`** = 영구 지식. PR 리뷰 거쳐 main 머지.
- **상세**: [`../../workflow-source/core/workflow_state_vs_project_docs.md`](../../workflow-source/core/workflow_state_vs_project_docs.md)

### 2.2. Bootstrap-driven 도입
- 사용자는 `python3 -m bootstrap_lib --target-root <project>` 한 번으로 표준 워크플로우 패키지를 받는다.
- bootstrap 은 `--harness` 로 하네스 선택 (10종: `codex` / `opencode` / `gemini-cli` / `antigravity` / `minimax-code` / `claude-code` / `aider` / `goose` / `pi-dev` / `codewhale` v0.10.4 신규), `--enable-mcp` 로 MCP 심기, `--adoption-mode {new,existing}` 로 빈/기존 프로젝트 모드 분기.
- **상세**: [`../../workflow-source/core/workflow_harness_distribution.md`](../../workflow-source/core/workflow_harness_distribution.md)

### 2.3. Pydantic v2 기반 강타입 계약
- v0.5.4 부터 orchestrator ↔ sub-agent 통신은 `core/orchestrator_subagent_contract_v1.md` 외부 spec 강제.
- `workflow_kit/contract_v1/` 의 `output_validator` (sub-agent §5 출력 검증) + `delegator` (`choose_role` 단일 / `choose_roles` 배치 / `recommend_model_tier` 자동) 가 enforcement helper.
- v0.5.7 부터 multi-component fan-out/in 지원. cross-ref 갱신 / parent_delegation_id 발급은 §6.3 MUST-NOT-delegate 로 orchestrator 직접 처리.

### 2.4. Read-only MCP 우선
- 모든 MCP 서버는 default read-only. bootstrap 시 `--mcp-bridge jsonrpc-bridge` (안정) 또는 `--mcp-bridge stdio-sdk` (실험적) 선택.
- read-only transport 승격 기준: [`../../workflow-source/core/read_only_mcp_transport_promotion.md`](../../workflow-source/core/read_only_mcp_transport_promotion.md)

### 2.5. Self-dogfooding
- 이 저장소 자체가 워크플로우의 첫 번째 적용 사례. `ai-workflow/memory/` 가 self-host 한 state. 변경 시 `state.json` / `session_handoff.md` / `work_backlog.md` 가 함께 갱신.

## 3. 컴포넌트 명세 (현재 상태)

| 컴포넌트 | 위치 | 책임 | 비고 |
|---|---|---|---|
| Workflow Kit | `workflow_kit/` | 공통 헬퍼 + contract v1 + MCP server + release pipeline | Python 패키지, editable install, **FULL mypy strict 도달 (v0.11.18, 109 file clean)** |
| Bootstrap | `scripts/bootstrap_lib/` | 새/기존 프로젝트에 워크플로우 도입 | v0.5.2+ 6-module 리팩터 |
| Skills | `skills/` (12종: 9 stable + 2 beta + 1 alpha + task-modes stable) | 워크플로우 단계 자동화 | `tool_version` + `status` envelope. v0.11.19~v0.11.21 3 batch stable 승격 |
| MCP Servers | `mcp_servers/` (12종: 8 stable + 4 beta) | 에이전트 도구 (read-only) | jsonrpc-bridge / stdio-sdk — [ADR-003](./ADR-003-read-only-mcp-default-policy.md) |
| Harnesses | `harnesses/` (10+1) | 하네스별 overlay (AGENTS.md, apply_guide, SKILL.md) | HARNESS_SPECS 레지스트리. **CodeWhale v0.10.4 신규** |
| State Memory | `ai-workflow/memory/` + `ai-workflow/memory/active/memory_index/` | 세션/릴리스별 state, backlog, handoff, ADR-005 memory index | .gitignore 일부 — [ADR-001](./ADR-001-source-state-knowledge-3-layer-separation.md), [ADR-005](./ADR-005-memora-inspired-memory-index.md) |
| Knowledge Base | `docs/` | 영구 지식, PR 리뷰 대상 | governance: `docs/index.md` |
| Contract v1 | `core/orchestrator_subagent_contract_v1.md` + `workflow_kit/contract_v1/` | 외부 spec + Pydantic v2 helper | [ADR-002](./ADR-002-pydantic-v2-contract-v1-external-spec.md) |

상세 모듈/함수 명세: [`../CODE_INDEX.md`](../CODE_INDEX.md) §2.

## 4. 향후 작성 예정 (Backlog)

- [x] **ADR-001: Source/State/Knowledge 3-layer 분리 결정** (v0.5.11 작성) — [ADR-001](./ADR-001-source-state-knowledge-3-layer-separation.md)
- [x] **ADR-002: Pydantic v2 contract v1 외부 spec 채택** (v0.5.11 작성) — [ADR-002](./ADR-002-pydantic-v2-contract-v1-external-spec.md)
- [x] **ADR-003: Read-only MCP 우선 정책** (v0.5.11 작성) — [ADR-003](./ADR-003-read-only-mcp-default-policy.md)
- [ADR-004: LLM Wiki Layer 도입](./ADR-004-llm-wiki-layer.md) — wiki layer 설계 (v0.6.0 accepted, P1 implemented)
- [Microsoft Memora Evaluation](./MICROSOFT_MEMORA_EVALUATION.md) — Microsoft Research `Memora` 개념과 우리 workflow memory 구조의 접점 정리 (2026-07-02)
- [x] **ADR-005: Memora-inspired Memory Index** (v0.11.22 Phase 1~3d 완료) — [ADR-005](./ADR-005-memora-inspired-memory-index.md). 평가 문서 결론을 정식 결정으로: `memory_index/` 메타데이터 레이어 + retrieval flow 3-tuple + canonical merge 기본 advisory. 3-layer 분리 정합 유지. Phase 1~3d 8 release 완료 (helper + schema + smoke + state.json hook + --merge opt-in + BM25 fallback + dispatcher entry + 3 skill opt-in wiring).
- [ADR-006: ADR-005 Memory Index Retrospective (Placeholder)](./ADR-006-memory-index-retrospective.md) — v0.11.22 의 8 release 누적 retrospective 자리. 회고 본문은 v0.11.23+ 또는 실 사용 30일 후 작성.
- **컴포넌트 다이어그램** — `workflow-source/`, `ai-workflow/`, `docs/` 3-layer 시각화 (mermaid)
- **CI smoke** 의 책임 영역 매트릭스 — v0.5.10 baseline 52 + 누적 200+ smoke + mypy-strict.yml workflow (v0.11.11+) + release-time gate (v0.11.12+) + cross-verify advisory (v0.11.13+)

## 다음에 읽을 문서

- [`../CODE_INDEX.md`](../CODE_INDEX.md) — 코드베이스 구조/진입점
- [`../PROJECT_PROFILE.md`](../PROJECT_PROFILE.md) — 운영 규칙/명령
- [`../INSTALLATION_AND_USAGE.md`](../INSTALLATION_AND_USAGE.md) — 설치·사용 가이드
- [`../DOCUMENT_INDEX.md`](../DOCUMENT_INDEX.md) — docs/ 전체 인덱스
- [`../../workflow-source/core/workflow_agent_topology.md`](../../workflow-source/core/workflow_agent_topology.md) — 다중 에이전트 토폴로지
- [`../../workflow-source/core/global_workflow_standard.md`](../../workflow-source/core/global_workflow_standard.md) — 공통 코어 표준
