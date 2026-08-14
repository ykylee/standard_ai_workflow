# Code-Index-Update Skill

- Purpose: describe the `code-index-update` skill — its role, input/output, and usage.
- Scope: recommending index documents to refresh, stale warnings, automatic index sync
- Audience: AI agent designer, developer, operator
- Status: stable (promoted in v0.11.19)
- Last updated: 2026-08-14
- Related: `../../core/code_index_update_skill_spec.md`, `../../core/workflow_skill_catalog.md`

## 1. Purpose

From the changed files and the project profile, derive which index and hub documents need
to be re-checked or updated, and record that in `session_handoff.md`.

## 2. Expected input

- `project_profile_path`
- `changed_files`

Optional:

- `work_backlog_index_path`
- `session_handoff_path`
- `change_summary`
- `apply` (flag): whether to sync index documents automatically

## 3. Expected output

- Candidate index documents to update, with a suggested priority
- Stale-risk warnings and the reasoning behind each recommendation
- `session_handoff.md` updated automatically (recommended index links + operational notes)
- `state.json` cache refreshed

## 4. Permission boundary

- Read and analyze; write only in the `--apply` step
- With `--apply`, may modify `session_handoff.md` and `state.json`
- Never edits the body of an index document (README and friends) — it surfaces the change
  for a human to confirm instead

## 5. Implementation notes

- Default candidate set: the document home, the operations hub, the backlog index, and the
  root README.
- When a child document changes, raise the priority of its parent hub — that hub is the
  thing most likely to have gone stale.
- Treat `ai-workflow/` as the workflow meta layer and exclude it from ordinary project
  index discovery.

## 6. Usage

- **Analysis only**:
```bash
python3 skills/code-index-update/scripts/run_code_index_update.py \
  --project-profile-path docs/PROJECT_PROFILE.md \
  --changed-file docs/operations/runbooks/new-guide.md
```

- **Automatic index sync**:
```bash
python3 skills/code-index-update/scripts/run_code_index_update.py \
  --project-profile-path docs/PROJECT_PROFILE.md \
  --session-handoff-path ai-workflow/memory/active/sessions \
  --changed-file docs/operations/runbooks/new-guide.md \
  --apply
```

## 7. Current status

- Beta stage: recommends index updates and supports automatic sync
- `--apply` wires up `session_handoff.md` and refreshes the `state.json` cache

## Read next

- Skills hub: [../README.md](../README.md)
- Full spec: [../../core/code_index_update_skill_spec.md](../../core/code_index_update_skill_spec.md)
