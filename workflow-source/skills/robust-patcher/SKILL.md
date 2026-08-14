# Skill: robust-patcher

- Purpose: fuzzy patching from Search-Replace blocks, to compensate for the low edit precision of local LLMs.
- Scope: SEARCH/REPLACE block parsing, fuzzy matching, syntax validation
- Audience: AI agent, developer
- Status: stable (promoted in v0.11.21)
- Last updated: 2026-08-14
- Related: `core/phase6_precision_editing_plan.md`

## 1. Overview

In local-LLM environments where exact line numbers or whitespace are hard to reproduce,
you supply only the code **as it is now (SEARCH)** and **as it should be (REPLACE)**; the
skill locates the target intelligently and applies the edit.

## 2. Usage (instructions for the LLM)

When editing code, use this format:

```
<<<<<<< SEARCH
[the existing code block you want to change]
=======
[the replacement code block]
>>>>>>> REPLACE
```

## 3. Usage examples (v0.11.21 stable)

```bash
# 1) apply a patch (exact match)
python3 skills/robust-patcher/scripts/run_robust_patcher.py \
  --file "src/main.py" \
  --patch-file "patch.txt"

# 2) dry run (preview, file unchanged)
python3 skills/robust-patcher/scripts/run_robust_patcher.py \
  --file "src/main.py" \
  --patch-file "patch.txt" \
  --dry-run

# 3) example patch file (patch.txt)
cat <<'EOF' > patch.txt
<<<<<<< SEARCH
def greet(name):
    return 'hello ' + name
=======
def greet(name):
    return f'hello {name}'
>>>>>>> REPLACE
EOF
```

## 4. Key properties

- **Fuzzy match**: applies the patch when similarity is at least 80%, even if indentation
  or blank lines differ (based on `difflib.SequenceMatcher.ratio()`).
- **Auto-validation**: if the patch introduces a Python syntax error, the file is not
  written and the run reports failure (atomic semantics — the original survives).
- **Per-block traceability**: emits `matched` / `fuzzy_score` / `preview` for each
  SEARCH/REPLACE block in `applied_blocks` (matching the Pydantic schema).

## 5. Output contract

| field | type | description |
|---|---|---|
| `status` | `"ok" / "error"` | run result |
| `file_path` | `str` | absolute path that was patched |
| `message` | `str` | human-readable summary (e.g. `Successfully applied 3 patch block(s).`) |
| `dry_run` | `bool` | whether `--dry-run` was used |
| `applied_blocks` | `list[AppliedPatchBlock]` | per-block detail (`block_index` / `matched` / `fuzzy_score` / `preview`) |
| `syntax_validated` | `bool` | whether the post-patch syntax check passed for `.py` files |
| `source_context` | `RobustPatcherSourceContext` | the `--file` / `--patch-file` inputs |

## 6. Error codes (4)

- `missing_required_document` — `--file` or `--patch-file` path is absent (blocked up front)
- `malformed_patch_block` — patch content has no valid SEARCH/REPLACE block at all
- `fuzzy_match_failed` — the SEARCH block did not reach the 0.8 fuzzy threshold (atomic
  rollback), or a post-patch SyntaxError occurred
- `robust_patcher_runtime_error` — unexpected exception (catch-all)

## v0.6.5 Stage Completion

From v0.6.5 on, this skill's output carries the `stage_completion` field of the v0.6.4
[Stage Gate Pattern](../../../core/stage_gate_pattern.md).

| Field | Value |
|---|---|
| `stage_name` | `robust-patcher` |
| `next_stage` | `validation-plan` |
| `approval_actor` | `user`, mandatory (affects state documents) |
| `approval_timestamp` | ISO 8601 |

Full spec: [`core/stage_gate_pattern.md`](../../../core/stage_gate_pattern.md),
[`core/output_schema_guide.md §3.4`](../../../core/output_schema_guide.md).
