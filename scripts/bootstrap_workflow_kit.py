#!/usr/bin/env python3
"""Bootstrap a reusable standard AI workflow kit into a target repository."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from workflow_kit.common.workflow_state import build_workflow_state_payload

DEFAULT_CORE_DOCS = [
    "global_workflow_standard.md",
    "workflow_skill_catalog.md",
    "workflow_mcp_candidate_catalog.md",
    "workflow_agent_topology.md",
    "output_schema_guide.md",
    "workflow_adoption_entrypoints.md",
    "workflow_harness_distribution.md",
]
DEFAULT_CORE_SUPPORT_PATHS = [
    "core/existing_project_onboarding_contract.md",
    "core/project_status_assessment.md",
    "core/prototype_promotion_scope.md",
    "core/read_only_mcp_transport_promotion.md",
    "core/workflow_release_spec.md",
    "core/workflow_configuration_layers.md",
    "core/workflow_global_injection_policy.md",
    "core/workflow_kit_roadmap.md",
    "core/session_start_skill_spec.md",
    "core/backlog_update_skill_spec.md",
    "core/doc_sync_skill_spec.md",
    "core/merge_doc_reconcile_skill_spec.md",
    "core/validation_plan_skill_spec.md",
    "core/code_index_update_skill_spec.md",
    "templates/project_workflow_profile_template.md",
    "templates/session_handoff_template.md",
    "templates/pilot_candidate_checklist.md",
    "templates/pilot_adoption_record_template.md",
    "schemas/output_sample_contracts.json",
    "schemas/generated_output_schemas.json",
    "examples/output_samples",
    "examples/README.md",
    "examples/end_to_end_skill_demo.md",
    "examples/end_to_end_mcp_demo.md",
    "examples/bootstrap_output_samples.md",
    "examples/pilot_adoption_open_git_client_example.md",
    "skills/README.md",
    "skills/prototype_layout.md",
    "skills/session-start/SKILL.md",
    "skills/backlog-update/SKILL.md",
    "skills/doc-sync/SKILL.md",
    "skills/merge-doc-reconcile/SKILL.md",
    "skills/validation-plan/SKILL.md",
    "skills/code-index-update/SKILL.md",
    "mcp/README.md",
    "mcp/prototype_layout.md",
    "mcp/read_only_bundle.md",
    "mcp/latest-backlog/MCP.md",
    "mcp/check-doc-metadata/MCP.md",
    "mcp/check-doc-links/MCP.md",
    "mcp/create-backlog-entry/MCP.md",
    "mcp/suggest-impacted-docs/MCP.md",
    "mcp/check-quickstart-stale-links/MCP.md",
    "tests/README.md",
    "tests/check_docs.py",
    "tests/check_bootstrap.py",
    "tests/check_validation_plan.py",
    "tests/check_code_index_update.py",
    "tests/check_existing_project_onboarding.py",
    "tests/check_quickstart_stale_links.py",
    "harnesses/_template/README.md",
    "harnesses/README.md",
    "harnesses/codex/apply_guide.md",
    "harnesses/opencode/apply_guide.md",
    "global-snippets/README.md",
    "scripts/README.md",
    "scripts/apply_harness_update.py",
    "scripts/bootstrap_workflow_kit.py",
    "scripts/export_harness_package.py",
    "scripts/generate_workflow_state.py",
    "scripts/scaffold_harness.py",
    "scripts/run_demo_workflow.py",
    "scripts/run_existing_project_onboarding.py",
    "workflow_kit/README.md",
]
IGNORED_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".idea",
    ".vscode",
    "node_modules",
    ".next",
    ".turbo",
    "dist",
    "build",
    "coverage",
    "__pycache__",
    ".venv",
    "venv",
}
SUPPORTED_HARNESSES = ("codex", "opencode")


@dataclass(frozen=True)
class Paths:
    target_root: Path
    kit_root: Path
    core_dir: Path
    project_dir: Path
    backlog_dir: Path
    readme_path: Path
    profile_path: Path
    state_path: Path
    handoff_path: Path
    backlog_index_path: Path
    daily_backlog_path: Path
    assessment_path: Path


@dataclass(frozen=True)
class HarnessDefinition:
    name: str
    description: str


def parse_args() -> argparse.Namespace:
    today = date.today().isoformat()
    parser = argparse.ArgumentParser(
        description="Scaffold a standard AI workflow kit into a target repository."
    )
    parser.add_argument("--target-root", default=".")
    parser.add_argument("--kit-dir", default="ai-workflow")
    parser.add_argument(
        "--adoption-mode",
        choices=["new", "existing"],
        default="new",
        help="Choose whether the target is a new project or an existing codebase.",
    )
    parser.add_argument("--project-slug", required=True)
    parser.add_argument("--project-name", required=True)
    parser.add_argument(
        "--project-purpose",
        default="TODO: 프로젝트 목적과 핵심 사용자 가치를 한두 문장으로 정리한다.",
    )
    parser.add_argument(
        "--stakeholders",
        default="TODO: 주요 이해관계자 목록을 정리한다.",
    )
    parser.add_argument("--doc-home", default="docs/README.md")
    parser.add_argument("--operations-dir", default="docs/operations/")
    parser.add_argument("--backlog-dir", default="docs/operations/backlog/")
    parser.add_argument("--session-doc-path", default="docs/operations/session_handoff.md")
    parser.add_argument("--environment-dir", default="docs/operations/environments/")
    parser.add_argument("--install-command", default="TODO: 설치 명령 입력")
    parser.add_argument("--run-command", default="TODO: 로컬 실행 명령 입력")
    parser.add_argument("--quick-test-command", default="TODO: 빠른 테스트 명령 입력")
    parser.add_argument("--isolated-test-command", default="TODO: 격리 테스트 명령 입력")
    parser.add_argument("--smoke-check-command", default="TODO: 실행 확인 명령 입력")
    parser.add_argument("--today", default=today)
    parser.add_argument("--initial-task-id", default="TASK-001")
    parser.add_argument("--initial-task-name", default="표준 AI 워크플로우 초기 도입")
    parser.add_argument(
        "--initial-task-status",
        choices=["planned", "in_progress", "blocked", "done"],
        default="planned",
    )
    parser.add_argument("--initial-priority", default="high")
    parser.add_argument("--owner", default="TODO")
    parser.add_argument("--host-name", default="TODO")
    parser.add_argument("--host-ip", default="TODO")
    parser.add_argument(
        "--harness",
        action="append",
        choices=list(SUPPORTED_HARNESSES),
        dest="harnesses",
        default=[],
        help="Generate harness-specific overlay files for the selected target.",
    )
    parser.add_argument(
        "--copy-core-docs",
        action="store_true",
        help="Copy selected core docs into the generated kit directory.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing generated files when the destination already exists.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the generation plan without writing files.",
    )
    return parser.parse_args()


def make_paths(args: argparse.Namespace) -> Paths:
    target_root = Path(args.target_root).resolve()
    kit_root = target_root / args.kit_dir
    project_dir = kit_root / "project"
    backlog_dir = project_dir / "backlog"
    return Paths(
        target_root=target_root,
        kit_root=kit_root,
        core_dir=kit_root / "core",
        project_dir=project_dir,
        backlog_dir=backlog_dir,
        readme_path=kit_root / "README.md",
        profile_path=project_dir / "project_workflow_profile.md",
        state_path=project_dir / "state.json",
        handoff_path=project_dir / "session_handoff.md",
        backlog_index_path=project_dir / "work_backlog.md",
        daily_backlog_path=backlog_dir / f"{args.today}.md",
        assessment_path=project_dir / "repository_assessment.md",
    )


def write_text(path: Path, content: str, *, force: bool) -> None:
    if path.exists() and not force:
        raise FileExistsError(f"Destination already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def copy_core_docs(paths: Paths, *, force: bool) -> list[str]:
    copied: list[str] = []
    paths.core_dir.mkdir(parents=True, exist_ok=True)
    for name in DEFAULT_CORE_DOCS:
        source = REPO_ROOT / "core" / name
        destination = paths.core_dir / name
        if destination.exists() and not force:
            raise FileExistsError(f"Destination already exists: {destination}")
        shutil.copyfile(source, destination)
        copied.append(str(destination))
    for raw_relative_path in DEFAULT_CORE_SUPPORT_PATHS:
        relative_path = Path(raw_relative_path)
        source = REPO_ROOT / relative_path
        destination = paths.kit_root / relative_path
        if source.is_dir():
            for file_path in sorted(source.rglob("*")):
                if not file_path.is_file():
                    continue
                nested_relative = file_path.relative_to(REPO_ROOT)
                nested_destination = paths.kit_root / nested_relative
                if nested_destination.exists() and not force:
                    raise FileExistsError(f"Destination already exists: {nested_destination}")
                nested_destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(file_path, nested_destination)
            continue
        if destination.exists() and not force:
            raise FileExistsError(f"Destination already exists: {destination}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
    return copied


def rel(path: Path, base: Path) -> str:
    return path.relative_to(base).as_posix()


def selected_harnesses(args: argparse.Namespace) -> list[str]:
    return sorted(dict.fromkeys(args.harnesses))


HARNESS_DEFINITIONS = {
    "codex": HarnessDefinition(
        name="codex",
        description="Generate AGENTS.md and a Codex config example.",
    ),
    "opencode": HarnessDefinition(
        name="opencode",
        description="Generate opencode.json and project-local OpenCode overlays.",
    ),
}


def global_snippet_sources() -> dict[str, dict[str, str]]:
    return {
        "codex": {
            "readme": str((REPO_ROOT / "global-snippets" / "codex" / "README.md").resolve()),
            "snippet": str((REPO_ROOT / "global-snippets" / "codex" / "config.toml.snippet").resolve()),
            "target": "~/.codex/config.toml",
            "policy": "additive_only",
        },
        "opencode": {
            "readme": str((REPO_ROOT / "global-snippets" / "opencode" / "README.md").resolve()),
            "snippet": str((REPO_ROOT / "global-snippets" / "opencode" / "opencode.global.jsonc").resolve()),
            "target": "~/.config/opencode/opencode.json",
            "policy": "additive_only",
        },
    }


def iter_repo_files(root: Path, *, max_depth: int = 3) -> list[Path]:
    results: list[Path] = []
    for current_root, dirs, files in os.walk(root):
        current_path = Path(current_root)
        try:
            relative = current_path.relative_to(root)
            depth = len(relative.parts)
        except ValueError:
            depth = 0
        dirs[:] = sorted(
            name
            for name in dirs
            if name not in IGNORED_DIRS and depth < max_depth
        )
        for file_name in sorted(files):
            results.append(current_path / file_name)
    return results


def detect_package_scripts(target_root: Path) -> dict[str, str]:
    package_json = target_root / "package.json"
    if not package_json.exists():
        return {}
    try:
        payload = json.loads(package_json.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    scripts = payload.get("scripts")
    if isinstance(scripts, dict):
        return {str(key): str(value) for key, value in scripts.items()}
    return {}


def guess_run_command(target_root: Path, package_scripts: dict[str, str]) -> str:
    for script_name in ("dev", "start", "serve"):
        if script_name in package_scripts:
            return f"npm run {script_name}"
    for candidate in ("app/main.py", "main.py"):
        if (target_root / candidate).exists():
            return f"python {candidate}"
    return "TODO: 로컬 실행 명령 입력"


def infer_project_context(args: argparse.Namespace, paths: Paths) -> dict[str, object]:
    if args.adoption_mode == "new":
        return {
            "top_level_entries": [],
            "source_dirs": [],
            "docs_dirs": [],
            "test_dirs": [],
            "stack_labels": [],
            "primary_stack": "unspecified",
            "package_scripts": {},
            "existing_docs_detected": False,
            "has_existing_tests": False,
            "doc_home": args.doc_home,
            "operations_dir": args.operations_dir,
            "backlog_dir": args.backlog_dir,
            "session_doc_path": args.session_doc_path,
            "environment_dir": args.environment_dir,
            "install_command": args.install_command,
            "run_command": args.run_command,
            "quick_test_command": args.quick_test_command,
            "isolated_test_command": args.isolated_test_command,
            "smoke_check_command": args.smoke_check_command,
            "analysis_summary": [
                "신규 프로젝트 모드이므로 기존 코드베이스 분석은 수행하지 않았다.",
                "프로젝트 특화 명령과 문서 구조는 생성된 profile 문서에서 직접 채워야 한다.",
            ],
        }

    files = iter_repo_files(paths.target_root)
    rel_files = [path.relative_to(paths.target_root).as_posix() for path in files]
    top_level_entries = sorted(
        path.name for path in paths.target_root.iterdir() if path.name != args.kit_dir
    )
    docs_dirs = sorted(
        {
            name
            for name in ("docs", "doc", "wiki", "handbook")
            if (paths.target_root / name).exists()
        }
    )
    test_dirs = sorted(
        {
            name
            for name in ("tests", "test", "spec", "__tests__")
            if (paths.target_root / name).exists()
        }
    )
    source_dirs = sorted(
        {
            name
            for name in ("src", "app", "apps", "services", "packages", "lib")
            if (paths.target_root / name).exists()
        }
    )

    stack_labels: list[str] = []
    if (paths.target_root / "package.json").exists():
        stack_labels.append("node")
    if (paths.target_root / "pyproject.toml").exists() or (paths.target_root / "requirements.txt").exists():
        stack_labels.append("python")
    if (paths.target_root / "Cargo.toml").exists():
        stack_labels.append("rust")
    if (paths.target_root / "go.mod").exists():
        stack_labels.append("go")
    if (paths.target_root / "Gemfile").exists():
        stack_labels.append("ruby")
    primary_stack = stack_labels[0] if stack_labels else "unknown"

    package_scripts = detect_package_scripts(paths.target_root)

    if docs_dirs and (paths.target_root / docs_dirs[0] / "README.md").exists():
        doc_home = f"{docs_dirs[0]}/README.md"
    elif (paths.target_root / "README.md").exists():
        doc_home = "README.md"
    else:
        doc_home = args.doc_home

    operations_dir = f"{docs_dirs[0]}/operations/" if docs_dirs else args.operations_dir
    backlog_dir = f"{operations_dir.rstrip('/')}/backlog/"
    session_doc_path = f"{operations_dir.rstrip('/')}/session_handoff.md"
    environment_dir = f"{operations_dir.rstrip('/')}/environments/"

    if primary_stack == "node":
        install_command = "npm install"
        run_command = guess_run_command(paths.target_root, package_scripts)
        quick_test_command = (
            "npm test"
            if "test" in package_scripts
            else ("npm run lint" if "lint" in package_scripts else "TODO: 빠른 테스트 명령 입력")
        )
        isolated_test_command = (
            "npm run test:unit"
            if "test:unit" in package_scripts
            else ("npm run test:ci" if "test:ci" in package_scripts else "TODO: 격리 테스트 명령 입력")
        )
        smoke_check_command = (
            "npm run test:smoke"
            if "test:smoke" in package_scripts
            else ("npm run smoke" if "smoke" in package_scripts else "TODO: 실행 확인 명령 입력")
        )
    elif primary_stack == "python":
        install_command = "uv sync" if (paths.target_root / "uv.lock").exists() else (
            "pip install -r requirements.txt"
            if (paths.target_root / "requirements.txt").exists()
            else "pip install -e ."
        )
        run_command = guess_run_command(paths.target_root, package_scripts)
        quick_test_command = "pytest -q" if test_dirs else "TODO: 빠른 테스트 명령 입력"
        isolated_test_command = (
            f"pytest {test_dirs[0]} -q" if test_dirs else "TODO: 격리 테스트 명령 입력"
        )
        smoke_check_command = "TODO: 실행 확인 명령 입력"
    elif primary_stack == "rust":
        install_command = "cargo fetch"
        run_command = "cargo run"
        quick_test_command = "cargo test"
        isolated_test_command = "cargo test --lib"
        smoke_check_command = "TODO: 실행 확인 명령 입력"
    elif primary_stack == "go":
        install_command = "go mod download"
        run_command = "go run ./..."
        quick_test_command = "go test ./..."
        isolated_test_command = "go test ./... -run TestSmoke"
        smoke_check_command = "TODO: 실행 확인 명령 입력"
    else:
        install_command = args.install_command
        run_command = args.run_command
        quick_test_command = args.quick_test_command
        isolated_test_command = args.isolated_test_command
        smoke_check_command = args.smoke_check_command

    analysis_summary = [
        f"상위 디렉터리 기준으로 `{', '.join(top_level_entries[:10])}` 구조를 확인했다." if top_level_entries else "상위 디렉터리 항목이 거의 비어 있다.",
        f"추정 기본 스택은 `{primary_stack}` 이며 감지된 스택 라벨은 `{', '.join(stack_labels) or '없음'}` 이다.",
        f"문서 디렉터리는 `{', '.join(docs_dirs) or '없음'}`, 테스트 디렉터리는 `{', '.join(test_dirs) or '없음'}` 으로 감지됐다.",
        f"package script 는 `{', '.join(sorted(package_scripts)[:8]) or '없음'}` 으로 확인됐다.",
    ]

    return {
        "top_level_entries": top_level_entries,
        "source_dirs": source_dirs,
        "docs_dirs": docs_dirs,
        "test_dirs": test_dirs,
        "stack_labels": stack_labels,
        "primary_stack": primary_stack,
        "package_scripts": package_scripts,
        "existing_docs_detected": bool(docs_dirs),
        "has_existing_tests": bool(test_dirs),
        "doc_home": doc_home,
        "operations_dir": operations_dir,
        "backlog_dir": backlog_dir,
        "session_doc_path": session_doc_path,
        "environment_dir": environment_dir,
        "install_command": install_command,
        "run_command": run_command,
        "quick_test_command": quick_test_command,
        "isolated_test_command": isolated_test_command,
        "smoke_check_command": smoke_check_command,
        "analysis_summary": analysis_summary,
        "sample_paths": rel_files[:20],
    }


def value_or_inferred(explicit: str, fallback: str) -> str:
    if explicit.startswith("TODO:"):
        return fallback
    return explicit


def render_readme(args: argparse.Namespace, context: dict[str, object]) -> str:
    if args.copy_core_docs:
        core_docs = "\n".join(
            f"- [core/{name}](./core/{name})" for name in DEFAULT_CORE_DOCS
        )
    else:
        core_docs = "- core 문서는 `--copy-core-docs` 옵션을 사용하면 함께 복사할 수 있다."
    generated_assessment = ""
    mode_summary = "신규 프로젝트용 기본 문서 세트를 생성했다."
    harness_lines = "\n".join(
        f"- `{name}` 하네스용 오버레이 파일 생성"
        for name in selected_harnesses(args)
    ) or "- 선택한 하네스 없음"
    if args.adoption_mode == "existing":
        generated_assessment = "- [project/repository_assessment.md](./project/repository_assessment.md)"
        mode_summary = "기존 프로젝트 분석 결과를 반영한 문서 초안과 평가 문서를 생성했다."
    return f"""# Standard AI Workflow Kit

- 문서 목적: `{args.project_name}` 저장소에 표준 AI 워크플로우 기본 문서 세트를 도입할 수 있도록 bootstrap 결과를 안내한다.
- 범위: 공통 코어 문서 위치, 프로젝트 상태 문서 세트, 도입 모드별 후속 작업
- 대상 독자: 개발자, 운영자, AI agent, 프로젝트 온보딩 담당자
- 상태: draft
- 최종 수정일: {args.today}
- 관련 문서: `./project/project_workflow_profile.md`, `./project/state.json`, `./project/session_handoff.md`, `./project/work_backlog.md`

## 1. 도입 모드

- 선택한 도입 모드: `{args.adoption_mode}`
- 요약:
- {mode_summary}

## 2. 생성된 파일

- [project/project_workflow_profile.md](./project/project_workflow_profile.md)
- [project/state.json](./project/state.json)
- [project/session_handoff.md](./project/session_handoff.md)
- [project/work_backlog.md](./project/work_backlog.md)
- [project/backlog/{args.today}.md](./project/backlog/{args.today}.md)
{generated_assessment}

## 3. 코어 문서

{core_docs}

## 4. 하네스 오버레이

{harness_lines}

## 5. 도입 직후 해야 할 일

1. `project_workflow_profile.md` 에 프로젝트 목적, 명령, 검증 규칙을 실제 값으로 채운다.
2. `state.json`, `session_handoff.md`, 오늘 날짜 backlog 를 현재 진행 작업 기준으로 갱신한다.
3. 기존 프로젝트 모드였다면 `repository_assessment.md` 의 추정값을 실제 저장소 규칙과 대조해 수정한다.
4. 선택한 하네스가 있으면 생성된 overlay 파일을 각 하네스 실행 경로에 맞게 검토한다.
5. 이후 표준 skill/MCP 도입 범위는 `core/` 문서를 기준으로 결정한다.

## 6. 언어와 컨텍스트 운영 원칙

- 사용자에게 직접 보이는 작업 보고, 상태 요약, handoff/backlog 갱신 문안은 기본적으로 한국어로 작성한다.
- 코드, 명령어, 파일 경로, 설정 key, 외부 시스템 고유 명칭은 필요할 때 원문 그대로 유지한다.
- 내부 사고 과정과 중간 분류는 모델이 가장 효율적인 형태로 처리하고, 사용자에게는 필요한 결론만 짧게 전달한다.
- handoff 와 backlog 에는 다음 세션에 필요한 핵심 사실만 남겨 불필요한 컨텍스트 누적을 줄인다.

## 7. 프로젝트 실제 문서 경로 설정값

- 문서 위키 홈: `{context['doc_home']}`
- 운영 문서 위치: `{context['operations_dir']}`
- 백로그 위치: `{context['backlog_dir']}`
- 세션 인계 문서 위치: `{context['session_doc_path']}`
- 환경 기록 위치: `{context['environment_dir']}`

## 다음에 읽을 문서

- 프로젝트 프로파일: [./project/project_workflow_profile.md](./project/project_workflow_profile.md)
- 빠른 상태 요약: [./project/state.json](./project/state.json)
- 세션 인계 문서: [./project/session_handoff.md](./project/session_handoff.md)
- 작업 백로그 인덱스: [./project/work_backlog.md](./project/work_backlog.md)
"""


def render_project_profile(args: argparse.Namespace, context: dict[str, object]) -> str:
    project_purpose = value_or_inferred(args.project_purpose, "TODO: 프로젝트 목적과 핵심 사용자 가치를 한두 문장으로 정리한다.")
    stakeholders = value_or_inferred(args.stakeholders, "TODO: 주요 이해관계자 목록을 정리한다.")
    install_command = value_or_inferred(args.install_command, str(context["install_command"]))
    run_command = value_or_inferred(args.run_command, str(context["run_command"]))
    quick_test_command = value_or_inferred(args.quick_test_command, str(context["quick_test_command"]))
    isolated_test_command = value_or_inferred(args.isolated_test_command, str(context["isolated_test_command"]))
    smoke_check_command = value_or_inferred(args.smoke_check_command, str(context["smoke_check_command"]))
    mode_note = (
        "기존 프로젝트 분석 결과를 바탕으로 초안 값을 채웠으므로, 실제 저장소 규칙과 다르면 즉시 수정해야 한다."
        if args.adoption_mode == "existing"
        else "신규 프로젝트 모드이므로 TODO 항목을 직접 채우는 것을 전제로 한다."
    )
    return f"""# Project Workflow Profile

- 문서 목적: 공통 표준 워크플로우를 `{args.project_name}` 저장소에 적용할 때 필요한 프로젝트 특화 규칙을 정리한다.
- 범위: 저장소 목적, 문서 구조, 기본 명령, 환경 기록 위치, 프로젝트 특화 검증 포인트, 예외 규칙
- 대상 독자: 개발자, 운영자, AI agent, 프로젝트 온보딩 담당자
- 상태: draft
- 최종 수정일: {args.today}
- 관련 문서: `../core/global_workflow_standard.md`, `./session_handoff.md`, `./work_backlog.md`

## 1. 프로젝트 개요

- 프로젝트명:
- `{args.project_name}`
- 프로젝트 목적:
- {project_purpose}
- 주요 이해관계자:
- {stakeholders}

## 2. 문서 구조

- 문서 위키 홈:
- `{context['doc_home']}`
- 운영 문서 위치:
- `{context['operations_dir']}`
- 백로그 위치:
- `{context['backlog_dir']}`
- 세션 인계 문서 위치:
- `{context['session_doc_path']}`
- 환경 기록 위치:
- `{context['environment_dir']}`

## 3. 기본 명령

- 설치:
- `{install_command}`
- 로컬 실행:
- `{run_command}`
- 빠른 테스트:
- `{quick_test_command}`
- 격리 테스트:
- `{isolated_test_command}`
- UI/API 실행 확인:
- `{smoke_check_command}`

## 4. 프로젝트 특화 검증 포인트

- 코드 변경 시:
- TODO: 기본 테스트, lint, 실행 확인 기준을 적는다.
- 문서 변경 시:
- TODO: 허브 링크, 메타데이터, 관련 운영 문서 정합성 기준을 적는다.
- UI 변경 시:
- TODO: 스크린샷, e2e, QA 확인 기준을 적는다.
- 배포/운영 변경 시:
- TODO: 배포 확인, 롤백 절차, 공지 기준을 적는다.

## 5. 프로젝트 특화 예외 규칙

- 병합 규칙:
- TODO: handoff 와 최신 backlog 충돌 시 우선 재작성 기준을 적는다.
- 승인 규칙:
- TODO: 어떤 문서나 변경이 리뷰를 반드시 거쳐야 하는지 적는다.
- 환경 제약:
- TODO: VPN, secure runner, staging 권한 등 환경 제약을 적는다.
- 기타:
- {mode_note}

## 다음에 읽을 문서

- 공통 표준: [../core/global_workflow_standard.md](../core/global_workflow_standard.md)
- 세션 인계 문서: [./session_handoff.md](./session_handoff.md)
- 작업 백로그 인덱스: [./work_backlog.md](./work_backlog.md)
"""


def render_session_handoff(args: argparse.Namespace, context: dict[str, object]) -> str:
    baseline = "TODO: 현재 세션 기준으로 이미 확인된 상태를 적는다."
    workstream = "TODO: 이번 주 또는 이번 세션의 핵심 축을 적는다."
    in_progress = "TODO: 진행 중 작업이 없으면 비워두지 말고 명시한다."
    blocked = "TODO: 차단 항목 또는 없음 여부를 적는다."
    completed = "TODO: 최근 완료된 작업 ID 와 이름을 적는다."
    if args.adoption_mode == "existing":
        baseline = f"기존 코드베이스 분석을 수행했고, 추정 기본 스택은 `{context['primary_stack']}` 이다."
        workstream = "기존 코드베이스 분석 결과를 바탕으로 워크플로우 문서 구조를 현재 저장소에 맞게 정렬하는 작업"
        in_progress = f"{args.initial_task_id} 기존 프로젝트 분석 및 워크플로우 도입 초안 작성"
        blocked = "실제 배포/운영 절차, 리뷰 규칙, 환경 제약은 추가 확인이 필요하다."
        completed = "기존 저장소 구조 자동 스캔 완료"
    return f"""# 세션 인계 문서

- 문서 목적: 새 세션이나 새 환경에서 이전 작업 상태를 빠르게 복원할 수 있도록 현재 기준 상태를 요약한다.
- 범위: 진행 중 작업, 차단 작업, 최근 완료 작업, 잔여 작업, 환경별 검증 현황
- 대상 독자: 개발자, 운영자, 리뷰어, 문서 작성자
- 상태: draft
- 최종 수정일: {args.today}
- 관련 문서: `./project_workflow_profile.md`, `./work_backlog.md`, `./backlog/{args.today}.md`

## 1. 현재 작업 요약

- 현재 기준선:
- {baseline}
- 현재 주 작업 축:
- {workstream}
- 최근 핵심 기준 문서:
- `{context['session_doc_path']}`, `{context['doc_home']}`

## 1.1 기록 원칙

- 이 문서는 다음 세션이 바로 이어받는 데 필요한 핵심 사실만 간결하게 남긴다.
- 사용자에게 직접 보여지는 요약과 작업 보고는 한국어를 기본으로 한다.
- 코드, 명령어, 파일 경로, 설정 key 는 필요한 경우 원문 그대로 유지한다.
- 내부 탐색 메모나 장문의 reasoning 기록은 남기지 않고, 결정과 검증 결과 중심으로 정리한다.

## 2. 진행 중 작업

- 현재 `in_progress` 작업:
- {in_progress}

## 3. 차단 작업

- 현재 `blocked` 작업:
- {blocked}

## 4. 최근 완료 작업

- 최근 완료 작업 목록:
- {completed}

## 5. 잔여 작업 우선순위

### 우선순위 1

- profile 문서의 추정 명령과 문서 구조를 실제 프로젝트 기준으로 검증
- 오늘 날짜 backlog 에 실제 진행 작업과 검증 계획을 반영

### 우선순위 2

- 문서 허브와 운영 절차 문서가 없으면 저장소에 맞는 위치를 새로 정리
- skill/MCP 도입 후보 범위를 현재 저장소 리스크에 맞게 좁히기

## 6. 환경별 검증 현황

- 검증 완료 호스트:
- `{args.host_name} / {args.host_ip}`
- 주요 제약:
- TODO: 검증 환경 제약을 적는다.

## 다음에 읽을 문서

- 작업 백로그 인덱스: [./work_backlog.md](./work_backlog.md)
- 프로젝트 프로파일: [./project_workflow_profile.md](./project_workflow_profile.md)
"""


def render_backlog_index(args: argparse.Namespace) -> str:
    return f"""# 작업 백로그 인덱스

- 문서 목적: 날짜별 작업 백로그 문서의 위치와 운영 기준을 관리한다.
- 범위: 일자별 백로그 문서
- 대상 독자: 프로젝트 참여자, 문서 작성자, 개발자, 운영자
- 상태: draft
- 최종 수정일: {args.today}
- 관련 문서: `./session_handoff.md`, `./project_workflow_profile.md`, `./backlog/{args.today}.md`

## 운영 원칙

- 세션 시작 시 본 인덱스와 최신 날짜 백로그를 먼저 확인한다.
- 새 작업은 브리핑 후 해당 날짜 백로그에 등록한다.
- 세션 종료 전에는 handoff 문서를 갱신한다.
- 검증 결과와 미실행 사유는 날짜별 백로그에 남긴다.
- 사용자에게 직접 보여지는 작업 기록과 상태 요약은 한국어를 기본으로 작성한다.
- 다음 세션에 필요한 핵심 사실만 남기고, 중간 탐색 흔적과 중복 요약은 줄인다.

## 날짜별 백로그 문서

- [{args.today} 작업 백로그](./backlog/{args.today}.md)
"""


def render_daily_backlog(args: argparse.Namespace, context: dict[str, object]) -> str:
    task_name = args.initial_task_name
    task_status = args.initial_task_status
    task_details = "TODO: 이번 작업의 목표와 변경 범위를 적는다."
    progress_note = f"`{args.today} 09:00` 기준 bootstrap 으로 기본 문서 세트를 생성했다."
    done_criteria = "TODO: 완료 판단 기준과 검증 기준을 적는다."
    if args.adoption_mode == "existing":
        task_name = "기존 코드베이스 분석 및 워크플로우 도입 초안 작성"
        task_status = "in_progress"
        task_details = "저장소 구조, 실행 명령, 테스트 흔적, 기존 문서 위치를 분석해 워크플로우용 profile/handoff/backlog 초안을 만든다."
        progress_note = f"`{args.today} 09:00` 기준 기존 저장소 분석과 워크플로우 문서 초안 생성을 수행했다."
        done_criteria = "repository assessment, profile, handoff, backlog 초안이 현재 저장소 기준으로 연결되고 추정값 검토 포인트가 backlog 에 남는다."
    return f"""# {args.today} 작업 백로그

- 문서 목적: {args.today}에 수행한 작업의 계획, 진행 현황, 완료 내역을 기록한다.
- 범위: {args.today} 작업 이력
- 대상 독자: 프로젝트 참여자, 문서 작성자, 개발자, 운영자
- 상태: draft
- 최종 수정일: {args.today}
- 관련 문서: `../work_backlog.md`, `../session_handoff.md`, `../project_workflow_profile.md`

## {args.initial_task_id} {task_name}

- 상태: {task_status}
- 우선순위: {args.initial_priority}
- 요청일: {args.today}
- 완료일:
- 담당:
- {args.owner}
- 호스트명:
- {args.host_name}
- 호스트 IP:
- {args.host_ip}
- 영향 문서:
- `{context['session_doc_path']}`
- `{context['backlog_dir']}`
- 작업 내용:
- {task_details}
- 진행 현황:
- {progress_note}
- 완료 기준:
- {done_criteria}
- 작업 결과:
- TODO: 실제 반영 결과를 적는다.
- 다음 세션 시작 포인트:
- profile 과 assessment 의 추정값부터 실제 프로젝트 규칙과 대조한다.
- 남은 리스크:
- 자동 추정한 명령, 문서 위치, 검증 규칙이 실제 운영 규칙과 다를 수 있다.
- 후속 작업:
- 실제 프로젝트 운영 규칙과 승인 절차를 profile 및 handoff 문서에 반영한다.

## 기록 메모

- 작업 기록은 한국어를 기본으로 작성한다.
- 코드, 명령어, 파일 경로, 설정 key 는 필요할 때 원문 그대로 유지한다.
- 다음 세션에 필요한 핵심 결정, 검증 결과, 미실행 사유만 남기고 장문의 중간 사고 기록은 생략한다.
"""


def render_assessment(args: argparse.Namespace, context: dict[str, object]) -> str:
    if args.adoption_mode != "existing":
        return ""
    top_entries = ", ".join(context["top_level_entries"]) or "없음"
    docs_dirs = ", ".join(context["docs_dirs"]) or "없음"
    test_dirs = ", ".join(context["test_dirs"]) or "없음"
    source_dirs = ", ".join(context["source_dirs"]) or "없음"
    stack_labels = ", ".join(context["stack_labels"]) or "없음"
    scripts = ", ".join(sorted(context["package_scripts"])) or "없음"
    sample_paths = "\n".join(f"- `{item}`" for item in context.get("sample_paths", []))
    return f"""# Repository Assessment

- 문서 목적: 기존 프로젝트에 표준 AI 워크플로우를 도입하기 전에 현재 코드베이스와 문서 구조를 빠르게 진단한다.
- 범위: 저장소 구조, 추정 기술 스택, 문서 위치, 테스트 흔적, 초기 워크플로우 도입 포인트
- 대상 독자: 개발자, 운영자, AI agent, 프로젝트 온보딩 담당자
- 상태: draft
- 최종 수정일: {args.today}
- 관련 문서: `./project_workflow_profile.md`, `./session_handoff.md`, `../core/workflow_adoption_entrypoints.md`

## 1. 요약

- 분석 대상 프로젝트:
- `{args.project_name}`
- 분석 모드:
- `existing`
- 추정 기본 스택:
- `{context['primary_stack']}`
- 감지된 스택 라벨:
- `{stack_labels}`

## 2. 저장소 구조 관찰

- 상위 디렉터리 항목:
- `{top_entries}`
- 소스 디렉터리 후보:
- `{source_dirs}`
- 문서 디렉터리 후보:
- `{docs_dirs}`
- 테스트 디렉터리 후보:
- `{test_dirs}`

## 3. 추정 명령

- 설치:
- `{context['install_command']}`
- 로컬 실행:
- `{context['run_command']}`
- 빠른 테스트:
- `{context['quick_test_command']}`
- 격리 테스트:
- `{context['isolated_test_command']}`
- 실행 확인:
- `{context['smoke_check_command']}`

## 4. package script 및 경로 샘플

- package script 목록:
- `{scripts}`
- 분석 중 확인한 경로 샘플:
{sample_paths or '- 없음'}

## 5. 워크플로우 도입 초안

- 추천 문서 위키 홈:
- `{context['doc_home']}`
- 추천 운영 문서 위치:
- `{context['operations_dir']}`
- 추천 backlog 위치:
- `{context['backlog_dir']}`
- 추천 session handoff 위치:
- `{context['session_doc_path']}`

## 6. 자동 분석 기반 다음 작업

- 현재 추정 명령과 실제 운영 명령이 일치하는지 확인한다.
- 기존 문서 체계가 있으면 운영 문서 위치를 그대로 따를지, 별도 워크플로우 디렉터리로 분리할지 결정한다.
- 빠른 테스트와 실행 확인 기준이 약하면 우선 profile 문서에서 검증 규칙을 먼저 보강한다.

## 다음에 읽을 문서

- 프로젝트 프로파일: [./project_workflow_profile.md](./project_workflow_profile.md)
- 세션 인계 문서: [./session_handoff.md](./session_handoff.md)
- 도입 분기 가이드: [../core/workflow_adoption_entrypoints.md](../core/workflow_adoption_entrypoints.md)
"""


def codex_agents_path(paths: Paths) -> Path:
    return paths.target_root / "AGENTS.md"


def codex_config_example_path(paths: Paths) -> Path:
    return paths.target_root / ".codex" / "config.toml.example"


def opencode_config_path(paths: Paths) -> Path:
    return paths.target_root / "opencode.json"


def opencode_skill_path(paths: Paths) -> Path:
    return paths.target_root / ".opencode" / "skills" / "standard-ai-workflow" / "SKILL.md"


def opencode_agent_path(paths: Paths) -> Path:
    return paths.target_root / ".opencode" / "agents" / "workflow-orchestrator.md"


def opencode_worker_agent_path(paths: Paths) -> Path:
    return paths.target_root / ".opencode" / "agents" / "workflow-worker.md"


def opencode_doc_worker_agent_path(paths: Paths) -> Path:
    return paths.target_root / ".opencode" / "agents" / "workflow-doc-worker.md"


def opencode_code_worker_agent_path(paths: Paths) -> Path:
    return paths.target_root / ".opencode" / "agents" / "workflow-code-worker.md"


def opencode_validation_worker_agent_path(paths: Paths) -> Path:
    return paths.target_root / ".opencode" / "agents" / "workflow-validation-worker.md"


def render_codex_agents(args: argparse.Namespace, paths: Paths, context: dict[str, object]) -> str:
    harness_note = (
        "기존 코드베이스 분석 결과를 반영한 초안이다. 추정 명령과 문서 경로는 실제 저장소 기준으로 수정할 수 있다."
        if args.adoption_mode == "existing"
        else "신규 프로젝트 기준 초안이다. TODO 항목과 명령은 실제 프로젝트 규칙으로 채워야 한다."
    )
    return f"""# AGENTS.md

- 문서 목적: Codex 가 이 저장소에서 먼저 읽어야 할 workflow 진입 규칙과 기본 작업 원칙을 제공한다.
- 범위: 세션 복원, workflow state docs 참조 순서, 사용자 보고 언어, 기본 실행/검증 명령
- 대상 독자: Codex, 저장소 관리자, workflow 설계자
- 상태: draft
- 최종 수정일: {args.today}
- 관련 문서: `ai-workflow/project/state.json`, `ai-workflow/project/session_handoff.md`, `ai-workflow/project/work_backlog.md`, `ai-workflow/project/project_workflow_profile.md`

## 목적

이 저장소에서는 표준 AI 워크플로우를 기준으로 작업한다. 세션 시작, backlog 갱신, 문서 동기화, 세션 종료는 `ai-workflow/` 아래 문서를 우선 기준으로 삼는다.

## 항상 먼저 읽을 문서

- `ai-workflow/project/state.json`
- `ai-workflow/project/session_handoff.md`
- `ai-workflow/project/work_backlog.md`
- `ai-workflow/project/project_workflow_profile.md`

`ai-workflow/` 는 세션 복원과 workflow 상태 관리용 메타 레이어다. 프로젝트 코드나 프로젝트 문서를 탐색할 때는 이 경로를 기본 탐색 범위에 넣지 말고, workflow 문서 자체를 갱신하거나 현재 세션 상태를 복원할 때만 예외적으로 참조한다.

## 작업 원칙

- 작업을 시작하기 전에 목적, 범위, 영향 문서를 짧게 정리한다.
- 작업 상태는 `planned`, `in_progress`, `blocked`, `done` 중 하나로 관리한다.
- 검증하지 않은 결과는 완료로 확정하지 않는다.
- 세션 종료 전에는 `state.json`, `session_handoff.md`, 최신 backlog 를 갱신한다.

## 언어와 컨텍스트 원칙

- 사용자에게 직접 보이는 작업 보고, 상태 요약, 문서 갱신 문안은 기본적으로 한국어로 작성한다.
- 코드, 명령어, 파일 경로, 설정 key, 외부 시스템 고유 명칭은 필요할 때 원문 그대로 유지한다.
- 내부 사고 과정과 임시 분류는 모델이 가장 효율적인 방식으로 처리하되, 사용자에게는 필요한 결론과 다음 행동만 짧게 전달한다.
- 장문의 중간 reasoning, 중복 요약, 불필요한 자기 설명을 피한다.
- handoff 와 backlog 에는 다음 세션에 필요한 핵심 사실만 남겨 불필요한 컨텍스트 누적을 줄인다.

## 프로젝트 실행 기본값

- 설치: `{context['install_command']}`
- 로컬 실행: `{context['run_command']}`
- 빠른 테스트: `{context['quick_test_command']}`
- 격리 테스트: `{context['isolated_test_command']}`
- 실행 확인: `{context['smoke_check_command']}`

## 문서 작업 기준

- 문서 위키 홈: `{context['doc_home']}`
- 운영 문서 위치: `{context['operations_dir']}`
- backlog 위치: `{context['backlog_dir']}`
- session handoff 위치: `{context['session_doc_path']}`

## Codex 전용 메모

- Codex 는 프로젝트 루트의 `AGENTS.md` 를 읽으므로, 상세 정책은 본 문서에서 시작하고 세부 운영 기준은 `ai-workflow/` 문서를 참조한다.
- OpenAI 관련 질문이 나오면 OpenAI 문서 MCP 를 우선 사용하는 구성을 권장한다.
- 가능한 경우 메인 에이전트는 조정과 통합에 집중하고, bounded scope 의 읽기/쓰기/검증 작업은 worker 성격의 서브 에이전트로 분리하는 패턴을 권장한다.
- worker 에게는 책임 파일과 종료 조건을 명확히 넘기고, 메인 에이전트에는 핵심 사실과 결과만 다시 모은다.
- `main`/`small` 모델을 함께 운영한다면, 메인 에이전트는 난도 높은 판단과 통합에, worker 는 bounded scope 탐색/초안/검증에 우선 배치하는 편이 효율적이다.
- {harness_note}
"""


def render_codex_config_example() -> str:
    return """# Merge this into ~/.codex/config.toml if you want Codex-wide defaults.

[mcp_servers.openaiDeveloperDocs]
url = "https://developers.openai.com/mcp"
default_tools_approval_mode = "approve"
supports_parallel_tool_calls = true
"""


def render_opencode_config(args: argparse.Namespace, paths: Paths) -> str:
    instructions = [
        "AGENTS.md",
        f"{rel(paths.state_path, paths.target_root)}",
        f"{rel(paths.profile_path, paths.target_root)}",
        f"{rel(paths.handoff_path, paths.target_root)}",
        f"{rel(paths.backlog_index_path, paths.target_root)}",
    ]
    return json.dumps(
        {
            "$schema": "https://opencode.ai/config.json",
            "instructions": instructions,
            "agent": {
                "workflow-orchestrator": {
                    "mode": "primary",
                    "description": "Standard AI workflow orchestrator for this project",
                    "prompt": "{file:.opencode/agents/workflow-orchestrator.md}",
                    "permission": {
                        "task": {
                            "*": "deny",
                            "workflow-*": "allow",
                        }
                    },
                },
                "workflow-worker": {
                    "description": "Scoped worker for implementation, draft writing, and verification tasks",
                    "prompt": "{file:.opencode/agents/workflow-worker.md}",
                },
                "workflow-doc-worker": {
                    "description": "Scoped worker for document reading, comparison, and draft updates",
                    "prompt": "{file:.opencode/agents/workflow-doc-worker.md}",
                },
                "workflow-code-worker": {
                    "description": "Scoped worker for bounded code edits and implementation tasks",
                    "prompt": "{file:.opencode/agents/workflow-code-worker.md}",
                },
                "workflow-validation-worker": {
                    "description": "Scoped worker for checks, logs, and validation evidence collection",
                    "prompt": "{file:.opencode/agents/workflow-validation-worker.md}",
                }
            },
            "mcp": {
                "openaiDeveloperDocs": {
                    "type": "remote",
                    "url": "https://developers.openai.com/mcp",
                }
            },
        },
        ensure_ascii=False,
        indent=2,
    ) + "\n"


def render_opencode_skill() -> str:
    return """---
name: standard-ai-workflow
description: Load the project workflow docs before starting or updating work in this repository.
---

# Standard AI Workflow

Use this skill when you need to start a session, update backlog state, sync documents, or prepare a handoff.

Always read:

- `ai-workflow/project/state.json`
- `ai-workflow/project/session_handoff.md`
- `ai-workflow/project/work_backlog.md`
- `ai-workflow/project/project_workflow_profile.md`

If the repository is still in adoption, also read:

- `ai-workflow/project/repository_assessment.md`

Follow these rules:

- Write user-facing status updates, work reports, and document drafts in Korean by default.
- Keep code, commands, file paths, config keys, and external product names in their original form when needed.
- Brief the task before editing files.
- Keep task status aligned with backlog records.
- Do not mark work done without validation evidence.
- Update `state.json`, the handoff, and the latest backlog before ending a session.
- Keep internal reasoning and intermediate classification compact, and avoid long repeated explanations to the user.
- Leave only essential facts in handoff/backlog so session context stays lean.
- Treat `ai-workflow/` as workflow metadata only. Ignore it during normal project document exploration unless the task is explicitly about workflow docs or session state.
"""


def opencode_edit_reliability_rules() -> str:
    return """Edit reliability rules:

- Read the target file immediately before editing so the edit tool anchors against the current file content.
- Keep each edit small and local. Prefer one focused hunk per call for indentation-heavy, generated, or recently changed files.
- Preserve the file's existing indentation and line-ending style unless the task explicitly asks for normalization.
- If inconsistent tabs/spaces or CRLF/LF line endings are the likely cause of edit failures, normalize only the assigned files first, then reread and apply the intended edit.
- Avoid matching huge repeated blocks. Anchor edits on nearby unique lines, function names, headings, or stable keys.
- After an edit-tool failure, reread the file and retry with a narrower replacement instead of repeating the same broad patch.
"""


def render_opencode_agent(args: argparse.Namespace, context: dict[str, object]) -> str:
    return f"""---
description: Orchestrates the standard AI workflow for this repository
mode: primary
permission:
  edit: deny
  bash: deny
  webfetch: deny
---

You are the workflow orchestrator for this repository.

Start each substantial task by reading:

- `AGENTS.md`
- `ai-workflow/project/state.json`
- `ai-workflow/project/session_handoff.md`
- `ai-workflow/project/work_backlog.md`
- `ai-workflow/project/project_workflow_profile.md`

Treat `ai-workflow/` as a workflow metadata layer, not part of the normal project work scope. After session restoration, ignore it during project code or project document exploration unless the task explicitly asks for workflow doc maintenance.

You may directly read only the minimum session-restoration set and tiny triage inputs:

- `ai-workflow/project/state.json`
- `ai-workflow/project/session_handoff.md`
- `ai-workflow/project/work_backlog.md`
- `ai-workflow/project/project_workflow_profile.md`
- one clearly bounded file or path for tiny triage

Project defaults:

- Install: `{context['install_command']}`
- Run: `{context['run_command']}`
- Quick test: `{context['quick_test_command']}`
- Isolated test: `{context['isolated_test_command']}`
- Smoke check: `{context['smoke_check_command']}`

When the repo is in adoption mode, review `ai-workflow/project/repository_assessment.md` before trusting inferred commands.

User-facing workflow rules:

- Write visible work reports, summaries, and document drafts in Korean by default.
- Keep code, commands, file paths, config keys, and external system names in their original form when useful.
- Use concise progress updates and avoid long repeated reasoning in user-visible messages.
- Keep internal processing compact and preserve only the facts needed for the next step or next session.
- Do not call direct tools yourself. Use only task delegation for repository exploration, comparisons, implementation, checks, and draft generation.
- Use sub-agents aggressively for file exploration, comparisons, log inspection, and draft generation when that helps reduce context pollution.
- Keep the main orchestrator focused on coordination, prioritization, integration, and the final user-facing report.
- Separate broad read-heavy exploration from write tasks when possible so one stream of work does not pollute another stream's context.
- Treat this agent as a read-mostly coordinator with task-only execution: delegate edits, scans, log review, and validation to sub-agents instead of making exceptions for direct tool use.
- Keep direct read narrow: after the session-restoration set, only tiny single-file or single-path triage reads stay local; broader reading goes to workers.
- Ask the user only when a missing decision is genuinely blocking or a risky external action needs confirmation; otherwise make the smallest reasonable assumption and continue through a worker.
- When delegating, give each worker a bounded scope, clear output, and a concise completion contract.
- Prefer `workflow-doc-worker` for large document reads and draft updates, `workflow-code-worker` for bounded implementation, config edits, and build-oriented tasks, and `workflow-validation-worker` for checks and evidence collection.
- If your harness supports per-agent model selection, prefer the main model for this orchestrator and a smaller model for the worker agents by default.
- Do not treat `ai-workflow/` as part of normal project document discovery. Use it only for workflow-state restoration or explicit workflow-maintenance tasks.
"""


def render_opencode_worker_agent(args: argparse.Namespace, context: dict[str, object]) -> str:
    edit_rules = opencode_edit_reliability_rules()
    return f"""---
description: Executes bounded workflow tasks for this repository
mode: subagent
permission:
  edit: allow
  bash: allow
  webfetch: allow
---

You are a workflow worker for this repository.

You are not the main orchestrator. Your role is to execute a tightly scoped task and return only the essential result.

Before starting, read only the minimum relevant context:

- `AGENTS.md`
- `ai-workflow/project/state.json` when it helps restore the current task baseline quickly
- the specific `ai-workflow/project/` document or file paths that match your assigned scope

Project defaults:

- Install: `{context['install_command']}`
- Run: `{context['run_command']}`
- Quick test: `{context['quick_test_command']}`
- Isolated test: `{context['isolated_test_command']}`
- Smoke check: `{context['smoke_check_command']}`

Worker rules:

- Stay within the assigned file or task scope.
- Prefer doing the actual bounded work instead of producing long plans.
- Summarize only the key facts, edits, risks, and follow-up items needed by the orchestrator.
- Avoid pasting large raw outputs when a short summary is enough.
- If you edit files, keep changes narrow and do not expand into unrelated cleanup.
- If you run checks, report only the command intent and the result that matters.
- Write user-facing drafts in Korean by default unless the assigned task clearly requires another language.
- Minimize asks during execution. Proceed with the smallest reasonable assumption unless the orchestrator explicitly requested a decision point.
- Ignore `ai-workflow/` during normal project document or source exploration unless the assigned task explicitly targets workflow docs or session-state updates.

{edit_rules}
"""


def render_opencode_doc_worker_agent(args: argparse.Namespace, context: dict[str, object]) -> str:
    edit_rules = opencode_edit_reliability_rules()
    return f"""---
description: Executes bounded document-focused workflow tasks for this repository
mode: subagent
permission:
  edit: allow
  bash: allow
  webfetch: allow
---

You are a document-focused workflow worker for this repository.

Your role is to read, compare, summarize, and update a tightly scoped set of documents without pulling unrelated context into the main orchestrator.

Before starting, read only the minimum relevant context:

- `AGENTS.md`
- `ai-workflow/project/state.json` when it helps restore the current task baseline quickly
- the assigned `ai-workflow/project/` documents or directly named doc paths

Worker rules:

- Stay within the assigned document scope.
- Prefer concise comparisons, change notes, and draft text over long quotations.
- Return only the facts, inconsistencies, draft wording, and follow-up items needed by the orchestrator.
- Keep user-facing drafts in Korean by default.
- Minimize asks during execution and resolve obvious document-structure choices locally when risk is low.
- If your harness supports per-agent model selection, this worker is a good default target for a smaller model.
- Ignore `ai-workflow/` when looking for project documentation unless the assigned task is explicitly about workflow docs or session-state maintenance.

{edit_rules}
"""


def render_opencode_code_worker_agent(args: argparse.Namespace, context: dict[str, object]) -> str:
    edit_rules = opencode_edit_reliability_rules()
    return f"""---
description: Executes bounded implementation and build-focused workflow tasks for this repository
mode: subagent
permission:
  edit: allow
  bash: allow
  webfetch: allow
---

You are an implementation and build-focused workflow worker for this repository.

Your role is to implement a tightly scoped code or config change, run the minimum relevant build-oriented checks when needed, and report only the essential result back to the orchestrator.

Before starting, read only the minimum relevant context:

- `AGENTS.md`
- `ai-workflow/project/state.json` when it helps restore the current task baseline quickly
- the specific source files, tests, and workflow docs tied to your assigned scope

Worker rules:

- Stay within the assigned write scope.
- Prefer shipping the bounded change over expanding into adjacent cleanup.
- Treat build, compile, package, or asset-generation commands as part of your default scope when they are the shortest path to proving the implementation still holds.
- If you run checks, report what matters: pass/fail, key regression risk, build impact, and any deferred follow-up.
- Avoid broad repository exploration unless explicitly assigned.
- Minimize asks during execution. Make bounded implementation choices locally unless the change would alter product behavior or ownership boundaries.
- If your harness supports per-agent model selection, use a smaller model for routine edits and reserve the main model for unusually risky or architectural code tasks.
- Ignore `ai-workflow/` during normal implementation-context discovery unless the assigned task explicitly targets workflow docs or workflow automation.

{edit_rules}
"""


def render_opencode_validation_worker_agent(args: argparse.Namespace, context: dict[str, object]) -> str:
    return f"""---
description: Executes bounded validation and evidence-collection tasks for this repository
mode: subagent
permission:
  edit: allow
  bash: allow
  webfetch: allow
---

You are a validation-focused workflow worker for this repository.

Your role is to run bounded checks, inspect logs, gather evidence, and return a compact validation summary to the orchestrator.

Before starting, read only the minimum relevant context:

- `AGENTS.md`
- `ai-workflow/project/state.json` when it helps restore the current task baseline quickly
- the assigned validation scope, commands, and relevant backlog or handoff notes

Project defaults:

- Quick test: `{context['quick_test_command']}`
- Isolated test: `{context['isolated_test_command']}`
- Smoke check: `{context['smoke_check_command']}`

Worker rules:

- Stay within the assigned validation scope and command set.
- Report only the result that matters: what ran, what failed or passed, and what evidence should be recorded.
- Avoid flooding the orchestrator with raw logs when a short summary is enough.
- Minimize asks during execution and complete the assigned checks unless the environment is genuinely blocked.
- If your harness supports per-agent model selection, this worker is usually a strong candidate for a smaller model.
- Ignore `ai-workflow/` during normal validation-context discovery unless the assigned task explicitly targets workflow docs or session-state verification.
"""


def write_codex_harness_files(
    args: argparse.Namespace,
    paths: Paths,
    context: dict[str, object],
) -> dict[str, str]:
    codex_config = codex_config_example_path(paths)
    write_text(codex_config, render_codex_config_example(), force=args.force)
    return {
        "codex_config_example": str(codex_config),
    }


def write_opencode_harness_files(
    args: argparse.Namespace,
    paths: Paths,
    context: dict[str, object],
) -> dict[str, str]:
    opencode_config = opencode_config_path(paths)
    opencode_skill = opencode_skill_path(paths)
    opencode_agent = opencode_agent_path(paths)
    opencode_worker_agent = opencode_worker_agent_path(paths)
    opencode_doc_worker_agent = opencode_doc_worker_agent_path(paths)
    opencode_code_worker_agent = opencode_code_worker_agent_path(paths)
    opencode_validation_worker_agent = opencode_validation_worker_agent_path(paths)
    write_text(opencode_config, render_opencode_config(args, paths), force=args.force)
    write_text(opencode_skill, render_opencode_skill(), force=args.force)
    write_text(opencode_agent, render_opencode_agent(args, context), force=args.force)
    write_text(opencode_worker_agent, render_opencode_worker_agent(args, context), force=args.force)
    write_text(opencode_doc_worker_agent, render_opencode_doc_worker_agent(args, context), force=args.force)
    write_text(opencode_code_worker_agent, render_opencode_code_worker_agent(args, context), force=args.force)
    write_text(
        opencode_validation_worker_agent,
        render_opencode_validation_worker_agent(args, context),
        force=args.force,
    )
    return {
        "opencode_config": str(opencode_config),
        "opencode_skill": str(opencode_skill),
        "opencode_agent": str(opencode_agent),
        "opencode_worker_agent": str(opencode_worker_agent),
        "opencode_doc_worker_agent": str(opencode_doc_worker_agent),
        "opencode_code_worker_agent": str(opencode_code_worker_agent),
        "opencode_validation_worker_agent": str(opencode_validation_worker_agent),
    }


HARNESS_FILE_BUILDERS = {
    "codex": write_codex_harness_files,
    "opencode": write_opencode_harness_files,
}


def write_harness_files(
    args: argparse.Namespace,
    paths: Paths,
    context: dict[str, object],
) -> dict[str, str]:
    generated: dict[str, str] = {}
    harnesses = selected_harnesses(args)
    if harnesses:
        codex_agents = codex_agents_path(paths)
        write_text(codex_agents, render_codex_agents(args, paths, context), force=args.force)
        generated["codex_agents"] = str(codex_agents)
    for harness in harnesses:
        builder = HARNESS_FILE_BUILDERS[harness]
        generated.update(builder(args, paths, context))
    return generated


def build_manifest(
    args: argparse.Namespace,
    paths: Paths,
    core_docs: list[str],
    context: dict[str, object],
    harness_files: dict[str, str],
) -> dict[str, object]:
    selected_snippets = {
        harness: global_snippet_sources()[harness]
        for harness in selected_harnesses(args)
        if harness in global_snippet_sources()
    }
    generated_files: dict[str, str] = {
        "readme": str(paths.readme_path),
        "project_profile": str(paths.profile_path),
        "workflow_state": str(paths.state_path),
        "session_handoff": str(paths.handoff_path),
        "work_backlog": str(paths.backlog_index_path),
        "daily_backlog": str(paths.daily_backlog_path),
    }
    if args.adoption_mode == "existing":
        generated_files["repository_assessment"] = str(paths.assessment_path)
    return {
        "target_root": str(paths.target_root),
        "kit_root": str(paths.kit_root),
        "project_slug": args.project_slug,
        "project_name": args.project_name,
        "adoption_mode": args.adoption_mode,
        "harnesses": selected_harnesses(args),
        "analysis_summary": context["analysis_summary"],
        "generated_files": generated_files,
        "generated_harness_files": harness_files,
        "global_snippet_candidates": selected_snippets,
        "copied_core_docs": core_docs,
        "next_steps": [
            f"Open {rel(paths.profile_path, paths.target_root)} and replace TODO placeholders.",
            f"Refresh {rel(paths.state_path, paths.target_root)} after updating workflow docs.",
            f"Update {rel(paths.handoff_path, paths.target_root)} with the current session baseline.",
            f"Register the next real task in {rel(paths.daily_backlog_path, paths.target_root)}.",
        ]
        + (
            [f"Review {rel(paths.assessment_path, paths.target_root)} and confirm inferred commands and doc paths."]
            if args.adoption_mode == "existing"
            else []
        )
        + (
            [
                "Review the recommended global snippet before merging it into your harness-wide config."
            ]
            if selected_snippets
            else []
        ),
    }


def main() -> int:
    args = parse_args()
    paths = make_paths(args)
    context = infer_project_context(args, paths)
    core_docs = [str(paths.core_dir / name) for name in DEFAULT_CORE_DOCS] if args.copy_core_docs else []
    harness_files: dict[str, str] = {}
    manifest = build_manifest(args, paths, core_docs, context, harness_files)

    if args.dry_run:
        print(json.dumps(manifest, ensure_ascii=False, indent=2))
        return 0

    try:
        write_text(paths.readme_path, render_readme(args, context), force=args.force)
        write_text(paths.profile_path, render_project_profile(args, context), force=args.force)
        write_text(paths.handoff_path, render_session_handoff(args, context), force=args.force)
        write_text(paths.backlog_index_path, render_backlog_index(args), force=args.force)
        write_text(paths.daily_backlog_path, render_daily_backlog(args, context), force=args.force)
        if args.adoption_mode == "existing":
            write_text(paths.assessment_path, render_assessment(args, context), force=args.force)
        write_text(
            paths.state_path,
            json.dumps(
                build_workflow_state_payload(
                    project_profile_path=paths.profile_path,
                    session_handoff_path=paths.handoff_path,
                    work_backlog_index_path=paths.backlog_index_path,
                    latest_backlog_path=paths.daily_backlog_path,
                    repository_assessment_path=paths.assessment_path if args.adoption_mode == "existing" else None,
                    generated_at=args.today,
                ),
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            force=args.force,
        )
        harness_files = write_harness_files(args, paths, context)
        if args.copy_core_docs:
            core_docs = copy_core_docs(paths, force=args.force)
        manifest = build_manifest(args, paths, core_docs, context, harness_files)
    except FileExistsError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
