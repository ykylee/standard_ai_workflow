"""lowlevel stdio 서버의 **1.x decorator / 2.x handler 등록** 양립 계약
(TASK-2026-07-29-main-003).

## 왜 필요한가

`read_only_mcp_sdk.py` 는 `mcp.server.lowlevel.Server` 의 `@list_tools()` /
`@call_tool()` decorator 에 의존했다. mcp 2.0.0 이 그 decorator 들을 없애고
`add_request_handler(method, params_type, handler)` 로 바꾸자 서버가 조립 단계에서
죽는다:

    AttributeError: 'Server' object has no attribute 'list_tools'

이 파손을 CI 에서 잡은 것은 `mcp-inspector` workflow **하나뿐**이었고, 그 workflow 는
`workflow-source/workflow_kit/server/**` 가 바뀔 때만 돈다. 그래서 상한 핀을 풀었던
커밋이 우연히 그 경로를 건드리기 전까지 아무도 보지 않았다. smoke 는 못 잡는다 —
`check_mcp_tool_descriptors.py` 는 **커밋된 파일의 모양**만 보고 서버를 띄우지 않는다.

이 검사는 그 사이를 메운다. SDK 설치 없이도 도는 **조립 계약** 검사다: 두 형태의
`Server` 를 흉내내고, 조립기가 각각에 맞게 등록하는지를 본다.

## 계약

1. handler 등록형(`add_request_handler` 존재)이면 `tools/list` / `tools/call` 을
   등록하고 decorator 는 건드리지 않는다.
2. decorator 형이면 `list_tools()` / `call_tool()` 을 쓴다.
3. 두 형태의 판정은 **버전 문자열이 아니라 계약의 존재**로 한다
   (`uses_handler_registration`).
4. 등록되는 method/params_type 쌍이 SDK 가 기대하는 이름과 같다
   (`tools/list` ↔ `PaginatedRequestParams`, `tools/call` ↔ `CallToolRequestParams`).
5. 2.x handler 는 `ListToolsResult` / `CallToolResult` 를 돌려준다 (list 가 아니다).
6. tool 실패(returncode != 0)는 **생성 시점에** `isError` 로 들어간다. 나중 대입
   (`result.isError = True`)은 2.x 에서 이름이 달라(`is_error`) 조용히 빗나간다.
7. 설치된 SDK 가 있으면 그것으로 실제 조립까지 해 본다.

Cross-ref: TASK-2026-07-29-main-003, releases/Beta-v1.0.0.md §2.43.
"""

from __future__ import annotations

import asyncio
import importlib
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

SOURCE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SOURCE_ROOT))

from workflow_kit.server import read_only_mcp_sdk as mod  # noqa: E402


class _FakeTypes:
    """`mcp.types` 중 조립기가 만지는 것만."""

    class Tool:
        def __init__(self, **kwargs: Any) -> None:
            self.kwargs = kwargs
            self.name = kwargs.get("name")

    class TextContent:
        def __init__(self, **kwargs: Any) -> None:
            self.kwargs = kwargs

    class CallToolResult:
        def __init__(self, **kwargs: Any) -> None:
            self.kwargs = kwargs
            # 2.x 의 실제 field 이름. 예전처럼 `result.isError = True` 로 나중에
            # 덮으면 여기에 안 닿는다 — 그 사고를 재현할 수 있게 이름을 맞춰 둔다.
            self.is_error = kwargs.get("isError")

    class ListToolsResult:
        def __init__(self, **kwargs: Any) -> None:
            self.kwargs = kwargs
            self.tools = kwargs.get("tools")

    PaginatedRequestParams = type("PaginatedRequestParams", (), {})
    CallToolRequestParams = type("CallToolRequestParams", (), {})


class _HandlerServer:
    """mcp >= 2.0 형태."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.registered: dict[str, tuple[Any, Any]] = {}

    def add_request_handler(self, method: str, params_type: Any, handler: Any) -> None:
        self.registered[method] = (params_type, handler)


class _DecoratorServer:
    """mcp 1.x 형태."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.list_tools_handler: Any = None
        self.call_tool_handler: Any = None
        self.call_tool_kwargs: dict[str, Any] = {}

    def list_tools(self) -> Any:
        def _register(fn: Any) -> Any:
            self.list_tools_handler = fn
            return fn

        return _register

    def call_tool(self, **kwargs: Any) -> Any:
        self.call_tool_kwargs = kwargs

        def _register(fn: Any) -> Any:
            self.call_tool_handler = fn
            return fn

        return _register


class _FakeLowlevel:
    def __init__(self, server_cls: type) -> None:
        self.Server = server_cls


@contextmanager
def _fake_sdk(server_cls: type, *, invoke: Any = None) -> Iterator[Any]:
    """조립기를 가짜 SDK 로 돌린다. yield 되는 것은 조립된 server.

    **patch 를 handler 호출까지 살려 둔다.** 초안은 build 직후 `finally` 로 되돌렸고,
    그래서 handler 안에서는 *진짜* `invoke_tool` 이 불렸다 — `isError` 되주입이
    통과해 버렸다(실측). 가짜를 심는 범위가 검사하려는 코드보다 좁으면, 검사는
    자기가 심은 것을 보지 못한다.
    """
    sdk = mod.OfficialSdkModules(
        types=_FakeTypes,
        stdio=object(),
        lowlevel=_FakeLowlevel(server_cls),
        models=object(),
    )
    saved_import = mod._import_sdk_modules
    saved_invoke = mod.invoke_tool
    mod._import_sdk_modules = lambda: sdk  # type: ignore[assignment]
    if invoke is not None:
        mod.invoke_tool = invoke  # type: ignore[assignment]
    try:
        yield mod.build_lowlevel_server()
    finally:
        mod._import_sdk_modules = saved_import  # type: ignore[assignment]
        mod.invoke_tool = saved_invoke  # type: ignore[assignment]


def test_handler_form_registers_both_methods() -> None:
    with _fake_sdk(_HandlerServer) as server:
        assert set(server.registered) == {"tools/list", "tools/call"}, sorted(server.registered)


def test_handler_form_uses_expected_params_types() -> None:
    with _fake_sdk(_HandlerServer) as server:
        assert server.registered["tools/list"][0] is _FakeTypes.PaginatedRequestParams
        assert server.registered["tools/call"][0] is _FakeTypes.CallToolRequestParams


def test_decorator_form_registers_both_handlers() -> None:
    with _fake_sdk(_DecoratorServer) as server:
        assert server.list_tools_handler is not None, "1.x 에서 list_tools 가 등록되지 않았다"
        assert server.call_tool_handler is not None, "1.x 에서 call_tool 이 등록되지 않았다"
        assert server.call_tool_kwargs.get("validate_input") is False, server.call_tool_kwargs


def test_form_is_decided_by_contract_not_version() -> None:
    assert mod.uses_handler_registration(_HandlerServer("x")) is True
    assert mod.uses_handler_registration(_DecoratorServer("x")) is False


def test_handler_form_returns_result_objects_not_lists() -> None:
    with _fake_sdk(_HandlerServer, invoke=lambda name, args: (0, {"status": "ok"})) as server:
        listed = asyncio.run(server.registered["tools/list"][1](None, None))
        assert isinstance(listed, _FakeTypes.ListToolsResult), type(listed).__name__
        assert isinstance(listed.tools, list), "ListToolsResult.tools 가 list 가 아니다"

        params = type("P", (), {"name": "latest_backlog", "arguments": {}})()
        called = asyncio.run(server.registered["tools/call"][1](None, params))
        assert isinstance(called, _FakeTypes.CallToolResult), type(called).__name__


def test_decorator_form_returns_plain_tool_list() -> None:
    with _fake_sdk(_DecoratorServer) as server:
        listed = asyncio.run(server.list_tools_handler())
        assert isinstance(listed, list), "1.x list_tools 는 list 를 돌려줘야 한다"


def test_failed_invoke_sets_is_error_at_construction() -> None:
    """`result.isError = True` 로 나중에 덮으면 2.x 에서 빗나간다."""
    for server_cls, call in (
        (_HandlerServer, lambda s: s.registered["tools/call"][1](None, type("P", (), {"name": "t", "arguments": {}})())),
        (_DecoratorServer, lambda s: s.call_tool_handler("t", {})),
    ):
        with _fake_sdk(server_cls, invoke=lambda name, args: (1, {"status": "ok"})) as server:
            result = asyncio.run(call(server))
        assert result.kwargs.get("isError") is True, (
            f"{server_cls.__name__}: returncode != 0 인데 isError 가 생성 시점에 안 들어갔다 "
            f"({result.kwargs.get('isError')!r})"
        )
        assert result.is_error is True, f"{server_cls.__name__}: 2.x field 에 안 닿았다"


def test_installed_sdk_actually_assembles() -> None:
    """설치된 진짜 SDK 로 조립까지 해 본다 (가짜는 우리 믿음만 검사한다)."""
    try:
        importlib.import_module("mcp.server.lowlevel")
    except ImportError:
        print("    (skip) mcp SDK 미설치 — 설치 환경에서만 의미 있는 검사다")
        return

    server = mod.build_lowlevel_server()
    if mod.uses_handler_registration(server):
        registered = getattr(server, "_request_handlers", {})
        for method in ("tools/list", "tools/call"):
            assert method in registered, f"실제 SDK 에 {method} 가 등록되지 않았다"
    else:
        # 1.x 는 등록 결과를 `request_handlers` 로 들고 있다.
        registered = getattr(server, "request_handlers", {})
        assert registered, "실제 SDK(1.x) 에 handler 가 하나도 등록되지 않았다"


def main() -> int:
    test_funcs = [
        test_handler_form_registers_both_methods,
        test_handler_form_uses_expected_params_types,
        test_decorator_form_registers_both_handlers,
        test_form_is_decided_by_contract_not_version,
        test_handler_form_returns_result_objects_not_lists,
        test_decorator_form_returns_plain_tool_list,
        test_failed_invoke_sets_is_error_at_construction,
        test_installed_sdk_actually_assembles,
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
