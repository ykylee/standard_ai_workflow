"""ADR-027 roadmap · milestone · WBS layer 의 파서 + 파생 + 생성기 (M-002).

`ai-workflow/memory/active/roadmap/` SSOT(index.md + M-NNN-*.md)를 읽어
선언(`Roadmap`)을 만들고, task frontmatter `wbs:` 링크와 합쳐
`roadmap_state.json`(`RoadmapState`)을 파생한다.

정본 계약: workflow-source/core/roadmap_milestone_wbs_spec.md
- 진척은 손으로 적지 않는다 — leaf ← task 상태, 중간 노드 ← 자식 롤업 (§7.2).
- 분모는 **선언한 leaf 수**다. 연결 task 수를 분모로 잡으면 링크를 지울수록
  진척이 오른다 (50차 규칙).
- roadmap 부재는 실패가 아니라 **해당 없음**이다 — 게이트도 파생도 성립하지
  않고, 호출자는 None 을 받는다 (graceful skip).
- `roadmap_state.json` 은 생성물이다. 손편집은 `check_roadmap_state_generated`
  가 대조한다. 재생성 대조에서 `generated_at` 은 제외한다 — 매일 바뀌는 값을
  리터럴로 물면 그 검사는 내일 red 다.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Final

from pydantic import ValidationError

from workflow_kit.common.atomic_write import atomic_write_json
from workflow_kit.common.paths import memory_active_dir
from workflow_kit.common.schemas.roadmap import (
    MILESTONE_ID_PATTERN,
    WBS_EXEMPT_VALUE,
    WBS_ID_PATTERN,
    Milestone,
    MilestoneState,
    Roadmap,
    RoadmapIndexEntry,
    RoadmapIssue,
    RoadmapItemStatus,
    RoadmapState,
    SdlcPhase,
    SessionStartRoadmapContext,
    TaskWbsLink,
    WbsGateVerdict,
    WbsNode,
    WbsNodeState,
)

# --- Layout constants ---------------------------------------------------------

ROADMAP_SUBDIR: Final[str] = "roadmap"
INDEX_FILE: Final[str] = "index.md"
STATE_FILE: Final[str] = "roadmap_state.json"

MILESTONE_FILE_RE: Final[re.Pattern[str]] = re.compile(r"^(M-\d{3})-[a-z0-9-]+\.md$")

#: index.md `## Milestones` 목록의 엔트리 줄.
_INDEX_ENTRY_RE: Final[re.Pattern[str]] = re.compile(
    r"^-\s+\*\*(M-\d{3})\*\*\s+\[(?P<phase>[a-z_]+)\]\s+(?P<title>.+?)\s+—\s+status:\s*(?P<status>[a-z_]+)\s*$"
)
_INDEX_PATH_RE: Final[re.Pattern[str]] = re.compile(r"^\s+-\s+path:\s+\[[^\]]*\]\((?P<path>[^)]+)\)\s*$")

#: 마일스톤 파일 `## WBS` 절의 노드 줄. 들여쓰기 2칸 = 1단계.
_WBS_LINE_RE: Final[re.Pattern[str]] = re.compile(
    r"^(?P<indent>\s*)-\s+\*\*(?P<id>WBS-[\d.]+)\*\*\s+(?P<title>.+?)(?:\s+—\s+산출물:\s*(?P<note>.+))?\s*$"
)

_FRONTMATTER_RE: Final[re.Pattern[str]] = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)

#: task frontmatter `wbs:` 참조 형식 — 'M-002/WBS-2.1' (스펙 §5).
_WBS_REF_RE: Final[re.Pattern[str]] = re.compile(r"^(M-\d{3})/(WBS-[\d.]+)$")


# --- Paths --------------------------------------------------------------------


def roadmap_root(workspace_root: Path) -> Path:
    """`ai-workflow/memory/active/roadmap/` — 브랜치 무관 공유 위치 (스펙 §2)."""
    return memory_active_dir(workspace_root) / ROADMAP_SUBDIR


def state_path(workspace_root: Path) -> Path:
    """`roadmap/roadmap_state.json` 절대 경로."""
    return roadmap_root(workspace_root) / STATE_FILE


def roadmap_exists(workspace_root: Path) -> bool:
    """게이트·파생의 성립 조건 — index.md 실재가 로드맵 존재의 정의다 (스펙 §6)."""
    return (roadmap_root(workspace_root) / INDEX_FILE).is_file()


#: index.md 메타데이터의 draft 표기 — 기존 프로젝트 온보딩 초안 (스펙 §9).
_INDEX_DRAFT_RE: Final[re.Pattern[str]] = re.compile(r"^-\s*상태:\s*draft\b", re.MULTILINE)


def roadmap_is_draft(workspace_root: Path) -> bool:
    """로드맵이 draft(소유자 미확정 초안)인가 — index.md 의 `- 상태: draft` 선언.

    draft 는 게이트를 발동시키지 않는다: 추정 초안이 강제를 발동시키면 draft 가
    draft 가 아니다. 소유자가 상태를 active 로 바꾸고 현재 마일스톤을 선언하는
    것이 확정이고, 그때 게이트가 선다.
    """
    index_path = roadmap_root(workspace_root) / INDEX_FILE
    if not index_path.is_file():
        return False
    return bool(_INDEX_DRAFT_RE.search(index_path.read_text(encoding="utf-8")))


# --- Frontmatter (YAML subset — 외부 의존 없이, kit 관행대로 손파서) -----------


def _parse_frontmatter_block(text: str) -> tuple[dict[str, object], str]:
    """frontmatter 를 {key: str | list[str]} 로. 스칼라 / 인라인 [] / 블록 리스트 지원."""
    match = _FRONTMATTER_RE.match(text)
    if not match:
        return {}, text
    body = text[match.end():]
    pairs: dict[str, object] = {}
    current_list_key: str | None = None
    for raw in match.group(1).splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        item = raw.strip()
        if current_list_key is not None and item.startswith("- "):
            existing = pairs[current_list_key]
            assert isinstance(existing, list)
            existing.append(item[2:].strip())
            continue
        current_list_key = None
        if ":" not in raw:
            continue
        key, _, value = raw.partition(":")
        key = key.strip()
        value = value.split("#", 1)[0].strip()
        if value == "":
            pairs[key] = []
            current_list_key = key
        elif value.startswith("[") and value.endswith("]"):
            inner = value[1:-1].strip()
            pairs[key] = [v.strip() for v in inner.split(",") if v.strip()] if inner else []
        else:
            pairs[key] = value
    return pairs, body


def _as_str(pairs: dict[str, object], key: str) -> str:
    value = pairs.get(key, "")
    return value if isinstance(value, str) else ""


def _as_list(pairs: dict[str, object], key: str) -> list[str]:
    value = pairs.get(key, [])
    return [str(v) for v in value] if isinstance(value, list) else []


# --- Milestone file parsing ---------------------------------------------------


def parse_milestone_text(text: str, source_path: str) -> tuple[Milestone | None, list[RoadmapIssue]]:
    """마일스톤 파일 1개의 frontmatter + `## WBS` 절을 파싱한다.

    스키마 위반(어휘 밖 sdlc_phase / status, id 형식)은 issue 로 변환한다 —
    어휘 밖 값은 조용히 기본값으로 뭉개지 않는다.
    """
    issues: list[RoadmapIssue] = []
    pairs, body = _parse_frontmatter_block(text)
    if not pairs:
        issues.append(RoadmapIssue(code="milestone_parse_error", detail="frontmatter 부재", where=source_path))
        return None, issues

    wbs_nodes, wbs_issues = _parse_wbs_section(body, source_path)
    issues.extend(wbs_issues)

    order_text = _as_str(pairs, "order")
    try:
        milestone = Milestone(
            id=_as_str(pairs, "id"),
            title=_as_str(pairs, "title"),
            sdlc_phase=SdlcPhase(_as_str(pairs, "sdlc_phase")),
            status=RoadmapItemStatus(_as_str(pairs, "status")),
            order=int(order_text) if order_text.isdigit() else -1,
            parallel_allowed=_as_list(pairs, "parallel_allowed"),
            deliverables=_as_list(pairs, "deliverables"),
            wbs=wbs_nodes,
            source_path=source_path,
        )
    except (ValidationError, ValueError) as exc:
        issues.append(RoadmapIssue(code="milestone_parse_error", detail=str(exc), where=source_path))
        return None, issues

    for node_id in _walk_ids(milestone.wbs):
        wbs_match = WBS_ID_PATTERN.match(node_id)
        if wbs_match and int(wbs_match.group(1)) != milestone.number:
            issues.append(RoadmapIssue(
                code="wbs_milestone_number_mismatch",
                detail=f"{node_id} 의 첫 세그먼트가 {milestone.id} 의 번호와 다르다",
                where=source_path,
            ))
    return milestone, issues


def _parse_wbs_section(body: str, source_path: str) -> tuple[list[WbsNode], list[RoadmapIssue]]:
    issues: list[RoadmapIssue] = []
    in_wbs = False
    roots: list[WbsNode] = []
    stack: list[tuple[int, WbsNode]] = []  # (indent, node)
    seen_ids: set[str] = set()
    for line in body.splitlines():
        if line.startswith("## "):
            in_wbs = line.strip() == "## WBS"
            continue
        if not in_wbs:
            continue
        match = _WBS_LINE_RE.match(line)
        if not match:
            continue
        node_id = match.group("id")
        if node_id in seen_ids:
            issues.append(RoadmapIssue(code="duplicate_wbs_id", detail=f"WBS id 중복: {node_id}", where=source_path))
            continue
        if not WBS_ID_PATTERN.match(node_id):
            issues.append(RoadmapIssue(code="wbs_id_format", detail=f"WBS id 형식 위반: {node_id}", where=source_path))
            continue
        seen_ids.add(node_id)
        node = WbsNode(
            id=node_id,
            title=match.group("title").strip(),
            deliverable_note=(match.group("note") or "").strip(),
        )
        indent = len(match.group("indent"))
        while stack and stack[-1][0] >= indent:
            stack.pop()
        if stack:
            stack[-1][1].children.append(node)
        else:
            roots.append(node)
        stack.append((indent, node))
    return roots, issues


def _walk_ids(nodes: list[WbsNode]) -> list[str]:
    out: list[str] = []
    for node in nodes:
        out.append(node.id)
        out.extend(_walk_ids(node.children))
    return out


# --- Index + directory loading ------------------------------------------------


def parse_index_text(text: str) -> tuple[list[RoadmapIndexEntry], list[RoadmapIssue]]:
    """index.md `## Milestones` 목록을 순서 선언으로 파싱한다."""
    issues: list[RoadmapIssue] = []
    entries: list[RoadmapIndexEntry] = []
    pending: tuple[str, str] | None = None  # (id, status) — path 줄을 기다린다
    position = 0
    for line in text.splitlines():
        entry_match = _INDEX_ENTRY_RE.match(line)
        if entry_match:
            if pending is not None:
                issues.append(RoadmapIssue(code="index_entry_without_path", detail=f"path 줄 부재: {pending[0]}", where=INDEX_FILE))
            pending = (entry_match.group(1), entry_match.group("status"))
            continue
        path_match = _INDEX_PATH_RE.match(line)
        if path_match and pending is not None:
            entry_id, status_text = pending
            pending = None
            position += 1
            try:
                entries.append(RoadmapIndexEntry(
                    id=entry_id,
                    status=RoadmapItemStatus(status_text),
                    path=path_match.group("path"),
                    position=position,
                ))
            except (ValidationError, ValueError):
                issues.append(RoadmapIssue(code="index_status_vocab", detail=f"{entry_id} status 어휘 밖: {status_text!r}", where=INDEX_FILE))
    if pending is not None:
        issues.append(RoadmapIssue(code="index_entry_without_path", detail=f"path 줄 부재: {pending[0]}", where=INDEX_FILE))
    return entries, issues


def load_roadmap(workspace_root: Path) -> tuple[Roadmap | None, list[RoadmapIssue]]:
    """roadmap/ 디렉터리 전체를 선언으로 읽는다. index 부재 → (None, []) — 해당 없음."""
    root = roadmap_root(workspace_root)
    index_path = root / INDEX_FILE
    if not index_path.is_file():
        return None, []

    issues: list[RoadmapIssue] = []
    entries, index_issues = parse_index_text(index_path.read_text(encoding="utf-8"))
    issues.extend(index_issues)

    milestones: list[Milestone] = []
    seen_milestone_ids: set[str] = set()
    files_by_id: dict[str, str] = {}
    for path in sorted(root.glob("M-*.md")):
        file_match = MILESTONE_FILE_RE.match(path.name)
        if not file_match:
            issues.append(RoadmapIssue(code="milestone_filename_format", detail=f"파일명 형식 위반 (M-NNN-<slug>.md): {path.name}", where=path.name))
            continue
        milestone, m_issues = parse_milestone_text(path.read_text(encoding="utf-8"), path.name)
        issues.extend(m_issues)
        if milestone is None:
            continue
        if milestone.id != file_match.group(1):
            issues.append(RoadmapIssue(code="index_id_mismatch", detail=f"frontmatter id {milestone.id} ≠ 파일명 {file_match.group(1)}", where=path.name))
            continue
        if milestone.id in seen_milestone_ids:
            issues.append(RoadmapIssue(code="duplicate_milestone_id", detail=f"milestone id 중복: {milestone.id}", where=path.name))
            continue
        seen_milestone_ids.add(milestone.id)
        files_by_id[milestone.id] = path.name
        milestones.append(milestone)

    by_id = {m.id: m for m in milestones}
    for entry in entries:
        milestone = by_id.get(entry.id)
        if milestone is None:
            issues.append(RoadmapIssue(code="index_missing_file", detail=f"index 가 가리키는 {entry.id} 의 파일이 없다", where=INDEX_FILE))
            continue
        if milestone.order != entry.position:
            issues.append(RoadmapIssue(
                code="order_mismatch",
                detail=f"{entry.id}: index 위치 {entry.position} ≠ frontmatter order {milestone.order}",
                where=files_by_id.get(entry.id, entry.id),
            ))
        if milestone.status != entry.status:
            issues.append(RoadmapIssue(
                code="index_status_mismatch",
                detail=f"{entry.id}: index status {entry.status.value} ≠ frontmatter status {milestone.status.value}",
                where=files_by_id.get(entry.id, entry.id),
            ))
    indexed_ids = {entry.id for entry in entries}
    for milestone in milestones:
        if milestone.id not in indexed_ids:
            issues.append(RoadmapIssue(code="index_entry_missing_for_file", detail=f"{milestone.id} 가 index 목록에 없다", where=milestone.source_path))

    return Roadmap(index_entries=entries, milestones=milestones), issues


# --- Task link collection -----------------------------------------------------


def collect_task_wbs_links(workspace_root: Path) -> list[TaskWbsLink]:
    """`active/<branch>/backlog/tasks/TASK-*.md` 전 브랜치에서 `wbs:` 선언을 모은다.

    로드맵은 프로젝트 전체의 것이므로 브랜치 네임스페이스 전부를 본다.
    `wbs:` 가 없는 task 는 링크가 아니다 (게이트는 M-004 의 일이고, 여기서는
    수집만 한다).
    """
    links: list[TaskWbsLink] = []
    active = memory_active_dir(workspace_root)
    if not active.is_dir():
        return links
    for task_path in sorted(active.glob("*/backlog/tasks/TASK-*.md")):
        pairs, _ = _parse_frontmatter_block(task_path.read_text(encoding="utf-8"))
        wbs_ref = _as_str(pairs, "wbs")
        if not wbs_ref:
            continue
        links.append(TaskWbsLink(
            task_id=_as_str(pairs, "id") or task_path.stem,
            task_status=_as_str(pairs, "status") or "unknown",
            wbs_ref=wbs_ref,
            exempt_reason=_as_str(pairs, "wbs_exempt_reason"),
            source_path=str(task_path.relative_to(workspace_root)),
        ))
    return links


# --- Derivation (스펙 §7.2) ---------------------------------------------------


def _derive_leaf_status(task_statuses: list[str]) -> RoadmapItemStatus:
    """leaf: 연결 task 전부 done → done / in_progress·blocked 우선 반영 / 0건 → planned."""
    if not task_statuses:
        return RoadmapItemStatus.PLANNED
    statuses = set(task_statuses)
    if statuses == {"done"}:
        return RoadmapItemStatus.DONE
    if "in_progress" in statuses:
        return RoadmapItemStatus.IN_PROGRESS
    if "blocked" in statuses:
        return RoadmapItemStatus.BLOCKED
    if "done" in statuses:
        return RoadmapItemStatus.IN_PROGRESS  # done+planned 혼재 = 진행 중
    return RoadmapItemStatus.PLANNED


def _derive_node(node: WbsNode, milestone_id: str, links_by_ref: dict[str, list[TaskWbsLink]]) -> WbsNodeState:
    if node.children:
        child_states = [_derive_node(child, milestone_id, links_by_ref) for child in node.children]
        total = sum(c.total_leaves for c in child_states)
        done = sum(c.done_leaves for c in child_states)
        child_statuses = {c.derived_status for c in child_states}
        if child_statuses == {RoadmapItemStatus.DONE}:
            derived = RoadmapItemStatus.DONE
        elif child_statuses == {RoadmapItemStatus.PLANNED}:
            derived = RoadmapItemStatus.PLANNED
        elif RoadmapItemStatus.BLOCKED in child_statuses and RoadmapItemStatus.IN_PROGRESS not in child_statuses:
            derived = RoadmapItemStatus.BLOCKED
        else:
            derived = RoadmapItemStatus.IN_PROGRESS
        return WbsNodeState(
            id=node.id, title=node.title, derived_status=derived,
            total_leaves=total, done_leaves=done, children=child_states,
        )
    linked = links_by_ref.get(f"{milestone_id}/{node.id}", [])
    derived = _derive_leaf_status([link.task_status for link in linked])
    return WbsNodeState(
        id=node.id, title=node.title, derived_status=derived,
        linked_task_ids=[link.task_id for link in linked],
        total_leaves=1, done_leaves=1 if derived is RoadmapItemStatus.DONE else 0,
    )


def collect_wbs_refs(roadmap: Roadmap) -> tuple[set[str], set[str]]:
    """(leaf refs, non-leaf refs) — 'M-002/WBS-2.1' 형태. 파생과 게이트가 공유한다."""
    leaf_refs: set[str] = set()
    non_leaf_refs: set[str] = set()

    def _collect(node: WbsNode, mid: str) -> None:
        ref = f"{mid}/{node.id}"
        if node.children:
            non_leaf_refs.add(ref)
            for child in node.children:
                _collect(child, mid)
        else:
            leaf_refs.add(ref)

    for milestone in roadmap.milestones:
        for root_node in milestone.wbs:
            _collect(root_node, milestone.id)
    return leaf_refs, non_leaf_refs


def derive_state(roadmap: Roadmap, links: list[TaskWbsLink], workspace_root: Path,
                 base_issues: list[RoadmapIssue] | None = None) -> RoadmapState:
    """선언 + task 링크 → RoadmapState. 불일치는 자동 수정하지 않고 issue 로 보고한다."""
    issues: list[RoadmapIssue] = list(base_issues or [])
    leaf_refs, non_leaf_refs = collect_wbs_refs(roadmap)

    links_by_ref: dict[str, list[TaskWbsLink]] = {}
    exempt_tasks: list[TaskWbsLink] = []
    for link in links:
        if link.wbs_ref == WBS_EXEMPT_VALUE:
            if not link.exempt_reason:
                issues.append(RoadmapIssue(code="exempt_without_reason", detail=f"{link.task_id}: wbs=exempt 인데 사유 선언이 없다", where=link.source_path))
            exempt_tasks.append(link)
            continue
        if not _WBS_REF_RE.match(link.wbs_ref):
            issues.append(RoadmapIssue(code="wbs_ref_format", detail=f"{link.task_id}: wbs 참조 형식 위반: {link.wbs_ref!r}", where=link.source_path))
            continue
        if link.wbs_ref in non_leaf_refs:
            issues.append(RoadmapIssue(code="wbs_link_not_leaf", detail=f"{link.task_id}: {link.wbs_ref} 는 leaf 가 아니다", where=link.source_path))
            continue
        if link.wbs_ref not in leaf_refs:
            issues.append(RoadmapIssue(code="wbs_dangling_link", detail=f"{link.task_id}: {link.wbs_ref} 가 로드맵에 없다", where=link.source_path))
            continue
        links_by_ref.setdefault(link.wbs_ref, []).append(link)

    milestone_states: list[MilestoneState] = []
    for milestone in sorted(roadmap.milestones, key=lambda m: m.order):
        wbs_states = [_derive_node(node, milestone.id, links_by_ref) for node in milestone.wbs]
        total = sum(s.total_leaves for s in wbs_states)
        done = sum(s.done_leaves for s in wbs_states)
        missing = [d for d in milestone.deliverables if not (workspace_root / d).exists()]

        all_leaves_done = total > 0 and done == total
        statuses = {s.derived_status for s in wbs_states}
        if all_leaves_done and not missing:
            derived = RoadmapItemStatus.DONE
        elif all_leaves_done and missing:
            derived = RoadmapItemStatus.IN_PROGRESS  # WBS 100% 여도 산출물 부재면 done 이 아니다 (§7.2)
        elif not statuses or statuses == {RoadmapItemStatus.PLANNED}:
            derived = RoadmapItemStatus.PLANNED
        elif RoadmapItemStatus.BLOCKED in statuses and RoadmapItemStatus.IN_PROGRESS not in statuses:
            derived = RoadmapItemStatus.BLOCKED
        else:
            derived = RoadmapItemStatus.IN_PROGRESS

        if milestone.status is RoadmapItemStatus.DONE and missing:
            issues.append(RoadmapIssue(code="deliverable_missing", detail=f"{milestone.id}: done 선언인데 산출물 부재: {missing}", where=milestone.source_path))
        # 불일치는 **done 경계**에서만 보고한다: 선언과 파생의 "끝났는가" 가
        # 갈릴 때가 드리프트다. in_progress 선언 + 링크 0(파생 planned)은
        # "열었는데 아직 task 가 없다" 는 정상 시작 상태다 — 씨앗 직후의 모든
        # 프로젝트가 그 모양이고, 그걸 물면 위양성이 첫날부터 경고를 낸다
        # (위양성을 내는 검사는 무시당한다).
        declared_done = milestone.status is RoadmapItemStatus.DONE
        derived_done = derived is RoadmapItemStatus.DONE
        if declared_done != derived_done:
            issues.append(RoadmapIssue(
                code="declared_derived_mismatch",
                detail=f"{milestone.id}: 선언 {milestone.status.value} ≠ 파생 {derived.value} (done 경계)",
                where=milestone.source_path,
            ))
        if milestone.status is RoadmapItemStatus.DONE:
            for ref, ref_links in links_by_ref.items():
                if ref.startswith(f"{milestone.id}/"):
                    open_tasks = [l.task_id for l in ref_links if l.task_status in ("planned", "in_progress", "blocked")]
                    if open_tasks:
                        issues.append(RoadmapIssue(code="done_milestone_open_task", detail=f"{milestone.id}: done 선언 아래 열린 task {open_tasks}", where=milestone.source_path))

        milestone_states.append(MilestoneState(
            id=milestone.id, title=milestone.title, sdlc_phase=milestone.sdlc_phase,
            declared_status=milestone.status, derived_status=derived,
            progress=(done / total) if total else 0.0,
            total_leaves=total, done_leaves=done,
            deliverables_missing=missing, wbs=wbs_states,
        ))

    current = next((m.id for m in milestone_states if m.declared_status is RoadmapItemStatus.IN_PROGRESS), None)
    return RoadmapState(
        generated_at=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        milestones=milestone_states,
        current_milestone_id=current,
        exempt_tasks=exempt_tasks,
        issues=issues,
    )


# --- Task-creation gate (스펙 §6, M-004) --------------------------------------


def evaluate_wbs_gate(
    workspace_root: Path,
    *,
    wbs: str | None,
    exempt_reason: str | None = None,
) -> WbsGateVerdict:
    """task 생성 게이트의 **단일 판정 함수** — CLI(backlog-update)와 MCP
    (create_backlog_entry)가 모두 이 함수를 부른다 (판정이 복제된 곳에 새 분류를
    넣지 않는다, 57차 규칙).

    - roadmap 부재 → `not_applicable` (기존 프로젝트 동작 그대로, additive).
    - 우회는 침묵이 아니라 선언이다: `wbs=exempt` 는 사유가 필수이고, 그 선언은
      frontmatter 에 남아 생성물이 센다.
    - SDLC 순서 게이트의 병행 허용은 코드가 아니라 **로드맵의 `parallel_allowed`
      선언**이 결정한다. 선언은 어느 쪽 마일스톤에 적어도 유효하다 (대칭) —
      "누가 적었나" 로 갈리면 선언 위치가 곧 함정이 된다.
    """
    if not roadmap_exists(workspace_root):
        return WbsGateVerdict(allowed=True, code="not_applicable", detail="roadmap 부재 — 게이트 해당 없음")
    if roadmap_is_draft(workspace_root):
        return WbsGateVerdict(
            allowed=True, code="draft_roadmap",
            detail="로드맵이 draft(소유자 미확정 초안)라 게이트가 아직 서지 않는다 — "
                   "index.md 상태를 active 로 바꾸고 현재 마일스톤을 선언하면 발동한다.",
        )
    roadmap, _ = load_roadmap(workspace_root)
    if roadmap is None or not roadmap.milestones:
        return WbsGateVerdict(allowed=True, code="not_applicable", detail="roadmap 을 읽지 못했다 — 게이트 해당 없음")

    if not wbs:
        return WbsGateVerdict(
            allowed=False, code="wbs_required",
            detail="roadmap 이 있는 프로젝트의 task 생성은 --wbs <M-NNN/WBS-N.N> 가 필수다. "
                   "로드맵 밖 작업은 --wbs exempt --wbs-exempt-reason <사유> 로 선언한다 (스펙 §6-1).",
        )
    if wbs == WBS_EXEMPT_VALUE:
        if not (exempt_reason or "").strip():
            return WbsGateVerdict(
                allowed=False, code="exempt_reason_required",
                detail="--wbs exempt 는 --wbs-exempt-reason <사유> 가 필수다 — 우회는 침묵이 아니라 선언이다.",
            )
        return WbsGateVerdict(allowed=True, code="exempt_declared", detail=f"게이트 예외 선언: {exempt_reason}")

    ref_match = _WBS_REF_RE.match(wbs)
    if not ref_match:
        return WbsGateVerdict(
            allowed=False, code="wbs_ref_format",
            detail=f"wbs 참조 형식 위반: {wbs!r} — 'M-NNN/WBS-N.N' 형태여야 한다.",
        )
    milestone_id = ref_match.group(1)
    leaf_refs, non_leaf_refs = collect_wbs_refs(roadmap)
    if wbs in non_leaf_refs:
        return WbsGateVerdict(
            allowed=False, code="wbs_not_leaf", milestone_id=milestone_id,
            detail=f"{wbs} 는 leaf 가 아니다 — task 는 leaf 에만 연결한다 (스펙 §3.2).",
        )
    if wbs not in leaf_refs:
        return WbsGateVerdict(
            allowed=False, code="wbs_dangling", milestone_id=milestone_id,
            detail=f"{wbs} 가 로드맵에 없다 — 로드맵에 leaf 를 먼저 선언한다.",
        )

    target = next((m for m in roadmap.milestones if m.id == milestone_id), None)
    assert target is not None  # leaf_refs 에 있으면 마일스톤도 있다
    if target.status is RoadmapItemStatus.DONE:
        return WbsGateVerdict(
            allowed=False, code="milestone_done", milestone_id=milestone_id,
            detail=f"{milestone_id} 는 done 선언이다 — 일이 남았다면 마일스톤 status 를 먼저 되돌린다 (스펙 §6-3).",
        )
    for earlier in roadmap.milestones:
        if earlier.order >= target.order or earlier.status is RoadmapItemStatus.DONE:
            continue
        if earlier.id in target.parallel_allowed or target.id in earlier.parallel_allowed:
            continue
        return WbsGateVerdict(
            allowed=False, code="sdlc_order", milestone_id=milestone_id,
            detail=f"앞선 마일스톤 {earlier.id}({earlier.status.value})가 끝나지 않았다 — "
                   f"먼저 닫거나, 병행이 맞다면 로드맵의 parallel_allowed 에 선언한다 (스펙 §6-2).",
        )
    return WbsGateVerdict(allowed=True, code="linked", milestone_id=milestone_id, detail=f"{wbs} 에 연결")


# --- Generator ----------------------------------------------------------------


def build_roadmap_state(workspace_root: Path) -> RoadmapState | None:
    """SSOT 전체에서 RoadmapState 를 계산한다 (쓰기 없음). roadmap 부재 → None."""
    roadmap, issues = load_roadmap(workspace_root)
    if roadmap is None:
        return None
    links = collect_task_wbs_links(workspace_root)
    return derive_state(roadmap, links, workspace_root, base_issues=issues)


def generate_roadmap_state(workspace_root: Path) -> RoadmapState | None:
    """RoadmapState 를 계산해 `roadmap_state.json` 으로 원자 기록한다.

    `wk refresh-state` 통합(M-003)의 진입점 — 별도 명령을 만들지 않는다
    (진입점이 둘로 갈리면 `--help` 도 갈린다).
    """
    built = build_roadmap_state(workspace_root)
    if built is None:
        return None
    atomic_write_json(state_path(workspace_root), built.model_dump(mode="json"))
    return built


#: session-start 권고에서 "산출물부터" 를 말하는 SDLC 단계 (스펙 §9 — 문서가
#: deliverable 인 단계들. implementation 부터는 WBS 후보 안내만 한다).
_DOC_PHASES: Final[frozenset[SdlcPhase]] = frozenset(
    {SdlcPhase.CONCEPT, SdlcPhase.REQUIREMENTS, SdlcPhase.DESIGN}
)


def _walk_leaf_states(nodes: list[WbsNodeState]) -> list[WbsNodeState]:
    out: list[WbsNodeState] = []
    for node in nodes:
        if node.children:
            out.extend(_walk_leaf_states(node.children))
        else:
            out.append(node)
    return out


def build_session_roadmap_context(workspace_root: Path) -> SessionStartRoadmapContext:
    """session-start 가 싣는 로드맵 요약 (M-003 배선의 정본 — 스펙 §9).

    roadmap 부재는 present=False 로 말한다 — 조용한 생략이 아니라 관측 결과다.
    """
    built = build_roadmap_state(workspace_root)
    if built is None:
        return SessionStartRoadmapContext(present=False)

    current = next(
        (m for m in built.milestones if m.id == built.current_milestone_id), None
    )
    if current is None:
        first_planned = next(
            (m for m in built.milestones if m.declared_status is RoadmapItemStatus.PLANNED), None
        )
        recommendation = (
            f"진행 중 마일스톤이 없다 — 다음 후보는 {first_planned.id}({first_planned.sdlc_phase.value}) "
            f"'{first_planned.title}'. 시작하려면 마일스톤 status 를 in_progress 로 선언하고 task 를 연다."
            if first_planned is not None
            else "모든 마일스톤이 닫혔다 — 로드맵에 다음 마일스톤을 선언한다."
        )
        return SessionStartRoadmapContext(
            present=True,
            issues_count=len(built.issues),
            recommendation=recommendation,
        )

    candidates = [
        f"{leaf.id} {leaf.title} ({leaf.derived_status.value})"
        for leaf in _walk_leaf_states(current.wbs)
        if leaf.derived_status is not RoadmapItemStatus.DONE
    ]
    if current.sdlc_phase in _DOC_PHASES and current.deliverables_missing:
        recommendation = (
            f"{current.id} 는 {current.sdlc_phase.value} 단계다 — 단계 산출물부터 채운다: "
            f"{current.deliverables_missing}"
        )
    elif candidates:
        recommendation = f"{current.id} 의 다음 WBS 후보: {candidates[0]}"
    else:
        recommendation = (
            f"{current.id} 의 WBS 가 전부 done 이다 — 산출물 확인 후 마일스톤을 닫는다"
        )
    return SessionStartRoadmapContext(
        present=True,
        current_milestone_id=current.id,
        current_sdlc_phase=current.sdlc_phase.value,
        declared_status=current.declared_status.value,
        progress=current.progress,
        done_leaves=current.done_leaves,
        total_leaves=current.total_leaves,
        next_wbs_candidates=candidates,
        deliverables_missing=current.deliverables_missing,
        issues_count=len(built.issues),
        recommendation=recommendation,
    )


def state_matches_regeneration(workspace_root: Path) -> tuple[bool, str]:
    """저장된 roadmap_state.json 이 재생성 결과와 같은가 (generated_at 제외).

    (일치 여부, 사유) — check_roadmap_state_generated 의 판정 정본.
    """
    import json

    built = build_roadmap_state(workspace_root)
    saved_path = state_path(workspace_root)
    if built is None:
        return (not saved_path.exists(), "roadmap 부재인데 state 파일이 남아 있다" if saved_path.exists() else "roadmap 부재 — 해당 없음")
    if not saved_path.exists():
        return False, "roadmap 은 있는데 roadmap_state.json 이 없다 — 재생성 필요"
    try:
        saved_raw = json.loads(saved_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return False, f"저장본 JSON 파싱 실패: {exc}"
    built_raw = built.model_dump(mode="json")
    for volatile in ("generated_at",):
        saved_raw.pop(volatile, None)
        built_raw.pop(volatile, None)
    if saved_raw != built_raw:
        return False, "저장본이 재생성 결과와 다르다 — 손편집이거나 SSOT 변경 후 미재생성"
    return True, "일치"
