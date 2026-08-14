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
