"""Orchestrator ↔ Sub-agent Contract v1 enforcement modules.

Two enforcement helpers introduced in v0.5.6 (P0 from v0.5.5 pilot findings):
- `output_validator`: validates a sub-agent output payload against §5 of the contract.
- `delegator.choose_role`: decides role mapping per §6.1 + rejects §6.3 actions.

Both modules are pure Python (no external deps beyond the standard library) so
they can be imported from any orchestrator runtime (Mavis, mavis, OpenCode,
Gemini CLI, etc.) and from sub-agent runtimes that already depend on the
standard_ai_workflow kit.

Reference: workflow-source/core/orchestrator_subagent_contract_v1.md
"""

from .output_validator import (
    OutputValidationError,
    OutputValidationResult,
    validate_output,
)
from .delegator import (
    DelegationDecision,
    DelegationRejected,
    choose_role,
)

__all__ = [
    "OutputValidationError",
    "OutputValidationResult",
    "validate_output",
    "DelegationDecision",
    "DelegationRejected",
    "choose_role",
]
