#!/usr/bin/env python3
"""`plan-status` — task 의 주장별 묶음과 결정 상태를 낸다 (읽기 전용).

계약 정본: ``core/claim_plan_spec.md`` §10 (ADR-031 결정 4). 내는 것은 1단계 주장마다 그것(또는
후손)을 인용한 완료 기준, 결정마다 **계산한** 상태와 칸의 값, 열린 결정, 받은편지함 건수다.

- 아무것도 쓰지 않는다. 상태 칸이 계산값과 달라도 고치지 않고 둘 다 보인다.
- ``--format=md`` 는 검증 보고에 붙일 `### 주장별` 절만 낸다. 판정 칸은 비어 있다 — 채우는 것은
  검증하는 쪽이다. 주장이 없는 task 는 아무것도 내지 않는다.
- 계산은 전부 :mod:`workflow_kit.common.plan_claims` 가 한다. 게이트와 같은 함수다.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from workflow_kit import __version__ as TOOL_VERSION
from workflow_kit.common import plan_claims, plan_responses, plan_tasks
from workflow_kit.common.errors import build_error_result
from workflow_kit.common.paths import (
    discover_project_profile_path,
    project_workspace_root,
    workflow_branch_dir,
)
from workflow_kit.common.schemas import (
    PlanClaimBundle,
    PlanDecisionStatus,
    PlanResponseVerdict,
    PlanStatusOutput,
    PlanStatusSourceContext,
)
from workflow_kit.common.stdio import force_utf8_stdio

FORMAT_JSON = "json"
FORMAT_MD = "md"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m workflow_kit plan-status",
        description="task 의 주장별 묶음과 결정 상태를 낸다 (읽기 전용).",
        allow_abbrev=False,
    )
    parser.add_argument("--task", required=True, help="task ID")
    parser.add_argument("--format", choices=(FORMAT_JSON, FORMAT_MD), default=FORMAT_JSON, dest="output_format")
    parser.add_argument("--project-profile-path", default=None, help="미지정 시 cwd 상위에서 자동 탐색")
    return parser


def render_markdown(
    bundles: list[plan_claims.ClaimBundle], open_decisions: list[tuple[str, str]],
) -> str:
    """검증 보고에 붙일 절. 주장이 없으면 빈 문자열."""
    if not bundles:
        return ""
    lines = ["### 주장별", "", "| 주장 | 기준 | 판정 |", "|---|---|---|"]
    for bundle in bundles:
        cited = ", ".join(f"#{n}" for n in bundle.criteria) or "—"
        verdict = "재지 않는 주장" if bundle.unmeasured else ""
        lines.append(f"| {bundle.claim.id} {bundle.claim.text} | {cited} | {verdict} |")
    if open_decisions:
        lines.extend(["", "- 열린 결정: " + ", ".join(f"{d} ({state})" for d, state in open_decisions)])
    return "\n".join(lines)


def response_verdict(
    path: Path, parsed: plan_responses.ParsedResponse, verdict: plan_responses.Verdict, *, location: str,
) -> PlanResponseVerdict:
    """응답 파일 한 건의 판정을 출력 모양으로 — `plan-import` 와 같은 모양이다."""
    return PlanResponseVerdict(
        name=path.name, location=location, eligible=verdict.eligible, stage=verdict.stage, reason=verdict.reason,
        responder=parsed.responder, received_at=parsed.received_at, comments=len(parsed.comments))


def build_status(task: plan_tasks.TaskPlan, workspace_root: Path) -> PlanStatusOutput:
    plan = task.plan
    bundles = plan_claims.claim_bundles(plan, task.criteria)
    result = plan_tasks.computed_states(task)
    open_ids = plan_tasks.computed_open_decisions(task)
    decisions = [
        PlanDecisionStatus(
            id=decision.id,
            claim_id=decision.claim_id,
            question=decision.question,
            default=decision.default,
            options=list(decision.option_values),
            state=result.states.get(decision.id, plan_claims.STATE_PROPOSED),
            column_state=decision.state,
            open=decision.id in open_ids,
        )
        for decision in plan.decisions
    ]
    issues = plan_claims.lint_plan(plan, criteria=task.criteria)
    warnings = [
        f"상태 칸이 계산값과 다르다: {d.id} 칸 {d.column_state} · 계산 {d.state}"
        for d in decisions if d.column_state != d.state
    ]
    branch_dir = plan_tasks.branch_dir_of(task)
    census = plan_responses.inbox_census(branch_dir)
    inbox = [
        response_verdict(path, parsed, verdict, location="inbox")
        for path in census.paths(task.task_id)
        for parsed, verdict in [plan_responses.judge(
            path, plan, task.task_id, plan_has_errors=plan_claims.has_error_rules(plan))]
    ]
    unknown = list(census.unknown)
    if inbox:
        warnings.append(f"계획 응답 {len(inbox)}건 미반영 ({task.task_id}) — plan-import 로 확인")
    if unknown:
        warnings.append(f"받은편지함에 알 수 없는 파일 {len(unknown)}건: {', '.join(unknown)}")
    # 배치 문제와 보관의 비파일 항목은 보고만 한다 (ADR-032 결정 18 · 25, 주장 스펙 §7-9).
    layout_note = census.layout_warning()
    if layout_note:
        warnings.append(layout_note)
    odd_archive = plan_responses.odd_archive_entries(branch_dir)
    if odd_archive:
        warnings.append(f"보관에 보통 파일이 아닌 응답 이름 항목 {len(odd_archive)}건(응답으로 읽지 않는다): "
                        + ", ".join(odd_archive))
    try:
        relative = task.path.resolve().relative_to(workspace_root.resolve()).as_posix()
    except ValueError:
        relative = task.path.name
    return PlanStatusOutput(
        status="warning" if warnings else "ok",  # type: ignore[arg-type]
        tool_version=TOOL_VERSION,
        warnings=warnings,
        task_id=task.task_id,
        task_status=task.status,
        has_plan=task.has_plan,
        plan_digest=plan_claims.plan_digest(plan) if task.has_plan else None,
        claims=[
            PlanClaimBundle(
                id=b.claim.id, text=b.claim.text, criteria=list(b.criteria), unmeasured=b.unmeasured)
            for b in bundles
        ],
        decisions=decisions,
        open_decisions=open_ids,
        lint=[issue.render() for issue in issues if issue.rule != "L5" or issue.severity != "note"],
        pending_responses=census.count(task.task_id),
        inbox=inbox,
        unknown_inbox_files=unknown,
        disputed_responses=list(result.disputed_responses),
        superseded_responses=list(result.superseded_responses),
        markdown=render_markdown(
            bundles, [(d, result.states.get(d, plan_claims.STATE_PROPOSED)) for d in open_ids]),
        source_context=PlanStatusSourceContext(task_id=task.task_id, task_path=relative),
    )


def _fail(error: str, error_code: str, task_id: str) -> int:
    print(json.dumps(build_error_result(
        tool_version=TOOL_VERSION, error=error, error_code=error_code,
        warnings=[], source_context={"task_id": task_id},
    ), ensure_ascii=False, indent=2))
    return 2


def main(argv: list[str] | None = None) -> int:
    force_utf8_stdio()
    args = build_parser().parse_args(argv)
    if args.project_profile_path:
        profile = Path(args.project_profile_path).resolve()
    else:
        discovered = discover_project_profile_path()
        if discovered is None:
            return _fail(
                "PROJECT_PROFILE.md 를 cwd 상위에서 찾지 못했다. --project-profile-path 로 명시하라.",
                "missing_required_document", args.task)
        profile = discovered.resolve()
    if not profile.is_file():
        return _fail(f"PROJECT_PROFILE.md 가 없다: {profile}", "missing_required_document", args.task)

    task_path = workflow_branch_dir(profile) / "backlog" / "tasks" / f"{args.task}.md"
    task = plan_tasks.read_task_plan(task_path) if task_path.is_file() else None
    if task is None:
        return _fail(f"task 파일이 없거나 읽을 수 없다: {task_path}", "task_not_found", args.task)

    output = build_status(task, project_workspace_root(profile))
    if args.output_format == FORMAT_MD:
        if output.markdown:
            print(output.markdown)
        return 0
    print(json.dumps(output.model_dump(mode="json"), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
