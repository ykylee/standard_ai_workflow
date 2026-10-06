---
name: doc-sync
description: |
  [KO] 표준 AI 워크플로우 문서 동기화 — 변경된 파일에서 영향 문서 후보를 뽑고 wiki index 기준 갱신 포인트를 advisory 로 제안한다.
  [EN] Standard AI workflow document sync — collect affected-document candidates from changed files and propose advisory update points based on the wiki index. Use after code or document edits to keep wiki / handoff / PROJECT_PROFILE consistent.
---

# doc-sync

## Role

Derive affected-document candidates from the changed files and propose update points
**as advisory**. Never apply them automatically.

## Procedure

1. Identify affected-document candidates from the current changed-file list.
2. Compare against the anchor catalog in `ai-workflow/wiki/index.md`.
3. Report each candidate with its path, a one-line summary, and a confidence (high / medium / low).
4. Judge whether a new concept / decision / pattern page is needed and propose it.

## Usage

```bash
python -m workflow_kit doc-sync --help
```

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
