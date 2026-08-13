#!/usr/bin/env python3
"""Native plugin archives are isolated by harness and ready for release assets."""

from __future__ import annotations

import json
import sys
import tempfile
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
sys.path.insert(0, str(SOURCE_ROOT))

from workflow_kit import __version__ as VERSION  # noqa: E402
from workflow_kit.plugin_distribution import (  # noqa: E402
    PLUGIN_HARNESS_SPECS,
    archive_name,
    build_plugin_archives,
)


def main() -> int:
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir) / "dist"
        archives = build_plugin_archives(output_dir, version=VERSION)
        if {path.name for path in archives} != {
            archive_name(spec, VERSION) for spec in PLUGIN_HARNESS_SPECS.values()
        }:
            raise AssertionError("Plugin archive names do not match the harness registry.")

        for archive in archives:
            with zipfile.ZipFile(archive) as bundle:
                names = set(bundle.namelist())
                if not any(name.endswith("/skills/session-start/SKILL.md") for name in names):
                    raise AssertionError(f"{archive.name} misses the shared skill payload.")
                if "codex-plugin" in archive.name:
                    if not any(name.endswith("/plugins/standard-ai-workflow/.codex-plugin/plugin.json") for name in names):
                        raise AssertionError("Codex archive misses its native manifest.")
                    if any(name.endswith("/.claude-plugin/plugin.json") for name in names):
                        raise AssertionError("Codex archive must not ship the Claude manifest.")
                    archive_root = archive.stem
                    marketplace_name = f"{archive_root}/.agents/plugins/marketplace.json"
                    if marketplace_name not in names:
                        raise AssertionError("Codex archive misses the discovered install marketplace.")
                    marketplace = json.loads(bundle.read(marketplace_name))
                    entry = marketplace["plugins"][0]
                    if entry["source"]["path"] != "./plugins/standard-ai-workflow":
                        raise AssertionError("Codex marketplace source path is not installable.")
                    plugin_root = f"{archive_root}/plugins/standard-ai-workflow"
                    if not any(name.startswith(plugin_root + "/") for name in names):
                        raise AssertionError("Codex marketplace source path does not resolve inside the archive.")
                if "claude-code-plugin" in archive.name:
                    if not any(name.endswith("/.claude-plugin/plugin.json") for name in names):
                        raise AssertionError("Claude archive misses its native manifest.")
                    if any(name.endswith("/.codex-plugin/plugin.json") for name in names):
                        raise AssertionError("Claude archive must not ship the Codex manifest.")

    print("Plugin distribution smoke check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
