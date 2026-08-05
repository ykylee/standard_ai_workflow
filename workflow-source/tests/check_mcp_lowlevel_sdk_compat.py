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

import ast
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
            self.is_error = kwargs.get("isError")  # sdk-field-ok: 2.x 를 흉내 내는 stub 의 자기 필드

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
        assert result.is_error is True, f"{server_cls.__name__}: 2.x field 에 안 닿았다"  # sdk-field-ok: 위 stub 의 필드를 읽는다


#: mcp 2.0.0 이 **snake_case 로 바꾼 필드** 의 snake 이름 (실측, 2026-08-05).
#:
#: 1.27.0 에서는 이 개념들이 **alias 없이 camelCase 필드 그 자체** 였고, 2.0.0 에서
#: 필드는 snake_case + camelCase 는 alias 가 됐다. alias 는 **생성 시 kwarg 로는
#: 통하지만 속성 접근으로는 통하지 않는다**:
#:
#:     result.isError    -> 1.x 에서만 동작 (2.x 는 AttributeError)
#:     result.is_error   -> 2.x 에서만 동작 (1.x 는 AttributeError)
#:
#: 양쪽을 지원하려면 `getattr(obj, "is_error", None)` 처럼 **문자열로** 물어야 한다.
#:
#: camelCase 쪽은 저장하지 않고 `_camel()` 로 파생한다 — 53쌍 전부 그 규칙이
#: 성립함을 실측했고, 두 목록을 나란히 두면 사본이 되어 갈라진다.
#: `meta`/`_meta` 는 **양쪽 버전 모두** alias 라 함정이 아니어서 제외한다.
RENAMED_SNAKE_FIELDS: tuple[str, ...] = (
    "cache_scope", "client_info", "cost_priority", "create_message", "created_at",
    "destructive_hint", "elicitation_id", "has_more", "idempotent_hint",
    "include_context", "input_requests", "input_responses", "input_schema",
    "intelligence_priority", "is_error", "last_modified", "last_updated_at",
    "list_changed", "max_tokens", "mime_type", "model_preferences", "next_cursor",
    "open_world_hint", "output_schema", "poll_interval", "progress_token",
    "prompts_list_changed", "protocol_version", "read_only_hint", "request_id",
    "request_state", "requested_schema", "required_capabilities",
    "resource_subscriptions", "resource_templates", "resources_list_changed",
    "result_type", "server_info", "speed_priority", "status_message", "stop_reason",
    "stop_sequences", "structured_content", "supported_versions", "system_prompt",
    "task_id", "task_support", "tool_choice", "tool_use_id", "tools_list_changed",
    "ttl_ms", "uri_template", "website_url",
)

#: 이 줄은 의도적으로 한쪽 버전 이름을 쓴다는 표시. 이유를 함께 적는다.
SDK_FIELD_MARKER = "sdk-field-ok:"


def _camel(snake: str) -> str:
    head, *rest = snake.split("_")
    return head + "".join(word[:1].upper() + word[1:] for word in rest)


def _banned_attribute_names() -> set[str]:
    return {name for snake in RENAMED_SNAKE_FIELDS for name in (snake, _camel(snake))}


def _imports_mcp(tree: ast.AST) -> bool:
    """이 모듈이 **실제로 mcp 를 import 하는가** (함수 안 지연 import 포함).

    범위를 이걸로 정하는 이유는 위양성이다. rename 된 이름 53쌍에는 `task_id`,
    `created_at`, `max_tokens` 처럼 **우리 자신의 객체에서도 흔한 이름** 이 섞여 있어,
    저장소 전역에 걸면 30건 중 28건이 위양성이었다(실측). 위양성을 내는 검사는
    무시당하고, 그러면 같은 검사가 잡아 줄 진짜 결함도 함께 무시된다(§2.48).
    """
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            if any(a.name == "mcp" or a.name.startswith("mcp.") for a in node.names):
                return True
        elif isinstance(node, ast.ImportFrom):
            if node.module and (node.module == "mcp" or node.module.startswith("mcp.")):
                return True
        elif isinstance(node, ast.Call):
            func = node.func
            is_import_module = (
                (isinstance(func, ast.Name) and func.id == "import_module")
                or (isinstance(func, ast.Attribute) and func.attr == "import_module")
            )
            if is_import_module and node.args and isinstance(node.args[0], ast.Constant):
                if str(node.args[0].value).startswith("mcp"):
                    return True
    return False


def test_no_version_locked_field_attribute_access() -> None:
    """SDK 를 쓰는 파일이 **버전 고정 필드 이름을 속성으로 읽지 않는가** (A안).

    이 저장소는 `result.isError` 함정을 이미 알고 있었다 — 바로 위
    `test_failed_invoke_sets_is_error_at_construction` 이 그것만 잡으라고 있는
    검사다. 그런데 그 검사는 *production 의 조립 경로* 만 보므로, 2026-08-05 에
    **새 파일**(`check_mcp_apply_mode_criterion.py`)이 `result.isError` 를 적었을 때
    아무것도 막지 못했고 로컬 venv 가 1.27.0 이라 통과했다. matrix 2.0.0 셀이
    잡았지만 그건 push 이후다. 여기서는 **작성 시점에** 막는다.

    의도적으로 한쪽 이름을 써야 하면(예: 2.x 를 흉내 내는 stub) 그 줄에
    `# sdk-field-ok: <이유>` 를 단다. 면제를 파일 목록으로 두면 정본과 갈라지고,
    무엇이 면제됐는지 안 보인다.

    **한계 (과장하지 않는다)**:
    - `getattr(obj, "isError")` 처럼 문자열 접근은 못 잡는다 — 그건 버전 무관
      접근자가 쓰는 형태라 의도적으로 통과시킨다.
    - mcp 를 import 하지 않는 파일이 *남에게서 받은* SDK 객체를 읽으면 못 잡는다.
      범위를 넓히면 위양성이 압도한다(위 `_imports_mcp` 참조).
    """
    banned = _banned_attribute_names()
    source_root = Path(__file__).resolve().parents[1]
    in_scope = 0
    problems: list[str] = []
    marked: list[str] = []
    for path in sorted(source_root.rglob("*.py")):
        posix = path.as_posix()
        if "/build/" in posix or "/.venv" in posix or "__pycache__" in posix:
            continue
        text = path.read_text(encoding="utf-8")
        try:
            tree = ast.parse(text)
        except SyntaxError:
            continue
        if not _imports_mcp(tree):
            continue
        in_scope += 1
        lines = text.splitlines()
        for node in ast.walk(tree):
            if not isinstance(node, ast.Attribute) or node.attr not in banned:
                continue
            line = lines[node.lineno - 1] if node.lineno <= len(lines) else ""
            where = f"{path.relative_to(source_root)}:{node.lineno} .{node.attr}"
            (marked if SDK_FIELD_MARKER in line else problems).append(where)

    assert in_scope >= 5, (
        f"mcp 를 import 하는 파일이 {in_scope}개 — 탐색 경로나 import 형태가 "
        "바뀌었는가 (대상 0건은 통과가 아니다)"
    )
    if marked:
        # 면제는 결함이 아니지만 **조용히 넘기지 않는다**.
        print(f"    [info] 의도적 면제 {len(marked)}건: {marked}")
    assert not problems, (
        "버전 고정 SDK 필드를 속성으로 읽는다 (1.x/2.x 한쪽에서 AttributeError): "
        + "; ".join(problems)
        + " — 양쪽을 지원하려면 getattr 로 두 이름을 물을 것. 의도적이면 그 줄에 "
        f"`# {SDK_FIELD_MARKER} <이유>`"
    )


def test_renamed_fields_match_installed_sdk() -> None:
    """선언한 목록이 **설치된 SDK 의 사실** 과 맞는가 (목록이 썩는 것을 막는다).

    `RENAMED_SNAKE_FIELDS` 는 손으로 적은 목록이다. SDK 가 필드를 더 바꾸면 이 목록은
    조용히 뒤처지고, 그러면 위 검사가 새 함정을 못 잡는다.

    1.x 에는 rename 된 쌍이 없으므로 대조 대상이 없다 — 그 경우 **확인하지 못했다고
    밝히고** 통과한다. 2.x 에서만 실질 판정이 된다.
    """
    try:
        types_module = importlib.import_module("mcp.types")
    except ImportError:
        print("    (skip) mcp SDK 미설치 — 설치 환경에서만 의미 있는 검사다")
        return

    observed: dict[str, str] = {}
    for cls_name in dir(types_module):
        fields = getattr(getattr(types_module, cls_name), "model_fields", None)
        if not isinstance(fields, dict):
            continue
        for field_name, field in fields.items():
            alias = getattr(field, "alias", None)
            if alias and alias != field_name and field_name != "meta":
                observed[field_name] = alias

    if not observed:
        print("    [info] 설치된 SDK 에 rename 된 쌍이 없다 (1.x) — 대조하지 못했다")
        return

    declared = set(RENAMED_SNAKE_FIELDS)
    missing = sorted(set(observed) - declared)
    assert not missing, (
        f"설치된 SDK 에 있는데 RENAMED_SNAKE_FIELDS 에 없는 필드 {len(missing)}건: "
        f"{missing} — 목록을 갱신해야 위 검사가 새 함정을 잡는다"
    )
    broken = {k: v for k, v in observed.items() if _camel(k) != v}
    assert not broken, (
        f"snake→camel 파생 규칙이 안 맞는 쌍: {broken} — camel 이름을 파생하지 말고 "
        "따로 저장해야 한다"
    )
    print(f"    [info] 설치된 SDK 의 rename {len(observed)}건이 전부 선언 + 규칙 정합")


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
        test_no_version_locked_field_attribute_access,
        test_renamed_fields_match_installed_sdk,
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
