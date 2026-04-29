#!/usr/bin/env python3
import subprocess
import json
import os
from pathlib import Path

def test_handoff_git_integration():
    print("Testing handoff-git integration...")
    
    # Path to latest backlog for testing (using the one from state.json or current date)
    latest_backlog = "ai-workflow/project/backlog/2026-04-27.md"
    
    cmd = [
        "python3", "mcp/create-session-handoff-draft/scripts/run_create_session_handoff_draft.py",
        "--latest-backlog-path", latest_backlog,
        "--git-range", "HEAD"
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    payload = json.loads(result.stdout)
    
    assert payload["status"] == "ok"
    assert "draft_handoff" in payload
    
    draft_text = "\n".join(payload["draft_handoff"])
    assert "Git 작업 이력 기반 요약" in draft_text
    assert "Git 작업 요약 (HEAD)" in draft_text
    
    print("  [OK] Handoff draft contains git summary")
    print("All tests passed for handoff-git integration!")

if __name__ == "__main__":
    try:
        test_handoff_git_integration()
    except Exception as e:
        print(f"Test failed: {e}")
        exit(1)
