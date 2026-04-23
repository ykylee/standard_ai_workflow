#!/usr/bin/env python3
"""Smoke test harness package export."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
EXPORT_SCRIPT = REPO_ROOT / "scripts" / "export_harness_package.py"


def main() -> int:
    with tempfile.TemporaryDirectory() as tmpdir:
        output_root = Path(tmpdir) / "dist"
        completed = subprocess.run(
            [
                sys.executable,
                str(EXPORT_SCRIPT),
                "--harness",
                "codex",
                "--harness",
                "opencode",
                "--output-dir",
                str(output_root),
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        payload = json.loads(completed.stdout)
        exports = payload["exports"]
        if len(exports) != 2:
            raise AssertionError("Expected two exported harness packages.")
        for export in exports:
            package_root = Path(export["package_root"])
            manifest_path = Path(export["manifest_path"])
            archive_path = Path(export["archive_path"])
            if not package_root.exists():
                raise AssertionError(f"Missing package root: {package_root}")
            if not manifest_path.exists():
                raise AssertionError(f"Missing manifest: {manifest_path}")
            if not archive_path.exists():
                raise AssertionError(f"Missing archive: {archive_path}")

            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            if not manifest["included_files"]:
                raise AssertionError("Manifest should include exported files.")
            if not manifest["global_snippet_files"]:
                raise AssertionError("Manifest should include related global snippet files.")
            included = set(manifest["included_files"])
            if "bundle/source-docs/schemas/read_only_harness_mcp_examples.json" not in included:
                raise AssertionError("Manifest should include read-only harness MCP examples.")
            if "bundle/source-docs/schemas/read_only_jsonrpc_fixtures.json" not in included:
                raise AssertionError("Manifest should include read-only JSON-RPC fixtures.")
            if "bundle/source-docs/schemas/read_only_transport_descriptors.json" not in included:
                raise AssertionError("Manifest should include read-only transport descriptors.")
            if "bundle/source-docs/mcp/read_only_bundle.md" not in included:
                raise AssertionError("Manifest should include read-only bundle documentation.")

    print("Harness package export smoke check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
