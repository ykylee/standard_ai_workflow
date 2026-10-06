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
   python -m workflow_kit compact-checkpoint --note \
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
python -m workflow_kit compact-checkpoint --help
```

The checkpoint lives in `.compact/` under the branch memory directory, ignores itself in git,
and is removed at session end (`python -m workflow_kit compact-checkpoint --clear`). It never touches `session_handoff.md`
or `state.json`.

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
