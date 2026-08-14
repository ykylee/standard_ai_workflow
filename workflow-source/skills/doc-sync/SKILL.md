# Doc-Sync Skill

- Purpose: describe the `doc-sync` skill and its implementation entry point.
- Scope: purpose, linked specs, expected input/output, permission boundary, implementation notes
- Audience: skill implementer, AI agent designer, operator
- Status: stable (promoted in v0.11.19)
- Last updated: 2026-08-14
- Related: `../../core/doc_sync_skill_spec.md`, `../../core/workflow_skill_catalog.md`, `../../core/workflow_agent_topology.md`, `../../core/workflow_mcp_candidate_catalog.md`

## 1. Purpose

From a list of changed files, recommend the baseline documents, hub documents, and state
documents that should be checked or updated alongside them, and record that in
`session_handoff.md`.

## 2. Linked specs

- Full spec: [../../core/doc_sync_skill_spec.md](../../core/doc_sync_skill_spec.md)
- Catalog: [../../core/workflow_skill_catalog.md](../../core/workflow_skill_catalog.md)

## 3. Expected input

- `project_profile_path`
- `changed_files`
- Optionally `baseline_documents`, `hub_documents`, `session_handoff_path`, `latest_backlog_path`, `change_summary`

## 4. Expected output

- `impacted_documents`
- `hub_update_candidates`
- `stale_warnings`
- `reasoning_notes`
- `recommended_review_order`
- `follow_up_actions`

## 5. Permission boundary

- Read and recommend; writes only in the `--apply` step
- With `--apply`, may modify only specific sections of `session_handoff.md`
- Never edits the project's own documents automatically

## 6. Implementation notes

- Split changed files into documents and non-documents.
- Treat runbooks, the handoff, the backlog, and hub documents as distinct candidate groups.
- Keep "this hub may be stale" and "the result may not have been recorded" as separate warnings.
- Treat `ai-workflow/` as the workflow meta layer and exclude it from project document
  discovery by default.

## 7. Usage

**`wk` is the only consumer-facing path** (canonical §11) — `skills/` is not shipped. The
implementation lives in `workflow-source/workflow_kit/tools/doc_sync.py`;
[scripts/run_doc_sync.py](./scripts/run_doc_sync.py) in this directory is a thin
in-repo development wrapper.

- Inspect the recommendations:
```bash
wk doc-sync \
  --project-profile-path docs/PROJECT_PROFILE.md \
  --session-handoff-path ai-workflow/memory/active/sessions \
  --changed-file app/main.py
```
- Apply them:
```bash
wk doc-sync \
  --project-profile-path docs/PROJECT_PROFILE.md \
  --session-handoff-path ai-workflow/memory/active/sessions \
  --changed-file app/main.py \
  --apply
```

## 8. Current status

- Beta stage: read-oriented recommendations with limited write support
- `--apply` refreshes the `Read next` section of `session_handoff.md`
- Recommended `follow_up_actions` are appended to the handoff's operational notes
- Per-project document structure is interpreted through the project profile

## 9. v0.11.22+ Phase 3c — memory_index retrieval wiring (opt-in)

doc-sync can *optionally* consume the ADR-005 memory_index retrieval 3-tuple
(cue exact → BM25 fallback → linked expansion) and emit it in the output field
`memory_index_query_output`. No disk changes (read-only retrieval). Same pattern as
session-start.

### Usage

```bash
wk doc-sync \
  --project-profile-path <PROJECT_PROFILE.md> \
  --changed-file <path1> --changed-file <path2> \
  --memory-index-dir <ws>/ai-workflow/memory/active/memory_index \
  --memory-query-tokens "adr,memora,retrieval"
```

Since v0.15.21 both flags are **overrides**. Even without them, retrieval activates
automatically when the standard workspace directory
`ai-workflow/memory/active/memory_index` exists. Query tokens are then **derived from
context** — the `current_axis` in `state.json` plus recent done titles; if derivation
fails it falls back to `doc,sync,workflow` and records the origin in the telemetry field
`query_source` (ADR-006 W-2, v1.1.5+). That emits telemetry source `doc-sync`
(Phase 13 AC2 source diversity ≥ 4). If the memory_index directory is absent, it is a
zero-risk skip (existing callers unaffected). Passing the flags overrides directory and tokens.

### Additional output field

`DocSyncOutput.memory_index_query_output` (optional, `dict[str, Any] | None`):

- `selected_ids` / `cue_hits` / `bm25_hits` / `expansion_hits` / `expansion_depth_used`
- `source_context`

`None` when absent (backward compatible).

### Follow-up

- Wiring for the `backlog-update` skill (Phase 3d, separate release).
- ADR-006 retrospective (after Phase 3d).

## Read next

- Skills hub: [../README.md](../README.md)
- ADR-005 memory_index: [../../../docs/architecture/ADR-005-memora-inspired-memory-index.md](../../../docs/architecture/ADR-005-memora-inspired-memory-index.md)
- Full spec: [../../core/doc_sync_skill_spec.md](../../core/doc_sync_skill_spec.md)
