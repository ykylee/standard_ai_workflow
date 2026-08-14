---
name: session-end
description: 표준 AI 워크플로우 세션 종료 — handoff 와 backlog 를 갱신하고 state.json 을 재생성해 다음 세션이 그대로 이어받게 남긴다.
---

# session-end

## Role

Close the session, leaving the state so the next session can pick it up directly.

## Order

Close a session in the order **update memory → commit → push**. Do not split the memory update into a separate turn after the commit, so that pushed commits always carry the memory update with them (collaboration consistency).

## Procedure

1. Update `session_handoff.md` — current baseline, in-progress / blocked / recently-done lists.
2. Bring the task statuses in today's backlog in line with the actual results (`planned` / `in_progress` / `blocked` / `done`).
3. **Regenerate** `state.json` (never hand-edit it — see the §11 contract below).
4. Make sure the updates from 1–3 land in the **same commit**, then push.

## Usage

```bash
wk refresh-state
```

If `wk` is missing, do not skip silently — report the installation
guidance and stop (`INSTALLATION_AND_USAGE.md` §3). A hand-written `state.json` that was
never regenerated diverges from its input documents.

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
