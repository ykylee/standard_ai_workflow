#!/usr/bin/env python3
"""Verify checked-in JSON-RPC draft bridge fixtures stay aligned with runtime output."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "generate_read_only_jsonrpc_fixtures.py"
FIXTURE_PATH = REPO_ROOT / "schemas" / "read_only_jsonrpc_fixtures.json"

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.generate_read_only_jsonrpc_fixtures import build_jsonrpc_fixtures


def main() -> int:
    checked_in = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    runtime = build_jsonrpc_fixtures()
    if checked_in != runtime:
        raise AssertionError("Checked-in read_only_jsonrpc_fixtures.json is out of date.")

    completed = subprocess.run(
        [sys.executable, str(SCRIPT_PATH)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    script_output = json.loads(completed.stdout)
    if script_output != runtime:
        raise AssertionError("generate_read_only_jsonrpc_fixtures.py output does not match runtime output.")

    if checked_in["fixture_phase"] != "jsonrpc_draft_fixture":
        raise AssertionError("Expected JSON-RPC draft fixture phase.")
    if checked_in["transport_ready"] is not False:
        raise AssertionError("Expected fixtures to remain transport_ready=false.")
    names = [fixture["name"] for fixture in checked_in["fixtures"]]
    expected_names = [
        "initialize",
        "tools_list",
        "latest_backlog_call_success",
        "check_doc_metadata_call_schema_error",
        "unknown_method",
        "malformed_json_parse_error",
        "non_object_invalid_request",
    ]
    if names != expected_names:
        raise AssertionError("Unexpected JSON-RPC fixture ordering.")

    success = checked_in["fixtures"][2]["response"]["result"]
    if success["structuredContent"]["status"] != "ok":
        raise AssertionError("Expected successful call fixture to contain structuredContent.")
    schema_error = checked_in["fixtures"][3]["response"]["error"]
    if schema_error["code"] != -32000:
        raise AssertionError("Expected schema failure fixture to use JSON-RPC server error code.")
    if schema_error["data"]["error_code"] != "invalid_tool_payload_schema":
        raise AssertionError("Expected schema failure fixture to preserve entrypoint error code.")
    malformed = checked_in["fixtures"][5]["response"]["error"]
    if malformed["code"] != -32700:
        raise AssertionError("Expected malformed JSON fixture to preserve Parse error.")
    non_object = checked_in["fixtures"][6]["response"]["error"]
    if non_object["code"] != -32600:
        raise AssertionError("Expected non-object request fixture to preserve Invalid Request.")

    print("Read-only JSON-RPC fixture generation check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
