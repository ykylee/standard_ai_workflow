#!/usr/bin/env python3
import json
import os
import subprocess
from pathlib import Path

def test_relative_paths_in_state():
    repo_root = Path(__file__).resolve().parents[1]
    output_path = repo_root / "ai-workflow/memory/gemini/phase6/state.json"
    
    # Run the generator
    cmd = [
        "python3", "scripts/generate_workflow_state.py",
        "--project-profile-path", "docs/PROJECT_PROFILE.md",
        "--session-handoff-path", "ai-workflow/memory/gemini/phase6/session_handoff.md",
        "--work-backlog-index-path", "ai-workflow/memory/work_backlog.md",
        "--output-path", str(output_path),
        "--workspace-root", str(repo_root)
    ]
    
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(repo_root))
    if result.returncode != 0:
        print(f"Error: {result.stderr}")
        exit(1)
        
    # Load and verify state.json
    state = json.loads(output_path.read_text(encoding="utf-8"))
    
    print("\nVerifying source_of_truth paths...")
    sot = state.get("source_of_truth", {})
    for key, val in sot.items():
        if val:
            print(f"  {key}: {val}")
            if val.startswith("/") or (":" in val and "\\" in val): # Check for absolute paths (Unix/Windows)
                print(f"❌ Error: {key} is an absolute path: {val}")
                exit(1)
            else:
                print(f"✅ OK: {key} is relative")

    print("\nVerifying next_documents paths...")
    next_docs = state.get("next_documents", [])
    for doc in next_docs:
        print(f"  {doc}")
        if doc.startswith("/") or (":" in doc and "\\" in doc):
            print(f"❌ Error: next_document is an absolute path: {doc}")
            exit(1)
        else:
            print(f"✅ OK: relative")

    print("\n🎉 Path relative-ness check passed!")

if __name__ == "__main__":
    test_relative_paths_in_state()
