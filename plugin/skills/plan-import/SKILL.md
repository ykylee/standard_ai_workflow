---
name: plan-import
description: |
  [KO] 표준 AI 워크플로우 계획 응답 반영 — 받은편지함의 계획 응답을 자격 판정해 보관으로 옮기고 task 의 결정 상태를 다시 계산한다.
  [EN] Standard AI workflow plan import — check the plan responses waiting in the branch inbox, archive the eligible ones and recompute the task's decision states. Use when session-start or backlog-update reports pending plan responses, or before closing a task that has decisions.
---

# plan-import

## Role

Apply the owner's answers to a task plan (ADR-031). A task's `Decisions` stay **open** until
the owner answers them: a default is not consent. Answers arrive as response files in the
branch memory inbox (`plan_responses/inbox/`); this command checks each one, moves the
eligible ones into the archive, recomputes every decision state and records one line in the
task's `Progress`.

## Procedure

1. Look first — the default is a dry run and writes nothing:

   ```bash
   python -m workflow_kit plan-import --task <TASK-ID>
   ```

   Each response reports `eligible` or the first failed stage (0–6) with the reason. A
   response for an older plan (stage 4) or from a non-approver (stage 5) is **not** applied.
2. Apply:

   ```bash
   python -m workflow_kit plan-import --task <TASK-ID> --apply
   ```

   If it reports `import_busy`, another import holds the inbox — run it again; nothing was
   written.
3. Read the result. `disputed` means two approvers disagree, or a response contradicts an
   answer recorded in conversation — **do not pick a side yourself**; ask the owner, then
   record the answer with `backlog-update --decision-state D<n>=answered:<value>`.
   `unopened` means the owner submitted without opening that decision — it is still open.
4. A response that should not count (wrong plan, sent by mistake) is set aside, never deleted:

   ```bash
   python -m workflow_kit plan-import --discard <file> --reason "<why>" --apply
   ```

Comments in a response are not applied automatically — read them and decide with the owner.
A task with open decisions or pending inbox responses cannot move to `done`.

## Usage

```bash
python -m workflow_kit plan-import --help
python -m workflow_kit plan-status --task <TASK-ID> --format md
```

The second command prints the per-claim table to attach to a verification report.

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
- Apply plan responses: `python -m workflow_kit plan-import`

- Run them with the Python that has `workflow_kit` installed (`python` on Windows, usually `python3` elsewhere) — not a `wk` executable, which Windows antivirus blocks.
- Empty handoff `in_progress` / `blocked` lists hold an **empty bullet `-`** — prose there is parsed as a work item.
- Handoff recently-completed entries start with `TASK-`, at most 10.
- `state.json` is a **generated artifact** — never hand-edit it; regenerate with `refresh-state` (sources: `backlog/tasks/` + `session_handoff.md`).
- Over the handoff §1 baseline cap, **move** lines with `rollover-baselines` — never delete them.
- Over the handoff §5 notes budget, **move** the oldest with `rollover-handoff-notes` (rules → `lessons.md`, notes → `sessions/`).
- Write the handoff and backlog only in their format — they feed the state.json generator.
