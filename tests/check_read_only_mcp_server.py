#!/usr/bin/env python3
"""Smoke test the draft read-only MCP server entrypoint."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
ENTRYPOINT = REPO_ROOT / "workflow_kit" / "server" / "read_only_entrypoint.py"


def run_json(args: list[str], *, expect_success: bool = True) -> tuple[int, dict[str, object]]:
    completed = subprocess.run(
        [sys.executable, str(ENTRYPOINT), *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if expect_success and completed.returncode != 0:
        raise AssertionError(f"Entrypoint failed unexpectedly: {completed.stderr}\n{completed.stdout}")
    return completed.returncode, json.loads(completed.stdout)


def main() -> int:
    _, manifest = run_json(["--list-tools"])
    if manifest["server_name"] != "workflow_read_only_bundle":
        raise AssertionError("Unexpected read-only server name.")
    if manifest["tool_count"] < 5:
        raise AssertionError("Expected at least five bundled read-only tools.")

    latest_backlog_payload = {
        "work_backlog_index_path": str(REPO_ROOT / "examples" / "acme_delivery_platform" / "work_backlog.md")
    }
    _, latest_backlog = run_json(
        ["--tool", "latest_backlog", "--payload-json", json.dumps(latest_backlog_payload, ensure_ascii=False)]
    )
    if latest_backlog["status"] != "ok":
        raise AssertionError("Expected latest_backlog tool dispatch to succeed.")
    if not latest_backlog["latest_backlog_path"]:
        raise AssertionError("Expected latest_backlog tool dispatch to return a path.")

    metadata_payload = {
        "doc_dir_path": str(REPO_ROOT / "examples" / "acme_delivery_platform")
    }
    _, metadata_result = run_json(
        ["--tool", "check_doc_metadata", "--payload-json", json.dumps(metadata_payload, ensure_ascii=False)]
    )
    if metadata_result["status"] != "ok":
        raise AssertionError("Expected check_doc_metadata dispatch to succeed.")
    if "checked_files" not in metadata_result:
        raise AssertionError("Expected check_doc_metadata dispatch to return checked_files.")

    failure_code, failure_payload = run_json(["--tool", "unknown_tool", "--payload-json", "{}"], expect_success=False)
    if failure_code == 0:
        raise AssertionError("Expected unknown tool dispatch to fail.")
    if failure_payload["error_code"] != "unknown_read_only_tool":
        raise AssertionError("Expected unknown_read_only_tool error code.")

    print("Read-only MCP server smoke check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
