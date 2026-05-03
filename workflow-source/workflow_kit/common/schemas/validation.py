"""Pydantic models for validation-related skills."""

from __future__ import annotations

from pydantic import BaseModel, Field
from workflow_kit.common.schemas.base import BaseOutput, Status


class ValidationPlanSourceContext(BaseModel):
    has_handoff: bool


class ValidationPlanOutput(BaseOutput):
    """Output contract for the validation-plan skill."""
    status: Status = Status.OK
    validation_plan_path: str = Field(..., description="Path to the generated validation plan")
    project_profile_path: str = Field(..., description="Path to the project profile used")
    change_summary: str | None = None
    changed_files: list[str] = Field(default_factory=list)
    session_handoff_path: str | None = None
    handoff_update_note: str | None = None
    source_context: ValidationPlanSourceContext
