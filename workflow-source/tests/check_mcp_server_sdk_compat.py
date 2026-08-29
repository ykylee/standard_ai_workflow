"""MCP SDK server wrapper 의 **1.x / 2.x 양쪽 해석** 계약 (TASK-2026-07-29-main-001).

## 왜 필요한가

`mcp_v1_server.py` 는 `from mcp.server.fastmcp import FastMCP` 라는 **단일 이름**에
의존했다. mcp 2.0.0 이 그 모듈을 없애고 `mcp.server.mcpserver.MCPServer` 로 옮기자
(2026-07-29 실측) import 가 항상 ImportError 로 떨어져 `HAS_FASTMCP=False` →
`sys.exit(1)` 이 됐다. 런타임 파손인데 CI 가 보고한 것은 엉뚱하게도
`mcp_v1_server.py:27 no-any-return` 이었다 — `ignore_missing_imports = true` 가
사라진 모듈을 error 가 아니라 `Any` 로 바꿔 놓았기 때문이다.

그래서 이 검사는 **설치된 SDK 가 무엇이든** wrapper 가 서버를 만들 수 있는지를 본다.
설치된 한 버전에서만 도는 검사는 다음 major 에서 또 같은 방식으로 놓친다. 세 환경을
`sys.modules` 에 심어 각각 재해석시킨다: 2.x 만 / 1.x 만 / 둘 다 없음.

## 계약

1. 2.x 만 있으면 `mcp.server.mcpserver.MCPServer` 를 잡는다.
2. 1.x 만 있으면 `mcp.server.fastmcp.FastMCP` 를 잡는다.
3. 둘 다 있으면 **새 것(2.x)** 을 잡는다.
4. 둘 다 없으면 `HAS_MCP_SERVER=False` 이고, 서버 생성은 조용히 성공하지 않고
   `SystemExit(1)` 로 죽는다 (fail-fast 보존).
5. 어느 쪽을 잡았는지 `MCP_SERVER_SOURCE` 로 드러난다 (진단 가능성).
6. 실제로 설치된 SDK 로 `create_v1_server` → `.tool()` decorator 가 함수를 그대로
   돌려주고 `.run` 이 호출 가능하다 (stub 이 아닌 진짜 계약 확인).

Cross-ref: TASK-2026-07-29-main-001, TASK-2026-07-29-main-002.
"""

from __future__ import annotations

#: 이 검사의 입력 표면 (spec `core/test_impact_tiering_spec.md` §2).
#: 게이트 채취 실측에서 뽑아 넓은 쪽으로 올렸다 — 좁으면 meta-watch 가 red 로 잡는다.
WATCHES = (
    "workflow-source/pyproject.toml",
    "workflow-source/workflow_kit/*",
)

import importlib
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

SOURCE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SOURCE_ROOT))

MODULE_NAME = "workflow_kit.server.mcp_v1_server"

V2_MODULE = "mcp.server.mcpserver"
V1_MODULE = "mcp.server.fastmcp"


class _RecordingServer:
    """FastMCP / MCPServer 의 *이 wrapper 가 쓰는 범위* 만 흉내낸다."""

    def __init__(self, name: str | None = None, **kwargs: Any) -> None:
        self.name = name
        self.kwargs = kwargs
        self.registered: list[tuple[str | None, str | None]] = []
        self.ran = False

    def tool(self, name: str | None = None, description: str | None = None) -> Any:
        self.registered.append((name, description))

        def _decorator(fn: Any) -> Any:
            return fn

        return _decorator

    def run(self) -> None:
        self.ran = True


def _install_stub(module_path: str, attr: str) -> None:
    """`module_path` 에 `attr` 이름의 stub 클래스를 심는다 (부모 패키지까지)."""
    parts = module_path.split(".")
    for i in range(1, len(parts) + 1):
        dotted = ".".join(parts[:i])
        if dotted not in sys.modules:
            mod = ModuleType(dotted)
            mod.__path__ = []  # type: ignore[attr-defined]
            sys.modules[dotted] = mod
        if i > 1:
            setattr(sys.modules[".".join(parts[: i - 1])], parts[i - 1], sys.modules[dotted])
    setattr(sys.modules[module_path], attr, _RecordingServer)


def _reload_with(env: str) -> ModuleType:
    """`env` 가 지정한 SDK 만 존재하는 상태로 wrapper 를 다시 해석한다.

    env: "v2" | "v1" | "both" | "none"
    """
    saved = {k: v for k, v in sys.modules.items() if k == "mcp" or k.startswith("mcp.")}
    saved_wrapper = sys.modules.pop(MODULE_NAME, None)
    for key in list(sys.modules):
        if key == "mcp" or key.startswith("mcp."):
            del sys.modules[key]
    try:
        if env in ("v2", "both"):
            _install_stub(V2_MODULE, "MCPServer")
        if env in ("v1", "both"):
            _install_stub(V1_MODULE, "FastMCP")
        if env == "none":
            # sys.modules 에서 지우기만 하면 **디스크에 설치된 진짜 mcp 를 다시 찾아온다**
            # (초안이 이 함정에 걸려 "SDK 없음" 을 재현하지 못했다). `None` 을 심어 두면
            # import 가 ImportError 로 끝난다 — 미설치 환경과 같은 신호다.
            sys.modules["mcp"] = None  # type: ignore[assignment]
        return importlib.import_module(MODULE_NAME)
    finally:
        for key in list(sys.modules):
            if key == "mcp" or key.startswith("mcp."):
                del sys.modules[key]
        sys.modules.update(saved)
        if saved_wrapper is not None:
            sys.modules[MODULE_NAME] = saved_wrapper
        else:
            sys.modules.pop(MODULE_NAME, None)


def test_v2_only_resolves_mcpserver() -> None:
    mod = _reload_with("v2")
    assert mod.HAS_MCP_SERVER is True, "2.x 만 있는데 SDK 없음으로 판정했다"
    assert mod.MCP_SERVER_SOURCE == "mcp.server.mcpserver.MCPServer", mod.MCP_SERVER_SOURCE


def test_v1_only_resolves_fastmcp() -> None:
    mod = _reload_with("v1")
    assert mod.HAS_MCP_SERVER is True, "1.x 만 있는데 SDK 없음으로 판정했다"
    assert mod.MCP_SERVER_SOURCE == "mcp.server.fastmcp.FastMCP", mod.MCP_SERVER_SOURCE


def test_both_present_prefers_v2() -> None:
    mod = _reload_with("both")
    assert mod.MCP_SERVER_SOURCE == "mcp.server.mcpserver.MCPServer", (
        f"둘 다 있으면 새 SDK 를 잡아야 한다 — {mod.MCP_SERVER_SOURCE}"
    )


def test_neither_present_fails_fast() -> None:
    mod = _reload_with("none")
    assert mod.HAS_MCP_SERVER is False, "SDK 가 없는데 있다고 판정했다"
    assert mod.MCP_SERVER_SOURCE is None, mod.MCP_SERVER_SOURCE
    try:
        mod.create_v1_server("x", version="0")
    except SystemExit as exc:
        assert exc.code == 1, f"exit code 가 1 이 아니다: {exc.code}"
    else:  # pragma: no cover - 계약 위반 시에만 도달
        raise AssertionError("SDK 없이 서버가 만들어졌다 — fail-fast 가 사라졌다")


def test_legacy_alias_tracks_new_flag() -> None:
    """`HAS_FASTMCP` 를 읽는 코드가 남아 있어도 판정이 갈리지 않는다."""
    for env in ("v1", "v2", "none"):
        mod = _reload_with(env)
        assert mod.HAS_FASTMCP == mod.HAS_MCP_SERVER, f"{env}: 별칭이 어긋났다"


def test_decorator_returns_function_unchanged() -> None:
    mod = _reload_with("v2")
    server = mod.create_v1_server("stub-server", version="0.0.0")

    def payload(a: int) -> int:
        return a

    assert server.tool(name="t", description="d")(payload) is payload, (
        ".tool() decorator 가 원래 함수를 돌려주지 않았다"
    )
    assert server.mcp.registered == [("t", "d")], server.mcp.registered
    server.run()
    assert server.mcp.ran is True, ".run() 이 SDK 로 전달되지 않았다"


def test_installed_sdk_actually_works() -> None:
    """stub 이 아니라 **설치된 진짜 SDK** 로 한 번 더 확인한다.

    stub 은 우리가 믿는 계약을 검사할 뿐이라, 그 믿음이 틀리면 같이 틀린다.
    """
    mod = importlib.import_module(MODULE_NAME)
    if not mod.HAS_MCP_SERVER:
        # 여기서 무조건 skip 하면, 다음 major 가 **두 이름을 다 없앴을 때도** 조용히
        # 통과한다 — 이 저장소가 이미 한 번 당한 "미분류는 통과" 패턴이다.
        # 그래서 mcp 자체가 없을 때만 skip 하고, mcp 는 있는데 서버 구현을 못 잡는
        # 경우는 **실패**로 드러낸다.
        try:
            importlib.import_module("mcp")
        except ImportError:
            print("    (skip) mcp SDK 미설치 — 설치 환경에서만 의미 있는 검사다")
            return
        raise AssertionError(
            "mcp 는 설치돼 있는데 서버 구현을 못 잡았다 — SDK 가 또 이름을 옮겼을 수 있다. "
            "mcp.server 하위 모듈 목록을 확인하고 import 사슬에 새 이름을 추가할 것."
        )

    assert mod.MCP_SERVER_SOURCE in (
        "mcp.server.mcpserver.MCPServer",
        "mcp.server.fastmcp.FastMCP",
    ), mod.MCP_SERVER_SOURCE

    server = mod.create_v1_server("compat-check", version="0.0.0")

    def payload(a: int) -> int:
        return a

    assert server.tool(name="compat_tool", description="compat")(payload) is payload, (
        f"{mod.MCP_SERVER_SOURCE}: .tool() 이 원래 함수를 돌려주지 않았다"
    )
    assert callable(getattr(server.mcp, "run", None)), f"{mod.MCP_SERVER_SOURCE}: .run 이 없다"


def main() -> int:
    test_funcs = [
        test_v2_only_resolves_mcpserver,
        test_v1_only_resolves_fastmcp,
        test_both_present_prefers_v2,
        test_neither_present_fails_fast,
        test_legacy_alias_tracks_new_flag,
        test_decorator_returns_function_unchanged,
        test_installed_sdk_actually_works,
    ]
    failures: list[tuple[str, str]] = []
    for func in test_funcs:
        try:
            func()
            print(f"  PASS: {func.__name__}")
        except AssertionError as e:
            failures.append((func.__name__, f"AssertionError: {e}"))
            print(f"  FAIL: {func.__name__} — {e}")
        except SystemExit as e:
            # wrapper 의 fail-fast 는 `sys.exit(1)` 이다. 잡지 않으면 결함 되주입 시
            # 첫 SystemExit 이 runner 를 통째로 끝내고 나머지 검사와 요약 줄이 사라진다
            # (실측). 실패는 실패로 세되 나머지는 계속 돌린다.
            failures.append((func.__name__, f"SystemExit: {e.code}"))
            print(f"  FAIL: {func.__name__} — 예상치 못한 SystemExit({e.code})")
        except Exception as e:  # noqa: BLE001
            failures.append((func.__name__, f"{type(e).__name__}: {e}"))
            print(f"  FAIL: {func.__name__} — {type(e).__name__}: {e}")

    total = len(test_funcs)
    print(f"\n{total - len(failures)}/{total} PASS")
    if failures:
        for name, err in failures:
            print(f"  - {name}: {err}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
