#!/usr/bin/env python3
"""MCP `plan_inbox` runner — 받은편지함의 미반영 계획 응답 (읽기 전용, plan_workbench_spec §8.3)."""
import sys
from pathlib import Path

LIB_PATH = Path(__file__).resolve().parents[2] / "lib"
if str(LIB_PATH) not in sys.path:
    sys.path.insert(0, str(LIB_PATH))

from common_utils import inject_workflow_source, mcp_main

inject_workflow_source()
from workflow_kit.common.plan_mcp import plan_inbox_payload


def build_args(parser):
    parser.add_argument("--workspace-root", required=False, default=None,
                        help="Workspace root of a workflow_kit project. Defaults to cwd.")
    parser.add_argument("--task-id", required=False, default=None, help="Only this task's responses.")


def main():
    mcp_main(
        description="Report plan responses waiting in the branch inbox (counts, per-file eligibility; no comment bodies).",
        arg_builder=build_args,
        payload_func=plan_inbox_payload,
    )


if __name__ == "__main__":
    main()
