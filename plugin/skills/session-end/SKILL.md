---
name: session-end
description: 표준 AI 워크플로우 세션 종료 — handoff 와 backlog 를 갱신하고 state.json 을 재생성해 다음 세션이 그대로 이어받게 남긴다.
---

# session-end

## 역할

세션을 종료하며, 다음 세션이 바로 이어받을 수 있게 상태를 남긴다.

## 순서

세션 종료는 **memory 갱신 → commit → push** 순서로 진행한다. memory 갱신을 commit 이후 별도 turn 에 분리하지 않는다 (push 시 memory 갱신 내용이 동일 commit 에 포함되도록 협업 정합 보장).

## 절차

1. `session_handoff.md` 를 갱신한다 — 현재 기준선, 진행 중 / 차단 / 최근 완료 목록.
2. 오늘 날짜 backlog 의 task 상태를 실제 결과에 맞춘다 (`planned` / `in_progress` / `blocked` / `done`).
3. `state.json` 을 **재생성**한다 (손으로 고치지 않는다 — 아래 §11 계약).
4. 1~3 의 갱신분이 **같은 commit 에** 담기게 한 뒤 push 한다.

## 실행

```bash
wk refresh-state
```

`wk` 가 없으면 조용히 넘어가지 않는다 — 설치 안내를 보고하고
멈춘다 (`INSTALLATION_AND_USAGE.md` §3). 재생성 없이 손으로 쓴 `state.json` 은
입력 문서와 갈라진다.

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
