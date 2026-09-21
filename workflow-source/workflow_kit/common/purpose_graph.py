"""Graph insights helper (v0.11.1 R-A follow-up cycle 4).

R-A follow-up 의 *cycle 4* (v0.11.1):
- PURPOSE.md 의 4-element (Goals / Key Questions / Research Scope / Evolving Thesis)
  ↔ 실제 deliverable (state.json recent_done_items + acceptance test) 의 매핑 분석
- 3 정형화:
  - Goal coverage (covered / partial / uncovered)
  - Surprising 발견 (scope creep 감지, advisory)
  - Gaps 식별 (uncovered goal priority 1-3)
- Health score (0-100, 4 tier: excellent ≥80 / good ≥60 / fair ≥40 / poor <40)

**이 지표가 실제로 재는 것은 어휘 겹침이지 프로젝트의 건강도가 아니다.**
Goals 는 지향 문장이고 deliverable 은 작업 제목이라, 결함 수리 위주의 저장소에서는
둘이 낱말을 공유할 이유가 없다. 이 저장소 실측(TASK-2026-09-07-main-010): goal 4개
전부 겹침 공집합이고, 한국어 조사를 제거해도 부분문자열까지 완화해도 회수되는 것은
`ai` 와 `처럼` 둘뿐이다. **토크나이저를 개선해도 열리지 않는 자리다** — 임계값만 옮긴다.
따라서 낮은 점수는 "프로젝트가 나쁘다" 가 아니라 **"어휘가 겹치지 않는다"** 로 읽는다.
이 산출물은 advisory 이고 어떤 skill·harness 지시문도 이것을 소비하지 않는다
(참조 0건, state.json 에도 저장되지 않는다) — 자동 판정의 근거로 쓰지 않는다.

이 모듈은 llm_wiki README §"Purpose.md — The Wiki's Soul" 의
*LLM can suggest updates based on usage patterns* 패턴을
standard_ai_workflow 의 PURPOSE ↔ deliverable 정합 자동 verify 로 정형화.

v0.9.4 builder._parse_purpose_summary + v0.11.0 cycle 3 purpose_ingest 와 정합:
- 동일 frontmatter / §1 Goals / §3 Research Scope 구조 가정
- recent_done_items 는 **두 형식**을 받는다: 현재 표준의 `TASK-…-NNN — 설명` 과
  v0.9.4 시절 legacy 인 `vX.Y.Z (hash): 설명`. 한때 이 모듈은 legacy 만 알아서
  살아 있는 항목이 전부 `version="unknown"` 으로 떨어졌고, 그 사실을 아무도
  보지 못한 이유는 이 경로를 재는 유일한 fixture 가 legacy 형식을 쓰고 있어서였다.
"""
from __future__ import annotations

import json
import re
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, TYPE_CHECKING

from workflow_kit.common.paths import memory_active_dir, state_path_for_workspace
from workflow_kit.common.project_docs import TASK_ID_PATTERN

if TYPE_CHECKING:  # 순환 import 회피 — 런타임 해석은 run_graph_insights 안에서 늦게 한다.
    from workflow_kit.common.schemas.roadmap import TaskGoalResolution

# PURPOSE.md candidate locations (mirrors purpose_context / purpose_ingest).
def _candidate_purpose_paths(workspace_root: Path) -> list[Path]:
    return [
        memory_active_dir(workspace_root) / "PURPOSE.md",
        memory_active_dir(workspace_root.parent) / "PURPOSE.md",
        workspace_root / "PURPOSE.md",
    ]


def find_purpose_path(workspace_root: Path) -> Path | None:
    """후보 위치 중 실재하는 PURPOSE.md. 없으면 None."""
    for candidate in _candidate_purpose_paths(workspace_root):
        if candidate.exists():
            return candidate
    return None


def _candidate_state_paths(workspace_root: Path) -> list[Path]:
    # v1.0.0 branch-scoped: state.json 은 `active/<branch>/` 로 이동했다.
    # state_path_for_workspace 가 branch-scoped → legacy 순으로 해석해 주므로 우선 사용하고,
    # 나머지는 하위호환 후보로 남긴다.
    from workflow_kit.common.paths import state_path_for_workspace, memory_active_dir

    return [
        state_path_for_workspace(workspace_root),
        memory_active_dir(workspace_root) / "state.json",
        workspace_root / "state.json",
    ]


# PURPOSE.md §1 Goals pattern.
_GOAL_PATTERN = re.compile(r"^[-*]\s+\*\*(G\d+)\*\*\s*:\s*(.+)$", re.MULTILINE)
# recent_done_items entry pattern (legacy): "vX.Y.Z (commit): description"
_RECENT_DONE_PATTERN = re.compile(r"^v(\d+\.\d+(?:\.\d+)?)\s+\(([0-9a-f]{7,8})\)\s*:\s*(.+)$")

# recent_done_items entry pattern (current): "TASK-YYYY-MM-DD-<slug>-NNN — description".
# 표준이 recently-done 항목을 `TASK-` 로 시작하도록 바꾼 뒤 살아 있는 생성기가 내는
# 형식이 이것이다 (`CLAUDE.md` §Memory Update Paths). 문법은 손으로 옮겨 적지 않고
# `project_docs.TASK_ID_PATTERN` 정본에서 파생한다 — 복제하면 갈라진다.
_TASK_DONE_PATTERN = re.compile(
    rf"^({TASK_ID_PATTERN})\s*(?:[—–-]{{1,2}})\s*(.+)$"
)


# ---------------------------------------------------------------------------
# Dataclass 6
# ---------------------------------------------------------------------------


@dataclass
class GoalKeyword:
    """PURPOSE.md §1 Goals 의 G1+ identifier + 본문 keyword."""

    gid: str  # "G1", "G2", ...
    text: str  # "G1: foo bar baz"
    keywords: list[str]  # [foo, bar, baz] (lowercase, stop word 제거)


@dataclass
class RecentDoneItem:
    """state.json recent_done_items 의 단일 entry."""

    version: str  # "v0.11.0"
    commit_hash: str  # "f71dde8"
    summary: str  # full entry string
    keywords: list[str]  # [two-step, cot, ingest, ...] (lowercase)


#: coverage 를 무엇으로 쟀는가 (provenance). 0.0 이 '안 닿았다' 인지 '못 쟀다'
#: 인지를 값만 보고는 가를 수 없어서 함께 내보낸다.
COVERAGE_MODE_DECLARED = "declared"
COVERAGE_MODE_UNDECLARED = "undeclared"
COVERAGE_MODE_NONE = "none"

#: 선언이 없어 coverage 축을 못 잰 상태. `poor` 와 섞으면 실패가 나쁨으로 읽힌다.
TIER_UNMEASURED = "unmeasured"


@dataclass
class GoalCoverageResult:
    """각 Goal 의 deliverable 매핑 coverage.

    `mode` 가 `declared` 일 때만 수치가 뜻을 가진다. `undeclared` 는 **못 쟀다** 는
    뜻이고, 그때의 0.0 을 '안 닿았다' 로 읽으면 안 된다.
    """

    total_goals: int
    covered_count: int
    partial_count: int
    uncovered_count: int
    coverage_pct: float  # 0.0 - 100.0
    covered: list[str] = field(default_factory=list)  # ["G1", ...]
    partial: list[str] = field(default_factory=list)
    uncovered: list[str] = field(default_factory=list)
    mode: str = COVERAGE_MODE_NONE
    #: 왜 못 쟀는가 / 무엇을 채우면 닿는가 — 조용한 0 을 만들지 않는다.
    provenance: list[str] = field(default_factory=list)


@dataclass
class SurprisingResult:
    """Goals 매핑 0 + scope_excluded 매칭 ❌ deliverable."""

    surprising: list[str]  # deliverable summary list
    is_scope_creep: list[bool]  # parallel to surprising
    scope_creep_warnings: list[str]
    mode: str = COVERAGE_MODE_NONE
    # 분모 — 훑은 deliverable **전체** 수. 호출자가 len(surprising) 로 비율을 내면
    # 분모가 분자와 같아져 늘 1.0 이 된다. 정본이 함께 돌려주는 이유다.
    total_items: int = 0


@dataclass
class GapResult:
    """Goals 중 deliverable 매핑 0 인 goal 식별."""

    gaps: list[str]  # ["G3", ...]
    priorities: list[int]  # parallel to gaps (1=highest)
    descriptions: list[str]  # parallel to gaps


@dataclass
class HealthScore:
    """종합 점수 + tier + breakdown."""

    score: int  # 0 - 100
    tier: str  # excellent / good / fair / poor
    breakdown: dict[str, int] = field(default_factory=dict)


@dataclass
class GraphInsightsResult:
    """unified entry 산출물."""

    goal_keywords: list[GoalKeyword]
    recent_items: list[RecentDoneItem]
    coverage: GoalCoverageResult | None  # 부재 시 None
    surprising: SurprisingResult | None
    gaps: GapResult | None
    health: HealthScore | None
    overall_warnings: list[str]


# ---------------------------------------------------------------------------
# stop words (영어 + 한국어 조사 일부) — keyword 추출 시 제거
# ---------------------------------------------------------------------------


_STOP_WORDS = frozenset([
    # english
    "the", "a", "an", "and", "or", "but", "is", "are", "was", "were",
    "in", "on", "at", "to", "for", "of", "with", "by", "from", "as",
    "this", "that", "these", "those", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "must", "can",
    # 한국어 일부 (조사)
    "이", "그", "저", "의", "를", "을", "에", "에서", "로", "으로", "와", "과",
    "은", "는", "이다", "있다", "하다",
])


def _tokenize(text: str) -> list[str]:
    """text 를 lowercase + stop word 제거 + 길이 2+ 만 token 화."""
    # 한글 / 영문 / 숫자 분리
    text = text.lower()
    # 한글 / 영문 / 숫자 token split (공백 + 특수문자)
    tokens = re.findall(r"[a-z0-9]+|[\uac00-\ud7af]+", text)
    return [t for t in tokens if len(t) >= 2 and t not in _STOP_WORDS]


# ---------------------------------------------------------------------------
# step 1: PURPOSE.md Goals keyword 추출
# ---------------------------------------------------------------------------


def extract_goal_keywords(purpose_path: Path | None) -> list[GoalKeyword]:
    """PURPOSE.md §1 Goals 의 G1+ identifier + 본문 keyword 추출.

    부재 / corrupted 모두 graceful skip → empty list.
    """
    if purpose_path is None or not purpose_path.exists():
        return []

    try:
        text = purpose_path.read_text(encoding="utf-8")
    except OSError:
        return []

    # §1 Goals section 추출 (간단히 G1+ pattern 직접 매칭)
    matches = _GOAL_PATTERN.findall(text)
    if not matches:
        return []

    result: list[GoalKeyword] = []
    for gid, body in matches:
        text_clean = body.strip()
        keywords = _tokenize(text_clean)
        result.append(GoalKeyword(gid=gid, text=f"{gid}: {text_clean}", keywords=keywords))
    return result


def extract_goal_ids(purpose_path: Path | None) -> list[str]:
    """PURPOSE.md §1 Goals 의 id 만 (G1, G2, ...) — 선언 사슬의 끝 칸.

    `state/roadmap.py` 의 goal 링크 검증이 이것을 부른다. §1 파싱 규약(`_GOAL_PATTERN`)
    의 정본이 여기 하나뿐이도록 **사본을 만들지 않고 이 함수를 내보낸다**.
    """
    return [g.gid for g in extract_goal_keywords(purpose_path)]


# ---------------------------------------------------------------------------
# step 2: state.json recent_done_items 파싱
# ---------------------------------------------------------------------------


def parse_recent_done_items(state_path: Path | None) -> list[RecentDoneItem]:
    """state.json 의 `session.recent_done_items` 파싱.

    두 형식을 받는다. 현재 표준은 `TASK-…-NNN — 설명` 이고, `vX.Y.Z (hash): 설명`
    은 v0.9.4 시절의 legacy 다. 둘 다 아니면 줄 전체를 본문으로 본다.

    부재 / json 파싱 실패 / corrupted 모두 graceful skip → empty list.
    """
    if state_path is None or not state_path.exists():
        return []

    try:
        data = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []

    if not isinstance(data, dict):
        return []

    session = data.get("session", {})
    items = session.get("recent_done_items", [])
    if not isinstance(items, list):
        return []

    result: list[RecentDoneItem] = []
    for entry in items:
        if not isinstance(entry, str):
            continue
        stripped = entry.strip()
        m = _RECENT_DONE_PATTERN.match(stripped)
        task_m = None if m else _TASK_DONE_PATTERN.match(stripped)
        if m:
            version, commit_hash, summary = m.group(1), m.group(2), m.group(3)
            full = f"v{version} ({commit_hash}): {summary}"
            keywords = _tokenize(summary)
            result.append(RecentDoneItem(
                version=f"v{version}",
                commit_hash=commit_hash,
                summary=full,
                keywords=keywords,
            ))
        elif task_m:
            # ID 는 **본문에서 뺀다**. 그러지 않으면 모든 항목이 공유하는
            # `task` / `2026` / `09` / `main` / `008` 이 키워드 집합에 들어가
            # 어휘 겹침을 재는 자리에 순수한 잡음을 섞는다.
            task_id, summary = task_m.group(1), task_m.group(2)
            result.append(RecentDoneItem(
                version=task_id,
                commit_hash="",
                summary=stripped,
                keywords=_tokenize(summary),
            ))
        else:
            # 형식 불일치 — keyword 추출만 시도
            keywords = _tokenize(entry)
            result.append(RecentDoneItem(
                version="unknown",
                commit_hash="",
                summary=entry,
                keywords=keywords,
            ))
    return result


# ---------------------------------------------------------------------------
# step 3: Goal coverage
# ---------------------------------------------------------------------------


def compute_goal_coverage(
    goal_keywords: list[GoalKeyword],
    recent_items: list[RecentDoneItem],
) -> GoalCoverageResult:
    """각 Goal ↔ recent_done_items 의 keyword 매칭률 (Jaccard similarity).

    - covered (≥1 keyword 매칭)
    - partial (1+ keyword 매칭이지만 overlap < 50%)
    - uncovered (0 keyword 매칭)

    .. deprecated::
        이 판정은 실측에서 상수 0 이었다 — 사유는 `compute_health_score` docstring
        의 '왜 어휘를 버렸는가'. 남겨 두는 것은 G4 약속(1 release 경고 → 1 release
        제거) 때문이고, `run_graph_insights` 는 더 이상 부르지 않는다.
    """
    warnings.warn(
        "compute_goal_coverage 는 어휘 겹침으로 coverage 를 재던 옛 경로다 — "
        "선언 기반 compute_goal_coverage_declared 를 쓴다. "
        "(deprecated since v1.10.0, removal in v1.11.0; TASK-2026-09-21-main-001)",
        DeprecationWarning,
        stacklevel=2,
    )
    if not goal_keywords:
        return GoalCoverageResult(
            total_goals=0,
            covered_count=0,
            partial_count=0,
            uncovered_count=0,
            coverage_pct=0.0,
        )

    if not recent_items:
        # recent done 부재 시 전부 uncovered
        return GoalCoverageResult(
            total_goals=len(goal_keywords),
            covered_count=0,
            partial_count=0,
            uncovered_count=len(goal_keywords),
            coverage_pct=0.0,
            uncovered=[g.gid for g in goal_keywords],
        )

    # recent done 의 모든 keyword set
    recent_kw_set: set[str] = set()
    for item in recent_items:
        recent_kw_set.update(item.keywords)

    covered: list[str] = []
    partial: list[str] = []
    uncovered: list[str] = []
    for g in goal_keywords:
        g_set = set(g.keywords)
        if not g_set:
            uncovered.append(g.gid)
            continue
        overlap = g_set & recent_kw_set
        if not overlap:
            uncovered.append(g.gid)
        else:
            ratio = len(overlap) / len(g_set)
            if ratio >= 0.5:
                covered.append(g.gid)
            else:
                partial.append(g.gid)

    total = len(goal_keywords)
    covered_count = len(covered)
    partial_count = len(partial)
    uncovered_count = len(uncovered)
    coverage_pct = round(100.0 * covered_count / total, 2) if total > 0 else 0.0

    return GoalCoverageResult(
        total_goals=total,
        covered_count=covered_count,
        partial_count=partial_count,
        uncovered_count=uncovered_count,
        coverage_pct=coverage_pct,
        covered=covered,
        partial=partial,
        uncovered=uncovered,
    )


# ---------------------------------------------------------------------------
# step 3b: 선언 기반 coverage (정본 경로 — TASK-2026-09-21-main-001)
# ---------------------------------------------------------------------------

#: 선언 사슬이 끊긴 자리의 어휘. 한 덩어리로 뭉치면 무엇을 고쳐야 하는지 사라진다.
UNRESOLVED_UNLINKED = "wbs_미선언"
UNRESOLVED_MILESTONE_NO_GOALS = "마일스톤_goals_미선언"
UNRESOLVED_DANGLING = "wbs_링크_끊김"


def _classify_declared(
    recent_items: list[RecentDoneItem],
    resolution: "TaskGoalResolution",
) -> tuple[dict[str, list[str]], dict[str, str]]:
    """recent item → (닿은 goal 목록) / (못 닿은 사유).

    둘 중 하나에만 들어간다. `exempt` 는 **사유가 아니라 분류**다 — 사람이
    '로드맵 밖' 이라고 선언한 것이라서 미분류가 아니다.
    """
    reached: dict[str, list[str]] = {}
    unresolved: dict[str, str] = {}
    exempt = set(resolution.exempt_tasks)
    unlinked = set(resolution.unlinked_tasks)
    dangling = set(resolution.dangling_tasks)
    for item in recent_items:
        task_id = item.version
        goals = resolution.goals_by_task.get(task_id)
        if goals:
            reached[task_id] = goals
        elif task_id in exempt:
            reached[task_id] = []
        elif task_id in unlinked:
            unresolved[task_id] = UNRESOLVED_UNLINKED
        elif task_id in dangling:
            unresolved[task_id] = UNRESOLVED_DANGLING
        else:
            # task 파일을 못 찾았거나(브랜치 아카이브 등) 마일스톤이 goals 를
            # 선언하지 않았다. 후자가 압도적이므로 그쪽 어휘를 쓰되, 어느 쪽이든
            # '선언을 채우면 닿는다' 는 같은 처방이다.
            unresolved[task_id] = UNRESOLVED_MILESTONE_NO_GOALS
    return reached, unresolved


def compute_goal_coverage_declared(
    goal_ids: list[str],
    recent_items: list[RecentDoneItem],
    resolution: "TaskGoalResolution",
) -> GoalCoverageResult:
    """`task.wbs → milestone.goals → PURPOSE §1` 선언 사슬로 goal coverage 를 낸다.

    어휘 겹침을 재지 않는다. 옛 식이 무엇을 재고 있었는지는
    `compute_health_score` docstring 이 기록한다.

    `partial` 은 **없다**. 선언은 닿거나 안 닿거나 둘 중 하나이고, 중간 등급을
    만들면 그 등급을 정하는 임계가 다시 추측이 된다.
    """
    total = len(goal_ids)
    if total == 0:
        return GoalCoverageResult(
            total_goals=0, covered_count=0, partial_count=0, uncovered_count=0,
            coverage_pct=0.0, mode=COVERAGE_MODE_UNDECLARED,
            provenance=["PURPOSE.md §1 Goals 를 읽을 수 없다 — coverage 미측정"],
        )

    reached, unresolved = _classify_declared(recent_items, resolution)
    touched: set[str] = set()
    for goals in reached.values():
        touched.update(goals)

    covered = [g for g in goal_ids if g in touched]
    uncovered = [g for g in goal_ids if g not in touched]

    provenance: list[str] = []
    if resolution.milestones_without_goals:
        provenance.append(
            "goals 미선언 마일스톤: " + ", ".join(resolution.milestones_without_goals)
        )
    if unresolved:
        by_reason: dict[str, int] = {}
        for reason in unresolved.values():
            by_reason[reason] = by_reason.get(reason, 0) + 1
        provenance.append(
            "선언 사슬이 끊긴 최근 완료 항목 "
            + f"{len(unresolved)}/{len(recent_items)}건 — "
            + ", ".join(f"{k} {v}건" for k, v in sorted(by_reason.items()))
        )

    return GoalCoverageResult(
        total_goals=total,
        covered_count=len(covered),
        partial_count=0,
        uncovered_count=len(uncovered),
        coverage_pct=round(100.0 * len(covered) / total, 2),
        covered=covered,
        partial=[],
        uncovered=uncovered,
        mode=COVERAGE_MODE_DECLARED,
        provenance=provenance,
    )


def find_surprising_declared(
    recent_items: list[RecentDoneItem],
    resolution: "TaskGoalResolution",
) -> SurprisingResult:
    """미분류 = **선언 사슬이 끊긴** 완료 항목 (어휘 겹침이 아니다).

    옛 판정은 '제목이 §3 제외 목록과 낱말을 공유하는가' 였고, 실측에서 통과한
    두 건의 근거가 전부 동음이의였다 (`runtime` / `흡수`, TASK-2026-09-21-main-001).
    이제는 사람이 `wbs:` 를 적었는지를 본다 — 적었으면 분류된 것이고,
    `exempt` 도 분류다.
    """
    reached, unresolved = _classify_declared(recent_items, resolution)
    surprising: list[str] = []
    is_scope_creep: list[bool] = []
    warnings: list[str] = []
    for item in recent_items:
        reason = unresolved.get(item.version)
        if reason is None:
            continue
        surprising.append(item.summary)
        is_scope_creep.append(True)
        warnings.append(
            f"{UNCLASSIFIED_WARNING_PREFIX} '{item.summary[:80]}...' — {reason}"
        )
    return SurprisingResult(
        surprising=surprising,
        is_scope_creep=is_scope_creep,
        scope_creep_warnings=warnings,
        mode=COVERAGE_MODE_DECLARED,
        total_items=len(recent_items),
    )


# ---------------------------------------------------------------------------
# step 4: Surprising 발견 (미분류 deliverable)
# ---------------------------------------------------------------------------

UNCLASSIFIED_WARNING_PREFIX = "미분류 산출물:"
"""이 모듈이 내는 경고의 접두사 (정본).

`purpose_context.check_scope_creep` 과 **접두사를 공유하면 안 된다**. 두 술어가
정반대이기 때문이다 (TASK-2026-09-07-main-010 실측):

- `purpose_context`: §3 제외 영역에 **걸리면** scope creep — 하려던 그 의미다.
- 이 모듈: goal 에도 제외 영역에도 **안 걸리면** — 즉 *분류할 수 없다*.

둘 다 `"scope creep 의심:"` 으로 시작하던 동안, 두 경고는 `scope_creep_warnings`
라는 **같은 이름의 두 필드**(top-level / `graph_insights.`)로 나가면서 읽는 쪽이
어느 규칙이 울렸는지 구분할 수 없었다. 필드 이름은 공개 schema 라 여기서 바꾸지
않는다 (G3 SemVer 보증 — 개명은 deprecation 사이클을 탄다). 대신 **문구**로 가른다.
`check_graph_insights_health_monotonic.py` 가 두 접두사의 분리를 고정한다.
"""


def find_surprising_deliverables(
    goal_keywords: list[GoalKeyword],
    recent_items: list[RecentDoneItem],
    scope_excluded: list[str],
) -> SurprisingResult:
    """Goals 매핑 0 + scope_excluded 매칭 ❌ deliverable.

    - Goals 매핑 0: deliverable 의 keywords 가 goal_keywords 어느 것의 set 과도 매칭 안 함
    - scope_excluded 매칭 ❌: deliverable keywords 가 scope_excluded 항목과도 매칭 안 함
    - → surprising 으로 분류 (scope creep 가능성, advisory)

    .. deprecated::
        실측에서 이 판정을 통과한 근거가 전부 동음이의였다 (`runtime` / `흡수`).
        `find_surprising_declared` 로 대체됐다.
    """
    warnings.warn(
        "find_surprising_deliverables 는 어휘 겹침으로 미분류를 재던 옛 경로다 — "
        "선언 기반 find_surprising_declared 를 쓴다. "
        "(deprecated since v1.10.0, removal in v1.11.0; TASK-2026-09-21-main-001)",
        DeprecationWarning,
        stacklevel=2,
    )
    goal_kw_sets = [set(g.keywords) for g in goal_keywords]
    excluded_kw_set: set[str] = set()
    for scope_item in scope_excluded:
        excluded_kw_set.update(_tokenize(scope_item))

    surprising: list[str] = []
    is_scope_creep: list[bool] = []
    scope_creep_warnings: list[str] = []

    for item in recent_items:
        item_kw_set = set(item.keywords)
        # Goals 매핑 검사
        matches_any_goal = any(item_kw_set & g_set for g_set in goal_kw_sets)
        if matches_any_goal:
            continue
        # scope_excluded 매칭 검사
        matches_excluded = bool(item_kw_set & excluded_kw_set)

        surprising.append(item.summary)
        if not matches_excluded:
            is_scope_creep.append(True)
            scope_creep_warnings.append(
                UNCLASSIFIED_WARNING_PREFIX
                + f" '{item.summary[:80]}...' — Goals 어휘 겹침 0 + §3 제외 영역 겹침 0"
            )
        else:
            is_scope_creep.append(False)

    return SurprisingResult(
        surprising=surprising,
        is_scope_creep=is_scope_creep,
        scope_creep_warnings=scope_creep_warnings,
        total_items=len(recent_items),
    )


# ---------------------------------------------------------------------------
# step 5: Gaps 식별
# ---------------------------------------------------------------------------


def find_gaps(
    goal_keywords: list[GoalKeyword],
    recent_items: list[RecentDoneItem],
) -> GapResult:
    """Goals 중 recent_done 매핑 0 인 goal 식별.

    priority 결정:
    - 1: §1 Goals 의 첫 번째 goal (highest)
    - 2: 두 번째 goal
    - 3+: 이후 goal
    """
    if not goal_keywords:
        return GapResult(gaps=[], priorities=[], descriptions=[])

    coverage = compute_goal_coverage(goal_keywords, recent_items)
    gaps = coverage.uncovered
    priorities: list[int] = []
    descriptions: list[str] = []
    for i, gid in enumerate(gaps):
        priorities.append(i + 1)  # 1 = highest
        # 매칭되는 goal text
        g_text = next((g.text for g in goal_keywords if g.gid == gid), gid)
        descriptions.append(g_text)

    return GapResult(gaps=gaps, priorities=priorities, descriptions=descriptions)


# ---------------------------------------------------------------------------
# step 6: Health score
# ---------------------------------------------------------------------------


def compute_health_score(
    coverage: GoalCoverageResult | None,
    surprising: SurprisingResult | None,
    gaps: GapResult | None,
) -> HealthScore:
    """PURPOSE Goals 에 **선언으로 닿은 비율** 점수 (0-100).

    해석은 `docs/` 가 아니라 이 docstring 이 정본이다.

    두 성분 모두 `task.wbs → milestone.goals → PURPOSE §1` 선언 사슬에서 나온다
    (스펙 §7.4). 어휘 겹침은 **더 이상 쓰지 않는다** — 그 이유는 아래 '왜 어휘를
    버렸는가' 에 적었다.

    두 성분의 합이고 **둘 다 비율**이다 (항목 *개수* 가 아니다):

    - coverage 성분 (0-70): `70 * covered/total_goals`
    - classification 성분 (0-30): `30 * (1 - 미분류/전체 deliverable)`

    **왜 어휘를 버렸는가** (TASK-2026-09-21-main-001 실측). 옛 식은 Goal 산문과
    완료 task 제목의 표면 어휘 겹침을 쟀다. 이 저장소 실측에서 4개 goal 전부
    겹침이 **정확히 0** 이었고(0/13 · 0/14 · 0/12 · 0/15), 조사 제거와 CJK
    bigram 두 대안 토크나이저로 다시 재도 최대 0.07 이었으며 그 유일한 겹침은
    기능어 `처럼` 이었다. 원인은 토크나이저도 임계도 아니라 **입력 쌍**이다 —
    Goals 는 전략 산문이고 완료 항목은 결함수리 제목이라 낱말을 공유할 이유가
    구조적으로 없다. 분류 성분도 같은 결함을 공유했다: 미분류를 면한 2건의
    근거가 전부 동음이의(`runtime` / `흡수`)였다. 즉 옛 점수는 coverage 축이
    상수 0 이고 분류 축이 잡음이었다. 어휘를 고치는 대신 **이미 존재하던 선언
    사슬**로 갈아탄 이유다.

    측정이 불가능할 때 만점도 0점도 주지 않는다. goal 선언이 하나도 없으면
    tier 는 `unmeasured` 이고, 그 상태는 '나쁘다' 가 아니라 **'아직 안 쟀다'**
    이다 (`coverage.provenance` 가 무엇을 채우면 닿는지 적는다).

    개수 기반 벌점을 쓰지 않는 이유도 그대로 유효하다 (TASK-2026-09-07-main-010 실측):
    옛 식 `100 - uncovered*15 - scope_creep*10 + min(surprising*5, 25)` 은
    벌점이 항목 수에 비례해 무한히 커지는데 보너스는 25 에서 막혀 있어,
    **완료 항목이 늘수록 점수가 내려갔다** — goal 매칭 0 을 고정하고 재면
    0건 40 → 3건 25 → 10건 -35(0 으로 clamp). 표준이 recently-done 을 10건으로
    상한하므로 활발한 저장소는 영구히 바닥에 눌렸고, 그 0 은 '나쁘다' 가 아니라
    **clamp 자국**이었다. 비율로 바꾸면 매칭된 일을 더 하는 것이 점수를 절대
    내리지 못한다 — `check_graph_insights_health_monotonic.py` 가 그것을 잰다.
    """
    if coverage is None:
        return HealthScore(score=0, tier="poor", breakdown={"missing_coverage": 100})

    if coverage.mode == COVERAGE_MODE_UNDECLARED:
        # 못 쟀다. 0 을 주고 `poor` 라고 부르면 '측정 실패' 가 '나쁨' 으로 읽힌다.
        return HealthScore(
            score=0,
            tier=TIER_UNMEASURED,
            breakdown={"coverage_mode_undeclared": 1},
        )

    total_goals = coverage.total_goals
    if total_goals > 0:
        coverage_component = 70.0 * coverage.covered_count / total_goals
    else:
        coverage_component = 0.0

    # 미분류 = goal 매칭 0 이면서 scope_excluded 에도 안 걸린 deliverable.
    # 분모는 **전체 deliverable 수** 다 — 개수가 아니라 비율이어야 단조성이 선다.
    unclassified = sum(1 for s in surprising.is_scope_creep if s) if surprising else 0
    total_items = surprising.total_items if surprising else 0
    if total_items > 0:
        classification_component = 30.0 * (1.0 - unclassified / total_items)
    else:
        # 잴 deliverable 이 없다 = 잘못 분류된 것도 없다. 통과가 아니라 **해당 없음**이라
        # 만점을 주지 않고 성분을 0 으로 둔다 (없음을 좋음으로 세지 않는다).
        classification_component = 0.0

    score = int(round(coverage_component + classification_component))
    score = max(0, min(100, score))

    if score >= 80:
        tier = "excellent"
    elif score >= 60:
        tier = "good"
    elif score >= 40:
        tier = "fair"
    else:
        tier = "poor"

    breakdown = {
        "coverage_component": int(round(coverage_component)),
        "covered_goals": coverage.covered_count,
        "total_goals": total_goals,
        "classification_component": int(round(classification_component)),
        "unclassified_items": unclassified,
        "total_items": total_items,
    }

    return HealthScore(score=score, tier=tier, breakdown=breakdown)


# ---------------------------------------------------------------------------
# unified entry
# ---------------------------------------------------------------------------

STATE_ABSENT_WARNING = (
    "state.json 부재 / recent_done_items 부재 — coverage/surprising/gaps 분석 limited"
)
"""`state.json` 을 못 찾았을 때의 warning 문구 (정본).

새로 만든 workspace 에서는 **정상**이다 — `seed_workspace_memory` 는 state.json 을
일부러 만들지 않는다 (`check_seed_workspace_memory::test_no_state_json`). 그래서
seed 산출물을 판정하는 검사는 이 한 줄을 허용 목록에 두고 *나머지* warning 이
비었는지를 본다. 문구를 손으로 옮겨 적으면 갈라지므로 여기서 import 한다.
"""


def run_graph_insights(
    purpose_path: Path | None = None,
    workspace_root: Path | None = None,
    state_path: Path | None = None,
    auto_find: bool = True,
    include_surprising: bool = True,
    include_gaps: bool = True,
) -> GraphInsightsResult:
    """unified entry: 5 stage 호출 → GraphInsightsResult.

    Args:
        purpose_path: PURPOSE.md 명시 path.
        workspace_root: workspace root (default: cwd).
        state_path: state.json 명시 path.
        auto_find: purpose_path/state_path 부재 시 자동 탐색.
        include_surprising: surprising analysis 포함 여부.
        include_gaps: gaps analysis 포함 여부.

    Returns:
        GraphInsightsResult
    """
    if workspace_root is None:
        workspace_root = Path.cwd()

    if auto_find:
        if purpose_path is None:
            for candidate in _candidate_purpose_paths(workspace_root):
                if candidate.exists():
                    purpose_path = candidate
                    break
        if state_path is None:
            for candidate in _candidate_state_paths(workspace_root):
                if candidate.exists():
                    state_path = candidate
                    break

    overall_warnings: list[str] = []

    # step 1: Goals keyword
    goals = extract_goal_keywords(purpose_path)
    if not goals:
        overall_warnings.append("PURPOSE.md 부재 / §1 Goals 부재 — coverage/surprising/gaps 분석 limited")

    # step 2: recent done
    items = parse_recent_done_items(state_path)
    if not items:
        overall_warnings.append(STATE_ABSENT_WARNING)

    # step 3: coverage — **선언 사슬**로 잰다 (스펙 §7.4). 어휘 겹침은 쓰지 않는다.
    #
    # `state.roadmap` 을 여기서 늦게 import 하는 이유: 그쪽이 goal id 파싱 정본으로
    # 이 모듈을 되부른다. 최상단에서 부르면 순환이 된다.
    from workflow_kit.common.state.roadmap import resolve_task_goals

    resolution = resolve_task_goals(workspace_root)
    goal_ids = [g.gid for g in goals]

    coverage: GoalCoverageResult | None = None
    if goals and items:
        coverage = compute_goal_coverage_declared(goal_ids, items, resolution)
        if coverage.mode == COVERAGE_MODE_DECLARED and not resolution.declared_goal_ids:
            # 선언이 **하나도** 없다. 이건 '안 닿았다' 가 아니라 '못 쟀다' 다.
            # 0 을 주고 poor 라고 부르면 측정 실패가 나쁨으로 읽힌다.
            coverage.mode = COVERAGE_MODE_UNDECLARED
            coverage.provenance.append(
                "roadmap 부재 또는 goals 선언 0 — 선언 사슬이 없어 coverage 를 못 잰다"
                if not resolution.roadmap_present
                else "마일스톤 goals 선언 0 — 선언을 채우면 coverage 를 잴 수 있다"
            )
        overall_warnings.extend(coverage.provenance)

    # step 4: 미분류 — 선언 사슬이 끊긴 완료 항목
    surprising: SurprisingResult | None = None
    if include_surprising and goals and items:
        surprising = find_surprising_declared(items, resolution)

    # step 5: gaps — coverage 의 uncovered 와 같은 정본에서 나온다
    gaps: GapResult | None = None
    if include_gaps and goals and coverage is not None:
        gaps = GapResult(
            gaps=list(coverage.uncovered),
            priorities=list(range(1, len(coverage.uncovered) + 1)),
            descriptions=[
                next((g.text for g in goals if g.gid == gid), gid)
                for gid in coverage.uncovered
            ],
        )
    elif include_gaps and goals:
        gaps = GapResult(gaps=[g.gid for g in goals], priorities=list(range(1, len(goals) + 1)),
                         descriptions=[g.text for g in goals])

    # step 6: health score
    health = compute_health_score(coverage, surprising, gaps)

    return GraphInsightsResult(
        goal_keywords=goals,
        recent_items=items,
        coverage=coverage,
        surprising=surprising,
        gaps=gaps,
        health=health,
        overall_warnings=overall_warnings,
    )


__all__ = [
    "UNCLASSIFIED_WARNING_PREFIX",
    "GoalKeyword",
    "RecentDoneItem",
    "GoalCoverageResult",
    "SurprisingResult",
    "GapResult",
    "HealthScore",
    "GraphInsightsResult",
    "extract_goal_keywords",
    "parse_recent_done_items",
    "compute_goal_coverage",
    "compute_goal_coverage_declared",
    "extract_goal_ids",
    "find_purpose_path",
    "find_surprising_deliverables",
    "find_surprising_declared",
    "COVERAGE_MODE_DECLARED",
    "COVERAGE_MODE_UNDECLARED",
    "COVERAGE_MODE_NONE",
    "TIER_UNMEASURED",
    "find_gaps",
    "compute_health_score",
    "run_graph_insights",
]
