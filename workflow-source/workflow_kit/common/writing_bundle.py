"""Shared callable implementations for writing/modifying MCP tools."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from workflow_kit.common.paths import resolve_existing_path

def apply_robust_patch_payload(
    *,
    file_path: str,
    patch_content: str,
    tool_version: str,
) -> dict[str, Any]:
    """
    Applies a Search-Replace block patch to a file.
    This is an adapter for robust-patcher/scripts/patch_engine.py logic.
    """
    # Import the engine logic (we might want to move the logic to common later)
    # For now, let's reach into the skills directory or just replicate the logic here.
    # Replicating or importing is a choice. Let's try to import if possible.
    
    import sys
    import os
    
    # Add skills directory to path to import patch_engine
    skills_path = str(Path(__file__).parent.parent.parent / "skills")
    if skills_path not in sys.path:
        sys.path.append(skills_path)
    
    try:
        from robust_patcher.scripts.patch_engine import apply_patch
    except ImportError:
        return {
            "status": "error",
            "tool_version": tool_version,
            "message": "robust-patcher engine not found in skills directory.",
            "warnings": ["Ensure workflow-source/skills/robust-patcher/scripts/patch_engine.py exists."]
        }

    path = resolve_existing_path(file_path)
    success, message = apply_patch(str(path), patch_content)
    
    return {
        "status": "ok" if success else "error",
        "tool_version": tool_version,
        "message": message,
        "file_path": str(path),
        "warnings": [] if success else [message],
    }
