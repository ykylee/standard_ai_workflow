# Project Workflow Profile

- 문서 목적: 공통 표준 워크플로우를 특정 저장소에 적용할 때, 프로젝트 특화 규칙만 얇게 정리할 수 있도록 템플릿을 제공한다.
- 범위: 저장소 목적, 문서 구조, 기본 명령, 환경 기록 위치, 장기 작업 계획 문서 위치, 프로젝트 특화 검증 포인트, 예외 규칙
- 대상 독자: 개발자, 운영자, AI agent, 프로젝트 온보딩 담당자
- 상태: draft
- 최종 수정일: 2026-04-18
- 관련 문서: `../core/global_workflow_standard.md`, `session_handoff_template.md`, `work_backlog_template.md`

## 1. 프로젝트 개요

- 프로젝트명:
- 예: `Acme Delivery Platform`
- 프로젝트 목적:
- 예: `배포 파이프라인과 운영 승인 흐름을 통합 관리한다.`
- 주요 이해관계자:
- 예: `플랫폼팀, QA팀, 운영팀`

## 2. 문서 구조

- 아래 경로는 `ai-workflow/project/` 내부 문서 위치가 아니라, 실제 프로젝트 저장소 기준 문서 경로를 적는다.

- 문서 위키 홈:
- 예: `docs/README.md`
- 운영 문서 위치:
- 예: `docs/operations/`
- 백로그 위치:
- 예: `docs/operations/backlog/`
- 세션 인계 문서 위치:
- 예: `docs/operations/session_handoff.md`
- 환경 기록 위치:
- 예: `docs/operations/environments/`
- 장기 작업 계획 문서 위치:
- 예: `docs/operations/plans/`

## 3. 기본 명령

- 설치:
- 예: `make install-dev`
- 로컬 실행:
- 예: `make run`
- 빠른 테스트:
- 예: `pytest`, `cargo test`
- 격리 테스트:
- 예: `docker compose --profile test run --rm api-test`
- UI/API 실행 확인:
- 예: `curl /health`, `npm run e2e`

## 4. 프로젝트 특화 검증 포인트

- 코드 변경 시:
- 예: `단위 테스트와 lint는 필수`
- 문서 변경 시:
- 예: `허브 링크와 metadata 검사 필수`
- UI 변경 시:
- 예: `스크린샷 또는 e2e 재검증 필요`
- 배포/운영 변경 시:
- 예: `실행 확인과 롤백 절차 검토 필요`

## 5. 프로젝트 특화 예외 규칙

- 병합 규칙:
- 예: `handoff와 최신 백로그를 병합 후 재작성`
- 승인 규칙:
- 예: `운영 문서 변경은 플랫폼팀 리뷰 필요`
- 환경 제약:
- 예: `사내 VPN 없이는 staging 접근 불가`
- 기타:

## 다음에 읽을 문서

- 공통 표준: [../core/global_workflow_standard.md](../core/global_workflow_standard.md)
- 세션 인계 템플릿: [./session_handoff_template.md](./session_handoff_template.md)
