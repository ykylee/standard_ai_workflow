---
name: doc-sync
description: |
  [KO] 표준 AI 워크플로우 문서 동기화 — 변경된 파일에서 영향 문서 후보를 뽑고 wiki index 기준 갱신 포인트를 advisory 로 제안한다.
  [EN] Standard AI workflow document sync — collect affected-document candidates from changed files and propose advisory update points based on the wiki index. Use after code or document edits to keep wiki / handoff / PROJECT_PROFILE consistent.
---

# doc-sync

## Role

Derive affected-document candidates from the changed files and propose update points
**as advisory**. Never apply them automatically.

## Procedure

1. Identify affected-document candidates from the current changed-file list.
2. Compare against the anchor catalog in `ai-workflow/wiki/index.md`.
3. Report each candidate with its path, a one-line summary, and a confidence (high / medium / low).
4. Judge whether a new concept / decision / pattern page is needed and propose it.

## Usage

```bash
wk doc-sync --help
```

## Memory Update Paths

<!-- generated-from: core/global_workflow_standard.md §1 · §3 · §8 · §11 — do not edit this block directly; edit the standard document and regenerate. -->

- Restore session-start baseline: `wk session-start`
- Register / update a task: `wk backlog-update`
- Sync affected documents (advisory): `wk doc-sync`
- Regenerate state.json at session close: `wk refresh-state`
- Roll off handoff §1 baselines when over cap: `wk rollover-baselines`
- Propose memory_index promotion candidates at close (advisory, no write): `wk suggest-memory-entries`

- When the handoff's `in_progress` / `blocked` lists are empty, leave an **empty bullet `-`**. Prose there is parsed as a work item.
- Entries in the handoff's recently-completed list start with `TASK-` and never exceed 10.
- A backlog task's `status` is one of `planned` / `in_progress` / `blocked` / `done`.
- `state.json` is a **generated artifact** — never hand-edit it. The SSOT is `backlog/tasks/` plus `session_handoff.md`; regenerate with `wk refresh-state` at session close.
- Handoff §1 baseline lines have a cap. When it is exceeded, **move** the excess with `wk rollover-baselines` — never delete them by hand. That prose exists nowhere else, unlike the recently-done list whose SSOT is `backlog/tasks/`.
- `session_handoff.md` and the backlog are **inputs to the state.json generator** — writing outside the format silently corrupts state.json.
