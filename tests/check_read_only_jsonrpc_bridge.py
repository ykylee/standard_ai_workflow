#!/usr/bin/env python3
"""Smoke test the draft JSON-RPC bridge for the read-only bundle."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
BRIDGE = REPO_ROOT / "workflow_kit" / "server" / "read_only_jsonrpc.py"


def run_request(request: dict[str, object]) -> dict[str, object]:
    completed = subprocess.run(
        [sys.executable, str(BRIDGE), "--request-json", json.dumps(request, ensure_ascii=False)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    if not completed.stdout.strip():
        raise AssertionError("Expected JSON-RPC response on stdout.")
    return json.loads(completed.stdout)


def main() -> int:
    initialize = run_request({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
    if initialize["result"]["serverInfo"]["name"] != "workflow_read_only_bundle":
        raise AssertionError("Expected read-only bundle serverInfo name.")
    if initialize["result"]["_meta"]["transport_ready"] is not False:
        raise AssertionError("Expected draft bridge to remain transport_ready=false.")

    tools_list = run_request({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
    tools = tools_list["result"]["tools"]
    if len(tools) < 5:
        raise AssertionError("Expected at least five read-only tools.")
    latest_backlog = next((tool for tool in tools if tool["name"] == "latest_backlog"), None)
    if latest_backlog is None:
        raise AssertionError("Expected latest_backlog tool descriptor.")
    if latest_backlog["annotations"]["readOnlyHint"] is not True:
        raise AssertionError("Expected readOnlyHint annotation.")

    call_payload = {
        "work_backlog_index_path": str(REPO_ROOT / "examples" / "acme_delivery_platform" / "work_backlog.md")
    }
    tool_call = run_request(
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": "latest_backlog", "arguments": call_payload},
        }
    )
    result = tool_call["result"]
    if result["structuredContent"]["status"] != "ok":
        raise AssertionError("Expected latest_backlog JSON-RPC tool call to succeed.")
    if result["content"][0]["type"] != "text":
        raise AssertionError("Expected text content wrapper.")
    if result["_meta"]["bridge_phase"] != "jsonrpc_draft_fixture":
        raise AssertionError("Expected JSON-RPC draft bridge phase metadata.")

    error_call = run_request(
        {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {"name": "check_doc_metadata", "arguments": {}},
        }
    )
    if error_call["error"]["code"] != -32000:
        raise AssertionError("Expected tool-call failure to map to JSON-RPC server error.")
    if error_call["error"]["data"]["error_code"] != "invalid_tool_payload_schema":
        raise AssertionError("Expected entrypoint error payload in JSON-RPC error data.")

    missing_method = run_request({"jsonrpc": "2.0", "id": 5, "method": "unknown/method", "params": {}})
    if missing_method["error"]["code"] != -32601:
        raise AssertionError("Expected unknown methods to return Method not found.")

    print("Read-only JSON-RPC bridge smoke check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
