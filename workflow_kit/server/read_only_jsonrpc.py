#!/usr/bin/env python3
"""Draft JSON-RPC bridge for the read-only tool bundle.

This is intentionally a small fixture layer, not a full MCP SDK server.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from workflow_kit.server.read_only_entrypoint import invoke_tool
from workflow_kit.server.read_only_registry import READ_ONLY_SERVER_NAME, build_transport_tool_descriptors


JSONRPC_VERSION = "2.0"


def jsonrpc_result(request_id: object, result: dict[str, Any]) -> dict[str, Any]:
    return {"jsonrpc": JSONRPC_VERSION, "id": request_id, "result": result}


def jsonrpc_error(request_id: object, code: int, message: str, data: dict[str, Any] | None = None) -> dict[str, Any]:
    error: dict[str, Any] = {"code": code, "message": message}
    if data is not None:
        error["data"] = data
    return {"jsonrpc": JSONRPC_VERSION, "id": request_id, "error": error}


def parse_request_json(raw_json: str) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    try:
        request = json.loads(raw_json)
    except json.JSONDecodeError as exc:
        return None, jsonrpc_error(
            None,
            -32700,
            "Parse error",
            {"reason": "request must be valid JSON", "position": exc.pos},
        )
    if not isinstance(request, dict):
        return None, jsonrpc_error(None, -32600, "Invalid Request", {"reason": "request must be a JSON object"})
    return request, None


def build_initialize_result() -> dict[str, Any]:
    descriptors = build_transport_tool_descriptors()
    return {
        "serverInfo": {
            "name": READ_ONLY_SERVER_NAME,
            "version": descriptors["tool_version"],
        },
        "capabilities": {
            "tools": {
                "listChanged": False,
            },
        },
        "_meta": {
            "transport_ready": False,
            "bridge_phase": "jsonrpc_draft_fixture",
            "descriptor_target": descriptors["descriptor_target"],
        },
    }


def build_tools_list_result() -> dict[str, Any]:
    descriptors = build_transport_tool_descriptors()
    return {
        "tools": descriptors["tools"],
        "_meta": {
            "transport_ready": descriptors["transport_ready"],
            "descriptor_target": descriptors["descriptor_target"],
            "tool_count": descriptors["tool_count"],
        },
    }


def build_tools_call_result(name: str, arguments: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    returncode, payload = invoke_tool(name, json.dumps(arguments, ensure_ascii=False))
    if returncode != 0:
        return returncode, payload
    return 0, {
        "content": [
            {
                "type": "text",
                "text": json.dumps(payload, ensure_ascii=False, sort_keys=True),
            }
        ],
        "structuredContent": payload,
        "_meta": {
            "transport_ready": False,
            "bridge_phase": "jsonrpc_draft_fixture",
            "tool": name,
        },
    }


def handle_jsonrpc_request(request: dict[str, Any]) -> dict[str, Any] | None:
    request_id = request.get("id")
    if request.get("jsonrpc") != JSONRPC_VERSION:
        return jsonrpc_error(request_id, -32600, "Invalid Request", {"reason": "jsonrpc must be 2.0"})

    method = request.get("method")
    if not isinstance(method, str):
        return jsonrpc_error(request_id, -32600, "Invalid Request", {"reason": "method is required"})

    if method == "notifications/initialized":
        return None
    if method == "initialize":
        return jsonrpc_result(request_id, build_initialize_result())
    if method == "tools/list":
        return jsonrpc_result(request_id, build_tools_list_result())
    if method == "tools/call":
        params = request.get("params")
        if not isinstance(params, dict):
            return jsonrpc_error(request_id, -32602, "Invalid params", {"reason": "params must be an object"})
        name = params.get("name")
        arguments = params.get("arguments", {})
        if not isinstance(name, str):
            return jsonrpc_error(request_id, -32602, "Invalid params", {"reason": "params.name must be a string"})
        if not isinstance(arguments, dict):
            return jsonrpc_error(request_id, -32602, "Invalid params", {"reason": "params.arguments must be an object"})
        returncode, result = build_tools_call_result(name, arguments)
        if returncode != 0:
            return jsonrpc_error(request_id, -32000, "Tool call failed", result)
        return jsonrpc_result(request_id, result)

    return jsonrpc_error(request_id, -32601, "Method not found", {"method": method})


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Draft JSON-RPC bridge for the read-only bundle.")
    parser.add_argument("--request-json", help="Single JSON-RPC request object to handle and print.")
    parser.add_argument(
        "--stdio-lines",
        action="store_true",
        help="Read newline-delimited JSON-RPC request objects from stdin and print responses.",
    )
    return parser.parse_args()


def print_response(response: dict[str, Any] | None) -> None:
    if response is not None:
        print(json.dumps(response, ensure_ascii=False, sort_keys=True), flush=True)


def main() -> int:
    args = parse_args()
    if args.request_json:
        request, error = parse_request_json(args.request_json)
        if error is not None:
            print_response(error)
            return 1
        assert request is not None
        print_response(handle_jsonrpc_request(request))
        return 0
    if args.stdio_lines:
        for line in sys.stdin:
            stripped = line.strip()
            if not stripped:
                continue
            request, error = parse_request_json(stripped)
            if error is not None:
                print_response(error)
                continue
            assert request is not None
            print_response(handle_jsonrpc_request(request))
        return 0

    print_response(
        jsonrpc_error(None, -32600, "Invalid Request", {"reason": "--request-json or --stdio-lines is required"})
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
