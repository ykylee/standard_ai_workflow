"""Strict Pydantic models for the claim-plan commands (ADR-031, `core/claim_plan_spec.md`)."""

from __future__ import annotations

from pydantic import BaseModel, Field

from workflow_kit.common.schemas.base import BaseOutput


class PlanClaimBundle(BaseModel):
    """1단계 주장 하나와 그것(또는 후손)을 인용한 완료 기준."""

    id: str
    text: str
    criteria: list[int] = Field(default_factory=list, description="인용한 완료 기준의 번호 (1부터)")
    unmeasured: bool = Field(..., description="인용한 기준이 하나도 없다 — 재지 않는 주장")


class PlanDecisionStatus(BaseModel):
    id: str
    claim_id: str
    question: str
    default: str
    options: list[str] = Field(default_factory=list)
    state: str = Field(..., description="계산한 상태 (스펙 §8) — 판정의 정본")
    column_state: str = Field(..., description="task 파일의 상태 칸에 적힌 값")
    open: bool


class PlanStatusSourceContext(BaseModel):
    task_id: str
    task_path: str


class PlanStatusOutput(BaseOutput):
    """`plan-status` — 주장별 묶음과 결정 상태. 읽기 전용이다."""

    task_id: str
    task_status: str | None = None
    has_plan: bool
    plan_digest: str | None = None
    claims: list[PlanClaimBundle] = Field(default_factory=list)
    decisions: list[PlanDecisionStatus] = Field(default_factory=list)
    open_decisions: list[str] = Field(default_factory=list)
    lint: list[str] = Field(default_factory=list)
    pending_responses: int = Field(0, description="받은편지함의 미반영 응답 건수")
    markdown: str = Field("", description="검증 보고에 붙일 `### 주장별` 절 — 주장이 없으면 빈 문자열")
    source_context: PlanStatusSourceContext
