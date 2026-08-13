# 표준 AI 워크플로우 — 상시 규칙 (플러그인 SessionStart 주입)

## 작업 원칙

<!-- generated-from: core/global_workflow_standard.md §1 · §3 · §8 · §11 — 이 블록은 직접 고치지 않는다. 표준 문서를 고치고 다시 생성한다. -->

- 새 세션은 항상 현재 상태 요약 문서부터 읽는다.
- 작업은 시작 전에 목적, 범위, 예상 산출물, 영향 문서를 짧게 브리핑한다.
- 작업은 상태 문서에 기록하고, 진행 상태는 `planned`, `in_progress`, `blocked`, `done` 중 하나로 관리한다.
- 검증하지 않은 결과는 완료로 확정하지 않는다.
- 세션 종료 전에는 다음 세션이 바로 이어받을 수 있게 현재 상태를 요약한다.
- 여러 에이전트가 함께 일할 수 있으므로, 작업 시작 전에 원격을 동기화해 다른 에이전트의 진행 상황을 확인하고 겹치지 않는 작업을 선택한다.
- 다른 에이전트의 작업을 지우거나 덮어쓰는 등 되돌릴 수 없는 작업은 단독으로 결정하지 않고 사용자에게 확인한다.
- 공통 표준은 얇게 유지하고, 프로젝트별 차이는 프로젝트 프로파일에 둔다.

## 세션 종료 순서

세션 종료는 **memory 갱신 → commit → push** 순서로 진행한다. memory 갱신을 commit 이후 별도 turn 에 분리하지 않는다 (push 시 memory 갱신 내용이 동일 commit 에 포함되도록 협업 정합 보장).

- 종료 전 갱신 대상: `state.json`, `session_handoff.md`, 최신 backlog

## 메모리 갱신 경로

- 세션 시작 baseline 복원: `wk session-start`
- task 등록 / 갱신: `wk backlog-update`
- 영향 문서 동기화 (advisory): `wk doc-sync`
- 세션 종료 시 state.json 재생성: `wk refresh-state`

- handoff 의 `in_progress` / `blocked` 목록이 비면 **빈 bullet `-`** 로 둔다. 산문을 쓰면 작업 항목으로 파싱된다.
- handoff 의 최근 완료 목록 항목은 `TASK-` 로 시작하고, 10건을 넘지 않는다.
- backlog task 의 `status` 는 `planned` / `in_progress` / `blocked` / `done` 중 하나다.
- `state.json` 은 **생성물**이다 — 손으로 고치지 않는다. SSOT 는 `backlog/tasks/` 와 `session_handoff.md` 이고, 세션 종료 시 `wk refresh-state` 로 재생성한다.
- `session_handoff.md` 와 backlog 는 **state.json 생성기의 입력**이다 — 형식을 벗어나 쓰면 state.json 이 조용히 오염된다.
