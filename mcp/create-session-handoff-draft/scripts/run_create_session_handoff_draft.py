#!/usr/bin/env python3
"""Prototype runner for create_session_handoff_draft MCP."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from workflow_kit import __version__ as TOOL_VERSION
from workflow_kit.common.read_only_bundle import create_session_handoff_draft_payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Run create_session_handoff_draft MCP prototype.")
    parser.add_argument("--latest-backlog-path")
    args = parser.parse_args()

    payload = create_session_handoff_draft_payload(
        latest_backlog_path=args.latest_backlog_path,
        tool_version=TOOL_VERSION,
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
