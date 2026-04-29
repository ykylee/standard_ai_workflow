# Project Workflow Profile

- 문서 목적: 공통 표준 워크플로우를 `Standard AI Workflow` 저장소에 적용할 때 필요한 프로젝트 특화 규칙을 정리한다.
- 범위: 저장소 목적, 문서 구조, 기본 명령, 환경 기록 위치, 프로젝트 특화 검증 포인트, 예외 규칙
- 대상 독자: 개발자, 운영자, AI agent, 프로젝트 온보딩 담당자
- 상태: draft
- 최종 수정일: 2026-04-24
- 관련 문서: `../core/global_workflow_standard.md`, `./session_handoff.md`, `./work_backlog.md`

## 1. 프로젝트 개요

- 프로젝트명:
- `Standard AI Workflow`
- 프로젝트 목적:
- 재사용 가능한 AI workflow 문서, skill prototype, read-only MCP draft, harness distribution 자산을 한 저장소에서 관리하고 검증한다.
- 주요 이해관계자:
- workflow 설계자, 저장소 관리자, Codex/OpenCode 통합 담당자

## 2. 문서 구조

- 문서 위키 홈:
- `README.md`
- 운영 문서 위치:
- `core/`
- 백로그 위치:
- `backlog/`
- 세션 인계 문서 위치:
- `ai-workflow/project/session_handoff.md`
- 환경 기록 위치:
- `releases/`

## 3. 기본 명령

- 설치:
- `python3 -m pip install -r requirements-dev.txt`
- 로컬 실행:
- `python3 scripts/run_demo_workflow.py --example-project acme_delivery_platform`
- 빠른 테스트:
- `python3 tests/check_docs.py, python3 tests/check_output_samples.py`
- 격리 테스트:
- `python3 tests/check_demo_workflow.py, python3 tests/check_existing_project_onboarding.py`
- UI/API 실행 확인:
- `python3 scripts/run_demo_workflow.py --example-project acme_delivery_platform`

## 4. 프로젝트 특화 검증 포인트

- 코드 변경 시:
- 공통 helper, runner, output contract 를 건드리면 관련 smoke 와 schema/sample 검증을 함께 돌린다.
- 문서 변경 시:
- README, core 문서, examples, scripts 안내 문서의 링크와 현재 구현 상태가 어긋나지 않는지 함께 확인한다.
- UI 변경 시:
- 실제 UI 는 없지만 Codex/OpenCode overlay 나 예시 출력 변경 시 user-facing 문구와 진입 흐름을 다시 읽는다.
- 배포/운영 변경 시:
- dist export, release note, harness package 구조가 현재 버전과 맞는지 확인하고, 필요한 경우 pre-release 산출물까지 재생성한다.

## 5. 프로젝트 특화 예외 규칙

- 병합 규칙:
- ai-workflow/project/session_handoff.md 와 최신 workflow backlog 가 충돌하면 병합 후 handoff 를 우선 재작성한다.
- 승인 규칙:
- release/export 구조, harness 기본 정책, output contract 변경은 문서와 테스트를 같이 맞춘 뒤 반영한다.
- 환경 제약:
- 루트 `.codex` 경로는 Codex config 디렉터리와 충돌할 수 있으므로 전역 설정 병합 전 수동 검토가 필요하다.
- 기타:
- 이 저장소는 self-dogfood 중이므로 `ai-workflow/project/*` 를 workflow state docs 로 사용하고, 실제 project docs 는 루트 `README.md`, `core/`, `backlog/` 를 우선 본다.

## 다음에 읽을 문서

- 공통 표준: [../core/global_workflow_standard.md](../core/global_workflow_standard.md)
- 세션 인계 문서: [./session_handoff.md](./session_handoff.md)
- 작업 백로그 인덱스: [./work_backlog.md](./work_backlog.md)
