#!/usr/bin/env python3
"""Generate checked-in JSON-RPC draft bridge fixtures."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from workflow_kit.server.read_only_jsonrpc import handle_jsonrpc_request, parse_request_json
from workflow_kit.server.read_only_registry import build_transport_tool_descriptors


def request_response_pair(name: str, request: dict[str, Any]) -> dict[str, Any]:
    response = handle_jsonrpc_request(request)
    if response is None:
        raise ValueError(f"Fixture request produced no response: {name}")
    return {
        "name": name,
        "request": request,
        "response": response,
    }


def raw_request_response_pair(name: str, raw_request: str) -> dict[str, Any]:
    request, response = parse_request_json(raw_request)
    if response is None:
        if request is None:
            raise ValueError(f"Raw fixture request produced neither request nor response: {name}")
        response = handle_jsonrpc_request(request)
    if response is None:
        raise ValueError(f"Raw fixture request produced no response: {name}")
    return {
        "name": name,
        "request": raw_request,
        "response": response,
    }


def build_jsonrpc_fixtures() -> dict[str, Any]:
    descriptors = build_transport_tool_descriptors()
    latest_backlog_payload = {
        "work_backlog_index_path": str(REPO_ROOT / "examples" / "acme_delivery_platform" / "work_backlog.md")
    }
    fixtures = [
        request_response_pair(
            "initialize",
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
        ),
        request_response_pair(
            "tools_list",
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
        ),
        request_response_pair(
            "latest_backlog_call_success",
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {"name": "latest_backlog", "arguments": latest_backlog_payload},
            },
        ),
        request_response_pair(
            "check_doc_metadata_call_schema_error",
            {
                "jsonrpc": "2.0",
                "id": 4,
                "method": "tools/call",
                "params": {"name": "check_doc_metadata", "arguments": {}},
            },
        ),
        request_response_pair(
            "unknown_method",
            {"jsonrpc": "2.0", "id": 5, "method": "unknown/method", "params": {}},
        ),
        raw_request_response_pair("malformed_json_parse_error", "{not-json"),
        raw_request_response_pair("non_object_invalid_request", "[]"),
    ]
    return {
        "status": "ok",
        "fixture_phase": "jsonrpc_draft_fixture",
        "transport_ready": False,
        "descriptor_target": descriptors["descriptor_target"],
        "tool_version": descriptors["tool_version"],
        "fixture_count": len(fixtures),
        "fixtures": fixtures,
    }


def main() -> int:
    print(json.dumps(build_jsonrpc_fixtures(), ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
