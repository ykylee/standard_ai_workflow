# Memory-Freeze Skill (R8)

- Purpose: at session close, freeze the mutable state under `ai-workflow/memory/active/` into `ai-workflow/memory/archive/YYYY-MM-DD/`. Implements rule R8 (Memory Raw Freeze).
- Scope: the freeze transition, the `.frozen` marker, atomic rename, archive integrity
- Audience: AI agent, workflow designer
- Status: stable (v1.0.1+, execution-contract smoke 6/6 — `../../tests/check_memory_freeze_skill.py`)
- Last updated: 2026-08-14
- Related: `../../.omo/plans/v0.6.1-plus-memory-raw-ops-design.md` §4 R8, `../../MEMORY_GOVERNANCE.md`

## 1. Purpose

At session close, freeze the current mutable workflow state in `active/` into an immutable
`archive/YYYY-MM-DD/`. After the freeze, `archive/` is a read-only raw source (R9), and that
freeze is what wiki-ingest reads.

## 2. Linked specs

- Rule R8: `v0.6.1-plus-memory-raw-ops-design.md` §4 R8
- R10 Freeze Lint: `../../tests/check_memory_freeze_lint.py`

## 3. Usage

```bash
python3 scripts/run_memory_freeze.py
```

## 4. Expected input

- `--active-root` (default: `ai-workflow/memory/active/`)
- `--archive-root` (default: `ai-workflow/memory/archive/`)
- `--freeze-date` (default: today, ISO `YYYY-MM-DD`)

## 5. Expected output

- `archive_path`: path of the archive directory that was created
- `frozen_files`: list of files that were frozen
- `file_count`: number of files frozen
- `status`: `success` / `skipped` (that date is already frozen) / `error`

## 6. Permission boundary

- read: every file under `active/`
- write: create `archive/YYYY-MM-DD/` plus the `.frozen` marker
- NEVER: delete files in `active/` (freeze = copy, NOT move)
- NEVER: modify an existing freeze under `archive/` (immutable)

## 7. Freeze protocol

1. `mkdir archive/YYYY-MM-DD/`
2. Copy every `.md` and `.json` file under `active/` into `archive/YYYY-MM-DD/`
3. Write the `.frozen` marker (YAML: `frozen_at`, `source`, `files`)
4. Print the archive path and the file list to stdout
5. If that date is already frozen, skip — an existing freeze is immutable

## v0.6.5 Stage Completion

From v0.6.5 on, this skill's output carries the `stage_completion` field of the v0.6.4
[Stage Gate Pattern](../../../core/stage_gate_pattern.md).

| Field | Value |
|---|---|
| `stage_name` | `memory-freeze` |
| `next_stage` | `(workflow end)` |
| `approval_actor` | `user`, mandatory (affects state documents) |
| `approval_timestamp` | ISO 8601 |

Full spec: [`core/stage_gate_pattern.md`](../../../core/stage_gate_pattern.md),
[`core/output_schema_guide.md §3.4`](../../../core/output_schema_guide.md).
