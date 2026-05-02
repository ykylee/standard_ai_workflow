#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path
from dataclasses import asdict

REPO_ROOT = Path(__file__).resolve().parents[4]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from workflow_kit.common.git import summarize_git_history

def main():
    parser = argparse.ArgumentParser(description="Summarize git history for session handoff.")
    parser.add_argument("--range", default="HEAD~3..HEAD", help="Commit range (e.g. HEAD~3..HEAD)")
    parser.add_argument("--format", choices=["markdown", "json"], default="markdown", help="Output format")
    parser.add_argument("--repo-path", default=".", help="Path to git repository")
    args = parser.parse_args()

    summary_data = summarize_git_history(args.repo_path, args.range)

    if args.format == "json":
        output = {
            "status": "ok",
            "commit_count": summary_data["commit_count"],
            "range": args.range,
            "entries": [asdict(e) for e in summary_data["entries"]],
            "categories": {cat: sum(1 for e in summary_data["entries"] if e.category == cat) for cat in set(e.category for e in summary_data["entries"])}
        }
        print(json.dumps(output, indent=2, ensure_ascii=False))
    else:
        print(summary_data["markdown"])

if __name__ == "__main__":
    main()
