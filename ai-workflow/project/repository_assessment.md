# Repository Assessment

- 문서 목적: 기존 프로젝트에 표준 AI 워크플로우를 도입하기 전에 현재 코드베이스와 문서 구조를 빠르게 진단한다.
- 범위: 저장소 구조, 추정 기술 스택, 문서 위치, 테스트 흔적, 초기 워크플로우 도입 포인트
- 대상 독자: 개발자, 운영자, AI agent, 프로젝트 온보딩 담당자
- 상태: draft
- 최종 수정일: 2026-04-24
- 관련 문서: `./project_workflow_profile.md`, `./session_handoff.md`, `../core/workflow_adoption_entrypoints.md`

## 1. 요약

- 분석 대상 프로젝트:
- `Standard AI Workflow`
- 분석 모드:
- `existing`
- 추정 기본 스택:
- `unknown`
- 감지된 스택 라벨:
- `없음`

## 2. 저장소 구조 관찰

- 상위 디렉터리 항목:
- `.codex.pre_workflow_2026-04-24, .git, .github, .gitignore, README.md, backlog, core, dist, examples, global-snippets, harnesses, mcp, releases, requirements-dev.txt, schemas, scripts, skills, split_checklist.md, templates, tests, work_backlog.md, workflow_kit`
- 소스 디렉터리 후보:
- `없음`
- 문서 디렉터리 후보:
- `없음`
- 테스트 디렉터리 후보:
- `tests`

## 3. 추정 명령

- 설치:
- `TODO: 설치 명령 입력`
- 로컬 실행:
- `TODO: 로컬 실행 명령 입력`
- 빠른 테스트:
- `TODO: 빠른 테스트 명령 입력`
- 격리 테스트:
- `TODO: 격리 테스트 명령 입력`
- 실행 확인:
- `TODO: 실행 확인 명령 입력`

## 4. package script 및 경로 샘플

- package script 목록:
- `없음`
- 분석 중 확인한 경로 샘플:
- `.codex.pre_workflow_2026-04-24`
- `.gitignore`
- `README.md`
- `requirements-dev.txt`
- `split_checklist.md`
- `work_backlog.md`
- `.github/workflows/smoke.yml`
- `ai-workflow/README.md`
- `ai-workflow/core/global_workflow_standard.md`
- `ai-workflow/core/output_schema_guide.md`
- `ai-workflow/core/workflow_adoption_entrypoints.md`
- `ai-workflow/core/workflow_agent_topology.md`
- `ai-workflow/core/workflow_harness_distribution.md`
- `ai-workflow/core/workflow_mcp_candidate_catalog.md`
- `ai-workflow/core/workflow_skill_catalog.md`
- `ai-workflow/project/project_workflow_profile.md`
- `ai-workflow/project/repository_assessment.md`
- `ai-workflow/project/session_handoff.md`
- `ai-workflow/project/state.json`
- `ai-workflow/project/work_backlog.md`

## 5. 워크플로우 도입 초안

- 추천 문서 위키 홈:
- `README.md`
- 추천 운영 문서 위치:
- `core/`
- 추천 backlog 위치:
- `backlog/`
- 추천 session handoff 위치:
- `ai-workflow/project/session_handoff.md`

## 6. 자동 분석 기반 다음 작업

- 현재 추정 명령과 실제 운영 명령이 일치하는지 확인한다.
- 이 저장소는 self-dogfood 중이므로 `ai-workflow/project/*` 와 루트 `README.md`, `core/`, `backlog/` 의 역할 경계를 먼저 확정한다.
- 빠른 테스트와 실행 확인 기준이 약하면 우선 profile 문서에서 검증 규칙을 먼저 보강한다.

## 다음에 읽을 문서

- 프로젝트 프로파일: [./project_workflow_profile.md](./project_workflow_profile.md)
- 세션 인계 문서: [./session_handoff.md](./session_handoff.md)
- 도입 분기 가이드: [../core/workflow_adoption_entrypoints.md](../core/workflow_adoption_entrypoints.md)
