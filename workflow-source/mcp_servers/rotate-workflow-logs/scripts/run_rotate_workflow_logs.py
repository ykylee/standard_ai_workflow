#!/usr/bin/env python3
import sys
from pathlib import Path

# Add lib to path for common_utils
LIB_PATH = Path(__file__).resolve().parents[2] / "lib"
if str(LIB_PATH) not in sys.path:
    sys.path.insert(0, str(LIB_PATH))

from common_utils import inject_workflow_source, mcp_main

inject_workflow_source()
from workflow_kit.common.read_only_bundle import rotate_workflow_logs_payload

def build_args(parser):
    parser.add_argument("--handoff-path", required=True, help="Path to the session handoff document.")
    parser.add_argument("--max-done-items", type=int, default=10,
                        help="Maximum number of done items to keep in 'recently done' (default: 10).")

def main():
    mcp_main(
        description="Rotate old done items from handoff into baseline to prevent bloat.",
        arg_builder=build_args,
        payload_func=rotate_workflow_logs_payload,
    )

if __name__ == "__main__":
    main()
