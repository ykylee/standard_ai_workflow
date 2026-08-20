"""Pydantic models for workflow-linter skill."""

from __future__ import annotations

from pydantic import BaseModel, Field
from workflow_kit.common.schemas.base import BaseOutput, Status


class LinterIssue(BaseModel):
    type: str = Field(..., description="Category of the issue (e.g., 'sync_error', 'broken_link')")
    code: str = Field(..., description="Specific error code")
    description: str = Field(..., description="Detailed description of the issue")
    severity: str = Field(..., description="Severity level: 'low', 'medium', 'high'")
    fix_suggestion: str | None = Field(None, description="Recommended action to resolve the issue")


class LinterSummary(BaseModel):
    total_issues: int
    sync_errors: int
    broken_links: int
    bloat_warnings: int
    #: v1.0.2 — 부재/파손으로 **읽지 못한** 상태 문서 수. 이 값이 0 이 아니면 나머지
    #: 정합 수치는 그만큼 덜 본 결과다 (빈 값끼리 비교해 통과한 몫이 섞여 있다).
    missing_documents: int = 0
    #: v1.2.2 — in_progress 3자 대조가 **무엇을 정본으로 봤는가** (`kind` / `path`).
    #: v0.14.0+ append-only 는 `backlog/tasks/`, 그 이전 레이아웃은 일자 backlog 다.
    #: 출처가 결과에 안 남으면 통과도 실패도 근거가 못 된다 — 실제로 이 값이
    #: 일자 index 로 고정돼 있던 것이 날짜 롤오버마다 헛 mismatch 를 냈다
    #: (TASK-2026-08-20-main-002).
    in_progress_source: dict[str, str] = Field(default_factory=dict)


class WorkflowLinterOutput(BaseOutput):
    """Output contract for the workflow-linter skill."""
    status: Status = Status.OK
    issues: list[LinterIssue] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    summary: LinterSummary
    source_context: dict[str, str] = Field(default_factory=dict)

    @property
    def linter_status(self) -> str:
        """Legacy ``linter_status`` key for downstream tests."""
        return "issues_found" if self.issues else "ok"
