"""Pydantic models for backlog-related skills."""

from __future__ import annotations

from typing import Any
from pydantic import Field
from workflow_kit.common.schemas.base import BaseOutput, Status


class StatusRecommendation(BaseOutput): # Wait, it is a nested object
    pass

from pydantic import BaseModel

class StatusRecommendation(BaseModel):
    value: str = Field(..., description="Recommended status value")
    reason: str = Field(..., description="Reason for the recommendation")


class BacklogUpdateSourceContext(BaseModel):
    daily_backlog_exists: bool
    existing_task_count: int
    project_profile_path: str


class BacklogUpdateOutput(BaseOutput):
    """Output contract for the backlog-update skill."""
    status: Status = Status.OK
    task_id: str = Field(..., description="ID of the task that was updated")
    target_backlog_path: str = Field(..., description="Path to the updated backlog file")
    draft_entry: list[str] = Field(..., description="Generated markdown lines for the backlog entry")
    fields_requiring_confirmation: list[str] = Field(default_factory=list)
    handoff_update_note: str | None = None
    index_update_note: str | None = None
    validation_note: str | None = None
    status_recommendation: StatusRecommendation | None = None
    source_context: BacklogUpdateSourceContext
