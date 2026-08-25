"""Registry for the first read-only MCP server bundle."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from workflow_kit import __version__ as TOOL_VERSION
from workflow_kit.common.output_contracts import (
    ERROR_PATH_CONTRACTS,
    SUCCESS_PATH_CONTRACTS,
    output_field_shapes_schema,
    output_json_schema_for_family,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
SOURCE_ROOT = REPO_ROOT / "workflow-source"


@dataclass(frozen=True)
class ReadOnlyToolFieldSpec:
    name: str
    cli_flag: str
    value_type: str
    description: str
    required: bool = False
    repeated: bool = False


@dataclass(frozen=True)
class ReadOnlyToolSpec:
    name: str
    description: str
    script_path: Path
    input_fields: tuple[ReadOnlyToolFieldSpec, ...]
    requires_any_of: tuple[str, ...] = ()
    payload_example: dict[str, object] | None = None
    #: v1.1.7 (TASK-2026-08-11-main-024): descriptor 의 `readOnlyHint` 는 이 선언에서
    #: 나온다. 이전에는 builder 가 전 도구에 True 를 하드코딩해 **파일을 쓰는 도구**
    #: (`apply_robust_patch` / `rotate_workflow_logs`) 까지 read-only 로 광고했다 —
    #: 하네스가 이 hint 로 auto-approve 할 수 있는 허위 주석이다 (ADR-003 v1.1 개정).
    read_only: bool = True


READ_ONLY_SERVER_NAME = "workflow_read_only_bundle"
READ_ONLY_TRANSPORT_DESCRIPTOR_TARGET = "mcp_tools_list_draft"

# --- bundle 분리 (v1.1.8+, TASK-2026-08-12-main-003 — ADR-003 v1.1.7 후속) -----
# "read_only" 라는 이름의 bundle 안에 write 도구 2종이 사는 긴장의 근본 정리.
# 서버/manifest/descriptor 는 bundle 선택자를 받는다:
#   - "read-only": read_only=True 도구만 (하네스 자동 노출용, 이름이 정직해진다)
#                  — v1.2.0 (2nd cycle) 부터 CLI `--bundle` 미지정 시 기본값.
#   - "write":     write-capable 도구만 (명시 opt-in, manual review 대상)
#   - "all":       구 표면 그대로 (v1.2.0 부터 명시 opt-in — 서빙 시 notice)
BUNDLE_READ_ONLY = "read-only"
BUNDLE_WRITE = "write"
BUNDLE_ALL = "all"
BUNDLE_LABELS: tuple[str, ...] = (BUNDLE_READ_ONLY, BUNDLE_WRITE, BUNDLE_ALL)
WRITE_SERVER_NAME = "workflow_write_bundle"


def server_name_for_bundle(bundle: str) -> str:
    if bundle == BUNDLE_WRITE:
        return WRITE_SERVER_NAME
    # "all" 은 기존 서버 이름 유지 (config 호환) — ADR-003 의 "read-only 우선" 표면.
    return READ_ONLY_SERVER_NAME


def tool_specs_for_bundle(bundle: str = BUNDLE_ALL) -> tuple["ReadOnlyToolSpec", ...]:
    if bundle not in BUNDLE_LABELS:
        raise ValueError(f"unknown bundle {bundle!r} (선언: {', '.join(BUNDLE_LABELS)})")
    if bundle == BUNDLE_READ_ONLY:
        return tuple(spec for spec in READ_ONLY_TOOL_SPECS if spec.read_only)
    if bundle == BUNDLE_WRITE:
        return tuple(spec for spec in READ_ONLY_TOOL_SPECS if not spec.read_only)
    return READ_ONLY_TOOL_SPECS

READ_ONLY_TOOL_SPECS: tuple[ReadOnlyToolSpec, ...] = (
    ReadOnlyToolSpec(
        name="latest_backlog",
        description="Locate the latest dated backlog document from an index or backlog directory.",
        script_path=SOURCE_ROOT / "mcp_servers" / "latest-backlog" / "scripts" / "run_latest_backlog.py",
        input_fields=(
            ReadOnlyToolFieldSpec(
                name="backlog_dir_path",
                cli_flag="--backlog-dir-path",
                value_type="path",
                description="Fallback backlog directory to scan for dated markdown files.",
            ),
            ReadOnlyToolFieldSpec(
                name="work_backlog_index_path",
                cli_flag="--work-backlog-index-path",
                value_type="path",
                description="Backlog index markdown file whose links point to dated backlog files.",
            ),
        ),
        requires_any_of=("backlog_dir_path", "work_backlog_index_path"),
        payload_example={"work_backlog_index_path": str(REPO_ROOT / "work_backlog.md")},
    ),
    ReadOnlyToolSpec(
        name="check_doc_metadata",
        description="Inspect markdown files and report missing required metadata fields.",
        script_path=SOURCE_ROOT / "mcp_servers" / "check-doc-metadata" / "scripts" / "run_check_doc_metadata.py",
        input_fields=(
            ReadOnlyToolFieldSpec(
                name="doc_dir_path",
                cli_flag="--doc-dir-path",
                value_type="path",
                description="Root directory whose markdown files will be scanned.",
                required=True,
            ),
        ),
        payload_example={"doc_dir_path": str(REPO_ROOT / "examples" / "acme_delivery_platform")},
    ),
    ReadOnlyToolSpec(
        name="check_doc_links",
        description="Inspect markdown relative links and report broken targets.",
        script_path=SOURCE_ROOT / "mcp_servers" / "check-doc-links" / "scripts" / "run_check_doc_links.py",
        input_fields=(
            ReadOnlyToolFieldSpec(
                name="doc_dir_path",
                cli_flag="--doc-dir-path",
                value_type="path",
                description="Root directory whose markdown files will be scanned for broken links.",
                required=True,
            ),
        ),
        payload_example={"doc_dir_path": str(REPO_ROOT / "examples" / "acme_delivery_platform")},
    ),
    ReadOnlyToolSpec(
        name="suggest_impacted_docs",
        description="Suggest impacted workflow documents from changed files and summary input.",
        script_path=SOURCE_ROOT / "mcp_servers" / "suggest-impacted-docs" / "scripts" / "run_suggest_impacted_docs.py",
        input_fields=(
            ReadOnlyToolFieldSpec(
                name="changed_files",
                cli_flag="--changed-file",
                value_type="string",
                description="Changed file paths that should be classified into impacted document candidates.",
                required=True,
                repeated=True,
            ),
            ReadOnlyToolFieldSpec(
                name="session_handoff_path",
                cli_flag="--session-handoff-path",
                value_type="path",
                description="Optional session handoff document to include as an impacted state document.",
            ),
            ReadOnlyToolFieldSpec(
                name="latest_backlog_path",
                cli_flag="--latest-backlog-path",
                value_type="path",
                description="Optional latest backlog document to include as an impacted state document.",
            ),
            ReadOnlyToolFieldSpec(
                name="work_backlog_index_path",
                cli_flag="--work-backlog-index-path",
                value_type="path",
                description="Optional backlog index document to include as an impacted state document.",
            ),
        ),
        payload_example={
            "changed_files": ["workflow-source/workflow_kit/server/read_only_entrypoint.py", "workflow-source/tests/check_read_only_mcp_server.py"],
            "latest_backlog_path": str(REPO_ROOT / "backlog" / "2026-04-22.md"),
        },
    ),
    ReadOnlyToolSpec(
        name="create_backlog_entry",
        description="Generate a draft backlog entry JSON for a new task.",
        script_path=SOURCE_ROOT / "mcp_servers" / "create-backlog-entry" / "scripts" / "run_create_backlog_entry.py",
        input_fields=(
            ReadOnlyToolFieldSpec(
                name="task_id",
                cli_flag="--task-id",
                value_type="string",
                description="Unique identifier for the task (e.g., TASK-001).",
                required=True,
            ),
            ReadOnlyToolFieldSpec(
                name="task_name",
                cli_flag="--task-name",
                value_type="string",
                description="Short descriptive name of the task.",
                required=True,
            ),
            ReadOnlyToolFieldSpec(
                name="request_date",
                cli_flag="--request-date",
                value_type="string",
                description="Date the task was requested (YYYY-MM-DD).",
                required=True,
            ),
            ReadOnlyToolFieldSpec(
                name="status",
                cli_flag="--status",
                value_type="string",
                description="Initial status of the task (default: planned).",
            ),
            ReadOnlyToolFieldSpec(
                name="priority",
                cli_flag="--priority",
                value_type="string",
                description="Priority of the task (default: high).",
            ),
            # ADR-027 M-004: roadmap 이 있는 workspace 의 task 생성 게이트.
            # CLI(backlog-update)와 같은 단일 판정 함수를 거친다.
            ReadOnlyToolFieldSpec(
                name="workspace_root",
                cli_flag="--workspace-root",
                value_type="path",
                description="Workspace root for the ADR-027 roadmap gate. Defaults to the server cwd.",
                required=False,
            ),
            ReadOnlyToolFieldSpec(
                name="wbs",
                cli_flag="--wbs",
                value_type="string",
                description="WBS leaf ref 'M-NNN/WBS-N.N', or 'exempt' with a reason. Required when the workspace has a roadmap.",
                required=False,
            ),
            ReadOnlyToolFieldSpec(
                name="wbs_exempt_reason",
                cli_flag="--wbs-exempt-reason",
                value_type="string",
                description="Mandatory reason when wbs='exempt' — the bypass is a declaration, not silence.",
                required=False,
            ),
        ),
        payload_example={
            "task_id": "TASK-009",
            "task_name": "MCP Server Promotion",
            "request_date": "2026-04-26",
        },
    ),
    ReadOnlyToolSpec(
        name="create_session_handoff_draft",
        description="Generate a draft session handoff document from the latest backlog.",
        script_path=SOURCE_ROOT / "mcp_servers" / "create-session-handoff-draft" / "scripts" / "run_create_session_handoff_draft.py",
        input_fields=(
            ReadOnlyToolFieldSpec(
                name="latest_backlog_path",
                cli_flag="--latest-backlog-path",
                value_type="path",
                description="Latest dated backlog document to extract task status from.",
            ),
            ReadOnlyToolFieldSpec(
                name="git_summary",
                cli_flag="--git-summary",
                value_type="string",
                description="Optional git summary text to include in the handoff.",
            ),
        ),
        payload_example={
            "latest_backlog_path": str(SOURCE_ROOT / "project" / "backlog" / "2026-04-26.md"),
            "git_summary": "### Git Summary\n- feat: some change",
        },
    ),
    ReadOnlyToolSpec(
        name="create_environment_record_stub",
        description="Generate a draft environment record stub for the current host.",
        script_path=SOURCE_ROOT / "mcp_servers" / "create-environment-record-stub" / "scripts" / "run_create_environment_record_stub.py",
        input_fields=(
            ReadOnlyToolFieldSpec(
                name="hostname",
                cli_flag="--hostname",
                value_type="string",
                description="Current host name.",
                required=True,
            ),
            ReadOnlyToolFieldSpec(
                name="os_type",
                cli_flag="--os-type",
                value_type="string",
                description="Current OS type (e.g., darwin, linux, windows).",
                required=True,
            ),
        ),
        payload_example={
            "hostname": "local-dev",
            "os_type": "darwin",
        },
    ),
    ReadOnlyToolSpec(
        name="check_quickstart_stale_links",
        description="Check quickstart and README entry docs for stale or missing links.",
        script_path=SOURCE_ROOT / "mcp_servers" / "check-quickstart-stale-links" / "scripts" / "run_check_quickstart_stale_links.py",
        input_fields=(
            ReadOnlyToolFieldSpec(
                name="quickstart_paths",
                cli_flag="--quickstart-path",
                value_type="path",
                description="One or more quickstart or README entry documents to inspect.",
                required=True,
                repeated=True,
            ),
            ReadOnlyToolFieldSpec(
                name="project_profile_path",
                cli_flag="--project-profile-path",
                value_type="path",
                description="Optional project profile document expected to be linked from entry docs.",
            ),
            ReadOnlyToolFieldSpec(
                name="session_handoff_path",
                cli_flag="--session-handoff-path",
                value_type="path",
                description="Optional session handoff document expected to be linked from entry docs.",
            ),
            ReadOnlyToolFieldSpec(
                name="work_backlog_index_path",
                cli_flag="--work-backlog-index-path",
                value_type="path",
                description="Optional backlog index document expected to be linked from entry docs.",
            ),
            ReadOnlyToolFieldSpec(
                name="agents_path",
                cli_flag="--agents-path",
                value_type="path",
                description="Optional AGENTS or harness guidance document expected to be linked from entry docs.",
            ),
        ),
        payload_example={
            "quickstart_paths": [str(REPO_ROOT / "README.md")],
            "work_backlog_index_path": str(REPO_ROOT / "work_backlog.md"),
        },
    ),
    ReadOnlyToolSpec(
        name="summarize_git_history",
        description="Summarize git commit history into categories and markdown for handoff.",
        script_path=SOURCE_ROOT / "mcp_servers" / "git-history-summarizer" / "scripts" / "run_git_history_summarizer.py",
        input_fields=(
            ReadOnlyToolFieldSpec(
                name="repo_path",
                cli_flag="--repo-path",
                value_type="path",
                description="Path to the git repository.",
                required=True,
            ),
            ReadOnlyToolFieldSpec(
                name="commit_range",
                cli_flag="--range",
                value_type="string",
                description="Commit range to summarize (e.g., 'HEAD~5..HEAD').",
                required=True,
            ),
        ),
        payload_example={
            "repo_path": ".",
            "commit_range": "HEAD~3..HEAD",
        },
    ),
    ReadOnlyToolSpec(
        name="rotate_workflow_logs",
        description="Rotate old done items from handoff into baseline to prevent bloat.",
        script_path=SOURCE_ROOT / "mcp_servers" / "rotate-workflow-logs" / "scripts" / "run_rotate_workflow_logs.py",
        input_fields=(
            ReadOnlyToolFieldSpec(
                name="handoff_path",
                cli_flag="--handoff-path",
                value_type="path",
                description="Path to the session handoff document.",
                required=True,
            ),
            ReadOnlyToolFieldSpec(
                name="max_done_items",
                cli_flag="--max-done-items",
                value_type="string",
                description="Maximum number of done items to keep in 'recently done' (default: 10).",
            ),
        ),
        payload_example={
            "handoff_path": "ai-workflow/memory/active/sessions",
            "max_done_items": "5",
        },
        # handoff 를 실제로 rewrite 한다 (read_only_bundle.py 의 written_paths).
        read_only=False,
    ),
    ReadOnlyToolSpec(
        name="assess_milestone_progress",
        # ADR-027 M-003: 진척의 SSOT 가 roadmap 층으로 바뀌었다 — 입력도 함께
        # 바뀐다 (matrix_path/backlog_path → workspace_root). 데모 휴리스틱
        # (common.milestones)은 함수까지 은퇴.
        description="Assess milestone progress from the ADR-027 roadmap layer (roadmap/ SSOT + task wbs links).",
        script_path=SOURCE_ROOT / "mcp_servers" / "milestone-progress" / "scripts" / "run_assess_milestone_progress.py",
        input_fields=(
            ReadOnlyToolFieldSpec(
                name="workspace_root",
                cli_flag="--workspace-root",
                value_type="path",
                description="Workspace root containing ai-workflow/memory/active/roadmap/. Defaults to the server cwd.",
                required=False,
            ),
        ),
        payload_example={
            "workspace_root": ".",
        },
    ),
    ReadOnlyToolSpec(
        name="smart_context_reader",
        description="Extract specific function or class blocks from a Python file to reduce LLM context bloat.",
        script_path=SOURCE_ROOT / "mcp_servers" / "smart-context-reader" / "scripts" / "run_smart_reader.py",
        input_fields=(
            ReadOnlyToolFieldSpec(
                name="file_path",
                cli_flag="--file-path",
                value_type="path",
                description="Path to the Python file.",
                required=True,
            ),
            ReadOnlyToolFieldSpec(
                name="symbols",
                cli_flag="--symbols",
                value_type="string",
                description="List of function or class names to extract. If empty, all are extracted.",
                repeated=True,
            ),
        ),
        payload_example={
            "file_path": "src/main.py",
            "symbols": ["calculate_total", "UserContext"],
        },
    ),
    ReadOnlyToolSpec(
        name="apply_robust_patch",
        description="Apply a robust Search-Replace block patch to a file with fuzzy matching and syntax validation.",
        script_path=SOURCE_ROOT / "mcp_servers" / "apply_robust_patch" / "scripts" / "run_apply_robust_patch.py",
        input_fields=(
            ReadOnlyToolFieldSpec(
                name="file_path",
                cli_flag="--file-path",
                value_type="path",
                description="Target file to patch.",
                required=True,
            ),
            ReadOnlyToolFieldSpec(
                name="patch_content",
                cli_flag="--patch-content",
                value_type="string",
                description="The SEARCH/REPLACE block content (using <<<<<<< SEARCH, =======, >>>>>>> REPLACE).",
                required=True,
            ),
        ),
        payload_example={
            "file_path": "src/main.py",
            "patch_content": "<<<<<<< SEARCH\ndef old():\n    pass\n=======\ndef new():\n    print('fixed')\n>>>>>>> REPLACE",
        },
        # 대상 파일을 실제로 write 한다 (patching.py, dry_run 입력 없음).
        read_only=False,
    ),
)

#: 파일시스템을 변경하는 도구의 **사실 목록** — 검사가 registry 선언과 대조한다.
#: 새 write 도구를 추가하면 여기와 spec 의 `read_only=False` 를 같이 갱신해야 하고,
#: 어느 한쪽만 고치면 `check_read_only_mcp_server` 가 잡는다.
WRITE_CAPABLE_TOOL_NAMES: frozenset[str] = frozenset({"apply_robust_patch", "rotate_workflow_logs"})


def get_tool_spec(tool_name: str) -> ReadOnlyToolSpec | None:
    for spec in READ_ONLY_TOOL_SPECS:
        if spec.name == tool_name:
            return spec
    return None


def input_json_schema_for_spec(spec: ReadOnlyToolSpec) -> dict[str, object]:
    properties: dict[str, object] = {}
    required: list[str] = []
    for field in spec.input_fields:
        field_schema: dict[str, object]
        if field.repeated:
            field_schema = {
                "type": "array",
                "items": {"type": "string"},
                "description": field.description,
            }
        else:
            field_schema = {
                "type": "string",
                "description": field.description,
            }
        properties[field.name] = field_schema
        if field.required:
            required.append(field.name)

    schema: dict[str, object] = {
        "type": "object",
        "properties": properties,
        "required": sorted(required),
        "additionalProperties": False,
    }
    if spec.requires_any_of:
        schema["anyOf"] = [{"required": [field_name]} for field_name in spec.requires_any_of]
    return schema


def build_transport_tool_descriptor(spec: ReadOnlyToolSpec) -> dict[str, object]:
    return {
        "name": spec.name,
        "description": spec.description,
        "inputSchema": input_json_schema_for_spec(spec),
        "outputSchema": output_json_schema_for_family(spec.name),
        "annotations": {
            "readOnlyHint": spec.read_only,
        },
        "_meta": {
            # registry 는 **transport 를 모른다** — 어느 bridge 가 자기를 서빙할지
            # 알 수 없으므로 `transport_ready` 같은 transport 사실을 선언하지 않는다
            # (§1.3 세 축, 2026-08-05). `bundle_phase` 는 registry 자신의 사실이다.
            "bundle_phase": "direct_call_adapter",
            "adapter": "workflow_kit.server.read_only_tools.invoke_read_only_tool",
            "descriptor_target": READ_ONLY_TRANSPORT_DESCRIPTOR_TARGET,
        },
    }


def build_transport_tool_descriptors(bundle: str = BUNDLE_ALL) -> dict[str, object]:
    specs = tool_specs_for_bundle(bundle)
    descriptors = [build_transport_tool_descriptor(spec) for spec in specs]
    return {
        "status": "ok",
        "tool_version": TOOL_VERSION,
        "server_name": server_name_for_bundle(bundle),
        "bundle": bundle,
        "descriptor_target": READ_ONLY_TRANSPORT_DESCRIPTOR_TARGET,
        "tool_count": len(descriptors),
        "tools": descriptors,
    }


def build_server_manifest(bundle: str = BUNDLE_ALL) -> dict[str, object]:
    specs = tool_specs_for_bundle(bundle)
    return {
        "status": "ok",
        "tool_version": TOOL_VERSION,
        "server_name": server_name_for_bundle(bundle),
        "bundle": bundle,
        "tool_count": len(specs),
        "transport": {
            "descriptor_target": READ_ONLY_TRANSPORT_DESCRIPTOR_TARGET,
            "descriptor_source": "workflow_kit.server.read_only_registry.build_transport_tool_descriptors",
        },
        "tools": [
            {
                "name": spec.name,
                "description": spec.description,
                "script_path": str(spec.script_path),
                "bundle_phase": "direct_call_adapter",
                "input_schema": {
                    "type": "object",
                    "fields": [
                        {
                            "name": field.name,
                            "cli_flag": field.cli_flag,
                            "value_type": field.value_type,
                            "required": field.required,
                            "repeated": field.repeated,
                            "description": field.description,
                        }
                        for field in spec.input_fields
                    ],
                    "requires_any_of": list(spec.requires_any_of),
                },
                "output_schema": {
                    "success_required_keys": sorted(SUCCESS_PATH_CONTRACTS.get(spec.name, frozenset())),
                    "error_required_keys": sorted(ERROR_PATH_CONTRACTS.get(spec.name, frozenset())),
                    "field_shapes": output_field_shapes_schema().get(spec.name, {}),
                    "json_schema_draft": "2020-12",
                    "json_schema_source": "workflow_kit.common.output_contracts.output_json_schema_for_family",
                    "json_schema": output_json_schema_for_family(spec.name),
                },
                "transport_descriptor": build_transport_tool_descriptor(spec),
                "payload_example": spec.payload_example,
            }
            for spec in specs
        ],
    }
