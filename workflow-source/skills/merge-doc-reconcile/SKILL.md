# Merge-Doc-Reconcile Skill

- Purpose: describe the `merge-doc-reconcile` skill and its implementation entry point.
- Scope: purpose, linked specs, expected input/output, permission boundary, implementation notes
- Audience: skill implementer, AI agent designer, operator
- Status: stable (promoted in v0.11.20)
- Last updated: 2026-08-14
- Related: `../../core/merge_doc_reconcile_skill_spec.md`, `../../core/workflow_skill_catalog.md`, `../../core/workflow_agent_topology.md`

## 1. Purpose

After a merge, structure the state mismatches and re-confirmation points across the
handoff, the backlog, and hub documents so the follow-up cleanup is tractable, and refresh
`state.json`.

## 2. Linked specs

- Full spec: [../../core/merge_doc_reconcile_skill_spec.md](../../core/merge_doc_reconcile_skill_spec.md)
- Catalog: [../../core/workflow_skill_catalog.md](../../core/workflow_skill_catalog.md)

## 3. Expected input

- `project_profile_path`
- `merge_result_summary`
- Conditionally `session_handoff_path`, `work_backlog_index_path`, `latest_backlog_path`
- Optionally `hub_documents`, `changed_files`, `pre_merge_notes`, `validation_result`

## 4. Expected output

- `reconcile_targets`
- `state_conflicts`
- `reconfirmation_points`
- `draft_reconcile_notes`
- `recommended_review_order`
- `warnings`

## 5. Permission boundary

- Read-oriented reconciliation; writes only in the `--apply` step
- With `--apply`, appends reconciliation notes to `session_handoff.md` and regenerates `state.json`
- Never marks anything `done` or clears a blocker automatically — that needs human confirmation

## 6. Implementation notes

- Compare the handoff against the latest backlog first.
- For hub/index documents, focus on link validity and whether the structural description is current.
- Anything left unverified after the merge stays as a re-confirmation point.
- Treat `ai-workflow/` as the workflow meta layer and exclude it from the ordinary
  changed-file set by default.
- Once the handoff and backlog are reconciled, regenerating `state.json` automatically is
  the expected default whenever the source-of-truth documents are in place.

## 7. Usage

- Entry script: [scripts/run_merge_doc_reconcile.py](./scripts/run_merge_doc_reconcile.py)
- Inspect what needs reconciliation:
```bash
python3 skills/merge-doc-reconcile/scripts/run_merge_doc_reconcile.py \
  --project-profile-path docs/PROJECT_PROFILE.md \
  --session-handoff-path ai-workflow/memory/active/sessions \
  --merge-result-summary "feature branch merge"
```
- Apply the result:
```bash
python3 skills/merge-doc-reconcile/scripts/run_merge_doc_reconcile.py \
  --project-profile-path docs/PROJECT_PROFILE.md \
  --session-handoff-path ai-workflow/memory/active/sessions \
  --merge-result-summary "feature branch merge" \
  --apply
```

## 7. Wiki-specific conflict types (R7, v0.6.1+)

Merging wiki pages (`ai-workflow/wiki/`) yields four conflict types:

| Type | Description | Resolution |
|---|---|---|
| `line-conflict` | same line edited on both sides | reconcile-text (word-level OT) |
| `section-conflict` | same section edited on both sides | additive (R5, combine both) |
| `semantic-conflict` | the two sides contradict each other | LLM review required |
| `index-conflict` | `index.md` anchor collision | manual review required |

Mode: read-only by default. `--apply` requires LLM approval plus `--confirm-llm-review`.

## 8. Current status

- Beta stage: post-merge consistency analysis with limited write support
- `--apply` appends reconciliation notes to `session_handoff.md`
- Refreshes the `state.json` cache to match the reconciled state
- Anything unverified after the merge is kept as a warning and a re-confirmation point

## Read next

- Skills hub: [../README.md](../README.md)
- Full spec: [../../core/merge_doc_reconcile_skill_spec.md](../../core/merge_doc_reconcile_skill_spec.md)
