# Standard AI Workflow

- 문서 목적: 여러 프로젝트에서 공통으로 사용할 수 있는 표준 AI 협업 워크플로우 문서와 템플릿, 향후 skill/MCP/agent 구현 기준을 독립 프로젝트 형태로 제공한다.
- 범위: 공통 표준 문서, 프로젝트 프로파일 템플릿, 세션 상태 문서 템플릿, skill/MCP/agent 설계 참고 문서, 분리 체크리스트
- 대상 독자: 개발자, 운영자, AI agent 설계자, 프로젝트 온보딩 담당자
- 상태: draft
- 최종 수정일: 2026-04-23
- 관련 문서: `./core/global_workflow_standard.md`, `./core/workflow_agent_topology.md`, `./split_checklist.md`
- 상태 진단 문서: `./core/project_status_assessment.md`
- 상위 로드맵 문서: `./core/workflow_kit_roadmap.md`
- 출력 스키마 가이드: `./core/output_schema_guide.md`
- 도입 분기 가이드: `./core/workflow_adoption_entrypoints.md`
- 상태 문서/프로젝트 문서 경계 가이드: `./core/workflow_state_vs_project_docs.md`
- 하네스 배포 가이드: `./core/workflow_harness_distribution.md`
- 릴리스 규격 가이드: `./core/workflow_release_spec.md`
- 승격 범위 가이드: `./core/prototype_promotion_scope.md`
- read-only MCP transport 승격 기준: `./core/read_only_mcp_transport_promotion.md`
- 설정 계층 가이드: `./core/workflow_configuration_layers.md`
- 비침투적 주입 정책: `./core/workflow_global_injection_policy.md`
- workflow kit 패키지 가이드: `./workflow_kit/README.md`

## 1. 이 폴더의 역할

이 저장소는 여러 프로젝트에서 공통으로 사용할 수 있는 표준 AI 워크플로우를 독립 패키지처럼 관리하기 위한 저장소다. 문서와 템플릿만으로도 최소 운영이 가능해야 하며, 이후 `skill`, `MCP`, `agent` 구현이 추가되더라도 같은 구조 안에서 확장할 수 있어야 한다.

핵심 원칙:

- 공통 규칙은 코어 문서로 둔다.
- 저장소별 차이는 프로젝트 프로파일 템플릿에 적는다.
- 세션 상태 문서는 템플릿으로 제공한다.
- `ai-workflow/project/` 아래 문서는 workflow state docs 이고, 실제 프로젝트 운영 문서인 `docs/...` 와 역할을 분리한다.
- skill, MCP, agent 는 설계 카탈로그로 먼저 제공하고, 실제 구현은 프로젝트 상황에 맞게 선택 적용한다.
- 이 저장소만 읽어도 구조를 이해할 수 있게 외부 저장소 의존 링크를 최소화한다.

## 2. 폴더 구성

| 경로 | 역할 |
| --- | --- |
| `core/` | 여러 프로젝트에 공통 적용할 코어 문서 |
| `templates/` | 프로젝트와 세션 상태 문서 템플릿 |
| `skills/` | 향후 공통 skill 구현 위치 |
| `mcp/` | 향후 공통 MCP 구현 위치 |
| `examples/` | 샘플 프로파일과 도입 예시 위치 |
| `global-snippets/` | 하네스 전역 설정에 넣을 수 있는 비침투적 snippet 예시 |
| `harnesses/` | Codex, OpenCode 같은 하네스별 배포 가이드 |
| `scripts/` | end-to-end 데모와 통합 실행 스크립트 위치 |
| `workflow_kit/` | 공통 파서, 분류, runner helper 를 담는 reusable package 루트 |
| `tests/` | 링크/템플릿/구현 smoke test 위치 |
| `releases/` | 릴리즈 노트와 pre-release 기록 위치 |
| `split_checklist.md` | 별도 프로젝트로 분리할 때 수행할 체크리스트 |

## 3. 현재 구현 상태

| 영역 | 상태 | 비고 |
| --- | --- | --- |
| 공통 표준 문서 | 사용 가능 | 바로 복사 가능 |
| 프로젝트/세션 템플릿 | 사용 가능 | 값 채우기 필요 |
| 샘플 도입 예시 | 사용 가능 | `examples/acme_delivery_platform/` 참고 |
| skill 프로토타입 | 사용 가능 | `session-start`, `backlog-update`, `doc-sync`, `merge-doc-reconcile`, `validation-plan`, `code-index-update` 포함 |
| skill 카탈로그 | 설계 완료, 프로토타입 포함 | 1차 핵심 skill 4종과 2차 skill 2종 실행형 초안 있음 |
| MCP 프로토타입 | 사용 가능 | `mcp/` 및 MCP 데모 참고 |
| MCP 카탈로그 | 설계 완료, 프로토타입 포함 | 우선순위 1 MCP 실행형 초안 있음 |
| 통합 데모 runner | 사용 가능 | `scripts/run_demo_workflow.py`, `scripts/run_existing_project_onboarding.py` 참고 |
| bootstrap scaffold | 사용 가능 | `scripts/bootstrap_workflow_kit.py` 참고 |
| harness overlays | 사용 가능 | `Codex`, `OpenCode`, `Gemini CLI`, `Antigravity` 대상 오버레이 생성 가능 |
| orchestrator/worker overlays | 사용 가능 | OpenCode 문서/구현/검증 worker 분화와 orchestrator task-only 운영 기본 원칙 포함 |
| harness package export | 사용 가능 | `scripts/export_harness_package.py` 로 dist 산출물 생성 가능 |
| 출력 스키마 가이드 | 사용 가능 | `validation-plan`, `code-index-update` 포함 |
| 출력 샘플 JSON | 사용 가능 | skill/MCP/runner 성공/실패 샘플 포함 |
| workflow kit package | 사용 가능 | `workflow_kit/common` 에 공통 파서/분류/helper 축적 중 |
| agent 토폴로지 | 설계 완료, 구현 미포함 | 역할과 권한 경계 중심 |

## 4. 권장 도입 순서

1. `core/global_workflow_standard.md` 를 기준 문서로 읽는다.
2. 새 저장소에 `project_workflow_profile_template.md` 를 복사해 프로젝트 특화 규칙을 채운다.
3. `templates/` 아래 세션/백로그 템플릿을 해당 저장소 문서 구조에 맞게 배치한다.
4. `core/workflow_skill_catalog.md`, `core/workflow_mcp_candidate_catalog.md`, `core/workflow_agent_topology.md` 를 읽고 도입 범위를 정한다.
5. 첫 도입은 세션 시작, 백로그 갱신, 문서 동기화처럼 영향이 큰 흐름부터 시작한다.
6. 반복 적용이 필요하면 `scripts/bootstrap_workflow_kit.py` 로 새 저장소용 기본 문서 세트를 생성한다.

도입 시작점은 두 가지로 나눌 수 있다.

- 신규 프로젝트: 템플릿 중심으로 바로 스캐폴딩
- 작업 중인 프로젝트: 기존 코드베이스 분석과 문서 초안 자동 생성부터 시작

배포 타겟은 하네스별로도 나눌 수 있다.

- Codex: `AGENTS.md` 와 Codex 설정 예시 중심
- OpenCode: `AGENTS.md`, `opencode.json`, project-local skill/agent 중심
- Gemini CLI: `GEMINI.md` 중심
- Antigravity: `ANTIGRAVITY.md` 중심
- 추후 하네스: 같은 오버레이 패턴과 레지스트리 기반 bootstrap 방식으로 확장 가능

## 5. 로컬 환경 설정 메모

공식 MCP Python SDK 를 이 저장소에서 로컬 검증에 쓰려면 Python 3.10 이상이 필요하다.

- 공식 패키지 이름은 `mcp` 이다.
- 현재 저장소에서는 Python 3.11 기반 `.venv` 가상환경을 기준으로 검증했다.
- macOS/Homebrew 기준 Python 3.11 설치 경로는 `/opt/homebrew/bin/python3.11` 이다.

이번 로컬 검증 환경 메모:

- OS: macOS `26.4.1`
- 아키텍처: `arm64`
- Homebrew 경로: `/opt/homebrew/bin/brew`
- Homebrew Python 경로: `/opt/homebrew/bin/python3.11`
- 저장소 가상환경 경로: `/Users/yklee/repos/standard_ai_workflow/.venv`
- 가상환경 Python: `3.11.15`
- 설치된 MCP Python SDK: `mcp 1.27.0`
- MCP site-packages 경로: `/Users/yklee/repos/standard_ai_workflow/.venv/lib/python3.11/site-packages`

최초 1회 설정 예시:

```bash
brew install python@3.11
rm -rf .venv
/opt/homebrew/bin/python3.11 -m venv .venv
./.venv/bin/python -m pip install --upgrade pip
./.venv/bin/python -m pip install "mcp[cli]"
```

가상환경 사용 예시:

```bash
source .venv/bin/activate
python -m pip show mcp
python tests/check_read_only_mcp_sdk_candidate.py
python tests/check_read_only_mcp_sdk_stdio.py
```

현재 확인된 설치 기준:

- Python: `3.11.15`
- MCP Python SDK: `mcp 1.27.0`

주의:

- Python 3.9 이하 환경에서는 공식 `mcp` 패키지가 설치되지 않는다.
- 이 저장소 루트에는 `mcp/` 디렉터리가 있으므로, SDK import 검증은 가상환경 Python 으로 실행해야 혼동이 없다.
- official SDK candidate 는 [workflow_kit/server/read_only_mcp_sdk.py](./workflow_kit/server/read_only_mcp_sdk.py) 에 있고, 설치 확인 스모크는 [tests/check_read_only_mcp_sdk_candidate.py](./tests/check_read_only_mcp_sdk_candidate.py) 를 사용한다.
- 실제 stdio round-trip 상호운용 스모크는 [tests/check_read_only_mcp_sdk_stdio.py](./tests/check_read_only_mcp_sdk_stdio.py) 를 사용한다.

## 6. 다른 프로젝트에 적용할 때 최소 복사 세트

최소 세트:

- `core/global_workflow_standard.md`
- `templates/project_workflow_profile_template.md`
- `templates/session_handoff_template.md`
- `templates/work_backlog_template.md`
- `templates/daily_backlog_template.md`

확장 세트:

- `core/workflow_skill_catalog.md`
- `core/workflow_mcp_candidate_catalog.md`
- `core/workflow_agent_topology.md`

## 7. 별도 프로젝트로 분리할 때 권장 구조

- `README.md`
- `split_checklist.md`
- `core/`
- `templates/`

실제 구현이 시작되면 아래를 추가한다.

- `skills/`
- `mcp/`
- `examples/`
- `tests/`

## 8. bootstrap 사용 예시

새 저장소 또는 임시 디렉터리에 표준 워크플로우 패키지를 생성하려면 아래처럼 실행할 수 있다.

```bash
python3 scripts/bootstrap_workflow_kit.py \
  --target-root /tmp/sample-repo \
  --project-slug sample_api \
  --project-name "Sample API" \
  --harness codex \
  --harness opencode \
  --harness antigravity \
  --copy-core-docs
```

기존 프로젝트용 분석 기반 도입은 아래처럼 시작할 수 있다.

```bash
python3 scripts/bootstrap_workflow_kit.py \
  --target-root /tmp/existing-repo \
  --project-slug payments_api \
  --project-name "Payments API" \
  --adoption-mode existing \
  --harness codex \
  --copy-core-docs
```

이 스크립트는 기본적으로 `ai-workflow/` 아래에 아래 구조를 만든다.

- `README.md`
- `project/project_workflow_profile.md`
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

- `ai-workflow/project/*`: workflow state docs. 세션 복원, backlog 상태, handoff, state cache 의 source-of-truth
- `project_workflow_profile.md` 안의 `docs/...` 경로: 실제 프로젝트 문서 위치. runbook, 운영 허브, project-level handoff 같은 현장 문서 위치

배포 가능한 하네스 패키지를 export 하려면 아래처럼 실행할 수 있다.

```bash
python3 scripts/export_harness_package.py \
  --harness codex \
  --harness opencode
```

이 export 는 이번 릴리즈 기준으로 workflow/skill 온보딩 묶음을 우선 배포한다.

- 기본 소비 진입점: `ai-workflow/README.md`, `ai-workflow/core/workflow_adoption_entrypoints.md`, `ai-workflow/core/workflow_skill_catalog.md`
- 기본 현장 문서: `ai-workflow/project/project_workflow_profile.md`, `ai-workflow/project/state.json`, `ai-workflow/project/session_handoff.md`, `ai-workflow/project/work_backlog.md`
- `ai-workflow/` 는 세션 복원과 workflow 상태 관리용 메타 레이어로 보고, 일반 프로젝트 코드/문서 탐색 범위에서는 기본적으로 제외한다.
- `backlog-update`, `merge-doc-reconcile` 는 source-of-truth 문서가 준비된 경우 `state.json` 을 자동 재생성한다. 독립 실행이 필요할 때는 `scripts/generate_workflow_state.py` 를 직접 사용할 수 있다.
- 기본 export 는 AI agent 컨텍스트 절약을 위해 런타임 파일만 포함하고, source docs 와 global snippet 예시는 제외한다.
- 하네스별 패키지는 `dist/harnesses/<target>/<version>/` 아래 개별 생성되며, zip 파일 이름에도 버전이 포함된다.
- 각 패키지 루트에는 `PACKAGE_CONTENTS.md` 와 `APPLY_GUIDE.md` 가 함께 생성돼 다른 환경에서 바로 적용 흐름을 읽을 수 있다.
- 개발 참고용 원본 문서나 전역 snippet 예시가 필요하면 export 시 opt-in 플래그로만 포함한다.

## 9. 구현 현황 요약

- skill 6종은 공통 `tool_version` 과 구조화된 실패 JSON (`status`, `error`, `error_code`, `warnings`, `source_context`) 패턴을 따른다.
- 통합 runner 2종은 하위 step 결과를 중첩 payload 로 유지하면서 `warnings`, `orchestration_plan`, `source_context` 를 상위 메타데이터로 제공한다.
- runner 는 하위 skill/MCP step 이 `status: "error"` 를 반환해도 상위 `workflow_step_failed` 형태로 감싸고, 실패한 step 이름과 upstream `error_code` 를 `source_context` 에 남긴다.
- OpenCode 는 orchestrator + generic/specialized worker overlay 생성까지 지원하고, Codex 는 동일한 task-only orchestrator + bounded worker 운영 패턴을 문서/템플릿으로 배포한다.
- `workflow_kit/common` 은 문서 파싱, 분류, reconcile, runner/error helper, read-only MCP 공통 callable layer, output contract validator 까지 축적돼 있어 개별 스크립트의 중복 로직이 줄어드는 방향으로 정리 중이다.
- 하네스 export bundle 은 read-only MCP descriptor 초안, 하네스별 MCP 설정 예시 draft, JSON-RPC fixture 를 함께 포함해 이후 MCP/server 연결 지점을 전달한다.
- `tests/check_*.py` 는 문서, bootstrap, harness export, output sample, generated schema, validation/code-index, onboarding runner, read-only MCP bundle 까지 smoke 기준선을 제공한다.

## 10. 2026-04-23 개발 종합 정리

이번 세션까지 기준으로 현재 저장소는 “workflow/skill 기반 온보딩 패키지 + 차기 MCP 승격 준비” 상태까지 올라왔다.

- read-only JSON-RPC bridge 는 malformed input, invalid request, initialize capability shape, notification lifecycle, stdio session initialize gating 까지 고정했다.
- official MCP Python SDK candidate 와 실제 stdio round-trip smoke 를 추가해 다음 릴리즈 MCP 승격 준비선을 만들었다.
- Python 3.11 + `mcp[cli]` 개발 환경 재현성과 CI smoke 설치 경로를 저장소 기준선으로 반영했다.
- 이번 릴리즈 방향을 workflow/skill 온보딩 중심으로 재정렬하고, 파일럿 적용 체크리스트와 기록 템플릿을 맞췄다.
- 하네스 export 는 `agent_runtime_minimal` 프로필과 버저닝을 도입해, 하네스별 minimal runtime 패키지와 zip 산출물을 실제로 생성할 수 있게 했다.
- 배포 패키지 루트에는 `PACKAGE_CONTENTS.md`, `APPLY_GUIDE.md`, `manifest.json` 이 함께 생성돼 다른 환경에서 바로 읽고 적용할 수 있다.

이번 릴리스 핵심 결과물:

- Codex package: GitHub release asset `standard-ai-workflow-codex-v0.3.2-beta.zip`
- OpenCode package: GitHub release asset `standard-ai-workflow-opencode-v0.3.2-beta.zip`
- release note: [releases/Beta-v0.3.2.md](./releases/Beta-v0.3.2.md)

## 11. 현재 한계

- 이 저장소는 문서 패키지 성격이 강하지만, 동시에 skill/MCP/runner 프로토타입과 공통 Python package 를 함께 포함하는 작업 저장소다.
- 프로젝트별 문서 경로와 명령 체계는 `project_workflow_profile_template.md` 를 채운 뒤에야 완성된다.
- 여러 프로젝트에서 시범 적용하기 전에는 공통 규칙이 과도한지 여부를 추가 검증해야 한다.
- `workflow_kit/common` 추출은 진행 중이지만, 아직 모든 skill/MCP 를 완전히 공통 라이브러리화한 상태는 아니다.
- 다중 실제 저장소 적용 기록과 CI 실패 원인 분류 고도화는 아직 저장소 내부에 충분히 포함되지 않았다.
- 공식 MCP SDK server candidate 는 준비됐지만, 기본 배포/하네스 적용 경로는 이번 릴리즈에서 의도적으로 제외했다.

## 12. 수동 대체 원칙

skill/MCP 구현이 아직 없더라도 아래 문서만으로 수동 운영은 가능해야 한다.

- 세션 시작: `core/global_workflow_standard.md`
- 프로젝트 특화 규칙: `templates/project_workflow_profile_template.md`
- 상태 문서 템플릿: `templates/`

## 다음에 읽을 문서

- 공통 코어 표준: [core/global_workflow_standard.md](./core/global_workflow_standard.md)
- 프로젝트 상태 진단: [core/project_status_assessment.md](./core/project_status_assessment.md)
- 상위 로드맵: [core/workflow_kit_roadmap.md](./core/workflow_kit_roadmap.md)
- release note: [releases/Beta-v0.3.2.md](./releases/Beta-v0.3.2.md)
- 출력 스키마 가이드: [core/output_schema_guide.md](./core/output_schema_guide.md)
- 도입 분기 가이드: [core/workflow_adoption_entrypoints.md](./core/workflow_adoption_entrypoints.md)
- 하네스 배포 가이드: [core/workflow_harness_distribution.md](./core/workflow_harness_distribution.md)
- 릴리스 규격: [core/workflow_release_spec.md](./core/workflow_release_spec.md)
- 승격 범위 가이드: [core/prototype_promotion_scope.md](./core/prototype_promotion_scope.md)
- read-only MCP transport 승격 기준: [core/read_only_mcp_transport_promotion.md](./core/read_only_mcp_transport_promotion.md)
- workflow kit 패키지: [workflow_kit/README.md](./workflow_kit/README.md)
- 설정 계층 가이드: [core/workflow_configuration_layers.md](./core/workflow_configuration_layers.md)
- 비침투적 주입 정책: [core/workflow_global_injection_policy.md](./core/workflow_global_injection_policy.md)
- 전역 snippet 허브: [global-snippets/README.md](./global-snippets/README.md)
- 샘플 도입 예시: [examples/README.md](./examples/README.md)
- 하네스 허브: [harnesses/README.md](./harnesses/README.md)
- end-to-end 데모: [examples/end_to_end_skill_demo.md](./examples/end_to_end_skill_demo.md)
  여기에는 메인 오케스트레이터와 `doc/code/validation` worker 분배 예시도 포함된다.
- end-to-end MCP 데모: [examples/end_to_end_mcp_demo.md](./examples/end_to_end_mcp_demo.md)
- 출력 샘플: [examples/output_samples/README.md](./examples/output_samples/README.md)
- 스크립트 허브: [scripts/README.md](./scripts/README.md)
- 프로젝트 프로파일 템플릿: [templates/project_workflow_profile_template.md](./templates/project_workflow_profile_template.md)
- agent 토폴로지: [core/workflow_agent_topology.md](./core/workflow_agent_topology.md)
- 분리 체크리스트: [split_checklist.md](./split_checklist.md)
