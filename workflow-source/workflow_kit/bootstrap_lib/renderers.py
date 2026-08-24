"""Render functions for the generated kit's doc artefacts.

Every ``render_*`` function takes the parsed CLI args and the inferred
project context, and returns the full text of the corresponding
generated artefact. The functions are pure (no side effects), so the
caller decides when and where to write the output.

Templates live in ``workflow-source/templates/`` and are loaded with
:func:`load_template`. The renderers substitute placeholders like
``YYYY-MM-DD`` or ``<Project Name>``.
"""

from __future__ import annotations

import argparse
import re
import os
from pathlib import Path

#: Filesystem root of the bootstrap kit (the directory that ships ``templates/`` etc.).
#: Resolved at import time so renderers can load templates without threading it
#: through every call site. Tests can monkey-patch this if they need to swap roots.
SOURCE_ROOT = Path(os.environ.get("STANDARD_AI_WORKFLOW_ROOT", Path(__file__).resolve().parents[2])).resolve()


def _selected_harnesses(args: argparse.Namespace) -> list[str]:
    """Helper: extract the selected harness list from args (imported lazily to avoid cycles)."""
    # Import here to avoid circular import (__main__ imports renderers, renderers
    # only needs to know the result, not selected_harnesses itself).
    from workflow_kit.bootstrap_lib.__main__ import selected_harnesses

    return selected_harnesses(args)


def _value_or_inferred(explicit: str | None, fallback: str) -> str:
    """Helper: prefer explicit CLI value unless it is empty or a ``TODO:`` placeholder."""
    from workflow_kit.bootstrap_lib.discovery import value_or_inferred

    return value_or_inferred(explicit, fallback)


def render_readme(
    args: argparse.Namespace,
    context: dict[str, object],
    *,
    default_core_docs: list[str],
) -> str:
    if args.copy_core_docs:
        core_docs = "\n".join(
            f"- [core/{name}](./core/{name})" for name in default_core_docs
        )
    else:
        core_docs = "- Core documents can be copied along with `--copy-core-docs`."
    generated_assessment = ""
    mode_summary = "Generated the default document set for a new project."
    harness_lines = "\n".join(
        f"- Generated overlay files for the `{name}` harness" for name in _selected_harnesses(args)
    ) or "- No harness selected"
    if args.adoption_mode == "existing":
        generated_assessment = (
            "- [ai-workflow/memory/active/repository_assessment.md]"
            "(./ai-workflow/memory/active/repository_assessment.md)"
        )
        mode_summary = "Generated draft documents and an assessment reflecting the analysis of the existing project."
    return f"""# Standard AI Workflow Kit

- Purpose: describe the bootstrap result so the `{args.project_name}` repository can adopt the standard AI workflow document set.
- Scope: where the shared core documents live, the project state document set, follow-up per adoption mode
- Audience: developer, operator, AI agent, project onboarding owner
- Status: draft
- Last updated: {args.today}
- Related: `docs/PROJECT_PROFILE.md`, `ai-workflow/memory/active/<branch>/state.json`, `ai-workflow/memory/active/<branch>/sessions`, `ai-workflow/memory/active/<branch>/backlog`

## 1. Adoption mode

- Selected adoption mode: `{args.adoption_mode}`
- Summary:
- {mode_summary}

## 2. Generated files

- [docs/PROJECT_PROFILE.md](../docs/PROJECT_PROFILE.md)
- [ai-workflow/memory/active/<branch>/state.json](./memory/active/state.json)
- [ai-workflow/memory/active/<branch>/sessions](./memory/active/session_handoff.md)
- [ai-workflow/memory/active/<branch>/backlog](./memory/active/work_backlog.md)
- [ai-workflow/memory/active/<branch>/backlog/{args.today}.md](./memory/active/backlog/{args.today}.md)
{generated_assessment}

## 3. Core documents

{core_docs}

## 4. Harness overlays

{harness_lines}

## 5. What to do right after adoption

1. Fill `PROJECT_PROFILE.md` with the project's real purpose, commands, and verification rules.
2. Update `state.json`, `session_handoff.md`, and today's backlog to match the work actually in progress.
3. In existing-project mode, check the inferred values in `repository_assessment.md` against the real repository rules and correct them.
4. If a harness was selected, review the generated overlay files against that harness's execution paths.
5. Decide how far to adopt the standard skills/MCP from the `core/` documents.

## 6. Language and context principles

- Write user-facing work reports, status summaries, and handoff/backlog updates in Korean by default.
- Keep code, commands, file paths, configuration keys, and external product names verbatim.
- Handle internal reasoning and intermediate classification however is most efficient, and give the user only the conclusion.
- Keep only the facts the next session needs in the handoff and backlog, so context does not pile up.

## 7. Configured project document paths

- Documentation home: `{context['doc_home']}`
- Operations docs: `{context['operations_dir']}`
- Backlog location: `{context['backlog_dir']}`
- Session handoff: `{context['session_doc_path']}`
- Environment records: `{context['environment_dir']}`

## Read next

- Project profile: [../docs/PROJECT_PROFILE.md](../docs/PROJECT_PROFILE.md)
- Quick state summary: [./memory/active/state.json](./memory/active/state.json)
- Session handoff: [./memory/active/session_handoff.md](./memory/active/session_handoff.md)
- Work backlog index: [./memory/active/work_backlog.md](./memory/active/work_backlog.md)
"""


def load_template(name: str) -> str:
    template_path = SOURCE_ROOT / "templates" / name
    if not template_path.exists():
        return f"MISSING TEMPLATE: {name}"
    return template_path.read_text(encoding="utf-8")


def render_project_profile(args: argparse.Namespace, context: dict[str, object]) -> str:
    content = load_template("project_workflow_profile_template.md")
    install_command = _value_or_inferred(args.install_command, str(context["install_command"]))
    run_command = _value_or_inferred(args.run_command, str(context["run_command"]))
    quick_test_command = _value_or_inferred(
        args.quick_test_command, str(context["quick_test_command"])
    )
    isolated_test_command = _value_or_inferred(
        args.isolated_test_command, str(context["isolated_test_command"])
    )
    smoke_check_command = _value_or_inferred(
        args.smoke_check_command, str(context["smoke_check_command"])
    )

    replacements = {
        "<Project Name>": args.project_name,
        "<핵심 사용자 가치 및 목표>": _value_or_inferred(
            args.project_purpose, "TODO: 프로젝트 목적 정리"
        ),
        "<협업 부서 및 담당자>": _value_or_inferred(
            args.stakeholders, "TODO: 주요 이해관계자 정리"
        ),
        "<README.md>": str(context["doc_home"]),
        "<docs/operations/>": str(context["operations_dir"]),
        "<ai-workflow/memory/backlog/>": str(context["backlog_dir"]),
        "<ai-workflow/memory/session_handoff.md>": str(context["session_doc_path"]),
        "<ai-workflow/memory/repository_assessment.md>": str(context["environment_dir"]),
        "<설치 및 가상환경 구성 명령>": install_command,
        "<어플리케이션 실행 명령>": run_command,
        "<단위 테스트 및 Lint 명령>": quick_test_command,
        "<Docker 또는 독립 환경 테스트 명령>": isolated_test_command,
        "<상태 체크 및 E2E 확인 명령>": smoke_check_command,
        "YYYY-MM-DD": args.today,
    }
    for key, val in replacements.items():
        content = content.replace(key, val)
    return content


def render_session_handoff(args: argparse.Namespace, context: dict[str, object]) -> str:
    content = load_template("session_handoff_template.md")

    current_focus = "TODO: Summarize the current session focus."
    in_progress = f"{args.initial_task_id} {args.initial_task_name}"
    blocked = "N/A"
    completed = "N/A"
    key_change = "Initial workflow docs generated."
    next_action = "Review and refine generated workflow docs."
    risk_or_blocker = "N/A"

    if args.adoption_mode == "existing":
        stack_labels = context.get("stack_labels") or []
        if len(stack_labels) > 1:
            stack_summary = (
                f"inferred primary stack: {context['primary_stack']}; "
                f"all detected stacks: {', '.join(stack_labels)}"
            )
        else:
            stack_summary = f"inferred primary stack: {context['primary_stack']}"
        current_focus = f"Existing codebase onboarding completed; {stack_summary}."
        completed = "Repository scan completed"
        key_change = "Generated initial workflow docs from the existing repository scan."
        next_action = "Validate generated profile, handoff, and backlog against the repository."

    replacements = {
        "<CURRENT_FOCUS>": current_focus,
        "<IN_PROGRESS_ITEM>": in_progress,
        "<BLOCKED_ITEM>": blocked,
        "<DONE_ITEM>": completed,
        "<KEY_CHANGE>": key_change,
        "<NEXT_ACTION>": next_action,
        "<RISK_OR_BLOCKER>": risk_or_blocker,
        "YYYY-MM-DD": args.today,
    }
    for key, val in replacements.items():
        content = content.replace(key, val)
    return content


def render_backlog_index(args: argparse.Namespace) -> str:
    content = load_template("work_backlog_template.md")
    replacements = {
        "YYYY-MM-DD": args.today,
    }
    for key, val in replacements.items():
        content = content.replace(key, val)
    return content


#: 옛 기본값. 이 값이 그대로 오면 "사용자가 고른 것" 이 아니라 "안 골랐다" 로 읽는다.
_LEGACY_INITIAL_TASK_ID = "TASK-001"


def initial_task_id(args: argparse.Namespace) -> str:
    """씨앗 task 의 ID. 사용자가 준 값이 있으면 그것, 없으면 **파생**한다.

    기본값이 `TASK-001` 이었는데 그것은 `project_docs.TASK_ID_PATTERN`
    (`TASK-YYYY-MM-DD-<slug>-NNN`)과 **맞지 않는다** — 즉 bootstrap 이 심는
    씨앗 task 를 kit 자신의 파서가 못 읽었다 (TASK-2026-08-24-main-003).
    날짜와 slug 에서 파생해 처음부터 유효한 ID 를 심는다.
    """
    explicit = getattr(args, "initial_task_id", None)
    if explicit and explicit != _LEGACY_INITIAL_TASK_ID:
        return explicit
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", str(args.project_slug)).strip("-") or "main"
    return f"TASK-{args.today}-{slug}-001"


def render_daily_backlog(args: argparse.Namespace, context: dict[str, object]) -> str:
    """daily backlog **index** (v0.14.0+ append-only layout).

    예전에는 `daily_backlog_template.md`(v0.14.0 **이전** 레이아웃)를 읽어
    치환했다. 그 결과 새 프로젝트는 첫날부터 어긋난 파일을 받았다
    (TASK-2026-08-24-main-003):

    - **표기가 갈렸다** — bootstrap 은 한국어 라벨을, 도구(`task_label`)는 영어를
      썼다. 같은 프로젝트 안에서 두 표기가 동시에 생겼다.
    - **레이아웃이 겹쳤다** — 파일 머리에 임베드 task(`## 1. TASK-XXX` + 계획/
      실행/검증 절)가 있고, `wk backlog-update` 는 그 아래에 append-only 인덱스
      항목을 덧붙인다. 한 파일에 두 형식이 쌓이고 유령 task 가 남았다.

    그래서 템플릿을 읽지 않고 **도구와 같은 정본 작성기로 조립한다**
    (`workflow_writes.render_daily_backlog_header` / `daily_index_entry_lines`).
    사본을 두면 갈라진다 — 이 결함이 바로 그 사본의 결과였다.
    """
    from workflow_kit.common.workflow_writes import (  # noqa: PLC0415
        daily_index_entry_lines,
        render_daily_backlog_header,
    )

    # 머리말은 파일 이름(stem = 날짜)만 쓴다. context 를 뒤지지 않고 args 에서
    # 곧장 만든다 — 있지도 않은 키를 or 로 받으면 "폴백이 있다" 는 거짓말이 된다.
    lines = render_daily_backlog_header(backlog_path=Path(f"{args.today}.md"))
    lines += daily_index_entry_lines(
        task_id=initial_task_id(args),
        title=args.initial_task_name,
        kind="generic",
        status=args.initial_task_status,
    )
    lines.append("")
    return "\n".join(lines)


def render_initial_task_file(args: argparse.Namespace) -> str:
    """씨앗 task 의 **per-task SSOT 파일** (v0.14.0+ layout).

    예전에는 이 파일이 아예 없었다 — 임베드 task 가 daily 파일 안에만 있었고,
    그것은 `TASK_ID_PATTERN` 과도 안 맞아 파서가 세지 않았다. 인덱스는 task 를
    가리키는데 가리켜진 파일이 없는 상태였다.

    본문은 도구가 쓰는 것과 **같은 라벨 레지스트리**(`task_label`)에서 나온다.
    """
    from workflow_kit.common.project_docs import task_label  # noqa: PLC0415
    from workflow_kit.common.workflow_writes import render_task_file  # noqa: PLC0415

    task_id = initial_task_id(args)
    body = [
        "## 📝 Description",
        "",
        f"- {task_label('status')}: {args.initial_task_status}",
        f"- {task_label('priority')}: {args.initial_priority}",
        f"- {task_label('request_date')}: {args.today}",
        f"- {task_label('owner')}: {args.owner}",
        f"- {task_label('summary')}: {args.initial_task_name}",
        f"- {task_label('done_criteria')}: TODO — 검증 방법을 구체적으로 적는다",
        "",
        "## 🛠️ Implementation / Content",
        "",
        f"- {task_label('progress')}: `{args.today}` bootstrap 초기 생성",
        f"- {task_label('next_step')}:",
        f"- {task_label('risks')}:",
        "",
        "## ✅ Outcome",
        "",
        f"- {task_label('result')}:",
        f"- {task_label('validation')}:",
        f"- {task_label('follow_up')}:",
        "",
    ]
    lines = render_task_file(
        task_id=task_id,
        title=args.initial_task_name,
        status=args.initial_task_status,
        created_at=args.today,
        kind="generic",
        source_anchor=f"generic-{task_id.lower()}",
        source_path=f"backlog/{args.today}.md",
        body_lines=body,
    )
    return "\n".join(lines)


def render_project_status_assessment(args: argparse.Namespace) -> str:
    content = load_template("project_status_assessment_template.md")
    return content.replace("<Project Name>", args.project_name).replace(
        "<YYYY-MM-DD>", args.today
    )


def render_assessment(args: argparse.Namespace, context: dict[str, object]) -> str:
    if args.adoption_mode != "existing":
        return ""
    top_entries = ", ".join(context["top_level_entries"]) or "none"
    docs_dirs = ", ".join(context["docs_dirs"]) or "none"
    test_dirs = ", ".join(context["test_dirs"]) or "none"
    source_dirs = ", ".join(context["source_dirs"]) or "none"
    stack_labels = ", ".join(context["stack_labels"]) or "none"
    scripts = ", ".join(sorted(context["package_scripts"])) or "none"
    sample_paths = "\n".join(f"- `{item}`" for item in context.get("sample_paths", []))
    return f"""# Repository Assessment

- Purpose: quickly diagnose the current codebase and document structure before adopting the standard AI workflow.
- Scope: repository structure, inferred stack, document locations, traces of tests, initial adoption points
- Audience: developer, operator, AI agent, project onboarding owner
- Status: draft
- Last updated: {args.today}
- Related: `./PROJECT_PROFILE.md`, `./session_handoff.md`, `../core/workflow_adoption_entrypoints.md`

## 1. Summary

- Analyzed project:
- `{args.project_name}`
- Analysis mode:
- `existing`
- Inferred primary stack:
- `{context['primary_stack']}`
- Detected stack labels:
- `{stack_labels}`

## 2. Repository structure observations

- Top-level entries:
- `{top_entries}`
- Source directory candidates:
- `{source_dirs}`
- Document directory candidates:
- `{docs_dirs}`
- Test directory candidates:
- `{test_dirs}`

## 3. Inferred commands

- Install:
- `{context['install_command']}`
- Run locally:
- `{context['run_command']}`
- Quick test:
- `{context['quick_test_command']}`
- Isolated test:
- `{context['isolated_test_command']}`
- Smoke check:
- `{context['smoke_check_command']}`

## 4. Package scripts and sample paths

- Package scripts:
- `{scripts}`
- Sample paths seen during analysis:
{sample_paths or '- none'}

## 5. Draft adoption plan

- Recommended documentation home:
- `{context['doc_home']}`
- Recommended operations docs:
- `{context['operations_dir']}`
- Recommended backlog location:
- `{context['backlog_dir']}`
- Recommended session handoff:
- `{context['session_doc_path']}`

## 6. Next steps from the automated analysis

- Check that the inferred commands match the real operational commands.
- If a document system already exists, decide whether to follow its operations-doc location or split into a separate workflow directory.
- If the quick-test and smoke-check criteria are weak, strengthen the verification rules in the profile document first.

## Read next

- Project profile: [./PROJECT_PROFILE.md](./PROJECT_PROFILE.md)
- Session handoff: [./session_handoff.md](./session_handoff.md)
- Adoption branch guide: [../core/workflow_adoption_entrypoints.md](../core/workflow_adoption_entrypoints.md)
"""


__all__ = [
    "SOURCE_ROOT",
    "load_template",
    "render_assessment",
    "render_backlog_index",
    "render_daily_backlog",
    "render_initial_task_file",
    "render_project_profile",
    "render_project_status_assessment",
    "render_readme",
    "render_session_handoff",
]
