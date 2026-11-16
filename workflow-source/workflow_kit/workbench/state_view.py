"""진척 값 (워크벤치 스펙 §7) — 진척 화면과 ``api/state`` 가 같이 쓴다.

원천은 생성물(`roadmap_state.json` · 브랜치 `state.json`)과 task 파일뿐이다. 재지 않은 것은 ``None`` 으로
두고 화면이 "미측정" 으로 그린다. 절대 경로 · 호스트 이름 · 사용자 홈 · 환경변수 · 토큰 이름은 싣지 않는다.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import re
import tempfile
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from workflow_kit.common import plan_claims, plan_responses, plan_tasks
from workflow_kit.common.paths import state_path_for_workspace
from workflow_kit.common.project_docs import task_label
from workflow_kit.common.state import roadmap
from workflow_kit.common.workflow_writes import read_task_list_field

SCHEMA = "workbench-state/1"
_TITLE_RE = re.compile(r"^#\s+\S+\s+—\s+(.+)$")


@dataclass(frozen=True)
class Where:
    """요청마다 다시 읽는 위치 — 브랜치가 바뀌면 따라간다 (스펙 §3)."""

    workspace_root: Path
    branch: str
    branch_dir: Path
    #: 프로필을 알면 진척 값을 원천에서 실시간으로 계산한다 (스펙 §7.1 — 모르면 생성물을 읽는다).
    profile_path: Path | None = None

    @property
    def tasks_dir(self) -> Path:
        return self.branch_dir / "backlog" / "tasks"

    @property
    def state_path(self) -> Path:
        return state_path_for_workspace(self.workspace_root, self.branch)

    @property
    def roadmap_path(self) -> Path:
        return roadmap.state_path(self.workspace_root)


# --------------------------------------------------------------------------- 실시간 계산 (§7.1)

_LIVE_LOCK = threading.Lock()
#: (프로필, 브랜치 디렉터리) → (원천 지문, 계산 시각, backlog 생성물 dict, roadmap 생성물 dict | None, 산출물 경로)
#: 브랜치가 키에 든다 — 생성기는 현재 브랜치의 메모리를 고르므로 파일이 그대로여도 브랜치가 바뀌면 다른 값이다.
_LIVE_CACHE: dict[tuple[Path, Path], tuple[tuple[Any, ...], str, dict[str, Any], dict[str, Any] | None,
                                           tuple[Path, ...]]] = {}
#: 실제로 생성기를 부른 횟수 — 검사가 "지문이 같으면 다시 계산하지 않는다" 를 잰다.
LIVE_COMPUTE_COUNT = 0


class LiveRefused(Exception):
    """원천에서 계산할 수 없다(생성기 거절) — 사유가 메시지다. 부르는 쪽이 생성물로 내려가며 사유를 보인다."""


#: 절대 경로 — 맨 앞이거나 공백 · 따옴표 · 괄호 뒤에서 시작하는 `/…` · `X:\…` (상대 경로 `a/b` 의 `/` 는 아니다).
_ABS_PATH_RE = re.compile(r"(?<![\w.~-])(?:[A-Za-z]:)?[\\/](?:[^\s'\"\\/]+[\\/])*[^\s'\",)\]]*")


def scrub_error(message: str, workspace_root: Path) -> str:
    """화면 · api 에 실을 실패 사유 — 작업 공간 경로는 상대로, 나머지 절대 경로는 가린다 (스펙 §7.2: 절대 경로를 싣지 않는다)."""
    for root in {str(workspace_root), str(workspace_root.resolve())}:
        message = message.replace(root + os.sep, "").replace(root, ".")
    return _ABS_PATH_RE.sub("<경로>", message)[:300]


def _stat_entry(path: Path) -> tuple[str, int, int]:
    try:
        st = path.stat()
    except OSError:
        return (str(path), -1, -1)  # 없음도 지문의 한 값이다 — 산출물이 생기면 바뀐다
    return (str(path), st.st_mtime_ns, st.st_size)


def _source_fingerprint(profile: Path, memory_dir: Path, extra: tuple[Path, ...] = ()) -> tuple[Any, ...]:
    """원천의 stat 지문 — 메모리 디렉터리 전체(task · handoff · roadmap · memory index) · 프로필 · 마일스톤 산출물."""
    entries: list[tuple[str, int, int]] = []
    for root, dirs, files in os.walk(memory_dir):
        dirs.sort()
        for name in sorted(files):
            entries.append(_stat_entry(Path(root) / name))
    entries.append(_stat_entry(profile))
    entries.extend(_stat_entry(path) for path in extra)
    return tuple(entries)


def _deliverable_paths(workspace_root: Path) -> tuple[Path, ...]:
    """마일스톤이 선언한 산출물 경로 — roadmap 파생값(`deliverables_missing`)이 이 파일들의 존재에 달려 있다."""
    loaded, _issues = roadmap.load_roadmap(workspace_root)
    if loaded is None:
        return ()
    return tuple(workspace_root / d for m in loaded.milestones for d in m.deliverables)


def live_sources(where: Where) -> tuple[str, dict[str, Any], dict[str, Any] | None] | None:
    """refresh-state 와 **같은 생성기**로 원천에서 계산한 (계산 시각, state, roadmap_state) — 저장소에는 쓰지 않는다.

    프로필을 모르면 ``None``. 생성기가 거절하면 :class:`LiveRefused` — 부르는 쪽이 생성물을 읽고 사유를 보인다.
    roadmap 원천이 없으면 roadmap 값은 ``None`` 이다 (디스크의 낡은 생성물을 실시간으로 보이지 않는다).
    """
    global LIVE_COMPUTE_COUNT
    if where.profile_path is None:
        return None
    from workflow_kit.common.paths import workflow_memory_dir
    from workflow_kit.common.state.cache import refresh_workflow_state_cache

    profile = where.profile_path
    key = (profile, where.branch_dir)
    memory_dir = workflow_memory_dir(profile)
    with _LIVE_LOCK:
        cached = _LIVE_CACHE.get(key)
        if cached is not None and cached[0] == _source_fingerprint(profile, memory_dir, cached[4]):
            return cached[1], cached[2], cached[3]
        deliverables = _deliverable_paths(where.workspace_root)
        fingerprint = _source_fingerprint(profile, memory_dir, deliverables)
        computed_at = dt.datetime.now().astimezone().isoformat(timespec="seconds")
        LIVE_COMPUTE_COUNT += 1
        with tempfile.TemporaryDirectory(prefix="workbench-live-") as tmp:
            out = Path(tmp) / "state.json"
            result = refresh_workflow_state_cache(project_profile_path=profile, output_path=out,
                                                  generated_at=computed_at)
            if result.get("status") != "refreshed":
                raise LiveRefused(f"생성기가 거절했다 ({result.get('status')}) — 원천 부재 {result.get('missing_paths') or []}")
            state_data = _read_json(out)
        if state_data is None:
            raise LiveRefused("생성기 출력을 읽지 못했다")
        built = roadmap.build_roadmap_state(where.workspace_root)
        roadmap_data = built.model_dump(mode="json") if built is not None else None
        _LIVE_CACHE[key] = (fingerprint, computed_at, state_data, roadmap_data, deliverables)
        return computed_at, state_data, roadmap_data


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def _item(raw: object) -> dict[str, str]:
    """`state.json` 의 항목 줄 ``<ID> — <제목>`` 을 나눈다."""
    text = str(raw)
    head, sep, tail = text.partition(" — ")
    return {"id": head.strip(), "title": tail.strip()} if sep else {"id": text.strip(), "title": ""}


def _items(backlog: dict[str, Any], key: str) -> list[dict[str, str]] | None:
    raw = backlog.get(key)
    if not isinstance(raw, list):
        return None  # 생성물에 그 목록이 없다 — 미측정
    return [_item(entry) for entry in raw]


def _milestones(data: dict[str, Any]) -> tuple[list[dict[str, Any]], list[str]]:
    issues = [issue for issue in data.get("issues") or [] if isinstance(issue, dict)]
    used: set[int] = set()
    milestones: list[dict[str, Any]] = []
    for entry in data.get("milestones") or []:
        if not isinstance(entry, dict):
            continue
        mid = str(entry.get("id", ""))
        total = entry.get("total_leaves")
        total = total if isinstance(total, int) else 0
        done = entry.get("done_leaves")
        notes: list[str] = []
        for index, issue in enumerate(issues):
            if mid and mid in str(issue.get("where", "")):
                used.add(index)
                notes.append(f"{issue.get('code', '')}: {issue.get('detail', '')}")
        notes.extend(f"산출물 없음: {path}" for path in entry.get("deliverables_missing") or [])
        milestones.append({
            "id": mid,
            "title": str(entry.get("title", "")),
            "declared": entry.get("declared_status"),
            "derived": entry.get("derived_status"),
            # 잎 0 은 "미측정" — 0% 가 아니다 (스펙 §7.2).
            "leaves_done": done if total > 0 and isinstance(done, int) else None,
            "leaves_total": total,
            "issues": notes,
        })
    orphan = [f"{issue.get('code', '')}: {issue.get('detail', '')}"
              for index, issue in enumerate(issues) if index not in used]
    return milestones, orphan


def task_title(task: plan_tasks.TaskPlan) -> str:
    for line in task.lines:
        match = _TITLE_RE.match(line)
        if match:
            return match.group(1).strip()
    return ""


def build_state(where: Where) -> dict[str, Any]:
    live: tuple[str, dict[str, Any], dict[str, Any] | None] | None
    state_data: dict[str, Any] | None
    computed_at: str | None
    live_error: str | None = None
    try:
        live = live_sources(where)
    except Exception as exc:  # noqa: BLE001 — 실시간 계산의 결함이 화면을 막지 않는다: 생성물로 내려가되 사유를 보인다
        live = None
        live_error = scrub_error(f"{type(exc).__name__}: {exc}", where.workspace_root)
    if live is not None:
        # roadmap 원천이 없으면 roadmap 값도 없다 — 디스크에 남은 낡은 생성물을 실시간으로 보이지 않는다.
        computed_at, state_data, roadmap_data = live
        source = "live"
    else:
        roadmap_data = _read_json(where.roadmap_path)
        state_data = _read_json(where.state_path)
        source = "generated"
        computed_at = None
    milestones, orphan_issues = _milestones(roadmap_data) if roadmap_data else ([], [])
    backlog = state_data.get("backlog") if state_data else None
    backlog = backlog if isinstance(backlog, dict) else {}
    census = plan_responses.inbox_census(where.branch_dir)
    plans: list[dict[str, Any]] = []
    for task in plan_tasks.iter_task_plans(where.tasks_dir):
        pending = census.count(task.task_id)
        if task.status not in plan_tasks.ACTIVE_STATUSES and not pending:
            continue
        plans.append({
            "task": task.task_id,
            "title": task_title(task),
            "status": task.status,
            "open_decisions": plan_tasks.computed_open_decisions(task),
            "pending_responses": pending,
        })
    return {
        "schema": SCHEMA,
        "branch": where.branch,
        "generated_at": {
            "roadmap": roadmap_data.get("generated_at") if roadmap_data else None,
            "state": state_data.get("generated_at") if state_data else None,
        },
        # live = 원천에서 refresh-state 와 같은 생성기로 지금 계산 · generated = 디스크의 생성물 (스펙 §7.1)
        "source": source,
        "computed_at": computed_at,
        "live_error": live_error,
        "milestones": milestones,
        "issues": orphan_issues,
        "tasks": {
            "in_progress": _items(backlog, "in_progress_items"),
            "blocked": _items(backlog, "blocked_items"),
            "planned": _items(backlog, "planned_items"),
            "recent_done": _items(backlog, "done_items"),
        },
        "plans": plans,
        "inbox": {
            "pending": census.pending,
            "unknown": list(census.unknown),
            "layout_problem": census.layout_problem,
        },
    }


@dataclass(frozen=True)
class DecisionView:
    decision: plan_claims.Decision
    state: str
    open: bool


@dataclass(frozen=True)
class PlanView:
    """계획 화면의 값 (스펙 §4.4) — task 파일과 계산값만."""

    task: plan_tasks.TaskPlan
    title: str
    digest: str
    bundles: list[plan_claims.ClaimBundle]
    decisions: list[DecisionView]
    pending: int
    layout_problem: str | None
    has_errors: bool
    verification: list[str]
    out_of_scope: list[str]
    plain_fields: list[tuple[str, str]]


def _field_lines(task: plan_tasks.TaskPlan) -> list[tuple[str, str]]:
    """``- 라벨: 값`` 줄 — 주장이 없는 task 의 화면은 이것을 그대로 보인다."""
    found: list[tuple[str, str]] = []
    for line in task.lines:
        match = re.match(r"^- ([^:]{1,60}):\s?(.*)$", line)
        if match and match.group(2).strip():
            found.append((match.group(1).strip(), match.group(2).strip()))
    return found


def build_plan(where: Where, task: plan_tasks.TaskPlan) -> PlanView:
    plan = task.plan
    result = plan_tasks.computed_states(task)
    open_ids = set(plan_tasks.computed_open_decisions(task))
    census = plan_responses.inbox_census(where.branch_dir)
    fields = _field_lines(task)
    return PlanView(
        task=task,
        title=task_title(task),
        digest=plan_claims.plan_digest(plan),
        bundles=plan_claims.claim_bundles(plan, task.criteria),
        decisions=[
            DecisionView(decision=d, state=result.states.get(d.id, plan_claims.STATE_PROPOSED), open=d.id in open_ids)
            for d in plan.decisions
        ],
        pending=census.count(task.task_id),
        layout_problem=census.layout_problem,
        has_errors=plan_claims.has_error_rules(plan),
        verification=read_task_list_field(list(task.lines), task_label("validation")),
        out_of_scope=read_task_list_field(list(task.lines), task_label("out_of_scope")),
        plain_fields=fields,
    )
