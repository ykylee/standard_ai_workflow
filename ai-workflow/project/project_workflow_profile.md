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
- 여러 프로젝트에서 공통으로 사용할 AI 협업 워크플로우 문서, 템플릿, skill/MCP/runner 프로토타입, 하네스 배포 기준을 독립 패키지 형태로 제공한다.
- 주요 이해관계자:
- 저장소 관리자, workflow 설계자, AI agent 운영자, 하네스 통합 담당자, 파일럿 적용 프로젝트 담당자

## 2. 문서 구조

- 문서 위키 홈:
- `README.md`
- 운영 문서 위치:
- `core/`
- 백로그 위치:
- `ai-workflow/project/backlog/<host-name>/<host-ip>/`
- 세션 인계 문서 위치:
- `ai-workflow/project/session_handoff.md`
- 환경 기록 위치:
- `README.md`
- 장기 작업 계획 문서 위치:
- `ai-workflow/project/plans/`

### 2.1 문서 구조 메모

- `ai-workflow/project/` 는 세션 상태와 handoff 용 workflow state docs 로 사용한다.
- 현재 저장소에는 별도 `docs/` 운영 문서 트리가 없으며, 프로젝트 설명과 운영 기준은 루트 `README.md`, `core/`, `tests/README.md`, `scripts/README.md` 를 우선 참조한다.
- 프로젝트 개발 backlog 는 루트 `backlog/` 에도 있다.
- 날짜별 workflow backlog 는 호스트명/IP 폴더 아래에 둬 병렬 작업 중 task 번호 충돌을 줄인다.
- 검증 환경 핵심값은 `README.md` 와 `ai-workflow/project/session_handoff.md` 에 기록한다.

## 3. 기본 명령

- 설치:
- `python3 -m pip install -r requirements-dev.txt`
- 로컬 실행:
- 상시 실행 서버 없음. 필요 시 개별 script 를 직접 실행한다.
- 빠른 테스트:
- `python3 tests/check_docs.py`
- 격리 테스트:
- `python3 tests/check_*.py`
- UI/API 실행 확인:
- `for t in tests/check_*.py; do python3 "$t" || exit 1; done`

## 4. 프로젝트 특화 검증 포인트

- 코드 변경 시:
- 변경한 skill/MCP/runner 와 직접 연결된 `tests/check_*.py` 를 우선 실행하고, 공통 계약 또는 문서 링크 영향이 있으면 `python3 tests/check_docs.py`, `python3 tests/check_output_samples.py`, `python3 tests/check_generated_schema_validation.py` 를 추가한다.
- 문서 변경 시:
- 문서 헤더 메타데이터, 상대 링크, `README.md`/허브 문서의 진입 링크를 확인하고 `python3 tests/check_docs.py` 를 실행한다.
- UI 변경 시:
- 현재 UI 없음. 하네스 문서나 브라우저 대상 산출물이 추가될 때 별도 시각 검증 기준을 만든다.
- 배포/운영 변경 시:
- 하네스 export, release note, manifest, zip 산출물 경로를 함께 확인하고 `python3 tests/check_export_harness_package.py` 를 실행한다.

## 5. 프로젝트 특화 예외 규칙

- 병합 규칙:
- `ai-workflow/project/session_handoff.md` 와 최신 `ai-workflow/project/backlog/*.md` 가 충돌하면 최신 검증 결과와 실제 변경 파일 기준으로 handoff 를 재작성하고 `state.json` 을 재생성한다.
- 승인 규칙:
- release note, 하네스 export 계약, output schema, MCP transport 계약 변경은 리뷰 대상이다.
- 환경 제약:
- 공식 MCP SDK 검증은 Python 3.11 이상과 `mcp[cli]` 설치 환경을 기준으로 한다. 저장소 루트의 `mcp/` 디렉터리와 SDK 패키지명이 겹치므로 가상환경 Python 으로 실행한다.
- 기타:
- `ai-workflow/` 는 일반 프로젝트 탐색 범위가 아니라 세션 복원과 workflow 상태 관리용 메타 레이어로 다룬다.

## 다음에 읽을 문서

- 공통 표준: [../core/global_workflow_standard.md](../core/global_workflow_standard.md)
- 세션 인계 문서: [./session_handoff.md](./session_handoff.md)
- 작업 백로그 인덱스: [./work_backlog.md](./work_backlog.md)
