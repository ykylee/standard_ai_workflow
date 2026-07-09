# Standard AI Workflow

- 문서 목적: 여러 프로젝트에서 공통으로 사용할 수 있는 표준 AI 협업 워크플로우 문서와 템플릿, 향후 skill/MCP/agent 구현 기준을 독립 프로젝트 형태로 제공한다.
- 범위: 공통 표준 문서, 프로젝트 프로파일 템플릿, 세션 상태 문서 템플릿, skill/MCP/agent 설계 참고 문서
- 대상 독자: 개발자, 운영자, AI agent 설계자, 프로젝트 온보딩 담당자
- 상태: stable
- 최종 수정일: 2026-07-09
- 버전: v0.13.2-beta (chapter 1+2+3+4 done, v0.9.1 chapter 5 done, v0.9.2 chapter 6 done, v0.9.3 chapter 7 done, v0.9.4 chapter 8 done, v0.9.5 chapter 9 done, v0.9.6 chapter 10 done, v0.10.0 chapter 11 done, v0.10.1 chapter 12 done, v0.10.2 chapter 13 done, v0.10.3 chapter 14 done; **Phase 13 in_progress (Operational Intelligence v1.0)** — v0.13.0 Quality Dashboard, v0.13.1 memory_index telemetry sidecar (AC2 close), **v0.13.2 self-recovering drift prevention (AC3 close)** — drift 검출 시 자동 fix (5 case) + manual_required 1 case 분리 + release note 본문에 self-recovery log 자동 emit; package: standard-ai-workflow 0.13.2, runtime __version__ = v0.13.2-beta, latest tag **v0.13.2-beta**, head = self-recover wiring commit)
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
| skill 프로토타입 | 사용 가능 | 12종 (1차 6종 + 2차 2종 + 3차 3종 + task-modes). **stable 9종 / beta 2종 / alpha 1종** (v0.11.19~v0.11.21 3 batch stable 승격 완료). 자세한 단계: `workflow-source/core/maturity_matrix.json` SSOT |
| skill 카탈로그 | 설계 완료, stable 단계 진입 | 11개 core skill + task-modes. v0.11.21 기준 9 stable + 2 beta (automated-repro-scaffold, git-conflict-resolver) |
| MCP 프로토타입 | 사용 가능 | 12종 (stable 8 + beta 4). jsonrpc-bridge (안정) + stdio-sdk (실험적) 양쪽 지원 |
| MCP 카탈로그 | 설계 완료, stable 단계 진입 | 우선순위 1 MCP 정식 stable + read_only_mcp_sdk v1.0 SDK candidate + 베타 4종 |
| 통합 데모 runner | 사용 가능 | `workflow-source/scripts/run_demo_workflow.py`, `workflow-source/scripts/run_existing_project_onboarding.py` 참고 |
| bootstrap scaffold | 사용 가능 | `python3 -m bootstrap_lib` (v0.5.2+ 권장) + 레거시 `bootstrap_workflow_kit.py` shim |
| harness overlays | 사용 가능 | 10개 하네스 대상: `Codex`, `OpenCode`, `Gemini CLI`, `Antigravity`, `MiniMax Code`, `CodeWhale` (v0.10.4 신규), `Claude Code`, `Aider`, `Goose`, `pi-dev` |
| harness interactive picker | 사용 가능 (v0.5.8+) | `--harness` 미지정 시 TTY 자동 picker, 비대화형 모드 검증 |
| orchestrator/worker overlays | 사용 가능 | OpenCode orchestrator + doc/code/validation worker 분화 및 위임 패턴 |
| contract v1 (orchestrator ↔ sub-agent) | 사용 가능 (v0.5.4+) | `workflow-source/core/orchestrator_subagent_contract_v1.md` 외부 spec + `workflow_kit/contract_v1/` enforcement helpers (output_validator, delegator.choose_roles). wire 가이드: `orchestrator_contract_v1_wire_guide.md` |
| 다중 컴포넌트 fan-out/in (v0.5.7) | 사용 가능 | `choose_roles` (multi-sub 위임) + `validate_fanin_output` (cross-ref 통합) |
| 다중 에이전트 오케스트레이션 | 사용 가능 | `orchestration_demo.py` 및 피드백 루프 시뮬레이션 |
| 워크플로우 린터 (Skill) | 사용 가능 | `run_workflow_linter.py`를 통한 문서 정합성 자동 검사 및 복구 (v0.11.20 stable) |
| 실전 스킬 (Git) | 사용 가능 (alpha) | `run_git_conflict_resolver.py`를 통한 컨텍스트 기반 충돌 해결 |
| Memora-inspired Memory Index | 사용 가능 (v0.11.22 Phase 1~3d 완료) | `workflow_kit.common.state.memory_index` helper + `ai-workflow/memory/active/memory_index/` 메타 레이어 + 3 skill opt-in wiring (session-start / doc-sync / backlog-update) + BM25 stdlib fallback. ADR-005/006 참조 |
| harness package export | 사용 가능 | `workflow-source/scripts/export_harness_package.py` 로 dist 산출물 생성. packaging smoke 자동화 (`tools/check_packaging.py`) |
| 출력 스키마 가이드 | 사용 가능 | `workflow-source/core/output_schema_guide.md` (Pydantic v2 기반) |
| 출력 샘플 JSON | 사용 가능 | skill/MCP/runner 성공/실패 샘플 (24 file, `examples/output_samples/`) |
| workflow kit package | 사용 가능 (FULL mypy strict, v0.11.18+) | `workflow_kit` + `bootstrap_lib` + `contract_v1` + `common.{state,contracts,schemas,server,memory_index,...}` (109 file mypy strict clean, 0 errors) |
| release pipeline 자동화 | 사용 가능 (v0.7.9+) | `tools/release_pipeline.py` 8 subcommand (validate / version-bump / note-draft / changelog-gen / release / gen-schema / verify / rollback / dist) + `--apply` flag |
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
- CodeWhale: `.codewhale/skills/codewhale-workflow/SKILL.md` 중심 (Constitution 보강, 단일 skill 파일)
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
- `workflow-source/tests/check_*.py` 162개는 문서, bootstrap, harness export, output sample, generated schema, validation/code-index, onboarding runner, read-only MCP bundle, contract v1 multi-component, wire guide 회귀, release_pipeline (30+ wrapper) 까지 smoke 기준선을 제공한다 (cumulative, v0.8.15+ 162/162 PASS).
- CI 는 `python 3.11` + `PYTHONPATH=workflow-source` + `pip install -r requirements*.txt` 경로로 매 push 마다 162개 smoke 전부 실행.

## 10. v0.8.0 → v0.9.0 누적 변경 요약 (2026-06-18)

v0.8.0 spec §5.3 (Stable API frozen + mypy strict 단계적 격상) 부터 v0.9.0 chapter 1 까지 누적된 핵심 변경 (16 + 1 release):

- **v0.8.0** — Stable API frozen + `mypy --strict` base 격상 + `pyproject.toml [project] version` SSOT + `__version__` 자동 derive + generated JSON Schema SSOT (21 family, 85,743 bytes) + `__all__` 27 entry 명시. spec §9 acceptance 7/12.
- **v0.8.1** — mypy strict 단계적 격상 1단계: `workflow_kit/url_validity.py` 25 error → 0 (Severity='info' 확장, EvictionStrategy 신규, CacheEntry.timestamp real bug fix, subprocess_run: Any 명시, max_diff_lines parameter 추가).
- **v0.8.2** — mypy strict 단계적 격상 2단계: `workflow_kit/okf_import.py` 9 error → 0 (opening docstring real bug fix, → U+2192 제거, cast(Mode) 명시, lambda→def, e→err loop var rename).
- **v0.8.3** — mypy strict 단계적 격상 3단계: `workflow_kit/okf_export.py` 2 error → 0.
- **v0.8.4** — mypy strict 단계적 격상 4단계: `phishing_federation.py` + `phishing_federation_v4.py` 8 error → 0 (_UrlRecord TypedDict 신규).
- **v0.8.5** — mypy strict 단계적 격상 5단계: `phishing_keywords.py` + `cache_lfu_decay.py` + `cache_lfu_decay_persist.py` 11 error → 0 (LFUConfig 명시 import, Callable[..., Any] | None).
- **v0.8.6** — mypy strict 단계적 격상 6단계: `workflow_kit_cli.py` 44 error → 0 (가장 큰 module, register decorator Callable 명시).
- **v0.8.7** — mypy strict 단계적 격상 7단계: `v_r13_commit_diff.py` + `cache_analytics.py` + `cache_analytics_trend_chart.py` 13 error → 0.
- **v0.8.8** — mypy strict 단계적 격상 8단계: `upgrade_diff.py` + `bitbucket_v2.py` + `lfu_integration.py` + `cache_size_compare.py` 8 error → 0 + `tools/release_pipeline.py` SSOT refactor.
- **v0.8.9** — dispatcher surface 28 → 30: `cache-lru-decay` + `cache-merge-csv` (v0.7.58 의 3 subcommand 잔여분 2개).
- **v0.8.10** — read-only MCP manifest byte-identical assertion (spec §9 #6) + spec §9 8/12.
- **v0.8.11** — phishing_keywords 2 pre-existing test fail fix (lowercase + dedup + mock-based openphish).
- **v0.8.12** — `.github/workflows/consumer-metrics-digest.yml` GH Actions weekly cron 자동화 (consumer-metrics --digest-markdown → GH issue comment).
- **v0.8.13** — mypy strict 단계적 격상 9단계: `common/state/builder.py` 13 error → 0 (cumulative fix 잔여분 흡수).
- **v0.8.14** — mypy strict 단계적 격상 10단계: `common/contracts/baselines.py` 27 error → 0 + 2 real bug fix (AuditLogEvent → StageCompletion, append_audit_log arg 순서).
- **v0.8.15** — `release-dist --apply` 1-command (`python -m build` + `twine check` + TestPyPI sim) + `--production` flag + `.gitignore` history file 등록 + work_backlog.md v0.7.25~v0.7.32 stale 정리. spec §9 9/12, tools test 52/52 PASS.
- **v0.9.0 (chapter 1+2+3+4 DONE, released 2026-06-18)** — Deprecation Policy Operational Spec 신규 (221 lines, 9 sections) + SSOT 정합 (`pyproject.toml [project] version` 0.8.1 → 0.9.1, runtime `__version__` = v0.9.1-beta) + mypy config 정합 (`[tool.mypy]` unknown option 5개 → `[tool.workflow-doctor]` section 분리, v0.8.0~v0.8.15 의 strict validation bypass 버그 fix). **chapter 2 = deprecation 1st cycle 실제 적용**: `phishing_federation_v4.fetch_federated_phishing_urls_v4` DeprecationWarning 추가 (`stacklevel=2`, deprecated + replacement + v0.10.0 removal 3-element message) + 6 신규 test (`check_v0_9_0_deprecation_1st_cycle.py`) + 4 acceptance verify (DeprecationWarning 1회 raise / output identical to consolidated / `__all__` 그대로 존재 / zero behavior change). **chapter 3 = spec drift patch + release note + Phase 11 close / Phase 12 kickoff**: spec §4.2/§4.3/§7.1 의 `v0.9.0-beta` → `v0.9.1-beta` 정직하게 인정 (chapter 1 의 `version-bump --minor` 의 patch bump interaction 결과), `Beta-v0.9.0.md` release note 신규 (chapter 1+2+3 묶음), `workflow_kit_roadmap.md` Phase 11 close + Phase 12 kickoff 갱신. **chapter 4 = release pipeline 실행 + 3-way 정합**: git tag `v0.9.0-beta` push + gh release create + assets 2 (whl + tar.gz) + 3-way 정합 verify (`git ls-remote --tags` + `cmd_release verify` + `gh release view`). 2 in-scope fix 동반: (1) cmd_release argparse `--dry-run` flag 누락 → AttributeError (v0.7.10 부터 14 release 동안 모든 호출 fail, v0.7.58-beta 가 latest tag 인 이유) fix, (2) cmd_release local tag create step 누락 → `src refspec does not match any` fail fix. release URL: https://github.com/ykylee/standard_ai_workflow/releases/tag/v0.9.0-beta. mypy strict **18 file baseline** 유지 (chapter 2 검증 중 side 발견: mypy 2.1.0 stricter checking 으로 `workflow_kit_cli.py` 49 error 노출 — v0.8.6 release note 의 "44 error → 0" 은 mypy 1.x 기준, spec §6 현실 조정과 정합 — 별도 후속). spec ↔ runtime drift: chapter 3 에서 spec patch 완료, *drift 재발 방지* 가 spec §4.2 verify 단계의 *운영 약속*.
- **v0.9.3 (chapter 7 DONE, released 2026-06-19)** — Phase 12 의 *deprecation 운영 안정화* 두 번째 release. **2nd cycle 적용** — `phishing_federation_v4.build_default_sources_v4` (1st cycle 의 *같은 module* 의 *다른 public function*). 1st cycle 운영 검증 결과: dispatcher (`cmd_federate`) 가 이미 `phishing_federation.build_default_sources` (consolidated) 사용 중 (line 255-257) → v4 module 자체가 *dead code 신호* → 2nd cycle first move 정공법. `DEPRECATION_MARKED_CALLABLES` whitelist +1 entry (총 2) + contract test 의 `dict[str, tuple[str, tuple, dict]]` format 확장 (1st/2nd cycle signature 차이 흡수) + `v0_9_0_deprecation_policy_spec.md` §3.5 + §3.6 추가. 4 acceptance test (`check_v0_9_3_deprecation_2nd_cycle.py`) + 1st cycle regression 6/6 + contract test 4/4 = **14/14 PASS**. 누적 smoke **162/162 + 22 별도 subset** (v0.9.0 6 + v0.9.1 4 + v0.9.2 8 + v0.9.3 4). 1st+2nd cycle 동시 종료 시점 = **v0.10.0** (spec §3.5 2nd cycle table 의 removal column). release URL: <https://github.com/ykylee/standard_ai_workflow/releases/tag/v0.9.3-beta>.

- **v0.9.4 (chapter 8 DONE, released 2026-06-23)** — Phase 12 의 *R-A follow-up* 첫 번째 release. v0.9.2 chapter 6 의 follow-up R-A (Purpose Refresh) = "state.json `purpose_digest` + session-start context load + wiki-event-sync release event hook" 을 **3 release 분할** (cycle 8 = part 1, cycle 9 = part 2, cycle 10 = part 3). **본 release (v0.9.4) 는 part 1** — `state.json.purpose_digest` 1-line 자동 생성. 신규 `workflow_kit.common.state.builder._parse_purpose_summary` helper (PURPOSE.md frontmatter `last_purpose_review` + §1 Goals 첫 번째 goal parse, 부재 시 graceful skip `(None, None)`) + `build_workflow_state_payload` output schema top-level 2 field 추가 (`purpose_digest`, `purpose_digest_rev`) + 3 candidate path resolution (`ai-workflow/memory/active/PURPOSE.md` primary / `../<workspace_parent>/ai-workflow/memory/active/PURPOSE.md` parent / `workspace_root/PURPOSE.md` fallback). spec `llm_wiki_concept_purpose_spec.md` §4.3 part 1 + §10 (R-A follow-up cycle table 신규) 추가 + §5 follow-up checklist 갱신. 3 acceptance test (`check_purpose_concept_state_json_v0_9_4.py`) + v0.9.2 regression 8/8 + deprecation cycle 14/14 = **25/25 PASS**. 누적 smoke **162/162 + 25 별도 subset** (v0.9.0 6 + v0.9.1 4 + v0.9.2 8 + v0.9.3 4 + v0.9.4 3). 1 in-scope fix 동반: `workflow_kit/__init__.py` loud fallback literal `"v0.9.4-beta-beta"` → `"v0.9.4-beta"` (suffix 중복, v0.9.3 commit 시점 spec drift 정정). spec §9 acceptance 10/12 → **11/12** (R-A follow-up part 1 ✅, part 2/3 후속 = v0.9.5/v0.9.6). release URL: <https://github.com/ykylee/standard_ai_workflow/releases/tag/v0.9.4-beta>.

- **v0.9.5 (chapter 9 DONE, released 2026-06-23)** — Phase 12 의 *R-A follow-up* 두 번째 release. **본 release 는 part 2** — skill context load integration. v0.9.4 의 `state.json.purpose_digest` 1-line 자동 생성 후속으로, session-start / backlog-update / doc-sync 3종 skill 의 *context load* 시 `state.json.purpose_digest` + PURPOSE.md 본문 (≤200 token) 자동 read + backlog-update 의 *in-scope check* 시 PURPOSE.md §3 Research Scope *제외 영역* 매칭 → scope creep 경고. 신규 `workflow_kit.common.purpose_context.build_purpose_context` helper (5 함수: `find_purpose_path` / `_read_state_digest_and_rev` / `read_purpose_body_excerpt` ≤800 char / `extract_research_scope` §3 포함·제외 / `check_scope_creep` hard warning) + 3 output schema 확장 (`SessionStartOutput.purpose_context` / `BacklogUpdateOutput.purpose_context` + `scope_creep_warnings` / `DocSyncOutput.purpose_context`, 각각 nested `*PurposeContext` Pydantic model) + 3 skill script 통합. spec `llm_wiki_concept_purpose_spec.md` §4.3 part 2 + §5 follow-up ✅ + §6 cross-ref + §10 cycle table detail + 3 skill spec §12/§13 신규 + `workflow_skill_catalog.md` §5.3 신규. 6 acceptance test (`check_purpose_concept_skill_context_v0_9_5.py`, 5 spec + 1 end-to-end subprocess) + v0.9.4 regression 3/3 + v0.9.2 regression 8/8 + deprecation cycle 14/14 = **31/31 PASS**. 누적 smoke **162/162 + 31 별도 subset** (v0.9.0 6 + v0.9.1 4 + v0.9.2 8 + v0.9.3 4 + v0.9.4 3 + v0.9.5 6). Graceful skip 정책: 3종 skill 모두 PURPOSE.md / state.json 부재 시 partial fill + `scope_warnings` advisory 1줄 (skill 실행 실패 ❌). spec §9 acceptance 11/12 → **12/12** (R-A follow-up part 1 + part 2 ✅, part 3 후속 = v0.9.6). release URL: <https://github.com/ykylee/standard_ai_workflow/releases/tag/v0.9.5-beta>.

- **v0.9.6 (chapter 10 DONE, released 2026-06-24)** — Phase 12 의 *R-A follow-up* 세 번째 (마지막) release. **본 release 는 part 3** — wiki-event-sync R-A trigger. v0.9.5 의 skill context load integration 후속으로, R-A (Purpose Refresh) 의 *trigger layer* 가 runtime 으로 추가: 30일 안 wiki log 의 ingest/query/release 분포 분석 + LLM suggest prompt (advisory, auto-commit ❌) + `last_purpose_review` date 갱신. 신규 `workflow_kit.common.purpose_refresh` helper (5 함수: `parse_log_events` / `analyze_30day_distribution` (ingest-like / query-like / release 분류 + top 10 topics + recent releases) / `_read_last_purpose_review` / `update_last_purpose_review` (`re.MULTILINE` regex + 이전/현재 추적) / `generate_llm_suggest_prompt` (markdown §1 분포 + §2 본문 ≤800 char + §3 4-element advisory) + `run_purpose_refresh` unified entry) + CLI dispatcher subcommand 31 `refresh-purpose` 등록 (destructive subcommand 정공법 memory #5 정합: `apply=False` default dry-run + `--apply` 명시 시 frontmatter 갱신 + `--window-days` / `--wiki-log-path` / `--purpose-path` / `--json` flag). spec `llm_wiki_concept_purpose_spec.md` §4.4 7 detail 확장 + §5 follow-up ✅ + §6 cross-ref + §10 cycle table detail + `workflow_skill_catalog.md` §5.4 신규 + `workflow_kit_cli.py` docstring header + subcommand 표. 6 acceptance test (`check_purpose_concept_ra_trigger_v0_9_6.py`, 30일 분포 / LLM prompt / frontmatter 갱신 / dry-run / apply / graceful skip 모두 PASS) + v0.9.4 regression 3/3 + v0.9.2 regression 8/8 + v0.9.5 환경의존 3 제외 = **37/37 PASS**. 누적 smoke **162/162 + 37 별도 subset** (v0.9.0 6 + v0.9.1 4 + v0.9.2 8 + v0.9.3 4 + v0.9.4 3 + v0.9.5 6 + v0.9.6 6). Graceful skip 정책: log.md / PURPOSE.md 부재 시 advisory warning 1줄 + no-op. LLM suggest 의 output 은 *advisory* 일 뿐, 자동 commit ❌ — 사람 review 후 `--apply` 로 명시적 갱신. spec §9 acceptance **12/12 유지** (R-A follow-up part 1 ✅ v0.9.4 + part 2 ✅ v0.9.5 + part 3 ✅ v0.9.6 = 3 release 분할 완료). R-A follow-up 3 release 분할 cycle 종료. release URL: <https://github.com/ykylee/standard_ai_workflow/releases/tag/v0.9.6-beta>.

- **v0.9.2 (chapter 6 DONE, released 2026-06-19)** — Phase 12 의 *외부 reference concept 흡수* 첫 release. Karpathy `llm-wiki.md` 패턴 + llm_wiki (nashsu) 의 *Purpose.md — The Wiki's Soul* 4-element concept 을 우리 workflow state docs layer 에 정형화. **bundle 비율 ~75%** (4-element 100% / LLM context read 80% follow-up R-A / suggest-update trigger 60% follow-up R-A / schema·purpose 분리 100%). 신규 `ai-workflow/memory/active/PURPOSE.md` (Goals G1~G4 / Key Questions Q1~Q4 / Research Scope 포함·제외 / Evolving Thesis working hypothesis 6개) + `PROJECT_PROFILE.md` §0 Purpose 참조 + 신규 spec `workflow-source/core/llm_wiki_concept_purpose_spec.md` (1차 출처 명시 + LICENSE 안전선: Karpathy gist + llm_wiki README GPLv3 영향 회피, **코드 직접 차용 ❌**) + 8 acceptance test (4-element + LLM-readable + structural verify 모두 PASS, 8/8). follow-up R-A (Purpose Refresh) 별도 cycle 8 (state.json `purpose_digest` + session-start context load + wiki-event-sync release event hook). release URL: <https://github.com/ykylee/standard_ai_workflow/releases/tag/v0.9.2-beta>.

- **v0.9.1 (chapter 5 DONE, released 2026-06-18)** — Phase 12 (운영 지능화 + deprecation 운영 안정화) 의 첫 release. **3 deliverables**: (1) **mypy strict workflow_kit_cli.py 격상** 49 → 0 error (register decorator outer return type Callable 명시 cascade fix + 6개 cast), cumulative **18 → 19 file clean** (workflow_kit_cli 신규 추가, full strict 도달 v1.0.0 milestone 의 진척). (2) **release pipeline automation** — `cmd_release --full-auto` flag 신규, pre-check conflict 시 자동 --auto-bump + 새 tag 로 1-cycle close. 2 in-scope fix 동반: cmd_rollback dispatch 누락 fix (v0.7.10 부터 14 release 동안 모든 rollback 호출 fail 했던 진짜 bug), test_release_dry_run_no_dist 의 error message acceptance 확장 (pyproject bump 으로 누적된 test fail fix). (3) **deprecation policy contract test** (`check_v0_9_1_deprecation_contract.py`, 4 신규 test) — `workflow_kit.__all__` 의 모든 public symbol 이 deprecation-free 또는 deprecation-marked contract verify, DEPRECATION_MARKED_CALLABLES whitelist + 자동 importlib + warnings.catch_warnings 의 meta-test. release URL: https://github.com/ykylee/standard_ai_workflow/releases/tag/v0.9.1-beta. Phase 12 완료 기준 3/6 (mypy / automation / contract test) 충족. spec §9 acceptance 9/12 *유지* (deprecation 2nd cycle / pipeline `--apply default=False` / consumer signal 2nd wave 후속).

**누적 (v0.8.0 → v0.10.3)**: 16 + 11 release (v0.9.0 chapter 1+2+3+4 + v0.9.1 chapter 5 + v0.9.2 chapter 6 + v0.9.3 chapter 7 + v0.9.4 chapter 8 + v0.9.5 chapter 9 + v0.9.6 chapter 10 + v0.10.0 chapter 11 + v0.10.1 chapter 12 + v0.10.2 chapter 13 + v0.10.3 chapter 14), mypy strict cumulative **19 file clean** (mypy 2.1.0 stricter checking, full strict 도달 v1.0.0 milestone), smoke test **162/162 PASS** (cumulative, v0.8.15+ 유지, 신규 63 test 별도 subset: v0.9.0 6 + v0.9.1 4 + v0.9.2 8 + v0.9.3 4 + v0.9.4 3 + v0.9.5 6 + v0.9.6 6 + v0.10.0 6 + v0.10.1 6 + v0.10.2 9 + v0.10.3 7), spec §9 acceptance **12/12**, **SemVer major** (v0.10.0) + 4 × **SemVer minor** (v0.10.1/0.10.2/0.10.3 + 1 follow-up 예정). Phase 11 close + Phase 12 kickoff + 4/6 → **6/6 완료** + delivery layer 확장 v0.10.1/0.10.2 + wiki 운영 R-A cycle 2 v0.10.3.

**PyPI 배포 정책**: GitHub Releases only, no actual PyPI/TestPyPI deployment. v0.8.15 의 TestPyPI/Production upload 는 *simulation* 만.

이번 기준선 핵심 결과물:

- release note: [releases/Beta-v0.10.3.md](./workflow-source/releases/Beta-v0.10.3.md) (v0.10.3 chapter 14 — **SemVer minor**, wiki 운영 R-A follow-up cycle 2, file deletion cascade cleanup, `workflow_kit.common.wiki_cascade` helper (5 함수 + 2 dataclass) + `cmd_cascade_delete` CLI subcommand 32 + 3-method matching (basename / stem / project-relative) + macOS case-insensitive `Path.samefile()` dedup + destructive subcommand 정공법 (apply=False default dry-run), `check_wiki_cascade_cleanup_v0_10_3.py` 7 acceptance test, breaking change ❌, tag `v0.10.3-beta` released 2026-06-24)
- release note: [releases/Beta-v0.10.2.md](./workflow-source/releases/Beta-v0.10.2.md) (v0.10.2 chapter 13 — **SemVer minor**, delivery layer 확장 후속, claude-code 진입점 정정 (entry_files=('CLAUDE.md',)) + aider / goose / custom 3 신규 adapter (10 harness) + session-start self-bootstrap mode (SessionStartOutput 에 2 field + status="warning" + init commands) + 4 apply_guide 갱신/신규, `check_v0_10_2_delivery_layer_extension.py` 9 acceptance test, `check_v0_10_1_skill_only_entry_mode.py` 갱신, breaking change ❌, tag `v0.10.2-beta` released 2026-06-24)
- release note: [releases/Beta-v0.10.1.md](./workflow-source/releases/Beta-v0.10.1.md) (v0.10.1 chapter 12 — **SemVer minor**, delivery layer 확장, `--entry-mode skill-only` option (3-mode: aggressive / safe / skill-only) + `--harness claude-code` adapter (1차 PoC, slash command 진입점) + `harnesses/claude-code/apply_guide.md` 신규 + HARNESS_SPECS / HARNESS_FILE_BUILDERS / SUPPORTED_HARNESSES 6→7, `check_v0_10_1_skill_only_entry_mode.py` 6 acceptance test, default = aggressive (v0.10.0 호환, breaking change ❌), tag `v0.10.1-beta` released 2026-06-24)
- release note: [releases/Beta-v0.10.0.md](./workflow-source/releases/Beta-v0.10.0.md) (v0.10.0 chapter 11 — **SemVer major**, deprecation 1st + 2nd cycle 동시 종료, `phishing_federation_v4.py` file delete + `__all__` 에서 제거 + `DEPRECATION_MARKED_CALLABLES` whitelist empty + 2 deprecation test file delete (cycle 1 + 2), consumer 명시적 except mandatory, `check_v0_10_0_deprecation_removal.py` 6 acceptance test + `check_v0_9_1_deprecation_contract.py` 4 test 갱신, tag `v0.10.0-beta` released 2026-06-24)
- release note: [releases/Beta-v0.9.6.md](./workflow-source/releases/Beta-v0.9.6.md) (v0.9.6 chapter 10 — R-A follow-up part 3, wiki-event-sync R-A trigger, `purpose_refresh.run_purpose_refresh` helper (5 함수) + CLI dispatcher subcommand 31 `refresh-purpose` + 30일 분포 + LLM suggest (advisory) + `last_purpose_review` 갱신, destructive subcommand 정공법 + graceful skip 정책, tag `v0.9.6-beta` released 2026-06-24)
- release note: [releases/Beta-v0.9.5.md](./workflow-source/releases/Beta-v0.9.5.md) (v0.9.5 chapter 9 — R-A follow-up part 2, skill context load integration, `purpose_context.build_purpose_context` helper (5 함수) + 3 output schema 확장 + 3 skill script 통합, scope creep check (제외 영역 hard warning), graceful skip 정책, tag `v0.9.5-beta` released 2026-06-23)
- release note: [releases/Beta-v0.9.4.md](./workflow-source/releases/Beta-v0.9.4.md) (v0.9.4 chapter 8 — R-A follow-up part 1, `state.json.purpose_digest` 1-line 자동 생성, `_parse_purpose_summary` helper + output schema 2 field 확장, R-A 3 release 분할 정공법 (part 1/2/3 = v0.9.4/0.9.5/0.9.6), tag `v0.9.4-beta` released 2026-06-23)
- release note: [releases/Beta-v0.9.3.md](./workflow-source/releases/Beta-v0.9.3.md) (v0.9.3 chapter 7 — deprecation 2nd cycle `build_default_sources_v4` 적용, 1st cycle 의 *같은 module* 의 *다른 public function*, DEPRECATION_MARKED_CALLABLES whitelist +1 (총 2), contract test format 확장 (tuple), tag `v0.9.3-beta` released 2026-06-19)
- release note: [releases/Beta-v0.9.2.md](./workflow-source/releases/Beta-v0.9.2.md) (v0.9.2 chapter 6 — purpose.md concept 흡수, 외부 reference 차용 정공법 1차 적용, llm_wiki Karpathy 패턴 + 4-element (Goals / Key Questions / Research Scope / Evolving Thesis), bundle 비율 ~75%, 1차 출처 GPLv3 영향 회피 (코드 직접 차용 ❌), tag `v0.9.2-beta` released 2026-06-19)
- release note: [releases/Beta-v0.9.1.md](./workflow-source/releases/Beta-v0.9.1.md) (v0.9.1 chapter 5 — mypy strict workflow_kit_cli 49→0 + release automation `--full-auto` + deprecation contract test, Phase 12 3/6 완료, tag `v0.9.1-beta` released 2026-06-18)
- release note: [releases/Beta-v0.9.0.md](./workflow-source/releases/Beta-v0.9.0.md) (v0.9.0 chapter 1+2+3+4 묶음 — deprecation 1st cycle 적용 + SSOT 정합 + mypy config 정합 + Phase 11 close + release pipeline 3-way 정합, tag `v0.9.0-beta` released 2026-06-18)
- github release: [https://github.com/ykylee/standard_ai_workflow/releases/tag/v0.10.3-beta](https://github.com/ykylee/standard_ai_workflow/releases/tag/v0.10.3-beta) (latest)
- github release: [https://github.com/ykylee/standard_ai_workflow/releases/tag/v0.10.2-beta](https://github.com/ykylee/standard_ai_workflow/releases/tag/v0.10.2-beta)
- github release: [https://github.com/ykylee/standard_ai_workflow/releases/tag/v0.10.1-beta](https://github.com/ykylee/standard_ai_workflow/releases/tag/v0.10.1-beta)
- github release: [https://github.com/ykylee/standard_ai_workflow/releases/tag/v0.10.0-beta](https://github.com/ykylee/standard_ai_workflow/releases/tag/v0.10.0-beta)
- github release: [https://github.com/ykylee/standard_ai_workflow/releases/tag/v0.9.6-beta](https://github.com/ykylee/standard_ai_workflow/releases/tag/v0.9.6-beta)
- github release: [https://github.com/ykylee/standard_ai_workflow/releases/tag/v0.9.5-beta](https://github.com/ykylee/standard_ai_workflow/releases/tag/v0.9.5-beta)
- github release: [https://github.com/ykylee/standard_ai_workflow/releases/tag/v0.9.4-beta](https://github.com/ykylee/standard_ai_workflow/releases/tag/v0.9.4-beta)
- github release: [https://github.com/ykylee/standard_ai_workflow/releases/tag/v0.9.3-beta](https://github.com/ykylee/standard_ai_workflow/releases/tag/v0.9.3-beta)
- github release: [https://github.com/ykylee/standard_ai_workflow/releases/tag/v0.9.1-beta](https://github.com/ykylee/standard_ai_workflow/releases/tag/v0.9.1-beta)
- github release: [https://github.com/ykylee/standard_ai_workflow/releases/tag/v0.9.0-beta](https://github.com/ykylee/standard_ai_workflow/releases/tag/v0.9.0-beta) (assets: whl + tar.gz, 3-way 정합 verify via `cmd_release verify`)
- release note: [releases/Beta-v0.8.15.md](./workflow-source/releases/Beta-v0.8.15.md) (v0.8.0 → v0.8.15 묶음, spec §9 9/12 완료)
- stable API spec: [core/v0_8_0_stable_api_spec.md](./workflow-source/core/v0_8_0_stable_api_spec.md) (v0.8.0 freeze)
- deprecation policy spec: [core/v0_9_0_deprecation_policy_spec.md](./workflow-source/core/v0_9_0_deprecation_policy_spec.md) (v0.9.0, chapter 3 spec drift patch 반영 — v0.9.0-beta → v0.9.1-beta 정직하게)
- workflow_kit_roadmap: [core/workflow_kit_roadmap.md](./workflow-source/core/workflow_kit_roadmap.md) (Phase 11 close + Phase 12 kickoff, v0.9.0 chapter 3 갱신)
- 전체 릴리스 노트 (Alpha-v0.1.0 ~ Beta-v0.9.0): [releases/](./workflow-source/releases/)

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
- 마지막 release note: [workflow-source/releases/Beta-v0.9.1.md](./workflow-source/releases/Beta-v0.9.1.md)
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
