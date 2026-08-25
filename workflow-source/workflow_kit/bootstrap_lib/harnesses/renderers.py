"""Per-harness renderers and write_*_harness_files dispatchers."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from workflow_kit.bootstrap_lib.harnesses import register_harness_builder
from workflow_kit.bootstrap_lib.mcp import render_mcp_toml_block
from workflow_kit.bootstrap_lib.paths import (
    Paths,
    antigravity_agents_path,
    codex_agents_path,
    codex_config_example_path,
    gemini_cli_agents_path,
    minimax_agents_path,
    opencode_agent_path,
    opencode_code_worker_agent_path,
    opencode_config_path,
    opencode_doc_worker_agent_path,
    opencode_skill_path,
    opencode_validation_worker_agent_path,
    opencode_worker_agent_path,
)
from workflow_kit.bootstrap_lib.writes import rel, write_text

#: pi-dev 전용 장의 제목 — 합쳐졌는지 판정하는 표식이자 idempotency key.
PI_DEV_SUPPLEMENT_HEADING = "# Pi Coding Agent Profile (pi-dev only)"
from workflow_kit.common.standard_rules import (
    find_memory_command,
    load_standard_rules,
    render_entrypoint_rules,
    render_memory_update_section,
)


def render_gemini_cli_agents(args: argparse.Namespace, paths: Paths, context: dict[str, object]) -> str:
    harness_note = (
        "This draft reflects an analysis of the existing codebase. The inferred commands and document paths may need to be corrected against the real repository."
        if args.adoption_mode == "existing"
        else "This is a new-project draft. Verify that the project's own run commands and document structure are correct."
    )
    # Ensure smoke check has a sensible default if still TODO
    smoke_check = context['smoke_check_command']
    if "TODO"in smoke_check:
        if context['primary_stack'] == 'python':
            smoke_check = "python3 --version"
        elif context['primary_stack'] == 'node':
            smoke_check = "node --version"

    _STANDARD_RULES = render_entrypoint_rules()
    return f"""# GEMINI.md

- Purpose: Provide the workflow entry rules and core working principles Gemini CLI should read first in this repository.
- Scope: session restore, the order to consult workflow state docs, user-facing report language, default run/verify commands
- Audience: Gemini CLI, repository maintainer, workflow designer
- Status: draft
- Last updated: {args.today}
- Related: `ai-workflow/memory/active/<branch>/state.json`, `ai-workflow/memory/active/<branch>/sessions`, `ai-workflow/memory/active/<branch>/backlog`, `docs/PROJECT_PROFILE.md`

## Purpose

Work in this repository follows the standard AI workflow. Session start, backlog updates,
document sync, and session close all take the documents under `ai-workflow/` as the
primary reference.

## Read these first

> `<branch>` is the current git branch name (`main` when this is not a git repository). Splitting per branch keeps concurrent work from overwriting itself.

- `ai-workflow/memory/active/<branch>/state.json`
- `ai-workflow/memory/active/<branch>/sessions`
- `ai-workflow/memory/active/<branch>/backlog`
- `docs/PROJECT_PROFILE.md`
- `ai-workflow/wiki/index.md` — R4 anchor based; load this first when an AI agent queries

`ai-workflow/` is a meta layer for session restore and workflow state. Do not include it in the default search scope when exploring project code or project documents — reference it only when updating the workflow documents themselves or restoring the current session state.

{_STANDARD_RULES}

## Language and context principles

- Write user-facing work reports, status summaries, and document updates in Korean by default.
- Keep code, commands, file paths, configuration keys, and external product names verbatim.
- Handle internal reasoning and scratch classification however is most efficient, but give the user only the conclusion and the next action.
- Avoid long intermediate reasoning, repeated summaries, and unnecessary self-explanation.
- Keep only the facts the next session needs in the handoff and backlog, so context does not pile up.

## Project run defaults

- Install: `{context['install_command']}`
- Run locally: `{context['run_command']}`
- Quick test: `{context['quick_test_command']}`
- Isolated test: `{context['isolated_test_command']}`
- Smoke check: `{smoke_check}`

## Documentation conventions

- Documentation home: `{context['doc_home']}`
- Operations docs: `{context['operations_dir']}`
- Backlog location: `{context['backlog_dir']}`
- Session handoff: `{context['session_doc_path']}`

## Gemini CLI notes

- Gemini CLI reads `GEMINI.md` at the project root, so start policy here and defer operational detail to the `ai-workflow/` documents.
- Treat instructions written in `GEMINI.md` as strong directives that take precedence over the system prompt.
- Where possible, keep the main agent on coordination and integration, and split bounded read/write/verify work into sub-agents (`invoke_agent`).
- Hand each sub-agent an explicit scope and exit condition, and collect only the key facts and results back into the main agent.
- {harness_note}
"""


def antigravity_agents_path(paths: Paths) -> Path:
    return paths.target_root / "ANTIGRAVITY.md"


def minimax_agents_path(paths: Paths) -> Path:
    """Return the MiniMax Code entry file path (project root ``MiniMax.md``)."""
    return paths.target_root / "MiniMax.md"




def render_antigravity_agents(args: argparse.Namespace, paths: Paths, context: dict[str, object]) -> str:
    harness_note = (
        "This draft reflects an analysis of the existing codebase. The inferred commands and document paths may need to be corrected against the real repository."
        if args.adoption_mode == "existing"
        else "This is a new-project draft. Verify that the project's own run commands and document structure are correct."
    )
    # Ensure smoke check has a sensible default if still TODO
    smoke_check = context['smoke_check_command']
    if "TODO"in smoke_check:
        if context['primary_stack'] == 'python':
            smoke_check = "python3 --version"
        elif context['primary_stack'] == 'node':
            smoke_check = "node --version"

    _STANDARD_RULES = render_entrypoint_rules()
    return f"""# ANTIGRAVITY.md

- Purpose: Provide the workflow entry rules and core working principles Antigravity should read first in this repository.
- Scope: session restore, the order to consult workflow state docs, user-facing report language, default run/verify commands
- Audience: Antigravity, repository maintainer, workflow designer
- Status: draft
- Last updated: {args.today}
- Related: `ai-workflow/memory/active/<branch>/state.json`, `ai-workflow/memory/active/<branch>/sessions`, `ai-workflow/memory/active/<branch>/backlog`, `docs/PROJECT_PROFILE.md`

## Purpose

Work in this repository follows the standard AI workflow. Session start, backlog updates,
document sync, and session close all take the documents under `ai-workflow/` as the
primary reference.

## Read these first

> `<branch>` is the current git branch name (`main` when this is not a git repository). Splitting per branch keeps concurrent work from overwriting itself.

- `ai-workflow/memory/active/<branch>/state.json`
- `ai-workflow/memory/active/<branch>/sessions`
- `ai-workflow/memory/active/<branch>/backlog`
- `docs/PROJECT_PROFILE.md`
- `ai-workflow/wiki/index.md` — R4 anchor based; load this first when an AI agent queries

`ai-workflow/` is a meta layer for session restore and workflow state. Do not include it in the default search scope when exploring project code or project documents — reference it only when updating the workflow documents themselves or restoring the current session state.

{_STANDARD_RULES}

## Language and context principles

- Write user-facing work reports, status summaries, and document updates in Korean by default.
- Keep code, commands, file paths, configuration keys, and external product names verbatim.
- Handle internal reasoning and scratch classification however is most efficient, but give the user only the conclusion and the next action.
- Avoid long intermediate reasoning, repeated summaries, and unnecessary self-explanation.
- Keep only the facts the next session needs in the handoff and backlog, so context does not pile up.

## Project run defaults

- Install: `{context['install_command']}`
- Run locally: `{context['run_command']}`
- Quick test: `{context['quick_test_command']}`
- Isolated test: `{context['isolated_test_command']}`
- Smoke check: `{smoke_check}`

## Antigravity-specific working principles

### 1. Using Artifacts (work evidence)
The Antigravity agent manages every significant decision and result as an Artifact.
- **Implementation Plan**: before any complex change, write a plan document so the intent is shared.
- **Task List**: break the work into units and record progress as it happens.
- **Walkthrough**: after finishing, submit a summary of the changes and the verification results.

### 2. Browser integration and sub-agents
When UI verification or external environment manipulation is needed, use the dedicated **browser sub-agent** rather than driving tools directly, and capture screenshots and recordings as evidence.

### 3. Workflow skill integration
Treat the tools under `ai-workflow/skills/` and `scripts/` as Antigravity **Specialized Skills**. For complex state updates or backlog sync, call those tools rather than editing files by hand.

## Documentation conventions

- Documentation home: `{context['doc_home']}`
- Operations docs: `{context['operations_dir']}`
- Backlog location: `{context['backlog_dir']}`
- Session handoff: `{context['session_doc_path']}`

## Antigravity notes

- Antigravity reads `ANTIGRAVITY.md` at the project root, so start policy here and defer operational detail to the `ai-workflow/` documents.
- Treat instructions written in `ANTIGRAVITY.md` as strong directives that take precedence over the system prompt.
- Where possible, keep the main agent on coordination and integration, and split bounded read/write/verify work into an appropriate sub-agent such as the browser sub-agent.
- Hand each sub-agent an explicit scope and exit condition, and collect only the key facts and results back into the main agent.
- {harness_note}
"""


def render_minimax_agents(args: argparse.Namespace, paths: Paths, context: dict[str, object]) -> str:
    """Render ``MiniMax.md`` — the MiniMax Code harness entry file."""
    harness_note = (
        "This draft reflects an analysis of the existing codebase. The inferred commands and document paths may need to be corrected against the real repository."
        if args.adoption_mode == "existing"
        else "This is a new-project draft. Verify that the project's own run commands and document structure are correct."
    )
    smoke_check = context['smoke_check_command']
    if "TODO" in smoke_check:
        if context['primary_stack'] == 'python':
            smoke_check = "python3 --version"
        elif context['primary_stack'] == 'node':
            smoke_check = "node --version"

    _STANDARD_RULES = render_entrypoint_rules()
    return f"""# MiniMax.md

- Purpose: Provide the workflow entry rules the MiniMax Code (Mavis) harness should read first in this repository.
- Scope: session restore, the order to consult workflow state docs, user-facing report language, default run/verify commands, orchestrator/worker principles
- Audience: MiniMax Code, repository maintainer, multi-agent operator
- Status: draft
- Last updated: {args.today}
- Related: `ai-workflow/memory/active/<branch>/state.json`, `ai-workflow/memory/active/<branch>/sessions`, `ai-workflow/memory/active/<branch>/backlog`, `docs/PROJECT_PROFILE.md`, `AGENTS.md`

## Purpose

Work in this repository follows the **Standard AI Workflow**. Session start, backlog updates, document sync, and session close all take the documents under `ai-workflow/` as the primary reference. MiniMax Code acts as the main orchestrator and delegates bounded-scope work to doc/code/validation workers to conserve context.

## Read these first

> `<branch>` is the current git branch name (`main` when this is not a git repository). Splitting per branch keeps concurrent work from overwriting itself.

- `ai-workflow/memory/active/<branch>/state.json`
- `ai-workflow/memory/active/<branch>/sessions`
- `ai-workflow/memory/active/<branch>/backlog`
- `docs/PROJECT_PROFILE.md`
- `AGENTS.md` (workflow rules summary)

`ai-workflow/` is a meta layer for session restore and workflow state. Do not include it in the default search scope when exploring project code or project documents — reference it only when updating the workflow documents themselves or restoring the current session state.

{_STANDARD_RULES}
- Keep the main orchestrator on coordination and integration as much as possible, and delegate tool calls, exploration, and edits to the `.MiniMax/agents/workflow-*.md` workers.

## Orchestrator / worker principles (multi-agent topology)

- **Orchestrator (Mavis, the MiniMax Code main agent)**: talks to the user, decomposes work, invokes and integrates workers, and owns syncing `state.json` / `session_handoff` / `work_backlog`. It does not take on tool calls itself.
- **doc-worker**: document link, metadata, and catalog consistency. Calls `ai-workflow/skills/doc-sync`, `merge-doc-reconcile`, `workflow-linter`.
- **code-worker**: code edits and refactoring. Calls `ai-workflow/skills/code-index-update`, `robust-patcher`. States the output file scope in `output_files`.
- **validation-worker**: runs tests and smoke checks and records the results. Calls `ai-workflow/skills/validation-plan`, `ai-workflow/tests/check_*.py`.

When delegating to a worker, state the intent and the responsibility boundary in the `WorkerTask` shape (worker_id, task_description, input_files, output_files, constraints, context_summary). Take the result back in the `WorkerResponse` shape (status, summary, produced_artifacts, risks_identified, suggested_follow_up).

## Language and context principles

- Write user-facing work reports, status summaries, and document updates in Korean by default.
- Keep code, commands, file paths, configuration keys, and external product names verbatim.
- Handle internal reasoning and scratch classification however is most efficient, but give the user only the conclusion and the next action.
- Avoid long intermediate reasoning, repeated summaries, and unnecessary self-explanation.
- Keep only the facts the next session needs in the handoff and backlog, so context does not pile up.

## Project run defaults

- Install: `{context['install_command']}`
- Run locally: `{context['run_command']}`
- Quick test: `{context['quick_test_command']}`
- Isolated test: `{context['isolated_test_command']}`
- Smoke check: `{smoke_check}`

## Documentation conventions

- Documentation home: `{context['doc_home']}`
- Operations docs: `{context['operations_dir']}`
- Backlog location: `{context['backlog_dir']}`
- Session handoff: `{context['session_doc_path']}`

## MiniMax Code notes

- MiniMax Code uses both `MiniMax.md` and `AGENTS.md` as entry points. On conflict with system policy, `MiniMax.md` wins — but keep the two documents pointing at the same facts.
- Copy `minimax_config_example.json` into your environment configuration (`~/.MiniMax/config.json`, or the project-local `.MiniMax/config.json`). Fill in server tokens and similar values yourself.
- Before a worker performs a dangerous external action (database migration, production deploy, secret rotation), get explicit user approval first.
- {harness_note}
"""


def render_minimax_config_example() -> str:
    """Render a ``MiniMax_config.example.json`` snippet for the user to copy.

    The values are intentionally placeholders; users fill in their own MCP
    server tokens, project name, and harness-specific options.
    """
    return """{
  "$schema": "https://MiniMax.dev/schema/config.json",
  "project_name": "Standard AI Workflow Project",
  "language": "ko-KR",
  "agents": {
    "workflow-orchestrator": {
      "file": ".MiniMax/agents/workflow-orchestrator.md",
      "role": "orchestrator"
    },
    "workflow-worker": {
      "file": ".MiniMax/agents/workflow-worker.md",
      "role": "worker"
    },
    "workflow-doc-worker": {
      "file": ".MiniMax/agents/workflow-doc-worker.md",
      "role": "doc-worker"
    },
    "workflow-code-worker": {
      "file": ".MiniMax/agents/workflow-code-worker.md",
      "role": "code-worker"
    },
    "workflow-validation-worker": {
      "file": ".MiniMax/agents/workflow-validation-worker.md",
      "role": "validation-worker"
    }
  },
  "mcp_servers": {
    "standard-ai-workflow-readonly": {
      "command": "python3",
      "args": ["-m", "workflow_kit.server.read_only_jsonrpc", "--stdio-lines"],
      "env": {
        "PYTHONPATH": "./workflow-source"
      },
      "transport_phase": "jsonrpc_draft",
      "description": "Read-only MCP draft fixture for the standard workflow kit. See workflow-source/schemas/read_only_transport_descriptors.json."
    }
  },
  "workflow": {
    "memory_dir": "ai-workflow/memory/active",
    "session_handoff_path": "ai-workflow/memory/active/<branch>/sessions",
    "work_backlog_index_path": "ai-workflow/memory/active/<branch>/backlog",
    "project_profile_path": "docs/PROJECT_PROFILE.md",
    "state_json_path": "ai-workflow/memory/active/<branch>/state.json"
  },
  "session_protocol": {
    "language": "ko-KR",
    "auto_refresh_state": true,
    "require_handoff_before_done": true
  }
}
"""


def render_minimax_orchestrator(args: argparse.Namespace, context: dict[str, object]) -> str:
    """Render the orchestrator overlay describing the orchestrator's role.

    책임 3 이 state.json/handoff/backlog 갱신을 지시하므로 **방법**(§11)을 같이
    싣는다 — 지시만 있으면 에이전트는 손으로 쓴다 (TASK-020 전수검사, TASK-028 주입).
    """
    _MEMORY_SECTION = render_memory_update_section()
    return f"""# workflow-orchestrator

- Purpose: Define the responsibilities, boundaries, and deliverables of the MiniMax Code main orchestrator persona.
- Scope: work decomposition, worker delegation, handoff/state sync, user reporting
- Audience: MiniMax Code, multi-agent operator
- Status: stable
- Last updated: {args.today}
- Related: `../../../MiniMax.md`, `../../../AGENTS.md`, `workflow-worker.md`

## Responsibilities

1. Take the user's request and break it into bounded-scope units of work.
2. Delegate each unit to a worker (doc/code/validation) in the `WorkerTask` shape.
3. Collect the workers' `WorkerResponse` values and update `state.json` / `session_handoff.md` / the latest `backlog`.
4. Give the user a short progress report and the next action, in Korean.

## Never do

- Never edit project code directly with `read_file` / `edit_file` (delegate to code-worker).
- Never run tests or smoke checks directly with `bash` (delegate to validation-worker).
- Never add speculative conclusions beyond what the workers actually reported.

## Exit criteria

- Every delegated unit returned either `WorkerResponse.status == "ok"` or an explicit blocked reason
- `session.last_orchestrator_action` in `state.json` reflects this session's final action
- The "next session starting point" in `session_handoff.md` is updated to a single sentence

{_MEMORY_SECTION}
"""


def render_minimax_worker(args: argparse.Namespace, context: dict[str, object]) -> str:
    """Render the generic worker overlay (sub-agent operating contract)."""
    return f"""# workflow-worker

- Purpose: Define the shared operating contract for MiniMax Code sub-workers.
- Scope: input, responsibilities, deliverables, communication format
- Audience: MiniMax Code, multi-agent operator
- Status: stable
- Last updated: {args.today}
- Related: `../../../workflow-source/core/workflow_agent_topology.md`, `../../../workflow-source/prompts/code_worker_prompt.md`, `../../../workflow-source/prompts/doc_worker_prompt.md`, `../../../workflow-source/prompts/validation_worker_prompt.md`

## Input

- The `WorkerTask` delegated by the orchestrator (worker_id, task_description, input_files, output_files, constraints, context_summary)

## Responsibilities

1. Change only what is listed in `output_files`.
2. After changing, report `produced_artifacts`, `risks_identified`, and `suggested_follow_up`.
3. If static verification fails or an external system call is needed, hand off to validation-worker.

## Never do

- Never modify another worker's `output_files`.
- Never add or remove dependencies that were not specified.

## Deliverables

- `WorkerResponse` (status, summary, produced_artifacts, risks_identified, suggested_follow_up, raw_worker_output)
"""


def render_minimax_doc_worker(args: argparse.Namespace, context: dict[str, object]) -> str:
    """Render the doc-worker overlay."""
    return f"""# workflow-doc-worker

- Purpose: Define the responsibilities and deliverables of the MiniMax Code doc-worker persona.
- Scope: document consistency, metadata, links, catalog sync
- Audience: MiniMax Code, multi-agent operator
- Status: stable
- Last updated: {args.today}
- Related: `workflow-worker.md`, `../../../workflow-source/prompts/doc_worker_prompt.md`

## Responsibilities

1. Use the `doc-sync` skill to identify which documents the changed code/docs affect, and produce a recommended review order.
2. Use the `merge-doc-reconcile` skill to reconcile conflicting handoff/state/backlog.
3. Use the `workflow-linter` skill to check and repair metadata/link/catalog consistency.
4. Apply the results by editing only the documents listed in `output_files`.

## Never do

- Never edit code (that is code-worker territory)
- When updating status with `backlog-update`, ask the orchestrator for an explicit delegation
"""


def render_minimax_code_worker(args: argparse.Namespace, context: dict[str, object]) -> str:
    """Render the code-worker overlay."""
    return f"""# workflow-code-worker

- Purpose: Define the responsibilities and deliverables of the MiniMax Code code-worker persona.
- Scope: code implementation, precision refactoring, regression fixes
- Audience: MiniMax Code, multi-agent operator
- Status: stable
- Last updated: {args.today}
- Related: `workflow-worker.md`, `../../../workflow-source/prompts/code_worker_prompt.md`

## Responsibilities

1. Change code only within the bounded scope the orchestrator delegated.
2. Use the `code-index-update` skill to sync the code index and catalog.
3. Use the `robust_patcher` skill to apply precise patches.
4. After changing, list the files actually modified in `produced_artifacts`.

## Never do

- Never modify files that were not specified.
- Never add or remove dependencies without explicit orchestrator approval.
"""


def render_minimax_validation_worker(args: argparse.Namespace, context: dict[str, object]) -> str:
    """Render the validation-worker overlay."""
    return f"""# workflow-validation-worker

- Purpose: Define the responsibilities and deliverables of the MiniMax Code validation-worker persona.
- Scope: running tests and smoke checks, recording results
- Audience: MiniMax Code, multi-agent operator
- Status: stable
- Last updated: {args.today}
- Related: `workflow-worker.md`, `../../../workflow-source/prompts/validation_worker_prompt.md`

## Responsibilities

1. Use the `validation-plan` skill to decide the verification level the change needs.
2. Run the smoke/test scripts, such as `ai-workflow/tests/check_*.py`.
3. Classify results clearly as `passed`, `failed`, or `skipped`, and attach the raw stderr to `risks_identified` on failure.

## Never do

- Never edit code or documents directly.
- External system calls require explicit orchestrator approval.
"""


def render_codex_agents(args: argparse.Namespace, paths: Paths, context: dict[str, object]) -> str:
    harness_note = (
        "This draft reflects an analysis of the existing codebase. The inferred commands and document paths may need to be corrected against the real repository."
        if args.adoption_mode == "existing"
        else "This is a new-project draft. Verify that the project's own run commands and document structure are correct."
    )
    # Ensure smoke check has a sensible default if still TODO
    smoke_check = context['smoke_check_command']
    if "TODO"in smoke_check:
        if context['primary_stack'] == 'python':
            smoke_check = "python3 --version"
        elif context['primary_stack'] == 'node':
            smoke_check = "node --version"

    _STANDARD_RULES = render_entrypoint_rules()
    return f"""# AGENTS.md

- Purpose: Provide the workflow entry rules and core working principles Codex should read first in this repository.
- Scope: session restore, the order to consult workflow state docs, user-facing report language, default run/verify commands
- Audience: Codex, repository maintainer, workflow designer
- Status: draft
- Last updated: {args.today}
- Related: `ai-workflow/memory/active/<branch>/state.json`, `ai-workflow/memory/active/<branch>/sessions`, `ai-workflow/memory/active/<branch>/backlog`, `docs/PROJECT_PROFILE.md`

## Purpose

Work in this repository follows the standard AI workflow. Session start, backlog updates,
document sync, and session close all take the documents under `ai-workflow/` as the
primary reference.

## Read these first

> `<branch>` is the current git branch name (`main` when this is not a git repository). Splitting per branch keeps concurrent work from overwriting itself.

- `ai-workflow/memory/active/<branch>/state.json`
- `ai-workflow/memory/active/<branch>/sessions`
- `ai-workflow/memory/active/<branch>/backlog`
- `docs/PROJECT_PROFILE.md`
- `ai-workflow/wiki/index.md` — R4 anchor based; load this first when an AI agent queries

`ai-workflow/` is a meta layer for session restore and workflow state. Do not include it in the default search scope when exploring project code or project documents — reference it only when updating the workflow documents themselves or restoring the current session state.

{_STANDARD_RULES}

## Language and context principles

- Write user-facing work reports, status summaries, and document updates in Korean by default.
- Keep code, commands, file paths, configuration keys, and external product names verbatim.
- Handle internal reasoning and scratch classification however is most efficient, but give the user only the conclusion and the next action.
- Avoid long intermediate reasoning, repeated summaries, and unnecessary self-explanation.
- Keep only the facts the next session needs in the handoff and backlog, so context does not pile up.

## Project run defaults

- Install: `{context['install_command']}`
- Run locally: `{context['run_command']}`
- Quick test: `{context['quick_test_command']}`
- Isolated test: `{context['isolated_test_command']}`
- Smoke check: `{smoke_check}`

## Documentation conventions

- Documentation home: `{context['doc_home']}`
- Operations docs: `{context['operations_dir']}`
- Backlog location: `{context['backlog_dir']}`
- Session handoff: `{context['session_doc_path']}`

## Codex notes

- Codex reads `AGENTS.md` at the project root, so start policy here and defer operational detail to the `ai-workflow/` documents.
- For OpenAI-related questions, prefer a setup that consults the OpenAI documentation MCP first.
- Where possible, keep the main agent on coordination and integration, and split bounded read/write/verify work into worker-style sub-agents.
- Hand each worker its owned files and exit condition explicitly, and collect only the key facts and results back into the main agent.
- When running `main` and `small` models together, it is more efficient to put the main agent on hard judgment and integration, and workers on bounded-scope exploration, drafting, and verification.
- {harness_note}
"""


def render_codex_config_example() -> str:
    return """# Merge this into ~/.codex/config.toml if you want Codex-wide defaults.

[mcp_servers.openaiDeveloperDocs]
url = "https://developers.openai.com/mcp"
default_tools_approval_mode = "approve"
supports_parallel_tool_calls = true
"""


def render_opencode_config(args: argparse.Namespace, paths: Paths) -> str:
    instructions = [
        "AGENTS.md",
        f"{rel(paths.state_path, paths.target_root)}",
        f"{rel(paths.profile_path, paths.target_root)}",
        f"{rel(paths.handoff_path, paths.target_root)}",
        f"{rel(paths.backlog_index_path, paths.target_root)}",
    ]
    return json.dumps(
        {
            "$schema": "https://opencode.ai/config.json",
            "instructions": instructions,
            "agent": {
                "workflow-orchestrator": {
                    "mode": "primary",
                    "description": "Standard AI workflow orchestrator for this project",
                    "prompt": "{file:.opencode/agents/workflow-orchestrator.md}",
                    "permission": {
                        "task": {
                            "*": "deny",
                            "workflow-*": "allow",
                        }
                    },
                },
                "workflow-worker": {
                    "description": "Scoped worker for implementation, draft writing, and verification tasks",
                    "prompt": "{file:.opencode/agents/workflow-worker.md}",
                },
                "workflow-doc-worker": {
                    "description": "Scoped worker for document reading, comparison, and draft updates",
                    "prompt": "{file:.opencode/agents/workflow-doc-worker.md}",
                },
                "workflow-code-worker": {
                    "description": "Scoped worker for bounded code edits and implementation tasks",
                    "prompt": "{file:.opencode/agents/workflow-code-worker.md}",
                },
                "workflow-validation-worker": {
                    "description": "Scoped worker for checks, logs, and validation evidence collection",
                    "prompt": "{file:.opencode/agents/workflow-validation-worker.md}",
                }
            },
            "mcp_servers": {
                "openaiDeveloperDocs": {
                    "type": "remote",
                    "url": "https://developers.openai.com/mcp",
                }
            },
        },
        ensure_ascii=False,
        indent=2,
    ) + "\n"


def render_opencode_skill() -> str:
    _STANDARD_RULES = render_entrypoint_rules()
    return f"""---
name: standard-ai-workflow
description: Load the project workflow docs before starting or updating work in this repository.
---

# Standard AI Workflow

Use this skill when you need to start a session, update backlog state, sync documents, or prepare a handoff.

Always read:

- `ai-workflow/memory/active/<branch>/state.json`
- `ai-workflow/memory/active/<branch>/sessions`
- `ai-workflow/memory/active/<branch>/backlog`
- `docs/PROJECT_PROFILE.md`

If the repository is still in adoption, also read:

- `ai-workflow/memory/active/repository_assessment.md`

Follow these rules:

- Write user-facing status updates, work reports, and document drafts in Korean by default.
- Keep code, commands, file paths, config keys, and external product names in their original form when needed.
{_STANDARD_RULES}

Additional repository conventions:

- Keep internal reasoning and intermediate classification compact, and avoid long repeated explanations to the user.
- Leave only essential facts in handoff/backlog so session context stays lean.
- Treat `ai-workflow/` as workflow metadata only. Ignore it during normal project document exploration unless the task is explicitly about workflow docs or session state.
"""


def render_opencode_agent(args: argparse.Namespace, context: dict[str, object]) -> str:
    # Ensure smoke check has a sensible default if still TODO
    smoke_check = context['smoke_check_command']
    if "TODO"in str(smoke_check):
        if context['primary_stack'] == 'python':
            smoke_check = "python3 --version"
        elif context['primary_stack'] == 'node':
            smoke_check = "node --version"

    return f"""---
description: Orchestrates the standard AI workflow for this repository
mode: primary
permission:
  edit: deny
  bash: deny
  webfetch: deny
---

You are the workflow orchestrator for this repository.

Start each substantial task by reading:

- `AGENTS.md`
- `ai-workflow/memory/active/<branch>/state.json`
- `ai-workflow/memory/active/<branch>/sessions`
- `ai-workflow/memory/active/<branch>/backlog`
- `docs/PROJECT_PROFILE.md`

Treat `ai-workflow/` as a workflow metadata layer, not part of the normal project work scope. After session restoration, ignore it during project code or project document exploration unless the task explicitly asks for workflow doc maintenance.

You may directly read only the minimum session-restoration set and tiny triage inputs:

- `ai-workflow/memory/active/<branch>/state.json`
- `ai-workflow/memory/active/<branch>/sessions`
- `ai-workflow/memory/active/<branch>/backlog`
- `docs/PROJECT_PROFILE.md`
- one clearly bounded file or path for tiny triage

Project defaults:

- Install: `{context['install_command']}`
- Run: `{context['run_command']}`
- Quick test: `{context['quick_test_command']}`
- Isolated test: `{context['isolated_test_command']}`
- Smoke check: `{smoke_check}`

When the repo is in adoption mode, review `ai-workflow/memory/active/repository_assessment.md` before trusting inferred commands.

User-facing workflow rules:

- Write visible work reports, summaries, and document drafts in Korean by default.
- Keep code, commands, file paths, config keys, and external system names in their original form when useful.
- Use concise progress updates and avoid long repeated reasoning in user-visible messages.
- Keep internal processing compact and preserve only the facts needed for the next step or next session.
- Do not call direct tools yourself. Use only task delegation for repository exploration, comparisons, implementation, checks, and draft generation.
- Use sub-agents aggressively for file exploration, comparisons, log inspection, and draft generation when that helps reduce context pollution.
- Keep the main orchestrator focused on coordination, prioritization, integration, and the final user-facing report.
- Separate broad read-heavy exploration from write tasks when possible so one stream of work does not pollute another stream's context.
- Treat this agent as a read-mostly coordinator with task-only execution: delegate edits, scans, log review, and validation to sub-agents instead of making exceptions for direct tool use.
- Keep direct read narrow: after the session-restoration set, only tiny single-file or single-path triage reads stay local; broader reading goes to workers.
- Ask the user only when a missing decision is genuinely blocking or a risky external action needs confirmation; otherwise make the smallest reasonable assumption and continue through a worker.
- When delegating, give each worker a bounded scope, clear output, and a concise completion contract.
- Prefer `workflow-doc-worker` for large document reads and draft updates, `workflow-code-worker` for bounded implementation, config edits, and build-oriented tasks, and `workflow-validation-worker` for checks and evidence collection.
- If your harness supports per-agent model selection, prefer the main model for this orchestrator and a smaller model for the worker agents by default.
- Do not treat `ai-workflow/` as part of normal project document discovery. Use it only for workflow-state restoration or explicit workflow-maintenance tasks.

{render_memory_update_section()}

> This orchestrator has bash denied, so it never runs the commands above itself — when a
> memory document needs updating, delegate running them to a worker rather than rewriting
> the document by hand.
"""


def render_opencode_worker_agent(args: argparse.Namespace, context: dict[str, object]) -> str:
    # Ensure smoke check has a sensible default if still TODO
    smoke_check = context['smoke_check_command']
    if "TODO"in str(smoke_check):
        if context['primary_stack'] == 'python':
            smoke_check = "python3 --version"
        elif context['primary_stack'] == 'node':
            smoke_check = "node --version"

    return f"""---
description: Executes bounded workflow tasks for this repository
mode: subagent
permission:
  edit: allow
  bash: allow
  webfetch: allow
---

You are a workflow worker for this repository.

You are not the main orchestrator. Your role is to execute a tightly scoped task and return only the essential result.

Before starting, read only the minimum relevant context:

- `AGENTS.md`
- `ai-workflow/memory/active/<branch>/state.json` when it helps restore the current task baseline quickly
- the specific `ai-workflow/memory/active/` document or file paths that match your assigned scope

Project defaults:

- Install: `{context['install_command']}`
- Run: `{context['run_command']}`
- Quick test: `{context['quick_test_command']}`
- Isolated test: `{context['isolated_test_command']}`
- Smoke check: `{smoke_check}`

Worker rules:

- Stay within the assigned file or task scope.
- Prefer doing the actual bounded work instead of producing long plans.
- Summarize only the key facts, edits, risks, and follow-up items needed by the orchestrator.
- Avoid pasting large raw outputs when a short summary is enough.
- If you edit files, keep changes narrow and do not expand into unrelated cleanup.
- If you run checks, report only the command intent and the result that matters.
- Write user-facing drafts in Korean by default unless the assigned task clearly requires another language.
- Minimize asks during execution. Proceed with the smallest reasonable assumption unless the orchestrator explicitly requested a decision point.
- Ignore `ai-workflow/` during normal project document or source exploration unless the assigned task explicitly targets workflow docs or session-state updates.
"""


def render_opencode_doc_worker_agent(args: argparse.Namespace, context: dict[str, object]) -> str:
    return f"""---
description: Executes bounded document-focused workflow tasks for this repository
mode: subagent
permission:
  edit: allow
  bash: allow
  webfetch: allow
---

You are a document-focused workflow worker for this repository.

Your role is to read, compare, summarize, and update a tightly scoped set of documents without pulling unrelated context into the main orchestrator.

Before starting, read only the minimum relevant context:

- `AGENTS.md`
- `ai-workflow/memory/active/<branch>/state.json` when it helps restore the current task baseline quickly
- the assigned `ai-workflow/memory/active/` documents or directly named doc paths

Worker rules:

- Stay within the assigned document scope.
- Prefer concise comparisons, change notes, and draft text over long quotations.
- Return only the facts, inconsistencies, draft wording, and follow-up items needed by the orchestrator.
- Keep user-facing drafts in Korean by default.
- Minimize asks during execution and resolve obvious document-structure choices locally when risk is low.
- If your harness supports per-agent model selection, this worker is a good default target for a smaller model.
- Ignore `ai-workflow/` when looking for project documentation unless the assigned task is explicitly about workflow docs or session-state maintenance.
"""


def render_opencode_code_worker_agent(args: argparse.Namespace, context: dict[str, object]) -> str:
    # Ensure smoke check has a sensible default if still TODO
    smoke_check = context['smoke_check_command']
    if "TODO"in str(smoke_check):
        if context['primary_stack'] == 'python':
            smoke_check = "python3 --version"
        elif context['primary_stack'] == 'node':
            smoke_check = "node --version"

    return f"""---
description: Executes bounded implementation and build-focused workflow tasks for this repository
mode: subagent
permission:
  edit: allow
  bash: allow
  webfetch: allow
---

You are an implementation and build-focused workflow worker for this repository.

Your role is to implement a tightly scoped code or config change, run the minimum relevant build-oriented checks when needed, and report only the essential result back to the orchestrator.

Before starting, read only the minimum relevant context:

- `AGENTS.md`
- `ai-workflow/memory/active/<branch>/state.json` when it helps restore the current task baseline quickly
- the specific source files, tests, and workflow docs tied to your assigned scope

Project defaults:

- Install: `{context['install_command']}`
- Run: `{context['run_command']}`
- Quick test: `{context['quick_test_command']}`
- Isolated test: `{context['isolated_test_command']}`
- Smoke check: `{smoke_check}`

Worker rules:

- Stay within the assigned write scope.
- Prefer shipping the bounded change over expanding into adjacent cleanup.
- Treat build, compile, package, or asset-generation commands as part of your default scope when they are the shortest path to proving the implementation still holds.
- If you run checks, report what matters: pass/fail, key regression risk, build impact, and any deferred follow-up.
- Avoid broad repository exploration unless explicitly assigned.
- Minimize asks during execution. Make bounded implementation choices locally unless the change would alter product behavior or ownership boundaries.
- If your harness supports per-agent model selection, use a smaller model for routine edits and reserve the main model for unusually risky or architectural code tasks.
- Ignore `ai-workflow/` during normal implementation-context discovery unless the assigned task explicitly targets workflow docs or workflow automation.
"""


def render_opencode_validation_worker_agent(args: argparse.Namespace, context: dict[str, object]) -> str:
    # Ensure smoke check has a sensible default if still TODO
    smoke_check = context['smoke_check_command']
    if "TODO"in str(smoke_check):
        if context['primary_stack'] == 'python':
            smoke_check = "python3 --version"
        elif context['primary_stack'] == 'node':
            smoke_check = "node --version"

    return f"""---
description: Executes bounded validation and evidence-collection tasks for this repository
mode: subagent
permission:
  edit: allow
  bash: allow
  webfetch: allow
---

You are a validation-focused workflow worker for this repository.

Your role is to run bounded checks, inspect logs, gather evidence, and return a compact validation summary to the orchestrator.

Before starting, read only the minimum relevant context:

- `AGENTS.md`
- `ai-workflow/memory/active/<branch>/state.json` when it helps restore the current task baseline quickly
- the assigned validation scope, commands, and relevant backlog or handoff notes

Project defaults:

- Quick test: `{context['quick_test_command']}`
- Isolated test: `{context['isolated_test_command']}`
- Smoke check: `{smoke_check}`

Worker rules:

- Stay within the assigned validation scope and command set.
- Report only the result that matters: what ran, what failed or passed, and what evidence should be recorded.
- Avoid flooding the orchestrator with raw logs when a short summary is enough.
- Minimize asks during execution and complete the assigned checks unless the environment is genuinely blocked.
- If your harness supports per-agent model selection, this worker is usually a strong candidate for a smaller model.
- Ignore `ai-workflow/` during normal validation-context discovery unless the assigned task explicitly targets workflow docs or session-state verification.
"""


def write_codex_harness_files(
    args: argparse.Namespace,
    paths: Paths,
    context: dict[str, object],
) -> dict[str, str]:
    codex_config = codex_config_example_path(paths)
    write_text(codex_config, render_codex_config_example(), force=args.force, rel_to=paths.target_root)
    return {
        "codex_config_example": str(codex_config),
    }


def write_opencode_harness_files(
    args: argparse.Namespace,
    paths: Paths,
    context: dict[str, object],
) -> dict[str, str]:
    opencode_config = opencode_config_path(paths)
    opencode_skill = opencode_skill_path(paths)
    opencode_agent = opencode_agent_path(paths)
    opencode_worker_agent = opencode_worker_agent_path(paths)
    opencode_doc_worker_agent = opencode_doc_worker_agent_path(paths)
    opencode_code_worker_agent = opencode_code_worker_agent_path(paths)
    opencode_validation_worker_agent = opencode_validation_worker_agent_path(paths)
    write_text(opencode_config, render_opencode_config(args, paths), force=args.force, rel_to=paths.target_root)
    write_text(opencode_skill, render_opencode_skill(), force=args.force, rel_to=paths.target_root)
    write_text(opencode_agent, render_opencode_agent(args, context), force=args.force, rel_to=paths.target_root)
    write_text(opencode_worker_agent, render_opencode_worker_agent(args, context), force=args.force, rel_to=paths.target_root)
    write_text(opencode_doc_worker_agent, render_opencode_doc_worker_agent(args, context), force=args.force, rel_to=paths.target_root)
    write_text(opencode_code_worker_agent, render_opencode_code_worker_agent(args, context), force=args.force, rel_to=paths.target_root)
    write_text(
        opencode_validation_worker_agent,
        render_opencode_validation_worker_agent(args, context),
        force=args.force,
        rel_to=paths.target_root,
    )
    return {
        "opencode_config": str(opencode_config),
        "opencode_skill": str(opencode_skill),
        "opencode_agent": str(opencode_agent),
        "opencode_worker_agent": str(opencode_worker_agent),
        "opencode_doc_worker_agent": str(opencode_doc_worker_agent),
        "opencode_code_worker_agent": str(opencode_code_worker_agent),
        "opencode_validation_worker_agent": str(opencode_validation_worker_agent),
    }


def write_gemini_cli_harness_files(
    args: argparse.Namespace,
    paths: Paths,
    context: dict[str, object],
) -> dict[str, str]:
    # GEMINI.md is written in write_harness_files if selected,
    # but we can also do it here if we want to be explicit or if we change write_harness_files.
    # Currently write_harness_files writes it.
    return {}


#: 진입 문서의 slash command 한 줄 설명. **목록 자체가 아니라 설명만** 여기 있다 —
#: 무엇이 있는지는 `PLUGIN_SKILLS` 가 정본이고, 여기 없는 slug 도 목록에는 반드시
#: 나온다 (아래 fallback). 고치려던 결함이 정확히 *누락* 이므로, 설명을 빠뜨려
#: 명령이 통째로 사라지는 일은 구조적으로 못 하게 한다.
_ENTRY_COMMAND_BLURBS: dict[str, str] = {
    "session-start": (
        "restore the `state.json` + `session_handoff.md` + `work_backlog.md` baseline"
    ),
    "backlog-update": "register/update a task + scope-creep warning",
    "doc-sync": "sync affected documents (advisory)",
    "session-end": "update handoff + backlog and regenerate `state.json` at session close",
}


def render_entry_command_list() -> str:
    """진입 문서가 안내할 slash command 목록. `PLUGIN_SKILLS` 에서 **파생한다**.

    손으로 쓴 산문이었을 때 (TASK-2026-08-20-main-013): main-008 이 4번째 명령
    (`session-end`)을 배선하고 진입 SKILL.md 도 4종을 안내하게 됐는데, **자동
    read 되는 `CLAUDE.md` 만 3종에 머물렀다.** 같은 어긋남("광고는 4단계인데
    배선은 3개")이 네 번째 자리에서 살아남은 것이다 — 사용자 노출이 가장 큰
    자리에서.

    산문은 그물에 안 걸린다. 그래서 목록을 산문에서 빼내 파생으로 만든다.
    """
    from workflow_kit.plugin_payload import PLUGIN_SKILLS  # noqa: PLC0415

    lines = []
    for spec in PLUGIN_SKILLS:
        blurb = _ENTRY_COMMAND_BLURBS.get(spec.slug)
        suffix = f" — {blurb}" if blurb else ""
        lines.append(f"- `/workflow-{spec.slug}`{suffix}")
    return "\n".join(lines)


def render_claude_code_agents(args: argparse.Namespace, context: dict[str, object]) -> str:
    """Render ``CLAUDE.md`` (Claude Code 진입점) — v0.10.2 진입점 정정.

    Claude Code 는 *root 진입점* 으로 ``CLAUDE.md`` 를 자동 read (v0.10.1 의
    잘못된 가정 정정). 본 render 는 표준 AI workflow 의 *지시* + AGENTS.md 와의
    *정합* 을 한국어로 명시. 기존 AGENTS.md 가 있으면 `@AGENTS.md` import 안내.
    """
    _STANDARD_RULES = render_entrypoint_rules()
    _ENTRY_COMMANDS = render_entry_command_list()
    return f"""# CLAUDE.md (Claude Code entry point)

- Purpose: the *directional intent* of the standard AI workflow, plus the entry rules Claude Code needs every session
- Scope: session restore, the order to consult workflow state docs, working principles, session close order
- Audience: Claude Code, repository maintainer, workflow designer
- Status: beta
- Last updated: {args.today}
- Related: `ai-workflow/memory/active/<branch>/state.json`, `docs/PROJECT_PROFILE.md`

## What this file is for

- **Role**: the entry-point document Claude Code *reads automatically at session start* in this repository.
- **Location**: `./CLAUDE.md` (or `./.claude/CLAUDE.md`) — both are read automatically.
- **Relationship to AGENTS.md**: Claude Code does *not* read `AGENTS.md` directly. If this
  project already has one, pull it in from `CLAUDE.md` with an `@AGENTS.md` import or a symlink:

  ```bash
  # import (add a single @AGENTS.md line inside CLAUDE.md)
  @AGENTS.md

  # or symlink (prefer the import for cross-platform setups)
  ln -s AGENTS.md CLAUDE.md
  ```

## Read these first

> `<branch>` is the current git branch name (`main` when this is not a git repository). Splitting per branch keeps concurrent work from overwriting itself.

- `ai-workflow/memory/active/<branch>/state.json`
- `ai-workflow/memory/active/<branch>/sessions`
- `ai-workflow/memory/active/<branch>/backlog`
- `docs/PROJECT_PROFILE.md`
- `ai-workflow/wiki/index.md` — R4 anchor based; load this first when an AI agent queries
- (if present) `ai-workflow/memory/active/PURPOSE.md` — directional intent one-liner + body excerpt

`ai-workflow/` is a meta layer for session restore and workflow state. Do not include it in
the default search scope when exploring project code or project documents — reference it only
when updating the workflow documents themselves or restoring the current session state.

## Entry slash commands (additive)

{_ENTRY_COMMANDS}

{_STANDARD_RULES}

## Language and context principles

- Write user-facing work reports, status summaries, and document updates in Korean by default.
- Keep code, commands, file paths, configuration keys, and external product names verbatim.
- Handle internal reasoning and scratch classification however is most efficient, but give
  the user only the conclusion and the next action.
- Avoid long intermediate reasoning, repeated summaries, and unnecessary self-explanation.
- Keep only the facts the next session needs in the handoff and backlog, so context does not pile up.

## self-bootstrap (when PURPOSE.md / state.json are absent)

When `state.json` or `PURPOSE.md` is absent, the session-start skill *skips gracefully*.
When the user invokes `/workflow-session-start` (or on automatic read), it attempts a
*minimum-effort* baseline restore:

1. `ai-workflow/memory/active/<branch>/state.json` missing → offer to scaffold it
2. `PURPOSE.md` missing → 4-element placeholder + suggest a light `init` call
3. `work_backlog.md` missing → empty index + guidance for registering the first task

## Project run defaults

- **install**: {context.get('install_command', 'TODO')}
- **run**: {context.get('run_command', 'TODO')}
- **quick test**: {context.get('quick_test_command', 'TODO')}
- **isolated test**: {context.get('isolated_test_command', 'TODO')}
- **smoke check**: {context.get('smoke_check_command', 'TODO')}

These commands are inferred. Correct them to the project's real commands before committing.

## Read next

- `ai-workflow/README.md` (kit overview)
- `docs/PROJECT_PROFILE.md` (project metadata)
- `ai-workflow/memory/active/<branch>/sessions` (current session handoff)
- `harnesses/claude-code/apply_guide.md` (Claude Code apply procedure)
"""


def render_claude_code_session_start_command(args: argparse.Namespace, context: dict[str, object]) -> str:
    """Render ``.claude/commands/workflow-session-start.md`` slash command.

    Claude Code 의 `/workflow-session-start` slash command. session-start skill 의
    *진입점* 으로 작동 (AGENTS.md 가 없는 skill-only 진입 환경). command body 는
    표준 session-start skill 의 *역할* 을 한국어로 설명.

    frontmatter 의 `description` 은 필수다. 없으면 Claude Code 가 **첫 줄을 설명으로
    쓰는데**, 그 자리에는 `write_text` 가 찍는 버전 마커가 앉는다 — 실제로 명령 목록에
    `<!-- standard-ai-workflow-kit: v… -->` 가 설명으로 떴다 (2026-08-05 실측).
    """
    return f"""---
description: Standard AI workflow session start — restore the current baseline from state.json + session_handoff.md + backlog and report the next candidate tasks.
---

# /workflow-session-start

> Claude Code slash command. The *session-start* entry point of the standard AI workflow.

## Role

This command restores the *current baseline* from `ai-workflow/memory/active/`:

1. Read `state.json` — `latest_backlog_path` + `in_progress_items` + `recent_done_items`
2. Read `session_handoff.md` — what the previous session handed over
3. Read `work_backlog.md` — the anchor for the current task list
4. Read `PROJECT_PROFILE.md` — project metadata
5. Read `PURPOSE.md` if present — directional intent one-liner + body excerpt ≤200 tokens

## Usage

This work goes **through the tools** — hand-editing the documents silently breaks the parsing contract (canonical §11).

```bash
{find_memory_command(load_standard_rules(), "Restore session-start baseline")} --help
```

## Procedure

1. Read `ai-workflow/memory/active/<branch>/state.json` first and summarize the current baseline
2. Pick 3–7 candidate follow-up tasks from the anchors in `session_handoff.md` + `work_backlog.md`
3. Report, in Korean: a one-line summary, 3–5 next-task candidates, and the recommended next action
4. When the tool output carries `roadmap_context` (ADR-027 — the project has
   `ai-workflow/memory/active/roadmap/`), fold the current milestone, SDLC phase, and
   next WBS candidates into the report; no roadmap → skip silently
4. **No intermediate reasoning, repeated summaries, or self-explanation** — give the user the *conclusion* only

## Language and context rules

- User-facing reports are in Korean
- Code, commands, file paths, and configuration keys stay verbatim
- Keep only the *facts the next session actually needs* in the handoff / backlog, to minimize context buildup

## next step

After reporting the summary and candidates, once the user confirms:
- `/workflow-backlog-update` to register today's work
- or `/workflow-doc-sync` to sync affected documents

## Related documents

- `ai-workflow/memory/active/<branch>/state.json`
- `ai-workflow/memory/active/<branch>/sessions`
- `ai-workflow/memory/active/<branch>/backlog`
- `docs/PROJECT_PROFILE.md`
- (if present) `ai-workflow/memory/active/PURPOSE.md`
"""


def render_claude_code_session_end_command(args: argparse.Namespace, context: dict[str, object]) -> str:
    """Render ``.claude/commands/workflow-session-end.md`` slash command.

    **왜 뒤늦게 생겼나** (TASK-2026-08-20-main-008): 플러그인 채널은 처음부터
    스킬 4종(session-start / backlog-update / doc-sync / **session-end**)을
    내보냈는데, bootstrap 채널은 3종만 emit 했다. 두 채널이 같은 킷의 같은
    절차를 서로 다른 집합으로 노출하고 있었고, `.claude/` 로 쓰는 프로젝트에서는
    **세션 종료 절차만 진입점이 없었다**.

    더 나쁜 것은 진입 스킬(`render_claude_code_skill`)의 `description` 이 이미
    "세션을 종료하며 handoff 를 남길 때 사용한다" 고 **약속**하고 있었다는 점이다 —
    광고와 배선이 어긋나면 모델은 있지도 않은 명령을 찾는다.

    frontmatter 의 `description` 은 필수다 (session-start 주석 참조).
    """
    return f"""---
description: Standard AI workflow session end — update the handoff and backlog, regenerate state.json, and leave the state so the next session resumes directly.
---

# /workflow-session-end

> Claude Code slash command. The *session-end* entry point of the standard AI workflow.

## Role

Close the session, leaving the state so the next session can pick it up directly.

## Order

{load_standard_rules().close_order}

## Procedure

1. Update `session_handoff.md` — current baseline, in-progress / blocked / recently-done lists.
2. Bring the task statuses in today's backlog in line with the actual results
   (`planned` / `in_progress` / `blocked` / `done`).
3. **Regenerate** `state.json` — never hand-edit it (see the parsing contract below).
4. Judge memory_index promotion candidates once (advisory, writes nothing).
5. Make sure the updates from 1–4 land in the **same commit**, then push.

## Usage

This work goes **through the tools** — hand-editing the documents silently breaks the parsing contract (canonical §11).

```bash
{find_memory_command(load_standard_rules(), "Regenerate state.json at session close")} --help
```

If the CLI is missing, do not skip silently — report the installation guidance and stop
(`INSTALLATION_AND_USAGE.md` §3). A hand-written `state.json` that was never regenerated
diverges from its input documents.

## Language and context rules

- User-facing reports are in Korean
- Code, commands, file paths, and configuration keys stay verbatim
- Keep only the *facts the next session actually needs* in the handoff / backlog

## Related documents

- `ai-workflow/memory/active/<branch>/session_handoff.md`
- `ai-workflow/memory/active/<branch>/backlog`
- `ai-workflow/memory/active/<branch>/state.json`
"""


def render_claude_code_backlog_update_command(args: argparse.Namespace, context: dict[str, object]) -> str:
    """Render ``.claude/commands/workflow-backlog-update.md`` slash command.

    backlog-update skill 의 *진입점*. task_brief + affected_documents vs
    PURPOSE.md §3 Research Scope *제외 영역* 매칭 → scope creep 경고.

    `description` 이 필수인 이유는 ``render_claude_code_session_start_command`` 참조.
    """
    return f"""---
description: Standard AI workflow backlog update — register/update a task in today's backlog and warn about scope creep when it overlaps PURPOSE.md's excluded areas.
---

# /workflow-backlog-update

> Claude Code slash command. The *backlog-update* entry point of the standard AI workflow.

## Role

Register or update today's work item in `ai-workflow/memory/active/<branch>/backlog/<YYYY-MM-DD>.md`.

## Usage

This work goes **through the tools** — hand-editing the documents silently breaks the parsing contract (canonical §11).

```bash
{find_memory_command(load_standard_rules(), "Register / update a task")} --help
```

## Procedure

1. Check the index anchor in `ai-workflow/memory/active/<branch>/backlog`
2. Today's `backlog/YYYY-MM-DD.md` file:
   - create it if absent
   - append to the existing entries if present
3. **in-scope check** (match against PURPOSE.md §3 Research Scope *excluded areas*):
   - `task_brief` + `affected_documents` vs excluded areas, by substring / first-2-token match
   - on a match, emit one `scope_creep_warnings` line (hard warning)
4. Task status: one of `planned` / `in_progress` / `blocked` / `done`
5. State priority, owner, and acceptance criteria
6. **roadmap gate** (ADR-027 §6) — when `ai-workflow/memory/active/roadmap/` exists,
   creating a task requires `--wbs M-NNN/WBS-N.N`; off-roadmap work is declared with
   `--wbs exempt --wbs-exempt-reason "<why>"`. Projects without a roadmap are unaffected.

## When PURPOSE.md is absent

`scope_creep_warnings = []` (graceful skip). No body reference is possible — advisory only.

## Read next

- `ai-workflow/memory/active/<branch>/backlog`
- (if present) `ai-workflow/memory/active/PURPOSE.md`
- The documents that will be affected

## Language rules

- Work reports, status summaries, update text = Korean
- Code, file paths, external product names = verbatim
"""


def render_claude_code_doc_sync_command(args: argparse.Namespace, context: dict[str, object]) -> str:
    """Render ``.claude/commands/workflow-doc-sync.md`` slash command.

    doc-sync skill 의 *진입점*. 영향 받은 문서 후보 추천 + 허브 / index 갱신 포인트.

    `description` 이 필수인 이유는 ``render_claude_code_session_start_command`` 참조.
    """
    return f"""---
description: Standard AI workflow document sync — derive affected-document candidates from the changed files and propose wiki-index update points as advisory.
---

# /workflow-doc-sync

> Claude Code slash command. The *doc-sync* entry point of the standard AI workflow.

## Role

After the work, identify the affected-document candidates and lay out the hub / index
update points under `ai-workflow/memory/active/`.

## Usage

This work goes **through the tools** — hand-editing the documents silently breaks the parsing contract (canonical §11).

```bash
{find_memory_command(load_standard_rules(), "Sync affected documents")} --help
```

## Procedure

1. Identify the current changed-file list and the affected-document candidates
2. Check the page catalog against the `ai-workflow/wiki/index.md` anchors
3. Emit *advisory* update points for the affected pages:
   - Candidate new concept / decision / pattern pages
   - Existing pages whose `last_touched` should be refreshed
4. When PURPOSE.md is absent: *advisory only* (no hard scope check)

## Output format

- The affected-document list (path + one-line summary)
- Recommended anchors / cross-references
- confidence (high / medium / low)

## Read next

- `ai-workflow/wiki/index.md`
- (if present) `ai-workflow/memory/active/PURPOSE.md`

## Language rules

- Update-point reports = Korean
- File paths, anchors, configuration keys = verbatim
"""


def render_claude_code_skill(args: argparse.Namespace, context: dict[str, object]) -> str:
    """Render ``.claude/skills/standard-ai-workflow/SKILL.md`` (model-invoked skill).

    slash command 4종과 **호출 주체가 다르다**: command 는 사용자가 `/` 로 부르고,
    skill 은 모델이 `description` 을 보고 스스로 고른다. 사용자가 "세션 시작하자" 처럼
    *명령 이름을 모르는 채* 말할 때 진입할 자리가 그동안 없었다.

    frontmatter 는 정적으로 유지한다 — ``tests/check_harness_skill_frontmatter.py``
    의 case 0 이 값 보간을 거부한다 (보간값이 `: ` 나 줄바꿈을 담으면 YAML 이
    조용히 깨진다).
    """
    _STANDARD_RULES = render_entrypoint_rules()
    return f"""---
name: standard-ai-workflow
description: The standard AI workflow entry point for this repository. Use it when starting or resuming a session, registering/updating a task in the backlog, syncing affected documents after a change, or leaving a handoff at session close.
---

# Standard AI Workflow

- **Role**: the entry skill that covers session start, backlog update, document sync, and session close in one place.
- **Location**: `.claude/skills/standard-ai-workflow/SKILL.md`
- **Invocation**: the model selects it automatically when the situation matches the `description` above. To invoke it directly,
  `/workflow-session-start`, `/workflow-backlog-update`, `/workflow-doc-sync`, `/workflow-session-end` slash command.
- Last updated: {args.today}

## 1. Session start — always read these first

1. `ai-workflow/memory/active/<branch>/state.json` — the current baseline
2. `ai-workflow/memory/active/<branch>/sessions` — the previous session's handoff
3. `ai-workflow/memory/active/<branch>/backlog` — the work backlog index
4. `docs/PROJECT_PROFILE.md` — project metadata
5. (if present) `ai-workflow/memory/active/PURPOSE.md` — directional intent

After reading, report in Korean only: **a one-line baseline summary, 3–5 next-task
candidates, and the recommended next action.** No intermediate reasoning, repeated
summaries, or self-explanation.

If `state.json` or `PURPOSE.md` is absent, do not treat it as a failure — *skip gracefully*
and offer to scaffold it.

## 2. Backlog update

Register today's work in `ai-workflow/memory/active/<branch>/backlog/<YYYY-MM-DD>.md` and
`./tasks/<TASK-ID>.md`. Use only the four status values `planned` / `in_progress` /
`blocked` / `done`. If it overlaps an excluded area in `PURPOSE.md` §3, leave a one-line
scope-creep warning.

## 3. Document sync (advisory)

Derive affected-document candidates from the changed files and *recommend* update points
against the `ai-workflow/wiki/index.md` anchors. Never apply them automatically.

## 4. Session close

Close the session so the next one resumes directly: update `session_handoff.md`, bring
today's backlog task statuses in line with the actual results, **regenerate** `state.json`
(never hand-edit it), and judge memory_index promotion candidates once. All of it lands in
the **same commit** as the work it describes — see the close order below.

{_STANDARD_RULES}

## Language and context principles

- User-facing reports, status summaries, and document text are in Korean.
- Code, commands, file paths, configuration keys, and external product names stay verbatim.
- Keep only the facts the next session needs in the handoff and backlog.
- `ai-workflow/` is the workflow meta layer. Do not include it in the default project code/document search scope.
"""


def write_claude_code_harness_files(
    args: argparse.Namespace,
    paths: Paths,
    context: dict[str, object],
) -> dict[str, str]:
    """Generate Claude Code harness overlay files (v1.0.4+, 3 slash command + 1 skill).

    Claude Code 의 진입점 = CLAUDE.md (root, 자동 read) + .claude/commands/*.md
    (slash command, 사용자 호출) + .claude/skills/*/SKILL.md (모델 자동 선택).
    본 함수는 `.claude/` 아래 4개 파일을 emit 한다. CLAUDE.md 자체는
    ``write_harness_files`` 의 진입점 dispatch 에서 emit (``render_claude_code_agents``).

    4 slash command (v1.3.1+: session-end 합류 — 플러그인 채널과 집합을 맞춘다):
    - ``workflow-session-start`` — baseline 복원
    - ``workflow-backlog-update`` — 작업 등록/갱신
    - ``workflow-doc-sync`` — 영향 문서 동기화
    - ``workflow-session-end`` — 세션 종료 (handoff/backlog 갱신 + state 재생성)

    1 skill (v1.0.4+):
    - ``standard-ai-workflow`` — 위 4종의 *모델 호출* 진입점. opencode / grok-build 는
      진작 skill 을 내보내고 있었는데 claude-code 만 없었다.
    """
    generated: dict[str, str] = {}
    claude_root = paths.target_root / ".claude" / "commands"

    session_start_cmd = claude_root / "workflow-session-start.md"
    backlog_update_cmd = claude_root / "workflow-backlog-update.md"
    doc_sync_cmd = claude_root / "workflow-doc-sync.md"
    session_end_cmd = claude_root / "workflow-session-end.md"
    skill_file = paths.target_root / ".claude" / "skills" / "standard-ai-workflow" / "SKILL.md"

    write_text(session_start_cmd, render_claude_code_session_start_command(args, context), force=args.force, rel_to=paths.target_root)
    generated["claude_code_session_start_command"] = str(session_start_cmd)
    write_text(backlog_update_cmd, render_claude_code_backlog_update_command(args, context), force=args.force, rel_to=paths.target_root)
    generated["claude_code_backlog_update_command"] = str(backlog_update_cmd)
    write_text(doc_sync_cmd, render_claude_code_doc_sync_command(args, context), force=args.force, rel_to=paths.target_root)
    generated["claude_code_doc_sync_command"] = str(doc_sync_cmd)
    write_text(session_end_cmd, render_claude_code_session_end_command(args, context), force=args.force, rel_to=paths.target_root)
    generated["claude_code_session_end_command"] = str(session_end_cmd)
    write_text(skill_file, render_claude_code_skill(args, context), force=args.force, rel_to=paths.target_root)
    generated["claude_code_skill"] = str(skill_file)

    return generated


# ---------------------------------------------------------------------------
# Aider adapter (v0.10.2+)
# ---------------------------------------------------------------------------
def render_aider_conventions(args: argparse.Namespace, context: dict[str, object]) -> str:
    """Render ``CONVENTIONS.md`` (Aider 진입점) + .aider/conventions.md 동일.

    Aider 는 ``--read`` flag 또는 ``.aider.conf.yml`` 의 ``read`` list 에 등록된
    파일을 자동 read. CONVENTIONS.md 를 root 와 .aider/ 양쪽에 emit 하면
    Aider 의 default 동작과 ``.aider.conf.yml`` 명시 read 둘 다 cover.
    """
    _STANDARD_RULES = render_entrypoint_rules()
    return f"""# Aider Conventions (CONVENTIONS.md)

- **Role**: the conventions document Aider *reads automatically at session start* in this repository.
- **Location**: both the root `CONVENTIONS.md` and `.aider/conventions.md` (identical content).
- Aider reads the root `CONVENTIONS.md` automatically (when it is listed in `read:` in `.aider.conf.yml`).
- Audience: Aider, repository maintainer
- Last updated: {args.today}

## Standard AI workflow entry

This project follows the standard AI workflow. Read in this order:

1. `ai-workflow/memory/active/<branch>/state.json`
2. `ai-workflow/memory/active/<branch>/sessions`
3. `ai-workflow/memory/active/<branch>/backlog`
4. `docs/PROJECT_PROFILE.md`
5. (if present) `ai-workflow/memory/active/PURPOSE.md`

{_STANDARD_RULES}

## Reporting rules

- Report to the user in Korean; keep code, commands, paths, and configuration keys verbatim
- Keep only the *facts the next session actually needs* in the handoff and backlog

## Aider-specific config

- Confirm `CONVENTIONS.md` is listed in `read:` in `.aider.conf.yml`
- Commit messages: Korean with English technical terms
- On a weak-model fallback (3.5 / 4o-mini), read this file first — it is the light one

## Read next

- `harnesses/aider/apply_guide.md` (apply procedure)
- `ai-workflow/README.md`
"""


def render_aider_config_example(args: argparse.Namespace, context: dict[str, object]) -> str:
    """Render ``.aider.conf.yml.example`` (Aider 가 자동 read 하는 파일 목록)."""
    return f"""# Aider config example (v0.10.2+)
#
# The file list Aider reads in this project, plus model settings.
# Usage: `cp .aider.conf.yml.example .aider.conf.yml`, then edit as needed.

# Conventions / workflow documents to auto-read
read:
  - CONVENTIONS.md
  - ai-workflow/memory/active/<branch>/state.json
  - ai-workflow/memory/active/<branch>/sessions
  - ai-workflow/memory/active/<branch>/backlog
  - docs/PROJECT_PROFILE.md
  - ai-workflow/memory/active/PURPOSE.md

# model: default
model: claude-3-5-sonnet-20241022

# weak model (commit message + lint)
weak-model: claude-3-5-haiku-20241022

# auto-commit
auto-commits: false
# Let Aider write only the *commit message*; a reviewer decides the actual commit

# commit message language: Korean
commit-language: ko

# lint command (smoke test)
lint-cmd: {context.get('smoke_check_command', 'echo TODO: lint command')}

# test command
test-cmd: {context.get('quick_test_command', 'echo TODO: test command')}
"""


def write_aider_harness_files(
    args: argparse.Namespace,
    paths: Paths,
    context: dict[str, object],
) -> dict[str, str]:
    """Generate Aider harness overlay files (v0.10.2+)."""
    generated: dict[str, str] = {}
    conventions = paths.target_root / "CONVENTIONS.md"
    aider_conventions = paths.target_root / ".aider" / "conventions.md"
    aider_config = paths.target_root / ".aider.conf.yml.example"

    body = render_aider_conventions(args, context)
    write_text(conventions, body, force=args.force, rel_to=paths.target_root)
    generated["aider_conventions_root"] = str(conventions)
    write_text(aider_conventions, body, force=args.force, rel_to=paths.target_root)
    generated["aider_conventions_aider_dir"] = str(aider_conventions)
    write_text(aider_config, render_aider_config_example(args, context), force=args.force, rel_to=paths.target_root)
    generated["aider_config_example"] = str(aider_config)

    return generated


# ---------------------------------------------------------------------------
# Goose adapter (v0.10.2+)
# ---------------------------------------------------------------------------
def render_goose_config(args: argparse.Namespace, context: dict[str, object]) -> str:
    """Render ``.goose/config.yaml`` (Goose extension 등록 config).

    명령 문자열은 전부 정본 §11.1 에서 꺼낸다 (`find_memory_command`) — 여기 박힌
    `wk …` 손 사본이 §11.1 개명 시 낡던 결함(TASK-026)과, `on_session_end` 가
    존재하지 않는 `skills/` 경로 + 없는 플래그를 부르던 결함(TASK-022 잔여)의 처방.
    """
    rules = load_standard_rules()
    session_start_cmd = find_memory_command(rules, "Restore session-start baseline")
    backlog_update_cmd = find_memory_command(rules, "Register / update a task")
    doc_sync_cmd = find_memory_command(rules, "Sync affected documents")
    refresh_state_cmd = find_memory_command(rules, "Regenerate state.json")
    return f"""# Goose config (v0.10.2+)
#
# Goose enters the workflow through extension registration. This config registers the
# *key entry points* of standard_ai_workflow as Goose pre/post hooks.
# Usage: Goose loads it automatically (or `goose config load`).

version: 1
project:
  name: {context.get('project_name', 'TODO')}
  workflow: standard-ai-workflow

# Register the standard AI workflow entry points
entry_points:
  session_start:
    description: "restore the state.json + handoff + work_backlog baseline"
    command: "{session_start_cmd}"
    trigger: on_session_start
  backlog_update:
    description: "register/update a task + scope-creep warning"
    command: "{backlog_update_cmd}"
    trigger: manual
  doc_sync:
    description: "sync affected documents (advisory)"
    command: "{doc_sync_cmd}"
    trigger: manual

# This project's *entry documents* (Goose reads them at startup)
read_files:
  - ai-workflow/memory/active/<branch>/state.json
  - ai-workflow/memory/active/<branch>/sessions
  - ai-workflow/memory/active/<branch>/backlog
  - docs/PROJECT_PROFILE.md
  - ai-workflow/memory/active/PURPOSE.md

# Goose *pre/post hooks* — regenerate state.json at session close (canonical §11)
hooks:
  on_session_end:
    - "{refresh_state_cmd}"

# language: Korean
language: ko
"""


def write_goose_harness_files(
    args: argparse.Namespace,
    paths: Paths,
    context: dict[str, object],
) -> dict[str, str]:
    """Generate Goose harness overlay files (v0.10.2+)."""
    generated: dict[str, str] = {}
    goose_config = paths.target_root / ".goose" / "config.yaml"

    write_text(goose_config, render_goose_config(args, context), force=args.force, rel_to=paths.target_root)
    generated["goose_config"] = str(goose_config)

    return generated


# ---------------------------------------------------------------------------
# Custom adapter (v0.10.2+) — a *neutral* adapter the caller wires up
# ---------------------------------------------------------------------------
def render_custom_skill_template(args: argparse.Namespace, context: dict[str, object]) -> str:
    """Render ``.workflow-kits/custom/SKILL.md`` (custom adapter 의 *neutral* 진입점).

    Custom adapter 는 *어떤 특정 하네스에도 종속되지 않는* 중립 진입점.
    Caller 가 자사의 internal harness / IDE / CLI 에 맞게 wire-up.
    """
    return f"""# Custom Workflow Kit Skill Template (v0.10.2+)

- **Role**: the *neutral entry point* of the standard AI workflow — the caller wires it up to
  their own harness / IDE / CLI. This file is a *reference template* only; no tool loads it automatically.
- **Location**: `.workflow-kits/custom/SKILL.md`
- Audience: custom harness users (callers)
- Last updated: {args.today}

## Entry contract

This skill's *contract* matches the output schemas of the three standard AI workflow skills:

1. **session-start**: restore the baseline from `state.json` + `session_handoff.md` + `work_backlog.md` + `PROJECT_PROFILE.md` + `PURPOSE.md` (if present). Report, in Korean, a one-line summary, 3–5 next-task candidates, and the recommended next action.
2. **backlog-update**: register/update today's task + scope-creep warning (matched against PURPOSE.md §3 excluded areas). Four task states (`planned` / `in_progress` / `blocked` / `done`).
3. **doc-sync**: identify affected documents + candidate anchor updates (advisory).

## Caller wire-up examples

Import, include, or reference this file from your own harness / IDE / CLI.

```bash
# e.g. an in-house internal CLI
ln -s .workflow-kits/custom/SKILL.md ~/.internal-cli/standard-ai-workflow.md
```

```python
# e.g. loading this file as a *reference doc* from an in-house Python tool
with open(".workflow-kits/custom/SKILL.md") as f:
    workflow_skill = f.read()
# → append to the caller tool's system prompt
```

## self-bootstrap (when PURPOSE.md / state.json are absent)

When this skill's caller invokes session-start:
1. `state.json` missing → create an empty placeholder and offer to scaffold it
2. `PURPOSE.md` missing → 4-element placeholder + suggest a light `init` call
3. `work_backlog.md` missing → empty index + guidance for registering the first task

{render_memory_update_section()}

## Read next

- `harnesses/custom/apply_guide.md` (caller wire-up procedure)
- `ai-workflow/README.md`
"""


def write_custom_harness_files(
    args: argparse.Namespace,
    paths: Paths,
    context: dict[str, object],
) -> dict[str, str]:
    """Generate Custom harness overlay files (v0.10.2+, neutral 진입점)."""
    generated: dict[str, str] = {}
    custom_skill = paths.target_root / ".workflow-kits" / "custom" / "SKILL.md"

    write_text(custom_skill, render_custom_skill_template(args, context), force=args.force, rel_to=paths.target_root)
    generated["custom_skill_template"] = str(custom_skill)

    return generated


def pi_dev_agents_supplement(
    args: argparse.Namespace,
    context: dict[str, object],
    *,
    base: str,
) -> str:
    """codex 판 `AGENTS.md` 뒤에 붙일 **pi-dev 전용 장**을 만들어 합친 문서를 돌려준다.

    v1.0.2 — pi-dev 와 codex/opencode 는 같은 root `AGENTS.md` 를 읽는다. 이전에는
    나중에 도는 쪽이 조용히 덮어써서 한쪽 하네스의 지침이 통째로 사라졌다. 파일이
    하나뿐이라면 답은 덮어쓰기가 아니라 합치기다.

    공통 규칙 블록(`## 작업 원칙` / `## 세션 종료 순서`)은 base 에 이미 있으므로
    다시 넣지 않는다 — 정본에서 생성되는 블록을 한 파일에 두 번 두면 그 자체가
    사본이 된다 (`check_standard_single_source.py` 가 보는 규약).

    이미 붙어 있으면 그대로 돌려준다 (idempotent — bootstrap 재실행 안전).
    """
    if PI_DEV_SUPPLEMENT_HEADING in base:
        return base
    body = render_pi_dev_agents(args, context)
    # pi-dev 판에서 harness-specific 장(`## 1.` 이후)만 떼어 낸다.
    marker = "## 1. Session start routine"
    idx = body.find(marker)
    specific = body[idx:] if idx >= 0 else body
    # base 에 이미 있는 **생성 블록**은 빼고 붙인다. 한 파일에 두 번 들어가면 그
    # 자체가 사본이고, 나중에 한쪽만 고쳐지면 갈라진다. v1.1.7 (TASK-028) 부터
    # pi-dev 단독판은 전체 블록(§1·§3·§8·§11)을 실으므로, 병합 시에는 그 블록을
    # **통째로** 제거한다 (렌더 문자열이 같으므로 exact substring 제거가 성립).
    specific = specific.replace(render_entrypoint_rules(), "")
    close_order = load_standard_rules().close_order
    specific = "\n".join(
        line for line in specific.splitlines() if close_order not in line
    )
    return (
        base.rstrip()
        + f"\n\n---\n\n{PI_DEV_SUPPLEMENT_HEADING}\n\n"
        + "> This repository uses codex/opencode and pi-dev together. The shared rules above\n"
        + "> apply to both harnesses; what follows is specific to the Pi Coding Agent.\n\n"
        + specific.strip()
        + "\n"
    )


def render_pi_dev_agents(args: argparse.Namespace, context: dict[str, object]) -> str:
    # v1.1.7 (TASK-2026-08-11-main-028): §8 한 줄만 pull 하던 것을 전체 생성 블록으로.
    # 단독 사용 시에도 §1·§3·§8·§11 이 실린다. codex 와 병합될 때는
    # `render_codex_pi_dev_shared_agents` 가 이 블록을 통째로 제거해 중복을 막는다.
    _STANDARD_RULES = render_entrypoint_rules()
    return f"""# AGENTS.md (Pi Coding Agent Profile)

- **Mandate**: this repository follows the 'Standard AI Workflow'. Base every action on the state in the documents below.
- **Priority Docs**:
    1. `ai-workflow/memory/active/<branch>/state.json` (source of truth for the current session)
    2. `ai-workflow/memory/active/<branch>/sessions` (what the previous session handed over)
    3. `ai-workflow/memory/active/<branch>/backlog` (task list)

## 1. Session start routine (mandatory)
At session start, read `ai-workflow/memory/active/<branch>/state.json` first and take in `current_focus` and `next_documents`. Then read `session_handoff.md` and resume from where the previous session stopped.

## 2. Working principles (Research → Strategy → Execution)
- **Research**: use `grep_search` and `read_file` to establish the current state of the code and documents objectively.
- **Strategy**: plan the change and decide which documents to update before and after the work.
- **Execution**: carry out the change with the `edit`, `write`, and `bash` tools.

## 3. Workflow state management
- Whenever a task's status changes, update the matching dated document under `ai-workflow/memory/active/<branch>/backlog/`.
- Before closing the session, update `ai-workflow/memory/active/<branch>/state.json` and `session_handoff.md` so the next agent keeps the context.
- Update state documents with the tools under "Memory Update Paths" below — writing by hand silently breaks the parsing contract.

## 4. Tool usage
- For complex workflow control (automatic state updates and the like), use the `wk` tools under "Memory Update Paths" below.
- Prefer handling every tool result as structured JSON.

## 5. Language
- Use Korean when reporting to the user or writing documents.
- Keep code and technical names verbatim.

{_STANDARD_RULES}
"""


def write_pi_dev_harness_files(
    args: argparse.Namespace,
    paths: Paths,
    context: dict[str, object],
) -> dict[str, str]:
    # Pi Coding Agent primarily uses AGENTS.md at the root
    # We will also create a pi-dev specific apply guide if possible
    return {}


def write_antigravity_harness_files(
    args: argparse.Namespace,
    paths: Paths,
    context: dict[str, object],
) -> dict[str, str]:
    return {}


# ---------------------------------------------------------------------------
# Grok Build adapter (v0.15.16+)
# ---------------------------------------------------------------------------
# Grok Build (xAI CLI TUI) 진입점:
#   - AGENTS.md: Codex 와 공통 root 진입점 (codex/opencode/pi-dev 와 동시 선택 시 자동 emit)
#   - GROK.md: Grok Build root entry point (additive rule, Korean baseline + subagent pattern)
#   - .grok/skills/standard-ai-workflow/SKILL.md: skill shown in the TUI picker
#   - .grok/config.toml.example: MCP stdio snippet + skill paths + memory opt-in
#
# AGENTS.md is already emitted by render_codex_agents in the codex/opencode/pi-dev dispatch
# block, so this render emits only GROK.md (idempotent; safe alongside codex).


def render_grok_build_agents(args: argparse.Namespace, context: dict[str, object]) -> str:
    """Render ``GROK.md`` — the Grok Build harness entry file.

    Grok Build 는 ``AGENTS.md`` 와 ``GROK.md`` 를 모두 자동 read. ``AGENTS.md`` 는
    Codex 와 공통 진입점 (codex/opencode/pi-dev dispatch block 에서 emit) 이므로
    본 render 는 ``GROK.md`` 만 emit. 두 문서가 가리키는 사실이 다르다면
    ``GROK.md`` 가 우선 (Grok Build 세션에서 additive rule).
    """
    harness_note = (
        "This draft reflects an analysis of the existing codebase. The inferred commands and document paths may need to be corrected against the real repository."
        if args.adoption_mode == "existing"
        else "This is a new-project draft. Verify that the project's own run commands and document structure are correct."
    )
    smoke_check = context['smoke_check_command']
    if "TODO" in smoke_check:
        if context['primary_stack'] == 'python':
            smoke_check = "python3 --version"
        elif context['primary_stack'] == 'node':
            smoke_check = "node --version"

    _STANDARD_RULES = render_entrypoint_rules()
    return f"""# GROK.md (Grok Build entry point)

- Purpose: the entry-point document Grok Build (the xAI CLI TUI) reads automatically every session in this repository.
- Scope: session restore, the order to consult workflow state docs, user-facing report language, subagent / memory / MCP principles
- Audience: Grok Build, repository maintainer, multi-agent operator
- Status: beta
- Last updated: {args.today}
- Related: `AGENTS.md` (shared with Codex), `ai-workflow/memory/active/<branch>/state.json`, `ai-workflow/memory/active/<branch>/sessions`, `ai-workflow/memory/active/<branch>/backlog`, `docs/PROJECT_PROFILE.md`

## Purpose

Work in this repository follows the **Standard AI Workflow**. Session start, backlog updates, document sync, and session close all take the documents under `ai-workflow/` as the primary reference. Grok Build acts as the main agent and delegates bounded-scope work to the built-in subagents (`explore` / `plan`) or custom agents (`.grok/agents/`) to conserve context.

## Read these first

> `<branch>` is the current git branch name (`main` when this is not a git repository). Splitting per branch keeps concurrent work from overwriting itself.

- `AGENTS.md` (entry point shared with Codex — Korean baseline + worker separation)
- `ai-workflow/memory/active/<branch>/state.json`
- `ai-workflow/memory/active/<branch>/sessions`
- `ai-workflow/memory/active/<branch>/backlog`
- `docs/PROJECT_PROFILE.md`
- `ai-workflow/wiki/index.md` — R4 anchor based; load this first when an AI agent queries

`ai-workflow/` is a meta layer for session restore and workflow state. Do not include it in the default search scope when exploring project code or project documents — reference it only when updating the workflow documents themselves or restoring the current session state.

## Relationship to AGENTS.md

- `AGENTS.md` is the entry point shared with Codex. It defines the main agent's Korean baseline, worker separation, and the order in which to consult `ai-workflow/memory/active/` documents.
- This `GROK.md` is a Grok Build *additive rule* — it only adds subagent usage, MCP registration, memory opt-in, and skill registration. Keep it consistent with `AGENTS.md`.
- Where the two documents disagree, `GROK.md` wins (additive rule inside a Grok Build session). The Korean baseline stays *identical*.

## Entry skill (TUI picker)

- Type `/`, search for `standard-ai-workflow`, and the `.grok/skills/standard-ai-workflow/SKILL.md` emitted by this harness appears.
- Skill body: session start, backlog update, and document sync procedures.

{_STANDARD_RULES}
- Keep the main agent on coordination and integration as much as possible, and delegate bounded-scope work to subagents / custom agents.

## Subagent principles (Grok Build multi-agent topology)

- **Main agent**: talks to the user, decomposes work, invokes and integrates subagents, and owns syncing `state.json` / `session_handoff` / `work_backlog`. It does not take on tool calls itself.
- **Built-in subagent `explore`** (read-only): codebase exploration, file search, grep — bounded-scope reads. Prefer splitting it onto a lighter model such as `--model grok-4.20-multi-agent`.
- **Built-in subagent `plan`** (read-only): work decomposition, impact analysis, implementation planning. The main agent checks with `plan` before making tool calls.
- **Custom agents** (`.grok/agents/`): define these when you need *role-specific personas* such as doc / code / validation workers.

When invoking a subagent, state the intent and responsibility boundary explicitly (`agent_id`, `task_description`, `input_files`, `output_files`, `constraints`, `context_summary`).

## MCP registration (`.grok/config.toml`)

- Copy the `.grok/config.toml.example` emitted by this harness to `.grok/config.toml` and use that.
- Absolute paths must be corrected:
  - `PYTHONPATH = "/ABSOLUTE/PATH/TO/standard_ai_workflow/workflow-source"`
  - `STANDARD_AI_WORKFLOW_ROOT = "/ABSOLUTE/PATH/TO/<project_root>"`
- With `--enable-mcp`, the `[mcp_servers.standardAiWorkflowReadOnly]` block is emitted automatically.
- Select the transport with `--mcp-bridge jsonrpc-bridge|stdio-sdk`. The default is `jsonrpc-bridge` (stable).

### Compatibility auto-import

Grok Build auto-loads these compatibility files (priority: config > claude > cursor > mcp).

| Source | Format | Location |
|---|---|---|
| `config.toml` | Native Grok config | `~/.grok/config.toml`, `.grok/config.toml` |
| `.claude.json` | Claude Code format | `~/.claude.json` |
| `.cursor/mcp.json` | Cursor format | `~/.cursor/mcp.json`, `<project>/.cursor/mcp.json` |
| `.mcp.json` | MCP standard | Project root |

→ An existing workflow MCP registration in Claude / Cursor / standard MCP sources is imported automatically. **But when the same `[mcp_servers]` alias appears in several sources, config.toml wins**, so an unintended override is possible.

## Memory (opt-in)

- `~/.grok/memory/` is opt-in via `--experimental-memory` or `GROK_MEMORY=1`.
- Do not trust the memory directory without that opt-in.
- `[memory]` settings: `enabled`, `[memory.session] save_on_end`, `[memory.search] max_results`, `[memory.initial_injection] min_score`.

## Language and context principles

- Write user-facing work reports, status summaries, and document updates in Korean by default.
- Keep code, commands, file paths, configuration keys, and external product names verbatim.
- Handle internal reasoning and scratch classification however is most efficient, but give the user only the conclusion and the next action.
- Avoid long intermediate reasoning, repeated summaries, and unnecessary self-explanation.
- Keep only the facts the next session needs in the handoff and backlog, so context does not pile up.

## Project run defaults

- Install: `{context['install_command']}`
- Run locally: `{context['run_command']}`
- Quick test: `{context['quick_test_command']}`
- Isolated test: `{context['isolated_test_command']}`
- Smoke check: `{smoke_check}`

## Documentation conventions

- Documentation home: `{context['doc_home']}`
- Operations docs: `{context['operations_dir']}`
- Backlog location: `{context['backlog_dir']}`
- Session handoff: `{context['session_doc_path']}`

## Grok Build notes

- Grok Build auto-reads both `AGENTS.md` and `GROK.md` as root entry points. On policy conflict `GROK.md` wins, but keep the two pointing at the same facts.
- Copy `.grok/config.toml.example` into your environment configuration (`~/.grok/config.toml`, or the project-local `.grok/config.toml`). Absolute paths must be corrected.
- Before a subagent or custom agent performs a dangerous external action (database migration, production deploy, secret rotation), get explicit user approval first.
- {harness_note}
"""


def render_grok_build_skill(args: argparse.Namespace, context: dict[str, object]) -> str:
    """Render ``.grok/skills/standard-ai-workflow/SKILL.md`` (TUI picker 표시)."""
    _STANDARD_CLOSE_ORDER = load_standard_rules().close_order
    return f"""---
name: standard-ai-workflow
description: Standard AI Workflow entry skill — walks through session start, backlog update, and document sync on the Korean baseline. Invoke it as `/standard-ai-workflow` from the Grok Build TUI picker.
---

# Standard AI Workflow Skill (Grok Build)

- **Role**: the workflow entry skill invoked from the Grok Build TUI picker. Covers session start, backlog update, and document sync in one place.
- **Location**: `.grok/skills/standard-ai-workflow/SKILL.md`
- **Invocation**: type `/` in the TUI, search for `standard-ai-workflow`, press Enter
- Audience: Grok Build, repository maintainer
- Last updated: {args.today}

## 1. When to use this skill

- When starting a new session and restoring the workflow baseline (`state.json` + `session_handoff.md` + `work_backlog.md`)
- When registering a new task in today's backlog or updating an existing task's status
- When affected documents need an (advisory) sync after code or document changes

## 2. Preconditions

- Both `AGENTS.md` and `GROK.md` exist at the project root
- `state.json`, `session_handoff.md`, and `work_backlog.md` exist under `ai-workflow/memory/active/`
- `docs/PROJECT_PROFILE.md` is filled in against the real repository

## 3. Procedure

### 3.1 Session start (baseline restore)

```bash
# read the workflow state docs first
cat ai-workflow/memory/active/<branch>/state.json
cat ai-workflow/memory/active/<branch>/session_handoff.md
cat ai-workflow/memory/active/<branch>/work_backlog.md
ls ai-workflow/memory/active/<branch>/backlog/
cat docs/PROJECT_PROFILE.md
cat ai-workflow/wiki/index.md   # R4 anchor based
```

At session start, *always* read those five documents before beginning work. Report to the user, on the Korean baseline: the next-task candidates and the recommended next action.

### 3.2 Backlog update

```bash
# add or update a task in today's backlog file
cat > ai-workflow/memory/active/<branch>/backlog/{args.today}.md <<EOF
# Backlog Index — {args.today}

- Purpose: ...
- Scope: ...
- Audience: ...
- Status: ...
- Last updated: {args.today}

## Tasks

- **TASK-{args.today}-001** [...] ... — ...
  - path: backlog/tasks/TASK-{args.today}-001.md
EOF
```

### 3.3 Document sync (advisory)

Identify affected documents automatically after code/document changes:

```bash
python3 ai-workflow/mcp_servers/check-doc-links/check_doc_links.py
python3 ai-workflow/mcp_servers/check-doc-metadata/check_doc_metadata.py
python3 ai-workflow/mcp_servers/suggest-impacted-docs/suggest_impacted_docs.py
```

(This skill is *advisory* — it never edits automatically. The user reviews the result and applies it.)

## 4. Session close procedure

{_STANDARD_CLOSE_ORDER}

```bash
# 1. update memory — update handoff/backlog with the tools, then regenerate state.json
{find_memory_command(load_standard_rules(), "Regenerate state.json")}

# 2. commit
git add -A
git commit -m "..."

# 3. push
git push
```

{render_memory_update_section()}

## 5. Read next

- Entry point: `GROK.md` (root)
- Shared entry point: `AGENTS.md` (root)
- Standard: `ai-workflow/core/global_workflow_standard.md`
- Apply guide: `workflow-source/harnesses/grok-build/apply_guide.md`
"""


def render_grok_build_config_example(args: argparse.Namespace, context: dict[str, object]) -> str:
    """Render ``.grok/config.toml.example`` — MCP stdio snippet + skill paths + memory opt-in.

    MCP 블록은 `bootstrap_lib.mcp.render_mcp_toml_block` 로 조립한다. 전에는 여기에
    command/args/alias/tool 설명을 **손으로 적어** 두고 있었다 (활성 1 + 주석 처리된
    stdio-sdk 변형 1) — Codex 는 정본을 쓰는데 Grok 만 사본이라, transport 기본값이나
    entry-point 모듈명이 바뀌면 Grok 만 옛 값을 계속 내보냈을 것이다 (2026-08-05).

    env 는 정본의 상대 경로가 아니라 ``/ABSOLUTE/PATH/TO/...`` placeholder 다.
    이 파일은 emit 되는 최종 설정이 아니라 **사용자가 `cp` 후 경로를 고치는 템플릿**
    이고, Grok Build 는 cwd > repo > user 순으로 load 하므로 cwd = 프로젝트 루트
    전제가 성립하지 않는다. 값은 다르되 *무엇을 실행하는가* 는 같아야 한다.
    """
    placeholder_env = {
        "PYTHONPATH": "/ABSOLUTE/PATH/TO/standard_ai_workflow/workflow-source",
        "STANDARD_AI_WORKFLOW_ROOT": "/ABSOLUTE/PATH/TO/<project_root>",
    }
    mcp_block = render_mcp_toml_block("jsonrpc-bridge", placeholder_env)
    mcp_alt_block = render_mcp_toml_block("stdio-sdk", placeholder_env, commented=True)
    return f'''# Grok Build config (v0.15.16+, standard-ai-workflow overlay)
#
# Usage: cp this file to `.grok/config.toml`, then correct the absolute paths.
#
#   cp .grok/config.toml.example .grok/config.toml
#   $EDITOR .grok/config.toml
#
# Grok Build auto-loads .grok/config.toml in the order cwd > repo > user.
# Claude (`.claude.json`) / Cursor (`.cursor/mcp.json`) / `.mcp.json` are also
# imported automatically (priority: config.toml > claude > cursor > mcp).

# ---------------------------------------------------------------------------
# Model (Grok Build default)
# ---------------------------------------------------------------------------
[models]
default = "grok-build"
web_search = "grok-4.20-multi-agent"

# split subagents onto a lighter model (e.g. explore / plan)
# [subagents]
# enabled = true
#
# [subagents.toggle]
# explore = true
# plan = true
#
# [subagents.models]
# explore = "grok-4.20-multi-agent"
# plan = "grok-4.20-multi-agent"

# ---------------------------------------------------------------------------
# Standard AI workflow MCP (read-only)
# ---------------------------------------------------------------------------
{mcp_block}
# stdio-sdk variant (experimental): only comes up on a python3 that has the `mcp` SDK.
# Without the SDK on the system python3 it dies with `Connection closed` —
# see the measured table in core/mcp_installation_by_harness.md §1.1.
{mcp_alt_block}
# ---------------------------------------------------------------------------
# Skills (project-local + user)
# ---------------------------------------------------------------------------
[skills]
paths = [".grok/skills"]
# ignore = []
# disabled = []

# ---------------------------------------------------------------------------
# Memory (opt-in)
# ---------------------------------------------------------------------------
# [memory]
# enabled = false                       # enable memory
#
# [memory.session]
# save_on_end = true                    # write metadata summary on session end
#
# [memory.watcher]
# enabled = true                        # watch memory files for external edits
#
# [memory.search]
# max_results = 6
# min_score = 0.35
#
# [memory.initial_injection]
# enabled = true
# min_score = 0.0

# ---------------------------------------------------------------------------
# Permissions (default: ask; the team standard is always_allow_all_sessions)
# ---------------------------------------------------------------------------
# [permission]
# default_action = "ask"

# ---------------------------------------------------------------------------
# Compatibility auto-import (optional)
# ---------------------------------------------------------------------------
# An existing workflow MCP in Claude / Cursor / standard MCP sources is imported automatically.
# When the same [mcp_servers] alias appears in several sources, config.toml wins.
[compat.claude]
mcps = true

[compat.cursor]
mcps = true

[compat.codex]
sessions = true

# ---------------------------------------------------------------------------
# Notifications (optional)
# ---------------------------------------------------------------------------
# [ui.notifications]
# method = "auto"
# condition = "unfocused"
# events = ["turn_complete", "approval_required"]
'''


def write_grok_build_harness_files(
    args: argparse.Namespace,
    paths: Paths,
    context: dict[str, object],
) -> dict[str, str]:
    """Generate Grok Build harness overlay files (v0.15.16+, 3 file emit).

    Grok Build 의 진입점 emit 전략:
    - ``AGENTS.md`` (root): codex/opencode/pi-dev dispatch block 의 render_codex_agents
      결과로 이미 emit (grok-build 와 동시 선택 시 idempotent). grok-build 만 단독
      선택 시에는 write_harness_files 의 entry dispatch 가 GROK.md 만 emit.
    - ``GROK.md`` (root): render_grok_build_agents 결과. write_harness_files 의
      grok-build branch 에서 emit.
    - ``.grok/skills/standard-ai-workflow/SKILL.md``: TUI picker 표시 skill.
    - ``.grok/config.toml.example``: MCP stdio snippet + skill paths + memory opt-in.

    3 file emit (GROK.md 는 dispatch block 에서):
    - ``.grok/skills/standard-ai-workflow/SKILL.md``
    - ``.grok/config.toml.example``
    """
    generated: dict[str, str] = {}
    grok_skill = paths.target_root / ".grok" / "skills" / "standard-ai-workflow" / "SKILL.md"
    grok_config = paths.target_root / ".grok" / "config.toml.example"

    write_text(grok_skill, render_grok_build_skill(args, context), force=args.force, rel_to=paths.target_root)
    generated["grok_build_skill"] = str(grok_skill)

    write_text(grok_config, render_grok_build_config_example(args, context), force=args.force, rel_to=paths.target_root)
    generated["grok_build_config_example"] = str(grok_config)

    return generated


#: Register each harness's ``write_*_harness_files`` implementation. The
#: :data:`HARNESS_FILE_BUILDERS` registry lives in
#: :mod:`bootstrap_lib.harnesses`; we just populate it from here.
register_harness_builder("codex", write_codex_harness_files)
register_harness_builder("opencode", write_opencode_harness_files)
register_harness_builder("gemini-cli", write_gemini_cli_harness_files)
register_harness_builder("pi-dev", write_pi_dev_harness_files)
register_harness_builder("antigravity", write_antigravity_harness_files)
register_harness_builder("claude-code", write_claude_code_harness_files)
register_harness_builder("aider", write_aider_harness_files)
register_harness_builder("goose", write_goose_harness_files)
register_harness_builder("grok-build", write_grok_build_harness_files)
register_harness_builder("custom", write_custom_harness_files)


def write_minimax_code_harness_files(
    args: argparse.Namespace,
    paths: Paths,
    context: dict[str, object],
) -> dict[str, str]:
    """Generate MiniMax Code harness overlay files.

    The overlay mirrors the OpenCode orchestrator + worker split but pins the
    entry files at ``AGENTS.md`` and ``MiniMax.md`` (the latter is the
    MiniMax Code-specific entry point) and emits a JSON config example so
    the user can drop the snippet into their ``~/.MiniMax/config.json`` or
    a project-local ``.MiniMax/config.json`` without further editing.
    """
    generated: dict[str, str] = {}

    minimax_root = paths.target_root / ".MiniMax"
    minimax_config = paths.target_root / "MiniMax_config.example.json"
    minimax_orchestrator = minimax_root / "agents" / "workflow-orchestrator.md"
    minimax_worker = minimax_root / "agents" / "workflow-worker.md"
    minimax_doc_worker = minimax_root / "agents" / "workflow-doc-worker.md"
    minimax_code_worker = minimax_root / "agents" / "workflow-code-worker.md"
    minimax_validation_worker = minimax_root / "agents" / "workflow-validation-worker.md"

    write_text(minimax_config, render_minimax_config_example(), force=args.force, rel_to=paths.target_root)
    generated["minimax_config_example"] = str(minimax_config)
    write_text(minimax_orchestrator, render_minimax_orchestrator(args, context), force=args.force, rel_to=paths.target_root)
    generated["minimax_orchestrator"] = str(minimax_orchestrator)
    write_text(minimax_worker, render_minimax_worker(args, context), force=args.force, rel_to=paths.target_root)
    generated["minimax_worker"] = str(minimax_worker)
    write_text(minimax_doc_worker, render_minimax_doc_worker(args, context), force=args.force, rel_to=paths.target_root)
    generated["minimax_doc_worker"] = str(minimax_doc_worker)
    write_text(minimax_code_worker, render_minimax_code_worker(args, context), force=args.force, rel_to=paths.target_root)
    generated["minimax_code_worker"] = str(minimax_code_worker)
    write_text(minimax_validation_worker, render_minimax_validation_worker(args, context), force=args.force, rel_to=paths.target_root)
    generated["minimax_validation_worker"] = str(minimax_validation_worker)
    return generated


# ---------------------------------------------------------------------------
# CodeWhale adapter (v0.10.4+)
# ---------------------------------------------------------------------------
def render_codewhale_skill(args: argparse.Namespace, context: dict[str, object]) -> str:
    """Render ``.codewhale/skills/codewhale-workflow/SKILL.md`` (CodeWhale 진입점).

    CodeWhale 의 Constitution 은 이미 검증/병렬화/컨텍스트 관리/계획 수립 규칙을
    내장하므로, 본 skill 은 *additive rule* 만 포함 — Constitution 과 중복되는
    규칙은 의도적으로 제외.
    """
    # Ensure smoke check has a sensible default
    smoke_check = context['smoke_check_command']
    if "TODO" in smoke_check:
        if context['primary_stack'] == 'python':
            smoke_check = "python3 --version"
        elif context['primary_stack'] == 'node':
            smoke_check = "node --version"

    _STANDARD_CLOSE_ORDER = load_standard_rules().close_order
    return f"""# CodeWhale Standard AI Workflow Skill

- Skill name: `codewhale-workflow`
- Purpose: provide the additive rules for running the standard AI workflow inside CodeWhale.
- Scope: session start order, Korean reporting, backlog/handoff management, project-profile-driven exploration
- Audience: CodeWhale agent, repository maintainer
- Status: draft
- Last updated: {args.today}
- Related: `ai-workflow/memory/active/<branch>/state.json`, `ai-workflow/memory/active/<branch>/sessions`, `ai-workflow/memory/active/<branch>/backlog`, `docs/PROJECT_PROFILE.md`

## Important — relationship to the Constitution

CodeWhale's Constitution (Articles I–VIII) already embeds the rules below, so this skill
**does not repeat them**:

- Never declare done without verification → Constitution Article II (Verification)
- Parallel execution / independent-work fan-out → Constitution Article III (Momentum)
- Context management / plan pattern → Constitution Regulations
- Sub-agent delegation strategy → Constitution Regulations (Orchestration)
- Execution discipline (tool usage, scope discipline) → Constitution Statutes

This skill injects only the **workflow-specific value** the Constitution does not provide.

## 1. Session start order

At CodeWhale session start, read the workflow state docs in this order:

1. `ai-workflow/memory/active/<branch>/state.json` — the current baseline
2. `ai-workflow/memory/active/<branch>/sessions` — the previous session's handoff
3. `ai-workflow/memory/active/<branch>/backlog` — the work backlog index
4. `docs/PROJECT_PROFILE.md` — project-specific rules
5. (if present) `ai-workflow/memory/active/PURPOSE.md` — the project's purpose

## 2. Language and reporting

- Write user-facing work reports, status summaries, document drafts, handoff, and backlog updates in **Korean**.
- Keep code, commands, file paths, configuration keys, and external product names verbatim.
- Follow the Constitution Statutes' language rule (match the user's message language), but this section wins for user-facing deliverables.

## 3. Task status values

| Status | Meaning |
| --- | --- |
| `planned` | Ready to start, not yet underway |
| `in_progress` | Being worked on in this session or continuing into the next |
| `blocked` | Cannot proceed — external dependency or pending decision |
| `done` | Meets its completion criteria and has verification evidence |

## 4. Memory layers

- `ai-workflow/memory/active/` — workflow state docs (source of truth for session restore, backlog status, handoff)
- The `docs/...` paths in `PROJECT_PROFILE.md` — where the real project documents live
- `ai-workflow/` is a **meta layer** for session restore and workflow state. Exclude it from ordinary project code/document exploration.

## 5. Session close

{_STANDARD_CLOSE_ORDER}

1. **Update memory**: update `state.json`, `session_handoff.md`, `work_backlog.md`
2. **Final verification**: run `workflow-linter` (document consistency)
3. Write the **next-session starting point** and a **close summary** into the handoff
4. **commit + push**: a single commit that includes the memory update

## 6. Backlog management

- Minimum fields per work item: name, status, priority, requested date, completed date, owner, host name, host IP, affected documents, description, progress, completion criteria, result, next-session starting point, remaining risks, follow-up
- Dated backlog: `ai-workflow/memory/active/<branch>/backlog/YYYY-MM-DD.md`

## 7. Default verification commands

```bash
# smoke check
{smoke_check}
# lint
{context.get('lint_command', 'echo TODO: lint command')}
# type check
{context.get('type_check_command', 'echo TODO: type check command')}
# quick test
{context.get('quick_test_command', 'echo TODO: quick test command')}
```

## 8. CodeWhale-specific operation

- CodeWhale's `agent` tool (explore/plan/review/implementer/verifier) lines up with the worker split in the workflow agent topology.
- The main orchestrator (parent) stays on coordination, integration, and user reporting, and delegates bulk exploration, implementation, and verification to sub-agents.
- Per Constitution Article VII (Domain Context), this workflow acts as CodeWhale's operating context.

{render_memory_update_section()}

## Read next

- `ai-workflow/README.md`
- `harnesses/codewhale/apply_guide.md`
- `workflow-source/core/workflow_harness_distribution.md` (CodeWhale section)
"""


def write_codewhale_harness_files(
    args: argparse.Namespace,
    paths: Paths,
    context: dict[str, object],
) -> dict[str, str]:
    """Generate CodeWhale harness overlay files (v0.10.4+).

    CodeWhale 의 진입점 = ``.codewhale/skills/codewhale-workflow/SKILL.md``
    (project-local skill). Constitution 이 이미 검증/병렬화/컨텍스트 관리 규칙을
    내장하므로, 단일 skill 파일만 emit.
    """
    generated: dict[str, str] = {}

    codewhale_root = paths.target_root / ".codewhale" / "skills" / "codewhale-workflow"
    skill_file = codewhale_root / "SKILL.md"

    write_text(skill_file, render_codewhale_skill(args, context), force=args.force, rel_to=paths.target_root)
    generated["codewhale_skill"] = str(skill_file)

    return generated


register_harness_builder("codewhale", write_codewhale_harness_files)
register_harness_builder("minimax-code", write_minimax_code_harness_files)


def write_mavis_harness_files(
    args: argparse.Namespace,
    paths: Paths,
    context: dict,
) -> dict[str, str]:
    """mavis 데스크탑 런타임 — project-local 산출물 0.

    mavis 는 *글로벌 한 곳* (``~/.minimax/mcp/mcp.json``) 만 읽으므로 본
    builder 는 no-op. ``--enable-mcp`` 와 함께 호출될 때
    :func:`bootstrap_lib.mcp.write_mavis_global_mcp_files` 가 별도 진입으로
    글로벌 merge 를 맡는다 (메인 bootstrap CLI).
    """
    return {}


register_harness_builder("mavis", write_mavis_harness_files)


# ---------------------------------------------------------------------------
# Self-check: HARNESS_SPECS (single source of truth for harness metadata) must
# agree with HARNESS_FILE_BUILDERS (the actual renderer registry). If they
# drift, the CLI --harness choices will not match the renderers, which is the
# same class of bug we hit in v0.5.7.1 (sub-packages missing) and in v0.5.7
# (HARNESS_DEFINITIONS missing pi-dev).
# ---------------------------------------------------------------------------
def _verify_harness_registry_consistency() -> None:
    from workflow_kit.bootstrap_lib.harnesses import HARNESS_FILE_BUILDERS, HARNESS_SPECS, SUPPORTED_HARNESSES

    spec_keys = set(HARNESS_SPECS)
    builder_keys = set(HARNESS_FILE_BUILDERS)
    supported = set(SUPPORTED_HARNESSES)
    missing_builder = sorted(spec_keys - builder_keys)
    missing_spec = sorted(builder_keys - spec_keys)
    missing_supported = sorted(supported - spec_keys)
    if missing_builder or missing_spec or missing_supported:
        problems = []
        if missing_builder:
            problems.append(
                "HARNESS_SPECS has entries without a renderer: " + ", ".join(missing_builder)
            )
        if missing_spec:
            problems.append(
                "HARNESS_FILE_BUILDERS has entries without a spec: " + ", ".join(missing_spec)
            )
        if missing_supported:
            problems.append(
                "SUPPORTED_HARNESSES has entries without a spec: "
                + ", ".join(missing_supported)
            )
        raise RuntimeError(
            "Harness registry drift detected. The single source of truth is "
            "HARNESS_SPECS; fix the following before releasing:\n  - "
            + "\n  - ".join(problems)
        )


_verify_harness_registry_consistency()

