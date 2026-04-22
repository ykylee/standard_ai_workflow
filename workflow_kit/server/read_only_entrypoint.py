#!/usr/bin/env python3
"""Draft entrypoint for the first read-only MCP tool bundle."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from workflow_kit import __version__ as TOOL_VERSION
from workflow_kit.server.read_only_registry import build_server_manifest, get_tool_spec


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Draft entrypoint for the read-only MCP bundle.")
    parser.add_argument("--list-tools", action="store_true", help="Print the bundled tool manifest as JSON.")
    parser.add_argument("--tool", help="Tool name from the read-only bundle registry.")
    parser.add_argument(
        "--payload-json",
        help="JSON object that will be converted into repeated CLI flags for the selected tool script.",
    )
    return parser.parse_args()


def payload_to_cli_args(payload: dict[str, Any]) -> list[str]:
    args: list[str] = []
    for key, value in payload.items():
        flag = f"--{key.replace('_', '-')}"
        if value is None:
            continue
        if isinstance(value, bool):
            if value:
                args.append(flag)
            continue
        if isinstance(value, list):
            for item in value:
                args.extend([flag, str(item)])
            continue
        args.extend([flag, str(value)])
    return args


def build_error_result(*, error: str, error_code: str, warnings: list[str], source_context: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "error",
        "tool_version": TOOL_VERSION,
        "error": error,
        "error_code": error_code,
        "warnings": warnings,
        "source_context": source_context,
    }


def invoke_tool(tool_name: str, payload_json: str | None) -> tuple[int, dict[str, Any]]:
    spec = get_tool_spec(tool_name)
    source_context = {"tool": tool_name, "payload_json": payload_json}
    if spec is None:
        return 1, build_error_result(
            error="알 수 없는 읽기 전용 MCP tool 이다.",
            error_code="unknown_read_only_tool",
            warnings=["등록된 tool 이름을 다시 확인해야 한다."],
            source_context=source_context,
        )
    if not payload_json:
        return 1, build_error_result(
            error="선택한 tool 을 실행하려면 payload JSON 이 필요하다.",
            error_code="missing_tool_payload",
            warnings=["`--payload-json` 에 JSON object 문자열을 전달해야 한다."],
            source_context=source_context,
        )
    try:
        payload = json.loads(payload_json)
    except json.JSONDecodeError:
        return 1, build_error_result(
            error="payload JSON 을 해석할 수 없다.",
            error_code="invalid_tool_payload",
            warnings=["`--payload-json` 은 JSON object 형태여야 한다."],
            source_context=source_context,
        )
    if not isinstance(payload, dict):
        return 1, build_error_result(
            error="payload JSON 은 object 형태여야 한다.",
            error_code="invalid_tool_payload_shape",
            warnings=["배열이나 문자열이 아니라 key/value object 를 전달해야 한다."],
            source_context=source_context,
        )

    cmd = [sys.executable, str(spec.script_path), *payload_to_cli_args(payload)]
    completed = subprocess.run(cmd, cwd=Path(__file__).resolve().parents[2], capture_output=True, text=True, check=False)
    try:
        parsed = json.loads(completed.stdout)
    except json.JSONDecodeError:
        parsed = build_error_result(
            error="하위 tool 이 JSON 출력을 반환하지 않았다.",
            error_code="invalid_tool_stdout",
            warnings=["script stdout/stderr 를 확인해야 한다."],
            source_context=source_context | {"returncode": completed.returncode, "stderr": completed.stderr.strip()},
        )
        return 1, parsed
    return completed.returncode, parsed


def main() -> int:
    args = parse_args()
    if args.list_tools:
        print(json.dumps(build_server_manifest(), ensure_ascii=False, indent=2))
        return 0
    if args.tool:
        returncode, payload = invoke_tool(args.tool, args.payload_json)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return returncode

    result = build_error_result(
        error="실행할 동작이 지정되지 않았다.",
        error_code="missing_server_action",
        warnings=["`--list-tools` 또는 `--tool <name> --payload-json '{...}'` 중 하나가 필요하다."],
        source_context={},
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
