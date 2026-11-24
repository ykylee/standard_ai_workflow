#!/usr/bin/env python3
"""Smoke test for MCP v1.0 SDK server implementation."""

from __future__ import annotations

import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"

if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

# We will try to import anyio and mcp client tools to run the test
try:
    import anyio
    from mcp import Client, StdioServerParameters
    HAS_CLIENT_DEPS = True
except ImportError:
    HAS_CLIENT_DEPS = False

async def run_v1_smoke() -> None:
    # Use latest_backlog_v1 as the test target
    server_script = SOURCE_ROOT / "mcp_servers" / "latest-backlog" / "scripts" / "run_latest_backlog_v1.py"
    
    server_params = StdioServerParameters(
        command=sys.executable,
        args=[str(server_script)],
        cwd=str(REPO_ROOT),
        env={
            **os.environ,
            "PYTHONPATH": str(SOURCE_ROOT),
        },
    )

    async with Client(server_params) as session:
        protocol_version = getattr(session, "protocol_version", getattr(session, "protocolVersion", None))
        if protocol_version != "2026-07-28":
            raise AssertionError(f"Expected modern MCP protocol, got {protocol_version!r}.")
        # List tools
        tools_result = await session.list_tools()
        tool_names = [t.name for t in tools_result.tools]
        print(f"Discovered tools: {tool_names}")

        if "latest_backlog" not in tool_names:
            raise AssertionError("latest_backlog tool not found in v1 server.")

        payload = {
            "work_backlog_index_path": str(SOURCE_ROOT / "examples" / "acme_delivery_platform" / "work_backlog.md")
        }
        result = await session.call_tool("latest_backlog", payload)
        is_error = getattr(result, "is_error", getattr(result, "isError", None))
        if is_error or not result.content:
            raise AssertionError("Expected latest_backlog to return content over modern MCP.")

def main() -> int:
    if not HAS_CLIENT_DEPS:
        print("Skipping MCP v1.0 smoke test: anyio or mcp not installed in the test runner environment.")
        return 0
    
    try:
        anyio.run(run_v1_smoke)
        print("MCP v1.0 smoke test passed.")
        return 0
    except Exception as e:
        print(f"MCP v1.0 smoke test failed: {e}")
        return 1

def test_case_1() -> None:
    assert main() == 0, "case_1 smoke FAIL"


def test_case_2() -> None:
    assert main() == 0, "case_2 smoke FAIL"


def test_case_3() -> None:
    assert main() == 0, "case_3 smoke FAIL"


def test_case_4() -> None:
    assert main() == 0, "case_4 smoke FAIL"


def test_case_5() -> None:
    assert main() == 0, "case_5 smoke FAIL"



if __name__ == "__main__":
    sys.exit(main())
