"""폼 → 응답 본문 (워크벤치 스펙 §6 의 1~8).

서버가 쓰는 것은 받은편지함의 응답 한 건뿐이다 — task 파일을 고치지 않고 ``plan-import`` 를 부르지 않는다.
판정 · 렌더 · 공개는 전부 :mod:`workflow_kit.common.plan_responses` 의 함수다 (스펙 §1-8).
"""

from __future__ import annotations

import datetime as dt
import threading
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from workflow_kit.common import plan_claims, plan_responses, plan_tasks


@dataclass(frozen=True)
class Outcome:
    """``status`` 가 200 이면 공개했다 — ``received_at`` 이 있다. 아니면 거절 사유다."""

    status: int
    message: str
    received_at: str | None = None
    path: Path | None = None

    @property
    def ok(self) -> bool:
        return self.status == 200


#: 같은 프로세스 안에서 같은 응답자의 시각을 정하고 공개하는 구간 — 단조 증가를 지킨다 (§6-6).
_PUBLISH_LOCK = threading.Lock()
_EPOCH = dt.datetime(1970, 1, 1, tzinfo=dt.timezone.utc)


def _now() -> dt.datetime:
    return dt.datetime.now().astimezone()


def format_received_at(moment: dt.datetime) -> str:
    return moment.isoformat(timespec="microseconds")


def _latest_eligible_micros(branch_dir: Path, task: plan_tasks.TaskPlan, responder: str) -> int | None:
    """그 task 의 받은편지함 · 보관에서 **자격 있는** 같은 응답자 응답의 가장 늦은 시각 (§6-6)."""
    paths = [
        *plan_responses.inbox_census(branch_dir).paths(task.task_id),
        *plan_responses.archive_files(branch_dir, task.task_id),
    ]
    latest: int | None = None
    for path in paths:
        try:
            parsed, verdict = plan_responses.judge(path, task.plan, task.task_id, plan_has_errors=False)
        except OSError:
            continue
        if not verdict.eligible or parsed.responder != responder:
            continue
        micros = plan_responses.received_micros(parsed.received_at)
        if micros is not None and (latest is None or micros > latest):
            latest = micros
    return latest


def _one(form: Mapping[str, Sequence[str]], key: str) -> str | None:
    values = form.get(key)
    if not values:
        return None
    return values[0]


def build_and_publish(
    *, branch_dir: Path, task: plan_tasks.TaskPlan, form: Mapping[str, Sequence[str]], responder: str,
    now: Callable[[], dt.datetime] | None = None,
) -> Outcome:
    plan = task.plan
    # 1. 배치 — 배타 이동이 성립하지 않는 배치에는 쓰지 않는다.
    problem = plan_responses.layout_problem(branch_dir)
    if problem:
        return Outcome(409, f"계획 응답 배치 문제: {problem} (claim_plan_spec §7-9)")
    # 2. 지문 · 오류 규칙.
    if plan_claims.has_error_rules(plan):
        return Outcome(409, "task 파일의 주장 · 결정이 오류 규칙(L2 · L6 · L9)을 어겼다 — 응답을 받을 수 없다")
    if _one(form, "plan_digest") != plan_claims.plan_digest(plan):
        return Outcome(409, "계획이 바뀌었다, 다시 열어라")
    # 3 · 4. 값.
    values: dict[str, str] = {}
    opened: dict[str, bool] = {}
    for decision in plan.decisions:
        if decision.answered:
            values[decision.id] = decision.default
            opened[decision.id] = False
            continue
        value = _one(form, f"value_{decision.id}")
        if value is None or value not in decision.option_values:
            return Outcome(422, f"{decision.id} 의 값이 선택지에 없다")
        values[decision.id] = value
        opened[decision.id] = _one(form, f"opened_{decision.id}") == "yes"
    # 5. 주석.
    targets = {"-", *(c.id for c in plan.claims), *(d.id for d in plan.decisions)}
    comments: list[tuple[str, str]] = []
    for key in sorted(form):
        if not key.startswith("comment_"):
            continue
        target = key[len("comment_"):]
        body = (_one(form, key) or "").replace("\r\n", "\n").replace("\r", "\n")
        if not body.strip():
            continue
        if target not in targets:
            return Outcome(422, f"주석 대상이 계획에 없다: {target[:40]}")
        if any((ord(ch) < 0x20 and ch not in "\n\t") or ord(ch) == 0x7F for ch in body):
            return Outcome(422, f"주석 [{target}] 에 제어 문자가 있다")
        comments.append((target, body))
    with _PUBLISH_LOCK:
        # 6. 시각 — 같은 응답자의 가장 늦은 자격 있는 응답보다 늦게.
        moment = (now or _now)()  # 기본값은 호출 시점에 찾는다 — 검사가 시계를 바꿔 끼울 수 있게
        latest = _latest_eligible_micros(branch_dir, task, responder)
        current = plan_responses.received_micros(format_received_at(moment))
        if latest is not None and current is not None and current <= latest:
            moment = (_EPOCH + dt.timedelta(microseconds=latest + 1)).astimezone(moment.tzinfo)
        received_at = format_received_at(moment)
        # 7. 렌더 · 자격.
        body_text = plan_responses.render_response(
            task_id=task.task_id, plan=plan, responder=responder, received_at=received_at,
            values=values, opened=opened, comments=comments)
        data = body_text.encode("utf-8")
        verdict = plan_responses.qualify(plan_responses.parse_response(data), plan, task.task_id)
        if not verdict.eligible:
            return Outcome(422, f"응답이 자격 {verdict.stage} 단계에서 떨어진다: {verdict.reason}")
        # 8. 공개.
        path = plan_responses.publish(branch_dir, task.task_id, data)
    return Outcome(200, f"{responder} 의 응답을 {received_at} 에 받았다 — 작업 세션이 `plan-import` 로 반영한다",
                   received_at=received_at, path=path)
