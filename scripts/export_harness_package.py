#!/usr/bin/env python3
"""Export harness-specific workflow packages into a dist directory."""

from __future__ import annotations

import argparse
import json
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SUPPORTED_HARNESSES = ("codex", "opencode")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export a harness-specific workflow package into dist/."
    )
    parser.add_argument(
        "--harness",
        action="append",
        choices=list(SUPPORTED_HARNESSES),
        dest="harnesses",
        required=True,
        help="Harness package to export.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(REPO_ROOT / "dist"),
        help="Root dist directory for exported packages.",
    )
    return parser.parse_args()


def selected_harnesses(args: argparse.Namespace) -> list[str]:
    return sorted(dict.fromkeys(args.harnesses))


def rel(path: Path, base: Path) -> str:
    return path.relative_to(base).as_posix()


def copy_file(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)


def copy_tree(source: Path, destination: Path) -> list[Path]:
    copied: list[Path] = []
    for path in sorted(source.rglob("*")):
        if path.is_dir():
            continue
        target = destination / path.relative_to(source)
        copy_file(path, target)
        copied.append(target)
    return copied


def workflow_common_sources() -> list[Path]:
    return [
        REPO_ROOT / "core" / "global_workflow_standard.md",
        REPO_ROOT / "core" / "workflow_adoption_entrypoints.md",
        REPO_ROOT / "core" / "workflow_harness_distribution.md",
        REPO_ROOT / "core" / "workflow_release_spec.md",
        REPO_ROOT / "mcp" / "read_only_bundle.md",
        REPO_ROOT / "schemas" / "read_only_harness_mcp_examples.json",
        REPO_ROOT / "schemas" / "read_only_jsonrpc_fixtures.json",
        REPO_ROOT / "schemas" / "read_only_transport_descriptors.json",
        REPO_ROOT / "harnesses" / "README.md",
    ]


def global_snippet_source_map() -> dict[str, list[Path]]:
    return {
        "codex": [
            REPO_ROOT / "global-snippets" / "codex" / "README.md",
            REPO_ROOT / "global-snippets" / "codex" / "config.toml.snippet",
        ],
        "opencode": [
            REPO_ROOT / "global-snippets" / "opencode" / "README.md",
            REPO_ROOT / "global-snippets" / "opencode" / "opencode.global.jsonc",
        ],
    }


def harness_specific_sources(harness: str) -> list[Path]:
    if harness == "codex":
        return [REPO_ROOT / "harnesses" / "codex" / "README.md"]
    if harness == "opencode":
        return [REPO_ROOT / "harnesses" / "opencode" / "README.md"]
    raise ValueError(f"Unsupported harness: {harness}")


def bootstrap_export_sources(harness: str, temp_repo: Path) -> list[Path]:
    args = [
        "python3",
        str(REPO_ROOT / "scripts" / "bootstrap_workflow_kit.py"),
        "--target-root",
        str(temp_repo),
        "--project-slug",
        "export_sample",
        "--project-name",
        "Export Sample",
        "--copy-core-docs",
        "--harness",
        harness,
    ]
    completed = shutil.which("python3")
    if completed is None:
        raise RuntimeError("python3 is required to export harness packages.")
    import subprocess

    subprocess.run(args, cwd=REPO_ROOT, check=True, capture_output=True, text=True)

    sources = [
        temp_repo / "ai-workflow",
    ]
    if harness == "codex":
        sources.extend(
            [
                temp_repo / "AGENTS.md",
                temp_repo / ".codex" / "config.toml.example",
            ]
        )
    elif harness == "opencode":
        sources.extend(
            [
                temp_repo / "opencode.json",
                temp_repo / ".opencode",
            ]
        )
    return sources


def export_harness(harness: str, output_root: Path) -> dict[str, object]:
    package_root = output_root / "harnesses" / harness
    bundle_root = package_root / "bundle"
    if package_root.exists():
        shutil.rmtree(package_root)
    bundle_root.mkdir(parents=True, exist_ok=True)

    included_files: list[str] = []

    snippet_files: list[str] = []

    for source in workflow_common_sources() + harness_specific_sources(harness):
        destination = bundle_root / "source-docs" / rel(source, REPO_ROOT)
        copy_file(source, destination)
        included_files.append(rel(destination, package_root))

    for source in global_snippet_source_map().get(harness, []):
        destination = bundle_root / "global-snippets" / rel(source, REPO_ROOT / "global-snippets")
        copy_file(source, destination)
        rel_dest = rel(destination, package_root)
        included_files.append(rel_dest)
        snippet_files.append(rel_dest)

    with tempfile.TemporaryDirectory() as tmpdir:
        temp_repo = Path(tmpdir) / "sample-target"
        temp_repo.mkdir(parents=True, exist_ok=True)
        for source in bootstrap_export_sources(harness, temp_repo):
            if source.is_dir():
                copied = copy_tree(source, bundle_root / source.name)
                included_files.extend(rel(path, package_root) for path in copied)
            else:
                destination = bundle_root / source.name
                copy_file(source, destination)
                included_files.append(rel(destination, package_root))

    manifest = {
        "harness": harness,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "source_root": str(REPO_ROOT),
        "bundle_root": str(bundle_root),
        "included_files": sorted(included_files),
        "global_snippet_files": sorted(snippet_files),
        "notes": [
            "This package is a generated dist artifact.",
            "Regenerate after updating core docs, harness docs, or bootstrap overlay builders.",
            "Global snippets are provided as additive examples and should be merged manually.",
        ],
    }
    manifest_path = package_root / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    archive_base = package_root / f"{harness}-workflow-kit"
    archive_path = shutil.make_archive(str(archive_base), "zip", root_dir=bundle_root)

    return {
        "harness": harness,
        "package_root": str(package_root),
        "bundle_root": str(bundle_root),
        "manifest_path": str(manifest_path),
        "archive_path": archive_path,
        "included_files_count": len(included_files),
    }


def main() -> int:
    args = parse_args()
    output_root = Path(args.output_dir).resolve()
    exports = [export_harness(harness, output_root) for harness in selected_harnesses(args)]
    payload = {
        "output_root": str(output_root),
        "exports": exports,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
