"""Filesystem path helpers shared across workflow kit prototypes."""

from __future__ import annotations

from pathlib import Path


def resolve_existing_path(raw: str) -> Path:
    """Resolve a path and fail early when the target does not exist."""
    path = Path(raw).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"path does not exist: {path}")
    return path

