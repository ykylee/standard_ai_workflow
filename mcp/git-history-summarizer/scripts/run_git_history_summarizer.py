#!/usr/bin/env python3
import argparse
import subprocess
import json
import sys
import re
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional

@dataclass
class CommitEntry:
    subject: str
    hash: str
    author: str
    date: str
    category: str

def get_git_log(repo_path: str, commit_range: str) -> List[str]:
    try:
        cmd = ["git", "-C", repo_path, "log", "--pretty=format:%s|%h|%an|%ad", "--date=iso", commit_range]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        if not result.stdout.strip():
            return []
        return result.stdout.strip().split("\n")
    except subprocess.CalledProcessError as e:
        print(f"Error running git log: {e.stderr}", file=sys.stderr)
        return []

def categorize_message(message: str) -> str:
    m = message.lower()
    if any(kw in m for kw in ["feat", "add", "implement"]): return "Feature"
    if any(kw in m for kw in ["fix", "bug", "patch"]): return "Bug Fix"
    if any(kw in m for kw in ["docs", "readme", "markdown"]): return "Docs"
    if any(kw in m for kw in ["refactor", "clean", "simplify"]): return "Refactor"
    if any(kw in m for kw in ["test", "spec", "check"]): return "Test"
    if any(kw in m for kw in ["chore", "config", "build", "ci", "deps"]): return "Chore"
    return "Other"

def process_logs(logs: List[str]) -> List[CommitEntry]:
    entries = []
    for line in logs:
        parts = line.split("|")
        if len(parts) < 4: continue
        subject, h, author, date = parts[0], parts[1], parts[2], parts[3]
        category = categorize_message(subject)
        entries.append(CommitEntry(subject, h, author, date, category))
    return entries

def generate_markdown(entries: List[CommitEntry], commit_range: str) -> str:
    if not entries:
        return f"No commits found in range `{commit_range}`."
    
    cat_map: Dict[str, List[str]] = {}
    for e in entries:
        if e.category not in cat_map: cat_map[e.category] = []
        cat_map[e.category].append(f"- {e.subject} ([{e.hash}](https://github.com/_repo_/commit/{e.hash}))")
    
    md = [f"## Git 작업 요약 ({commit_range})\n"]
    for cat in ["Feature", "Bug Fix", "Refactor", "Docs", "Test", "Chore", "Other"]:
        if cat in cat_map:
            md.append(f"### {cat}")
            md.extend(cat_map[cat])
            md.append("")
    return "\n".join(md)

def main():
    parser = argparse.ArgumentParser(description="Summarize git history for session handoff.")
    parser.add_argument("--range", default="HEAD~3..HEAD", help="Commit range (e.g. HEAD~3..HEAD)")
    parser.add_argument("--format", choices=["markdown", "json"], default="markdown", help="Output format")
    parser.add_argument("--repo-path", default=".", help="Path to git repository")
    args = parser.parse_args()

    logs = get_git_log(args.repo_path, args.range)
    entries = process_logs(logs)

    if args.format == "json":
        output = {
            "status": "ok",
            "commit_count": len(entries),
            "range": args.range,
            "entries": [asdict(e) for e in entries],
            "categories": {cat: sum(1 for e in entries if e.category == cat) for cat in set(e.category for e in entries)}
        }
        print(json.dumps(output, indent=2, ensure_ascii=False))
    else:
        md_summary = generate_markdown(entries, args.range)
        print(md_summary)

if __name__ == "__main__":
    main()
