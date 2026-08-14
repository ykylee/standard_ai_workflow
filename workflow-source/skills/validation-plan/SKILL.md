# Validation-Plan Skill

- Purpose: describe the `validation-plan` skill — its role, input/output, and usage.
- Scope: deciding the verification level, structuring recommended commands, generating test scaffolding
- Audience: AI agent designer, developer, operator
- Status: stable (promoted in v0.11.19)
- Last updated: 2026-08-14
- Related: `../../core/validation_plan_skill_spec.md`, `../../core/workflow_skill_catalog.md`

## 1. Purpose

From the changed files and the project profile, decide how much verification this piece of
work needs, and generate a test scaffold that can be filled in immediately.

## 2. Expected input

- `project_profile_path`
- `changed_files`
- `change_summary`

Optional:

- `session_handoff_path`
- `latest_backlog_path`
- `scaffold` (flag): whether to generate the test scaffold
- `task_id`: used in the generated test file's name and comments

## 3. Expected output

- Summary of the detected change types (code, docs, ui, ops, …)
- Recommended verification level and the commands to run
- **Test scaffold**: creates `tests/repro_{task_id}.py`
- `session_handoff.md` updated automatically (links to generated files + operational notes)
- Expected evidence and the documentation checklist

## 4. Permission boundary

- Read and analyze; write only in the `--scaffold` step
- With `--scaffold`, may create new files under `tests/` and modify `session_handoff.md`
- Actually running the tests is the caller's responsibility, not this skill's

## 5. Implementation notes

- Prefer the project profile's `quick test` and `isolated test` commands.
- Generate a `unittest`-based Python skeleton so verification logic can be written straight away.
- Treat `ai-workflow/` as the workflow meta layer and exclude it from the ordinary
  changed-file set.

## 6. Usage

- **Analysis only**:
```bash
python3 skills/validation-plan/scripts/run_validation_plan.py \
  --project-profile-path docs/PROJECT_PROFILE.md \
  --changed-file app/main.py \
  --change-summary "fix login logic"
```

- **Generate the scaffold and record it**:
```bash
python3 skills/validation-plan/scripts/run_validation_plan.py \
  --project-profile-path docs/PROJECT_PROFILE.md \
  --session-handoff-path ai-workflow/memory/active/sessions \
  --changed-file app/main.py \
  --change-summary "fix login logic" \
  --scaffold \
  --task-id TASK-123
```

## 7. Current status

- Beta stage: builds the verification plan and generates test scaffolding
- `--scaffold` creates `tests/repro_{task_id}.py` and wires it into `session_handoff.md`

## Read next

- Skills hub: [../README.md](../README.md)
- Full spec: [../../core/validation_plan_skill_spec.md](../../core/validation_plan_skill_spec.md)
