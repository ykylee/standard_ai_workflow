#!/usr/bin/env python3
import subprocess
import json
import os

def test_git_history_summarizer():
    print("Testing git-history-summarizer MCP...")
    
    # Test Markdown format
    cmd_md = ["python3", "mcp/git-history-summarizer/scripts/run_git_history_summarizer.py", "--range", "HEAD~1..HEAD"]
    result_md = subprocess.run(cmd_md, capture_output=True, text=True, check=True)
    assert "Git 작업 요약" in result_md.stdout
    print("  [OK] Markdown output format")

    # Test JSON format
    cmd_json = ["python3", "mcp/git-history-summarizer/scripts/run_git_history_summarizer.py", "--range", "HEAD~1..HEAD", "--format", "json"]
    result_json = subprocess.run(cmd_json, capture_output=True, text=True, check=True)
    data = json.loads(result_json.stdout)
    assert data["status"] == "ok"
    assert "entries" in data
    assert len(data["entries"]) >= 1
    print("  [OK] JSON output format")

    print("All tests passed for git-history-summarizer!")

if __name__ == "__main__":
    try:
        test_git_history_summarizer()
    except Exception as e:
        print(f"Test failed: {e}")
        exit(1)
