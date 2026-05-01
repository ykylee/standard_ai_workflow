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
from workflow_kit.common.read_only_bundle import smart_context_reader_payload

def main():
    parser = argparse.ArgumentParser(description="Extract specific function or class blocks from a Python file.")
    parser.add_argument("--file-path", required=True, help="Path to the Python file.")
    parser.add_argument("--symbols", nargs="*", help="List of function or class names to extract.")
    args = parser.parse_args()

    result = smart_context_reader_payload(
        file_path=args.file_path,
        symbols=args.symbols,
        tool_version=TOOL_VERSION
    )
    
    if result["status"] == "ok":
        print("\n\n".join(result["extracted_content"]))
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        sys.exit(1)

if __name__ == "__main__":
    main()
