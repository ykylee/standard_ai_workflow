#!/usr/bin/env python3
"""MCP `plan_import` runner — 계획 응답 반영 (write, 기본 dry-run, plan_workbench_spec §8.3)."""
import sys
from pathlib import Path

LIB_PATH = Path(__file__).resolve().parents[2] / "lib"
if str(LIB_PATH) not in sys.path:
    sys.path.insert(0, str(LIB_PATH))

from common_utils import inject_workflow_source, mcp_main

inject_workflow_source()
from workflow_kit.common.plan_mcp import plan_import_payload


def build_args(parser):
    parser.add_argument("--workspace-root", required=False, default=None,
                        help="Workspace root of a workflow_kit project. Defaults to cwd.")
    parser.add_argument("--task-id", required=False, default=None, help="Task whose inbox responses to apply.")
    parser.add_argument("--discard", required=False, default=None, help="Response file to set aside as .rejected.md.")
    parser.add_argument("--reason", required=False, default=None, help="Why the response is discarded.")
    parser.add_argument("--response", required=False, default=None, help="Apply only this inbox response file.")
    parser.add_argument("--apply", action="store_true", help="Actually move and write (default: dry run).")


def main():
    mcp_main(
        description="Apply plan responses from the branch inbox to a task (dry run unless --apply), or discard one.",
        arg_builder=build_args,
        payload_func=plan_import_payload,
    )


if __name__ == "__main__":
    main()
