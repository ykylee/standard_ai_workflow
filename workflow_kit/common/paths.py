"""Filesystem path helpers shared across workflow kit prototypes."""

from __future__ import annotations
import os
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


def workflow_project_dir(project_profile_path: Path) -> Path:
    return project_profile_path.resolve().parent


def project_workspace_root(project_profile_path: Path) -> Path:
    profile_dir = workflow_project_dir(project_profile_path)
    if profile_dir.name == "project" and profile_dir.parent.name == "ai-workflow":
        return profile_dir.parent.parent.resolve()
    return profile_dir


def path_exists_from_profile(project_profile_path: Path, raw: str | None) -> Path | None:
    if not raw:
        return None
    return path_exists_relative(project_workspace_root(project_profile_path), raw)


def declared_doc_path_from_profile(project_profile_path: Path, raw: str | None) -> str | None:
    if not raw:
        return None
    return declared_doc_path(project_workspace_root(project_profile_path), raw)
