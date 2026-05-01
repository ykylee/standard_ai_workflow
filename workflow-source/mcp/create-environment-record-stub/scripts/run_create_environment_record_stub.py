#!/usr/bin/env python3
"""Prototype runner for create_environment_record_stub MCP."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from workflow_kit import __version__ as TOOL_VERSION
from workflow_kit.common.read_only_bundle import create_environment_record_stub_payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Run create_environment_record_stub MCP prototype.")
    parser.add_argument("--hostname", required=True)
    parser.add_argument("--os-type", required=True)
    args = parser.parse_args()

    payload = create_environment_record_stub_payload(
        hostname=args.hostname,
        os_type=args.os_type,
        tool_version=TOOL_VERSION,
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
