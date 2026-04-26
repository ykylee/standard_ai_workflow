import json
import re
from pathlib import Path
from typing import Dict, List, Any

from workflow_kit.common.project_docs import parse_backlog, parse_handoff

def check_workflow_consistency(
    state_json_path: Path,
    handoff_path: Path,
    latest_backlog_path: Path
) -> Dict[str, Any]:
    issues = []
    warnings = []
    
    # Load data
    try:
        if not state_json_path.exists():
            return {"status": "error", "error_code": "missing_state_json", "description": "state.json file not found"}
        state = json.loads(state_json_path.read_text(encoding="utf-8"))
    except Exception as e:
        return {"status": "error", "error_code": "state_json_load_failure", "description": f"Failed to load state.json: {e}"}
        
    try:
        handoff = parse_handoff(handoff_path)
    except Exception as e:
        warnings.append(f"Failed to parse handoff: {e}")
        handoff = {}

    try:
        backlog = parse_backlog(latest_backlog_path)
    except Exception as e:
        warnings.append(f"Failed to parse backlog: {e}")
        backlog = {}
    
    # 1. Check in_progress consistency
    backlog_in_progress = {item.split()[0] for item in backlog.get("in_progress_items", []) if item.startswith("TASK-")}
    handoff_in_progress = {item.split()[0] for item in handoff.get("in_progress_items", []) if item.startswith("TASK-") and "N/A" not in item}
    state_in_progress = {item.split()[0] for item in state.get("session", {}).get("in_progress_items", []) if item.startswith("TASK-") and "N/A" not in item}
    
    all_tasks = backlog_in_progress | handoff_in_progress | state_in_progress
    for task in all_tasks:
        missing = []
        if task not in backlog_in_progress: missing.append("backlog")
        if task not in handoff_in_progress: missing.append("handoff")
        if task not in state_in_progress: missing.append("state.json")
        
        if missing:
            issues.append({
                "type": "sync_error",
                "code": "task_status_mismatch",
                "description": f"Task {task} is inconsistent. Missing in: {', '.join(missing)}",
                "severity": "medium",
                "fix_suggestion": f"Ensure {task} is listed in all three core documents."
            })

    # 2. Check for bloat in handoff
    done_items = handoff.get("recent_done_items", [])
    if len(done_items) > 10:
        issues.append({
            "type": "bloat_warning",
            "code": "handoff_bloat",
            "description": f"Handoff has {len(done_items)} recently done items.",
            "severity": "low",
            "fix_suggestion": "Move older tasks to baseline summary and keep only last 5-10 in recently done."
        })

    # 3. Check for broken links in handoff/backlog (simple regex)
    for path in [handoff_path, latest_backlog_path]:
        if not path.exists():
            continue
        content = path.read_text(encoding="utf-8")
        links = re.findall(r"\[.*?\]\((.*?)\)", content)
        for link in links:
            if link.startswith("http") or link.startswith("#") or not link.strip():
                continue
            # Handle relative links
            try:
                # Remove query or fragments if any
                clean_link = link.split("#")[0].split("?")[0]
                link_path = (path.parent / clean_link).resolve()
                if not link_path.exists():
                    issues.append({
                        "type": "broken_link",
                        "code": "file_not_found",
                        "description": f"Broken link in {path.name}: {link}",
                        "severity": "medium",
                        "fix_suggestion": f"Fix the relative path or create the missing file: {link}"
                    })
            except Exception:
                warnings.append(f"Invalid link format detected in {path.name}: {link}")

    return {
        "status": "ok" if not issues else "issues_found",
        "issues": issues,
        "warnings": warnings,
        "summary": {
            "total_issues": len(issues),
            "sync_errors": len([i for i in issues if i["type"] == "sync_error"]),
            "broken_links": len([i for i in issues if i["type"] == "broken_link"]),
            "bloat_warnings": len([i for i in issues if i["type"] == "bloat_warning"])
        }
    }
