---
type: topic
status: active
last_ingested_from: ai-workflow/memory/active/main/session_analysis_2026-07-09.md + workflow-source/core/maturity_matrix.json
related_pages:
  - topics/workflow-audit-2026-07-09
  - concepts/project-architecture
  - patterns/frozen-archive-immutability
  - workflow-source/core/maturity_matrix.json
created: 2026-07-09
updated: 2026-07-09
---

# Beta MCP 4종 Stable 승격 로드맵 (2026-07-09)

## TL;DR

본 토픽은 2026-07-09 audit 의 P1-2 후보 (Beta MCP 4종 stable 승격 로드맵 부재) 를 해소하기 위한 작업안. 현 상태 4종 (`git_history_summarizer`, `workflow_log_rotator`, `smart_context_reader`, `apply_robust_patch`) 의 stage maturity 를 평가하고, skill 의 3-batch 승격 패턴을 차용하여 batch 별 승격 일정 + acceptance criteria + 검증 helper 를 정의한다.

## 1. 현 상태 스냅샷 (v0.11.22-beta)

| MCP | stage | server | test | production use |
|---|---|---|---|---|
| `git_history_summarizer` | beta | official_sdk | `tests/check_git_history_summarizer.py` | audit-session / state.json.recent_done_items 보강 |
| `workflow_log_rotator` | beta | official_sdk | (테스트 부재 — 추정) | 미사용 또는 부분 사용 |
| `smart_context_reader` | beta | official_sdk | `tests/check_smart_context_reader.py` | doc-worker / code-worker prompt 의 context load |
| `apply_robust_patch` | beta | official_sdk | (테스트 부재 — 추정) | robust-patcher skill 의 dispatcher 진입점 |

총 8 stable (stdin read-only 7 + 외부 1) + 4 beta. skill 의 9 stable / 1 beta 와 비대칭.

## 2. skill 승격 패턴 (차용 기준)

v0.11.19~v0.11.21 의 3-batch skill stable 승격 패턴 (`Beta-v0.11.19.md`, `Beta-v0.11.20.md`, `Beta-v0.11.21.md` 참조):

| Batch | release | skill | acceptance |
|---|---|---|---|
| 1st | v0.11.19 | session-start / doc-sync / validation-plan / code-index-update | CLI argparse / Pydantic schema / error_code 4종 / 단일 명령 / 예시 실행 섹션 / smoke test 5 case |
| 2nd | v0.11.20 | backlog-update / merge-doc-reconcile / workflow-linter / project-status-assessment | 동일 |
| 3rd | v0.11.21 | robust-patcher | 동일 + 신규 helper (`apply_robust_patch_detailed`) + atomic semantics |

6 조건 stable 정합:
1. CLI argparse 정의 + `--help` 출력
2. Pydantic schema (BaseOutput 패턴)
3. error_code 4종 (예: missing_required / malformed_input / runtime_error / unsupported_option)
4. 단일 명령 진입점
5. 예시 실행 섹션 (`SKILL.md` 또는 README)
6. smoke test ≥ 5 case PASS

## 3. MCP stable 정합 조건 (skill 패턴 차용)

본 토픽은 MCP stable 승격을 위한 다음 6 조건을 제안한다 (skill 6 조건 + MCP 특수):

| # | 조건 | 검증 방법 |
|---|---|---|
| 1 | **MCP tool schema** (input/output Pydantic model) | `workflow_kit/common/schemas/<tool>.py` 존재 + `BaseOutput` 패턴 |
| 2 | **stdio-sdk 통합** | `mcp_servers/read_only_tools.py` / `read_only_registry.py` 등록 + `official_sdk` transport 정상 |
| 3 | **error_code 4종** | `error_code = {missing_required_arg, malformed_input, runtime_error, unsupported_option}` |
| 4 | **단일 진입점** | dispatcher subcommand (skill) 또는 mcp tool (MCP) 단일 노출 |
| 5 | **예시 실행** | `mcp_servers/<tool>/SKILL.md` 또는 README 의 example |
| 6 | **smoke test ≥ 5 case** | `tests/check_<tool>.py` ≥ 5 PASS |

추가: **read-only semantics** — 본 프로젝트의 MCP 는 모두 read-only (ADR-003). beta 4종 모두 read-only 여야 stable 승격.

## 4. batch 별 승격 로드맵 (제안)

본 로드맵은 *제안* 이며, 실제 release 일정은 maintainer 결정 후 backlog 에 반영.

### 4.1 1st batch (P1-2.a, 목표 v0.11.26~v0.11.27)

**대상**: `git_history_summarizer` + `smart_context_reader`

이유:
- 두 도구 모두 *read-only* 가 자연스러움 (history summarize, context read).
- audit / state.json.recent_done_items 보강 + doc-worker context load 라는 실사용처 존재.
- 테스트 파일 존재 (`check_git_history_summarizer.py`, `check_smart_context_reader.py`).

**작업 항목**:
- [ ] 두 도구 schema 정합 (`workflow_kit/common/schemas/{git_history_summarizer,smart_context_reader}.py`)
- [ ] stdio-sdk 등록 확인 (이미 `official_sdk` server 에 등록됨 — 검증)
- [ ] error_code 4종 정의 + 적용
- [ ] `SKILL.md` 작성 (각 mcp_servers/<tool>/)
- [ ] smoke test 5 case 보강 (현재 ≥1 추정, 부족분 추가)
- [ ] `maturity_matrix.json` `promotion_in_release: v0.11.26 (1st batch)` 추가
- [ ] release note 작성 (`Beta-v0.11.26.md` 또는 v0.11.27)
- [ ] 본 토픽 §"Acceptance 기록" 에 batch summary 기록

### 4.2 2nd batch (P1-2.b, 목표 v0.11.28~v0.11.29)

**대상**: `workflow_log_rotator` + `apply_robust_patch`

이유:
- `workflow_log_rotator` 는 workflow 운영 핵심 (log rotation + milestone summary). read-only 의 자연스러운 대상.
- `apply_robust_patch` 는 robust-patcher skill 의 진입점. skill 이 이미 stable (v0.11.21) 이므로 MCP 진입점도 정합 필요.

**작업 항목**:
- [ ] `workflow_log_rotator` 테스트 보강 (`tests/check_workflow_log_rotator.py` 신규)
- [ ] `apply_robust_patch` 테스트 확인 (skill 측 smoke 와 통합)
- [ ] 두 도구 schema 정합
- [ ] stdio-sdk 등록 확인
- [ ] error_code 4종 정의
- [ ] `SKILL.md` 작성
- [ ] smoke test 5 case 확보
- [ ] `maturity_matrix.json` `promotion_in_release: v0.11.28 (2nd batch)` 추가

### 4.3 잔여 사항 (선택)

- skill 의 `automated-repro-scaffold`, `git-conflict-resolver` 의 MCP 진입점 (있다면) 도 동일 패턴 적용.
- 신규 MCP 추가 시 본 로드맵 패턴 차용.

## 5. Acceptance 기록 (placeholder)

| release | 1st batch | 2nd batch | 비고 |
|---|---|---|---|
| v0.11.26 (예정) | git_history_summarizer + smart_context_reader | — |  |
| v0.11.28 (예정) | — | workflow_log_rotator + apply_robust_patch |  |
| v0.11.30 (예정) | 잔여 보강 | — |  |

## 6. Risk / Open issues

- **MCP 4종의 Pydantic schema 가 미작성**. skill stable 승격 시 신규 schema 작성했으나 MCP 는 기존 `dict` emission 가능. 작업 1 에서 신규 schema 작성 필요.
- **stdio-sdk 와 jsonrpc-bridge 의 동시 지원** — MCP 가 두 transport 모두 동작해야 함. 현재는 dual-mode 라고 catalog 에 명시 (`workflow_mcp_candidate_catalog.md` §6). 검증 필요.
- **운영 사용량 측정 부재** — MCP 가 실제로 몇 번 호출되는지 dashboard 없음. P2-3 (quality dashboard) 와 결합 후보.
- **deprecation 정책** — stable 승격 후 breaking change 시 1 release DeprecationWarning → 1 release removal (PROJECT_PROFILE §5). MCP 별 적용.

## 7. 인용 및 후속

- SSOT: [`../../../workflow-source/core/maturity_matrix.json`](../../../workflow-source/core/maturity_matrix.json)
- skill 3-batch 패턴: [`../../../workflow-source/releases/Beta-v0.11.19.md`](../../../workflow-source/releases/Beta-v0.11.19.md) (1st) / [`Beta-v0.11.20.md`](../../../workflow-source/releases/Beta-v0.11.20.md) (2nd) / [`Beta-v0.11.21.md`](../../../workflow-source/releases/Beta-v0.11.21.md) (3rd)
- 본 토픽의 audit 출처: [`workflow-audit-2026-07-09.md`](workflow-audit-2026-07-09.md) §3.2 P1-2
- 후속 작업 시 본 토픽을 wiki index (`ai-workflow/wiki/index.md`) 에 등록 필요.

## 다음에 읽을 문서
- [`workflow-audit-2026-07-09.md`](workflow-audit-2026-07-09.md)
- [`../../../workflow-source/core/maturity_matrix.json`](../../../workflow-source/core/maturity_matrix.json)
- [`../../../workflow-source/core/workflow_mcp_candidate_catalog.md`](../../../workflow-source/core/workflow_mcp_candidate_catalog.md)
- [`../../../workflow-source/core/strategic_threads.md`](../../../workflow-source/core/strategic_threads.md)
