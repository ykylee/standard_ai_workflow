---
name: session-end
description: 표준 AI 워크플로우 세션 종료 — handoff 와 backlog 를 갱신하고 state.json 을 재생성해 다음 세션이 그대로 이어받게 남긴다.
---

# session-end

## 역할

세션을 종료하며, 다음 세션이 바로 이어받을 수 있게 상태를 남긴다.

## 순서

Close a session in the order **update memory → commit → push**. Do not split the memory update into a separate turn after the commit, so that pushed commits always carry the memory update with them (collaboration consistency).

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

## Memory Update Paths

<!-- generated-from: core/global_workflow_standard.md §1 · §3 · §8 · §11 — do not edit this block directly; edit the standard document and regenerate. -->

- Restore session-start baseline: `wk session-start`
- Register / update a task: `wk backlog-update`
- Sync affected documents (advisory): `wk doc-sync`
- Regenerate state.json at session close: `wk refresh-state`

- When the handoff's `in_progress` / `blocked` lists are empty, leave an **empty bullet `-`**. Prose there is parsed as a work item.
- Entries in the handoff's recently-completed list start with `TASK-` and never exceed 10.
- A backlog task's `status` is one of `planned` / `in_progress` / `blocked` / `done`.
- `state.json` is a **generated artifact** — never hand-edit it. The SSOT is `backlog/tasks/` plus `session_handoff.md`; regenerate with `wk refresh-state` at session close.
- `session_handoff.md` and the backlog are **inputs to the state.json generator** — writing outside the format silently corrupts state.json.
