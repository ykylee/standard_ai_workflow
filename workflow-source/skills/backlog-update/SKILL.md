# Backlog-Update Skill

- Purpose: describe the `backlog-update` skill and its implementation entry point.
- Scope: purpose, linked specs, expected input/output, permission boundary, implementation notes
- Audience: skill implementer, AI agent designer, operator
- Status: stable (promoted in v0.11.20)
- Last updated: 2026-08-14
- Related: `../../core/backlog_update_skill_spec.md`, `../../core/workflow_skill_catalog.md`, `../../core/workflow_agent_topology.md`

## 1. Purpose

Create a new task entry in the dated backlog, or draft a status update for an existing one.

## 2. Linked specs

- Full spec: [../../core/backlog_update_skill_spec.md](../../core/backlog_update_skill_spec.md)
- Catalog: [../../core/workflow_skill_catalog.md](../../core/workflow_skill_catalog.md)

## 3. Expected input

- `project_profile_path`
- `task_brief`
- Conditionally `daily_backlog_path`, `target_date`, `task_id`
- Optionally `work_backlog_index_path`, `session_handoff_path`, `owner`, `affected_documents`, `validation_result`
- `kind` (`release` | `session` | `generic`, default `generic`) — both the `kind` in the task
  SSOT frontmatter and the `[kind]` marker in the daily index

## 4. Expected output

- `operation_type`
- `target_backlog_path`
- `task_id`
- `draft_entry`
- `status_recommendation`
- `fields_requiring_confirmation`
- `warnings`

### 4.1 `--apply` output layout (append-only since v0.14.0)

- `backlog/tasks/TASK-<date>[-<branch-slug>]-<NNN>.md` — **the SSOT for the body**.
  Six frontmatter keys are required (`id` / `status` / `created_at` / `source_anchor` /
  `source_path` / `kind`).
- `backlog/<date>.md` — **a set of links**. The task body is never inlined. Re-applying the
  same task replaces only that block (no duplicates, no full rewrite).
- No `.bak` files are created (that concept was dropped in v0.15.0).

`MEMORY_GOVERNANCE.md` §2 is canonical for this layout, and
`tests/check_backlog_update_layout.py` compares the output against it.

## 5. Permission boundary

- Centered on producing drafts and update proposals
- **Writes nothing to the repository without `--apply`** (including state-cache regeneration)
- Never confirms `done` without verification
- Never updates a task that does not exist as if it did
- With `--apply`, may directly update the dated backlog, the backlog index, and the handoff
  status lists — within a narrow scope

## 6. Implementation notes

- Keep creation and update strictly separate.
- Resolve backlog paths through the project profile.
- Leave follow-up handoff/index updates as notes and handle them as a separate step.
- After updating backlog or handoff status, regenerating `state.json` automatically is the
  expected default whenever the source-of-truth documents are in place.

## 7. Usage (v0.11.20 stable)

**`wk` is the only consumer-facing path** (canonical §11) — `skills/` is not shipped. The
implementation lives in `workflow-source/workflow_kit/tools/backlog_update.py`;
[scripts/run_backlog_update.py](./scripts/run_backlog_update.py) in this directory is a
thin in-repo development wrapper.

```bash
# update an existing entry (prints the JSON draft only)
wk backlog-update \
  --project-profile-path examples/acme_delivery_platform/PROJECT_PROFILE.md \
  --daily-backlog-path examples/acme_delivery_platform/backlog/2026-04-18.md \
  --mode update \
  --task-id TASK-021 \
  --task-name "Document the delivery-status sync failure runbook" \
  --task-brief "Checked how the runbook and handoff reflect it." \
  --status in_progress

# --apply writes through to backlog / index / handoff
wk backlog-update \
  --project-profile-path examples/acme_delivery_platform/PROJECT_PROFILE.md \
  --daily-backlog-path examples/acme_delivery_platform/backlog/2026-04-18.md \
  --work-backlog-index-path examples/acme_delivery_platform/work_backlog.md \
  --session-handoff-path examples/acme_delivery_platform/session_handoff.md \
  --mode update \
  --task-id TASK-021 \
  --task-name "Document the delivery-status sync failure runbook" \
  --task-brief "Moved back to blocked while verification is pending." \
  --status blocked \
  --apply
```

- Without `--apply`, the prototype only prints the JSON draft and does not touch backlog files.
- With `--apply`, the draft is written into the target backlog file and, where possible, the
  backlog index and handoff status lists are synced as well.

## 8. Current status

- A read-only draft-generation prototype exists
- Distinguishes creating a new entry from updating an existing one, and emits the draft
  entry plus warnings
- Never confirms `done` automatically without a verification result

## 9. v0.11.22+ Phase 3d — memory_index retrieval wiring (opt-in)

backlog-update can *optionally* consume the ADR-005 memory_index retrieval 3-tuple
(cue exact → BM25 fallback → linked expansion) and emit it in the output field
`memory_index_query_output`. No disk changes (read-only retrieval). Same pattern as
session-start and doc-sync.

### Usage

```bash
wk backlog-update \
  --project-profile-path <PROJECT_PROFILE.md> \
  --task-name "<name>" --task-brief "<brief>" \
  --memory-index-dir <ws>/ai-workflow/memory/active/memory_index \
  --memory-query-tokens "adr,memora,retrieval"
```

Since v0.15.21 both flags are **overrides**. Even without them, retrieval activates
automatically when the standard workspace directory
`ai-workflow/memory/active/memory_index` exists. Query tokens are then **derived from
context** — the `current_axis` in `state.json` plus recent done titles; if derivation fails
it falls back to `backlog,task,workflow` and records the origin in the telemetry field
`query_source` (ADR-006 W-2, v1.1.5+). That emits telemetry source `backlog-update`
(Phase 13 AC2 source diversity ≥ 4). If the memory_index directory is absent, it is a
zero-risk skip (existing callers unaffected). Passing the flags overrides directory and tokens.

### Additional output field

`BacklogUpdateOutput.memory_index_query_output` (optional, `dict[str, Any] | None`):

- `selected_ids` / `cue_hits` / `bm25_hits` / `expansion_hits` / `expansion_depth_used`
- `source_context`

`None` when absent (backward compatible).

### Follow-up

- The v0.11.22 release itself (Phases 1–3d bundled).
- ADR-006 retrospective (after Phase 3d).

## Read next

- Skills hub: [../README.md](../README.md)
- Full spec: [../../core/backlog_update_skill_spec.md](../../core/backlog_update_skill_spec.md)
- ADR-005 memory_index: [../../../docs/architecture/ADR-005-memora-inspired-memory-index.md](../../../docs/architecture/ADR-005-memora-inspired-memory-index.md)
