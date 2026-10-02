---
name: backlog-update
description: |
  [KO] 표준 AI 워크플로우 백로그 갱신 — 오늘 날짜 backlog 에 task 를 등록/갱신하고 PURPOSE.md 제외 영역과 겹치면 scope creep 을 경고한다.
  [EN] Standard AI workflow backlog update — register or update a task in today's daily backlog and warn on scope creep when the change overlaps a PURPOSE.md excluded area. Use when picking up new work or updating progress on a tracked task.
---

# backlog-update

## Role

Register or update today's work in `ai-workflow/memory/active/<branch>/backlog/<YYYY-MM-DD>.md`
and `./tasks/<TASK-ID>.md`.

## Procedure

1. Create today's backlog file if it does not exist; otherwise merge into the existing entries.
2. Use only the four status values `planned` / `in_progress` / `blocked` / `done`.
3. **in-scope check** — compare `task_brief` and the affected documents against the
   excluded areas in `PURPOSE.md` §3; on overlap, leave a one-line scope-creep warning.
   Without `PURPOSE.md`, proceed advisory-only with no warning.
4. State the priority, owner, and completion criteria.
5. **roadmap gate** (ADR-027 §6) — when the project has
   `ai-workflow/memory/active/roadmap/`, creating a task **requires**
   `--wbs M-NNN/WBS-N.N` (a leaf of the roadmap; the SDLC-order and done-milestone
   gates apply). Off-roadmap work is declared, never slipped through:
   `--wbs exempt --wbs-exempt-reason "<why>"` — the declaration lands in the task
   frontmatter and is counted in `roadmap_state.json`. Projects without a roadmap
   are unaffected.

## Usage

```bash
python -m workflow_kit backlog-update --help
```

When not changing the status, omit `--status` — leaving it unset means "do not change it"
and the existing status is preserved.

## Memory Update Paths

<!-- generated-from: core/global_workflow_standard.md §1 · §3 · §8 · §11 — do not edit this block directly; edit the standard document and regenerate. -->

- Restore session-start baseline: `python -m workflow_kit session-start`
- Register / update a task: `python -m workflow_kit backlog-update`
- Sync affected documents (advisory): `python -m workflow_kit doc-sync`
- Regenerate state.json at session close: `python -m workflow_kit refresh-state`
- Roll off handoff §1 baselines when over cap: `python -m workflow_kit rollover-baselines`
- Roll off handoff §5 accumulated notes when over budget: `python -m workflow_kit rollover-handoff-notes`
- Propose memory_index promotion candidates at close (advisory, no write): `python -m workflow_kit suggest-memory-entries`
- Relay working state across a context compaction (skill + hooks): `python -m workflow_kit compact-checkpoint`

- Run these with the Python interpreter that has `workflow_kit` installed — `python` on Windows, usually `python3` on macOS / Linux. Do not call a `wk` executable instead: on Windows it is an unsigned per-install launcher that reputation-based antivirus blocks.
- When the handoff's `in_progress` / `blocked` lists are empty, leave an **empty bullet `-`**. Prose there is parsed as a work item.
- Entries in the handoff's recently-completed list start with `TASK-` and never exceed 10.
- A backlog task's `status` is one of `planned` / `in_progress` / `blocked` / `done`.
- `state.json` is a **generated artifact** — never hand-edit it. The SSOT is `backlog/tasks/` plus `session_handoff.md`; regenerate with `python -m workflow_kit refresh-state` at session close.
- Handoff §1 baseline lines have a cap. When it is exceeded, **move** the excess with `python -m workflow_kit rollover-baselines` — never delete them by hand. That prose exists nowhere else, unlike the recently-done list whose SSOT is `backlog/tasks/`.
- Handoff §5 accumulated sections (everything outside the declared current-section list) have a byte budget. When it is exceeded, **move** the oldest with `python -m workflow_kit rollover-handoff-notes` — rules go to `lessons.md`, other notes to `sessions/`.
- `session_handoff.md` and the backlog are **inputs to the state.json generator** — writing outside the format silently corrupts state.json.
