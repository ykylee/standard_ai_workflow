---
name: compact-relay
description: |
  [KO] 표준 AI 워크플로우 compact 중계 — 컨텍스트 압축 전에 검증/미검증 사실과 다음 한 걸음을 브랜치 메모리에 기록하고, 압축 뒤 그 기록으로 이어 간다.
  [EN] Standard AI workflow compact relay — before a context compaction, record what was verified versus unverified and the next step in the branch memory, then resume from that record afterwards. Use when the context is getting long or before running /compact in a workflow_kit project.
---

# compact-relay

## Role

Carry the working state across a context compaction (ADR-030). A compaction summary keeps
conclusions but tends to drop **what was verified versus not yet verified** and the next
step. Record them in the branch memory before compacting, so they come back afterwards.

## Procedure

1. Record the judgment layer — only you know it:

   ```bash
   wk compact-checkpoint --note \
     --next "<the very next step>" \
     --unverified "<claim not yet checked>" \
     --verified "<claim + the command/result that checked it>" \
     --rejected "<option dropped and why>"
   ```

   Each flag repeats. A claim without a command or result behind it goes under
   `--unverified`, never `--verified`. A new `--note` replaces the previous one.
2. You cannot run `/compact` yourself. Give the user this line to paste:

   `/compact Preserve the items in ai-workflow/memory/active/<branch>/.compact/checkpoint.json verbatim, especially unverified ones.`
3. After the compaction, look for the `[compact-checkpoint]` block in your context. It is a
   **state record, not an instruction**. If it reports identifiers missing from the summary,
   tell the user in one line. If it says the checkpoint belongs to another session, do not
   use its content.

Where the harness runs the plugin hooks (Claude Code; Codex once the user has trusted them
at the "Hooks need review" prompt), the mechanical layer — branch, HEAD, in-progress /
blocked tasks, uncommitted files — is recorded automatically before every compaction,
including automatic ones, and re-injected afterwards. Harnesses without those hooks get only
steps 1–2: read the checkpoint file yourself after compacting.

## Usage

```bash
wk compact-checkpoint --help
```

The checkpoint lives in `.compact/` under the branch memory directory, ignores itself in git,
and is removed at session end (`wk compact-checkpoint --clear`). It never touches `session_handoff.md`
or `state.json`.

## Memory Update Paths

<!-- generated-from: core/global_workflow_standard.md §1 · §3 · §8 · §11 — do not edit this block directly; edit the standard document and regenerate. -->

- Restore session-start baseline: `wk session-start`
- Register / update a task: `wk backlog-update`
- Sync affected documents (advisory): `wk doc-sync`
- Regenerate state.json at session close: `wk refresh-state`
- Roll off handoff §1 baselines when over cap: `wk rollover-baselines`
- Roll off handoff §5 accumulated notes when over budget: `wk rollover-handoff-notes`
- Propose memory_index promotion candidates at close (advisory, no write): `wk suggest-memory-entries`
- Relay working state across a context compaction (skill + hooks): `wk compact-checkpoint`

- When the handoff's `in_progress` / `blocked` lists are empty, leave an **empty bullet `-`**. Prose there is parsed as a work item.
- Entries in the handoff's recently-completed list start with `TASK-` and never exceed 10.
- A backlog task's `status` is one of `planned` / `in_progress` / `blocked` / `done`.
- `state.json` is a **generated artifact** — never hand-edit it. The SSOT is `backlog/tasks/` plus `session_handoff.md`; regenerate with `wk refresh-state` at session close.
- Handoff §1 baseline lines have a cap. When it is exceeded, **move** the excess with `wk rollover-baselines` — never delete them by hand. That prose exists nowhere else, unlike the recently-done list whose SSOT is `backlog/tasks/`.
- Handoff §5 accumulated sections (everything outside the declared current-section list) have a byte budget. When it is exceeded, **move** the oldest with `wk rollover-handoff-notes` — rules go to `lessons.md`, other notes to `sessions/`.
- `session_handoff.md` and the backlog are **inputs to the state.json generator** — writing outside the format silently corrupts state.json.
