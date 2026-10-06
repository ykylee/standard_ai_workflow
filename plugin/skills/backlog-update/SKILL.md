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
5. **Plan before you build** — record the plan in the task's `## 🧭 Plan` section with
   `--plan-file` (files that change), `--plan-step` (order of work, citing the completion
   criteria), `--plan-risk`, and `--plan-proof` (what will prove it is done). Plan fields
   merge on update; when the plan changes, replace with `--replace-field plan_files` etc.
6. **roadmap gate** (ADR-027 §6) — when the project has
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
