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


def main() -> int:
    cases = [
        ("test_descriptors_load", test_descriptors_load),
        ("test_tool_definitions", test_tool_definitions),
        ("test_declared_count_matches", test_declared_count_matches),
        ("test_config_examples_parse", test_config_examples_parse),
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
