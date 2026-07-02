"""ADR-005 Memora-inspired Memory Index (v0.11.22+ Phase 1) helper.

memory_index/ state layer 의 entries + anchors + retrieval 3-tuple 을 다룬다.
본 모듈은 *읽기 + validation + query* 의 표준 진입점.
Phase 1.5 (후속 release) = state.json `memory_entries[]` optional pass-through.
Phase 2 (후속 release) = canonical `--merge` opt-in + BM25/embedding fallback.

ADR-005 cross-ref: docs/architecture/ADR-005-memora-inspired-memory-index.md
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Final

from workflow_kit.common.atomic_write import atomic_write_json
from workflow_kit.common.schemas.base import Status
from workflow_kit.common.schemas.memory_index import (
    MemoryEntry,
    MemoryIndexOutput,
    MemoryIndexQuery,
    MemoryIndexQueryResult,
    MemoryIndexValidationIssue,
    MemoryIndexValidationOutput,
)


# --- Constants ---

ID_PATTERN: Final[re.Pattern[str]] = re.compile(r"^MEM-\d{4}-\d{2}-\d{2}-\d{3}$")
MEMORY_INDEX_SUBDIR: Final[str] = "memory_index"
ENTRIES_SUBDIR: Final[str] = "entries"


# --- Path helpers ---


def memory_index_root(workspace_root: Path) -> Path:
    """`ai-workflow/memory/active/memory_index/` 위치를 반환한다.

    ADR-005 §1 의 state layer sub-area layout.
    """
    return workspace_root / "ai-workflow" / "memory" / "active" / MEMORY_INDEX_SUBDIR


def entries_dir(memory_index: Path | None = None, *, workspace_root: Path | None = None) -> Path:
    """`memory_index/entries/` 경로. memory_index 또는 workspace_root 중 하나로 resolve."""
    if memory_index is None:
        if workspace_root is None:
            raise ValueError("either memory_index or workspace_root required")
        memory_index = memory_index_root(workspace_root)
    return memory_index / ENTRIES_SUBDIR


def make_id(memory_index: Path, today: str | None = None) -> str:
    """같은 날짜에서 단조 증가하는 NNN (001~) 의 새 id 발급.

    부재 시 001. caller 는 동일 process 에서 race 가능성 인지.
    """
    target = today or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    pattern = re.compile(rf"^MEM-{re.escape(target)}-(\d{{3}})\.json$")
    used: list[int] = []
    ed = entries_dir(memory_index=memory_index)
    if ed.exists():
        for p in ed.glob(f"MEM-{target}-*.json"):
            m = pattern.match(p.name)
            if m:
                used.append(int(m.group(1)))
    next_seq = max(used, default=0) + 1
    return f"MEM-{target}-{next_seq:03d}"


# --- Entry I/O ---


def load_memory_index(workspace_root: Path) -> list[MemoryEntry]:
    """`memory_index/entries/*.json` 을 모두 읽어 `MemoryEntry` list 로 반환.

    알파벳 순 정렬. JSON decode 또는 schema validate 실패 시 silent skip
    (caller 가 `validate_memory_index` 로 진단).
    """
    root = memory_index_root(workspace_root)
    ed = entries_dir(memory_index=root)
    if not ed.exists():
        return []
    out: list[MemoryEntry] = []
    for json_path in sorted(ed.glob("*.json")):
        try:
            data = json.loads(json_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        try:
            out.append(MemoryEntry.model_validate(data))
        except Exception:
            continue
    return out


def save_memory_entry(
    workspace_root: Path,
    entry: MemoryEntry,
    *,
    target_id: str | None = None,
) -> Path:
    """단일 entry 를 `memory_index/entries/<id>.json` 에 atomic write.

    `target_id` 가 있으면 그 id 로 강제 (id 회전 / 옮김 시).
    `updated_at` 이 비어 있으면 현재 시각으로 stamp.
    """
    write_id = target_id or entry.id
    if not ID_PATTERN.match(write_id):
        raise ValueError(f"id does not match MEM-YYYY-MM-DD-NNN pattern: {write_id!r}")

    root = memory_index_root(workspace_root)
    ed = entries_dir(memory_index=root)
    ed.mkdir(parents=True, exist_ok=True)
    target = ed / f"{write_id}.json"

    payload = entry.model_dump(mode="json")
    if not payload.get("updated_at"):
        payload["updated_at"] = datetime.now(timezone.utc).isoformat()
    atomic_write_json(target, payload)
    return target


# --- Validation (ADR-005 §4 merge 규칙 의 default advisory 구현) ---


def validate_no_duplicate_primary(entries: list[MemoryEntry]) -> list[MemoryIndexValidationIssue]:
    """duplicate primary_abstraction (case-insensitive) + duplicate id 만 hard issue.

    ADR-005 §4 의 "primary_abstraction 동일 + source_paths 동일 = 차단" 의
    *canonical 부분* (source_paths 비교는 Phase 2). 동일 id 도 filesystem 충돌의 근본 원인.
    """
    issues: list[MemoryIndexValidationIssue] = []

    # 1) id 중복 (filesystem level conflict)
    id_groups: dict[str, list[str]] = {}
    for e in entries:
        id_groups.setdefault(e.id, []).append(e.id)
    dup_ids = sorted(k for k, v in id_groups.items() if len(v) > 1)
    if dup_ids:
        issues.append(MemoryIndexValidationIssue(
            code="duplicate_id",
            detail=f"동일 id 의 entry 가 다수 존재합니다: {dup_ids}",
            affected_ids=dup_ids,
        ))

    # 2) primary_abstraction 중복 (case-insensitive)
    primary_groups: dict[str, list[str]] = {}
    for e in entries:
        key = e.primary_abstraction.strip().lower()
        if not key:
            continue
        primary_groups.setdefault(key, []).append(e.id)
    dup_primary_keys = sorted(k for k, v in primary_groups.items() if len(v) > 1)
    if dup_primary_keys:
        affected: list[str] = sorted({eid for k in dup_primary_keys for eid in primary_groups[k]})
        issues.append(MemoryIndexValidationIssue(
            code="duplicate_primary_abstraction",
            detail=(
                "동일 primary_abstraction (case-insensitive) 의 entry 가 다수: "
                f"{dup_primary_keys}"
            ),
            affected_ids=affected,
        ))

    return issues


def validate_memory_index(workspace_root: Path) -> MemoryIndexValidationOutput:
    """`memory_index/` 의 전체 validation 결과."""
    entries = load_memory_index(workspace_root)
    issues = validate_no_duplicate_primary(entries)
    return MemoryIndexValidationOutput(total_entries=len(entries), issues=issues)


# --- Cue anchor inverse index (ADR-005 §3) ---


def build_cue_anchor_index(entries: list[MemoryEntry]) -> dict[str, list[str]]:
    """cue_anchors inverse index. key = anchor (lower-cased), value = [entry_id].

    ADR-005 §3 anchor index 의 in-memory version.
    JSON file 화 (`anchors/by_*.json`) 는 Phase 1.5 helper (현재 in-memory 만).
    """
    inv: dict[str, list[str]] = {}
    for e in entries:
        for anchor in e.cue_anchors:
            key = anchor.strip().lower()
            if not key:
                continue
            inv.setdefault(key, []).append(e.id)
    return inv


# --- Retrieval 3-tuple (ADR-005 §5) ---


def _anchor_exact_match(
    query_tokens: list[str],
    anchor_index: dict[str, list[str]],
) -> set[str]:
    """1단계: cue_anchors ↔ query_tokens 의 exact match (case-insensitive)."""
    seeds: set[str] = set()
    for token in query_tokens:
        norm = token.strip().lower()
        if not norm:
            continue
        if norm in anchor_index:
            seeds.update(anchor_index[norm])
    return seeds


def _linked_expansion(
    seed_ids: set[str],
    entries_by_id: dict[str, MemoryEntry],
    max_depth: int,
) -> tuple[set[str], int]:
    """3단계: `mentioned_in` + `source_paths` 따라 1-hop expansion, `max_depth` cap.

    `path` 의 마지막 stem (`MEM-YYYY-MM-DD-NNN` or `MEM-YYYY-MM-DD-NNN.json`) 만
    ID 로 lookup 한다. 동일 entry 내 self-reference 는 cycle guard 가 visited set 으로 차단.
    """
    if max_depth <= 0 or not seed_ids:
        return set(seed_ids), 0
    visited: set[str] = set(seed_ids)
    frontier: set[str] = set(seed_ids)
    used_depth = 0
    for _ in range(max_depth):
        if not frontier:
            break
        used_depth += 1
        next_frontier: set[str] = set()
        for eid in frontier:
            entry = entries_by_id.get(eid)
            if entry is None:
                continue
            for path in entry.mentioned_in + entry.source_paths:
                stem = Path(path).name
                if stem.endswith(".json"):
                    stem = stem[: -len(".json")]
                if stem in entries_by_id and stem not in visited:
                    next_frontier.add(stem)
        visited.update(next_frontier)
        frontier = next_frontier
    return visited, used_depth


def query_memory_index(
    workspace_root: Path,
    query: MemoryIndexQuery,
) -> MemoryIndexQueryResult:
    """3-tuple retrieval: 1 anchor exact → 2 (Phase 2 BM25) → 3 linked expansion.

    Phase 1: 1 + 3 만. `max_depth=0` 이면 anchor exact only early termination.
    Phase 2+: 2단계 (BM25 or embedding fallback) 추가 helper.
    """
    entries = load_memory_index(workspace_root)
    entries_by_id = {e.id: e for e in entries}
    anchor_index = build_cue_anchor_index(entries)

    seeds = _anchor_exact_match(query.query_tokens, anchor_index)

    if query.max_depth <= 0:
        selected = [entries_by_id[i] for i in sorted(seeds) if i in entries_by_id][: query.top_k]
        return MemoryIndexQueryResult(
            query_tokens=list(query.query_tokens),
            selected_entries=selected,
            expansion_depth_used=0,
            cue_hits=len(seeds),
            expansion_hits=0,
        )

    expanded_ids, used_depth = _linked_expansion(seeds, entries_by_id, query.max_depth)
    expansion_only = expanded_ids - seeds
    selected_ids = sorted(seeds | expansion_only)[: query.top_k]
    selected = [entries_by_id[i] for i in selected_ids if i in entries_by_id]
    return MemoryIndexQueryResult(
        query_tokens=list(query.query_tokens),
        selected_entries=selected,
        expansion_depth_used=used_depth,
        cue_hits=len(seeds),
        expansion_hits=len(expansion_only),
    )


# --- Top-level wrapper ---


def memory_index_status(workspace_root: Path) -> MemoryIndexOutput:
    """Top-level 진입점. CLI / caller 가 사용."""
    validation = validate_memory_index(workspace_root)
    return MemoryIndexOutput(
        status=Status.WARNING if validation.issues else Status.OK,
        entries_loaded=validation.total_entries,
        issues=validation.issues,
        source_context={"workspace_root": str(workspace_root)},
    )
