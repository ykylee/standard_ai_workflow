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
-

## 3. 차단 작업

- 현재 `blocked` 작업:
- 
-

## 4. 최근 완료 작업

- 최근 완료 작업 목록:
- TASK-2026-07-25-main-001 선언과 사실을 맞춘다 (Pages / mypy strict / YAML·스킬·MCP 검사층)
- TASK-2026-07-27-main-001 진입점 규칙 단일 출처화 + 자기 적용을 검사로 고정
- TASK-2026-07-27-main-002 남은 결함 3건 + CI 자기참조 해소
## 5. 다음 세션 시작 포인트

TASK-2026-07-27-main-001 과 -002 로 종료했다. 세부는 릴리스 노트 §2.31~§2.35 에 있다.

- [ ] 푸시 후 CI 확인. §2.35 (4) 로 `check_release_summary_v0_11_15` 의 자기참조를
      없앴으므로, 이제 CI smoke 가 green 이어야 한다 — 아니면 다른 원인이다.
- [ ] `active/<branch>/` 로 바뀐 bootstrap layout 을 실제 소비자 프로젝트에 적용해 볼 것
      (기존 평면 프로젝트는 유지되지만, 옮기려면 `tools/migrate_memory_to_branch_scoped.py`)

## 6. 남은 리스크 / 확인하지 못한 것

- **확인 못 함**: 새로 생성한 진입점을 실제 에이전트 세션에서 로드해 보지는 않았다.
  파일 내용과 bootstrap 산출물, `check_self_application.py` 까지만 검증했다.
- **확인 못 함**: branch-scoped bootstrap 을 *기존 소비자 프로젝트* 에 재실행해 본 적은
  없다. 평면 layout 보존 분기는 temp fixture 로만 확인했다.
- **주요 제약**: 발표자료(`docs/presentations/`)의 11·12·15·22번 주장이 이제 사실이다.
  덱의 원리는 `core/workflow_design_principles.md` 가 정본이다.
