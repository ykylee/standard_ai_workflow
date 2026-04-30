#!/usr/bin/env python3
"""Prototype runner for create_session_handoff_draft MCP."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT / "ai-workflow") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "ai-workflow"))

from workflow_kit import __version__ as TOOL_VERSION
from workflow_kit.common.read_only_bundle import create_session_handoff_draft_payload
from workflow_kit.common.git import summarize_git_history


def main() -> int:
    parser = argparse.ArgumentParser(description="Run create_session_handoff_draft MCP prototype.")
    parser.add_argument("--latest-backlog-path")
    parser.add_argument("--git-range", help="Commit range for git summary (e.g. HEAD~3..HEAD)")
    parser.add_argument("--repo-path", default=".", help="Path to git repository")
    args = parser.parse_args()

    git_summary = None
    if args.git_range:
        summary_data = summarize_git_history(repo_path=args.repo_path, commit_range=args.git_range)
        git_summary = summary_data["markdown"]

    payload = create_session_handoff_draft_payload(
        latest_backlog_path=args.latest_backlog_path,
        git_summary=git_summary,
        tool_version=TOOL_VERSION,
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
