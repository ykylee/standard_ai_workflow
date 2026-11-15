"""Pydantic models for read-only exploration skills."""

from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field
from workflow_kit.common.schemas.base import BaseOutput, Status


class LatestBacklogOutput(BaseOutput):
    status: Status = Status.OK
    latest_backlog_path: str | None = None
    candidates: list[str] = Field(default_factory=list)


class MissingMetadata(BaseModel):
    path: str
    missing_fields: list[str]


class CheckDocMetadataOutput(BaseOutput):
    status: Status = Status.OK
    checked_files: list[str] = Field(default_factory=list)
    missing_metadata: list[MissingMetadata] = Field(default_factory=list)


class BrokenLinks(BaseModel):
    path: str
    broken_links: list[str]


class CheckDocLinksOutput(BaseOutput):
    status: Status = Status.OK
    checked_files: list[str] = Field(default_factory=list)
    broken_links: list[BrokenLinks] = Field(default_factory=list)


class ImpactedDoc(BaseModel):
    path: str
    reasoning: str | None = None


class SuggestImpactedDocsOutput(BaseOutput):
    status: Status = Status.OK
    impacted_documents: list[str] = Field(default_factory=list)
    reasoning_notes: list[str] = Field(default_factory=list)


class StaleLinkWarning(BaseModel):
    path: str
    missing_targets: list[str]


class CheckQuickstartStaleLinksOutput(BaseOutput):
    status: Status = Status.OK
    checked_files: list[str] = Field(default_factory=list)
    broken_links: list[BrokenLinks] = Field(default_factory=list)
    missing_expected_links: list[StaleLinkWarning] = Field(default_factory=list)
    stale_link_warnings: list[str] = Field(default_factory=list)
    reasoning_notes: list[str] = Field(default_factory=list)


class CreateSessionHandoffDraftOutput(BaseOutput):
    status: Status = Status.OK
    draft_handoff: list[str] = Field(default_factory=list)
    source_context: dict[str, Any]


class CreateEnvironmentRecordStubOutput(BaseOutput):
    status: Status = Status.OK
    draft_record: list[str] = Field(default_factory=list)
    source_context: dict[str, Any]


class SmartContextReaderOutput(BaseOutput):
    status: Status = Status.OK
    extracted_content: list[str] = Field(default_factory=list)
    not_found_symbols: list[str] = Field(default_factory=list)


class GitHistoryEntry(BaseModel):
    subject: str
    hash: str
    author: str
    date: str
    category: str


class SummarizeGitHistoryOutput(BaseOutput):
    """MCP `summarize_git_history` — `read_only_bundle.summarize_git_history_payload` 의 출력."""

    status: Status = Status.OK
    commit_count: int = Field(..., ge=0)
    range: str
    markdown: str
    entries: list[GitHistoryEntry] = Field(default_factory=list)


class RotateWorkflowLogsOutput(BaseOutput):
    """MCP `rotate_workflow_logs` — handoff 최근 완료 목록을 상한까지 줄인 결과."""

    status: Status = Status.OK
    rotated: bool
    rotated_count: int = Field(..., ge=0)
    remaining_count: int = Field(..., ge=0)
    rotated_items: list[str] = Field(default_factory=list)
    written_paths: list[str] = Field(default_factory=list)


class MilestoneBrief(BaseModel):
    id: str
    sdlc_phase: str
    declared_status: str
    derived_status: str
    progress: float


class AssessMilestoneProgressOutput(BaseOutput):
    """MCP `assess_milestone_progress` — roadmap 층(ADR-027)의 현재 마일스톤 진척.

    roadmap 이 없으면 `roadmap_present=False` 이고 `sdlc_phase` · `milestones` · `issues_count` 를 싣지 않는다.
    """

    status: Status = Status.OK
    roadmap_present: bool
    milestone_id: str | None
    milestone_name: str | None
    sdlc_phase: str | None = None
    progress_percentage: float
    done_count: int = Field(..., ge=0)
    total_count: int = Field(..., ge=0)
    milestones: list[MilestoneBrief] = Field(default_factory=list)
    issues_count: int | None = None
    suggestion: str
