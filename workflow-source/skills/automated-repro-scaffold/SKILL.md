# Skill: automated-repro-scaffold

- Purpose: describe the skill that generates a standalone sandbox script for reproducing a bug.
- Scope: how to run it, key features, worked examples
- Audience: AI agent, developer
- **Status: stable** (v0.11.24 — Pydantic BaseOutput conformance + 4 error codes + single entry point + smoke test)
- Last updated: 2026-08-14
- Related: `core/automated_repro_scaffold_skill_spec.md`, `core/workflow_skill_catalog.md`, `workflow_kit/common/schemas/automated_repro_scaffold.py`

## Usage (stable)

```bash
python3 workflow-source/skills/automated-repro-scaffold/scripts/run_automated_repro_scaffold.py \
  --report "bug_report.md" \
  --output "tests/repro_issue_1.py"
```

`--dry-run`: print the plan and a template preview without writing the script.
`--json`: force the status/error_code envelope on stdout.

## Key features
- **Issue analysis**: extract the core reproduction logic from a text bug report.
- **Code scaffolding**: emit a standalone `unittest`-based test.
- **Dependency injection**: include mock data or minimal environment setup when needed.
- **StageCompletion integration** (v0.6.5+): emits `next_stage="validation-plan"` so the
  downstream workflow connects automatically.

## Input contract

```json
{
  "report": "bug_report.md",   // required — path to the bug report
  "output": "tests/repro_X.py" // required — where to write the generated scaffold
}
```

## Output contract — Pydantic conformance (v0.11.24)

```json
{
  "status": "ok|warning|error",
  "tool_version": "v0.11.24-beta",
  "warnings": ["..."],
  "repro_script_path": "tests/repro_X.py",
  "repro_script_lines": 42,
  "execution_command": "python3 tests/repro_X.py",
  "next_stage": "validation-plan",
  "source_context": {
    "report_path": "bug_report.md",
    "output_path": "tests/repro_X.py"
  }
}
```

## Error codes (4, stable in v0.11.24)

| Error code | When | Notes |
|---|---|---|
| `automated_repro_scaffold_report_file_not_found` | `--report` path is absent | blocked up front |
| `automated_repro_scaffold_output_dir_unwritable` | cannot write the `--output` directory/file | OSError caught |
| `automated_repro_scaffold_template_render_failed` | internal template formatting failed | KeyError/ValueError caught |
| `automated_repro_scaffold_runtime_error` | catch-all OSError (report read, …) | other runtime failures |

## Worked examples (v0.11.24 stable)

### Example 1 — success

```bash
$ echo "Test bug: foo returns None instead of 42" > /tmp/bug.md
$ python3 workflow-source/skills/automated-repro-scaffold/scripts/run_automated_repro_scaffold.py \
    --report /tmp/bug.md \
    --output /tmp/repro_bug.py

{
  "status": "ok",
  "tool_version": "v0.11.24-beta",
  "warnings": ["This scaffold was generated automatically. The actual reproduction logic still has to be written."],
  "repro_script_path": "/tmp/repro_bug.py",
  "repro_script_lines": 36,
  "execution_command": "python3 /tmp/repro_bug.py",
  "next_stage": "validation-plan",
  "source_context": { "report_path": "/tmp/bug.md", "output_path": "/tmp/repro_bug.py" },
  "stage_completion": { "stage_name": "automated-repro-scaffold", "stage_status": "ok", ... }
}
```

### Example 2 — report missing (error_code: automated_repro_scaffold_report_file_not_found)

```bash
$ python3 workflow-source/skills/automated-repro-scaffold/scripts/run_automated_repro_scaffold.py \
    --report /tmp/missing.md \
    --output /tmp/repro_bug.py

{
  "status": "error",
  "tool_version": "v0.11.24-beta",
  "error": "report file not found: /tmp/missing.md",
  "error_code": "automated_repro_scaffold_report_file_not_found",
  "warnings": ["report file not found: /tmp/missing.md"],
  "source_context": { "report_path": "/tmp/missing.md", "output_path": "/tmp/repro_bug.py" },
  "stage_completion": { "stage_name": "automated-repro-scaffold", "stage_status": "error", ... }
}
```

### Example 3 — dry run (no script written)

```bash
$ python3 workflow-source/skills/automated-repro-scaffold/scripts/run_automated_repro_scaffold.py \
    --report /tmp/bug.md \
    --output /tmp/repro_bug.py \
    --dry-run

{
  "mode": "dry-run",
  "would_write_to": "/tmp/repro_bug.py",
  "preview_first_500": "#!/usr/bin/env python3\nimport unittest\n..."
}
```

## Checklist

- [x] Does the script run standalone with no dependency on other files? (stdlib `unittest` only)
- [x] Does it reproduce the reported failure via `assert` or a raised exception? (placeholder at scaffold stage; filled in later)
- [x] Is the run command stated explicitly? (`execution_command` field)
- [x] Conforms to the Pydantic v2 schema (`AutomatedReproScaffoldOutput`)? ✅ (v0.11.24)
- [x] Four error codes defined? ✅ (v0.11.24)
- [x] Smoke test passing? ✅ (`tests/check_automated_repro_scaffold.py`)

## Downstream

The generated repro script connects automatically to the `validation-plan` stage via
StageCompletion's `next_stage`. When this skill is run on its own, whoever picks it up
fills in the reproduction logic and runs it with the python3 call in `execution_command`.
