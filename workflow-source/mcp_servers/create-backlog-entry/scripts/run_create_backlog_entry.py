#!/usr/bin/env python3
import sys
from pathlib import Path

# Add lib to path for common_utils
LIB_PATH = Path(__file__).resolve().parents[2] / "lib"
if str(LIB_PATH) not in sys.path:
    sys.path.insert(0, str(LIB_PATH))

from common_utils import inject_workflow_source, mcp_main

inject_workflow_source()
from workflow_kit.common.read_only_bundle import create_backlog_entry_payload

TOOL_VERSION = "0.5.10-beta"

def build_args(parser):
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--task-name", required=True)
    parser.add_argument("--request-date", required=True)
    parser.add_argument("--status", default="planned")
    parser.add_argument("--priority", default="high")
    # ADR-027 M-004: roadmap gate — CLI 와 같은 단일 판정 함수를 거친다.
    parser.add_argument("--workspace-root", required=False, default=".",
                        help="Workspace root for the ADR-027 roadmap gate. Defaults to cwd.")
    parser.add_argument("--wbs", required=False, default=None,
                        help="WBS leaf ref 'M-NNN/WBS-N.N', or 'exempt' with a reason.")
    parser.add_argument("--wbs-exempt-reason", required=False, default=None,
                        help="Mandatory reason when wbs='exempt'.")

def main():
    mcp_main(
        description="Run create_backlog_entry MCP prototype.",
        arg_builder=build_args,
        payload_func=create_backlog_entry_payload
    )

if __name__ == "__main__":
    main()
