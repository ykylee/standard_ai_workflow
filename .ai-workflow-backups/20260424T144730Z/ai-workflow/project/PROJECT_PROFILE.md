# Project Workflow Profile

- 문서 목적: 공통 표준 워크플로우를 `Export Sample` 저장소에 적용할 때 필요한 프로젝트 특화 규칙을 정리한다.
- 범위: 저장소 목적, 문서 구조, 기본 명령, 환경 기록 위치, 프로젝트 특화 검증 포인트, 예외 규칙
- 대상 독자: 개발자, 운영자, AI agent, 프로젝트 온보딩 담당자
- 상태: draft
- 최종 수정일: 2026-04-24
- 관련 문서: `../core/global_workflow_standard.md`, `./session_handoff.md`, `./work_backlog.md`

## 1. 프로젝트 개요

- 프로젝트명:
- `Standard AI Workflow`
- 프로젝트 목적:
- 여러 프로젝트에서 공통으로 사용할 수 있는 표준 AI 협업 워크플로우 문서와 템플릿, skill/MCP/agent 구현 기준을 독립 프로젝트 형태로 제공한다.
- 주요 이해관계자:
- 개발자, 운영자, AI agent 설계자, 프로젝트 온보딩 담당자

## 2. 문서 구조

- 문서 위키 홈:
- `docs/README.md`
- 운영 문서 위치:
- `docs/operations/`
- 백로그 위치:
- `docs/operations/backlog/`
- 세션 인계 문서 위치:
- `docs/operations/session_handoff.md`
- 환경 기록 위치:
- `docs/operations/environments/`

## 3. 기본 명령

- 설치:
- `pip install -r requirements-dev.txt` 또는 `python -m venv .venv && source .venv/bin/activate && pip install -r requirements-dev.txt`
- 로컬 실행:
- `python tests/check_*.py` (개별 테스트 파일 실행)
- 빠른 테스트:
- `python -m pytest tests/ -v` 또는 `python tests/check_docs.py`
- 격리 테스트:
- `python tests/check_session_start.py && python tests/check_docs.py`
- UI/API 실행 확인:
- 이 프로젝트는 CLI 기반 문서 패키지로 UI/API 없음

## 4. 프로젝트 특화 검증 포인트

- 코드 변경 시:
- `python -m pytest tests/ -v` 로 전체 테스트 통과 확인
- 문서 변경 시:
- `python tests/check_docs.py` 로 링크/템플릿 정합성 확인
- UI 변경 시:
- 이 프로젝트는 UI 없음
- 배포/운영 변경 시:
- GitHub release 태그 기준 `standard-ai-workflow-*-v{version}.zip` 패키지 생성 확인

## 5. 프로젝트 특화 예외 규칙

- 병합 규칙:
- TODO: handoff 와 최신 backlog 충돌 시 우선 재작성 기준을 적는다.
- 승인 규칙:
- TODO: 어떤 문서나 변경이 리뷰를 반드시 거쳐야 하는지 적는다.
- 환경 제약:
- TODO: VPN, secure runner, staging 권한 등 환경 제약을 적는다.
- 기타:
- skill/MCP 프로토타입과 문서 패키지가 함께 포함된 작업 저장소로, 다중 적용 전 공통 규칙 추가 검증 필요

## 다음에 읽을 문서

- 공통 표준: [../core/global_workflow_standard.md](../core/global_workflow_standard.md)
- 세션 인계 문서: [./session_handoff.md](./session_handoff.md)
- 작업 백로그 인덱스: [./work_backlog.md](./work_backlog.md)
