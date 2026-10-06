---
name: session-end
description: |
  [KO] 표준 AI 워크플로우 세션 종료 — handoff 와 backlog 를 갱신하고 state.json 을 재생성해 다음 세션이 그대로 이어받게 남긴다.
  [EN] Standard AI workflow session end — update handoff and backlog, then regenerate state.json so the next session can resume directly. Use when closing a session in a workflow_kit project.
---

# session-end

## Role

Close the session, leaving the state so the next session can pick it up directly.

## Order

Close a session in the order **update memory → commit → push** — the memory update rides in the pushed commit, never in a later turn.

## Procedure

1. Update `session_handoff.md` — current baseline, in-progress / blocked / recently-done lists.
   If a compaction checkpoint exists (`.compact/checkpoint.json` in the branch memory directory),
   carry over the lines worth keeping, then remove it with `python -m workflow_kit compact-checkpoint --clear` — the
   checkpoint is session-local and never committed.
2. Bring the task statuses in today's backlog in line with the actual results (`planned` / `in_progress` / `blocked` / `done`).
3. **Regenerate** `state.json` (never hand-edit it — see the §11 contract below).
4. Make sure the updates from 1–3 land in the **same commit**, then push.

## Usage

```bash
python -m workflow_kit refresh-state
```

If no Python interpreter can import `workflow_kit` (`python -m workflow_kit --help` fails with
`No module named workflow_kit`), do not skip silently — report the installation
guidance and stop (`INSTALLATION_AND_USAGE.md` §3). A hand-written `state.json` that was
never regenerated diverges from its input documents.

## Memory Update Paths

<!-- generated-from: core/global_workflow_standard.md §1 · §3 · §8 · §11 — do not edit this block directly; edit the standard document and regenerate. -->

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
