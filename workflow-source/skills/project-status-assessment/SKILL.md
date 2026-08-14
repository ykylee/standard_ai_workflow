# Skill: project-status-assessment

- Purpose: describe the skill that diagnoses a repository's stack, structure, tests, and documentation to judge how ready it is for the workflow.
- Scope: input/output contract, what is diagnosed, usage
- Audience: AI agent, workflow onboarding owner
- Status: stable (promoted in v0.11.20)
- Last updated: 2026-08-14
- Related: `core/project_status_assessment.md`, `core/workflow_skill_catalog.md`

## 1. Overview

Before introducing the workflow into a new project, you need an objective picture of where
that project currently stands. This skill walks the file system, checks which configuration
files, source directories, and tests exist, and produces a standardized diagnostic report.

## 2. Input and output

### Inputs
- `project-root`: root of the project to diagnose (default: `.`)
- `output-path`: where to write the report (default: `ai-workflow/memory/active/repository_assessment.md`)
- `apply`: whether to actually create/update files

### Outputs
- `status`: `"ok"`
- `assessment`:
    - `primary_stack`: detected primary stack (e.g. Python, Node.js, Go)
    - `structure_score`: how well organized the layout is
    - `test_coverage_hint`: whether tests exist and of what kind
    - `docs_score`: documentation level
- `recommended_actions`: what to shore up first before adopting the workflow

## 3. Diagnostic logic

1. **Stack detection**: identify the primary language and framework from `package.json`,
   `requirements.txt`, `go.mod`, `Cargo.toml`, and friends.
2. **Structure analysis**: check for the standard directories — `src/`, `lib/`, `tests/`, `docs/`.
3. **Command inference**: read `scripts/` and configuration files to derive candidate
   `install` / `run` / `test` commands.
4. **Maturity rating**: assign a maturity level of 1–4 from the findings.

## 4. Usage (v0.11.20 stable)

```bash
# human-readable markdown report (default)
python3 skills/project-status-assessment/scripts/run_project_status_assessment.py \
  --project-root /path/to/target/project \
  --apply

# JSON output for orchestrators (Pydantic schema)
python3 skills/project-status-assessment/scripts/run_project_status_assessment.py \
  --project-root /path/to/target/project \
  --apply \
  --json
```

## v0.6.5 Stage Completion

From v0.6.5 on, this skill's output carries the `stage_completion` field of the v0.6.4
[Stage Gate Pattern](../../../core/stage_gate_pattern.md).

| Field | Value |
|---|---|
| `stage_name` | `project-status-assessment` |
| `next_stage` | `(workflow end)` |
| `approval_actor` | `user`, mandatory (affects state documents) |
| `approval_timestamp` | ISO 8601 |

Full spec: [`core/stage_gate_pattern.md`](../../../core/stage_gate_pattern.md),
[`core/output_schema_guide.md §3.4`](../../../core/output_schema_guide.md).
