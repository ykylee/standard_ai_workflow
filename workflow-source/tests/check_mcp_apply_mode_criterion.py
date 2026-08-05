#!/usr/bin/env python3
"""`apply_mode` 승격 기준을 **실행** 한다 (v1.0.5+).

## 왜 필요한가

`transport_ready` 는 한 boolean 으로 서로 다른 질문 셋에 답하고 있었다 — 런타임 능력
(`mcp` 를 import 할 수 있나) / 구현 단계 (draft 냐 SDK 냐) / 정책 (활성 설정으로 붙여도
되나). 그래서 "무엇이 참이면 true 인가" 를 적을 수 없었고, registry 에는 상수 `False`
로 박혀 있었다 — registry 는 어느 transport 가 자기를 서빙할지 **모르므로 답할 자격이
없다.** 조건 없는 플래그는 영원히 false 다 (2026-08-05, §2.63).

축을 셋으로 쪼개면 승격 기준이 필요한 것은 **정책 축 하나** 다:

    sdk_available   런타임 능력 — read_only_mcp_sdk 가 자기 프로세스에서 계산
    transport_phase 구현 단계   — 각 transport 모듈이 자기 것을 선언
    apply_mode      정책        — 이 파일이 판정한다

## 승격 기준 (`apply_mode = active_ok`)

`bootstrap_lib.mcp.MCP_BRIDGE_APPLY_MODE` 에 `active_ok` 로 선언된 bridge 는 아래를
**둘 다** 통과해야 한다. 선언만으로는 통과하지 못한다.

1. **공식 MCP 클라이언트 왕복** — 손수 만든 JSON-RPC 가 아니라 `mcp` SDK 의
   `ClientSession` 으로 `initialize` → `tools/list` → `tools/call` 이 성공한다.
   (`check_bootstrap_mcp_roundtrip.py` 는 stdin/stdout 에 JSON 을 직접 쓰는
   손수 만든 클라이언트다 — 그건 우리 구현끼리의 대화라 하네스 호환성을 증명하지
   못한다.)
2. **emit 되는 command 로 뜬다** — bootstrap 이 실제로 내보내는 `command`/`args`/`env`
   그대로, 그리고 **`mcp` extra 가 없는 인터프리터** 에서 뜬다. 하네스가 spawn 하는
   것은 `python3` 이고 거기에 SDK 가 있다는 보장이 없다. `stdio-sdk` 는 정확히 이
   조건에서 `Connection closed` 로 죽는다 — 성숙도가 아니라 의존성 문제다.

## 2번을 어떻게 재는가 (그리고 한계)

`mcp` 를 import 하면 `ModuleNotFoundError` 를 내는 shim 디렉터리를 `PYTHONPATH` 맨
앞에 붙여 "extra 없는 인터프리터" 를 재현한다. 새 venv 를 만드는 것보다 빠르고
결정적이다.

**한계**: 이것은 `mcp` **하나만** 가린다. transport 가 다른 optional dep 에 의존하게
되면 이 검사는 못 잡는다. 그리고 여기서 통과해도 *실제 사용자의* python 이 kit 자체를
import 할 수 있는지는 별도 문제다 (`PYTHONPATH`/wheel 설치).

## 검사 규칙

0. 선언 표가 존재하고 두 bridge 를 다 덮는가 (대상 0건은 통과가 아니다)
1. `active_ok` bridge — extra 없는 인터프리터 + 공식 클라이언트로 왕복 성공
2. `manual_review_only` bridge — **왜** 그런지가 사실인가. 통과해 버리면 선언이
   과도하게 보수적이라는 뜻이므로 그것도 보고한다 (조용히 넘기지 않는다)
3. `mcp` SDK 부재 시 이 검사는 **skip 이 아니라 fail** 이다 — 공식 클라이언트가
   없으면 1번을 잰 적이 없는 것이고, 안 잰 것은 통과가 아니다
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
sys.path.insert(0, str(SOURCE_ROOT))
sys.path.insert(0, str(SOURCE_ROOT / "scripts"))

from bootstrap_lib.mcp import (  # noqa: E402
    MCP_BRIDGE_APPLY_MODE,
    MCP_BRIDGE_PHASE,
    MCP_SERVER_ALIAS,
    render_claude_code_mcp_config,
)
from bootstrap_lib.paths import Paths  # noqa: E402

#: 왕복에 쓸 tool 과 payload. 인자 없는 호출은 schema error 를 내므로 실제 값을 준다.
PROBE_TOOL = "latest_backlog"
PROBE_ARGS = {"backlog_dir_path": "ai-workflow/memory/active/main/backlog"}


def _emitted_server_spec(bridge: str) -> dict[str, object]:
    """bootstrap 이 **실제로 내보내는** 서버 정의를 그대로 읽어 온다.

    렌더러를 재현하지 않고 호출한다 — 재현은 검증이 아니다.
    """
    fields = {name: REPO_ROOT for name in Paths.__dataclass_fields__}
    args = argparse.Namespace(mcp_bridge=bridge)
    config = json.loads(render_claude_code_mcp_config(args, Paths(**fields)))
    server = config["mcpServers"][MCP_SERVER_ALIAS]
    assert isinstance(server, dict)
    return server


def _shim_dir(tmp: str) -> str:
    """`import mcp` 가 실패하는 디렉터리. "extra 없는 인터프리터" 재현."""
    root = Path(tmp) / "no_mcp_extra"
    (root / "mcp").mkdir(parents=True, exist_ok=True)
    (root / "mcp" / "__init__.py").write_text(
        'raise ModuleNotFoundError("No module named \'mcp\' '
        '(check_mcp_apply_mode_criterion shim: extra 없는 인터프리터 재현)")\n',
        encoding="utf-8",
    )
    return str(root)


async def _round_trip(server: dict[str, object], extra_pythonpath: str | None) -> tuple[bool, str]:
    """공식 MCP 클라이언트로 initialize + tools/list + tools/call 왕복."""
    from mcp import ClientSession, StdioServerParameters  # noqa: PLC0415
    from mcp.client.stdio import stdio_client  # noqa: PLC0415

    env = dict(os.environ)
    env.update({str(k): str(v) for k, v in dict(server.get("env") or {}).items()})
    if extra_pythonpath:
        env["PYTHONPATH"] = os.pathsep.join(
            [extra_pythonpath, *( [env["PYTHONPATH"]] if env.get("PYTHONPATH") else [] )]
        )
    params = StdioServerParameters(
        command=str(server["command"]),
        args=[str(a) for a in list(server["args"])],
        env=env,
        cwd=str(REPO_ROOT),
    )
    try:
        async with stdio_client(params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                tools = await session.list_tools()
                if not tools.tools:
                    return False, "tools/list 가 0건"
                result = await session.call_tool(PROBE_TOOL, PROBE_ARGS)
                if _is_error(result):
                    return False, f"tools/call {PROBE_TOOL} 이 오류를 냈다"
                return True, f"tools/list {len(tools.tools)}종 + tools/call 성공"
    except BaseException as exc:  # noqa: BLE001 — 서버가 안 뜨는 것도 판정 대상이다
        return False, _flatten(exc)


def _is_error(result: object) -> bool:
    """`CallToolResult` 의 오류 여부 — **SDK 버전마다 이름이 다르다.**

    mcp 1.x 는 `isError`(camelCase), 2.0.0 은 `is_error`(snake_case) 다. 이 저장소는
    이미 같은 함정을 겪었는데(`read_only_mcp_sdk._call_result` 의 주석: 2.0.0 에서
    대입이 조용히 빗나가 실패가 성공으로 보고될 자리였다) 이 검사를 처음 쓸 때 또
    `isError` 로 적었고, mcp-sdk-matrix 의 2.0.0 셀에서 걸렸다 (2026-08-05).
    **매트릭스가 있는 이유가 이것이다** — 로컬 venv 는 1.27.0 이라 통과했다.
    """
    for name in ("is_error", "isError"):
        value = getattr(result, name, None)
        if value is not None:
            return bool(value)
    raise AttributeError(
        "CallToolResult 에 is_error / isError 가 둘 다 없다 — SDK API 가 또 바뀌었다"
    )


def _flatten(exc: BaseException) -> str:
    """ExceptionGroup 을 펼쳐 **원인** 을 보여 준다.

    stdio 클라이언트는 TaskGroup 을 쓰므로 서버 기동 실패가
    `ExceptionGroup: unhandled errors in a TaskGroup` 로 감싸여 온다 — 그대로
    보고하면 "왜 죽었는지" 가 사라진다.
    """
    subs = getattr(exc, "exceptions", None)
    if subs:
        return " / ".join(_flatten(sub) for sub in subs)
    return f"{type(exc).__name__}: {str(exc)[:110]}"


def _probe(bridge: str, tmp: str) -> tuple[bool, str]:
    server = _emitted_server_spec(bridge)
    return asyncio.run(_round_trip(server, _shim_dir(tmp)))


# --- Case 0 ----------------------------------------------------------------


def test_declaration_table_covers_bridges() -> bool:
    """0) 선언 표가 두 축 모두에서 bridge 를 빠짐없이 덮는가."""
    bridges = set(MCP_BRIDGE_PHASE)
    modes = set(MCP_BRIDGE_APPLY_MODE)
    if len(bridges) < 2:
        print(f"  FAIL: transport_phase 표가 {len(bridges)}개 — bridge 2종을 덮어야 한다")
        return False
    if bridges != modes:
        print(f"  FAIL: 두 표의 대상이 다르다 — phase={sorted(bridges)}, apply_mode={sorted(modes)}")
        return False
    bad = {b: m for b, m in MCP_BRIDGE_APPLY_MODE.items()
           if m not in {"active_ok", "manual_review_only"}}
    if bad:
        print(f"  FAIL: apply_mode 어휘 위반 {bad}")
        return False
    print(f"  PASS: bridge {sorted(bridges)} 가 phase / apply_mode 양쪽에 선언됨")
    return True


# --- Case 1 · 2 ------------------------------------------------------------


def test_apply_mode_declarations_are_earned() -> bool:
    """1·2) 선언이 실측으로 뒷받침되는가 (`mcp` extra 없는 인터프리터 기준)."""
    try:
        import mcp  # noqa: F401, PLC0415
    except ImportError:
        # 안 잰 것은 통과가 아니다. skip 으로 넘기면 "기준을 만족했다" 와
        # "기준을 재지 않았다" 가 같은 모양이 된다.
        print("  FAIL: `mcp` SDK 부재 — 공식 클라이언트가 없으면 기준 1번을 잰 적이 "
              "없는 것이다. `pip install -e './workflow-source[mcp-sdk]'` 후 재실행")
        return False

    ok = True
    with tempfile.TemporaryDirectory() as tmp:
        for bridge in sorted(MCP_BRIDGE_APPLY_MODE):
            declared = MCP_BRIDGE_APPLY_MODE[bridge]
            passed, detail = _probe(bridge, tmp)
            if declared == "active_ok" and not passed:
                print(f"  FAIL: {bridge} — `active_ok` 로 선언했는데 기준 미달 ({detail})")
                ok = False
            elif declared == "active_ok":
                print(f"  ok: {bridge} — active_ok 근거 확인 ({detail})")
            elif passed:
                # 결함은 아니지만 조용히 넘기지 않는다: 선언이 사실보다 보수적이다.
                print(f"  [info] {bridge} — `manual_review_only` 인데 기준을 통과했다 "
                      f"({detail}). 승격을 검토할 것")
            else:
                print(f"  ok: {bridge} — manual_review_only 근거 확인 ({detail})")
    if ok:
        print("  PASS: 모든 apply_mode 선언이 실측으로 뒷받침됨")
    return ok


def main() -> int:
    cases = [
        ("test_declaration_table_covers_bridges", test_declaration_table_covers_bridges),
        ("test_apply_mode_declarations_are_earned", test_apply_mode_declarations_are_earned),
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
