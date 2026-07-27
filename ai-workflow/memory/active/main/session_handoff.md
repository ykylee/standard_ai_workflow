# Session Handoff

- 문서 목적: 다음 세션이 바로 이어받을 수 있도록 현재 상태를 요약한다.
- 범위: 현재 기준선, 진행 상태, 다음 시작 포인트, 남은 리스크
- 대상 독자: AI agent, 저장소 관리자
- 상태: active
- 최종 수정일: 2026-07-27
- 관련 문서: [state.json](./state.json), [backlog](./backlog/), [sessions](./sessions/)

## 1. 현재 작업 요약

- 현재 기준선: v1.0.0-beta (origin/main e7a08bf) 기준 + 본 세션 변경 반영
- 현재 주 작업 축: 진입점 규칙의 단일 출처화 — 정본 `core/global_workflow_standard.md` 에서 생성하고 검사로 강제
- 최근 핵심 기준 문서:
  - [global_workflow_standard.md](../../../core/global_workflow_standard.md)
  - [Beta-v1.0.0.md §2.31](../../../../workflow-source/releases/Beta-v1.0.0.md)

## 2. 진행 중 작업

- 현재 `in_progress` 작업:
-

## 3. 차단 작업

- 현재 `blocked` 작업:
-

## 4. 최근 완료 작업

- 최근 완료 작업 목록:
- TASK-2026-07-25-main-001 선언과 사실을 맞춘다 (Pages / mypy strict / YAML·스킬·MCP 검사층)
- TASK-2026-07-27-main-001 진입점 규칙 단일 출처화 + 자기 적용을 검사로 고정

## 5. 다음 세션 시작 포인트

TASK-2026-07-27-main-001 로 종료했다. 세부는 릴리스 노트 §2.31~§2.34 에 있다.

- [ ] 푸시 후 CI 확인 — smoke 는 `.venv/bin/python` 기준 217/217 이지만 시스템 `python3` 로는
      의존성 부재로 8건이 떨어진다 (코드 결함 아님, §3 검증 참조)
- [ ] 남은 결함 3건 착수 여부 판단 (아래 §6)

## 6. 남은 리스크 / 확인하지 못한 것

- **확인 못 함**: 새로 생성한 진입점을 실제 에이전트 세션에서 로드해 보지는 않았다.
  파일 내용과 bootstrap 산출물, 그리고 `check_self_application.py` 까지만 검증했다.
- **알려진 결함 (이번에 고치지 않음)**:
  - `AGENTS.md` 를 codex 와 pi-dev 가 함께 쓴다 — 둘 다 선택하면 나중 것이 이긴다.
  - bootstrap 은 평평한 `active/` 레이아웃을 만드는데 이 저장소는 브랜치별
    `active/<branch>/` 다. 그래서 루트 진입점의 경로만 손으로 맞췄다.
  - `WORK_STATUS_RE` 는 대문자 task ID 만 받는데 `TASK_ID_PATTERN` 은 소문자 브랜치
    세그먼트를 허용한다 (`TASK-2026-07-27-main-001`). 두 정규식이 갈라져 있다.
- **주요 제약**: 이번 변경으로 발표자료(`docs/presentations/`)의 11·12·15·22번 주장이
  사실이 됐다. 덱의 원리는 `core/workflow_design_principles.md` 가 정본이다.
