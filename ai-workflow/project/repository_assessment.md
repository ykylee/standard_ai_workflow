# Repository Assessment

- 문서 목적: 기존 프로젝트에 표준 AI 워크플로우를 도입하기 전에 현재 코드베이스와 문서 구조를 빠르게 진단한다.
- 범위: 저장소 구조, 추정 기술 스택, 문서 위치, 테스트 흔적, 초기 워크플로우 도입 포인트
- 대상 독자: 개발자, 운영자, AI agent, 프로젝트 온보딩 담당자
- 상태: draft
- 최종 수정일: 2026-04-26
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
- `.DS_Store, .ai-workflow-backups, .git, .github, .gitignore, .opencode, .venv, AGENTS.md, GEMINI.md, QUICKSTART.md, README.md, backlog, core, dist, examples, global-snippets, harnesses, mcp, opencode.json, releases, requirements-dev.txt, schemas, scripts, skills, split_checklist.md, templates, tests, tmp, work_backlog.md, workflow_kit`
- 소스 디렉터리 후보:
- `없음`
- 문서 디렉터리 후보:
- `없음`
- 테스트 디렉터리 후보:
- `tests`

## 3. 추정 명령

- 설치:
- `pip install -r requirements-dev.txt`
- 로컬 실행:
- `python3 scripts/run_demo_workflow.py`
- 빠른 테스트:
- `python3 tests/check_docs.py`
- 격리 테스트:
- `for t in tests/check_*.py; do python3 "$t" || exit 1; done`
- 실행 확인:
- `python3 scripts/bootstrap_workflow_kit.py --help`

## 4. package script 및 경로 샘플

- package script 목록:
- `없음`
- 분석 중 확인한 경로 샘플:
- `.DS_Store`
- `.gitignore`
- `AGENTS.md`
- `GEMINI.md`
- `QUICKSTART.md`
- `README.md`
- `opencode.json`
- `requirements-dev.txt`
- `split_checklist.md`
- `work_backlog.md`
- `.ai-workflow-backups/20260424T125353Z/AGENTS.md`
- `.ai-workflow-backups/20260424T125353Z/.opencode/.gitignore`
- `.ai-workflow-backups/20260424T125353Z/.opencode/package-lock.json`
- `.ai-workflow-backups/20260424T125353Z/.opencode/package.json`
- `.ai-workflow-backups/20260424T125353Z/ai-workflow/README.md`
- `.ai-workflow-backups/20260424T144730Z/.opencode/.gitignore`
- `.ai-workflow-backups/20260424T144730Z/.opencode/package-lock.json`
- `.ai-workflow-backups/20260424T144730Z/.opencode/package.json`
- `.ai-workflow-backups/20260424T144730Z/ai-workflow/README.md`
- `.ai-workflow-backups/v2-backup-20260424234723/README.md`

## 5. 워크플로우 도입 초안

- 추천 문서 위키 홈:
- `README.md`
- 추천 운영 문서 위치:
- `docs/operations/`
- 추천 backlog 위치:
- `docs/operations/backlog/`
- 추천 session handoff 위치:
- `docs/operations/session_handoff.md`

## 6. 자동 분석 기반 다음 작업

- 현재 추정 명령과 실제 운영 명령이 일치하는지 확인한다.
- 기존 문서 체계가 있으면 운영 문서 위치를 그대로 따를지, 별도 워크플로우 디렉터리로 분리할지 결정한다.
- 빠른 테스트와 실행 확인 기준이 약하면 우선 profile 문서에서 검증 규칙을 먼저 보강한다.

## 다음에 읽을 문서

- 프로젝트 프로파일: [./project_workflow_profile.md](./project_workflow_profile.md)
- 세션 인계 문서: [./session_handoff.md](./session_handoff.md)
- 도입 분기 가이드: [../core/workflow_adoption_entrypoints.md](../core/workflow_adoption_entrypoints.md)
