# Project Workflow Profile

- 문서 목적: 프로젝트 특화 규칙과 실행/검증 기준을 정의한다.
- 범위: 프로젝트 개요, 문서 구조, 기본 명령, 검증 포인트, 예외 규칙
- 대상 독자: 개발자, 운영자, AI agent, 프로젝트 온보딩 담당자
- 상태: stable
- 최종 수정일: 2026-06-09
- 관련 문서: [공통 표준](https://github.com/ykylee/standard_ai_workflow/blob/main/ai-workflow/core/global_workflow_standard.md), [Orchestrator ↔ Sub-agent Contract v1](https://github.com/ykylee/standard_ai_workflow/blob/main/workflow-source/core/orchestrator_subagent_contract_v1.md), [Maturity Matrix](https://github.com/ykylee/standard_ai_workflow/blob/main/workflow-source/core/maturity_matrix.json), [설치·사용 가이드](./INSTALLATION_AND_USAGE.md)

## 1. 프로젝트 개요
- 프로젝트명: Standard AI Workflow
- 프로젝트 슬러그: `standard-ai-workflow`
- 프로젝트 목적: 여러 프로젝트에서 공통으로 사용할 수 있는 표준 AI 협업 워크플로우 문서와 템플릿, skill/MCP/agent 구현 기준을 독립 프로젝트 형태로 제공한다.
- 주요 이해관계자: 저장소 maintainer (`ykylee`), 워크플로우 도입 검토자, 멀티 에이전트 운영자
- 현재 베이스라인: **v0.5.10-beta** (v0.5.6 P0 enforcement + v0.5.7 multi-component + v0.5.8 interactive picker + v0.5.9.x wire 가이드 + v0.5.10 sub.delegation_id parent-prefix spec 정합)

## 2. 문서 구조 (Path)
- 문서 위키 홈: docs/README.md
- 운영 문서 홈: ai-workflow/memory/
- 백로그 위치: ai-workflow/memory/backlog/
- 세션 인계 문서: `ai-workflow/memory/release/v0.5.10/session_handoff.md` (현 브랜치 v0.5.10 인계)
- 환경 기록 위치: ai-workflow/memory/environments/

## 3. 기본 명령 (Commands)

### 3.1 환경 셋업 (최초 1회)
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
```

### 3.2 로컬 실행 (부트스트랩)
```bash
python3 workflow-source/scripts/bootstrap_workflow_kit.py \
  --target-root . \
  --project-slug standard-ai-workflow \
  --project-name "Standard AI Workflow" \
  --harness codex \
  --adoption-mode existing \
  --copy-core-docs \
  --enable-mcp \
  --force
```

### 3.3 회귀 (Smoke)
- 전체 스모크: `for t in workflow-source/tests/check_*.py; do python "$t" || exit 1; done`
- 부트스트랩 회귀: `python workflow-source/tests/check_bootstrap.py`
- MCP round-trip: `python workflow-source/tests/check_bootstrap_mcp_roundtrip.py`
- 문서 링크: `python workflow-source/tests/check_docs.py`
- contract v1 (v0.5.4 신규):
  - `python workflow-source/tests/check_contract_v1_roundtrip.py`
  - `python workflow-source/tests/check_contract_v1_role_mapping.py`
  - `python workflow-source/tests/check_contract_v1_direct_only.py`
- 워크플로우 linter: `PYTHONPATH=workflow-source python workflow-source/skills/workflow-linter/scripts/run_workflow_linter.py --project-profile-path docs/PROJECT_PROFILE.md --state-json-path ai-workflow/memory/release/v0.5.5/state.json --session-handoff-path ai-workflow/memory/release/v0.5.5/session_handoff.md --latest-backlog-path ai-workflow/memory/release/v0.5.5/backlog/2026-06-07.md`

### 3.4 실행 확인 (상태 동기화)
```bash
python3 workflow-source/scripts/generate_workflow_state.py \
  --project-profile-path docs/PROJECT_PROFILE.md \
  --session-handoff-path ai-workflow/memory/session_handoff.md \
  --work-backlog-index-path ai-workflow/memory/work_backlog.md \
  --output-path ai-workflow/memory/state.json
```

## 4. 검증 포인트 (Validation)
- 코드 변경: 모든 `workflow-source/tests/check_*.py` 스모크 테스트 통과 및 출력 스키마 계약(`schemas/generated_output_schemas.json`) 준수 여부 확인.
- 문서 변경: 필수 메타데이터 존재 여부 및 Markdown 상대 링크 무결성 확인 (`python workflow-source/tests/check_docs.py`).
- UI 변경: 현재 프로젝트는 CLI/문서 위주이나, 하네스 오버레이 생성 시 각 하네스(Codex, Antigravity 등)에서의 렌더링 확인.
- 배포/운영: `workflow-source/scripts/export_harness_package.py`를 통한 패키지 생성 확인 및 `workflow-source/releases/` 가이드라인 준수.
- contract v1 (v0.5.4 부터): orchestrator ↔ sub-agent 위임 시 §4 입력 / §5 출력 스키마 준수 여부. 3개 회귀 (`check_contract_v1_*`) 로 검증.
- contract v1 enforcement (v0.5.6 신규): sub-agent 출력은 `workflow_kit.contract_v1.output_validator.validate_output()`, Mavis 측 위임 결정은 `workflow_kit.contract_v1.delegator.choose_role()` 로 자동 enforce. 5개 회귀 (`check_contract_v1_*`) 로 검증.

## 5. 예외 규칙 (Policy)
- 병합: `ai-workflow/memory/state.json` 등 자동 생성 파일은 충돌 시 소스 문서(backlog, handoff)를 기준으로 재생성한다.
- 승인: 코어 문서(`workflow-source/core/`) 변경 시 아키텍처 리뷰 필수 (특히 `global_workflow_standard.md`, `maturity_matrix.json`, `orchestrator_subagent_contract_v1.md`).
- 제약: Python 3.10+ 환경 필수 (MCP SDK 의존성). pydantic / anyio / mcp 가 venv 에 설치되어 있어야 회귀가 동작 (시스템 python 으로는 ModuleNotFoundError).
- 기타: 모든 스킬 및 MCP 출력은 공통 JSON 계약 구조를 따라야 함.
- (v0.5.6 신규) sub-agent 출력은 §5 spec fit 자동 검증 (`workflow_kit.contract_v1.output_validator.validate_output()`). 위반 시 §7.4 정책.
- (v0.5.6 신규) orchestrator 측 위임 결정은 `workflow_kit.contract_v1.delegator.choose_role()` 자동 호출. §6.3 MUST-NOT-delegate 매치 시 직접 처리.
- (v0.5.7 신규) multi-component sub-task 는 `delegator.choose_roles()` (fan-out) + `output_validator.validate_fanin_output()` (fan-in) 으로 자동 enforce. cross-ref 갱신 / fan-in 통합 보고 / parent_delegation_id 발급은 §6.3 에 따라 orchestrator 직접 처리. 자세한 wire 패턴: [`workflow-source/core/orchestrator_contract_v1_wire_guide.md`](https://github.com/ykylee/standard_ai_workflow/blob/main/workflow-source/core/orchestrator_contract_v1_wire_guide.md).
- (v0.5.7 신규) `task.required_model_tier` 가 명시되지 않으면 `delegator.recommend_model_tier()` 가 main keyword (아키텍처/정책/5+ 파일/cross-cutting/5+ source) 기반 자동 결정. `choose_role` 결과의 `decision.recommended_model_tier` 에 박힘.
- (v0.5.8 신규) 비대화형 환경에서 `--harness` 미지정 시 fail (interactive picker 는 TTY 에서만 동작). 자동화/CI 경로는 `--harness codex --harness opencode ...` 명시 필수.
- (v0.5.10 신규) sub-agent `delegation_id` 는 부모의 `{parent_id}-st-{N}` 형식 (parent-prefix spec). 회귀: `tests/check_wire_guide_v059.py`, `tests/check_contract_v1_multi_component.py`.
- **신규 (v0.5.4)**: orchestrator는 sub-agent 위임 가능한 작업을 직접 도구 호출로 처리하지 않는다 (제6.1장). 자세한 contract: [`workflow-source/core/orchestrator_subagent_contract_v1.md`](https://github.com/ykylee/standard_ai_workflow/blob/main/workflow-source/core/orchestrator_subagent_contract_v1.md).

## 다음에 읽을 문서
- [설치·사용 가이드 (v0.5.10 신규)](./INSTALLATION_AND_USAGE.md)
- [세션 인계 문서 v0.5.10](https://github.com/ykylee/standard_ai_workflow/blob/main/ai-workflow/memory/release/v0.5.10/session_handoff.md)
- [작업 백로그 (v0.6.3 archive)](https://github.com/ykylee/standard_ai_workflow/blob/main/ai-workflow/memory/archive/2026-06-12/work_backlog.md)
- [Orchestrator ↔ Sub-agent Contract v1](https://github.com/ykylee/standard_ai_workflow/blob/main/workflow-source/core/orchestrator_subagent_contract_v1.md)
- [Wire 가이드 v0.5.7+](https://github.com/ykylee/standard_ai_workflow/blob/main/workflow-source/core/orchestrator_contract_v1_wire_guide.md)
- [Maturity Matrix](https://github.com/ykylee/standard_ai_workflow/blob/main/workflow-source/core/maturity_matrix.json)
- [릴리스 노트 v0.5.10](https://github.com/ykylee/standard_ai_workflow/blob/main/workflow-source/releases/Beta-v0.5.10.md)

