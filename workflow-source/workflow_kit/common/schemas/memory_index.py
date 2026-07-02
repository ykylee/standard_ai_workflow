"""Pydantic models for ADR-005 Memora-inspired Memory Index (v0.11.22+ Phase 1).

memory_index/ state layer 의 entries/MEM-*.json 스키마 + retrieval 3-tuple output contract.
ADR-005 §2 (schema) + §4 (merge rule) + §5 (retrieval 3-tuple) 의 Pydantic 측 구현.

ADR-005 cross-ref: docs/architecture/ADR-005-memora-inspired-memory-index.md
"""

from __future__ import annotations

import re
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator

from workflow_kit.common.schemas.base import BaseOutput, Status


class MergeState(str, Enum):
    """ADR-005 §4 merge lifecycle.

    - ACTIVE: canonical 단일 entry (default).
    - LINKED: 다중 entry 가 같은 topic 으로 묶임; retrieval 결과에 양쪽 노출.
    - MERGED: Phase 2 opt-in 의 canonical merge 결과 (source_paths 합집합 보존).
    """
    ACTIVE = "active"
    LINKED = "linked"
    MERGED = "merged"


_ID_PATTERN = re.compile(r"^MEM-\d{4}-\d{2}-\d{2}-\d{3}$")


class MemoryEntry(BaseModel):
    """MEM-YYYY-MM-DD-NNN.json entry 스키마.

    ADR-005 §2 의 field 그대로. v0.11.22+ Phase 1 = schema_version=1 only.
    """
    id: str = Field(..., description="MEM-YYYY-MM-DD-NNN")
    schema_version: int = Field(default=1, ge=1, le=99,
                                description="schema breaking change tracker")
    source_paths: list[str] = Field(default_factory=list,
                                    description="본문 원문이 있는 경로")
    primary_abstraction: str = Field(
        ..., min_length=1, max_length=200,
        description="6-8 단어 canonical 요약 (ADR-005 §4 merge 규칙의 기준점)",
    )
    cue_anchors: list[str] = Field(default_factory=list,
                                   description="다중 semantic entry point (lower-case match)")
    value_digest: str = Field(default="", description="본문 1줄 요약 (preview 용)")
    owners: list[str] = Field(default_factory=list, description="책임자/역할")
    scope: list[str] = Field(default_factory=list, description="project / team / org 등")
    merge_state: MergeState = Field(default=MergeState.ACTIVE,
                                    description="merge lifecycle")
    mentioned_in: list[str] = Field(default_factory=list,
                                    description="이 entry 를 참조하는 영구 문서 / wiki / ADR 경로")
    created_at: datetime = Field(..., description="최초 생성 시각")
    updated_at: datetime = Field(..., description="마지막 갱신 시각")

    @field_validator("id")
    @classmethod
    def _validate_id(cls, v: str) -> str:
        """id 패턴 강제 (ADR-005 §2 schema_version=1 기준)."""
        if not _ID_PATTERN.match(v):
            raise ValueError(f"id does not match MEM-YYYY-MM-DD-NNN pattern: {v!r}")
        return v


class MemoryIndexQuery(BaseModel):
    """Retrieval query 입력."""
    query_tokens: list[str] = Field(..., min_length=1,
                                    description="anchor 후보 token list")
    top_k: int = Field(default=10, ge=1, le=100)
    max_depth: int = Field(default=2, ge=0, le=3,
                           description="linked expansion depth cap (worker latency 보호)")


class MemoryIndexQueryResult(BaseModel):
    """Retrieval query 출력."""
    query_tokens: list[str]
    selected_entries: list[MemoryEntry] = Field(default_factory=list)
    expansion_depth_used: int = 0
    cue_hits: int = 0
    expansion_hits: int = 0


class MemoryIndexValidationIssue(BaseModel):
    """Validation issue (1개 = 1 row)."""
    code: str = Field(..., description="duplicate_id / duplicate_primary_abstraction 등")
    detail: str = Field(..., description="human-readable 설명")
    affected_ids: list[str] = Field(default_factory=list)


class MemoryIndexValidationOutput(BaseModel):
    """Validation 결과."""
    total_entries: int = 0
    issues: list[MemoryIndexValidationIssue] = Field(default_factory=list)


class MemoryIndexOutput(BaseOutput):
    """Top-level output (BaseOutput 정합, 다른 stable skill 와 동일 패턴)."""
    status: Status = Status.OK
    entries_loaded: int = 0
    issues: list[MemoryIndexValidationIssue] = Field(default_factory=list)
    source_context: dict[str, Any] = Field(default_factory=dict)


# --- Phase 2: --merge opt-in canonical merge schemas (ADR-005 §4) ---


class MemoryMergeRequest(BaseModel):
    """ADR-005 §4 canonical merge 의 caller 입력.

    `apply=False` (default) 는 dry-run preview. `apply=True` 일 때만 atomic write.
    `target_id` 가 있으면 그 id 로 통합 (caller 가 새 id 회전), None 이면 첫 source id 사용.
    """
    source_ids: list[str] = Field(..., min_length=2,
                                  description="merge 할 source entry id 들 (≥2)")
    target_id: str | None = Field(default=None,
                                  description="통합 entry 의 id; None 이면 첫 source id 사용")
    apply: bool = Field(default=False, description="True 일 때만 atomic write; default dry-run")


class MemoryMergeResult(BaseModel):
    """`apply_memory_merge` 의 결과.

    `applied` field 가 True 면 actual merge 발생 + caller 가 새 file 들을 commit 해야 함.
    dry-run (default) 일 때 `applied=False` + `preview` dict 에 의도된 결과 emit.
    """
    request: MemoryMergeRequest
    applied: bool
    target_id: str
    source_ids: list[str]
    merged_source_paths: list[str]
    merged_cue_anchors: list[str]
    mentioned_in: list[str]
    warnings: list[str] = Field(default_factory=list)
