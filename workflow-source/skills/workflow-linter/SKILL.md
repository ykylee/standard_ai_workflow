# Skill: workflow-linter

- Purpose: describe the skill that checks data consistency across the core workflow documents (`state.json`, handoff, backlog).
- Scope: input/output contract, what is checked, consistency rules
- Audience: AI agent, workflow operator
- Status: stable (promoted in v0.11.20)
- Last updated: 2026-08-14
- Related: `ai-workflow/memory/active/state.json`, `ai-workflow/memory/active/sessions`

## 1. Overview

As agents update documents across many sessions, sections go missing, statuses drift apart,
and links rot. This skill catches that automatically so the context does not quietly get
corrupted.

## 2. Input and output

### Inputs
- `project-root`: project root path (default: `.`)
- `state-json-path`: path to `state.json` (optional)
- `handoff-path`: path to `session_handoff.md` (optional)
- `latest-backlog-path`: path to the latest backlog file (optional)
- `json`: emit standard JSON output (optional)

### Outputs (JSON mode)
- `status`: `"ok"` or `"issues_found"`
- `issues`: problems found (type, code, description, severity, fix_suggestion)
- `summary`: totals (total_issues, sync_errors, broken_links, …)
- `warnings`: warnings raised while parsing

## 3. What it checks

1. **Status sync (`task_status_mismatch`)**: is an `in_progress` task in the backlog
   reflected identically in the handoff and in `state.json`?
2. **Link validity (`file_not_found`)**: do the relative paths referenced in the documents
   actually exist?
3. **Rotation (`handoff_bloat`)**: has the handoff's completed list grown too long?
   (warns above 10 entries)

## 4. Usage (v0.11.20 stable)

```bash
# default run (text report)
python3 skills/workflow-linter/scripts/run_workflow_linter.py

# JSON output (for orchestrators)
python3 skills/workflow-linter/scripts/run_workflow_linter.py --json

# explicit paths
python3 skills/workflow-linter/scripts/run_workflow_linter.py \
  --project-profile-path docs/PROJECT_PROFILE.md \
  --state-json-path ai-workflow/memory/active/state.json \
  --handoff-path ai-workflow/memory/active/sessions

# maturity matrix + auto-fix (--apply)
python3 skills/workflow-linter/scripts/run_workflow_linter.py --maturity --apply
```

## v0.6.5 Stage Completion

From v0.6.5 on, this skill's output carries the `stage_completion` field of the v0.6.4
[Stage Gate Pattern](../../../core/stage_gate_pattern.md).

| Field | Value |
|---|---|
| `stage_name` | `workflow-linter` |
| `next_stage` | `(workflow end)` |
| `approval_actor` | `user`, mandatory (affects state documents) |
| `approval_timestamp` | ISO 8601 |

Full spec: [`core/stage_gate_pattern.md`](../../../core/stage_gate_pattern.md),
[`core/output_schema_guide.md §3.4`](../../../core/output_schema_guide.md).
