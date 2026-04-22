"""Direct-call adapter for the first read-only MCP bundle."""

from __future__ import annotations

from typing import Any

from workflow_kit.common.read_only_bundle import (
    check_doc_links_payload,
    check_doc_metadata_payload,
    check_quickstart_stale_links_payload,
    latest_backlog_payload,
    suggest_impacted_docs_payload,
)


def invoke_read_only_tool(*, tool_name: str, payload: dict[str, Any], tool_version: str) -> dict[str, Any]:
    if tool_name == "latest_backlog":
        return latest_backlog_payload(
            backlog_dir_path=payload.get("backlog_dir_path"),
            work_backlog_index_path=payload.get("work_backlog_index_path"),
            tool_version=tool_version,
        )
    if tool_name == "check_doc_metadata":
        return check_doc_metadata_payload(doc_dir_path=str(payload["doc_dir_path"]), tool_version=tool_version)
    if tool_name == "check_doc_links":
        return check_doc_links_payload(doc_dir_path=str(payload["doc_dir_path"]), tool_version=tool_version)
    if tool_name == "suggest_impacted_docs":
        return suggest_impacted_docs_payload(
            changed_files=[str(item) for item in payload["changed_files"]],
            session_handoff_path=payload.get("session_handoff_path"),
            latest_backlog_path=payload.get("latest_backlog_path"),
            work_backlog_index_path=payload.get("work_backlog_index_path"),
            tool_version=tool_version,
        )
    if tool_name == "check_quickstart_stale_links":
        return check_quickstart_stale_links_payload(
            quickstart_paths=[str(item) for item in payload["quickstart_paths"]],
            project_profile_path=payload.get("project_profile_path"),
            session_handoff_path=payload.get("session_handoff_path"),
            work_backlog_index_path=payload.get("work_backlog_index_path"),
            agents_path=payload.get("agents_path"),
            tool_version=tool_version,
        )
    raise KeyError(tool_name)
