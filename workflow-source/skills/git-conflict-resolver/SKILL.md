# Skill: git-conflict-resolver

## Overview
Automated analysis and resolution of git merge conflicts. This skill helps the agent resolve complex 3-way merge conflicts by classifying conflict types and applying predefined or custom strategies.

## Key Features
- **Conflict Marker Analysis**: Detects and parses `<<<<<<<`, `=======`, and `>>>>>>>`.
- **Classification**: Identifies if a conflict is in a configuration file, documentation, or source code.
- **Resolution Strategies**:
    - `ours`: Keep changes from the current branch.
    - `theirs`: Use changes from the incoming branch.
    - `smart`: Attempt to combine non-overlapping changes (for docs/lists).
- **Validation**: Automatically runs syntax checks or tests after resolution.

## Input Contract
```json
{
  "repo_path": "string",
  "target_file": "string",
  "strategy": "ours|theirs|smart|analyze_only"
}
```

## Output Contract
```json
{
  "status": "ok|warning|error",
  "conflict_count": "number",
  "resolved_count": "number",
  "resolution_summary": "string",
  "unresolved_conflicts": "list[object]"
}
```


## Usage

```bash
# resolve a file with conflict markers using the "ours" strategy
python3 scripts/run_conflict_resolver.py \
    --target-file path/to/conflicted.md \
    --strategy ours

# explicit repo path, JSON output
python3 scripts/run_conflict_resolver.py \
    --repo-path /path/to/repo \
    --target-file src/app.py \
    --strategy smart --json
```

| flag | required | description |
|---|---|---|
| `--target-file` | ✅ | file whose conflict markers to resolve |
| `--repo-path` | | repository path (default: cwd) |
| `--strategy` | | `ours` / `theirs` / `smart` (default: implementation default) |
| `--json` | | JSON output |

`smart` auto-merges only when both sides changed non-overlapping list entries. When it
cannot, it leaves that block in `unresolved_conflicts` — it never silently overwrites
something it did not actually resolve.

## v0.6.5 Stage Completion

From v0.6.5 on, this skill's output carries the `stage_completion` field of the v0.6.4
[Stage Gate Pattern](../../../core/stage_gate_pattern.md).

| Field | Value |
|---|---|
| `stage_name` | `git-conflict-resolver` |
| `next_stage` | `(workflow end)` |
| `approval_actor` | `user`, mandatory (affects state documents) |
| `approval_timestamp` | ISO 8601 |

Full spec: [`core/stage_gate_pattern.md`](../../../core/stage_gate_pattern.md),
[`core/output_schema_guide.md §3.4`](../../../core/output_schema_guide.md).
