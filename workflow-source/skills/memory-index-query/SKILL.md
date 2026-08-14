# Memory Index Query Skill

- Purpose: describe the skill entry point and output for the ADR-005 memory_index retrieval 3-tuple.
- Scope: input/output, permission boundary, where session-start / doc-sync / backlog-update integrate.
- Audience: skill callers (session-start / doc-sync / backlog-update), memory_index users.
- Status: beta (v0.11.22+ Phase 3, subcommand 36)
- Last updated: 2026-08-14
- Related: `../../../docs/architecture/ADR-005-memora-inspired-memory-index.md`, `../../../workflow-source/core/workflow_skill_catalog.md`

## 1. Purpose

Expose the ADR-005 memory_index retrieval 3-tuple (cue exact → BM25 fallback → linked
expansion) as the standard retrieval layer for session-start, doc-sync, and backlog-update.
In Phase 3 this skill does retrieval only — read-only, no disk changes.

## 2. Entry point

```bash
python3 scripts/run_memory_index_query.py \
  --workspace-root <ws> \
  --query-tokens <csv> \
  [--top-k 10] [--max-depth 2] [--use-bm25-fallback] [--json]
```

Or via the dispatcher subcommand:

```bash
python3 -m workflow_kit.workflow_kit_cli --command memory-index-query \
  --workspace-root <ws> \
  --query-tokens <csv> \
  [--top-k 10] [--max-depth 2] [--use-bm25-fallback] [--json]
```

## 3. Input

- `--workspace-root` (required) — a workspace containing `ai-workflow/memory/active/memory_index/`.
- `--query-tokens` (required) — comma-separated token list, e.g. `"memora,memory retrieval"`.
- `--top-k` (optional, default 10, range 1..100).
- `--max-depth` (optional, default 2, range 0..3) — linked-expansion depth cap.
- `--use-bm25-fallback` (optional, default False — opt-in).
- `--json` (optional, default False) — JSON on stdout instead of human-readable text.

## 4. Output

`MemoryIndexQueryOutput` (a `BaseOutput` subclass, Pydantic):

| field | meaning |
| --- | --- |
| `status` | `ok` / `warning` / `error` |
| `query_tokens` | echo of the input |
| `selected_ids` | entry ids returned by retrieval |
| `selected_count` | length of the above |
| `cue_hits` | stage 1 hits (cue anchor exact) |
| `bm25_hits` | stage 2 fills (BM25 fallback; only when `use_bm25_fallback=True`) |
| `expansion_hits` | stage 3 unique additions (linked expansion) |
| `expansion_depth_used` | expansion depth actually applied |
| `source_context` | call info — workspace_root, top_k, max_depth, use_bm25_fallback, … |

## 4.1 Error codes (stable since v1.1.3)

Failures are emitted as an **`ErrorOutput` JSON on stdout** (stdout is what machines read;
stderr is what humans read). This satisfies the "at least 3 error codes" requirement in
`skill_beta_criteria.md` §3.1.

| error_code | When |
| --- | --- |
| `invalid_query_tokens` | `--query-tokens` is empty (including separators only) |
| `missing_required_document` | the `--workspace-root` path does not exist |
| `memory_index_query_runtime_error` | an exception during retrieval (corrupt entries, …) |

## 4.2 Usage examples

```bash
# default (human-readable)
python3 workflow-source/skills/memory-index-query/scripts/run_memory_index_query.py \
    --workspace-root . --query-tokens "telemetry,memory-index"

# JSON + BM25 fallback opt-in
python3 workflow-source/skills/memory-index-query/scripts/run_memory_index_query.py \
    --workspace-root . --query-tokens "memora,retrieval" \
    --top-k 5 --max-depth 1 --use-bm25-fallback --json

# via the dispatcher (telemetry source is recorded as "dispatcher")
wk memory-index-query --workspace-root=. --query-tokens="telemetry,phase-13"
```

Failure example — the kind is distinguished by `error_code`:

```bash
$ ... --workspace-root /nonexistent --query-tokens t
{
  "status": "error",
  "error_code": "missing_required_document",
  ...
}
```

## 5. Permissions

Read-only — even with `use_bm25_fallback=True`, the memory_index on disk is never modified.
Results go to stdout as JSON or text. Downstream skills (session-start and friends) can
consume this output directly in the workflow layer.

## 6. Follow-up

- Phase 3b: wiring for session-start / doc-sync / backlog-update (this Phase 3 release
  exposes only the entry point and dispatcher).
- Phase 3+: `workflow_kit.common.state.memory_index.query_memory_index_for_dispatcher` is
  the standard retrieval entry point for the v0.11.23+ skill canvas.
- ADR-006 retrospective: after Phase 3b wiring, based on real usage data.
