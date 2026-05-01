# Repository Assessment

- 문서 목적: 대상 저장소의 워크플로우 성숙도를 진단하고 도입 전략을 제안한다.
- 범위: 저장소 구조 분석, 성숙도 평가, 개선 제안
- 대상 독자: 개발자, AI 에이전트, 프로젝트 매니저
- 상태: draft (Phase 6 진입)
- 최종 수정일: 2026-05-01
- 관련 문서: [../../docs/PROJECT_PROFILE.md](../../docs/PROJECT_PROFILE.md), [../../workflow-source/core/maturity_matrix.json](../../workflow-source/core/maturity_matrix.json)

## 1. 요약

- 분석 대상 프로젝트: `Standard AI Workflow`
- 현재 상태: **Phase 6 (편집 정밀화 및 지능형 읽기 도구 최적화)**
- 주요 기술 스택: Python 3.10+, Markdown, JSON-RPC, MCP (Model Context Protocol)
- 워크플로우 성숙도: Level 4+ (전략적 최적화 및 도구 고도화 단계)

## 2. 저장소 구조

- **Core Logic**: `workflow-source/workflow_kit/` (워크플로우 핵심 로직 및 공통 모듈)
- **Operational Docs**: `ai-workflow/memory/` (세션 상태 및 백로그 관리)
- **Automation Scripts**: `workflow-source/scripts/` (부트스트랩, 배포, 상태 생성 등)
- **Tests**: `workflow-source/tests/` (문서 무결성 및 스크립트 기능 검증)
- **Examples**: `workflow-source/examples/` (워크플로우 적용 사례 및 출력 샘플)
- **Schemas**: `workflow-source/schemas/` (JSON 스키마 및 규약 문서)
- **Skills and MCP Tools**: `workflow-source/skills/`, `workflow-source/mcp/`

## 3. 핵심 자동화 도구 및 명령

- **부트스트랩**: `python3 workflow-source/scripts/bootstrap_workflow_kit.py` (신규 프로젝트에 워크플로우 이식)
- **데모 실행**: `python3 workflow-source/scripts/run_demo_workflow.py` (표준 워크플로우 사이클 시뮬레이션)
- **문서 검증**: `python3 workflow-source/tests/check_docs.py` (링크 및 메타데이터 무결성 점검)
- **배포 번들링**: `python3 workflow-source/scripts/export_harness_package.py`

## 4. 워크플로우 도입 현황

- **문서화**: 모든 운영 문서가 `ai-workflow/memory/` 하위에 표준화되어 있으며, `AGENTS.md`를 통해 Codex 진입점이 명확함.
- **상태 관리**: `state.json`과 날짜별 백로그를 통해 세션 간 연속성이 완벽하게 보장됨.
- **정밀 편집**: Phase 6 진입으로 `robust-patcher` 기반의 고신뢰도 코드 수정 체계 구축 중.

## 5. 향후 과제

- **지능형 컨텍스트**: `smart-context-reader`를 통한 대규모 코드베이스 분석 효율화.
- **팀 협업 최적화**: 멀티 에이전트 환경에서의 상태 동기화 및 충돌 방지 로직 강화.

## 다음에 읽을 문서

- 관련 문서: [../../docs/PROJECT_PROFILE.md](../../docs/PROJECT_PROFILE.md), [../../workflow-source/core/maturity_matrix.json](../../workflow-source/core/maturity_matrix.json)
- 세션 인계 문서: [./session_handoff.md](./session_handoff.md)
