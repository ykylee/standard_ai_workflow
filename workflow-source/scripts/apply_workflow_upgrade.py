#!/usr/bin/env python3
"""Apply and upgrade the standard AI workflow kit in a target repository."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

# Try to import version from the kit if possible
try:
    REPO_ROOT = Path(__file__).resolve().parents[2]
    SOURCE_ROOT = REPO_ROOT / "workflow-source"
    if str(SOURCE_ROOT) not in sys.path:
        sys.path.insert(0, str(SOURCE_ROOT))
    from workflow_kit import __version__ as WORKFLOW_KIT_VERSION
except ImportError:
    WORKFLOW_KIT_VERSION = "unknown"

# Reuse gitignore patterns from setup_gitignore if available, otherwise define here
try:
    from setup_gitignore import GITIGNORE_PATTERNS
except ImportError:
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

# Paths that are considered "Data" and should be preserved during upgrade
PRESERVE_RELATIVE_PATHS = [
    Path("ai-workflow/memory"),
    Path("ai-workflow/WORKFLOW_INDEX.md"),
    Path("ai-workflow/README.md"),
    Path("ai-workflow/VERSION"), # We handle this explicitly
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Upgrade the workflow kit in a target repository."
    )
    parser.add_argument(
        "--source-root",
        help="Path to the new version bundle or exported package root.",
    )
    parser.add_argument(
        "--target-root",
        default=".",
        help="Target repository root to upgrade.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show changes without applying them.",
    )
    parser.add_argument(
        "--setup-gitignore-only",
        action="store_true",
        help="Only run the .gitignore setup and exit.",
    )
    parser.add_argument(
        "--skip-gitignore",
        action="store_true",
        help="Do not modify .gitignore during upgrade.",
    )
    parser.add_argument(
        "--force-cleanup",
        action="store_true",
        help="Delete files in the target ai-workflow/ that are not in the new bundle.",
    )
    return parser.parse_args()


def get_file_hash(path: Path) -> str:
    hash_sha256 = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_sha256.update(chunk)
    return hash_sha256.hexdigest()


def ensure_gitignore_patterns(target_root: Path, dry_run: bool) -> list[str]:
    # Try to use the standalone script logic if it exists in the same dir
    try:
        from setup_gitignore import ensure_gitignore_patterns as standalone_ensure
        return standalone_ensure(target_root, dry_run)
    except ImportError:
        pass

    gitignore_path = target_root / ".gitignore"
    if not gitignore_path.exists():
        if dry_run:
            return ["Create .gitignore with standard patterns"]
        gitignore_path.write_text("\n".join(GITIGNORE_PATTERNS) + "\n", encoding="utf-8")
        return ["Created .gitignore"]

    content = gitignore_path.read_text(encoding="utf-8")
    added = []
    to_append = []
    
    if "/ai-workflow/scripts/" not in content:
        to_append.extend(["", "# Added by Workflow Upgrade Script"] + GITIGNORE_PATTERNS)
        added.append("Appended standard patterns to .gitignore")

    if to_append and not dry_run:
        with gitignore_path.open("a", encoding="utf-8") as f:
            f.write("\n".join(to_append) + "\n")
    
    return added


def get_current_version(target_root: Path) -> str:
    version_path = target_root / "ai-workflow" / "VERSION"
    if version_path.exists():
        return version_path.read_text(encoding="utf-8").strip()
    return "unknown"


def apply_upgrade(source_bundle: Path, target_root: Path, dry_run: bool, force_cleanup: bool) -> dict[str, list[str]]:
    results = {
        "created": [],
        "updated": [],
        "deleted": [],
        "preserved": [],
        "ignored": []
    }

    # 1. Map files in source bundle
    source_files: dict[Path, Path] = {}
    for p in source_bundle.rglob("*"):
        if p.is_file():
            source_files[p.relative_to(source_bundle)] = p

    # 2. Map files in target ai-workflow
    target_workflow_root = target_root / "ai-workflow"
    target_files: set[Path] = set()
    if target_workflow_root.exists():
        for p in target_workflow_root.rglob("*"):
            if p.is_file():
                target_files.add(p.relative_to(target_root))

    # 3. Handle specific version migrations (optional)
    # This is where you would add logic for specific version jumps if needed.
    # For example: if current_version < "v0.4.0": run_some_migration()
    
    # 4. Handle Update/Create
    for rel_path, src_path in source_files.items():
        dst_path = target_root / rel_path
        
        # Check if preserved
        is_preserved = any(rel_path == p or p in rel_path.parents for p in PRESERVE_RELATIVE_PATHS)
        
        if dst_path.exists():
            if is_preserved:
                results["preserved"].append(str(rel_path))
                continue
            
            src_hash = get_file_hash(src_path)
            dst_hash = get_file_hash(dst_path)
            
            if src_hash != dst_hash:
                results["updated"].append(str(rel_path))
                if not dry_run:
                    dst_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src_path, dst_path)
            else:
                results["ignored"].append(str(rel_path))
        else:
            results["created"].append(str(rel_path))
            if not dry_run:
                dst_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src_path, dst_path)

    # 4. Handle Cleanup (Stale files in ai-workflow/)
    if force_cleanup:
        for rel_path in target_files:
            if rel_path not in source_files:
                # Never delete preserved paths
                if any(rel_path == p or p in rel_path.parents for p in PRESERVE_RELATIVE_PATHS):
                    continue
                
                results["deleted"].append(str(rel_path))
                if not dry_run:
                    (target_root / rel_path).unlink()

    # 5. Update VERSION file
    if not dry_run:
        version_path = target_root / "ai-workflow" / "VERSION"
        version_path.parent.mkdir(parents=True, exist_ok=True)
        version_path.write_text(WORKFLOW_KIT_VERSION, encoding="utf-8")

    return results


def main():
    args = parse_args()
    target_root = Path(args.target_root).resolve()

    if args.setup_gitignore_only:
        print(f"--- Setting up .gitignore in {target_root} ---")
        changes = ensure_gitignore_patterns(target_root, args.dry_run)
        if changes:
            for c in changes:
                print(f"  - {c}")
        else:
            print("  - No changes needed.")
        sys.exit(0)

    if not args.source_root:
        print("Error: --source-root is required for upgrade.")
        sys.exit(1)

    source_root = Path(args.source_root).resolve()
    
    # Find bundle root
    bundle_root = source_root / "bundle" if (source_root / "bundle").is_dir() else source_root
    
    if not (bundle_root / "ai-workflow").is_dir():
        print(f"Error: Could not find ai-workflow/ in {bundle_root}")
        sys.exit(1)

    current_version = get_current_version(target_root)
    print(f"--- Upgrading Workflow Kit in {target_root} ---")
    print(f"Current version: {current_version}")
    print(f"Target version:  {WORKFLOW_KIT_VERSION}")
    
    if args.dry_run:
        print("[DRY RUN] No changes will be written.")

    # Apply file changes
    results = apply_upgrade(bundle_root, target_root, args.dry_run, args.force_cleanup)
    
    # Apply .gitignore changes
    gitignore_changes = []
    if not args.skip_gitignore:
        gitignore_changes = ensure_gitignore_patterns(target_root, args.dry_run)

    # Print Summary
    print(f"\nSummary of changes:")
    print(f"- Created:   {len(results['created'])}")
    print(f"- Updated:   {len(results['updated'])}")
    print(f"- Deleted:   {len(results['deleted'])}")
    print(f"- Preserved: {len(results['preserved'])}")
    print(f"- Ignored:   {len(results['ignored'])} (already up to date)")
    print(f"- gitignore: {len(gitignore_changes)} changes")

    if results["updated"]:
        print("\nUpdated files:")
        for p in results["updated"]:
            print(f"  [OVERWRITE] {p}")

    if results["deleted"]:
        print("\nDeleted files (stale):")
        for p in results["deleted"]:
            print(f"  [DELETE]    {p}")

    if gitignore_changes:
        print("\nGitignore updates:")
        for c in gitignore_changes:
            print(f"  - {c}")

    print("\nUpgrade completed successfully.")


if __name__ == "__main__":
    main()
