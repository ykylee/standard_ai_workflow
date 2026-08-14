---
name: doc-sync
description: 표준 AI 워크플로우 문서 동기화 — 변경된 파일에서 영향 문서 후보를 뽑고 wiki index 기준 갱신 포인트를 advisory 로 제안한다.
---

# doc-sync

## 역할

변경된 파일에서 영향 문서 후보를 뽑고, 갱신 포인트를 **advisory 로** 제안한다.
자동 반영하지 않는다.

## 절차

1. 현재 변경된 파일 목록에서 영향 문서 후보를 식별한다.
2. `ai-workflow/wiki/index.md` 의 anchor 카탈로그와 대조한다.
3. 후보별로 경로 + 1줄 요약 + confidence (high / medium / low) 를 보고한다.
4. 새 concept / decision / pattern 페이지가 필요한지 판단해 제안한다.

## 실행

```bash
wk doc-sync --help
```

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
