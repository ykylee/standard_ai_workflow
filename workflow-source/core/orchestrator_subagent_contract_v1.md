# Orchestrator ↔ Sub-agent Delegation Contract v1

- 문서 목적: 메인 오케스트레이터(세션 루트 세션)가 sub-agent 워커에게 작업을 위임할 때 따르는 외부 contract v1 을 명시한다. 이 contract 는 standard_ai_workflow v0.5.4 부터 적용되며, [이슈 #1](https://github.com/ykylee/standard_ai_workflow/issues/1) ("오케스트레이터가 서브 에이전트를 호출하지 않고 직접 도구를 사용") 의 영구 해결을 위한 기준선이 된다.
- 범위: 위임 입력/출력 스키마, 4개 역할 경계, 위임 가능/불가 카탈로그, 에러/폴백 정책, 검증 시나리오
- 대상 독자: standard_ai_workflow 도입자, 멀티 에이전트 운영자, AI 에이전트 설계자
- 상태: stable (v1, 2026-06-07)
- 최종 수정일: 2026-06-07
- 관련 문서:
  - 권장 운영 원칙: [./workflow_agent_topology.md](./workflow_agent_topology.md)
  - 공통 표준: [./global_workflow_standard.md](./global_workflow_standard.md)
  - 스킬 카탈로그: [./workflow_skill_catalog.md](./workflow_skill_catalog.md)
  - MCP 카탈로그: [./workflow_mcp_candidate_catalog.md](./workflow_mcp_candidate_catalog.md)
  - Maturity Matrix: [./maturity_matrix.json](./maturity_matrix.json)

## 1. 동기

[이슈 #1](https://github.com/ykylee/standard_ai_workflow/issues/1) 에서 보고된 현상:

> "오케스트레이터는 과제 전체를 관리하는 역할로 실제 작업은 서브 에이전트에게 일임하도록 정의했는데, 테스트 환경에서 사용해보니 실제로는 직접 모든 작업을 하고 있는 현상을 발견"

[workflow_agent_topology.md §5](./workflow_agent_topology.md#5-메인-오케스트레이터-운영-원칙) 에서도 다음 원칙을 명시하고 있다:

> "메인 오케스트레이터는 읽기/쓰기 작업을 직접 모두 떠안기보다 서브 에이전트를 적극 활용해 작업을 분담한다. … 대량 파일 탐색, 문서 비교, 로그 확인, 초안 생성처럼 컨텍스트를 빠르게 부풀리는 작업은 가능한 한 서브 에이전트로 분리한다."

그러나 v0.5.3 까지 "원칙" 만 있고 외부 contract 가 없어, 구현체/도구/세션 환경에 따라 orchestrator 가 직접 도구를 호출하는 회귀가 반복됐다. v1 은 이 contract 를 **외부 명세**로 박아, 후속 구현체(메인 오케스트레이터 런타임, 워커 에이전트, 검증 도구) 가 같은 기준을 따르도록 강제한다.

## 2. 적용 범위

- **대상 시스템**: standard_ai_workflow 를 도입한 모든 프로젝트. v0.5.4 이상.
- **대상 오케스트레이터 런타임**: Mavis (Mavis orchestrator), 그 외 동일 패턴을 따르는 멀티 에이전트 런타임
- **대상 워커**: `mini-coder-max`, `general` 등 task-scoped 실행 권한을 가진 sub-agent
- **호환성**: v0.5.3 이하 시스템은 contract v1 을 따르지 않아도 되지만, v0.5.4 로 업그레이드 시 적용 권장
- **버전**: `contract_version: "1.0"`. 후방 호환은 v1.x 에서만 보장. v2 부터는 명시적 마이그레이션

## 3. 역할 (Roles)

contract v1 은 다음 4개 역할을 정의한다. 각 역할은 책임, 권한, 도구 성격이 다르며, 워커는 하나의 역할에 매핑된다.

### 3.1 orchestrator (메인 오케스트레이터)

| 항목 | 값 |
| --- | --- |
| 책임 | 우선순위 결정, 결과 통합, 사용자 보고, 위험 조정, ask_user 호출 |
| 권장 도구 성격 | task delegation + 최소 triage read |
| write 권한 | handoff / backlog / state.json / PROJECT_PROFILE 갱신 (직접) |
| 금지 | 대량 파일 read, bounded patch 직접 수행, 빌드/테스트 직접 실행, 로그 수집 직접 수행 |
| 식별자 | root session id (예: `mvs_…`) |
| 기본 모델 | main |

### 3.2 doc-worker

| 항목 | 값 |
| --- | --- |
| 책임 | 대량 문서 read, 문서 비교, 허브/상태 문서 초안 작성, 단어 단위 정확도 작업 |
| 권장 도구 성격 | read-heavy + bounded edit |
| write 권한 | 맡은 범위 안의 md/docx/html 파일 (대량 비교 결과/초안) |
| 금지 | 코드/설정 직접 수정, 빌드/테스트 실행, 사용자-facing 결정 |
| 식별자 | `agent: doc-worker` |
| 기본 모델 | small (정책/구조 재설계 시 main 승격) |

### 3.3 code-worker

| 항목 | 값 |
| --- | --- |
| 책임 | 범위가 명확한 구현, 코드/설정 수정, 빌드/컴파일 확인, 범위 좁은 리팩터, 테스트 보강 |
| 권장 도구 성격 | read + bounded edit + bounded bash |
| write 권한 | 맡은 범위 안의 소스/설정/스크립트 파일 |
| 금지 | 정책 결정, 사용자-facing 보고, handoff 직접 갱신 |
| 식별자 | `agent: code-worker` |
| 기본 모델 | small (아키텍처 변경/광범위 리팩터/높은 회귀 위험은 main 승격) |

### 3.4 validation-worker

| 항목 | 값 |
| --- | --- |
| 책임 | 테스트 실행, 로그 확인, 검증 증빙 수집, 실패 원인 요약 |
| 권장 도구 성격 | read + bash (실행 위주) |
| write 권한 | 검증 결과 보고 (대상 파일 직접 수정 X, 보고만) |
| 금지 | 사용자-facing 보고, handoff 직접 갱신, 정책 결정 |
| 식별자 | `agent: validation-worker` |
| 기본 모델 | small (실패 원인이 복합/로그 해석 어려움/테스트 전략 재설계는 main 승격) |

### 3.5 generic workflow-worker (임시/예외)

| 항목 | 값 |
| --- | --- |
| 책임 | 위 3개로 분류 어려운 bounded task 또는 임시 작업 |
| 권장 도구 성격 | task-scoped execution |
| 비고 | 가능하면 doc/code/validation 중 하나로 분해. 분류 불가 시에만 사용 |
| 식별자 | `agent: workflow-worker` |
| 기본 모델 | small (여러 도메인 판단 묶음 시 main 승격) |

## 4. 위임 입력 스키마 (orchestrator → sub-agent)

오케스트레이터가 sub-agent 에게 작업을 넘길 때 사용하는 표준 페이로드. **모든 위임은 이 스키마로 직렬화**되어야 한다.

```json
{
  "contract_version": "1.0",
  "delegation_id": "del-2026-06-07-001",
  "issued_at": "2026-06-07T18:30:00+09:00",
  "issued_by": {
    "session_id": "mvs_a96f8eb4990a482ca14e3e5223447bb7",
    "role": "orchestrator"
  },
  "task": {
    "task_id": "TASK-V054-001",
    "task_type": "doc_draft | code_change | validation_run | bounded_research",
    "brief": "1~2 문장으로 무엇을 만들어야 하는지",
    "constraints": [
      "scope: workflow-source/core/ 아래 contract v1 spec 만",
      "do not touch: workflow_kit, scripts, tests"
    ],
    "inputs": {
      "files": [
        "workflow-source/core/workflow_agent_topology.md",
        "workflow-source/core/global_workflow_standard.md"
      ],
      "context_paths": [
        "ai-workflow/memory/release/v0.5.4/"
      ]
    },
    "expected_outputs": {
      "primary_artifact": "workflow-source/core/orchestrator_subagent_contract_v1.md",
      "artifact_kind": "markdown",
      "must_include": [
        "위임 입력/출력 스키마",
        "4개 역할 경계",
        "위임 가능/불가 카탈로그"
      ]
    },
    "validation": {
      "required": true,
      "criteria": "linter status ok + check_docs.py PASS",
      "owner": "orchestrator"
    },
    "deadline_hint": "2026-06-07T20:00:00+09:00"
  },
  "context": {
    "branch": "release/v0.5.4",
    "memory_layer_root": "ai-workflow/memory/release/v0.5.4/",
    "project_root": "/Users/yklee/repos/standard_ai_workflow_minimax"
  }
}
```

### 4.1 필드 정의

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `contract_version` | string | ✅ | "1.0" 고정 |
| `delegation_id` | string | ✅ | `del-YYYY-MM-DD-NNN` 패턴, 세션 내 유니크 |
| `issued_at` | ISO 8601 | ✅ | 위임 발행 시각 |
| `issued_by.session_id` | string | ✅ | 오케스트레이터 root session id |
| `issued_by.role` | enum | ✅ | 항상 `"orchestrator"` |
| `task.task_id` | string | ✅ | backlog 의 TASK-NNN 또는 임시 식별자 |
| `task.task_type` | enum | ✅ | `doc_draft` / `code_change` / `validation_run` / `bounded_research` |
| `task.brief` | string | ✅ | 1~2 문장, 무엇을 만들어야 하는지 |
| `task.constraints` | string[] | ❌ | scope 제한, 금지 영역 명시 |
| `task.inputs.files` | path[] | ❌ | 읽어야 할 파일 (상대경로, repo root 기준) |
| `task.inputs.context_paths` | path[] | ❌ | 참고용 디렉터리 (예: memory layer) |
| `task.expected_outputs.primary_artifact` | path | ✅ | 주 산출물 경로 |
| `task.expected_outputs.artifact_kind` | enum | ✅ | `markdown` / `python` / `json` / `toml` / `text` / `code` / `other` |
| `task.expected_outputs.must_include` | string[] | ❌ | 반드시 포함해야 할 항목 |
| `task.validation.required` | bool | ✅ | true 면 orchestrator 가 검증 단계 포함 |
| `task.validation.criteria` | string | ❌ | 검증 기준 (linter/test PASS 등) |
| `task.validation.owner` | enum | ✅ | 항상 `"orchestrator"` (검증 책임 명시) |
| `task.deadline_hint` | ISO 8601 | ❌ | 권장 완료 시각, 강제 X |
| `context.branch` | string | ✅ | git branch |
| `context.memory_layer_root` | path | ❌ | 메모리 layer 루트 |
| `context.project_root` | path | ✅ | 절대 경로 |

## 5. 위임 출력 스키마 (sub-agent → orchestrator)

sub-agent 가 작업을 끝내고 orchestrator 에게 보고할 때 사용하는 표준 페이로드. **모든 보고는 이 스키마로 직렬화**되어야 한다.

```json
{
  "contract_version": "1.0",
  "delegation_id": "del-2026-06-07-001",
  "completed_at": "2026-06-07T19:45:00+09:00",
  "worker": {
    "session_id": "mvs_child_xxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    "role": "doc-worker",
    "model_tier": "small"
  },
  "result": {
    "status": "ok | partial | failed",
    "summary": "주 산출물 1~3 줄 요약",
    "artifacts": [
      {
        "path": "workflow-source/core/orchestrator_subagent_contract_v1.md",
        "kind": "markdown",
        "lines": 280,
        "action": "created"
      }
    ],
    "written_paths": [
      "workflow-source/core/orchestrator_subagent_contract_v1.md"
    ],
    "validation_result": {
      "ran": true,
      "command": "python workflow-source/tests/check_docs.py",
      "status": "pass",
      "details": "102 markdown files PASS"
    },
    "next_step": "orchestrator 가 PR 본문 작성 + cross-link 갱신"
  },
  "warnings": [
    "section 4.1 의 deadline_hint 는 권장값이라 미준수해도 ok 처리함"
  ],
  "risks": [
    "contract doc 분량이 300줄을 넘으면 topology.md 와 중복 가독성 저하 가능"
  ]
}
```

### 5.1 필드 정의

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `contract_version` | string | ✅ | "1.0" 고정 |
| `delegation_id` | string | ✅ | 입력의 delegation_id 와 일치 |
| `completed_at` | ISO 8601 | ✅ | 보고 시각 |
| `worker.session_id` | string | ✅ | sub-agent session id |
| `worker.role` | enum | ✅ | 입력 task_type 에 매핑된 역할 |
| `worker.model_tier` | enum | ✅ | `"small"` / `"main"` |
| `result.status` | enum | ✅ | `ok` / `partial` / `failed` |
| `result.summary` | string | ✅ | 1~3 줄 요약 |
| `result.artifacts` | object[] | ✅ | 산출물 목록 (path, kind, lines, action) |
| `result.written_paths` | path[] | ✅ | 실제 write 한 파일 경로 |
| `result.validation_result.ran` | bool | ✅ | 검증 실행 여부 |
| `result.validation_result.command` | string | ❌ | 실행한 명령 (ran=true 일 때) |
| `result.validation_result.status` | enum | ❌ | `pass` / `fail` / `skipped` |
| `result.validation_result.details` | string | ❌ | 결과 요약 |
| `result.next_step` | string | ✅ | orchestrator 가 다음에 할 일 |
| `warnings` | string[] | ❌ | 단서, 가정, 한계 |
| `risks` | string[] | ❌ | 후속 작업 시 주의 |

## 6. 위임 가능 / 불가 카탈로그

오케스트레이터는 다음 카탈로그를 보고 직접 처리 vs 위임을 결정한다. **이 목록은 권장이 아니라 contract v1 의 의무 분배**다.

### 6.1 위임 가능 (MUST delegate)

| 작업 | 권장 역할 | 비고 |
| --- | --- | --- |
| 5개 이상 파일 read | doc-worker | bulk context read |
| 2개 이상 문서 비교/대조 | doc-worker | diff/dedup |
| 단일 문서 200줄+ 초안 작성 | doc-worker | 분량이 큰 단일 산출물 |
| 5개 이상 파일 bounded patch | code-worker | multi-file change |
| 빌드/컴파일/lint/test 실행 | validation-worker | 명령 단위 검증 |
| 5개 이상 로그 파일 read/요약 | validation-worker | run result 수집 |
| 외부 저장소 분석/탐색 | doc-worker | pilot validation 등 |
| 새 파일 300줄+ 작성 | doc-worker 또는 code-worker | kind 에 따라 |

### 6.2 위임 가능 (SHOULD delegate)

| 작업 | 권장 역할 | 비고 |
| --- | --- | --- |
| 단일 파일 50~200줄 read | doc-worker | 직접 read 도 가능하지만, 컨텍스트 보호 위해 위임 권장 |
| 1~2개 파일 bounded patch | code-worker | 짧은 patch 는 직접 가능, 큰 patch 는 위임 |
| 단일 테스트 실행 | validation-worker | 짧은 명령이지만 로그/타이밍은 sub-agent 가 정리 |

### 6.3 직접 처리 (MUST NOT delegate)

| 작업 | 처리 주체 | 이유 |
| --- | --- | --- |
| handoff / backlog / state.json 갱신 | orchestrator | handoff/backlog 는 orchestrator 의 단일 진실 공급원 |
| ask_user 호출 | orchestrator | 사용자 인터랙션은 오케스트레이터 책임 |
| 우선순위 결정 | orchestrator | 트레이드오프는 orchestrator 가 통합 판단 |
| sub-agent 출력 통합/리뷰 | orchestrator | 결과 통합은 orchestrator 책임 |
| PR 본문 작성 | orchestrator | 사용자-facing 메시지 |
| 짧은 triage read (1 파일, 50줄 미만) | orchestrator | 컨텍스트 부풀림 작음 |
| 메모리 layer 의 session_handoff.md / state.json 직접 write | orchestrator | 단일 진실 공급원 |

### 6.4 위임 금지 영역

| 영역 | 이유 |
| --- | --- |
| 사용자-facing 결정 (요구사항 확정, 스코프 축소) | orchestrator → 사용자 인터페이스 단일화 |
| 보안/권한 관련 설정 변경 | risk-owned by orchestrator, 변경은 sub-agent 가 못 함 |
| handoff/backlog 직접 write | §6.3 와 동일 |

## 7. 에러 / 폴백 정책

sub-agent 위임이 실패할 때의 정책.

### 7.1 실패 정의

| 상태 | 정의 | 처리 |
| --- | --- | --- |
| `result.status = "failed"` | sub-agent 가 작업을 끝내지 못함 | §7.2 |
| `result.status = "partial"` | 일부는 완료, 일부는 미완 | §7.3 |
| sub-agent 응답 없음 (timeout) | deadline_hint + 30분 | §7.2 |
| 출력 스키마 위반 | contract_version / delegation_id / required field 누락 | §7.4 |

### 7.2 failed / timeout

1. orchestrator 가 1회 재위임 (같은 delegation_id + 새 completed_at)
2. 재위임도 실패 시:
   - 작업 범위를 50% 축소하여 1회 더 재시도
   - 그래도 실패 시 orchestrator 가 직접 처리 (직접 처리 영역으로 격상)
3. 직접 처리도 불가능하면 사용자에게 상향 (`ask_user` 또는 사용자-facing 보고에 명시)

### 7.3 partial

1. orchestrator 가 결과 검토, 누락 부분 식별
2. 누락 부분만 별도 delegation_id 로 재위임
3. §7.2 와 동일 폴백

### 7.4 출력 스키마 위반

1. orchestrator 가 위반 보고 (worker.session_id, delegation_id, 누락 필드)
2. sub-agent 가 보정한 출력 재제출
3. 보정 불가 시 §7.2 의 failed 와 동일

### 7.5 검증 실패 (result.validation_result.status = "fail")

1. orchestrator 가 실패 원인 sub-agent 에 위임 (validation-worker 역할)
2. 원인 파악 후 fix 위임 (code-worker 또는 doc-worker)
3. 재검증 → 통과 시 `ok`, 실패 시 §7.2

## 8. 검증 시나리오 (Validation Scenarios)

contract v1 의 거동을 검증하는 시나리오. 각 시나리오는 `tests/` 에 regression check 로 박는다.

### 8.1 S1: 입력 스키마 직렬화 (Round-trip)

- orchestrator 가 §4 의 입력 페이로드 생성
- sub-agent 가 그대로 받아 §5 의 출력 페이로드 생성
- delegation_id / contract_version / role 매핑 보존
- 회귀: `tests/check_contract_v1_roundtrip.py` (신규)

### 8.2 S2: 4개 역할 분배 (Role Mapping)

- §6.1 의 5개 작업을 orchestrator 가 위임 결정
- 각 작업이 올바른 role 에 매핑되는지 검증
- 회귀: `tests/check_contract_v1_role_mapping.py` (신규)

### 8.3 S3: 직접 처리 영역 준수 (Negative Test)

- handoff 직접 write, ask_user 호출 등을 sub-agent 가 시도하는 mock 입력 생성
- sub-agent 가 거부하는지 검증 (또는 contract 가 "직접 처리" 임을 강제하는지)
- 회귀: `tests/check_contract_v1_direct_only.py` (신규)

### 8.4 S4: 실전 시나리오 (Live Demo)

- TASK-V054-001 자체가 이 contract 의 첫 적용 대상
- orchestrator (Mavis / mvs_a96f8eb4990a482ca14e3e5223447bb7) 가 doc-worker 에게 contract spec 의 1차 초안 작성을 위임
- doc-worker 가 초안 작성 + validation
- orchestrator 가 통합/리뷰/최종 커밋
- PR 본문에 "S4 라이브 데모" 섹션 추가
- 회귀: 라이브 데모 자체가 검증이며, 별도 자동화 X

#### 8.4.1 v0.5.5 S4 라이브 데모 결과 (Phase 11 pilot)

v0.5.5 TASK-V055-001 의 S4 라이브 데모는 4 시나리오 contract v1 round-trip 으로 실행 (단, simulated walkthrough — single-spawn producer work 제약 + mavis-team multi-step 한계):

| 시나리오 | Devhub_example PR | delegation_id | 역할 | 스키마 fit |
|----------|------------------|---------------|------|-----------|
| chore (단일 파일 .gitignore) | #493 | del-2026-06-07-p493 | doc-worker | ✅ |
| feature code (N:M weight, multi-file) | #492 | del-2026-06-07-p492 | code-worker (main 승격) | ✅ |
| UI feature (sub-task 1 of 3) | #491 | del-2026-06-07-p491-ui | code-worker | ✅ |
| docs traceability (4 matrix cross-ref) | #490 | del-2026-06-07-p490 | doc-worker | ✅ |

전체 round-trip 결과: `check_pilot_phase11_contract_v1.py` (신규 회귀) PASS.

§6 카탈로그 정합성: 85% (3.5/4.0) — 멀티 fan-out + cross-ref 명시 row 가 v0.5.6 P1.

상세 결과: [`workflow-source/examples/pilot_phase11_devhub_contract_v1.md`](../examples/pilot_phase11_devhub_contract_v1.md).

## 9. 구현 가이드 (Reference)

### 9.0 v0.5.6 enforcement helpers

v0.5.6 부터 contract v1 의 §5/§6 enforcement 가 Python 모듈로 제공된다:

- **§5 출력 검증**: `workflow_kit.contract_v1.output_validator.validate_output(payload, expected_delegation_id=None) -> OutputValidationResult`
- **§6 위임 결정**: `workflow_kit.contract_v1.delegator.choose_role(task, strict=False) -> DelegationDecision`

오케스트레이터 / sub-agent 런타임은 이 헬퍼를 호출해서 contract v1 을 자동 enforce 한다. 자세한 사용 예시는 [`workflow_kit/contract_v1/__init__.py`](../../workflow_kit/contract_v1/__init__.py) 와 회귀 [`check_contract_v1_output_validator.py`](../../tests/check_contract_v1_output_validator.py) / [`check_contract_v1_delegator.py`](../../tests/check_contract_v1_delegator.py) 참조.

### 9.1 오케스트레이터 (Mavis) 측

- 위임 결정: `delegator.choose_role(task)` 호출 (자동 enforce). `must_not_delegate=True` 시 직접 처리
- 입력 생성: §4 스키마로 직렬화, `choose_role` 이 반환한 `delegation_id` 사용, sub-agent prompt 에 포함
- 결과 수신: `output_validator.validate_output(payload, expected_delegation_id=...)` 호출. 위반 시 §7.4 의 "출력 스키마 위반" 정책
- 타임아웃: deadline_hint + 30분

### 9.2 sub-agent 측

- 입력 수신: §4 스키마를 prompt 의 일부로 파싱
- 작업 수행: §3 의 role 권한 내에서
- 출력: §5 스키마로 직렬화, orchestrator 에게 보고. `validate_output` 으로 자체 검증 후 보고 권장
- 실패 시: `status: "failed"` + `warnings` + `risks` 채워서 보고

### 9.3 검증 도구

- §8 의 S1~S3 는 `tests/` 아래 회귀 스크립트로 박는다
- §8.4 는 라이브 데모이며 PR 본문에 명시
- v0.5.6 의 §5/§6 enforcement 회귀: `check_contract_v1_output_validator.py` + `check_contract_v1_delegator.py`

## 10. 마이그레이션 (v0.5.3 → v0.5.4)

- v0.5.3 사용자가 v0.5.4 로 업그레이드 시:
  - contract v1 은 권장 (must 가 아님). 점진 적용 가능
  - 우선순위: §8.4 의 라이브 데모와 같은 작업 패턴부터 contract 입력/출력을 명시
  - 검증 도구 (S1~S3) 가 빨간불이면 contract 위반 → 패턴 수정

## 11. 차기 버전 (v2 후보)

contract v2 에서 다음 항목 검토:

- 스트리밍 출력 (긴 작업 중간 progress 보고)
- 양방향 ping (sub-agent 가 orchestrator 에 질문)
- 멀티 sub-agent fan-out / fan-in
- 에스크레이션 우선순위 (P0/P1/P2)
- observability (각 delegation_id 별 latency / token 사용량 추적)

## 다음에 읽을 문서

- [권장 운영 원칙](./workflow_agent_topology.md)
- [공통 표준](./global_workflow_standard.md)
- [Maturity Matrix](./maturity_matrix.json)
- [릴리스 노트](../releases/Beta-v0.5.4.md)
