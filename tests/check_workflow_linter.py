#!/usr/bin/env python3
import json
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

def run_linter(project_root: Path, extra_args: list[str] = []) -> dict:
    cmd = [
        sys.executable,
        str(REPO_ROOT / "skills/workflow-linter/scripts/run_workflow_linter.py"),
        "--project-root", str(project_root),
        "--json"
    ] + extra_args
    result = subprocess.run(cmd, capture_output=True, text=True)
    try:
        return json.loads(result.stdout)
    except:
        print("STDOUT:", result.stdout)
        print("STDERR:", result.stderr)
        return {"status": "error", "error": "Failed to parse JSON output"}

def test_linter_pass():
    print("Testing linter pass case...")
    with tempfile.TemporaryDirectory() as tmp_dir:
        root = Path(tmp_dir)
        (root / "ai-workflow/memory/backlog").mkdir(parents=True)
        
        state_json = root / "ai-workflow/memory/state.json"
        handoff = root / "ai-workflow/memory/session_handoff.md"
        backlog = root / "ai-workflow/memory/backlog/2026-04-26.md"
        
        state_json.write_text(json.dumps({
            "source_of_truth": {"latest_backlog_path": str(backlog)},
            "session": {"in_progress_items": ["TASK-001 Test task"]},
            "project": {"project_name": "Test"}
        }))
        # Format matters: extract_list_after_label needs the exact prefix "- Label:"
        handoff.write_text("## 1. 현재 작업 요약\n- 현재 기준선: Test\n- 현재 주 작업 축: Test\n\n## 2. 진행 중 작업\n- 현재 `in_progress` 작업:\n  - TASK-001 Test task")
        backlog.write_text("## TASK-001 Test task\n- 상태: in_progress")
        
        # Valid link
        readme = root / "README.md"
        readme.write_text("Hello")
        handoff.write_text(handoff.read_text() + "\n\n[README](../../README.md)")

        result = run_linter(root)
        if result["status"] != "ok":
            print(f"FAILED. Result: {json.dumps(result, indent=2, ensure_ascii=False)}")
        assert result["status"] == "ok", f"Expected ok, got {result['status']}"
        assert not result["issues"], f"Expected no issues, but found: {result['issues']}"
        print("✅ Pass case successful.")

def test_linter_fail_task_mismatch():
    print("Testing linter task mismatch case...")
    with tempfile.TemporaryDirectory() as tmp_dir:
        root = Path(tmp_dir)
        (root / "ai-workflow/memory/backlog").mkdir(parents=True)
        
        state_json = root / "ai-workflow/memory/state.json"
        handoff = root / "ai-workflow/memory/session_handoff.md"
        backlog = root / "ai-workflow/memory/backlog/2026-04-26.md"
        
        state_json.write_text(json.dumps({
            "source_of_truth": {"latest_backlog_path": str(backlog)},
            "session": {"in_progress_items": ["TASK-001 Test task"]},
            "project": {"project_name": "Test"}
        }))
        handoff.write_text("## 1. 현재 작업 요약\n- 현재 기준선: Test\n- 현재 주 작업 축: Test\n\n## 2. 진행 중 작업\n- 현재 `in_progress` 작업:\n  - (Empty)") # TASK-001 missing
        backlog.write_text("## TASK-001 Test task\n- 상태: in_progress")

        result = run_linter(root)
        assert result["linter_status"] == "issues_found"
        task_issues = [i for i in result["issues"] if i["code"] == "task_status_mismatch"]
        assert task_issues, "Expected task status mismatch issue"
        print("✅ Task mismatch detection successful.")

def test_linter_fail_broken_link():
    print("Testing linter broken link case...")
    with tempfile.TemporaryDirectory() as tmp_dir:
        root = Path(tmp_dir)
        (root / "ai-workflow/memory/backlog").mkdir(parents=True)
        
        state_json = root / "ai-workflow/memory/state.json"
        handoff = root / "ai-workflow/memory/session_handoff.md"
        backlog = root / "ai-workflow/memory/backlog/2026-04-26.md"
        
        state_json.write_text(json.dumps({
            "source_of_truth": {"latest_backlog_path": str(backlog)},
            "session": {"in_progress_items": []},
            "project": {"project_name": "Test"}
        }))
        handoff.write_text("## 1. 현재 작업 요약\n- 현재 기준선: Test\n- 현재 주 작업 축: Test\n\n[Non-existent File](../../missing.md)")
        backlog.write_text("Nothing here")

        result = run_linter(root)
        assert result["linter_status"] == "issues_found"
        link_issues = [i for i in result["issues"] if i["code"] == "file_not_found"]
        assert link_issues, "Expected broken link issue"
        print("✅ Broken link detection successful.")

if __name__ == "__main__":
    try:
        test_linter_pass()
        test_linter_fail_task_mismatch()
        test_linter_fail_broken_link()
        print("\n🎉 All workflow-linter smoke tests passed!")
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)
