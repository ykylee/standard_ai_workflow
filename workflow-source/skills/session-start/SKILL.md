# Session-Start Skill

- Purpose: describe the `session-start` skill and its implementation entry point.
- Scope: purpose, linked specs, expected input/output, permission boundary, implementation notes
- Audience: skill implementer, AI agent designer, operator
- Status: stable (promoted in v0.11.19)
- Last updated: 2026-08-14
- Related: `../../core/session_start_skill_spec.md`, `../../core/workflow_skill_catalog.md`, `../../core/workflow_agent_topology.md`

## 1. Purpose

At the start of a new session, read the handoff, the backlog, and the project profile, and
restore the current baseline as a structured summary.

## 2. Linked specs

- Full spec: [../../core/session_start_skill_spec.md](../../core/session_start_skill_spec.md)
- Catalog: [../../core/workflow_skill_catalog.md](../../core/workflow_skill_catalog.md)

## 3. Expected input

- `session_handoff_path`
- `work_backlog_index_path`
- `project_profile_path`
- Optionally `latest_backlog_path`, `changed_files`, `environment_hint`

## 4. Expected output

- `summary`
- `in_progress_items`
- `blocked_items`
- `latest_backlog_path`
- `next_documents`
- `recommended_next_action`
- `warnings`

## 5. Permission boundary

- Read-only by default
- Never modifies state documents directly
- Never re-adjudicates a `done`

## 6. Implementation notes

- When locating the latest backlog, prefer the backlog index.
- Conflicts between the handoff and the backlog are reported as warnings only.
- The project profile's document structure is the primary reference.

## 7. Usage

**`wk` is the only consumer-facing path** (canonical §11) — `skills/` ships in neither the
pip package nor the bootstrap bundle, so these paths must never be given to consumers
(TASK-021/027). The implementation lives in the distributed
`workflow-source/workflow_kit/tools/session_start.py`;
[scripts/run_session_start.py](./scripts/run_session_start.py) in this directory is a thin
in-repo development wrapper.

```bash
# inside a workspace, no arguments — PROJECT_PROFILE.md is discovered automatically (v1.1.7+)
wk session-start

# with explicit paths
wk session-start \
  --session-handoff-path examples/acme_delivery_platform/session_handoff.md \
  --work-backlog-index-path examples/acme_delivery_platform/work_backlog.md \
  --project-profile-path examples/acme_delivery_platform/PROJECT_PROFILE.md
```

- Prints a JSON summary to stdout.
- Finds the latest backlog from the index document when one exists, and otherwise (in the
  branch-scoped layout) by observing the daily backlog directory (v1.1.7+).

## 8. Current status

- A read-only execution prototype exists
- Reads the handoff, backlog index, and project profile and prints a structured summary of
  the current state
- Provides a conservative, warning-based summary only; never edits documents

## 9. v0.11.22+ Phase 3b — memory_index retrieval wiring (opt-in)

session-start can *optionally* consume the ADR-005 memory_index retrieval 3-tuple
(cue exact → BM25 fallback → linked expansion) and emit it in the output field
`memory_index_query_output`. No disk changes (read-only retrieval).

### Usage

```bash
wk session-start \
  --session-handoff-path <handoff.md> \
  --work-backlog-index-path <work_backlog.md> \
  --project-profile-path <PROJECT_PROFILE.md> \
  --memory-index-dir <workspace>/ai-workflow/memory/active/memory_index \
  --memory-query-tokens "adr,memora,retrieval"
```

Since v0.15.21 both flags are **overrides**. Even without them, retrieval activates
automatically when the standard workspace directory
`ai-workflow/memory/active/memory_index` exists. Query tokens are then **derived from
context** — the `current_axis` in `state.json` plus recent done titles; if derivation fails
it falls back to `session,handoff,workflow` and records the origin in the telemetry field
`query_source` (ADR-006 W-2, v1.1.5+). That emits telemetry source `session-start`
(Phase 13 AC2 source diversity ≥ 4). If the memory_index directory is absent, it is a
zero-risk skip (existing callers unaffected). Passing the flags overrides directory and tokens.

### Additional output field

`SessionStartOutput.memory_index_query_output` (optional, `dict[str, Any] | None`):

- `selected_ids` — entry ids returned by retrieval
- `cue_hits` / `bm25_hits` / `expansion_hits` / `expansion_depth_used`
- `source_context` — call info (workspace_root / memory_index_dir)

The field is *optional* so existing callers do not break — `None` when absent
(backward compatible).

### Follow-up

- Wiring for other skills such as doc-sync and backlog-update (Phase 3c/3d, separate releases).
- ADR-006 retrospective (after Phase 3c/d).

## Read next

- Skills hub: [../README.md](../README.md)
- Full spec: [../../core/session_start_skill_spec.md](../../core/session_start_skill_spec.md)
- ADR-005 memory_index: [../../../docs/architecture/ADR-005-memora-inspired-memory-index.md](../../../docs/architecture/ADR-005-memora-inspired-memory-index.md)
