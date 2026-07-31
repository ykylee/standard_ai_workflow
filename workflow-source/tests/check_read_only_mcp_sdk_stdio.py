#!/usr/bin/env python3
"""Smoke test the official MCP SDK stdio candidate through a real MCP client session.

## 1.x / 2.x 양쪽 (TASK-2026-07-31-main-001)

이 검사는 **클라이언트 쪽** 이라 SDK 의 응답 모델을 직접 읽는다. mcp 2.0.0 이 모델
field 를 snake_case 로 바꾸면서 (`serverInfo` → `server_info`, `isError` → `is_error`)
이 파일이 2.x 에서 깨져 있었다. 서버 쪽은 §2.43 에서 camel alias 로 양쪽을 받게
이관했지만, **읽는 쪽은 그 이관 범위에 없었다** — §2.41 과 같은 모양이다.

깨진 것을 아무도 못 본 이유는 이 검사가 smoke 에서만 돌고, smoke 는
`requirements-dev.txt` 의 핀 때문에 1.x 로만 돌기 때문이다. `mcp-sdk-matrix` workflow
가 이 구멍을 메우고, 실제로 그 matrix 가 이 결함을 처음 잡았다.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

try:
    import anyio
    from mcp import ClientSession
    from mcp.client.stdio import StdioServerParameters, stdio_client
    HAS_MCP_SDK = True
except ImportError:
    HAS_MCP_SDK = False


REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"


def _field(model: object, *names: str) -> Any:
    """1.x/2.x 어느 이름으로 오든 같은 값을 읽는다.

    `getattr(model, name, None)` 을 이어 붙이면 **어느 이름도 없을 때 조용히 None** 이
    되어, 다음 rename 에서 검사가 통과해 버린다. 그래서 없으면 실패시킨다 — 이 파일이
    이번에 깨진 방식이 정확히 "이름이 옮겨졌는데 아무도 안 봤다" 였다.
    """
    for name in names:
        if hasattr(model, name):
            return getattr(model, name)
    raise AssertionError(
        f"{type(model).__name__} 에 {names} 중 어느 이름도 없다 — SDK 가 또 field 를 옮겼는가?"
    )


async def run_stdio_smoke() -> None:
    server = StdioServerParameters(
        command=sys.executable,
        args=["-m", "workflow_kit.server.read_only_mcp_sdk", "--stdio-sdk"],
        cwd=str(REPO_ROOT),
        env={
            **os.environ,
            "PYTHONPATH": str(SOURCE_ROOT),
        },
    )

    async with stdio_client(server) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            initialize = await session.initialize()
            if _field(initialize, "server_info", "serverInfo").name != "workflow_read_only_bundle":
                raise AssertionError("Expected stdio SDK server to expose read-only bundle server name.")

            tools_result = await session.list_tools()
            if len(tools_result.tools) < 6:
                raise AssertionError(f"Expected at least six read-only tools over stdio SDK session, got {len(tools_result.tools)}.")
            latest_backlog = next((tool for tool in tools_result.tools if tool.name == "latest_backlog"), None)
            if latest_backlog is None:
                raise AssertionError("Expected latest_backlog tool over stdio SDK session.")
            if latest_backlog.annotations is None or _field(
                latest_backlog.annotations, "read_only_hint", "readOnlyHint"
            ) is not True:
                raise AssertionError("Expected latest_backlog tool to remain read-only annotated.")

            create_backlog_entry = next((tool for tool in tools_result.tools if tool.name == "create_backlog_entry"), None)
            if create_backlog_entry is None:
                raise AssertionError("Expected create_backlog_entry tool over stdio SDK session.")

            latest_backlog_payload = {
                "work_backlog_index_path": str(SOURCE_ROOT / "examples" / "acme_delivery_platform" / "work_backlog.md")
            }
            call_result = await session.call_tool("latest_backlog", latest_backlog_payload)
            if _field(call_result, "is_error", "isError"):
                raise AssertionError("Expected latest_backlog stdio SDK call to succeed.")
            call_structured = _field(call_result, "structured_content", "structuredContent")
            if call_structured is None or call_structured["status"] != "ok":
                raise AssertionError("Expected stdio SDK call to preserve structuredContent.")

            schema_error = await session.call_tool("check_doc_metadata", {})
            if not _field(schema_error, "is_error", "isError"):
                raise AssertionError("Expected invalid check_doc_metadata payload to surface as tool error.")
            error_structured = _field(schema_error, "structured_content", "structuredContent")
            if error_structured is None:
                raise AssertionError("Expected failing stdio SDK call to preserve structuredContent.")
            if error_structured["error_code"] != "invalid_tool_payload_schema":
                raise AssertionError("Expected schema-invalid stdio SDK call to preserve entrypoint error code.")


def main() -> int:
    if not HAS_MCP_SDK:
        print("Skipping Read-only MCP SDK stdio smoke check: mcp or anyio not installed.")
        return 0
    anyio.run(run_stdio_smoke)
    print("Read-only MCP SDK stdio smoke check passed.")
    return 0


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
    raise SystemExit(main())
