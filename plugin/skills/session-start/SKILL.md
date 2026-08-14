---
name: session-start
description: |
  [KO] 표준 AI 워크플로우 세션 시작 — state.json + session_handoff.md + backlog 로 현재 기준선을 복원하고 다음 작업 후보를 보고한다.
  [EN] Standard AI workflow session start — restore the current baseline from state.json + session_handoff.md + backlog and report the next candidate tasks. Use when beginning a new session or resuming work in a workflow_kit project.
---

# session-start

## Role

Restore the current baseline from `ai-workflow/memory/active/<branch>/` and report the
next candidate tasks.

## Procedure

1. `state.json` — the current baseline (`latest_backlog_path`, in-progress / blocked / recently-done lists)
2. `session_handoff.md` — what the previous session handed over
3. `backlog/<YYYY-MM-DD>.md` — the current task list
4. `docs/PROJECT_PROFILE.md` — project metadata
5. (if present) `ai-workflow/memory/active/PURPOSE.md` — directional intent

After reading, report in Korean only: **a one-line baseline summary, 3–5 next-task
candidates, and the recommended next action.** No intermediate reasoning, repeated
summaries, or self-explanation.

If `state.json` or `PURPOSE.md` is absent, do not treat it as a failure — *skip gracefully*
and offer to scaffold it.

## Usage

```bash
wk session-start --help
```

If `wk` is missing, do not skip silently — report the installation
guidance and stop (`INSTALLATION_AND_USAGE.md` §3).

## Memory Update Paths

<!-- generated-from: core/global_workflow_standard.md §1 · §3 · §8 · §11 — do not edit this block directly; edit the standard document and regenerate. -->

- Restore session-start baseline: `wk session-start`
- Register / update a task: `wk backlog-update`
- Sync affected documents (advisory): `wk doc-sync`
- Regenerate state.json at session close: `wk refresh-state`
- Roll off handoff §1 baselines when over cap: `wk rollover-baselines`

- When the handoff's `in_progress` / `blocked` lists are empty, leave an **empty bullet `-`**. Prose there is parsed as a work item.
- Entries in the handoff's recently-completed list start with `TASK-` and never exceed 10.
- A backlog task's `status` is one of `planned` / `in_progress` / `blocked` / `done`.
- `state.json` is a **generated artifact** — never hand-edit it. The SSOT is `backlog/tasks/` plus `session_handoff.md`; regenerate with `wk refresh-state` at session close.
- Handoff §1 baseline lines have a cap. When it is exceeded, **move** the excess with
- `session_handoff.md` and the backlog are **inputs to the state.json generator** — writing outside the format silently corrupts state.json.
