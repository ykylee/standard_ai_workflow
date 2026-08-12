"""MCP tool 정의와 설정 예시를 스펙에 대조한다 (v1.0.3+).

## 왜 필요한가

이 저장소는 MCP 표면이 셋이다 — `workflow_kit/server/`(SDK·JSON-RPC 2경로),
`mcp_servers/` 의 도구 디렉터리, `examples/mcp_config_examples/` 의 harness 설정.
그런데 **tool 정의가 MCP 스펙에 맞는지 검사하는 것이 없었다.**

공식 [MCP Inspector](https://github.com/modelcontextprotocol/inspector) 는 서버를
실제로 띄워 `tools/list` 를 호출해 검증한다 — 그 층은 별도 워크플로우가 담당한다
(Node 필요). 여기서는 그 앞 층, 즉 **커밋된 산출물이 스펙 모양인지** 를 의존성 없이
본다. 두 층은 다른 것을 본다: 여기가 통과해도 서버가 그 descriptor 를 실제로
노출하는지는 알 수 없고, 그 반대도 마찬가지다.

## 검사 규칙

1. descriptor 파일이 파싱되고 `tools` 가 비어 있지 않은가
2. tool 마다 — `name` 이 `[a-zA-Z0-9_-]{1,64}`, `description` 비어 있지 않음,
   `inputSchema` 가 `type: "object"` + `properties` 를 가진 JSON Schema
3. `tool_count` 선언이 실제 개수와 일치하는가 (선언 ↔ 사실)
4. harness 설정 예시(JSON/TOML)가 전부 파싱되는가
5. **렌더러가 뱉는 TOML** 이 파싱되고 `tool_descriptions` 키가 코드가 쓴 문자열인가
   — 4번은 커밋된 예시 파일만 본다. 생성기 출력은 아무도 파싱해 본 적이 없었다.
6. 방언 표 `MCP_CONFIG_ROOT_KEY` 가 **독립 출처** (`examples/mcp_config_examples/`)
   와 같은가 — draft 예시가 OpenCode 에 `mcp_servers` 를 가르치는 동안 렌더러는
   `mcp` 를 내보내고 있었다. 표와 렌더러를 대조하면 둘 다 표를 읽으므로
   **무엇을 되주입해도 통과한다**; 따로 작성된 예시 파일이 유일한 외부 증인이다.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
DESCRIPTORS = SOURCE_ROOT / "schemas" / "read_only_transport_descriptors.json"
CONFIG_EXAMPLES = SOURCE_ROOT / "examples" / "mcp_config_examples"

# MCP 스펙: tool 이름은 영숫자 + 밑줄/하이픈
TOOL_NAME_RE = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")


def _load() -> dict | None:
    if not DESCRIPTORS.is_file():
        print(f"  FAIL: {DESCRIPTORS.relative_to(REPO_ROOT)} 부재")
        return None
    try:
        return json.loads(DESCRIPTORS.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"  FAIL: descriptor JSON 파싱 실패 — {e}")
        return None


def test_descriptors_load() -> bool:
    """1) descriptor 가 파싱되고 tool 이 있는가."""
    d = _load()
    if d is None:
        return False
    tools = d.get("tools")
    if not isinstance(tools, list) or not tools:
        print(f"  FAIL: `tools` 가 비어 있거나 리스트가 아니다 ({type(tools).__name__})")
        return False
    print(f"  PASS: tool {len(tools)}개 로드 (server={d.get('server_name')!r})")
    return True


def test_tool_definitions() -> bool:
    """2) tool 정의가 MCP 스펙 모양인가."""
    d = _load()
    if d is None:
        return False
    ok = True
    for t in d.get("tools", []):
        name = t.get("name")
        if not isinstance(name, str) or not TOOL_NAME_RE.match(name):
            print(f"  FAIL: tool 이름 위반 {name!r} (영숫자 + `_`/`-`, 1–64자)")
            ok = False
            continue
        if not t.get("description"):
            print(f"  FAIL: {name} — `description` 부재/빈 값")
            ok = False
        schema = t.get("inputSchema")
        if not isinstance(schema, dict):
            print(f"  FAIL: {name} — `inputSchema` 부재/객체 아님")
            ok = False
            continue
        if schema.get("type") != "object":
            print(f"  FAIL: {name} — `inputSchema.type` = {schema.get('type')!r} "
                  "(MCP 는 object 를 요구한다)")
            ok = False
        if "properties" not in schema:
            print(f"  FAIL: {name} — `inputSchema.properties` 부재")
            ok = False
        for req in schema.get("required", []) or []:
            if req not in (schema.get("properties") or {}):
                print(f"  FAIL: {name} — `required` 의 {req!r} 가 properties 에 없다")
                ok = False
    if ok:
        print(f"  PASS: tool 정의 {len(d.get('tools', []))}개 스펙 정합")
    return ok


def test_declared_count_matches() -> bool:
    """3) 선언한 `tool_count` 가 사실과 같은가.

    선언과 사실이 갈리는 것이 이 저장소가 반복해서 겪은 결함이므로, 수치를
    적어 두는 곳은 실제와 대조한다.
    """
    d = _load()
    if d is None:
        return False
    declared = d.get("tool_count")
    actual = len(d.get("tools", []))
    if declared is None:
        print("  PASS: `tool_count` 선언 없음 (대조 대상 아님)")
        return True
    if declared != actual:
        print(f"  FAIL: `tool_count` 선언 {declared} != 실제 {actual}")
        return False
    print(f"  PASS: tool_count 선언 {declared} == 실제 {actual}")
    return True


def test_config_examples_parse() -> bool:
    """4) harness MCP 설정 예시가 전부 파싱되는가."""
    if not CONFIG_EXAMPLES.is_dir():
        print(f"  FAIL: {CONFIG_EXAMPLES.relative_to(REPO_ROOT)} 부재")
        return False
    files = sorted(p for p in CONFIG_EXAMPLES.iterdir() if p.suffix in {".json", ".toml"})
    if not files:
        print("  FAIL: 설정 예시가 0개 — 탐색 경로 확인 필요")
        return False
    try:
        import tomllib
    except ImportError:  # pragma: no cover — Python 3.10
        import tomli as tomllib

    ok = True
    for p in files:
        rel = p.relative_to(REPO_ROOT)
        try:
            if p.suffix == ".json":
                json.loads(p.read_text(encoding="utf-8"))
            else:
                tomllib.loads(p.read_text(encoding="utf-8"))
        except Exception as e:  # noqa: BLE001
            print(f"  FAIL: {rel} — {type(e).__name__}: {str(e)[:90]}")
            ok = False
    if ok:
        print(f"  PASS: 설정 예시 {len(files)}개 파싱")
    return ok


def test_rendered_toml_keys_are_what_the_code_wrote() -> bool:
    """5) **렌더러가 실제로 뱉는 TOML** 이 파싱되고, 키가 코드가 쓴 문자열인가.

    4번은 *커밋된 예시 파일* 만 본다. 생성기가 뱉는 것은 아무도 파싱해 본 적이
    없었고, 그래서 `tool_descriptions` 의 키가 조용히 다른 것을 뜻하고 있었다:
    `workflow_kit.read_only = "…"` 는 TOML 의 dotted key 규칙에 따라
    ``{workflow_kit = {read_only = "…"}}`` 로 **중첩**된다. 코드는 `MCP_TOOL_NAME`
    이라는 키 하나를 쓴다고 말하는데 파일은 다른 구조를 뜻했다 (2026-08-05).

    Codex 와 Grok Build 가 같은 helper 를 쓰므로 이 case 가 양쪽을 함께 덮는다.
    """
    try:
        import tomllib
    except ImportError:  # pragma: no cover — Python 3.10
        import tomli as tomllib

    sys.path.insert(0, str(SOURCE_ROOT / "scripts"))
    from bootstrap_lib.mcp import (  # noqa: PLC0415
        MCP_SERVER_ALIAS,
        MCP_TOOL_NAME,
        render_mcp_toml_block,
    )

    ok = True
    for bridge in ("jsonrpc-bridge", "stdio-sdk"):
        block = render_mcp_toml_block(bridge, {"STANDARD_AI_WORKFLOW_ROOT": "."})
        try:
            parsed = tomllib.loads(block)
        except Exception as e:  # noqa: BLE001
            print(f"  FAIL: {bridge} — TOML 파싱 실패 {type(e).__name__}: {str(e)[:90]}")
            ok = False
            continue
        server = parsed.get("mcp_servers", {}).get(MCP_SERVER_ALIAS)
        if not isinstance(server, dict):
            print(f"  FAIL: {bridge} — `mcp_servers.{MCP_SERVER_ALIAS}` 가 없다")
            ok = False
            continue
        descriptions = server.get("tool_descriptions")
        if not isinstance(descriptions, dict) or MCP_TOOL_NAME not in descriptions:
            print(f"  FAIL: {bridge} — `tool_descriptions` 의 키가 {MCP_TOOL_NAME!r} 가 아니다 "
                  f"(실제: {sorted(descriptions) if isinstance(descriptions, dict) else descriptions!r}); "
                  "점이 든 키는 따옴표로 감싸야 중첩되지 않는다")
            ok = False
        if not server.get("args"):
            print(f"  FAIL: {bridge} — `args` 가 비어 있다")
            ok = False
    if ok:
        print("  PASS: 렌더러 TOML 2종 파싱 + tool_descriptions 키가 코드가 쓴 문자열")
    return ok


def test_root_key_table_matches_authored_examples() -> bool:
    """6) 방언 표(`MCP_CONFIG_ROOT_KEY`)가 **따로 작성된 설정 예시** 와 같은가.

    `scripts/generate_read_only_harness_mcp_examples.py` 의 OpenCode 예시가
    `mcp_servers` 를 가르치는 동안 실제 `render_opencode_mcp_config` 은 `mcp` 를
    내보내고 있었다 — 예시대로 붙여넣으면 OpenCode 가 서버를 못 본다 (2026-08-05).

    **표와 렌더러를 대조하면 안 된다.** 이제 렌더러도 같은 표를 읽으므로 표를 바꾸면
    양쪽이 함께 바뀌어 **무엇을 되주입해도 통과한다** (실제로 처음 이렇게 짰다가
    결함 상태에서 6/6 PASS 가 나왔다). 자기 자신과 비교하는 검사는 아무것도 보장하지
    않는다.

    그래서 **독립 출처** 인 `examples/mcp_config_examples/<harness>-mcp.json` 과
    대조한다. 이 파일들은 하네스 문서를 보고 따로 작성된 것이고, 실제로 이번 결함
    당시에도 `opencode-mcp.json` 은 처음부터 `mcp` 를 쓰고 있었다 — 증인은 있었는데
    아무도 대조하지 않았을 뿐이다.

    Codex 는 TOML 이라 대상이 아니다 (그쪽은 case 5 가 파싱해서 본다).
    """
    sys.path.insert(0, str(SOURCE_ROOT / "scripts"))
    from bootstrap_lib.mcp import MCP_CONFIG_ROOT_KEY  # noqa: PLC0415

    witnessed: list[str] = []
    unwitnessed: list[str] = []
    ok = True
    for harness, declared in sorted(MCP_CONFIG_ROOT_KEY.items()):
        witness = CONFIG_EXAMPLES / f"{harness}-mcp.json"
        if not witness.is_file():
            unwitnessed.append(harness)
            continue
        keys = list(json.loads(witness.read_text(encoding="utf-8")))
        if keys != [declared]:
            print(f"  FAIL: {harness} — 표는 {declared!r} 인데 "
                  f"{witness.relative_to(REPO_ROOT)} 는 {keys} 를 쓴다")
            ok = False
            continue
        witnessed.append(harness)

    # 증인이 없는 하네스는 결함이 아니지만 **조용히 넘기지 않는다** — 대조하지 못한
    # 것과 대조해서 맞은 것이 같은 모양이면 커버리지가 조용히 0 으로 떨어진다.
    if unwitnessed:
        print(f"  [info] 독립 예시가 없어 대조 못 함: {unwitnessed}")
    if len(witnessed) < 3:
        print(f"  FAIL: 대조된 하네스 {len(witnessed)}개 — 예시 파일 명명 규칙이 "
              "바뀌었을 수 있다 (대상 0건은 통과가 아니다)")
        return False
    if ok:
        print(f"  PASS: 방언 표 {len(witnessed)}종이 독립 설정 예시와 일치")
    return ok


def test_example_tools_lists_match_registry() -> bool:
    """7) 예시 설정의 `tools` 배열이 registry 도구 목록과 같은가 (v1.1.7).

    TASK-2026-08-11-main-025: MiniMax 렌더러의 손 목록이 10개에서 멈춰 registry
    13개와 어긋났는데 아무 검사도 대조하지 않았다. 렌더러는 이제 registry 에서
    파생하지만, **커밋된 예시 파일** 은 여전히 따로 작성된 사본이다 — 예시에
    `tools` 배열이 있으면 registry 와 같아야 한다. 대상 0건은 통과가 아니다.
    """
    if str(SOURCE_ROOT) not in sys.path:
        sys.path.insert(0, str(SOURCE_ROOT))
    from workflow_kit.server.read_only_registry import READ_ONLY_TOOL_SPECS  # noqa: PLC0415

    registry_names = [spec.name for spec in READ_ONLY_TOOL_SPECS]

    def _tools_arrays(node: object) -> list[list[str]]:
        found: list[list[str]] = []
        if isinstance(node, dict):
            for key, value in node.items():
                if key == "tools" and isinstance(value, list):
                    found.append([str(v) for v in value])
                else:
                    found.extend(_tools_arrays(value))
        elif isinstance(node, list):
            for item in node:
                found.extend(_tools_arrays(item))
        return found

    ok = True
    compared = 0
    for example in sorted(CONFIG_EXAMPLES.glob("*.json")):
        for tools in _tools_arrays(json.loads(example.read_text(encoding="utf-8"))):
            compared += 1
            if tools != registry_names:
                missing = sorted(set(registry_names) - set(tools))
                extra = sorted(set(tools) - set(registry_names))
                print(f"  FAIL: {example.name} 의 tools 가 registry 와 다르다 — "
                      f"누락 {missing} / 잉여 {extra}")
                ok = False
    if compared == 0:
        print("  FAIL: tools 배열을 가진 예시가 0건 — 대상 0건은 통과가 아니다")
        return False
    if ok:
        print(f"  PASS: 예시 {compared}건의 tools 배열이 registry {len(registry_names)}종과 일치")
    return ok


def main() -> int:
    cases = [
        ("test_descriptors_load", test_descriptors_load),
        ("test_tool_definitions", test_tool_definitions),
        ("test_declared_count_matches", test_declared_count_matches),
        ("test_config_examples_parse", test_config_examples_parse),
        ("test_rendered_toml_keys_are_what_the_code_wrote",
         test_rendered_toml_keys_are_what_the_code_wrote),
        ("test_root_key_table_matches_authored_examples",
         test_root_key_table_matches_authored_examples),
        ("test_example_tools_lists_match_registry",
         test_example_tools_lists_match_registry),
    ]
    results = []
    for name, fn in cases:
        print(f"\n[{name}]")
        results.append((name, fn()))
    passed = sum(1 for _, ok in results if ok)
    print()
    for name, ok in results:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
    print(f"\n=== {passed}/{len(cases)} PASS ===")
    return 0 if passed == len(cases) else 1


if __name__ == "__main__":
    sys.exit(main())
