"""진척 값 (워크벤치 스펙 §7) — 진척 화면과 ``api/state`` 가 같이 쓴다.

원천은 생성물(`roadmap_state.json` · 브랜치 `state.json`)과 task 파일뿐이다. 재지 않은 것은 ``None`` 으로
두고 화면이 "미측정" 으로 그린다. 절대 경로 · 호스트 이름 · 사용자 홈 · 환경변수 · 토큰 이름은 싣지 않는다.
"""

from __future__ import annotations

import json
import re
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

    @property
    def tasks_dir(self) -> Path:
        return self.branch_dir / "backlog" / "tasks"

    @property
    def state_path(self) -> Path:
        return state_path_for_workspace(self.workspace_root, self.branch)

    @property
    def roadmap_path(self) -> Path:
        return roadmap.state_path(self.workspace_root)


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
    roadmap_data = _read_json(where.roadmap_path)
    state_data = _read_json(where.state_path)
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
