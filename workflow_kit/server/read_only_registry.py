"""Registry for the first read-only MCP server bundle."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from workflow_kit import __version__ as TOOL_VERSION


REPO_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class ReadOnlyToolSpec:
    name: str
    description: str
    script_path: Path


READ_ONLY_SERVER_NAME = "workflow_read_only_bundle"

READ_ONLY_TOOL_SPECS: tuple[ReadOnlyToolSpec, ...] = (
    ReadOnlyToolSpec(
        name="latest_backlog",
        description="Locate the latest dated backlog document from an index or backlog directory.",
        script_path=REPO_ROOT / "mcp" / "latest-backlog" / "scripts" / "run_latest_backlog.py",
    ),
    ReadOnlyToolSpec(
        name="check_doc_metadata",
        description="Inspect markdown files and report missing required metadata fields.",
        script_path=REPO_ROOT / "mcp" / "check-doc-metadata" / "scripts" / "run_check_doc_metadata.py",
    ),
    ReadOnlyToolSpec(
        name="check_doc_links",
        description="Inspect markdown relative links and report broken targets.",
        script_path=REPO_ROOT / "mcp" / "check-doc-links" / "scripts" / "run_check_doc_links.py",
    ),
    ReadOnlyToolSpec(
        name="suggest_impacted_docs",
        description="Suggest impacted workflow documents from changed files and summary input.",
        script_path=REPO_ROOT / "mcp" / "suggest-impacted-docs" / "scripts" / "run_suggest_impacted_docs.py",
    ),
    ReadOnlyToolSpec(
        name="check_quickstart_stale_links",
        description="Check quickstart and README entry docs for stale or missing links.",
        script_path=REPO_ROOT / "mcp" / "check-quickstart-stale-links" / "scripts" / "run_check_quickstart_stale_links.py",
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
                "bundle_phase": "draft_entrypoint",
            }
            for spec in READ_ONLY_TOOL_SPECS
        ],
    }
