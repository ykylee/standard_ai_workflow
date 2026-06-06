"""File-write helpers and the manifest builder.

The bootstrap script needs three write primitives:

- :func:`write_text` writes a single file (and refuses to overwrite
  unless ``force`` is set).
- :func:`copy_core_docs` copies the kit's standard core docs and support
  paths into the generated kit.
- :func:`build_manifest` collects everything the bootstrap script wrote
  into a single JSON-serialisable summary, so the entry-point can echo
  it back to the operator.

These helpers are pure functions on ``Paths`` and :class:`argparse.Namespace`;
they don't need to know about harnesses or MCP.
"""

from __future__ import annotations

import json
import shutil
from dataclasses import asdict
from pathlib import Path
from typing import Any

from bootstrap_lib.paths import Paths


def rel(path: Path, base: Path) -> str:
    """Return a relative path string for ``path`` against ``base``.

    Falls back to the absolute string when ``path`` is not under ``base``.
    """
    try:
        return str(path.resolve().relative_to(base.resolve()))
    except ValueError:
        return str(path.resolve())


def write_text(path: Path, content: str, *, force: bool) -> None:
    if path.exists() and not force:
        raise FileExistsError(f"Destination already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def copy_core_docs(
    paths: Paths,
    *,
    force: bool,
    default_core_docs: list[str],
    default_core_support_paths: list[str],
    source_root: Path,
) -> list[str]:
    """Copy the kit's standard core docs + support paths into the generated kit."""
    copied: list[str] = []
    paths.core_dir.mkdir(parents=True, exist_ok=True)
    for name in default_core_docs:
        source = source_root / "core" / name
        destination = paths.core_dir / name
        if destination.exists() and not force:
            raise FileExistsError(f"Destination already exists: {destination}")
        shutil.copyfile(source, destination)
        copied.append(str(destination))
    for raw_relative_path in default_core_support_paths:
        relative_path = Path(raw_relative_path)
        source = source_root / relative_path
        destination = paths.kit_root / relative_path
        if source.is_dir():
            for file_path in sorted(source.rglob("*")):
                if not file_path.is_file():
                    continue
                nested_relative = file_path.relative_to(source_root)
                nested_destination = paths.kit_root / nested_relative
                if nested_destination.exists() and not force:
                    raise FileExistsError(f"Destination already exists: {nested_destination}")
                nested_destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(file_path, nested_destination)
            continue
        if destination.exists() and not force:
            raise FileExistsError(f"Destination already exists: {destination}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
    return copied


def build_manifest(
    args: Any,
    paths: Paths,
    core_docs: list[str],
    context: dict[str, object],
    harness_files: dict[str, str],
    dependency_files: list[str] | None,
    selected_harnesses: list[str],
    global_snippet_sources_fn: Any,
) -> dict[str, object]:
    """Collect everything the bootstrap wrote into a JSON-serialisable summary."""
    selected_snippets = {
        harness: global_snippet_sources_fn()[harness]
        for harness in selected_harnesses
        if harness in global_snippet_sources_fn()
    }
    generated_files: dict[str, str] = {
        "readme": str(paths.readme_path),
        "project_profile": str(paths.profile_path),
        "workflow_state": str(paths.state_path),
        "session_handoff": str(paths.handoff_path),
        "work_backlog": str(paths.backlog_index_path),
        "daily_backlog": str(paths.daily_backlog_path),
        "project_status_assessment": str(paths.status_assessment_path),
    }
    if getattr(args, "adoption_mode", "new") == "existing":
        generated_files["repository_assessment"] = str(paths.assessment_path)
    next_steps = [
        f"Open {rel(paths.profile_path, paths.target_root)} and replace TODO placeholders.",
        f"Refresh {rel(paths.state_path, paths.target_root)} after updating workflow docs.",
        f"Update {rel(paths.handoff_path, paths.target_root)} with the current session baseline.",
        f"Register the next real task in {rel(paths.daily_backlog_path, paths.target_root)}.",
    ]
    install_command = context.get("install_command")
    if dependency_files:
        next_steps.append(
            f"Run `{install_command}` to install recommended dependencies."
        )
    if getattr(args, "adoption_mode", "new") == "existing":
        next_steps.append(
            f"Review {rel(paths.assessment_path, paths.target_root)} and confirm inferred commands and doc paths."
        )
    if selected_snippets:
        next_steps.append(
            "Review the recommended global snippet before merging it into your harness-wide config."
        )
    return {
        "target_root": str(paths.target_root),
        "kit_root": str(paths.kit_root),
        "project_slug": args.project_slug,
        "project_name": args.project_name,
        "adoption_mode": args.adoption_mode,
        "harnesses": selected_harnesses,
        "analysis_summary": context.get("analysis_summary", []),
        "generated_files": generated_files,
        "generated_harness_files": harness_files,
        "updated_dependency_files": dependency_files or [],
        "global_snippet_candidates": selected_snippets,
        "copied_core_docs": core_docs,
        "next_steps": next_steps,
    }


__all__ = [
    "build_manifest",
    "copy_core_docs",
    "rel",
    "write_text",
]
