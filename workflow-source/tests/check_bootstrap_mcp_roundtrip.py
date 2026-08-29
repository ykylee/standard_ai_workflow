#!/usr/bin/env python3
"""Smoke test: end-to-end MCP round-trip via bootstrap-emitted config.

This complements the existing read-only JSON-RPC bridge smoke tests by
verifying that the **mcp.json file emitted by ``bootstrap --enable-mcp``**
can actually be spawned by a harness, run a JSON-RPC session, and serve
``tools/list`` + ``tools/call`` without errors. It catches the case where
the bootstrap generates a syntactically valid config but the underlying
bridge entry point is broken (wrong PYTHONPATH, missing module, etc.).

By default this test runs the smoke for **every supported harness** so a
single run covers Codex / OpenCode / Antigravity / MiniMax Code.
A specific subset can be requested via the ``--harness`` flag (repeatable).

Usage::

    PYTHONPATH=workflow-source python3 workflow-source/tests/check_bootstrap_mcp_roundtrip.py
    PYTHONPATH=workflow-source python3 workflow-source/tests/check_bootstrap_mcp_roundtrip.py --harness minimax-code

The test is CWD-independent: it anchors PYTHONPATH at this repository's
``workflow-source`` directory and the harness cwd at the bootstrap output
directory (a temp dir per harness run).
"""

from __future__ import annotations

#: 이 검사의 입력 표면 (spec `core/test_impact_tiering_spec.md` §2).
#: 게이트 채취 실측에서 뽑아 넓은 쪽으로 올렸다 — 좁으면 meta-watch 가 red 로 잡는다.
WATCHES = (
    "workflow-source/pyproject.toml",
    "workflow-source/workflow_kit/*",
)

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"

sys.path.insert(0, str(SOURCE_ROOT / "scripts"))

from workflow_kit.bootstrap_lib.mcp import MCP_CONFIG_RENDERERS  # noqa: E402

#: Harness name → key in the bootstrap manifest's ``generated_harness_files``
#: dict that points at the emitted MCP config file.
HARNESS_CONFIG_KEY = {
    "codex": "codex_mcp_config",
    "opencode": "opencode_mcp_config",
    "antigravity": "antigravity_mcp_config",
    "minimax-code": "minimax_code_mcp_config",
    "claude-code": "claude_code_mcp_config",
}

#: 이 목록은 `MCP_CONFIG_RENDERERS` 의 사본이므로 갈라질 수 있다. docstring 은
#: "every supported harness" 를 돈다고 적어 두고 실제로는 손으로 유지되는 부분집합만
#: 돌고 있었다 — claude-code 렌더러를 추가했을 때 여기 넣지 않으면 **새 하네스가
#: 조용히 미검증으로 남는다**. import 시점에 정본과 대조해 즉시 깨뜨린다.
_UNCOVERED = sorted(set(MCP_CONFIG_RENDERERS) - set(HARNESS_CONFIG_KEY))
if _UNCOVERED:
    raise SystemExit(
        f"MCP 렌더러가 있는데 round-trip 대상에 없다: {_UNCOVERED}. "
        "HARNESS_CONFIG_KEY 에 manifest key 를 추가할 것 "
        "(대상에서 빠진 하네스는 '통과' 가 아니라 '안 봄' 이다)."
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--harness",
        action="append",
        choices=list(HARNESS_CONFIG_KEY),
        help="Limit the smoke to a single harness. Repeatable; defaults to all.",
    )
    return parser.parse_args()


def run_bootstrap(target_root: Path, harness: str) -> dict[str, object]:
    """Run ``bootstrap --enable-mcp`` for a single harness and return the manifest payload.

    The bootstrap script writes a progress preamble to stdout before
    printing the final manifest. We therefore locate the manifest by
    parsing successive JSON candidates from the end of stdout rather
    than relying on a fixed delimiter.
    """
    args = [
        sys.executable,
        str(SOURCE_ROOT / "scripts" / "bootstrap_workflow_kit.py"),
        "--target-root",
        str(target_root),
        "--project-slug",
        f"mcp_smoke_{harness.replace('-', '_')}",
        "--project-name",
        f"MCP Smoke {harness}",
        "--harness",
        harness,
        "--adoption-mode",
        "new",
        "--copy-core-docs",
        "--enable-mcp",
    ]
    env = os.environ.copy()
    env["PYTHONPATH"] = f"{SOURCE_ROOT}{os.pathsep}{SOURCE_ROOT.parent / 'scripts'}"
    completed = subprocess.run(
        args,
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=True,
        env=env,
    )
    # Walk backwards over the lines, trying to parse a JSON object out of
    # the tail. The manifest is the last valid JSON object on stdout.
    lines = completed.stdout.splitlines()
    for end in range(len(lines), 0, -1):
        found_start = None
        for start in range(end - 1, -1, -1):
            if lines[start].lstrip().startswith("{"):
                candidate = "\n".join(lines[start:end])
                try:
                    payload = json.loads(candidate)
                except json.JSONDecodeError:
                    continue
                if isinstance(payload, dict) and "generated_harness_files" in payload:
                    return payload
                found_start = start
                break
        if found_start is not None:
            end = found_start
    raise AssertionError(
        f"bootstrap did not produce a recognisable manifest on stdout. "
        f"Last 200 chars:\n{completed.stdout[-200:]}"
    )


def spawn_bridge(
    manifest: dict[str, object],
    target_root: Path,
    harness: str,
) -> subprocess.Popen[str]:
    """Spawn the MCP bridge described by the bootstrap manifest for ``harness``.

    Anchors ``PYTHONPATH`` at the kit's ``workflow-source`` so the entry
    point can resolve ``workflow_kit`` regardless of the caller's cwd,
    and rewrites the emitted ``python3`` command to the test runner's
    interpreter (``sys.executable``). The bootstrap's relative ``python3``
    resolves against the harness's ``$PATH``; in the smoke test we
    cannot assume the harness PATH contains a Python that has the kit's
    dependencies, so we pin to the same interpreter we used to run the
    test (which definitely has them).
    """
    config_key = HARNESS_CONFIG_KEY[harness]
    if config_key not in manifest["generated_harness_files"]:
        raise AssertionError(
            f"bootstrap did not emit {config_key!r} for harness {harness!r}. "
            f"Keys present: {sorted(manifest['generated_harness_files'])}"
        )
    config_path = Path(str(manifest["generated_harness_files"][config_key]))
    config_text = config_path.read_text(encoding="utf-8")
    if config_path.suffix == ".toml":
        # Codex uses TOML; we only care about the [mcp_servers.<alias>] table.
        server_block = _parse_codex_toml_server_block(config_text)
    else:
        config = json.loads(config_text)
        # Resolve to the actual server block under our canonical alias.
        # Each harness uses a slightly different top-level key, and the
        # ``mcp`` / ``mcpServers`` / ``mcp_servers`` keys wrap a dict
        # keyed by the server alias (``standardAiWorkflowReadOnly``).
        if "mcp" in config and isinstance(config["mcp"], dict):
            server_block = (
                config["mcp"].get("standardAiWorkflowReadOnly") or config["mcp"]
            )
        elif "mcpServers" in config and isinstance(config["mcpServers"], dict):
            server_block = (
                config["mcpServers"].get("standardAiWorkflowReadOnly") or config["mcpServers"]
            )
        elif "mcp_servers" in config and isinstance(config["mcp_servers"], dict):
            server_block = (
                config["mcp_servers"].get("standardAiWorkflowReadOnly") or config["mcp_servers"]
            )
        else:
            server_block = {}
    if not server_block or "command" not in server_block:
        raise AssertionError(
            f"Emitted MCP config for {harness!r} has no recognisable server block. "
            f"Top-level keys: {sorted(config)}"
        )
    # OpenCode 방언 (1.17.12 실측): command 는 배열 전체, env 키는 `environment`.
    # 다른 방언은 command 문자열 + args 분리 + `env` 를 유지한다.
    if isinstance(server_block["command"], list):
        launch_args = list(server_block["command"][1:])
    else:
        launch_args = list(server_block.get("args", []))
    cmd = [sys.executable, *launch_args]
    env = os.environ.copy()
    block_env = server_block.get("environment", server_block.get("env", {}))
    # main-018 형식 게이트: emit 된 PYTHONPATH 는 target 프로젝트에 **실재하는**
    # 디렉터리여야 한다. 이전에는 bootstrap 이 checkout 에서 돌았다는 이유만으로
    # 존재하지 않는 "workflow-source" 가 신규 프로젝트에 emit 됐다 — smoke 는
    # PYTHONPATH 를 스스로 덮어써서 그 결함을 못 봤다.
    if "PYTHONPATH" in block_env:
        emitted_pp = target_root / str(block_env["PYTHONPATH"])
        if not emitted_pp.is_dir():
            raise AssertionError(
                f"emitted PYTHONPATH points at a directory that does not exist "
                f"in the target project: {block_env['PYTHONPATH']!r} "
                f"(resolved: {emitted_pp})"
            )
    kit_env = {**block_env, "PYTHONPATH": str(SOURCE_ROOT)}
    env.update({k: str(v) for k, v in kit_env.items()})
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


def round_trip(
    proc: subprocess.Popen[str], request: dict[str, object], *, timeout: float = 5.0
) -> dict[str, object]:
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


def _parse_codex_toml_server_block(toml_text: str) -> dict[str, object]:
    """Best-effort parser for the Codex ``[mcp_servers.<alias>]`` TOML block.

    Codex's snippet uses a flat layout with simple key = value pairs plus a
    single string array for ``args``. We don't need full TOML semantics —
    just enough to extract ``command``, ``args`` (parsed from a TOML list
    literal), and the env vars.
    """
    import re

    # Locate the [mcp_servers.standardAiWorkflowReadOnly] section.
    section_match = re.search(
        r"^\[mcp_servers\.standardAiWorkflowReadOnly\]\s*$(.*?)(?=^\[|\Z)",
        toml_text,
        re.MULTILINE | re.DOTALL,
    )
    if not section_match:
        raise AssertionError("Codex TOML is missing the [mcp_servers.standardAiWorkflowReadOnly] section.")
    body = section_match.group(1)
    server: dict[str, object] = {}

    # command = "python3"
    command_match = re.search(r'^\s*command\s*=\s*"([^"]+)"', body, re.MULTILINE)
    if not command_match:
        raise AssertionError("Codex TOML is missing `command = \"...\"`.")
    server["command"] = command_match.group(1)

    # args = ["-m", "workflow_kit.server.read_only_jsonrpc", "--stdio-lines"]
    args_match = re.search(r"^\s*args\s*=\s*\[(.*?)\]\s*$", body, re.MULTILINE | re.DOTALL)
    if args_match:
        items = re.findall(r'"([^"]+)"', args_match.group(1))
        server["args"] = items
    else:
        server["args"] = []

    # env entries like: PYTHONPATH = "workflow-source"
    env: dict[str, str] = {}
    for env_match in re.finditer(r'^\s*([A-Z_][A-Z0-9_]*)\s*=\s*"([^"]*)"', body, re.MULTILINE):
        key = env_match.group(1)
        if key in {"command"} or key in {"startup_timeout_sec", "tool_timeout_sec"}:
            continue
        env[key] = env_match.group(2)
    if env:
        server["env"] = env
    return server


def smoke_one_harness(harness: str) -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        target_root = Path(tmpdir) / f"mcp-smoke-{harness}"
        target_root.mkdir(parents=True, exist_ok=True)
        manifest = run_bootstrap(target_root, harness)
        proc = spawn_bridge(manifest, target_root, harness)
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
            if call_result.get("_meta", {}).get("transport_phase") != "jsonrpc_draft":
                raise AssertionError("latest_backlog call did not return the expected bridge phase.")
            structured = call_result.get("structuredContent", {})
            if structured.get("status") != "ok":
                raise AssertionError(
                    f"latest_backlog structuredContent status is {structured.get('status')!r}, expected 'ok'."
                )
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
                snippet = stderr.strip().splitlines()[:5]
                print(f"  [{harness}] bridge stderr (first 5 lines):\n    " + "\n    ".join(snippet))


def unit_checks() -> None:
    """emit 조립의 단위 계약 — 플랫폼 분기(main-017)와 env 조건(main-018).

    smoke 는 이 호스트의 산출물만 밟는다. win32 분기와 '체크인 산출물은 posix
    고정' 계약은 여기서 명시적으로 잰다 — 기대값은 리터럴이 아니라 정본
    (:mod:`workflow_kit.common.python_launcher`)에서 파생한다.
    """
    from workflow_kit.bootstrap_lib.mcp import _mcp_server_env, mcp_server_command
    from workflow_kit.common.python_launcher import (
        POSIX_PYTHON,
        WIN32_PYTHON,
        python_launcher,
    )
    from workflow_kit.plugin_payload import _payload_mcp_entry

    # 1) 플랫폼 분기 — win32 는 python, 그 외 posix 관례, 기본값은 현재 호스트.
    assert mcp_server_command("jsonrpc-bridge", "read-only", platform="win32")[0] == WIN32_PYTHON
    assert mcp_server_command("jsonrpc-bridge", "read-only", platform="posix")[0] == POSIX_PYTHON
    assert mcp_server_command("stdio-sdk", platform="win32")[0] == WIN32_PYTHON
    assert mcp_server_command("jsonrpc-bridge")[0] == python_launcher()

    # 2) 체크인되는 플러그인 payload 는 렌더 호스트와 무관하게 posix 고정이다 —
    #    payload 해시 비교가 무너지지 않아야 한다.
    _, payload_cmd = _payload_mcp_entry()
    assert payload_cmd[0] == POSIX_PYTHON, payload_cmd

    # 3) env 는 emit 을 소비하는 target 의 레이아웃에서 잰다 (main-018).
    import tempfile as _tempfile
    from types import SimpleNamespace

    with _tempfile.TemporaryDirectory() as td:
        fresh = Path(td) / "fresh"
        fresh.mkdir()
        env_fresh = _mcp_server_env(SimpleNamespace(target_root=fresh))
        assert "PYTHONPATH" not in env_fresh, env_fresh

        vendored = Path(td) / "vendored"
        (vendored / "workflow-source").mkdir(parents=True)
        env_vendored = _mcp_server_env(SimpleNamespace(target_root=vendored))
        assert env_vendored.get("PYTHONPATH") == "workflow-source", env_vendored
    print("  - unit checks (launcher platform branch, payload pin, env-by-layout) ... ok")


def main() -> int:
    args = parse_args()
    harnesses = args.harness or list(HARNESS_CONFIG_KEY)
    unit_checks()
    print(f"Running MCP round-trip smoke for: {harnesses}")
    for harness in harnesses:
        print(f"  - {harness} ...", end=" ", flush=True)
        smoke_one_harness(harness)
        print("ok")
    print("Bootstrap-emitted MCP config round-trip smoke check passed for all selected harnesses.")
    return 0


def test_case_1() -> None:
    assert main() == 0, "case_1 smoke FAIL"


def test_case_2() -> None:
    assert main() == 0, "case_2 smoke FAIL"


def test_case_3() -> None:
    assert main() == 0, "case_3 smoke FAIL"


def test_case_4() -> None:
    assert main() == 0, "case_4 smoke FAIL"


def test_case_5() -> None:
    assert main() == 0, "case_5 smoke FAIL"



if __name__ == "__main__":
    raise SystemExit(main())
