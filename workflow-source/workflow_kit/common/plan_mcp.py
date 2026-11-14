"""MCP 도구 `plan_inbox` (read-only) · `plan_import` (write) — 워크벤치 스펙 §8.3.

- `plan_inbox` 는 받은편지함을 :func:`plan_responses.inbox_census` 로만 센다 (ADR-032 결정 16). 파일마다
  응답자 · 시각 · 자격 단계만 싣고 주석 본문은 싣지 않는다.
- `plan_import` 는 CLI `plan-import` 를 **같은 인터프리터의 하위 프로세스**로 부른다 — 출력 계약(family
  `plan_import`)이 CLI 와 글자 그대로 같다. stdio MCP 서버는 표준 출력이 전송로라 같은 프로세스에서
  CLI 의 출력을 가로채지 않는다.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from workflow_kit.common import plan_claims, plan_responses, plan_tasks
from workflow_kit.common.errors import build_error_result
from workflow_kit.common.paths import (
    branch_for_workspace,
    discover_project_profile_path,
    project_workspace_root,
    workflow_branch_dir,
)
from workflow_kit.common.schemas import PlanInboxFile, PlanInboxOutput, PlanInboxSourceContext
from workflow_kit.common.schemas.base import Status

PLAN_IMPORT_TIMEOUT_S = 120


def _profile(workspace_root: str | None) -> Path | None:
    start = Path(workspace_root or ".").resolve()
    found = discover_project_profile_path(start)
    return found.resolve() if found else None


def _missing_profile(tool_version: str, context: dict[str, Any]) -> dict[str, Any]:
    return build_error_result(
        tool_version=tool_version,
        error="PROJECT_PROFILE.md 를 workspace_root 상위에서 찾지 못했다.",
        error_code="missing_required_document",
        warnings=["workspace_root 에 workflow_kit 를 쓰는 저장소의 경로를 준다."],
        source_context=context,
    )


def plan_inbox_payload(*, workspace_root: str | None = None, task_id: str | None = None,
                       tool_version: str) -> dict[str, Any]:
    profile = _profile(workspace_root)
    if profile is None:
        return _missing_profile(tool_version, {"task_id": task_id})
    workspace = project_workspace_root(profile)
    branch_dir = workflow_branch_dir(profile)
    census = plan_responses.inbox_census(branch_dir)
    tasks_dir = branch_dir / "backlog" / "tasks"
    task_ids = [task_id] if task_id else sorted(census.files)
    files: list[PlanInboxFile] = []
    for tid in task_ids:
        task = plan_tasks.read_task_plan(tasks_dir / f"{tid}.md")
        for path in census.paths(tid):
            stage: int | None
            if task is None:
                parsed = plan_responses.read_response(path)
                stage, reason = 0, "task 파일이 이 브랜치에 없거나 읽을 수 없다 — 자격을 볼 수 없다"
            else:
                parsed, verdict = plan_responses.judge(
                    path, task.plan, tid, plan_has_errors=plan_claims.has_error_rules(task.plan))
                stage, reason = verdict.stage, verdict.reason
            files.append(PlanInboxFile(task=tid, name=path.name, responder=parsed.responder,
                                       received_at=parsed.received_at, stage=stage, reason=reason))
    warnings = [note for note in (census.warning(), census.layout_warning()) if note]
    pending = census.pending if not task_id else ({task_id: census.count(task_id)} if census.count(task_id) else {})
    output = PlanInboxOutput(
        status=Status.WARNING if warnings else Status.OK,
        tool_version=tool_version,
        warnings=warnings,
        pending=pending,
        files=files,
        unknown=list(census.unknown),
        layout_problem=census.layout_problem,
        source_context=PlanInboxSourceContext(branch=branch_for_workspace(workspace), task_id=task_id),
    )
    return output.model_dump(mode="json")


def plan_import_payload(*, workspace_root: str | None = None, task_id: str | None = None,
                        discard: str | None = None, reason: str | None = None, response: str | None = None,
                        apply: bool = False, tool_version: str) -> dict[str, Any]:
    context: dict[str, Any] = {"task_id": task_id, "discard": discard, "apply": bool(apply)}
    profile = _profile(workspace_root)
    if profile is None:
        return _missing_profile(tool_version, context)
    argv = [sys.executable, "-m", "workflow_kit", "plan-import", "--project-profile-path", str(profile)]
    for flag, value in (("--task", task_id), ("--discard", discard), ("--reason", reason), ("--response", response)):
        if value is not None:
            argv.extend([flag, str(value)])
    if apply:
        argv.append("--apply")
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    # 서버 프로세스가 workflow_kit 를 찾은 경로를 그대로 넘긴다 — 소스 실행(runner 가 sys.path 에 넣은 경우)도 같은 패키지를 쓴다.
    env["PYTHONPATH"] = os.pathsep.join(entry for entry in sys.path if entry)
    try:
        proc = subprocess.run(argv, capture_output=True, encoding="utf-8", errors="replace", check=False,
                              env=env, cwd=str(project_workspace_root(profile)), timeout=PLAN_IMPORT_TIMEOUT_S)
    except subprocess.TimeoutExpired:
        return build_error_result(tool_version=tool_version, error="plan-import 가 제한 시간 안에 끝나지 않았다.",
                                  error_code="plan_import_timeout", warnings=[], source_context=context)
    try:
        result = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return build_error_result(
            tool_version=tool_version, error="plan-import 의 출력이 JSON 이 아니다.", error_code="plan_import_bad_output",
            warnings=[line for line in proc.stderr.splitlines()[-3:] if line.strip()],
            source_context=context | {"returncode": proc.returncode})
    return result if isinstance(result, dict) else build_error_result(
        tool_version=tool_version, error="plan-import 의 출력이 object 가 아니다.", error_code="plan_import_bad_output",
        warnings=[], source_context=context)
