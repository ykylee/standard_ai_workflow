"""Pydantic models for session-start skill."""

from __future__ import annotations

from pydantic import BaseModel, Field
from workflow_kit.common.schemas.base import BaseOutput, Status


class SessionStartSourceDocs(BaseModel):
    session_handoff_path: str
    work_backlog_index_path: str
    project_profile_path: str


class SessionStartPurposeContext(BaseModel):
    """v0.9.5 chapter 9 R-A follow-up part 2: skill context load integration.

    session-start skill 이 PURPOSE.md + state.json.purpose_digest 를 자동 read 한 결과.
    """

    purpose_digest: str | None = None
    purpose_digest_rev: str | None = None
    purpose_path: str | None = None
    body_excerpt: str | None = None
    body_excerpt_truncated: bool = False
    body_excerpt_char_count: int = 0
    scope_included: list[str] = Field(default_factory=list)
    scope_excluded: list[str] = Field(default_factory=list)
    scope_warnings: list[str] = Field(default_factory=list)


class SessionStartOutput(BaseOutput):
    """Output contract for the session-start skill."""
    status: Status = Status.OK
    summary: list[str] = Field(default_factory=list)
    in_progress_items: list[str] = Field(default_factory=list)
    blocked_items: list[str] = Field(default_factory=list)
    latest_backlog_path: str | None = None
    next_documents: list[str] = Field(default_factory=list)
    recommended_next_action: str = ""
    validation_notes: list[str] = Field(default_factory=list)
    environment_constraints: list[str] = Field(default_factory=list)
    source_documents: SessionStartSourceDocs
    purpose_context: SessionStartPurposeContext | None = None
    # v0.10.2: self-bootstrap mode (PURPOSE.md / state.json / handoff / backlog 모두 부재 시)
    self_bootstrap_suggested: bool = False
    self_bootstrap_init_commands: list[str] = Field(default_factory=list)

    @property
    def primary_summary(self) -> str:
        """Backwards-compatible string view of the summary list."""
        if not self.summary:
            return ""
        return self.summary[0]
