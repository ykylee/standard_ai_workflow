"""Helper for Antigravity-specific Multi-Agent delegation."""

from __future__ import annotations

from pathlib import Path
from typing import Any


class AntigravityMultiAgentHelper:
    """Helper to delegate tasks to specialized sub-agents in Antigravity."""

    ROLE_TOOL_MAPPING = {
        "doc-worker": [
            "latest_backlog", 
            "check_doc_metadata", 
            "check_doc_links", 
            "check_quickstart_stale_links",
            "summarize_git_history"
        ],
        "code-worker": [
            "smart_context_reader",
            "apply_robust_patch",
            "grep_search",
            "replace_file_content",
            "run_command"
        ],
        "validation-worker": [
            "run_command",
            "browser_subagent",
            "check_output_samples",
            "generate_image"
        ]
    }

    def __init__(self, prompt_dir: Path):
        self.prompt_dir = prompt_dir

    def get_role_prompt(self, role: str) -> str:
        """Read the system prompt for a given role."""
        prompt_path = self.prompt_dir / f"{role.replace('-', '_')}.md"
        if not prompt_path.exists():
            raise FileNotFoundError(f"Prompt for role '{role}' not found at {prompt_path}")
        return prompt_path.read_text(encoding="utf-8")

    def build_subagent_task(self, role: str, task_description: str) -> str:
        """Combine role prompt and task description for a subagent call."""
        role_prompt = self.get_role_prompt(role)
        allowed_tools = self.ROLE_TOOL_MAPPING.get(role, [])
        tool_guideline = f"\n\n## AUTHORIZED TOOLS\nYou are authorized to use the following tools: {', '.join(allowed_tools)}" if allowed_tools else ""
        
        return f"{role_prompt}{tool_guideline}\n\n## YOUR SPECIFIC TASK\n{task_description}"


def delegate_to_worker(role: str, task: str) -> dict[str, str]:
    """
    Format a request for a sub-agent.
    Note: This is intended to be used as a guideline for the Orchestrator 
    when calling the 'browser_subagent' or similar tools in Antigravity.
    """
    # prompt 는 **패키지 안**에 있다 (`workflow_kit/assets/prompts/`).
    # 원래 위치 `workflow-source/templates/prompts/` 는 wheel 미포함이라 소비자
    # 설치본에서는 `FileNotFoundError` 였다 (2026-08-18, TASK-2026-08-18-main-003).
    prompt_dir = Path(__file__).resolve().parents[1] / "assets" / "prompts"
    helper = AntigravityMultiAgentHelper(prompt_dir)
    
    return {
        "TaskName": f"{role.capitalize()} Assignment",
        "Task": helper.build_subagent_task(role, task),
        "TaskSummary": f"Delegating {role} task: {task[:50]}..."
    }
