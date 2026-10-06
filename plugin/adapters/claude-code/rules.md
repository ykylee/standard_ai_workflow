# Standard AI workflow — always-on rules (injected by the plugin SessionStart hook)

## Working Principles

<!-- generated-from: core/global_workflow_standard.md §1 · §3 · §8 · §11 — do not edit this block directly; edit the standard document and regenerate. -->

- Read the state summary documents first, every session.
- Before starting work, state its purpose, scope, deliverables, and affected documents, and record the plan in the task file (files, order of work, risks, proof).
- Track work in the state documents with exactly one status: `planned`, `in_progress`, `blocked`, `done`.
- Never mark an unverified result as done.
- Before ending a session, leave a state summary the next session can resume from.
- With multiple agents: sync with the remote first, check what the others are doing, and pick work that does not overlap.
- Never decide irreversible actions alone — deleting or overwriting another agent's work needs the user's confirmation.
- Keep the shared standard thin; project-specific differences go in the project profile.

## Session Close Order

Close a session in the order **update memory → commit → push** — the memory update rides in the pushed commit, never in a later turn.

- Update before closing: `state.json`, `session_handoff.md`, the latest backlog

## Memory Update Paths

- Restore session-start baseline: `python -m workflow_kit session-start`
- Register / update a task: `python -m workflow_kit backlog-update`
- Sync affected documents (advisory): `python -m workflow_kit doc-sync`
- Regenerate state.json at session close: `python -m workflow_kit refresh-state`
- Roll off handoff §1 baselines over cap: `python -m workflow_kit rollover-baselines`
- Roll off handoff §5 notes over budget: `python -m workflow_kit rollover-handoff-notes`
- Propose memory_index entries at close (advisory): `python -m workflow_kit suggest-memory-entries`
- Relay working state across compaction: `python -m workflow_kit compact-checkpoint`

- Run them with the Python that has `workflow_kit` installed (`python` on Windows, usually `python3` elsewhere) — not a `wk` executable, which Windows antivirus blocks.
- Empty handoff `in_progress` / `blocked` lists hold an **empty bullet `-`** — prose there is parsed as a work item.
- Handoff recently-completed entries start with `TASK-`, at most 10.
- `state.json` is a **generated artifact** — never hand-edit it; regenerate with `refresh-state` (sources: `backlog/tasks/` + `session_handoff.md`).
- Over the handoff §1 baseline cap, **move** lines with `rollover-baselines` — never delete them.
- Over the handoff §5 notes budget, **move** the oldest with `rollover-handoff-notes` (rules → `lessons.md`, notes → `sessions/`).
- Write the handoff and backlog only in their format — they feed the state.json generator.
