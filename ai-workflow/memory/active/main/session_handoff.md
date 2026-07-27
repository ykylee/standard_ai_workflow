# Session Handoff

- 문서 목적: 다음 세션이 바로 이어받을 수 있도록 현재 상태를 요약한다.
- 범위: 현재 기준선, 진행 상태, 다음 시작 포인트, 남은 리스크
- 대상 독자: AI agent, 저장소 관리자
- 상태: active
- 최종 수정일: 2026-07-27
- 관련 문서: [state.json](./state.json), [backlog](./backlog/), [sessions](./sessions/)

## 1. 현재 작업 요약

- 현재 기준선: v1.0.0-beta + `origin/main` = `dac83e3` (CI smoke·mypy-strict 모두 green)
- 현재 주 작업 축: 환경에 기대던 판정을 계약 검증으로 분리 + 원인은 추측이 아니라 관측으로 확정
- 최근 핵심 기준 문서:
  - [global_workflow_standard.md](../../../core/global_workflow_standard.md)
  - [Beta-v1.0.0.md §2.35~§2.36](../../../../workflow-source/releases/Beta-v1.0.0.md)

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
- TASK-2026-07-27-main-002 남은 결함 3건 + CI 자기참조 해소
- TASK-2026-07-27-main-003 남은 자기참조 3건 해소 + CI red 원인 계측 확정

## 5. 다음 세션 시작 포인트

TASK-2026-07-27-main-003 으로 종료했다. 세부는 릴리스 노트 §2.35 (6)~(8) 과 §2.36 에 있다.
**CI 는 green 이다** — `origin/main` = `dac83e3`, smoke·mypy-strict 모두 success, 3커밋 연속.

- [ ] **`backlog-update --apply` 가 state.json 을 손상시킨다.** 이번 세션에서 실측:
      긴 `recent_done_items` 2건을 조용히 지우고 새 항목은 추가하지 않았다. `written_paths`
      도 state.json 과 task SSOT 를 보고하지 않는다(4개 썼는데 2개만 보고). handoff 의
      in_progress / blocked 에는 빈 bullet 을 계속 덧붙인다. 이번엔 손으로 되돌려 갱신했다.
      → **stable 선언 skill 이 상태 문서를 파괴하는 것이라 우선순위 높다.**
- [ ] 슬래시(`/`) 가 들어간 브랜치에서 `check_branch_scoped_memory` 와
      `check_self_application` 이 깨진다 (probe 브랜치에서 실측). main 에서는 안 드러난다.
- [ ] 스케줄 workflow 2건 여전히 red — `consumer-metrics-digest` (issue 게시 스텝),
      `okf-validate` (V-R10 online URL 검증). 이번 작업과 무관한 별건.
- [ ] `active/<branch>/` 로 바뀐 bootstrap layout 을 실제 소비자 프로젝트에 적용해 볼 것
      (기존 평면 프로젝트는 유지되지만, 옮기려면 `tools/migrate_memory_to_branch_scoped.py`)

## 6. 남은 리스크 / 확인하지 못한 것

- **이번 세션의 교훈**: §2.35 (6) 에서 **관측하지 않은 값을 관측한 것처럼 적었다**. CI 의
  실패 사유가 어디에도 안 남아 있는 상태에서 로컬 출력을 CI 의 것으로 서술했고, 그래서
  원인을 mypy 로 잘못 지목했다. 실제 원인은 `gh` 인증 부재였다(§2.36). 처방이 맞았던 건
  운이다. **로컬 재현의 출력과 CI 의 출력은 다른 증거다.**
- **`gh` 인증 유무는 verdict 를 바꾸는 1급 환경 변수다** — CI 에서는 `skipped`, 로컬에서는
  `ci_sanity`/`ci_stale`. verdict 를 보는 검사는 전부 집합 검사 + 주입 검증이어야 한다.
- **확인 못 함**: 새로 생성한 진입점을 실제 에이전트 세션에서 로드해 보지는 않았다.
  파일 내용과 bootstrap 산출물, `check_self_application.py` 까지만 검증했다.
- **확인 못 함**: branch-scoped bootstrap 을 *기존 소비자 프로젝트* 에 재실행해 본 적은
  없다. 평면 layout 보존 분기는 temp fixture 로만 확인했다.
- **주요 제약**: 발표자료(`docs/presentations/`)의 11·12·15·22번 주장이 이제 사실이다.
  덱의 원리는 `core/workflow_design_principles.md` 가 정본이다.
