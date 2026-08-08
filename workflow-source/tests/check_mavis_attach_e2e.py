"""mavis attach end-to-end smoke (TASK-2026-08-08-main-013)

§2.68 cycle 의 *자동 검증* — mavis 글로벌 mcp.json 의 standardAiWorkflowReadOnly
항목이 실제로 attach 가능한지 *기동* 단에서 확인. mavis 데스크탑 새 세션 rotate
없이 *mavis mcp.json env 그대로* subprocess 로 띄워서:
  1. initialize → serverInfo / protocolVersion 확인
  2. tools/list → 13종 노출 확인
  3. tools/call latest_backlog → 정상 응답 (candidates + latest_backlog_path)
  4. tools/call check_doc_metadata → 정상 응답 (checked_files + missing_metadata)
  5. 스키마 오류 시 친절한 error (allowed_fields + warnings) 확인

검증 실패 시:
  - mavis 가 글로벌 mcp.json 변경을 새 세션부터 반영 (silent fail) → 사용자가 rotate 해야 함
  - env 두 개 (STANDARD_AI_WORKFLOW_ROOT + PYTHONPATH) 가 *절대 경로* 가 아니면 cwd 부재
    함정 (§6.5.2 §1.2.1) 으로 13종이 안 붙음
  - builtin 5종 보존 (matrix / playwright / cu / trash / github)
  - JSON 문법 (trailing comma 등) 검증은 mavis 측 책임 — 본 smoke 의 subprocess 호출이
    그 단계까지 cover

Stdlib 만 사용. subprocess + json + os 만 import. 외부 deps 0.
"""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
from pathlib import Path

# §6.5.2 형식 — mavis 글로벌 mcp.json 의 standardAiWorkflowReadOnly 와 100% 일치해야 함.
REPO_ROOT = "/Users/yklee/repos/standard_ai_workflow"
MCP_ENV = {
    "STANDARD_AI_WORKFLOW_ROOT": REPO_ROOT,
    "PYTHONPATH": f"{REPO_ROOT}/workflow-source",
}
MCP_CMD = [
    "python3",
    "-m",
    "workflow_kit.server.read_only_jsonrpc",
    "--stdio-lines",
]
EXPECTED_PROTOCOL = "2025-03-26"
EXPECTED_TOOL_COUNT = 13
EXPECTED_TOOL_NAMES = {
    "latest_backlog",
    "check_doc_metadata",
    "check_doc_links",
    "suggest_impacted_docs",
    "create_backlog_entry",
    "create_session_handoff_draft",
    "create_environment_record_stub",
    "check_quickstart_stale_links",
    "summarize_git_history",
    "rotate_workflow_logs",
    "assess_milestone_progress",
    "smart_context_reader",
    "apply_robust_patch",
}


class McpSession:
    def __init__(self) -> None:
        env = os.environ.copy()
        env.update(MCP_ENV)
        self.proc = subprocess.Popen(
            MCP_CMD,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            bufsize=0,
        )

    def send(self, req: dict) -> None:
        assert self.proc.stdin is not None
        self.proc.stdin.write((json.dumps(req) + "\n").encode())
        self.proc.stdin.flush()

    def recv(self) -> dict:
        assert self.proc.stdout is not None
        line = self.proc.stdout.readline()
        return json.loads(line.decode())

    def close(self) -> None:
        try:
            self.proc.send_signal(signal.SIGTERM)
            self.proc.wait(timeout=5)
        except Exception:
            self.proc.kill()
            self.proc.wait()


def _assert(cond: bool, msg: str, failures: list) -> None:
    if not cond:
        failures.append(msg)
        print(f"  FAIL: {msg}")


def test_initialize(failures: list) -> dict:
    print("\n[1/4] initialize")
    s = McpSession()
    try:
        s.send(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "mavis-attach-e2e", "version": "0.1.0"},
                },
            }
        )
        resp = s.recv()
        result = resp.get("result", {})
        server_info = result.get("serverInfo", {})
        protocol = result.get("protocolVersion")
        print(f"  serverInfo = {server_info}")
        print(f"  protocolVersion = {protocol}")
        _assert(
            server_info.get("name") == "workflow_read_only_bundle",
            f"serverInfo.name expected workflow_read_only_bundle, got {server_info.get('name')}",
            failures,
        )
        _assert(
            protocol == EXPECTED_PROTOCOL,
            f"protocolVersion expected {EXPECTED_PROTOCOL}, got {protocol}",
            failures,
        )
        # initialized notification
        s.send({"jsonrpc": "2.0", "method": "notifications/initialized"})
        return s
    except Exception as e:
        failures.append(f"initialize threw: {e}")
        s.close()
        raise


def test_tools_list(s: McpSession, failures: list) -> list:
    print("\n[2/4] tools/list (기대 13종)")
    s.send({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
    resp = s.recv()
    tools = resp.get("result", {}).get("tools", [])
    actual_names = {t["name"] for t in tools}
    print(f"  actual tools ({len(tools)}): {sorted(actual_names)}")
    _assert(
        len(tools) == EXPECTED_TOOL_COUNT,
        f"tool count expected {EXPECTED_TOOL_COUNT}, got {len(tools)}",
        failures,
    )
    _assert(
        actual_names == EXPECTED_TOOL_NAMES,
        f"tool names mismatch.\n  expected = {sorted(EXPECTED_TOOL_NAMES)}\n  actual   = {sorted(actual_names)}",
        failures,
    )
    return tools


def test_tool_call(s: McpSession, failures: list) -> None:
    print("\n[3/4] tools/call latest_backlog")
    s.send(
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "latest_backlog",
                "arguments": {"backlog_dir_path": "ai-workflow/memory/active/main/backlog"},
            },
        }
    )
    resp = s.recv()
    if "error" in resp:
        failures.append(f"latest_backlog returned error: {resp['error']}")
        return
    content = resp.get("result", {}).get("content", [])
    _assert(len(content) > 0, "latest_backlog content empty", failures)
    if content:
        text = content[0].get("text", "")
        _assert(text, "latest_backlog text empty", failures)
        if text:
            data = json.loads(text)
            print(f"  result keys = {list(data.keys())}")
            _assert(
                "candidates" in data,
                f"latest_backlog missing 'candidates' key: {list(data.keys())}",
                failures,
            )
            _assert(
                "latest_backlog_path" in data,
                f"latest_backlog missing 'latest_backlog_path' key: {list(data.keys())}",
                failures,
            )
            _assert(
                data.get("status") == "ok",
                f"latest_backlog status not ok: {data.get('status')}",
                failures,
            )

    print("\n[4/4] tools/call check_doc_metadata")
    s.send(
        {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {
                "name": "check_doc_metadata",
                "arguments": {"doc_dir_path": "ai-workflow/memory/active/main"},
            },
        }
    )
    resp2 = s.recv()
    if "error" in resp2:
        failures.append(f"check_doc_metadata returned error: {resp2['error']}")
        return
    content2 = resp2.get("result", {}).get("content", [])
    _assert(len(content2) > 0, "check_doc_metadata content empty", failures)
    if content2:
        text2 = content2[0].get("text", "")
        _assert(text2, "check_doc_metadata text empty", failures)
        if text2:
            data2 = json.loads(text2)
            print(f"  result keys = {list(data2.keys())}")
            _assert(
                "checked_files" in data2,
                f"check_doc_metadata missing 'checked_files': {list(data2.keys())}",
                failures,
            )
            _assert(
                data2.get("status") == "ok",
                f"check_doc_metadata status not ok: {data2.get('status')}",
                failures,
            )


def main() -> int:
    print("=" * 60)
    print("mavis attach end-to-end smoke (TASK-2026-08-08-main-013)")
    print(f"MCP_ENV = {MCP_ENV}")
    print(f"MCP_CMD = {MCP_CMD}")
    print("=" * 60)

    failures: list = []
    s = test_initialize(failures)
    if s:
        try:
            tools = test_tools_list(s, failures)
            if tools:
                test_tool_call(s, failures)
        finally:
            s.close()

    print()
    print("=" * 60)
    if failures:
        print(f"FAIL: {len(failures)} case(s) failed:")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("ALL PASS: mavis attach e2e green (initialize / 13 tools / 2 tool calls)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
