---
name: session-start
description: 표준 AI 워크플로우 세션 시작 — state.json + session_handoff.md + backlog 로 현재 기준선을 복원하고 다음 작업 후보를 보고한다.
---

# session-start

## 역할

`ai-workflow/memory/active/<branch>/` 의 현재 baseline 을 복원하고, 다음 작업
후보를 보고한다.

## 절차

1. `state.json` — 현재 기준선 (`latest_backlog_path`, 진행/차단/최근 완료 목록)
2. `session_handoff.md` — 이전 세션의 인계 사항
3. `backlog/<YYYY-MM-DD>.md` — 현재 작업 목록
4. `docs/PROJECT_PROFILE.md` — 프로젝트 메타
5. (있으면) `ai-workflow/memory/active/PURPOSE.md` — directional intent

읽은 뒤 한국어로 **1줄 기준선 요약 + 3~5개 다음 작업 후보 + 권장 다음 행동** 만
보고한다. 중간 reasoning, 중복 요약, 자기 설명은 내지 않는다.

`state.json` 이나 `PURPOSE.md` 가 없으면 실패로 처리하지 말고 *graceful skip* 후
scaffold 를 제안한다.

## 실행

```bash
wk session-start --help
```

`wk` 가 없으면 조용히 넘어가지 않는다 — 설치 안내를 보고하고
멈춘다 (`INSTALLATION_AND_USAGE.md` §3).

## 메모리 갱신 경로

<!-- generated-from: core/global_workflow_standard.md §1 · §3 · §8 · §11 — 이 블록은 직접 고치지 않는다. 표준 문서를 고치고 다시 생성한다. -->

- 세션 시작 baseline 복원: `wk session-start`
- task 등록 / 갱신: `wk backlog-update`
- 영향 문서 동기화 (advisory): `wk doc-sync`
- 세션 종료 시 state.json 재생성: `wk refresh-state`

- handoff 의 `in_progress` / `blocked` 목록이 비면 **빈 bullet `-`** 로 둔다. 산문을 쓰면 작업 항목으로 파싱된다.
- handoff 의 최근 완료 목록 항목은 `TASK-` 로 시작하고, 10건을 넘지 않는다.
- backlog task 의 `status` 는 `planned` / `in_progress` / `blocked` / `done` 중 하나다.
- `state.json` 은 **생성물**이다 — 손으로 고치지 않는다. SSOT 는 `backlog/tasks/` 와 `session_handoff.md` 이고, 세션 종료 시 `wk refresh-state` 로 재생성한다.
- `session_handoff.md` 와 backlog 는 **state.json 생성기의 입력**이다 — 형식을 벗어나 쓰면 state.json 이 조용히 오염된다.
