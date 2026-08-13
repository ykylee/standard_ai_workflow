"""Build release archives for plugin-capable harnesses.

The source payload is shared, but each harness receives only its native
manifest and supporting files. Add a :class:`PluginHarnessSpec` entry to ship
another harness without changing the archive builder or release pipeline.
"""

from __future__ import annotations

import argparse
import json
import shutil
import tempfile
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from workflow_kit.plugin_payload import (
    CLAUDE_CODE_MANIFEST_RELPATH,
    CLAUDE_CODE_MCP_RELPATH,
    CODEX_MANIFEST_RELPATH,
    PAYLOAD_DIRNAME,
    PLUGIN_NAME,
    current_kit_version,
)


@dataclass(frozen=True)
class PluginHarnessSpec:
    """A native plugin package definition for one supported harness."""

    slug: str
    manifest_relpath: str
    include_prefixes: tuple[str, ...]
    marketplace_name: str | None = None


PLUGIN_HARNESS_SPECS: dict[str, PluginHarnessSpec] = {
    "codex": PluginHarnessSpec(
        slug="codex",
        manifest_relpath=CODEX_MANIFEST_RELPATH,
        include_prefixes=(CODEX_MANIFEST_RELPATH, CLAUDE_CODE_MCP_RELPATH, "skills/"),
        marketplace_name=PLUGIN_NAME,
    ),
    "claude-code": PluginHarnessSpec(
        slug="claude-code",
        manifest_relpath=CLAUDE_CODE_MANIFEST_RELPATH,
        include_prefixes=(CLAUDE_CODE_MANIFEST_RELPATH, CLAUDE_CODE_MCP_RELPATH, "skills/", "adapters/claude-code/"),
    ),
}


def default_repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def archive_name(spec: PluginHarnessSpec, version: str) -> str:
    return f"{PLUGIN_NAME}-{spec.slug}-plugin-{version}.zip"


def archive_path(output_dir: Path, spec: PluginHarnessSpec, version: str) -> Path:
    return output_dir / "plugins" / spec.slug / version / archive_name(spec, version)


def selected_specs(harnesses: Iterable[str] | None = None) -> list[PluginHarnessSpec]:
    names = sorted(dict.fromkeys(harnesses or PLUGIN_HARNESS_SPECS))
    unknown = [name for name in names if name not in PLUGIN_HARNESS_SPECS]
    if unknown:
        raise ValueError(f"Unsupported plugin harnesses: {', '.join(unknown)}")
    return [PLUGIN_HARNESS_SPECS[name] for name in names]


def _included(relpath: str, spec: PluginHarnessSpec) -> bool:
    return any(relpath == prefix or relpath.startswith(prefix) for prefix in spec.include_prefixes)


def _write_marketplace(root: Path, spec: PluginHarnessSpec) -> None:
    """Write the Codex marketplace required to install an extracted release asset."""
    if spec.marketplace_name is None:
        return
    marketplace = {
        "name": spec.marketplace_name,
        "interface": {"displayName": "Standard AI Workflow"},
        "plugins": [
            {
                "name": PLUGIN_NAME,
                "source": {"source": "local", "path": f"./plugins/{PLUGIN_NAME}"},
                "policy": {"installation": "AVAILABLE", "authentication": "ON_INSTALL"},
                "category": "Productivity",
            }
        ],
    }
    (root / "marketplace.json").write_text(json.dumps(marketplace, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build_plugin_archives(
    output_dir: Path,
    *,
    version: str | None = None,
    harnesses: Iterable[str] | None = None,
    repo_root: Path | None = None,
) -> list[Path]:
    """Build native plugin archives and return their absolute paths."""
    root = repo_root or default_repo_root()
    payload = root / PAYLOAD_DIRNAME
    resolved_version = version or current_kit_version()
    archives: list[Path] = []
    for spec in selected_specs(harnesses):
        if not (payload / spec.manifest_relpath).is_file():
            raise FileNotFoundError(f"Missing {spec.slug} manifest: {spec.manifest_relpath}")
        with tempfile.TemporaryDirectory(prefix="saw-plugin-") as tmpdir:
            archive_root = Path(tmpdir) / f"{PLUGIN_NAME}-{spec.slug}-plugin-{resolved_version}"
            staged_root = (
                archive_root / "plugins" / PLUGIN_NAME
                if spec.marketplace_name is not None
                else archive_root / PLUGIN_NAME
            )
            for source in sorted(payload.rglob("*")):
                if not source.is_file():
                    continue
                relpath = source.relative_to(payload).as_posix()
                if _included(relpath, spec):
                    target = staged_root / relpath
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(source, target)
            _write_marketplace(archive_root, spec)
            destination = archive_path(output_dir, spec, resolved_version)
            destination.parent.mkdir(parents=True, exist_ok=True)
            archive_base = destination.with_suffix("")
            shutil.make_archive(str(archive_base), "zip", root_dir=archive_root.parent, base_dir=archive_root.name)
            archives.append(destination)
    return archives


def planned_plugin_archives(output_dir: Path, version: str) -> list[Path]:
    return [archive_path(output_dir, spec, version) for spec in selected_specs()]


def main() -> int:
    parser = argparse.ArgumentParser(description="Build native plugin release archives.")
    parser.add_argument("--harness", action="append", choices=sorted(PLUGIN_HARNESS_SPECS))
    parser.add_argument("--output-dir", type=Path, default=default_repo_root() / "dist")
    parser.add_argument("--version", default=current_kit_version())
    args = parser.parse_args()
    archives = build_plugin_archives(args.output_dir, version=args.version, harnesses=args.harness)
    print(json.dumps({"version": args.version, "archives": [str(path) for path in archives]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
