#!/usr/bin/env python3
"""Set up .gitignore for the standard AI workflow kit."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Patterns that should be in .gitignore for a clean workflow setup
GITIGNORE_PATTERNS = [
    "# Workflow layer (selective tracking)",
    "/ANTIGRAVITY.md",
    "/AGENTS.md",
    "/GEMINI.md",
    "",
    "# Exclude duplicated engine/tool copies",
    "/ai-workflow/scripts/",
    "/ai-workflow/skills/",
    "/ai-workflow/workflow_kit/",
    "/ai-workflow/mcp/",
    "/ai-workflow/schemas/",
    "/ai-workflow/templates/",
    "/ai-workflow/examples/",
    "/ai-workflow/global-snippets/",
    "/ai-workflow/harnesses/",
    "/ai-workflow/tests/",
    "",
    "# Keep the data (memory) and core guides",
    "!/ai-workflow/README.md",
    "!/ai-workflow/WORKFLOW_INDEX.md",
    "!/ai-workflow/core/",
    "!/ai-workflow/memory/",
]


def ensure_gitignore_patterns(target_root: Path, dry_run: bool) -> list[str]:
    gitignore_path = target_root / ".gitignore"
    if not gitignore_path.exists():
        if dry_run:
            return ["Create .gitignore with standard patterns"]
        gitignore_path.write_text("\n".join(GITIGNORE_PATTERNS) + "\n", encoding="utf-8")
        return ["Created .gitignore"]

    content = gitignore_path.read_text(encoding="utf-8")
    added = []
    
    # Check for individual lines to avoid duplicate blocks
    lines_to_add = []
    
    # We use a marker to identify the block if we want to be clean, 
    # but for simplicity we'll just check if a key pattern exists.
    if "/ai-workflow/scripts/" not in content:
        lines_to_add.extend(["", "# Added by Workflow Setup Script"] + GITIGNORE_PATTERNS)
        added.append("Appended standard patterns to .gitignore")

    if lines_to_add and not dry_run:
        with gitignore_path.open("a", encoding="utf-8") as f:
            f.write("\n".join(lines_to_add) + "\n")
    
    return added


def main():
    parser = argparse.ArgumentParser(description="Set up .gitignore for the standard AI workflow.")
    parser.add_argument("--target-root", default=".", help="Target repository root.")
    parser.add_argument("--dry-run", action="store_true", help="Show changes without applying them.")
    args = parser.parse_args()

    target_root = Path(args.target_root).resolve()
    print(f"--- Setting up .gitignore in {target_root} ---")
    
    changes = ensure_gitignore_patterns(target_root, args.dry_run)
    
    if not changes:
        print("No changes needed. .gitignore is already up to date.")
    else:
        for change in changes:
            print(f"- {change}")
        if args.dry_run:
            print("\n[DRY RUN] No changes were written.")
        else:
            print("\n.gitignore updated successfully.")


if __name__ == "__main__":
    main()
