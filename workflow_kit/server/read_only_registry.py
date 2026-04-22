"""Registry for the first read-only MCP server bundle."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from workflow_kit import __version__ as TOOL_VERSION
from workflow_kit.common.output_contracts import ERROR_PATH_CONTRACTS, SUCCESS_PATH_CONTRACTS, output_field_shapes_schema


REPO_ROOT = Path(__file__).resolve().parents[2]


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


READ_ONLY_SERVER_NAME = "workflow_read_only_bundle"

READ_ONLY_TOOL_SPECS: tuple[ReadOnlyToolSpec, ...] = (
    ReadOnlyToolSpec(
        name="latest_backlog",
        description="Locate the latest dated backlog document from an index or backlog directory.",
        script_path=REPO_ROOT / "mcp" / "latest-backlog" / "scripts" / "run_latest_backlog.py",
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
        script_path=REPO_ROOT / "mcp" / "check-doc-metadata" / "scripts" / "run_check_doc_metadata.py",
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
        script_path=REPO_ROOT / "mcp" / "check-doc-links" / "scripts" / "run_check_doc_links.py",
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
        script_path=REPO_ROOT / "mcp" / "suggest-impacted-docs" / "scripts" / "run_suggest_impacted_docs.py",
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
            "changed_files": ["workflow_kit/server/read_only_entrypoint.py", "tests/check_read_only_mcp_server.py"],
            "latest_backlog_path": str(REPO_ROOT / "backlog" / "2026-04-22.md"),
        },
    ),
    ReadOnlyToolSpec(
        name="check_quickstart_stale_links",
        description="Check quickstart and README entry docs for stale or missing links.",
        script_path=REPO_ROOT / "mcp" / "check-quickstart-stale-links" / "scripts" / "run_check_quickstart_stale_links.py",
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
)


def get_tool_spec(tool_name: str) -> ReadOnlyToolSpec | None:
    for spec in READ_ONLY_TOOL_SPECS:
        if spec.name == tool_name:
            return spec
    return None


def build_server_manifest() -> dict[str, object]:
    return {
        "status": "ok",
        "tool_version": TOOL_VERSION,
        "server_name": READ_ONLY_SERVER_NAME,
        "tool_count": len(READ_ONLY_TOOL_SPECS),
        "tools": [
            {
                "name": spec.name,
                "description": spec.description,
                "script_path": str(spec.script_path),
                "transport_ready": False,
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
                },
                "payload_example": spec.payload_example,
            }
            for spec in READ_ONLY_TOOL_SPECS
        ],
    }
