"""ADR-005 Memora-inspired Memory Index (v0.11.22+ Phase 1) helper.

memory_index/ state layer 의 entries + anchors + retrieval 3-tuple 을 다룬다.
본 모듈은 *읽기 + validation + query* 의 표준 진입점.
Phase 1.5 (후속 release) = state.json `memory_entries[]` optional pass-through.
Phase 2 (후속 release) = canonical `--merge` opt-in + BM25/embedding fallback.

ADR-005 cross-ref: docs/architecture/ADR-005-memora-inspired-memory-index.md
"""

from __future__ import annotations

import json
import math
import re
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Final, TypedDict

from workflow_kit.common.atomic_write import atomic_write_json, atomic_write_text
from workflow_kit.common.schemas.base import Status
from workflow_kit.common.paths import memory_active_dir
from workflow_kit.common.schemas.memory_index import (
    MemoryEntry,
    MemoryIndexOutput,
    MemoryIndexQuery,
    MemoryIndexQueryOutput,
    MemoryIndexQueryResult,
    MemoryIndexTelemetryEvent,
    MemoryIndexTelemetrySummary,
    MemoryIndexValidationIssue,
    MemoryIndexValidationOutput,
    MemoryMergeRequest,
    MemoryMergeResult,
    MergeState,
)
# tool_version SSOT (memory.md §v0.8.0 hotfix 정공법):
# 사이트-packages editable install 의 workflow_kit.__version__ 우선, 부재 시 literal fallback.
try:
    from workflow_kit import __version__ as _WORKFLOW_KIT_VERSION
except ImportError:  # pragma: no cover - editable install fallback
    _WORKFLOW_KIT_VERSION = "v0.11.22-beta"


# --- Constants ---

ID_PATTERN: Final[re.Pattern[str]] = re.compile(r"^MEM-\d{4}-\d{2}-\d{2}-\d{3}$")
MEMORY_INDEX_SUBDIR: Final[str] = "memory_index"
ENTRIES_SUBDIR: Final[str] = "entries"
TELEMETRY_SUBDIR: Final[str] = "telemetry"
TELEMETRY_FILE: Final[str] = "events.jsonl"


# --- Path helpers ---


def memory_index_root(workspace_root: Path) -> Path:
    """`ai-workflow/memory/active/memory_index/` 위치를 반환한다.

    ADR-005 §1 의 state layer sub-area layout.
    """
    return memory_active_dir(workspace_root) / MEMORY_INDEX_SUBDIR


def entries_dir(memory_index: Path | None = None, *, workspace_root: Path | None = None) -> Path:
    """`memory_index/entries/` 경로. memory_index 또는 workspace_root 중 하나로 resolve."""
    if memory_index is None:
        if workspace_root is None:
            raise ValueError("either memory_index or workspace_root required")
        memory_index = memory_index_root(workspace_root)
    return memory_index / ENTRIES_SUBDIR


def telemetry_dir(workspace_root: Path) -> Path:
    """`memory_index/telemetry/` 경로 (sibling of entries/).

    Phase 13 AC2 telemetry sidecar 위치. `events.jsonl` 1 file 로 모든 retrieval call 기록.
    """
    return memory_index_root(workspace_root) / TELEMETRY_SUBDIR


def telemetry_path(workspace_root: Path) -> Path:
    """`memory_index/telemetry/events.jsonl` 절대 경로."""
    return telemetry_dir(workspace_root) / TELEMETRY_FILE


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
    return load_memory_index_at(memory_index_root(workspace_root))


def load_memory_index_at(memory_index_dir: Path) -> list[MemoryEntry]:
    """`memory_index/entries/` 의 절대 경로를 직접 받아 load.

    `load_memory_index(workspace_root)` 가 default layout 사용, 본 함수는 override 가능.
    state.json 생성자가 caller 지정 dir 로 load 시 사용 (Phase 1.5).
    """
    ed = entries_dir(memory_index=memory_index_dir)
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


# --- Phase 2b: BM25 2단계 fallback (stdlib only, no external dep) ---

_TOKEN_RE = re.compile(r"[A-Za-z0-9가-힣]+")


def _bm25_text_for_entry(entry: MemoryEntry) -> str:
    """BM25 corpus 의 document text — `primary_abstraction + cue_anchors + value_digest`."""
    parts: list[str] = [entry.primary_abstraction]
    parts.extend(entry.cue_anchors)
    if entry.value_digest:
        parts.append(entry.value_digest)
    return " ".join(parts)


def _bm25_tokenize(text: str) -> list[str]:
    """영숫자 + 한글 토큰 분리, lower-case."""
    return [t.lower() for t in _TOKEN_RE.findall(text) if t]


class _BM25Index(TypedDict):
    entries: list[MemoryEntry]
    doc_tf: list[Counter[str]]
    doc_len: list[int]
    df: dict[str, int]
    avgdl: float
    N: int


def _bm25_build_index(entries: list[MemoryEntry]) -> _BM25Index:
    """BM25 inverted index 계산."""
    corpus = [_bm25_text_for_entry(e) for e in entries]
    N = len(corpus)
    df: dict[str, int] = {}
    doc_tf: list[Counter[str]] = []
    doc_len: list[int] = []
    for doc in corpus:
        tokens = _bm25_tokenize(doc)
        cnt = Counter(tokens)
        doc_tf.append(cnt)
        doc_len.append(len(tokens))
        for term in cnt:
            df[term] = df.get(term, 0) + 1
    avgdl = sum(doc_len) / N if N else 0.0
    return {
        "entries": entries,
        "doc_tf": doc_tf,
        "doc_len": doc_len,
        "df": df,
        "avgdl": avgdl,
        "N": N,
    }


def _bm25_score(
    query_tokens: list[str],
    index: _BM25Index,
    *,
    k1: float = 1.5,
    b: float = 0.75,
) -> list[tuple[int, float]]:
    """각 entry 별 BM25 score. (index, score) desc sort, score 0 제외."""
    entries = index["entries"]
    doc_tf = index["doc_tf"]
    doc_len = index["doc_len"]
    df = index["df"]
    avgdl = index["avgdl"]
    N = index["N"]
    if not N:
        return []
    scores: list[float] = [0.0] * N
    q_unique = list({t.strip().lower() for t in query_tokens if t and t.strip()})
    for q in q_unique:
        n = df.get(q, 0)
        if not n:
            continue
        # BM25+ smooth idf
        idf = math.log((N - n + 0.5) / (n + 0.5) + 1)
        for i, cnt in enumerate(doc_tf):
            f = cnt.get(q, 0)
            if not f:
                continue
            denom = (
                f + k1 * (1 - b + b * doc_len[i] / avgdl)
                if avgdl > 0
                else f + k1
            )
            scores[i] += idf * (f * (k1 + 1)) / denom
    out: list[tuple[int, float]] = [
        (i, s) for i, s in enumerate(scores) if s > 0
    ]
    out.sort(key=lambda t: t[1], reverse=True)
    return out


def _bm25_retrieve(
    entries: list[MemoryEntry],
    query_tokens: list[str],
    top_k: int,
) -> list[MemoryEntry]:
    """BM25 top-k retrieve. score 0 entry 는 제외."""
    if top_k <= 0 or not entries:
        return []
    index = _bm25_build_index(entries)
    scored = _bm25_score(query_tokens, index)
    return [index["entries"][i] for i, _ in scored[:top_k]]


def query_memory_index(
    workspace_root: Path,
    query: MemoryIndexQuery,
) -> MemoryIndexQueryResult:
    """3-tuple retrieval — 1 anchor exact → 2 BM25 fallback → 3 linked expansion.

    - 1단계: cue_anchor exact match (case-insensitive). hit 없으면 빈 set.
    - 2단계 (Phase 2b, opt-in): `query.use_bm25_fallback=True` 일 때만 1단계/3단계 결과가
      `top_k` 미달이면 BM25 top-k 로 fill. score 0 entry 는 제외.
    - 3단계: `mentioned_in` + `source_paths` 1-hop expansion, max_depth cap.
    """
    entries = load_memory_index(workspace_root)
    entries_by_id = {e.id: e for e in entries}
    anchor_index = build_cue_anchor_index(entries)

    seeds = _anchor_exact_match(query.query_tokens, anchor_index)

    # Phase 2b: 2단계 BM25 fallback helper
    def _bm25_fill(current: list[MemoryEntry], exclude_ids: set[str]) -> tuple[list[MemoryEntry], int]:
        if not query.use_bm25_fallback or len(current) >= query.top_k:
            return current, 0
        needed = query.top_k - len(current)
        bm25_pool = [e for e in entries if e.id not in exclude_ids]
        bm25_picks = _bm25_retrieve(bm25_pool, query.query_tokens, needed)
        return current + bm25_picks, len(bm25_picks)

    if query.max_depth <= 0:
        cue_selected = [entries_by_id[i] for i in sorted(seeds) if i in entries_by_id]
        cue_selected, bm25_added = _bm25_fill(cue_selected, seeds)
        return MemoryIndexQueryResult(
            query_tokens=list(query.query_tokens),
            selected_entries= cue_selected[: query.top_k],
            expansion_depth_used=0,
            cue_hits=len(seeds),
            expansion_hits=0,
            bm25_hits=bm25_added,
        )

    expanded_ids, used_depth = _linked_expansion(seeds, entries_by_id, query.max_depth)
    expansion_only = expanded_ids - seeds
    seed_and_linked = seeds | expansion_only

    selected_ids = sorted(seed_and_linked)[: query.top_k]
    selected: list[MemoryEntry] = [entries_by_id[i] for i in selected_ids if i in entries_by_id]
    selected, bm25_added = _bm25_fill(selected, seed_and_linked)
    return MemoryIndexQueryResult(
        query_tokens=list(query.query_tokens),
        selected_entries=selected[: query.top_k],
        expansion_depth_used=used_depth,
        cue_hits=len(seeds),
        expansion_hits=len(expansion_only),
        bm25_hits=bm25_added,
    )


# --- Top-level wrapper ---


def memory_index_status(workspace_root: Path) -> MemoryIndexOutput:
    """Top-level 진입점. CLI / caller 가 사용."""
    validation = validate_memory_index(workspace_root)
    return MemoryIndexOutput(
        tool_version=_WORKFLOW_KIT_VERSION,
        status=Status.WARNING if validation.issues else Status.OK,
        entries_loaded=validation.total_entries,
        issues=validation.issues,
        source_context={"workspace_root": str(workspace_root)},
    )


def query_memory_index_for_dispatcher(
    workspace_root: Path,
    query_tokens: list[str],
    *,
    top_k: int = 10,
    max_depth: int = 2,
    use_bm25_fallback: bool = False,
) -> MemoryIndexQueryOutput:
    """Phase 3: dispatcher `cmd_memory_index_query` 가 부르는 표준 entry.

    `query_memory_index(workspace_root, query)` 결과를 `MemoryIndexQueryOutput` 으로 wrap.
    다른 CLI subcommand 나 skill 이 본 wrapper 만 호출하면 retrieval layer 자동 활용.
    """
    query = MemoryIndexQuery(
        query_tokens=list(query_tokens),
        top_k=top_k,
        max_depth=max_depth,
        use_bm25_fallback=use_bm25_fallback,
    )
    result = query_memory_index(workspace_root, query)
    return MemoryIndexQueryOutput(
        tool_version=_WORKFLOW_KIT_VERSION,
        status=Status.OK,
        query_tokens=list(query_tokens),
        selected_ids=[e.id for e in result.selected_entries],
        selected_count=len(result.selected_entries),
        cue_hits=result.cue_hits,
        bm25_hits=result.bm25_hits,
        expansion_hits=result.expansion_hits,
        expansion_depth_used=result.expansion_depth_used,
        source_context={
            "workspace_root": str(workspace_root),
            "top_k": top_k,
            "max_depth": max_depth,
            "use_bm25_fallback": use_bm25_fallback,
        },
    )


# --- Phase 2: --merge opt-in canonical merge (ADR-005 §4) ---


def _dedupe_keep_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for v in values:
        if v not in seen:
            seen.add(v)
            out.append(v)
    return out


def apply_memory_merge(
    workspace_root: Path,
    request: MemoryMergeRequest,
) -> MemoryMergeResult:
    """ADR-005 §4 canonical merge — `--merge` opt-in.

    - `request.apply=False` (default) → dry-run preview 만. disk 변경 없음.
    - `request.apply=True` → target emit + source entries 의 `merge_state=LINKED` 로 atomic 갱신.

    target `primary_abstraction` 은 첫 source 의 값을 사용. caller 가 의도적 비대칭이면
    `MemoryMergeResult.warnings` 에 advisory emit.
    """
    entries = load_memory_index(workspace_root)
    entries_by_id = {e.id: e for e in entries}

    # source_ids 검증
    missing = [sid for sid in request.source_ids if sid not in entries_by_id]
    if missing:
        raise ValueError(f"source_ids 부재: {missing}")
    if len(set(request.source_ids)) != len(request.source_ids):
        raise ValueError(f"source_ids 가 중복: {request.source_ids}")

    sources = [entries_by_id[sid] for sid in request.source_ids]
    target_id = request.target_id or sources[0].id
    primary = sources[0].primary_abstraction

    warnings: list[str] = []
    if any(s.primary_abstraction.strip().lower() != sources[0].primary_abstraction.strip().lower()
           for s in sources[1:]):
        warnings.append(
            "source entries 의 primary_abstraction 가 case-insensitive 로 비대칭 — caller 의 의도 확인 권장"
        )
    if any(s.schema_version != sources[0].schema_version for s in sources[1:]):
        warnings.append("source entries 의 schema_version 비대칭 — schema migration 권장")

    merged_source_paths = _dedupe_keep_order([p for s in sources for p in s.source_paths])
    merged_cue_anchors = _dedupe_keep_order([a for s in sources for a in s.cue_anchors])
    mentioned_in = _dedupe_keep_order([m for s in sources for m in s.mentioned_in])
    owners = _dedupe_keep_order([o for s in sources for o in s.owners])
    scope = _dedupe_keep_order([sc for s in sources for sc in s.scope])

    now = datetime.now(timezone.utc)
    target_entry = MemoryEntry(
        id=target_id,
        schema_version=sources[0].schema_version,
        source_paths=merged_source_paths,
        primary_abstraction=primary,
        cue_anchors=merged_cue_anchors,
        value_digest=f"merged from {len(sources)} sources: " + ", ".join(request.source_ids),
        owners=owners,
        scope=scope,
        merge_state=MergeState.MERGED,
        mentioned_in=mentioned_in,
        created_at=sources[0].created_at,
        updated_at=now,
    )

    if not request.apply:
        return MemoryMergeResult(
            request=request,
            applied=False,
            target_id=target_id,
            source_ids=list(request.source_ids),
            merged_source_paths=merged_source_paths,
            merged_cue_anchors=merged_cue_anchors,
            mentioned_in=mentioned_in,
            warnings=warnings,
        )

    # apply=True: target emit + source LINKED 갱신. atomic_write_json 호출은 save_memory_entry 경유.
    save_memory_entry(workspace_root, target_entry)
    for s in sources:
        if s.id == target_id:
            continue  # target 과 같은 id 면 따로 갱신 안 함 (target_entry 가 그 entry 의 새 모습)
        linked_entry = s.model_copy(update={"merge_state": MergeState.LINKED, "updated_at": now})
        save_memory_entry(workspace_root, linked_entry)

    return MemoryMergeResult(
        request=request,
        applied=True,
        target_id=target_id,
        source_ids=list(request.source_ids),
        merged_source_paths=merged_source_paths,
        merged_cue_anchors=merged_cue_anchors,
        mentioned_in=mentioned_in,
        warnings=warnings,
    )


# --- Phase 13 AC2: telemetry sidecar (v0.13.1+) ---


def append_telemetry_event(
    workspace_root: Path,
    event: MemoryIndexTelemetryEvent,
) -> Path:
    """memory_index retrieval 1 호출의 event 를 `telemetry/events.jsonl` 에 1 line append.

    - file 부재 시 parent dir 자동 생성.
    - JSON encode + newline 1 개 terminator (POSIX `text` mode).
    - in-process lock (`threading.Lock`) 으로 동시 append 시 line race 방지.
    - 본 helper 는 caller (3 skill + dispatcher subcommand) 의 *zero-effort* 호출이
      정공법 — try/except 로 wrap 하여 retrieval 본체 실패가 와도 telemetry 자체가
      깨지면 안 되므로, 본 helper 자체는 OSError 시 silent return + stderr 경고.

    Returns:
        telemetry events.jsonl Path (caller 가 commit 시 참조 가능).
    """
    import sys as _sys
    import threading as _threading

    target = telemetry_path(workspace_root)
    target.parent.mkdir(parents=True, exist_ok=True)

    payload = event.model_dump(mode="json")
    line = json.dumps(payload, ensure_ascii=False) + "\n"

    # in-process lock — concurrent emit (3 skill 이 동시에 실행될 가능성) 시
    # line race 방지. cross-process 동시성은 best-effort (crash-safe 는 consumer_metrics
    # 의 open("a") + write + flush 패턴과 동일 정공법).
    lock_attr = "_memory_index_telemetry_lock"
    lock = getattr(append_telemetry_event, lock_attr, None)
    if lock is None:
        lock = _threading.Lock()
        setattr(append_telemetry_event, lock_attr, lock)
    with lock:
        try:
            with target.open("a", encoding="utf-8") as fp:
                fp.write(line)
                fp.flush()
        except OSError as e:
            # telemetry 부재가 retrieval 본체를 깨면 안 됨 (zero-risk default).
            print(
                f"WARN: memory_index telemetry append 실패: {type(e).__name__}: {e}",
                file=_sys.stderr,
            )
    return target


def _read_telemetry_events(tp: Path) -> tuple[list[MemoryIndexTelemetryEvent], int]:
    """`events.jsonl` 의 모든 line 을 parse. malformed line skip + 카운트.

    Returns:
        (parsed events, skipped line count).
    """
    events: list[MemoryIndexTelemetryEvent] = []
    skipped = 0
    if not tp.exists():
        return events, 0
    try:
        text = tp.read_text(encoding="utf-8")
    except OSError:
        return events, 0
    for raw in text.splitlines():
        stripped = raw.strip()
        if not stripped:
            continue
        try:
            data = json.loads(stripped)
        except json.JSONDecodeError:
            skipped += 1
            continue
        try:
            events.append(MemoryIndexTelemetryEvent.model_validate(data))
        except Exception:
            skipped += 1
            continue
    return events, skipped


#: 윈도 지표의 기본 크기(일). Phase 13 AC2 의 "지속적 사용" 을 재는 창.
DEFAULT_TELEMETRY_WINDOW_DAYS: int = 30


def summarize_telemetry(
    workspace_root: Path,
    *,
    window_days: int = DEFAULT_TELEMETRY_WINDOW_DAYS,
    now: "datetime | None" = None,
) -> MemoryIndexTelemetrySummary:
    """`telemetry/events.jsonl` 의 read-time 집계.

    - file 부재 / empty → total_calls=0, hit_rate=0.0 graceful return.
    - malformed line skip → events_skipped 증가, events_parsed 불변.
    - by_source 분해: source 별 {calls, hits} dict.
    - first_event_at / last_event_at: 가장 이른/늦은 timestamp 의 ISO 8601 repr.
    - hit 정의: selected_count > 0 (어떤 단계든 1+ entry 가 retrieval 됨).

    Args:
        window_days: v1.1.3+. 최근 N일 윈도 지표를 함께 계산한다 (`window_*` 필드).
            **전체 기간 필드는 그대로다** — 기존 소비자 정합. 0 이면 윈도 집계를
            건너뛴다.
        now: 윈도 기준 시각 (테스트 주입용). 생략 시 현재 UTC.

    왜 윈도가 필요한가: 전체 기간 `by_source` 는 **각 경로를 한 번씩만 돌려도**
    4 source 가 찬다. 2026-08-09 P0-2 가 실제로 그렇게 충족됐고, 그래서 그 숫자는
    *지속적 사용* 을 재지 못한다. 윈도는 방치하면 값이 떨어진다.
    """
    tp = telemetry_path(workspace_root)
    events, skipped = _read_telemetry_events(tp)

    total_calls = len(events)
    total_hits = sum(1 for e in events if e.selected_count > 0 and not e.error)
    # round(4) 를 계산 지점(단일 출처)에서 한다. hit_rate 가 33일간 정확히 1.0
    # 이던 시절에는 소비자별 반올림 차이가 보이지 않았고, 첫 miss (W-2 컨텍스트
    # 질의) 가 Panel 3 (raw) != Panel 8 (round 4) cross-check 실패로 드러냈다.
    hit_rate = round((total_hits / total_calls), 4) if total_calls else 0.0

    by_source: dict[str, dict[str, int]] = {}
    for e in events:
        bucket = by_source.setdefault(e.source, {"calls": 0, "hits": 0})
        bucket["calls"] += 1
        if e.selected_count > 0 and not e.error:
            bucket["hits"] += 1

    first_event_at = ""
    last_event_at = ""
    if events:
        timestamps = [e.timestamp for e in events]
        first_event_at = min(timestamps).isoformat()
        last_event_at = max(timestamps).isoformat()

    # --- 윈도 집계 (v1.1.3+) ---------------------------------------------
    window_calls = 0
    window_hits = 0
    window_by_source: dict[str, dict[str, int]] = {}
    if window_days > 0 and events:
        reference = now or datetime.now(timezone.utc)
        cutoff = reference - timedelta(days=window_days)
        for e in events:
            ts = e.timestamp
            # 과거 event 가 naive 로 들어온 경우 UTC 로 간주 — 비교에서 터지지 않게.
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            if ts < cutoff:
                continue
            window_calls += 1
            bucket = window_by_source.setdefault(e.source, {"calls": 0, "hits": 0})
            bucket["calls"] += 1
            if e.selected_count > 0 and not e.error:
                window_hits += 1
                bucket["hits"] += 1

    return MemoryIndexTelemetrySummary(
        total_calls=total_calls,
        total_hits=total_hits,
        hit_rate=hit_rate,
        by_source=by_source,
        first_event_at=first_event_at,
        last_event_at=last_event_at,
        events_parsed=total_calls,
        events_skipped=skipped,
        window_days=window_days,
        window_calls=window_calls,
        window_hits=window_hits,
        window_hit_rate=round((window_hits / window_calls), 4) if window_calls else 0.0,
        window_by_source=window_by_source,
        window_source_count=len(window_by_source),
    )


def read_telemetry_events(workspace_root: Path) -> list[MemoryIndexTelemetryEvent]:
    """telemetry events 의 raw list (subcommand `--show-events` 용).

    malformed line 은 skip. caller 가 timestamp 별 sort 필요 시 자체 처리.
    """
    tp = telemetry_path(workspace_root)
    events, _ = _read_telemetry_events(tp)
    return events


# --- W-1 (ADR-006 후속): write-path advisory — entry 승격 후보 제안 ---

#: 제목 token 이 기존 entry corpus 에 이만큼 미만으로 덮이면 "index 가 모르는
#: 작업" 후보로 본다. 실측 근거는 tests/check_memory_entry_suggestions.py 참조.
#: 판정이 아니라 후보 선별 — 최종 적재 여부는 사람/에이전트가 결정한다.
SUGGESTION_COVERAGE_THRESHOLD: Final[float] = 0.5

#: 후보 제안 시 cue_anchors 로 제시할 token 의 최대 개수.
_SUGGESTED_ANCHORS_CAP: Final[int] = 8

#: cue 로서 정보가 없는 범용 token (handoff 제목에 항상 나오는 것들).
_ANCHOR_STOPWORDS: Final[frozenset[str]] = frozenset({
    "task", "main", "2026", "the", "and", "for",
})


def _next_entry_id(entries: list[MemoryEntry], date_str: str) -> str:
    """`MEM-<date>-NNN` 의 다음 빈 sequence. 같은 날짜 entry 가 없으면 001."""
    prefix = f"MEM-{date_str}-"
    used = [
        int(e.id[len(prefix):])
        for e in entries
        if e.id.startswith(prefix) and e.id[len(prefix):].isdigit()
    ]
    return f"{prefix}{(max(used) + 1) if used else 1:03d}"


def suggest_memory_entry_candidates(
    entries: list[MemoryEntry],
    handoff_text: str,
    *,
    date_str: str,
    threshold: float = SUGGESTION_COVERAGE_THRESHOLD,
    max_candidates: int = 5,
) -> dict[str, object]:
    """세션이 남긴 완료 작업 중 memory_index 가 모르는 것을 entry 후보로 제안한다.

    **advisory 다 — 아무것도 쓰지 않는다.** ADR-006 회고의 W-1: 30일간 신규
    entry 0건의 원인은 쓰기 운영 루프 부재였다. 자동 적재는 하지 않는다 —
    entry 의 primary_abstraction/value_digest 는 *무엇이 기억할 가치가 있는가*
    라는 판단이고, 도구가 대신 쓰면 거짓이 된다.

    판정: handoff §4 (최근 완료 작업) 의 제목 token 이 기존 entry corpus
    (`primary_abstraction + cue_anchors + value_digest`) 로 얼마나 덮이는지
    (coverage = |제목 ∩ entry| / |제목|). 최대 coverage 가 threshold 미만이면
    후보. 후보에는 스키마 모양의 skeleton 을 함께 준다 — 채우는 건 사람이다.

    Returns:
        ``{"candidates": [...], "compared": int, "covered": int,
        "threshold": float, "entries_loaded": int}``
        각 candidate: ``{"task_id", "title", "best_coverage",
        "nearest_entry_id", "suggested_cue_anchors", "skeleton"}``
    """
    from workflow_kit.common.drift_detection import extract_section, extract_task_titles

    section = extract_section(handoff_text, "최근 완료 작업")
    titles = extract_task_titles(section)

    entry_tokens: list[tuple[MemoryEntry, set[str]]] = [
        (e, set(_bm25_tokenize(_bm25_text_for_entry(e)))) for e in entries
    ]

    candidates: list[dict[str, object]] = []
    covered = 0
    next_id = _next_entry_id(entries, date_str)
    for task_id, title in titles.items():
        tokens = set(_bm25_tokenize(title))
        if not tokens:
            continue
        best_coverage = 0.0
        nearest: str | None = None
        for entry, etoks in entry_tokens:
            coverage = len(tokens & etoks) / len(tokens)
            if coverage > best_coverage:
                best_coverage = coverage
                nearest = entry.id
        if best_coverage >= threshold:
            covered += 1
            continue
        anchors = [
            t for t in _bm25_tokenize(title)
            if len(t) >= 2 and t not in _ANCHOR_STOPWORDS and not t.isdigit()
        ]
        anchors = _dedupe_keep_order(anchors)
        candidates.append({
            "task_id": task_id,
            "title": title,
            "best_coverage": round(best_coverage, 4),
            "nearest_entry_id": nearest,
            "suggested_cue_anchors": anchors[:_SUGGESTED_ANCHORS_CAP],
            "skeleton": {
                "id": next_id,
                "schema_version": 1,
                "source_paths": ["<원문 경로 — task 파일 / 세션 기록>"],
                "primary_abstraction": f"<6-8 단어 canonical 요약: {title[:60]}>",
                "cue_anchors": anchors[:_SUGGESTED_ANCHORS_CAP],
                "value_digest": "<본문 1줄 요약 — 사람이 채울 것>",
                "owners": [],
                "scope": [],
                "merge_state": "active",
                "mentioned_in": [],
                "created_at": f"{date_str}T00:00:00Z",
                "updated_at": f"{date_str}T00:00:00Z",
            },
        })
    candidates.sort(key=lambda c: (float(str(c["best_coverage"])), str(c["task_id"])))
    return {
        "candidates": candidates[:max_candidates],
        "candidates_total": len(candidates),
        "compared": len(titles),
        "covered": covered,
        "threshold": threshold,
        "entries_loaded": len(entries),
    }


# --- W-2 (ADR-006 후속): 컨텍스트 유래 질의 token ---

#: 질의 출처 값 (telemetry `query_source` 에 그대로 기록).
QUERY_SOURCE_CONTEXT: Final[str] = "context"
QUERY_SOURCE_DEFAULT: Final[str] = "default"
QUERY_SOURCE_EXPLICIT: Final[str] = "explicit"

#: 컨텍스트 유도 질의의 token 상한.
_CONTEXT_QUERY_CAP: Final[int] = 8


def derive_context_query_tokens(
    state_path: Path | None,
    *,
    base_tokens: list[str],
    max_tokens: int = _CONTEXT_QUERY_CAP,
) -> tuple[list[str], str]:
    """현재 작업 컨텍스트에서 질의 token 을 유도한다. 실패 시 (base_tokens, "default").

    ADR-006 회고 (W-2): 3 skill 의 질의는 각자 고정 trio 였고 공통 token
    "workflow" 가 항상 같은 entry 를 집어 33일간 질의 다양성이 1 이었다.
    여기서는 state.json 의 `session.current_axis` + `backlog.done_items` 상위
    3건 제목에서 token 을 뽑는다 — 질의가 지금 하는 일을 따라가면 조회 결과도
    (그리고 miss 도) 정보를 갖는다.

    유도 실패(state 부재/파싱 불가/유의미 token 없음)는 base_tokens 로
    떨어지되 출처를 반드시 함께 돌려준다 — 조용한 fallback 은 출처를
    내놓아야 한다. caller 는 출처를 telemetry `query_source` 에 기록한다.
    """
    if state_path is None or not state_path.is_file():
        return list(base_tokens), QUERY_SOURCE_DEFAULT
    try:
        data = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return list(base_tokens), QUERY_SOURCE_DEFAULT
    session = data.get("session") or {}
    backlog = data.get("backlog") or {}
    parts: list[str] = []
    axis = session.get("current_axis")
    if isinstance(axis, str):
        parts.append(axis)
    done_items = backlog.get("done_items")
    if isinstance(done_items, list):
        parts.extend(str(item) for item in done_items[:3])
    tokens = [
        t for t in _bm25_tokenize(" ".join(parts))
        if len(t) >= 2 and not t.isdigit() and t not in _ANCHOR_STOPWORDS
    ]
    tokens = _dedupe_keep_order(tokens)[:max_tokens]
    if not tokens:
        return list(base_tokens), QUERY_SOURCE_DEFAULT
    return tokens, QUERY_SOURCE_CONTEXT
