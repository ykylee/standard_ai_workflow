---
name: backlog-update
description: 표준 AI 워크플로우 백로그 갱신 — 오늘 날짜 backlog 에 task 를 등록/갱신하고 PURPOSE.md 제외 영역과 겹치면 scope creep 을 경고한다.
---

# backlog-update

## 역할

오늘 작업을 `ai-workflow/memory/active/<branch>/backlog/<YYYY-MM-DD>.md` 와
`./tasks/<TASK-ID>.md` 에 등록하거나 갱신한다.

## 절차

1. 오늘 날짜 backlog 파일이 없으면 신규 작성, 있으면 기존 항목에 병합한다.
2. 상태값은 `planned` / `in_progress` / `blocked` / `done` 넷만 쓴다.
3. **in-scope check** — `task_brief` 와 영향 문서를 `PURPOSE.md` §3 의 제외 영역과
   대조해, 겹치면 scope creep 경고를 1줄 남긴다. `PURPOSE.md` 가 없으면 경고 없이
   advisory 로만 진행한다.
4. 우선순위 / 담당 / 완료 기준을 명시한다.

## 실행

```bash
wk backlog-update --help
```

상태를 바꾸지 않을 때는 `--status` 를 주지 않는다 — 미지정은 "바꾸지 말라" 는
뜻이고 기존 상태가 보존된다.

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
