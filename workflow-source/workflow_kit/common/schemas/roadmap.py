"""Pydantic models for ADR-027 roadmap · milestone · WBS layer (M-002).

`ai-workflow/memory/active/roadmap/` SSOT(index.md + M-NNN-*.md)의 파싱 결과와,
그로부터 파생되는 기계 정본 `roadmap_state.json` 의 스키마.

정본 계약: workflow-source/core/roadmap_milestone_wbs_spec.md
결정 기록: ai-workflow/wiki/decisions/adr-027-roadmap-wbs-sdlc.md

설계 메모
- 선언(사람이 쓴 것)과 파생(task 상태에서 계산한 것)을 **다른 모델**로 둔다.
  선언 모델에는 파생 값을 싣지 않는다 — 산문이 SSOT 를 복제하면 갈라진다.
- 어휘는 전수 버킷이다: `SdlcPhase` 6개 / `RoadmapItemStatus` 4개
  (task status 어휘 `project_docs.TASK_STATUSES` 와 같은 4개). 어휘 밖 값은
  ValidationError 로 즉시 거부한다 — 모름을 통과로 세지 않는다.
"""

from __future__ import annotations

import re
from enum import Enum
from typing import Final

from pydantic import BaseModel, Field, field_validator


class SdlcPhase(str, Enum):
    """스펙 §4 의 SDLC 단계 어휘 (전수 6개)."""

    CONCEPT = "concept"
    REQUIREMENTS = "requirements"
    DESIGN = "design"
    IMPLEMENTATION = "implementation"
    STABILIZATION = "stabilization"
    RELEASE = "release"


class RoadmapItemStatus(str, Enum):
    """마일스톤 선언 status / WBS·마일스톤 파생 status 공용 어휘.

    task status 어휘(`project_docs.TASK_STATUSES`)와 같은 4개다 — 층이 달라도
    상태 언어가 갈리면 롤업이 번역을 요구하게 된다.
    """

    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    DONE = "done"


MILESTONE_ID_PATTERN: Final[re.Pattern[str]] = re.compile(r"^M-(\d{3})$")
WBS_ID_PATTERN: Final[re.Pattern[str]] = re.compile(r"^WBS-(\d+)(?:\.(\d+))+$")

#: task frontmatter `wbs:` 의 게이트 예외 선언 값 (스펙 §5).
WBS_EXEMPT_VALUE: Final[str] = "exempt"


class WbsNode(BaseModel):
    """WBS 트리 노드 (선언 측).

    status 필드가 **없다** — leaf 상태는 연결 task 에서, 중간 노드는 자식에서
    파생한다 (스펙 §3.2). 선언에 status 를 실으면 두 정본이 생긴다.
    """

    id: str = Field(..., description="WBS-<마일스톤번호>.<n>(.<n>)*")
    title: str = Field(..., min_length=1, max_length=200)
    deliverable_note: str = Field(default="", description="'산출물: …' 꼬리 산문 (있으면)")
    children: list["WbsNode"] = Field(default_factory=list)

    @field_validator("id")
    @classmethod
    def _validate_id(cls, v: str) -> str:
        if not WBS_ID_PATTERN.match(v):
            raise ValueError(f"WBS id 형식 위반 (WBS-N.N[.N]*): {v!r}")
        return v


class Milestone(BaseModel):
    """마일스톤 파일(M-NNN-<slug>.md) frontmatter + WBS 절의 파싱 결과."""

    id: str = Field(..., description="M-NNN")
    title: str = Field(..., min_length=1, max_length=200)
    sdlc_phase: SdlcPhase
    status: RoadmapItemStatus = Field(..., description="선언 status — 파생과 어긋나면 검사가 지목한다")
    order: int = Field(..., ge=1, description="index.md 목록 순서와 일치해야 한다")
    parallel_allowed: list[str] = Field(
        default_factory=list,
        description="SDLC 순서 게이트(§6-2)를 병행 허용할 마일스톤 id — 게이트 우회는 코드가 아니라 이 선언이 결정한다",
    )
    deliverables: list[str] = Field(
        default_factory=list,
        description="workspace 상대 경로 — done 판정은 WBS 완료 + 이 경로 실재 둘 다 필요 (§7.2)",
    )
    wbs: list[WbsNode] = Field(default_factory=list)
    source_path: str = Field(default="", description="파싱 원본 (workspace 상대)")

    @field_validator("id")
    @classmethod
    def _validate_id(cls, v: str) -> str:
        if not MILESTONE_ID_PATTERN.match(v):
            raise ValueError(f"milestone id 형식 위반 (M-NNN): {v!r}")
        return v

    @property
    def number(self) -> int:
        """M-002 → 2. WBS 첫 세그먼트 대조에 쓴다."""
        match = MILESTONE_ID_PATTERN.match(self.id)
        assert match is not None  # field_validator 가 보장
        return int(match.group(1))


class RoadmapIndexEntry(BaseModel):
    """index.md `## Milestones` 목록의 한 줄 — 순서 선언."""

    id: str
    status: RoadmapItemStatus
    path: str = Field(..., description="index.md 기준 상대 경로")
    position: int = Field(..., ge=1, description="목록에서의 1-기반 위치 = SDLC 순서")


class Roadmap(BaseModel):
    """roadmap/ 디렉터리 전체의 파싱 결과 (선언 측)."""

    index_entries: list[RoadmapIndexEntry] = Field(default_factory=list)
    milestones: list[Milestone] = Field(default_factory=list)


class RoadmapIssue(BaseModel):
    """format/integrity 문제 1건. code 는 검사·생성물이 공유하는 어휘다."""

    code: str = Field(..., description="예: index_file_mismatch / wbs_dangling_link / declared_derived_mismatch")
    detail: str
    where: str = Field(default="", description="파일 경로 또는 id")


class TaskWbsLink(BaseModel):
    """task frontmatter `wbs:` 1건의 수집 결과."""

    task_id: str
    task_status: str = Field(..., description="task frontmatter status (roadmap 어휘 밖 값도 보존)")
    wbs_ref: str = Field(..., description="'M-002/WBS-2.1' 또는 'exempt'")
    exempt_reason: str = Field(default="", description="wbs=exempt 일 때의 선언 사유")
    source_path: str = Field(default="")


class WbsNodeState(BaseModel):
    """WBS 노드의 파생 상태 (생성물 측)."""

    id: str
    title: str
    derived_status: RoadmapItemStatus
    linked_task_ids: list[str] = Field(default_factory=list, description="이 leaf 를 가리키는 task (역방향은 생성물이 계산한다)")
    total_leaves: int = Field(default=0, ge=0, description="분모 — 선언한 leaf 수 (연결 task 수가 아니다)")
    done_leaves: int = Field(default=0, ge=0)
    children: list["WbsNodeState"] = Field(default_factory=list)


class MilestoneState(BaseModel):
    """마일스톤의 선언 + 파생 종합 (생성물 측)."""

    id: str
    title: str
    sdlc_phase: SdlcPhase
    declared_status: RoadmapItemStatus
    derived_status: RoadmapItemStatus
    progress: float = Field(..., ge=0.0, le=1.0, description="done leaf / 선언 leaf (분모는 선언 — 50차 규칙)")
    total_leaves: int = Field(default=0, ge=0)
    done_leaves: int = Field(default=0, ge=0)
    deliverables_missing: list[str] = Field(default_factory=list)
    wbs: list[WbsNodeState] = Field(default_factory=list)


class WbsGateVerdict(BaseModel):
    """task 생성 게이트(스펙 §6)의 판정 1건 — CLI 와 MCP 가 같은 판정을 받는다.

    code 어휘 (allowed): `not_applicable`(roadmap 부재) / `draft_roadmap`(소유자
    미확정 초안 — 게이트 발동 전) / `linked` / `exempt_declared`
    code 어휘 (denied): `wbs_required` / `exempt_reason_required` / `wbs_ref_format`
    / `wbs_dangling` / `wbs_not_leaf` / `milestone_done` / `sdlc_order`
    """

    allowed: bool
    code: str
    detail: str = ""
    milestone_id: str = Field(default="", description="판정 대상 마일스톤 (있으면)")


class SessionStartRoadmapContext(BaseModel):
    """session-start 가 보고하는 로드맵 요약 (M-003 배선, additive).

    roadmap 부재 시 present=False 뿐인 객체가 실린다 — 조용한 생략 대신
    '관측했고 없었다' 를 말한다.
    """

    present: bool = False
    current_milestone_id: str | None = None
    current_sdlc_phase: str = Field(default="", description="SdlcPhase value; 현재 마일스톤 부재 시 빈 문자열")
    declared_status: str = ""
    progress: float = Field(default=0.0, ge=0.0, le=1.0)
    done_leaves: int = 0
    total_leaves: int = 0
    next_wbs_candidates: list[str] = Field(
        default_factory=list,
        description="현재 마일스톤에서 아직 done 이 아닌 leaf — 'WBS-id title (derived_status)'")
    deliverables_missing: list[str] = Field(default_factory=list)
    issues_count: int = 0
    recommendation: str = Field(default="", description="SDLC 단계 산출물 권고 등 advisory 한 줄")


class RoadmapState(BaseModel):
    """roadmap_state.json 정본 스키마 — 생성물이며 손편집 금지 (스펙 §7.1)."""

    schema_version: int = Field(default=1, ge=1)
    generated_by: str = Field(
        default="workflow_kit.common.state.roadmap.generate_roadmap_state",
        description="생성물 표식 — check_roadmap_state_generated 가 손편집을 대조한다",
    )
    generated_at: str = Field(default="", description="YYYY-MM-DD. 재생성 대조에서는 제외한다 (매일 바뀌는 값은 비교에서 뺀다)")
    milestones: list[MilestoneState] = Field(default_factory=list)
    current_milestone_id: str | None = Field(default=None, description="order 순 첫 in_progress (선언 기준)")
    exempt_tasks: list[TaskWbsLink] = Field(default_factory=list, description="wbs=exempt 선언 task — 게이트 우회는 침묵이 아니라 선언이고, 여기서 세어진다")
    issues: list[RoadmapIssue] = Field(default_factory=list, description="format + integrity 불일치 전체 (report-only)")
