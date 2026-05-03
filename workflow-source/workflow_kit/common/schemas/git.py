"""Pydantic models for git-conflict-resolver skill."""

from __future__ import annotations

from typing import List
from pydantic import BaseModel, Field
from workflow_kit.common.schemas.base import BaseOutput, Status


class UnresolvedConflict(BaseModel):
    lines: str
    reason: str


class GitConflictResolverOutput(BaseOutput):
    """Output contract for the git-conflict-resolver skill."""
    status: Status = Status.OK
    conflict_count: int = Field(..., description="Total number of conflicts found")
    resolved_count: int = Field(..., description="Number of conflicts successfully resolved")
    resolution_summary: str = Field(..., description="Human-readable summary of resolutions")
    unresolved_conflicts: List[UnresolvedConflict] = Field(default_factory=list)
