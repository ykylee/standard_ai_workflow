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


def render_daily_backlog(args: argparse.Namespace, context: dict[str, object]) -> str:
    content = load_template("daily_backlog_template.md")

    task_goal = "TODO: 작업 목표"
    done_criteria = "TODO: 완료 기준"
    progress = f"`{args.today} 09:00` bootstrap 초기 생성"

    if args.adoption_mode == "existing":
        task_goal = "기존 프로젝트 분석 및 워크플로우 도입"
        done_criteria = "profile/handoff/backlog 초안 생성 및 검토 완료"
        progress = f"`{args.today} 09:00` 기존 저장소 분석 및 문서 생성 완료"

    replacements = {
        "TASK-XXX": args.initial_task_id,
        "<작업명>": args.initial_task_name,
        "planned | in_progress | done | blocked": args.initial_task_status,
        "high | medium | low": args.initial_priority,
        "<name>": args.owner,
        "<file_paths>": f"{context['session_doc_path']}, {context['backlog_dir']}",
        "TODO: 작업 목표": task_goal,
        "TODO: 완료 기준": done_criteria,
        "YYYY-MM-DD": args.today,
    }
    for key, val in replacements.items():
        content = content.replace(key, val)
    content = content.replace("- 진행 현황:", f"- 진행 현황: {progress}")
    return content


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
    "render_project_profile",
    "render_project_status_assessment",
    "render_readme",
    "render_session_handoff",
]
