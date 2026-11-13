"""주장 트리 계획 — task 파일을 읽어 계획과 결정 상태를 돌려주는 얇은 I/O 층.

계산은 전부 :mod:`workflow_kit.common.plan_claims` (순수 함수)가 한다. 이 모듈은 파일을 읽어
그 함수에 넘기기만 한다 — 게이트 · ``plan-status`` · state 생성기 · 우회 검출이 "task 파일을 어떻게
읽는가" 를 각자 정하면 갈라진다 (`core/claim_plan_spec.md` §1-6).

보관 응답을 읽는 자리는 :func:`archived_responses` 하나다 — 자격(스펙 §8.1)을 매번 다시 본 것만 돌려준다.
응답 파일의 형식과 디렉터리는 :mod:`workflow_kit.common.plan_responses` 가 안다.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from workflow_kit.common import plan_claims, plan_responses
from workflow_kit.common.project_docs import task_label, task_label_aliases
from workflow_kit.common.workflow_writes import read_task_list_field

_FRONTMATTER_RE = re.compile(r"^---\n(.+?)\n---", re.S)

#: `state.json` 의 `open_decisions` 가 세는 task 상태 (스펙 §11).
ACTIVE_STATUSES: tuple[str, ...] = ("in_progress", "blocked", "planned")


@dataclass(frozen=True)
class TaskPlan:
    task_id: str
    status: str | None
    path: Path
    lines: tuple[str, ...]
    plan: plan_claims.Plan
    criteria: tuple[str, ...]

    @property
    def has_plan(self) -> bool:
        return not self.plan.empty


def _plan_markers() -> tuple[str, ...]:
    return tuple(
        f"- {alias}:"
        for key in (plan_claims.CLAIMS_KEY, plan_claims.DECISIONS_KEY)
        for alias in task_label_aliases(key)
    )


def read_task_plan(path: Path) -> TaskPlan | None:
    """task 파일 하나를 읽는다. 읽을 수 없거나 frontmatter 에 ``id`` 가 없으면 ``None``."""
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    frontmatter = _FRONTMATTER_RE.match(text)
    if not frontmatter:
        return None
    id_match = re.search(r"^id:\s*(\S+)", frontmatter.group(1), re.M)
    if not id_match:
        return None
    status_match = re.search(r"^status:\s*(\S+)", frontmatter.group(1), re.M)
    lines = text.splitlines()
    return TaskPlan(
        task_id=id_match.group(1),
        status=status_match.group(1) if status_match else None,
        path=path,
        lines=tuple(lines),
        plan=plan_claims.parse_plan(lines),
        criteria=tuple(read_task_list_field(lines, task_label("done_criteria"))),
    )


def iter_task_plans(tasks_dir: Path | None) -> Iterator[TaskPlan]:
    """주장 또는 결정이 있는 task 만 돌려준다. 없는 task 는 파싱하지 않는다."""
    if tasks_dir is None or not tasks_dir.is_dir():
        return
    markers = _plan_markers()
    for task_file in sorted(tasks_dir.glob("TASK-*.md")):
        try:
            text = task_file.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if not any(marker in text for marker in markers):
            continue
        task = read_task_plan(task_file)
        if task is not None and task.has_plan:
            yield task


def branch_dir_of(task: TaskPlan) -> Path:
    """그 task 파일이 속한 브랜치 네임스페이스 — ``<branch>/backlog/tasks/<id>.md`` 의 ``<branch>``."""
    return task.path.parent.parent.parent


def archived_responses(task: TaskPlan) -> tuple[plan_claims.Response, ...]:
    """그 task 의 자격 있는 보관 응답 (스펙 §8.1). task 파일이 오류 규칙을 어기면 하나도 없다 (0 단계)."""
    return plan_responses.qualified_archive(branch_dir_of(task), task.task_id, task.plan)


def pending_responses(task: TaskPlan) -> list[Path]:
    """그 task 의 받은편지함 응답 (스펙 §7-7)."""
    return plan_responses.inbox_files(branch_dir_of(task), task.task_id)


def computed_states(task: TaskPlan) -> plan_claims.StateResult:
    """결정 상태의 **계산값** (스펙 §8). 게이트와 ``plan-status`` 는 칸이 아니라 이것으로 판정한다."""
    return plan_claims.compute_states(task.plan, archived_responses(task))


def computed_open_decisions(task: TaskPlan) -> list[str]:
    return plan_claims.open_decision_ids(task.plan, archived_responses(task))


def column_open_decisions(tasks_dir: Path | None) -> dict[str, int]:
    """`state.json` 의 `open_decisions` — 진행 중 · 차단 · 계획 task 의 **칸 기준** 열린 결정 수.

    생성기의 입력은 task 파일뿐이다. 그래서 칸으로 센다 — 판정의 정본은 게이트(계산값)이고,
    둘이 어긋나면 :func:`bypassed_done_tasks` 류의 경고가 드러낸다 (스펙 §11).
    """
    counts: dict[str, int] = {}
    for task in iter_task_plans(tasks_dir):
        if task.status not in ACTIVE_STATUSES:
            continue
        opened = plan_claims.column_open_decision_ids(task.plan)
        if opened:
            counts[task.task_id] = len(opened)
    return counts


def bypassed_done_tasks(tasks_dir: Path | None) -> list[tuple[str, list[str]]]:
    """``done`` 인데 계산한 열린 결정이 있는 task (스펙 §4 우회 검출).

    게이트를 모르는 옛 kit 이 닫았거나 손으로 닫은 것이다. 읽기 전용 판정이다 — 파일을 고치지 않는다.
    """
    found: list[tuple[str, list[str]]] = []
    for task in iter_task_plans(tasks_dir):
        if task.status != "done":
            continue
        opened = computed_open_decisions(task)
        if opened:
            found.append((task.task_id, opened))
    return found


def bypass_warnings(tasks_dir: Path | None) -> list[str]:
    return [
        f"done 인데 열린 결정이 있다: {task_id} ({', '.join(opened)})"
        for task_id, opened in bypassed_done_tasks(tasks_dir)
    ]
