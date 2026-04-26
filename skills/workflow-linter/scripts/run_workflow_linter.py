#!/usr/bin/env python3
"""Runner for the workflow-linter skill."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

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
    parser.add_argument("--state-json-path")
    parser.add_argument("--handoff-path")
    parser.add_argument("--latest-backlog-path")
    parser.add_argument("--apply", action="store_true", help="Attempt to auto-fix some issues")
    parser.add_argument("--json", action="store_true", help="Output in standard JSON format")
    return parser.parse_args()

def main() -> int:
    args = parse_args()
    root = Path(args.project_root).resolve()
    
    # Resolve paths with fallbacks
    state_json_path = (
        Path(args.state_json_path).resolve() if args.state_json_path 
        else root / "ai-workflow/project/state.json"
    )
    handoff_path = (
        Path(args.handoff_path).resolve() if args.handoff_path 
        else root / "ai-workflow/project/session_handoff.md"
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
            latest_backlog_path = root / f"ai-workflow/project/backlog/{date.today().isoformat()}.md"

        source_context["latest_backlog_path"] = str(latest_backlog_path)

        # 1. Workflow Consistency (Docs)
        result_data = check_workflow_consistency(
            state_json_path=state_json_path,
            handoff_path=handoff_path,
            latest_backlog_path=latest_backlog_path
        )

        # 2. Maturity Consistency (SSOT)
        from workflow_kit.common.linter import check_maturity_consistency
        matrix_path = root / "core/maturity_matrix.json"
        roadmap_path = root / "core/workflow_kit_roadmap.md"
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
            # Auto-fix logic can be added here
            # For now, we just log that we would fix them
            pass

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
