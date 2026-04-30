#!/usr/bin/env python3
"""Runner for the workflow-linter skill."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT / "ai-workflow") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "ai-workflow"))

from workflow_kit import __version__ as TOOL_VERSION
from workflow_kit.common.errors import build_error_result
from workflow_kit.common.paths import resolve_existing_path
from workflow_kit.common.linter import check_workflow_consistency
from workflow_kit.common.runner import (
    build_runner_success_result,
    build_top_level_step_error_result,
    WorkflowStepError,
)

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Lint workflow documents for consistency.")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--project-profile-path")
    parser.add_argument("--state-json-path")
    parser.add_argument("--handoff-path")
    parser.add_argument("--latest-backlog-path")
    parser.add_argument("--apply", action="store_true", help="Attempt to auto-fix some issues")
    parser.add_argument("--json", action="store_true", help="Output in standard JSON format")
    return parser.parse_args()

def main() -> int:
    args = parse_args()
    root = Path(args.project_root).resolve()

    from workflow_kit.common.paths import workflow_branch_dir, workflow_memory_dir

    # Resolve project profile
    profile_path = None
    if args.project_profile_path:
        profile_path = Path(args.project_profile_path).resolve()
    else:
        # Fallback: look for docs/PROJECT_PROFILE.md
        candidate = root / "docs/PROJECT_PROFILE.md"
        if candidate.exists():
            profile_path = candidate
        else:
            candidate = root / "ai-workflow/memory/PROJECT_PROFILE.md"
            if candidate.exists():
                profile_path = candidate

    # Resolve paths with fallbacks
    branch_dir = workflow_branch_dir(profile_path) if profile_path else root / "ai-workflow/memory"

    state_json_path = (
        Path(args.state_json_path).resolve() if args.state_json_path
        else branch_dir / "state.json"
    )
    handoff_path = (
        Path(args.handoff_path).resolve() if args.handoff_path
        else branch_dir / "session_handoff.md"
    )

    source_context = {
        "project_root": str(root),
        "state_json_path": str(state_json_path),
        "handoff_path": str(handoff_path),
    }

    try:
        # Resolve latest backlog path
        latest_backlog_path = None
        if args.latest_backlog_path:
            latest_backlog_path = Path(args.latest_backlog_path).resolve()
        elif state_json_path.exists():
            try:
                state_data = json.loads(state_json_path.read_text(encoding="utf-8"))
                latest_backlog_path = Path(state_data["source_of_truth"]["latest_backlog_path"]).resolve()
            except Exception:
                pass

        if not latest_backlog_path:
            # Last resort fallback (guess by date)
            from datetime import date
            latest_backlog_path = branch_dir / f"backlog/{date.today().isoformat()}.md"

        source_context["latest_backlog_path"] = str(latest_backlog_path)

        # 1. Workflow Consistency (Docs)
        result_data = check_workflow_consistency(
            state_json_path=state_json_path,
            handoff_path=handoff_path,
            latest_backlog_path=latest_backlog_path
        )

        # 2. Maturity Consistency (SSOT)
        from workflow_kit.common.linter import check_maturity_consistency
        matrix_path = root / "ai-workflow/core/maturity_matrix.json"
        roadmap_path = root / "ai-workflow/core/workflow_kit_roadmap.md"
        maturity_data = check_maturity_consistency(matrix_path, roadmap_path, root)

        if maturity_data.get("status") != "skipped":
            # Merge results
            result_data["issues"].extend(maturity_data.get("issues", []))
            result_data["warnings"].extend(maturity_data.get("warnings", []))
            if maturity_data.get("status") == "issues_found":
                result_data["status"] = "issues_found"

            # Recalculate summary
            result_data["summary"]["maturity_errors"] = len([i for i in result_data["issues"] if i.get("type") == "maturity_error"])
            result_data["summary"]["total_issues"] = len(result_data["issues"])
            result_data["summary"]["sync_errors"] = len([i for i in result_data["issues"] if i.get("type") == "sync_error"])
            result_data["summary"]["broken_links"] = len([i for i in result_data["issues"] if i.get("type") == "broken_link"])

        if result_data.get("status") == "error":
            error_result = build_error_result(
                tool_version=TOOL_VERSION,
                error=result_data.get("description", "Unknown linter error"),
                error_code=result_data.get("error_code", "linter_failed"),
                warnings=result_data.get("warnings", []),
                source_context=source_context
            )
            print(json.dumps(error_result, ensure_ascii=False, indent=2))
            return 1

        written_paths = []
        if args.apply and result_data["issues"]:
            # Auto-fix logic
            modified_state = False
            for issue in result_data["issues"]:
                if issue["code"] == "task_status_mismatch" and "state.json" in issue["description"]:
                    # Extract task ID from description (simple heuristic)
                    task_match = re.search(r"Task (TASK-\d+)", issue["description"])
                    if task_match:
                        task_id = task_match.group(1)
                        # Add to state.json
                        if "session" not in state_data: state_data["session"] = {}
                        if "in_progress_items" not in state_data["session"]: state_data["session"]["in_progress_items"] = []

                        if task_id not in [t.split()[0] for t in state_data["session"]["in_progress_items"]]:
                            # Try to find full name from backlog/handoff if available
                            # For simplicity, just add the ID for now
                            state_data["session"]["in_progress_items"].append(task_id)
                            modified_state = True

            if modified_state:
                state_json_path.write_text(json.dumps(state_data, indent=2, ensure_ascii=False), encoding="utf-8")
                written_paths.append(str(state_json_path))
                # Update result_data status if all sync issues were fixed (optional, complex)

        if args.json:
            final_result = build_runner_success_result(
                tool_version=TOOL_VERSION,
                warnings=result_data.get("warnings", []),
                orchestration_plan={
                    "orchestrator": "main",
                    "note": "Linter results should be reviewed before proceeding with major state changes."
                },
                source_context=source_context,
                written_paths=written_paths,
                extra_fields={
                    "linter_status": result_data["status"],
                    "issues": result_data["issues"],
                    "summary": result_data["summary"]
                }
            )
            print(json.dumps(final_result, ensure_ascii=False, indent=2))
        else:
            issues = result_data["issues"]
            if not issues:
                print("✅ Workflow consistency check passed.")
            else:
                print(f"❌ Found {len(issues)} issues:")
                for issue in issues:
                    print(f"- [{issue['severity'].upper()}] ({issue['code']}) {issue['description']}")
                    print(f"  💡 Suggestion: {issue['fix_suggestion']}")

            if result_data.get("warnings"):
                print(f"\n⚠️ Warnings: {len(result_data['warnings'])}")
                for w in result_data["warnings"]:
                    print(f"  - {w}")

        return 1 if result_data["status"] == "issues_found" else 0

    except Exception as exc:
        error_result = build_error_result(
            tool_version=TOOL_VERSION,
            error=str(exc),
            error_code="workflow_linter_runtime_error",
            warnings=[],
            source_context=source_context
        )
        print(json.dumps(error_result, ensure_ascii=False, indent=2))
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
