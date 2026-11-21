"""안내 페이지 ``GET /`` — 지원 하네스 4종의 허브 MCP 등록 명령 (hub_spec §4.1, 요구 R2.6 · I4).

토큰을 보이지 않는다. 두 단계로 보인다:
    ① 등록 전 — 토큰 없이 허브 MCP 를 등록해 부트스트랩 도구(프로젝트 조회 · 등록 · 합류 · 셋업)를 쓴다.
    ② 셋업 뒤 — 부트스트랩이 쓴 설정(환경 변수 참조)으로 다시 연결한다. 명령은 셋업 지시가 대신 낸다.
"""

from __future__ import annotations

import html

from workflow_kit import __version__ as KIT_VERSION
from workflow_kit.hub.render import SUPPORTED_HARNESSES, entry_file


def harness_commands(public_url: str) -> dict[str, dict[str, str]]:
    """하네스 → {등록 전 명령, 셋업 뒤 설명}. 4종 목록은 :data:`SUPPORTED_HARNESSES` 에서 파생한다."""
    mcp = public_url.rstrip("/") + "/mcp"
    table = {
        "claude-code": {
            "before": f"claude mcp add --transport http workflow-hub {mcp}",
            "after": "부트스트랩이 .mcp.json 에 'Authorization: Bearer ${WORKFLOW_HUB_TOKEN}' 를 쓴다 — 토큰을 환경에 올리고 다시 시작",
        },
        "codex": {
            "before": f"codex mcp add workflow-hub --url {mcp}",
            "after": "부트스트랩이 --bearer-token-env-var WORKFLOW_HUB_TOKEN 로 다시 등록한다. 비대화(codex exec)는 "
                     "[mcp_servers.workflow-hub] default_tools_approval_mode = \"approve\" 가 있어야 허브 도구를 부른다",
        },
        "minimax-code": {
            "before": f"저장소 뿌리의 .mcp.json 에 {{\"mcpServers\": {{\"workflow-hub\": {{\"type\": \"http\", \"url\": \"{mcp}\"}}}}}}",
            "after": "부트스트랩이 같은 .mcp.json 에 환경 변수 참조 헤더를 더한다 (Claude Code 와 같은 파일)",
        },
        "antigravity": {
            "before": f"agy mcp add workflow-hub {mcp}",
            "after": "주의: Antigravity 는 헤더의 환경 변수 참조를 확장하지 않는다. 부트스트랩이 토큰을 사용자 범위 "
                     "~/.gemini/config/mcp_config.json 에 평문으로 넣는 명령을 경고와 함께 낸다 — 그 파일을 공유하지 않는다",
        },
    }
    return {h: table[h] for h in SUPPORTED_HARNESSES}


def render_page(public_url: str) -> str:
    rows = []
    for h, c in harness_commands(public_url).items():
        rows.append(
            f"<section><h2>{html.escape(h)} <small>({html.escape(entry_file(h))})</small></h2>"
            f"<p>① 등록 전</p><pre>{html.escape(c['before'])}</pre>"
            f"<p>② 셋업 뒤</p><p>{html.escape(c['after'])}</p></section>"
        )
    return (
        "<!doctype html><html lang=\"ko\"><head><meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
        "<title>워크플로우 허브</title>"
        "<style>body{font-family:system-ui,sans-serif;max-width:860px;margin:2rem auto;padding:0 16px;line-height:1.55}"
        "pre{background:#f4f4f5;padding:.6rem .8rem;overflow-x:auto;white-space:pre-wrap;word-break:break-all}"
        "@media (prefers-color-scheme:dark){body{background:#111;color:#eee}pre{background:#222}}</style></head><body>"
        f"<h1>워크플로우 허브</h1><p>kit {html.escape(KIT_VERSION)} · 계약 hub/1 · 주소 <code>{html.escape(public_url)}</code></p>"
        "<p>저장소 뿌리에서 하네스에 허브 MCP 를 등록한 뒤, 에이전트에게 \"워크플로우 허브에 이 저장소를 등록하고 셋업해\" 라고 한다. "
        "부트스트랩 도구가 프로젝트 등록(또는 합류) · <code>.gitignore</code> 확인 · 토큰 저장 · 진입 파일 · 하네스 설정을 차례로 지시한다.</p>"
        + "".join(rows)
        + "</body></html>"
    )
