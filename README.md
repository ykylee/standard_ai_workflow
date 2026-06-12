# Standard AI Workflow

- 문서 목적: 여러 프로젝트에서 공통으로 사용할 수 있는 표준 AI 협업 워크플로우 문서와 템플릿, 향후 skill/MCP/agent 구현 기준을 독립 프로젝트 형태로 제공한다.
- 범위: 공통 표준 문서, 프로젝트 프로파일 템플릿, 세션 상태 문서 템플릿, skill/MCP/agent 설계 참고 문서
- 대상 독자: 개발자, 운영자, AI agent 설계자, 프로젝트 온보딩 담당자
- 상태: stable
- 최종 수정일: 2026-06-12
- 버전: v0.6.3-beta
- 관련 문서: `./workflow-source/core/global_workflow_standard.md`, `./workflow-source/core/workflow_agent_topology.md`
- 상태 진단 문서: `./workflow-source/core/project_status_assessment.md`
- 상위 로드맵 문서: `./workflow-source/core/workflow_kit_roadmap.md`
- 출력 스키마 가이드: `./workflow-source/core/output_schema_guide.md`
- 도입 분기 가이드: `./workflow-source/core/workflow_adoption_entrypoints.md`
- 상태 문서/프로젝트 문서 경계 가이드: `./workflow-source/core/workflow_state_vs_project_docs.md`
- 하네스 배포 가이드: `./workflow-source/core/workflow_harness_distribution.md`
- 릴리스 규격 가이드: `./workflow-source/core/workflow_release_spec.md`
- 승격 범위 가이드: `./workflow-source/core/prototype_promotion_scope.md`
- read-only MCP transport 승격 기준: `./workflow-source/core/read_only_mcp_transport_promotion.md`
- 하네스별 로컬 MCP 설치 가이드: `./workflow-source/core/mcp_installation_by_harness.md`
- 하네스별 MCP config 예시 5종: `./workflow-source/examples/mcp_config_examples/`
- 설정 계층 가이드: `./workflow-source/core/workflow_configuration_layers.md`
- 비침투적 주입 정책: `./workflow-source/core/workflow_global_injection_policy.md`
- workflow kit 패키지 가이드: `./workflow-source/workflow_kit/README.md`
- **개발자용 설치·사용 가이드 (v0.5.10 신규)**: [`./docs/INSTALLATION_AND_USAGE.md`](./docs/INSTALLATION_AND_USAGE.md)
- **릴리스 절차 가이드 (v0.5.7+)**: [`./docs/RELEASE.md`](./docs/RELEASE.md)

## 1. 이 폴더의 역할

이 저장소는 여러 프로젝트에서 공통으로 사용할 수 있는 표준 AI 워크플로우를 독립 패키지처럼 관리하기 위한 저장소다. 문서와 템플릿만으로도 최소 운영이 가능해야 하며, 이후 `skill`, `MCP`, `agent` 구현이 추가되더라도 같은 구조 안에서 확장할 수 있어야 한다.

핵심 원칙:

- 공통 규칙은 코어 문서로 둔다.
- 저장소별 차이는 프로젝트 프로파일 템플릿에 적는다.
- 세션 상태 문서는 템플릿으로 제공한다.
- `ai-workflow/memory/active/` 아래 문서는 workflow state docs 이고, 실제 프로젝트 운영 문서인 `docs/...` 와 역할을 분리한다.
- skill, MCP, agent 는 설계 카탈로그로 먼저 제공하고, 실제 구현은 프로젝트 상황에 맞게 선택 적용한다.
- 이 저장소만 읽어도 구조를 이해할 수 있게 외부 저장소 의존 링크를 최소화한다.

## 2. 폴더 구성

| 경로 | 역할 |
| --- | --- |
| `workflow-source/core/` | 여러 프로젝트에 공통 적용할 코어 문서 |
| `workflow-source/templates/` | 프로젝트와 세션 상태 문서 템플릿 |
| `workflow-source/skills/` | 향후 공통 skill 구현 위치 |
| `workflow-source/mcp_servers/` | 향후 공통 MCP 구현 위치 |
| `workflow-source/examples/` | 샘플 프로파일과 도입 예시 위치 |
| `workflow-source/global-snippets/` | 하네스 전역 설정에 넣을 수 있는 비침투적 snippet 예시 |
| `workflow-source/harnesses/` | Codex, OpenCode 같은 하네스별 배포 가이드 |
| `workflow-source/scripts/` | end-to-end 데모와 통합 실행 스크립트 위치 |
| `workflow-source/workflow_kit/` | 공통 파서, 분류, runner helper 를 담는 reusable package 루트 |
| `workflow-source/tests/` | 링크/템플릿/구현 smoke test 위치 |
| `workflow-source/releases/` | 릴리즈 노트와 pre-release 기록 위치 |

## 3. 현재 구현 상태

| 영역 | 상태 | 비고 |
| --- | --- | --- |
| 공통 표준 문서 | 사용 가능 | 바로 복사 가능 |
| 프로젝트/세션 템플릿 | 사용 가능 | 값 채우기 필요 |
| 샘플 도입 예시 | 사용 가능 | `workflow-source/examples/acme_delivery_platform/` 참고 |
| skill 프로토타입 | 사용 가능 | `workflow-source/skills/` 및 `workflow-source/scripts/` 참고. 11종 (1차 6종 + 2차 2종 + 3차 3종) |
| skill 카탈로그 | 설계 완료, 프로토타입 포함 | 1차 핵심 skill 4종과 2차 skill 2종 실행형 초안 + 3차 (backlog-steward, robust-patcher, git-conflict-resolver) |
| MCP 프로토타입 | 사용 가능 | `workflow-source/mcp_servers/` 및 MCP 데모 참고. jsonrpc-bridge (안정) + stdio-sdk (실험적) 양쪽 지원 |
| MCP 카탈로그 | 설계 완료, 프로토타입 포함 | 우선순위 1 MCP 실행형 초안 + read_only_mcp_sdk v1.0 SDK candidate |
| 통합 데모 runner | 사용 가능 | `workflow-source/scripts/run_demo_workflow.py`, `workflow-source/scripts/run_existing_project_onboarding.py` 참고 |
| bootstrap scaffold | 사용 가능 | `python3 -m bootstrap_lib` (v0.5.2+ 권장) + 레거시 `bootstrap_workflow_kit.py` shim |
| harness overlays | 사용 가능 | 6개 하네스 대상: `Codex`, `OpenCode`, `Gemini CLI`, `Antigravity`, `MiniMax Code`, `pi-dev` |
| harness interactive picker | 사용 가능 (v0.5.8 신규) | `--harness` 미지정 시 TTY 자동 picker, 비대화형 모드 검증 |
| orchestrator/worker overlays | 사용 가능 | OpenCode orchestrator + doc/code/validation worker 분화 및 위임 패턴 |
| contract v1 (orchestrator ↔ sub-agent) | 사용 가능 (v0.5.4+) | `workflow-source/core/orchestrator_subagent_contract_v1.md` 외부 spec + `workflow_kit/contract_v1/` enforcement helpers (output_validator, delegator.choose_roles). wire 가이드: `orchestrator_contract_v1_wire_guide.md` |
| 다중 컴포넌트 fan-out/in (v0.5.7) | 사용 가능 | `choose_roles` (multi-sub 위임) + `validate_fanin_output` (cross-ref 통합) |
| 다중 에이전트 오케스트레이션 | 사용 가능 | `orchestration_demo.py` 및 피드백 루프 시뮬레이션 |
| 워크플로우 린터 (Skill) | 사용 가능 | `run_workflow_linter.py`를 통한 문서 정합성 자동 검사 및 복구 |
| 실전 스킬 (Git) | 사용 가능 | `run_git_conflict_resolver.py`를 통한 컨텍스트 기반 충돌 해결 |
| harness package export | 사용 가능 | `workflow-source/scripts/export_harness_package.py` 로 dist 산출물 생성. v0.5.8 부터 packaging smoke 자동화 (`tools/check_packaging.py`) |
| 출력 스키마 가이드 | 사용 가능 | `workflow-source/core/output_schema_guide.md` (Pydantic v2 기반) |
| 출력 샘플 JSON | 사용 가능 | skill/MCP/runner 성공/실패 샘플 |
| workflow kit package | 사용 가능 | `workflow_kit` + `bootstrap_lib` + `contract_v1` (v0.5.6+), `common.{state,contracts,schemas,server}` (v0.5.7.1+ wheel 포함) |
| agent 토폴로지 | 설계 완료, 구현 미포함 | 역할과 권한 경계 중심 |

## 4. 권장 도입 순서

1. `workflow-source/core/global_workflow_standard.md` 를 기준 문서로 읽는다.
2. 새 저장소에 `workflow-source/templates/project_workflow_profile_template.md` 를 복사해 프로젝트 특화 규칙을 채운다.
3. `workflow-source/templates/` 아래 세션/백로그 템플릿을 해당 저장소 문서 구조에 맞게 배치한다.
4. `workflow-source/core/workflow_skill_catalog.md`, `workflow-source/core/workflow_mcp_candidate_catalog.md`, `workflow-source/core/workflow_agent_topology.md` 를 읽고 도입 범위를 정한다.
5. 첫 도입은 세션 시작, 백로그 갱신, 문서 동기화처럼 영향이 큰 흐름부터 시작한다.
6. 반복 적용이 필요하면 `workflow-source/scripts/bootstrap_workflow_kit.py` 로 새 저장소용 기본 문서 세트를 생성한다.

도입 시작점은 두 가지로 나눌 수 있다.

- 신규 프로젝트: 템플릿 중심으로 바로 스캐폴딩
- 작업 중인 프로젝트: 기존 코드베이스 분석과 문서 초안 자동 생성부터 시작

배포 타겟은 하네스별로도 나눌 수 있다.

- Codex: `AGENTS.md` 와 Codex 설정 예시 중심
- OpenCode: `AGENTS.md`, `opencode.json`, project-local skill/agent 중심
- Gemini CLI: `GEMINI.md` 중심
- Antigravity: `ANTIGRAVITY.md` 중심
- MiniMax Code: `AGENTS.md` + `MiniMax.md` + `MiniMax_config.example.json` + `.minimax/agents/` (orchestrator + doc/code/validation worker) 중심
- pi-dev: `AGENTS.md` + `SYSTEM.md` (에이전트 페르소나) 중심
- 추후 하네스: 같은 오버레이 패턴과 레지스트리 기반 bootstrap 방식으로 확장 가능 (harness 추가는 `workflow-source/scripts/bootstrap_lib/harnesses/__init__.py` 의 `HARNESS_SPECS` 한 줄 + `bootstrap_lib/__main__.py` 의 `register_harness_builder` 한 줄로 끝난다)

## 5. 로컬 환경 설정 메모

공식 MCP Python SDK 를 이 저장소에서 로컬 검증에 쓰려면 Python 3.10 이상이 필요하다 (3.11+ 권장).

- 공식 패키지 이름은 `mcp` 이다.
- Python 3.9 이하 환경에서는 `mcp` 패키지가 설치되지 않는다.
- **자세한 설치 절차, editable install, 스모크 테스트 실행, 워크플로우 kit 호출, 부트스트랩, MCP 서버 실행, 자주 만나는 문제 해결은 [`./docs/INSTALLATION_AND_USAGE.md`](./docs/INSTALLATION_AND_USAGE.md) 참고.**

## 6. 개발 및 온보딩 가이드 (Self-dogfooding)

이 저장소 자체를 개발할 때(Self-dogfooding) 또는 처음 체크아웃한 후에는 [`./docs/INSTALLATION_AND_USAGE.md`](./docs/INSTALLATION_AND_USAGE.md) 의 §3.A 절차로 editable install 한 뒤, 아래 명령어로 로컬 런타임 도구와 하네스 파일을 동기화한다.

1. **워크플로우 런타임 동기화**:
   원본 소스(`workflow-source/`)를 기반으로 로컬 `ai-workflow/` 런타임 도구를 동기화하고 하네스 파일(예: `ANTIGRAVITY.md`)을 생성합니다.
   ```bash
   python3 -m bootstrap_lib \
     --target-root . \
     --project-slug standard-ai-workflow \
     --project-name "Standard AI Workflow" \
     --harness antigravity \
     --adoption-mode existing \
     --copy-core-docs \
     --force
   ```

2. **상태 동기화**:
   현재의 백로그와 세션 인계 사항을 바탕으로 상태 요약(`state.json`)을 갱신합니다.
   ```bash
   python3 workflow-source/scripts/generate_workflow_state.py \
     --project-profile-path docs/PROJECT_PROFILE.md \
     --session-handoff-path ai-workflow/memory/active/session_handoff.md \
     --work-backlog-index-path ai-workflow/memory/active/work_backlog.md \
     --output-path ai-workflow/memory/active/state.json
   ```

> [!NOTE]
> 하네스 엔트리포인트 파일(`ANTIGRAVITY.md` 등)과 `ai-workflow/` 하위의 실행 도구(`scripts/`, `skills/` 등)는 깃 이력 관리를 위해 `.gitignore`에 등록되어 있습니다. 최초 체크아웃 후에는 위 부트스트랩 명령어를 실행하여 로컬에 생성해 주시기 바랍니다.

## 6. 다른 프로젝트에 적용할 때 최소 복사 세트

최소 세트:

- `workflow-source/core/global_workflow_standard.md`
- `workflow-source/templates/project_workflow_profile_template.md`
- `workflow-source/templates/session_handoff_template.md`
- `workflow-source/templates/work_backlog_template.md`
- `workflow-source/templates/daily_backlog_template.md`

확장 세트:

- `workflow-source/core/workflow_skill_catalog.md`
- `workflow-source/core/workflow_mcp_candidate_catalog.md`
- `workflow-source/core/workflow_agent_topology.md`

## 7. 별도 프로젝트로 분리할 때 권장 구조

- `README.md`
- `workflow-source/core/`
- `workflow-source/templates/`

실제 구현이 시작되면 아래를 추가한다.

- `workflow-source/skills/`
- `workflow-source/mcp_servers/`
- `workflow-source/examples/`
- `workflow-source/tests/`

## 8. bootstrap 사용 예시

새 저장소 또는 임시 디렉터리에 표준 워크플로우 패키지를 생성하려면 아래처럼 실행할 수 있다.

```bash
python3 workflow-source/scripts/bootstrap_workflow_kit.py \
  --target-root /tmp/sample-repo \
  --project-slug sample_api \
  --project-name "Sample API" \
  --harness codex \
  --harness opencode \
  --harness antigravity \
  --copy-core-docs
```

로컬 MCP 까지 함께 심으려면 `--enable-mcp` 옵션을 추가한다. 각 하네스별 MCP config 스니펫이 `<root>/.codex/mcp.toml`, `<root>/mcp.opencode.json`, `<root>/.gemini/mcp.json`, `<root>/antigravity.mcp.json`, `<root>/.MiniMax/mcp.json` 중 선택한 하네스 경로로 emit 된다.

```bash
python3 workflow-source/scripts/bootstrap_workflow_kit.py \
  --target-root <project_root> \
  --project-slug <slug> --project-name "<name>" \
  --harness minimax-code \
  --adoption-mode existing --copy-core-docs \
  --enable-mcp                       # ← 로컬 MCP 동시 심기
  # --mcp-bridge stdio-sdk            # 선택: 정식 SDK stdio 사용 (실험적)
```

자세한 가이드: [workflow-source/core/mcp_installation_by_harness.md](./workflow-source/core/mcp_installation_by_harness.md), 예시 5종: [workflow-source/examples/mcp_config_examples/](./workflow-source/examples/mcp_config_examples/)

기존 프로젝트용 분석 기반 도입은 아래처럼 시작할 수 있다.

```bash
python3 workflow-source/scripts/bootstrap_workflow_kit.py \
  --target-root /tmp/existing-repo \
  --project-slug payments_api \
  --project-name "Payments API" \
  --adoption-mode existing \
  --harness codex \
  --copy-core-docs
```

이 스크립트는 기본적으로 `ai-workflow/` 아래에 아래 구조를 만든다.

- `README.md`
- `project/PROJECT_PROFILE.md`
- `project/session_handoff.md`
- `project/work_backlog.md`
- `project/backlog/YYYY-MM-DD.md`
- `project/repository_assessment.md` (`existing` 모드일 때)
- `AGENTS.md`, `.codex/config.toml.example` (`codex` 선택 시)
- `AGENTS.md`, `opencode.json`, `.opencode/...` (`opencode` 선택 시)
- `GEMINI.md` (`gemini-cli` 선택 시)
- `ANTIGRAVITY.md` (`antigravity` 선택 시)
- 선택 시 `core/*.md`

여기서 역할을 명확히 나누면 아래와 같다.

- `ai-workflow/memory/active/*`: workflow state docs. 세션 복원, backlog 상태, handoff, state cache 의 source-of-truth
- `PROJECT_PROFILE.md` 안의 `docs/...` 경로: 실제 프로젝트 문서 위치. runbook, 운영 허브, project-level handoff 같은 현장 문서 위치

배포 가능한 하네스 패키지를 export 하려면 아래처럼 실행할 수 있다.

```bash
python3 workflow-source/scripts/export_harness_package.py \
  --harness codex \
  --harness opencode
```

이 export 는 이번 릴리즈 기준으로 workflow/skill 온보딩 묶음을 우선 배포한다.

- 기본 소비 진입점: `workflow-source/README.md`, `workflow-source/core/workflow_adoption_entrypoints.md`, `workflow-source/core/workflow_skill_catalog.md`
- 기본 현장 문서: `ai-workflow/memory/active/PROJECT_PROFILE.md`, `ai-workflow/memory/active/state.json`, `ai-workflow/memory/active/session_handoff.md`, `ai-workflow/memory/active/work_backlog.md`
- `ai-workflow/` 는 세션 복원과 workflow 상태 관리용 메타 레이어로 보고, 일반 프로젝트 코드/문서 탐색 범위에서는 기본적으로 제외한다.
- `backlog-update`, `merge-doc-reconcile` 는 source-of-truth 문서가 준비된 경우 `state.json` 을 자동 재생성한다. 독립 실행이 필요할 때는 `workflow-source/scripts/generate_workflow_state.py` 를 직접 사용할 수 있다.
- 기본 export 는 AI agent 컨텍스트 절약을 위해 런타임 파일만 포함하고, source docs 와 global snippet 예시는 제외한다.
- 하네스별 패키지는 `dist/harnesses/<target>/<version>/` 아래 개별 생성되며, zip 파일 이름에도 버전이 포함된다.
- 각 패키지 루트에는 `PACKAGE_CONTENTS.md` 와 `APPLY_GUIDE.md` 가 함께 생성돼 다른 환경에서 바로 적용 흐름을 읽을 수 있다.
- 개발 참고용 원본 문서나 전역 snippet 예시가 필요하면 export 시 opt-in 플래그로만 포함한다.

## 9. 구현 현황 요약

- skill 11종은 공통 `tool_version` 과 구조화된 실패 JSON (`status`, `error`, `error_code`, `warnings`, `source_context`) 패턴을 따른다.
- 통합 runner 2종은 하위 step 결과를 중첩 payload 로 유지하면서 `warnings`, `orchestration_plan`, `source_context` 를 상위 메타데이터로 제공한다.
- runner 는 하위 skill/MCP step 이 `status: "error"` 를 반환해도 상위 `workflow_step_failed` 형태로 감싸고, 실패한 step 이름과 upstream `error_code` 를 `source_context` 에 남긴다.
- OpenCode 는 orchestrator + generic/specialized worker overlay 생성까지 지원하고, Codex 는 동일한 task-only orchestrator + bounded worker 운영 패턴을 문서/템플릿으로 배포한다.
- `workflow_kit.common` (state, contracts, schemas, runner, errors, output_contracts, reconcile, scaffold, doc_sync 등 30+ submodule) 은 v0.5.2+ 본격 추출 진행 중. `workflow_kit/contract_v1/` (v0.5.6+, v0.5.7 multi-component 확장) 은 Pydantic v2 기반 외부 contract enforcement helpers.
- 하네스 export bundle 은 read-only MCP descriptor, 하네스별 MCP 설정 예시 (5종), JSON-RPC fixture 를 함께 포함한다.
- `workflow-source/tests/check_*.py` 52개는 문서, bootstrap, harness export, output sample, generated schema, validation/code-index, onboarding runner, read-only MCP bundle, contract v1 multi-component, wire guide 회귀 까지 smoke 기준선을 제공한다.
- CI 는 `python 3.11` + `PYTHONPATH=workflow-source` + `pip install -r requirements*.txt` 경로로 매 push 마다 52개 smoke 전부 실행.

## 10. v0.6.0 기준 누적 변경 요약 (2026-06-12 이후)

v0.5.4 부터 v0.6.0 까지 누적된 핵심 변경:

- v0.5.4 — orchestrator ↔ sub-agent delegation contract v1 외부 spec + `workflow_kit/contract_v1/` (issue #1 영구 해결)
- v0.5.5 — Phase 11 본격 pilot (Devhub Example × Contract v1 실전 검증)
- v0.5.6 — contract v1 §5/§6 P0 enforcement (output_validator + delegator.choose_role, sub-agent 응답 자동 검증, MUST NOT delegate 7 패턴 거부)
- v0.5.7 — contract v1 §4.2/§5.2 multi-component fan-out/in + recommend_model_tier + wheel packaging 보강 (v0.5.7.1: state/contracts/schemas 포함 누락 fix)
- v0.5.8 — interactive `--harness` picker (TTY 자동 picker) + packaging smoke automation (`tools/check_packaging.py`)
- v0.5.9 / v0.5.9.1 — wire 가이드 §3 sub_payloads + §7/§8/§9 sub.delegation_id parent-prefix rule 명시
- v0.5.10 — `choose_roles` sub.delegation_id parent-prefix spec 정합 (배치 위임 ID 가 `{parent_id}-st-{N}` 형식 강제)

이번 기준선 핵심 결과물:

- Codex package: GitHub release asset `standard-ai-workflow-codex-v0.6.0-beta.zip`
- OpenCode package: GitHub release asset `standard-ai-workflow-opencode-v0.6.0-beta.zip` (planned)
- release note: [releases/Beta-v0.6.0.md](./workflow-source/releases/Beta-v0.6.0.md) (planned)
- 전체 릴리스 노트 (Alpha-v0.1.0 ~ Beta-v0.5.10.1): [releases/](./workflow-source/releases/)

## 11. 현재 한계

- 이 저장소는 문서 패키지 성격이 강하지만, 동시에 skill/MCP/runner 프로토타입과 공통 Python package 를 함께 포함하는 작업 저장소다.
- 프로젝트별 문서 경로와 명령 체계는 `project_workflow_profile_template.md` 를 채운 뒤에야 완성된다.
- 여러 프로젝트에서 시범 적용하기 전에는 공통 규칙이 과도한지 여부를 추가 검증해야 한다.
- `workflow_kit/common` 의 모든 skill/MCP 공통 라이브러리화는 진행 중 (v0.5.2+ 본격 추출, v0.5.7+ contract_v1 추가).
- 다중 실제 저장소 적용 기록과 CI 실패 원인 분류 고도화는 아직 저장소 내부에 충분히 포함되지 않았다.
- 정식 MCP SDK stdio 전송 (`--mcp-bridge stdio-sdk`) 은 실험적이며 알려진 connection-closed 회귀가 있다. 안정 전송은 `--mcp-bridge jsonrpc-bridge` (default).
- `check_workflow_linter.py` 가 `warning` 을 반환하는 것은 v0.5.0 부터의 baseline 동작이며 의도된 통과다.

## 12. 수동 대체 원칙

skill/MCP 구현이 아직 없더라도 아래 문서만으로 수동 운영은 가능해야 한다.

- 세션 시작: `core/global_workflow_standard.md`
- 프로젝트 특화 규칙: `templates/project_workflow_profile_template.md`
- 상태 문서 템플릿: `templates/`

## 다음에 읽을 문서

- **개발자용 설치·사용 가이드 (v0.5.10 신규)**: [docs/INSTALLATION_AND_USAGE.md](./docs/INSTALLATION_AND_USAGE.md)
- **릴리스 절차 (v0.5.7+)**: [docs/RELEASE.md](./docs/RELEASE.md)
- 공통 코어 표준: [workflow-source/core/global_workflow_standard.md](./workflow-source/core/global_workflow_standard.md)
- contract v1 외부 spec: [workflow-source/core/orchestrator_subagent_contract_v1.md](./workflow-source/core/orchestrator_subagent_contract_v1.md)
- contract v1 wire 가이드: [workflow-source/core/orchestrator_contract_v1_wire_guide.md](./workflow-source/core/orchestrator_contract_v1_wire_guide.md)
- 프로젝트 상태 진단: [workflow-source/core/project_status_assessment.md](./workflow-source/core/project_status_assessment.md)
- 상위 로드맵: [workflow-source/core/workflow_kit_roadmap.md](./workflow-source/core/workflow_kit_roadmap.md)
- 마지막 release note: [workflow-source/releases/Beta-v0.5.10.md](./workflow-source/releases/Beta-v0.5.10.md)
- 출력 스키마 가이드: [workflow-source/core/output_schema_guide.md](./workflow-source/core/output_schema_guide.md)
- 도입 분기 가이드: [workflow-source/core/workflow_adoption_entrypoints.md](./workflow-source/core/workflow_adoption_entrypoints.md)
- 하네스 배포 가이드: [workflow-source/core/workflow_harness_distribution.md](./workflow-source/core/workflow_harness_distribution.md)
- 릴리스 규격: [workflow-source/core/workflow_release_spec.md](./workflow-source/core/workflow_release_spec.md)
- 승격 범위 가이드: [workflow-source/core/prototype_promotion_scope.md](./workflow-source/core/prototype_promotion_scope.md)
- read-only MCP transport 승격 기준: [workflow-source/core/read_only_mcp_transport_promotion.md](./workflow-source/core/read_only_mcp_transport_promotion.md)
- workflow kit 패키지: [workflow-source/workflow_kit/README.md](./workflow-source/workflow_kit/README.md)
- 설정 계층 가이드: [workflow-source/core/workflow_configuration_layers.md](./workflow-source/core/workflow_configuration_layers.md)
- 비침투적 주입 정책: [workflow-source/core/workflow_global_injection_policy.md](./workflow-source/core/workflow_global_injection_policy.md)
- 전역 snippet 허브: [workflow-source/global-snippets/README.md](./workflow-source/global-snippets/README.md)
- 샘플 도입 예시: [workflow-source/examples/README.md](./workflow-source/examples/README.md)
- 하네스 허브: [workflow-source/harnesses/README.md](./workflow-source/harnesses/README.md)
- end-to-end 데모: [workflow-source/examples/end_to_end_skill_demo.md](./workflow-source/examples/end_to_end_skill_demo.md)
  여기에는 메인 오케스트레이터와 `doc/code/validation` worker 분배 예시도 포함된다.
- end-to-end MCP 데모: [workflow-source/examples/end_to_end_mcp_demo.md](./workflow-source/examples/end_to_end_mcp_demo.md)
- 출력 샘플: [workflow-source/examples/output_samples/README.md](./workflow-source/examples/output_samples/README.md)
- 스크립트 허브: [workflow-source/scripts/README.md](./workflow-source/scripts/README.md)
- 프로젝트 프로파일 템플릿: [workflow-source/templates/project_workflow_profile_template.md](./workflow-source/templates/project_workflow_profile_template.md)
- agent 토폴로지: [workflow-source/core/workflow_agent_topology.md](./workflow-source/core/workflow_agent_topology.md)
