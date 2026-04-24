"""Filesystem path helpers shared across workflow kit prototypes."""

from __future__ import annotations

from pathlib import Path
import re


def resolve_existing_path(raw: str) -> Path:
    """Resolve a path and fail early when the target does not exist."""
    path = Path(raw).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"path does not exist: {path}")
    return path


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


def safe_path_segment(value: str | None, *, fallback: str) -> str:
    raw = (value or "").strip()
    if not raw or raw.upper() == "TODO":
        raw = fallback
    segment = re.sub(r"[^A-Za-z0-9._-]+", "_", raw).strip("._-")
    return segment or fallback


def host_scoped_backlog_path(*, project_profile_path: Path, target_date: str, host_name: str | None, host_ip: str | None) -> Path:
    project_dir = workflow_project_dir(project_profile_path)
    host_segment = safe_path_segment(host_name, fallback="unknown-host")
    ip_segment = safe_path_segment(host_ip, fallback="unknown-ip")
    return (project_dir / "backlog" / host_segment / ip_segment / f"{target_date}.md").resolve()


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
