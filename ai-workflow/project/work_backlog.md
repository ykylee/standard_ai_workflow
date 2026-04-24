# 작업 백로그 인덱스

- 문서 목적: 날짜별 작업 백로그 문서의 위치와 운영 기준을 관리한다.
- 범위: 일자별 백로그 문서
- 대상 독자: 프로젝트 참여자, 문서 작성자, 개발자, 운영자
- 상태: draft
- 최종 수정일: 2026-04-24
- 관련 문서: `./session_handoff.md`, `./project_workflow_profile.md`, `./backlog/iyeong-gyun-ui-MacBookAir.local/192.168.0.139/2026-04-24.md`

## 운영 원칙

- 세션 시작 시 본 인덱스와 최신 날짜 백로그를 먼저 확인한다.
- 새 작업은 브리핑 후 해당 날짜 백로그에 등록한다.
- 세션 종료 전에는 handoff 문서를 갱신한다.
- 검증 결과와 미실행 사유는 날짜별 백로그에 남긴다.
- 날짜별 backlog 는 `backlog/<host-name>/<host-ip>/YYYY-MM-DD.md` 형식으로 호스트별 분리한다.
- 사용자에게 직접 보여지는 작업 기록과 상태 요약은 한국어를 기본으로 작성한다.
- 다음 세션에 필요한 핵심 사실만 남기고, 중간 탐색 흔적과 중복 요약은 줄인다.

## 날짜별 백로그 문서

- [2026-04-24 작업 백로그](./backlog/iyeong-gyun-ui-MacBookAir.local/192.168.0.139/2026-04-24.md)

## 최신 진행 상태

- 최신 작업: `TASK-001 표준 AI 워크플로우 초기 도입`
- 상태: `in_progress`
- 다음 확인: `python3 tests/check_docs.py` 실행 결과와 `ai-workflow/project/state.json` 재생성 여부

## 장기 작업 계획 문서

- [TASK-001 표준 AI 워크플로우 초기 도입 계획](./plans/TASK-001-standard-workflow-onboarding.md)
- [TASK-002 기존 프로젝트 온보딩 자동 루틴 강화 계획](./plans/TASK-002-existing-project-onboarding-hardening.md)
- [TASK-003 실제 적용 검증 및 파일럿 기록 계획](./plans/TASK-003-pilot-adoption-validation.md)
- [TASK-004 출력 계약 및 실패 스키마 안정화 계획](./plans/TASK-004-output-contract-stabilization.md)
- [TASK-005 공통 라이브러리 추출 및 스크립트 정리 계획](./plans/TASK-005-reusable-package-extraction.md)
- [TASK-006 read-only MCP SDK transport 승격 계획](./plans/TASK-006-read-only-mcp-sdk-promotion.md)
- [TASK-007 릴리즈 패키징 및 운영 절차 정리 계획](./plans/TASK-007-release-packaging-operations.md)
