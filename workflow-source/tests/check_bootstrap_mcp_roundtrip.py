#!/usr/bin/env python3
"""Smoke test: end-to-end MCP round-trip via bootstrap-emitted config.

This complements the existing read-only JSON-RPC bridge smoke tests by
verifying that the **mcp.json file emitted by ``bootstrap --enable-mcp``**
can actually be spawned by a harness, run a JSON-RPC session, and serve
``tools/list`` + ``tools/call`` without errors. It catches the case where
the bootstrap generates a syntactically valid config but the underlying
bridge entry point is broken (wrong PYTHONPATH, missing module, etc.).

Usage::

    PYTHONPATH=workflow-source python3 workflow-source/tests/check_bootstrap_mcp_roundtrip.py

The test is CWD-independent: it anchors PYTHONPATH at this repository's
``workflow-source`` directory and the harness cwd at the bootstrap output
directory (``/tmp/mcp-smoke`` by default).
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"


def run_bootstrap(target_root: Path) -> dict[str, object]:
    """Run ``bootstrap --enable-mcp`` and return the manifest payload."""
    args = [
        sys.executable,
        str(SOURCE_ROOT / "scripts" / "bootstrap_workflow_kit.py"),
        "--target-root",
        str(target_root),
        "--project-slug",
        "mcp_smoke",
        "--project-name",
        "MCP Smoke",
        "--harness",
        "minimax-code",
        "--adoption-mode",
        "new",
        "--copy-core-docs",
        "--enable-mcp",
    ]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(SOURCE_ROOT)
    if str(SOURCE_ROOT.parent / "scripts") not in env.get("PYTHONPATH", ""):
        env["PYTHONPATH"] = f"{SOURCE_ROOT}{os.pathsep}{SOURCE_ROOT.parent / 'scripts'}"
    completed = subprocess.run(
        args,
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=True,
        env=env,
    )
    # Manifest is the last JSON object printed on stdout
    payload = json.loads(completed.stdout.split("}\n")[-2] + "}")
    return payload


def spawn_bridge(manifest: dict[str, object], target_root: Path) -> subprocess.Popen[str]:
    """Spawn the MCP bridge described by the bootstrap manifest.

    Anchors ``PYTHONPATH`` at the kit's ``workflow-source`` so the entry
    point can resolve ``workflow_kit`` regardless of the caller's cwd,
    and rewrites the emitted ``python3`` command to the test runner's
    interpreter (``sys.executable``). The bootstrap's relative ``python3``
    resolves against the harness's ``$PATH``; in the smoke test we
    cannot assume the harness PATH contains a Python that has the kit's
    dependencies, so we pin to the same interpreter we used to run the
    test (which definitely has them).
    """
    config = json.loads(
        Path(str(manifest["generated_harness_files"]["minimax_code_mcp_config"])).read_text(
            encoding="utf-8"
        )
    )
    server = config["mcp_servers"]["standardAiWorkflowReadOnly"]
    # Replace the emitted "python3" with the test runner's interpreter so
    # the spawned bridge has the same Python environment as the test.
    cmd = [sys.executable, *server["args"]]
    env = os.environ.copy()
    # Bootstrap emits a relative PYTHONPATH ("workflow-source"). Anchor it
    # at the kit's actual workflow-source so the bridge can import
    # ``workflow_kit`` from any cwd.
    kit_env = {**server.get("env", {}), "PYTHONPATH": str(SOURCE_ROOT)}
    env.update({k: str(v) for k, v in kit_env.items()})
    # STANDARD_AI_WORKFLOW_ROOT should be the absolute bootstrap target
    env["STANDARD_AI_WORKFLOW_ROOT"] = str(target_root.resolve())
    return subprocess.Popen(
        cmd,
        cwd=str(target_root),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=0,
        env=env,
    )


def round_trip(proc: subprocess.Popen[str], request: dict[str, object], *, timeout: float = 5.0) -> dict[str, object]:
    """Send a single JSON-RPC request over stdio and return the response."""
    assert proc.stdin is not None and proc.stdout is not None
    proc.stdin.write(json.dumps(request, ensure_ascii=False) + "\n")
    proc.stdin.flush()
    deadline = time.time() + timeout
    line = ""
    while time.time() < deadline:
        line = proc.stdout.readline()
        if line:
            return json.loads(line)
        time.sleep(0.05)
    raise AssertionError(f"No response within {timeout}s for request {request['method']}")


def main() -> int:
    with tempfile.TemporaryDirectory() as tmpdir:
        target_root = Path(tmpdir) / "mcp-smoke"
        target_root.mkdir(parents=True, exist_ok=True)
        manifest = run_bootstrap(target_root)
        if "minimax_code_mcp_config" not in manifest["generated_harness_files"]:
            raise AssertionError("bootstrap did not emit a minimax_code_mcp_config file.")
        proc = spawn_bridge(manifest, target_root)
        try:
            init = round_trip(
                proc,
                {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
            )
            if init["result"]["serverInfo"]["name"] != "workflow_read_only_bundle":
                raise AssertionError("initialize did not return the expected server name.")

            tools = round_trip(
                proc,
                {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
            )["result"]["tools"]
            if not tools:
                raise AssertionError("tools/list returned no tools.")
            names = {tool["name"] for tool in tools}
            for required in ("latest_backlog", "check_doc_metadata", "check_doc_links"):
                if required not in names:
                    raise AssertionError(f"required tool missing: {required}")

            call_result = round_trip(
                proc,
                {
                    "jsonrpc": "2.0",
                    "id": 3,
                    "method": "tools/call",
                    "params": {
                        "name": "latest_backlog",
                        "arguments": {
                            "work_backlog_index_path": str(
                                REPO_ROOT
                                / "workflow-source"
                                / "examples"
                                / "acme_delivery_platform"
                                / "work_backlog.md"
                            )
                        },
                    },
                },
            )["result"]
            if call_result.get("_meta", {}).get("bridge_phase") != "jsonrpc_draft_fixture":
                raise AssertionError("latest_backlog call did not return the expected bridge phase.")
            structured = call_result.get("structuredContent", {})
            if structured.get("status") != "ok":
                raise AssertionError(f"latest_backlog structuredContent status is {structured.get('status')!r}, expected 'ok'.")
        finally:
            try:
                if proc.stdin is not None:
                    proc.stdin.close()
            except Exception:
                pass
            try:
                proc.wait(timeout=2)
            except Exception:
                proc.kill()
            stderr = proc.stderr.read() if proc.stderr is not None else ""
            if stderr.strip():
                # Surface only the first 400 chars to avoid log noise
                snippet = stderr.strip().splitlines()[:5]
                print(f"bridge stderr (first 5 lines):\n  " + "\n  ".join(snippet))

    print("Bootstrap-emitted MCP config round-trip smoke check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
