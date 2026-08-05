#!/usr/bin/env python3
"""Generate draft harness MCP config examples for the read-only descriptor bundle.

**정본 의존 (2026-08-05).** 이 생성기는 alias / command / args / 최상위 키를 손으로
적어 두고 있었다 — `bootstrap_lib.mcp` 가 같은 사실의 정본인데 사본을 들고 있었던
것이고, 실제로 갈라졌다: OpenCode 예시가 `mcp_servers` 를 가르치는데 실제
`render_opencode_mcp_config` 이 내보내는 키는 `mcp` 였다. 예시대로 붙여넣으면
OpenCode 가 서버를 못 본다. 이제 넷 다 `bootstrap_lib.mcp` 에서 가져온다.

여기서 만드는 것은 여전히 **draft 예시**다 (`transport_ready=false`,
`manual_review_only`, 전부 주석 처리). 그 상태값은 `core/read_only_mcp_transport_promotion.md`
§4 의 계약이고 이 변경의 범위가 아니다 — 바꾸려면 "무엇이 참이면 승격인가" 를 먼저
정의해야 한다.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))
if str(SOURCE_ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT / "scripts"))

from bootstrap_lib.mcp import (
    MCP_CONFIG_ROOT_KEY,
    MCP_SERVER_ALIAS,
    mcp_server_command,
)
from workflow_kit.server.read_only_registry import build_transport_tool_descriptors


SOURCE_DESCRIPTOR_PATH = "workflow-source/schemas/read_only_transport_descriptors.json"
SERVER_ALIAS = MCP_SERVER_ALIAS
#: 예시가 보여 주는 bridge. draft 단계라 JSON-RPC 로 고정한다
#: (`core/read_only_mcp_transport_promotion.md` §4).
DRAFT_BRIDGE = "jsonrpc-bridge"
#: `python3 -m workflow_kit.server.read_only_jsonrpc --stdio-lines` 를 조립하는 정본.
DRAFT_COMMAND = mcp_server_command(DRAFT_BRIDGE)
#: `bridge_entrypoint` 필드가 이름하는 모듈 — args 의 `-m` 다음 값이 곧 그것이다.
DRAFT_ENTRYPOINT = DRAFT_COMMAND[DRAFT_COMMAND.index("-m") + 1]


def tool_names_from_descriptor(descriptor_bundle: dict[str, object]) -> list[str]:
    tools = descriptor_bundle["tools"]
    if not isinstance(tools, list):
        raise TypeError("Expected descriptor tools to be a list.")
    return [str(tool["name"]) for tool in tools if isinstance(tool, dict)]


def codex_toml_example(tool_names: list[str]) -> str:
    tools = ", ".join(tool_names)
    args_inline = ", ".join(json.dumps(part) for part in DRAFT_COMMAND[1:])
    return "\n".join(
        [
            "# Draft only: generated from schemas/read_only_transport_descriptors.json.",
            "# transport_ready=false; do not paste this as an active server until an MCP SDK server loop exists.",
            f"# Tools described: {tools}",
            f"# [mcp_servers.{SERVER_ALIAS}]",
            f"# command = {json.dumps(DRAFT_COMMAND[0])}",
            f"# args = [{args_inline}]",
            "# NOTE: current bridge is a JSON-RPC draft fixture, not a full MCP SDK server.",
        ]
    )


def opencode_jsonc_example(tool_names: list[str]) -> str:
    tools = ", ".join(tool_names)
    args_inline = ", ".join(json.dumps(part) for part in DRAFT_COMMAND[1:])
    return "\n".join(
        [
            "{",
            "  // Draft only: generated from schemas/read_only_transport_descriptors.json.",
            "  // transport_ready=false; do not enable until an MCP SDK server loop exists.",
            f"  // Tools described: {tools}",
            # 최상위 키는 하네스 방언이다. 손으로 적었을 때 `mcp_servers` 로 갈라져
            # 있었고, 그건 OpenCode 가 읽지 않는 키다 (2026-08-05).
            f'  {json.dumps(MCP_CONFIG_ROOT_KEY["opencode"])}: {{',
            f'    // "{SERVER_ALIAS}": {{',
            '    //   "type": "local",',
            f'    //   "command": {json.dumps(DRAFT_COMMAND[0])},',
            f'    //   "args": [{args_inline}]',
            "    // }",
            "  }",
            "}",
        ]
    )


def build_harness_mcp_examples() -> dict[str, object]:
    descriptor_bundle = build_transport_tool_descriptors()
    tool_names = tool_names_from_descriptor(descriptor_bundle)
    return {
        "status": "ok",
        "tool_version": descriptor_bundle["tool_version"],
        "source_descriptor_path": SOURCE_DESCRIPTOR_PATH,
        "descriptor_target": descriptor_bundle["descriptor_target"],
        "transport_ready": descriptor_bundle["transport_ready"],
        "tool_count": descriptor_bundle["tool_count"],
        "tool_names": tool_names,
        "harness_examples": {
            "codex": {
                "format": "toml_snippet_draft",
                "target_path": "~/.codex/config.toml",
                "apply_mode": "manual_review_only",
                "bridge_entrypoint": DRAFT_ENTRYPOINT,
                "server_alias": SERVER_ALIAS,
                "content": codex_toml_example(tool_names),
            },
            "opencode": {
                "format": "jsonc_snippet_draft",
                "target_path": "opencode.json",
                "apply_mode": "manual_review_only",
                "bridge_entrypoint": DRAFT_ENTRYPOINT,
                "server_alias": SERVER_ALIAS,
                "content": opencode_jsonc_example(tool_names),
            },
        },
    }


def main() -> int:
    print(json.dumps(build_harness_mcp_examples(), ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
