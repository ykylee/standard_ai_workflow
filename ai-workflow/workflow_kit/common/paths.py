"""Filesystem path helpers shared across workflow kit prototypes."""

from __future__ import annotations
import os
import subprocess
from pathlib import Path


def resolve_existing_path(raw: str) -> Path:
    """Resolve a path and fail early when the target does not exist."""
    path = Path(raw).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"path does not exist: {path}")
    return path


def safe_relpath(path: Path, start: Path) -> str:
    """Return a relative version of a path if it is under start, otherwise absolute string."""
    try:
        resolved_path = path.resolve()
        resolved_start = start.resolve()
        if resolved_path.is_relative_to(resolved_start):
            return os.path.relpath(resolved_path, resolved_start)
        return str(resolved_path)
    except (ValueError, OSError):
        return str(path)


def path_exists_relative(base: Path, raw: str | None) -> Path | None:
    if not raw:
        return None
    candidate = (base / raw).resolve()
    if candidate.exists():
        return candidate
    return None


def declared_doc_path(base: Path, raw: str | None) -> str | None:
    if not raw:
        return None
    return str((base / raw).resolve())


def workflow_memory_dir(project_profile_path: Path) -> Path:
    """Return the base directory for workflow memory (ai-workflow/memory/)."""
    profile_dir = project_profile_path.resolve().parent
    # If the profile is in docs/, the memory dir is usually ../ai-workflow/memory/
    if profile_dir.name == "docs":
        memory_dir = (profile_dir.parent / "ai-workflow" / "memory").resolve()
        if memory_dir.exists():
            return memory_dir
    return profile_dir


def project_workspace_root(project_profile_path: Path) -> Path:
    profile_dir = project_profile_path.resolve().parent
    if profile_dir.name == "docs":
        return profile_dir.parent
    memory_dir = workflow_memory_dir(project_profile_path)
    if memory_dir.name == "memory" and memory_dir.parent.name == "ai-workflow":
        return memory_dir.parent.parent.resolve()
    return memory_dir


def get_current_branch() -> str:
    """Return the current git branch name. Default to 'main' if not in a git repo."""
    try:
        branch = subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            stderr=subprocess.DEVNULL,
            text=True
        ).strip()
        return branch if branch else "main"
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "main"


def workflow_branch_dir(project_profile_path: Path) -> Path:
    """Return the branch-specific directory within the memory dir."""
    base_dir = workflow_memory_dir(project_profile_path)
    branch = get_current_branch()
    # Normalize branch name for filesystem safety if needed, 
    # but here we allow nested folders if branch name has '/'
    return (base_dir / branch).resolve()


def path_exists_from_profile(project_profile_path: Path, raw: str | None) -> Path | None:
    if not raw:
        return None
    # Check branch-specific dir first, then fall back to workspace root
    branch_dir = workflow_branch_dir(project_profile_path)
    candidate = (branch_dir / raw).resolve()
    if candidate.exists():
        return candidate
    return path_exists_relative(project_workspace_root(project_profile_path), raw)


def declared_doc_path_from_profile(project_profile_path: Path, raw: str | None) -> str | None:
    if not raw:
        return None
    return declared_doc_path(project_workspace_root(project_profile_path), raw)
