#!/usr/bin/env python3
"""`plan-import` — 받은편지함의 계획 응답을 보관으로 옮기고 결정 상태를 다시 계산한다.

계약 정본: ``core/claim_plan_spec.md`` §9 (명령) · §7 (디렉터리) · §8 (자격 · 계산).

```
python -m workflow_kit plan-import --task=<TASK-ID> [--response=<파일>] [--apply]
python -m workflow_kit plan-import --discard=<파일> --reason=<사유> [--apply]
```

- 기본은 dry-run 이다. 판정은 ``--apply`` 와 같고 아무것도 쓰지 않는다 (받은편지함 디렉터리도 만들지 않는다).
- **판정 순서**: 0 단계(task 파일의 오류 규칙)를 잠금보다 먼저 본다 — 잠금 없이 판정할 수 있고, 거부된 명령은
  아무것도 바꾸지 않아야 한다. 그다음 잠금, 쥔 뒤 받은편지함과 task 파일을 **다시** 읽는다.
- ``--apply`` 가 하는 일은 셋이다: 자격 있는 응답을 보관으로 옮긴다 · 다시 계산해 상태 칸을 적는다 · Progress 한 줄.
  주석은 반영하지 않는다. task 의 ``status`` 는 건드리지 않는다 — ``done`` 인 task 도 받는다.
- 잠금을 못 쥐면 기다리지 않는다: ``import_busy`` 를 보고하고 rc 0, 아무것도 쓰지 않는다.
- 계산은 전부 :mod:`workflow_kit.common.plan_claims` 가, 응답 형식과 디렉터리는
  :mod:`workflow_kit.common.plan_responses` 가 안다. 이 파일은 순서만 정한다.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

from workflow_kit import __version__ as TOOL_VERSION
from workflow_kit.common import plan_claims, plan_responses, plan_tasks
from workflow_kit.common.atomic_write import atomic_write_text
from workflow_kit.common.errors import build_error_result
from workflow_kit.common.paths import (
    discover_project_profile_path,
    project_workspace_root,
    workflow_branch_dir,
)
from workflow_kit.common.project_docs import task_label
from workflow_kit.common.schemas import (
    PlanImportOutput,
    PlanImportSourceContext,
    PlanResponseVerdict,
    PlanStateChange,
)
from workflow_kit.common.stdio import force_utf8_stdio
from workflow_kit.common.workflow_writes import _set_list_field

MODE_IMPORT = "import"
MODE_DISCARD = "discard"



def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m workflow_kit plan-import",
        description="받은편지함의 계획 응답을 보관으로 옮기고 결정 상태를 다시 계산한다 (기본 dry-run).",
        allow_abbrev=False,
    )
    parser.add_argument("--task", default=None, help="task ID (--discard 에서는 파일 이름에서 읽는다)")
    parser.add_argument("--response", default=None, help="받은편지함의 응답 파일 하나만 옮긴다")
    parser.add_argument("--discard", default=None, help="받은편지함 또는 보관의 응답 파일을 거둔다 (.rejected.md)")
    parser.add_argument("--reason", default=None, help="--discard 의 사유 — Progress 에 남는다")
    parser.add_argument("--apply", action="store_true", help="실제로 옮기고 쓴다")
    parser.add_argument("--project-profile-path", default=None, help="미지정 시 cwd 상위에서 자동 탐색")
    return parser


@dataclass
class Context:
    task_id: str
    mode: str
    task_path: Path
    branch_dir: Path
    workspace_root: Path

    def rel(self, path: Path) -> str:
        try:
            return path.resolve().relative_to(self.workspace_root.resolve()).as_posix()
        except ValueError:
            return path.name


def _error(ctx_task: str, mode: str, error: str, code: str, rc: int, warnings: list[str] | None = None) -> int:
    print(json.dumps(build_error_result(
        tool_version=TOOL_VERSION, error=error, error_code=code, warnings=warnings or [],
        source_context={"task_id": ctx_task, "mode": mode},
    ), ensure_ascii=False, indent=2))
    return rc


def _emit(output: PlanImportOutput) -> int:
    print(json.dumps(output.model_dump(mode="json"), ensure_ascii=False, indent=2))
    return 0


def _resolve_response(raw: str, branch_dir: Path, *, inbox_only: bool) -> Path | None:
    """응답 파일을 찾는다 — 경로 그대로, 또는 이름만 주면 받은편지함 · 보관에서. 그 두 디렉터리 밖이면 ``None``."""
    inbox = plan_responses.inbox_dir(branch_dir)
    archive = plan_responses.responses_dir(branch_dir)
    allowed = (inbox,) if inbox_only else (inbox, archive)
    candidates = [Path(raw)] if Path(raw).is_file() else []
    candidates += [directory / Path(raw).name for directory in allowed]
    for candidate in candidates:
        if candidate.is_file() and any(candidate.resolve().parent == d.resolve() for d in allowed):
            return candidate.resolve().parent / candidate.name
    return None


def _order_key(item: tuple[Path, plan_responses.ParsedResponse, plan_responses.Verdict], task_id: str) -> tuple[int, int]:
    path, parsed, _ = item
    micros = plan_responses.received_micros(parsed.received_at)
    return (micros if micros is not None else -1, plan_responses.number_of(path, task_id) or 0)


def _verdict(
    path: Path, parsed: plan_responses.ParsedResponse, verdict: plan_responses.Verdict, *,
    location: str, action: str, moved_to: str | None,
) -> PlanResponseVerdict:
    return PlanResponseVerdict(
        name=path.name, location=location, eligible=verdict.eligible, stage=verdict.stage, reason=verdict.reason,
        responder=parsed.responder, received_at=parsed.received_at, comments=len(parsed.comments),
        action=action, moved_to=moved_to)


def _predict_name(ctx: Context, path: Path, taken: set[int], *, rejected: bool) -> Path:
    """dry-run — 옮기면 놓일 이름. 실제 이동과 같은 규칙으로 번호를 고른다 (접미사를 통틀어 유일)."""
    number = plan_responses.number_of(path, ctx.task_id) or 0
    while number in taken:
        number += 1
    taken.add(number)
    suffix = plan_responses.REJECTED_SUFFIX if rejected else ".md"
    return plan_responses.responses_dir(ctx.branch_dir) / f"{ctx.task_id}-{number}{suffix}"


def _read_lines(path: Path) -> tuple[list[str], bool]:
    """task 파일을 줄로 — (줄들, 끝에 줄바꿈이 있었나)."""
    text = path.read_bytes().decode("utf-8").replace("\r\n", "\n")
    return (text[:-1] if text.endswith("\n") else text).split("\n"), text.endswith("\n")


def _write_lines(path: Path, lines: list[str], trailing: bool) -> None:
    """한 번에 바꿔 놓는다 — 쓰는 도중의 반쯤 쓴 task 파일을 다른 명령(게이트 · 쓰는 쪽)이 읽지 않게.

    줄바꿈은 그 파일의 것을 따른다 (`atomic_write_text` 가 기존 관례를 읽는다).
    """
    atomic_write_text(path, "\n".join(lines) + ("\n" if trailing else ""))


def _recalc_note(changes: list[tuple[str, str, str]]) -> str:
    return "결정 상태 재계산: " + ", ".join(f"{d} {old} → {new}" for d, old, new in changes)


def _finish(
    ctx: Context, task: plan_tasks.TaskPlan, *, apply: bool, outcome: str,
    responses: list[plan_claims.Response], verdicts: list[PlanResponseVerdict],
    headline: str | None, warnings: list[str],
) -> int:
    """다시 계산하고, (``--apply`` 면) 상태 칸과 Progress 를 적고, 결과를 낸다."""
    result = plan_claims.compute_states(task.plan, responses)
    lines, trailing = _read_lines(ctx.task_path)
    lines, changes = plan_claims.rewrite_decision_states(lines, result.states)
    if headline is not None:
        progress: str | None = headline.replace("{superseded}", str(len(result.superseded_responses))).replace(
            "{tally}", _tally(task.plan, result))
        if changes and outcome == "discarded":
            progress = f"{progress} · {_recalc_note(changes)}"
    else:
        progress = _recalc_note(changes) if changes else None
    wrote = False
    if apply and progress is not None:
        lines, found = _set_list_field(lines, task_label("progress"), [progress])
        if not found:
            warnings.append("task 파일에 Progress 줄이 없어 한 줄을 남기지 못했다")
        _write_lines(ctx.task_path, lines, trailing)
        wrote = True
    open_ids = plan_claims.open_decision_ids(task.plan, responses)
    unknown = plan_responses.unknown_inbox_files(ctx.branch_dir)
    if unknown:
        warnings.append(f"받은편지함에 알 수 없는 파일 {len(unknown)}건: {', '.join(unknown)}")
    if result.disputed_responses:
        warnings.append("다툼에 든 응답: " + ", ".join(result.disputed_responses))
    remaining = len(plan_responses.inbox_files(ctx.branch_dir, ctx.task_id)) - (
        0 if apply else sum(1 for v in verdicts if v.location == "inbox" and v.action in ("archived", "rejected")))
    if progress is None and outcome in ("imported", "dry_run"):
        outcome = "nothing_to_do" if apply else outcome
    return _emit(PlanImportOutput(
        status="warning" if warnings else "ok",  # type: ignore[arg-type]
        tool_version=TOOL_VERSION,
        warnings=warnings,
        task_id=ctx.task_id,
        applied=wrote,
        outcome=outcome,
        responses=verdicts,
        state_changes=[PlanStateChange(id=d, before=old, after=new) for d, old, new in changes],
        states=dict(result.states),
        open_decisions=open_ids,
        progress_line=progress,
        pending_responses=remaining,
        unknown_inbox_files=unknown,
        source_context=PlanImportSourceContext(task_id=ctx.task_id, task_path=ctx.rel(ctx.task_path), mode=ctx.mode),
    ))


def _tally(plan: plan_claims.Plan, result: plan_claims.StateResult) -> str:
    kinds = [state.split(":", 1)[0] for state in result.states.values()]
    return (f"결정 {len(plan.decisions)} (바뀜 {kinds.count(plan_claims.STATE_CHANGED)} · "
            f"유지 {kinds.count(plan_claims.STATE_KEPT)} · 미열람 {kinds.count(plan_claims.STATE_UNOPENED)} · "
            f"다툼 {kinds.count(plan_claims.STATE_DISPUTED)})")


def _busy(ctx: Context) -> int:
    return _emit(PlanImportOutput(
        status="warning",  # type: ignore[arg-type]
        tool_version=TOOL_VERSION,
        warnings=["import_busy — 다른 plan-import 가 받은편지함을 쥐고 있다. 아무것도 쓰지 않았다, 다시 부른다."],
        task_id=ctx.task_id, applied=False, outcome="import_busy",
        pending_responses=len(plan_responses.inbox_files(ctx.branch_dir, ctx.task_id)),
        source_context=PlanImportSourceContext(task_id=ctx.task_id, task_path=ctx.rel(ctx.task_path), mode=ctx.mode),
    ))


def _load_task(ctx: Context) -> tuple[plan_tasks.TaskPlan | None, int | None]:
    """task 를 읽고 0 단계를 본다. (task, 끝낼 rc) — rc 가 있으면 이미 오류를 냈다."""
    task = plan_tasks.read_task_plan(ctx.task_path) if ctx.task_path.is_file() else None
    if task is None:
        return None, _error(ctx.task_id, ctx.mode, f"task 파일이 없거나 읽을 수 없다: {ctx.task_path}", "task_not_found", 2)
    if plan_claims.has_error_rules(task.plan):
        errors = plan_claims.lint_errors(plan_claims.lint_plan(task.plan, criteria=task.criteria))
        return None, _error(
            ctx.task_id, ctx.mode,
            "task 파일의 주장 · 결정이 오류 규칙을 어긴다 — 어떤 응답도 자격이 없다 (0 단계). 아무것도 옮기지 않았다: "
            + " / ".join(issue.render() for issue in errors),
            "plan_lint_error", 1)
    return task, None


def run_import(ctx: Context, *, response: str | None, apply: bool) -> int:
    task, rc = _load_task(ctx)
    if task is None:
        return rc if rc is not None else 2
    only: Path | None = None
    if response is not None:
        only = _resolve_response(response, ctx.branch_dir, inbox_only=True)
        if only is None or plan_responses.number_of(only, ctx.task_id) is None or only.name.endswith(
                plan_responses.REJECTED_SUFFIX):
            return _error(ctx.task_id, ctx.mode,
                          f"--response 는 그 task 의 받은편지함 파일이어야 한다: {response}", "response_not_found", 2)

    def body() -> int:
        fresh, fresh_rc = _load_task(ctx)  # 잠금을 쥔 뒤 다시 읽는다
        if fresh is None:
            return fresh_rc if fresh_rc is not None else 2
        paths = [only] if only is not None else plan_responses.inbox_files(ctx.branch_dir, ctx.task_id)
        judged = [
            (path, *plan_responses.judge(path, fresh.plan, ctx.task_id, plan_has_errors=False))
            for path in paths if path.is_file()
        ]
        judged.sort(key=lambda item: _order_key(item, ctx.task_id))
        taken = plan_responses.taken_numbers(ctx.branch_dir, ctx.task_id)
        verdicts: list[PlanResponseVerdict] = []
        incoming: list[plan_claims.Response] = []
        moved: list[tuple[plan_responses.ParsedResponse, Path]] = []
        for path, parsed, verdict in judged:
            if not verdict.eligible:
                verdicts.append(_verdict(path, parsed, verdict, location="inbox", action="kept_in_inbox", moved_to=None))
                continue
            if apply:
                target = plan_responses.move_exclusive(path, ctx.branch_dir, ctx.task_id)
            else:
                taken.discard(plan_responses.number_of(path, ctx.task_id) or 0)
                target = _predict_name(ctx, path, taken, rejected=False)
                incoming.append(plan_claims.Response(
                    responder=parsed.responder, received_at=parsed.received_at, decisions=parsed.decisions,
                    content_sha256=parsed.content_sha256, name=target.name))
            moved.append((parsed, target))
            verdicts.append(_verdict(path, parsed, verdict, location="inbox", action="archived", moved_to=ctx.rel(target)))
        responses = [*plan_responses.qualified_archive(ctx.branch_dir, ctx.task_id, fresh.plan), *incoming]
        headline = None
        if moved:
            responders = ", ".join(sorted({parsed.responder for parsed, _ in moved}))
            headline = (
                f"plan 응답 {len(moved)}건 ({responders}): {{tally}} · "
                f"주석 {sum(len(parsed.comments) for parsed, _ in moved)} · 대체 {{superseded}} — "
                + ", ".join(ctx.rel(target) for _, target in moved))
        return _finish(ctx, fresh, apply=apply, outcome="imported" if apply else "dry_run",
                       responses=responses, verdicts=verdicts, headline=headline, warnings=[])

    if not apply:
        return body()
    with plan_responses.inbox_lock(ctx.branch_dir) as held:
        return body() if held else _busy(ctx)


def run_discard(ctx: Context, target_path: Path, *, reason: str, apply: bool) -> int:
    task, rc = _load_task(ctx)
    if task is None:
        return rc if rc is not None else 2
    location = "inbox" if target_path.parent.resolve() == plan_responses.inbox_dir(ctx.branch_dir).resolve() else "archive"

    def body() -> int:
        fresh, fresh_rc = _load_task(ctx)
        if fresh is None:
            return fresh_rc if fresh_rc is not None else 2
        if not target_path.is_file():
            return _error(ctx.task_id, ctx.mode, f"거둘 응답 파일이 없다: {target_path.name}", "response_not_found", 2)
        parsed, verdict = plan_responses.judge(target_path, fresh.plan, ctx.task_id, plan_has_errors=False)
        if apply:
            rejected = plan_responses.move_exclusive(target_path, ctx.branch_dir, ctx.task_id, rejected=True)
        else:
            taken = plan_responses.taken_numbers(ctx.branch_dir, ctx.task_id, ignore=target_path)
            rejected = _predict_name(ctx, target_path, taken, rejected=True)
        responses = [
            r for r in plan_responses.qualified_archive(ctx.branch_dir, ctx.task_id, fresh.plan)
            if apply or location != "archive" or r.name != target_path.name
        ]
        headline = f"plan 응답 거둠 ({target_path.name}): {reason} — {ctx.rel(rejected)}"
        return _finish(
            ctx, fresh, apply=apply, outcome="discarded" if apply else "dry_run", responses=responses,
            verdicts=[_verdict(target_path, parsed, verdict, location=location, action="rejected",
                               moved_to=ctx.rel(rejected))],
            headline=headline, warnings=[])

    if not apply:
        return body()
    with plan_responses.inbox_lock(ctx.branch_dir) as held:
        return body() if held else _busy(ctx)


def main(argv: list[str] | None = None) -> int:
    force_utf8_stdio()
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.discard is None:
        if args.task is None:
            parser.error("--task 또는 --discard 가 필요하다")
        if args.reason is not None:
            parser.error("--reason 은 --discard 와 함께만 쓴다")
    else:
        if args.response is not None:
            parser.error("--discard 와 --response 는 함께 쓰지 않는다")
        if not any(ch.isalnum() for ch in (args.reason or "")):
            parser.error("--discard 에는 --reason=<사유> 가 필요하다")
    mode = MODE_DISCARD if args.discard is not None else MODE_IMPORT
    label = args.task or ""

    if args.project_profile_path:
        profile = Path(args.project_profile_path).resolve()
    else:
        discovered = discover_project_profile_path()
        if discovered is None:
            return _error(label, mode, "PROJECT_PROFILE.md 를 cwd 상위에서 찾지 못했다. --project-profile-path 로 명시하라.",
                          "missing_required_document", 2)
        profile = discovered.resolve()
    if not profile.is_file():
        return _error(label, mode, f"PROJECT_PROFILE.md 가 없다: {profile}", "missing_required_document", 2)
    branch_dir = workflow_branch_dir(profile)

    target: Path | None = None
    task_id = args.task
    if mode == MODE_DISCARD:
        target = _resolve_response(args.discard, branch_dir, inbox_only=False)
        named = plan_responses.task_of_response_name(target.name) if target is not None else None
        if target is None or named is None:
            return _error(label, mode, f"--discard 는 받은편지함 또는 보관의 응답 파일이어야 한다: {args.discard}",
                          "response_not_found", 2)
        if task_id is not None and plan_responses.number_of(target, task_id) is None:
            return _error(label, mode, f"그 파일은 {task_id} 의 응답이 아니다: {target.name}", "response_not_found", 2)
        task_id = task_id or named
    assert task_id is not None
    ctx = Context(
        task_id=task_id, mode=mode, task_path=branch_dir / "backlog" / "tasks" / f"{task_id}.md",
        branch_dir=branch_dir, workspace_root=project_workspace_root(profile))
    if mode == MODE_DISCARD and target is not None:
        return run_discard(ctx, target, reason=args.reason.strip(), apply=args.apply)
    return run_import(ctx, response=args.response, apply=args.apply)


if __name__ == "__main__":
    sys.exit(main())
