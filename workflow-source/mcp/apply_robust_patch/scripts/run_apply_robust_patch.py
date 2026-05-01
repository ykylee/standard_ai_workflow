#!/usr/bin/env python3
import sys
import json
import argparse
from pathlib import Path

# Add workflow-source to path
REPO_ROOT = Path(__file__).resolve().parents[4]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from workflow_kit import __version__ as TOOL_VERSION
from workflow_kit.common.writing_bundle import apply_robust_patch_payload

def main():
    parser = argparse.ArgumentParser(description="Apply a robust Search-Replace patch to a file.")
    parser.add_argument("--file-path", required=True, help="Target file to patch.")
    parser.add_argument("--patch-content", required=True, help="The SEARCH/REPLACE block content.")
    args = parser.parse_args()

    result = apply_robust_patch_payload(
        file_path=args.file_path,
        patch_content=args.patch_content,
        tool_version=TOOL_VERSION
    )
    
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(0 if result["status"] == "ok" else 1)

if __name__ == "__main__":
    main()
