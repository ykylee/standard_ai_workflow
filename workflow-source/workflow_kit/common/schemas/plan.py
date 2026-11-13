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


class PlanResponseVerdict(BaseModel):
    """응답 파일 한 건의 자격 판정 (스펙 §8.1) 과, `plan-import` 가 그것에 한 일."""

    name: str
    location: str = Field(..., description="`inbox` 또는 `archive`")
    eligible: bool
    stage: int | None = Field(None, description="처음 어긋난 자격 단계 (0~6) — 자격이 있으면 null")
    reason: str = ""
    responder: str = ""
    received_at: str = ""
    comments: int = 0
    action: str = Field("none", description="`archived` · `rejected` · `kept_in_inbox` · `none` (dry-run 은 하려던 일)")
    moved_to: str | None = Field(None, description="옮긴(옮길) 경로 — 작업 공간 기준")


class PlanStateChange(BaseModel):
    id: str
    before: str = Field(..., description="상태 칸에 적혀 있던 값")
    after: str = Field(..., description="다시 계산한 값")


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
    inbox: list[PlanResponseVerdict] = Field(default_factory=list, description="받은편지함 파일별 자격")
    unknown_inbox_files: list[str] = Field(default_factory=list, description="받은편지함의 응답 이름 꼴이 아닌 `.md`")
    disputed_responses: list[str] = Field(default_factory=list, description="다툼에 든 유효 응답")
    superseded_responses: list[str] = Field(default_factory=list, description="같은 응답자의 뒤 응답 때문에 세지 않은 응답")
    markdown: str = Field("", description="검증 보고에 붙일 `### 주장별` 절 — 주장이 없으면 빈 문자열")
    source_context: PlanStatusSourceContext


class PlanImportSourceContext(BaseModel):
    task_id: str
    task_path: str
    mode: str = Field(..., description="`import` 또는 `discard`")


class PlanImportOutput(BaseOutput):
    """`plan-import` — 받은편지함의 응답을 보관으로 옮기고 결정 상태를 다시 계산한다."""

    task_id: str
    applied: bool = Field(..., description="`--apply` 로 실제로 썼는가 (dry-run · import_busy 는 false)")
    outcome: str = Field(..., description="`imported` · `discarded` · `nothing_to_do` · `import_busy` · `dry_run`")
    responses: list[PlanResponseVerdict] = Field(default_factory=list)
    state_changes: list[PlanStateChange] = Field(default_factory=list)
    states: dict[str, str] = Field(default_factory=dict, description="결정마다 다시 계산한 상태")
    open_decisions: list[str] = Field(default_factory=list)
    progress_line: str | None = Field(None, description="task `Progress` 에 적은(적을) 한 줄")
    pending_responses: int = Field(0, description="이 호출 뒤 받은편지함에 남는 그 task 의 응답 건수")
    unknown_inbox_files: list[str] = Field(default_factory=list)
    source_context: PlanImportSourceContext
