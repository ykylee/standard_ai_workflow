# Session Handoff

- 문서 목적: 다음 세션이 바로 이어받을 수 있도록 현재 상태를 요약한다.
- 범위: 현재 기준선, 진행 상태, 다음 시작 포인트, 남은 리스크
- 대상 독자: AI agent, 저장소 관리자
- 상태: active
- 최종 수정일: 2026-08-14
- 관련 문서: [backlog](./backlog/), [sessions](./sessions/)

## 1. 현재 작업 요약

- 현재 기준선: perf/changed-selection 워크스페이스 seed (2026-08-14). 아직 작업 전이다.
- 현재 주 작업 축: run_all_checks --changed — 검사가 자기 관찰 경로를 선언하고, 무관한 검사를 건너뛴다 (미선언은 항상 실행)
- 범위 밖(건드리지 않는다): 2축→1축 조건부(main-004) / 무거운 검사 추가 최적화 / push 게이트 변경

## 2. 진행 중 작업

- 현재 `in_progress` 작업:
- TASK-2026-08-14-perf-changed-selection-001 — run_all_checks --changed 선택 실행

## 3. 차단 작업

- 현재 `blocked` 작업:

## 4. 최근 완료 작업

- 최근 완료 작업 목록:

## 5. 다음 세션 시작 포인트

- [`backlog/tasks/TASK-2026-08-14-perf-changed-selection-001.md`](./backlog/tasks/TASK-2026-08-14-perf-changed-selection-001.md) 의 완료 기준을 먼저 읽는다.
- 작업 범위를 벗어나는 변경은 다른 워크스페이스와 충돌할 수 있으므로 backlog 에 별도 task 로 남긴다.

## 6. 남은 리스크

- 아직 검증된 산출물이 없다.
