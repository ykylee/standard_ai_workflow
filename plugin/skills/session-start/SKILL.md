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

When `ai-workflow/memory/active/roadmap/` exists, the tool output carries
`roadmap_context` (ADR-027): the current milestone, its SDLC phase, progress, and the
next WBS candidates. Fold it into the baseline report — and when the current phase is
concept / requirements / design with its declared deliverable still missing, recommend
filling that deliverable first (the default onboarding order is concept → requirements →
design → implementation). No roadmap → `present=false`; skip silently.

`python -m workflow_kit session-start` now checks the harness entry points on **every** start: files declared
by the harness registry but missing on disk are created at the current kit version, and
files that exist but carry an older marker are **reported, never overwritten** — an
undeclared local edit must not disappear just because a session opened. The report lands
in `warnings`; relay it. Run `python -m workflow_kit ensure-entrypoints` to inspect the same picture on demand,
or `--apply` to fill only what is missing.

## Usage

```bash
python -m workflow_kit session-start --help
```

If no Python interpreter can import `workflow_kit` (`python -m workflow_kit --help` fails with
`No module named workflow_kit`), do not skip silently — report the installation
guidance and stop (`INSTALLATION_AND_USAGE.md` §3).

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
