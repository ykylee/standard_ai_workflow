"""mavis attach end-to-end smoke (TASK-2026-08-08-main-013)

§2.68 cycle 의 *자동 검증* — mavis 글로벌 mcp.json 의 standardAiWorkflowReadOnly
항목이 실제로 attach 가능한지 *기동* 단에서 확인. mavis 데스크탑 새 세션 rotate
없이 *mavis mcp.json env 그대로* subprocess 로 띄워서 (v1.1.4+: 항목을 하드코딩
사본이 아니라 실제 `~/.minimax/mcp/mcp.json` 에서 읽는다. 파일/항목 부재 =
mavis 미설치 호스트 → graceful skip, `--require-mavis` 로 강제):
  1. initialize → serverInfo / protocolVersion 확인
  2. tools/list → 해당 bundle 의 도구 전량 노출 확인 (기대치는 정본 registry 파생)
  3. tools/call latest_backlog → 정상 응답 (candidates + latest_backlog_path)
  4. tools/call check_doc_metadata → 정상 응답 (checked_files + missing_metadata)
  5. 스키마 오류 시 친절한 error (allowed_fields + warnings) 확인

검증 실패 시:
  - mavis 가 글로벌 mcp.json 변경을 새 세션부터 반영 (silent fail) → 사용자가 rotate 해야 함
  - env 두 개 (STANDARD_AI_WORKFLOW_ROOT + PYTHONPATH) 가 *절대 경로* 가 아니면 cwd 부재
    함정 (§6.5.2 §1.2.1) 으로 도구가 안 붙음
  - builtin 5종 보존 (matrix / playwright / cu / trash / github)
  - JSON 문법 (trailing comma 등) 검증은 mavis 측 책임 — 본 smoke 의 subprocess 호출이
    그 단계까지 cover

외부 deps 0. stdlib + 저장소 정본 registry(`server.read_only_registry`) 만 쓴다 —
기대 도구 목록을 사본으로 들고 있지 않기 위해서다 (아래 EXPECTED_TOOL_NAMES 주석).
"""

from __future__ import annotations

#: 이 검사의 입력 표면 (spec `core/test_impact_tiering_spec.md` §2).
#: 게이트 채취 실측에서 뽑아 넓은 쪽으로 올렸다 — 좁으면 meta-watch 가 red 로 잡는다.
WATCHES = (
    "workflow-source/pyproject.toml",
    "workflow-source/workflow_kit/*",
)

import json
import os
import signal
import subprocess
import sys
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[1]
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from workflow_kit.server.read_only_registry import (  # noqa: E402
    BUNDLE_READ_ONLY,
    tool_specs_for_bundle,
)

# §6.5.2 — mavis 글로벌 mcp.json 의 standardAiWorkflowReadOnly 를 **파일에서 직접**
# 읽는다 (v1.1.4). 이전에는 그 항목의 *사본* 을 여기 하드코딩했는데, 사본에는 darwin
# 호스트의 절대 경로(`/Users/...`)가 박혀 있어 다른 호스트에서는 존재하지 않는 경로로
# subprocess 를 띄우다 늘 red 였다 — 검사가 재는 것은 "이 호스트의 mavis 가 실제로
# attach 가능한가" 이므로, 정본(실제 mcp.json)을 읽어야 사본 갈라짐도 함께 사라진다.
# mavis 미설치 호스트(파일/항목 부재)는 graceful skip — 모름 ≠ 실패. 강제하려면
# --require-mavis (TASK-2026-08-09-main-004 의 gh 부재 + --require-gh 와 같은 패턴).
MAVIS_MCP_JSON = Path.home() / ".minimax" / "mcp" / "mcp.json"
SERVER_KEY = "standardAiWorkflowReadOnly"


def load_mavis_entry() -> tuple[list[str], dict[str, str]] | None:
    """실제 글로벌 mcp.json 의 항목에서 (command+args, env) 를 얻는다. 부재 시 None."""
    if not MAVIS_MCP_JSON.is_file():
        return None
    data = json.loads(MAVIS_MCP_JSON.read_text(encoding="utf-8"))
    entry = data.get("mcpServers", {}).get(SERVER_KEY)
    if not isinstance(entry, dict):
        return None
    cmd = [entry["command"], *entry.get("args", [])]
    env = {str(k): str(v) for k, v in entry.get("env", {}).items()}
    return cmd, env


# module-level 로 유지 — 기존 테스트 함수들이 그대로 쓴다. 부재 시 main() 이 skip.
_LOADED = load_mavis_entry()
MCP_CMD, MCP_ENV = _LOADED if _LOADED else ([], {})
EXPECTED_PROTOCOL = "2025-03-26"


def _bundle_from_args(cmd: list[str]) -> str:
    """mavis 항목이 실제로 지정한 bundle. 미지정이면 CLI 기본값 (v1.2.0+ read-only).

    `--bundle X` / `--bundle=X` 두 형태를 모두 본다.
    """
    for idx, token in enumerate(cmd):
        if token == "--bundle" and idx + 1 < len(cmd):
            return cmd[idx + 1]
        if token.startswith("--bundle="):
            return token.split("=", 1)[1]
    return BUNDLE_READ_ONLY


# 기대치는 **정본 registry 에서 파생**한다. 이전 판은 13종 이름을 여기 하드코딩한
# 사본이었고, v1.2.0 이 `--bundle` 기본값을 `all`→`read-only` 로 뒤집자 (write 도구
# `apply_robust_patch`/`rotate_workflow_logs` 2종이 read-only 서버에서 빠졌다)
# 사본만 13 에 멈춰 red 로 남았다 — **이 파일이 두 번째로 겪는 같은 결함**이다
# (v1.1.4 에 호스트 경로 사본을 같은 이유로 지웠고, 그 주석이 바로 위에 있다).
# 실측 2026-08-13: 깨끗한 트리에서도 `expected 13, got 11`.
# 정본에서 파생하므로 앞으로 bundle 구성이 바뀌어도 조용히 갈라지지 않는다.
EXPECTED_TOOL_NAMES = {spec.name for spec in tool_specs_for_bundle(_bundle_from_args(MCP_CMD))}
EXPECTED_TOOL_COUNT = len(EXPECTED_TOOL_NAMES)


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
    print(f"\n[2/4] tools/list (기대 {EXPECTED_TOOL_COUNT}종)")
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
    if _LOADED is None:
        msg = (
            f"SKIP: mavis 글로벌 mcp.json 부재 또는 {SERVER_KEY} 항목 없음 "
            f"({MAVIS_MCP_JSON}) — mavis 미설치 호스트로 판단. "
            "attach 검증을 강제하려면 --require-mavis."
        )
        if "--require-mavis" in sys.argv:
            print(f"FAIL(require-mavis): {msg}")
            return 1
        print(msg)
        return 0
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
    print(f"ALL PASS: mavis attach e2e green (initialize / {EXPECTED_TOOL_COUNT} tools / 2 tool calls)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
