"""허브 ASGI 앱 — ``/healthz`` · ``POST /v1/tools/<name>`` · ``/mcp`` (hub_spec §4.1, DS1 · DS5).

MCP 와 HTTP 는 :func:`workflow_kit.hub.tools.call` 하나를 부른다. MCP 는 공식 SDK 의
lowlevel 서버를 stateless streamable HTTP 로 연다 — 도구 목록 · 호출 처리기가 요청의
``Authorization`` 머리를 읽어 인증 경계(토큰 없으면 부트스트랩 묶음만, 요구 R2.3)를 긋는다.

시각은 요청마다 한 번 :data:`clock` 으로 정해 도구에 넘긴다 (hub_spec §1-7).
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, AsyncIterator, Callable

import mcp.types as mtypes
from mcp.server.lowlevel import Server
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from starlette.applications import Starlette
from starlette.concurrency import run_in_threadpool
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, Response
from starlette.routing import Route
from starlette.types import Receive, Scope, Send

from workflow_kit import __version__ as HUB_VERSION
from workflow_kit.hub import CONTRACT, KIT_COMPAT_VERSION
from workflow_kit.hub import tools as hubtools
from workflow_kit.hub.errors import HubError
from workflow_kit.hub.orchestration import WAIT_CAP_S, Orchestration
from workflow_kit.hub.relay import POLL_CAP_S, Relays
from workflow_kit.hub.store import Ctx, Principal, Store

#: 요청 본문 상한 (요구 R13.5).
MAX_BODY = 256 * 1024
#: 허브 전역 동시 대기 상한 · 대기 중 들여다보기 간격 (2.1 스펙 §6.2).
WAIT_CAPACITY = 64
WAIT_POLL_S = 0.5
#: 큰 상한을 받는 도구 — 1.x 전환의 대량 운반은 선택 클라이언트가 한다 (소유자 2026-11-21, 리허설 §16.5:
#: 이 저장소의 감지 결과만 ~430KB). LLM 이 도구 인자로 싣는 경로(MCP)에는 해당하지 않는다.
BIG_BODY_TOOLS: dict[str, int] = {"hub_migrate_plan": 8 * 1024 * 1024, "hub_migrate_import": 8 * 1024 * 1024,
                                  "hub_project_import": 64 * 1024 * 1024}  # 허브 간 이전 묶음 (클라이언트가 나른다)

Clock = Callable[[], datetime]


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _bearer(headers: Any) -> str | None:
    raw = headers.get("authorization") or ""
    if raw.lower().startswith("bearer "):
        token = raw[7:].strip()
        return token or None
    return None


def _hub_headers(store: Store) -> dict[str, str]:
    return {"X-Hub-Version": HUB_VERSION, "X-Hub-Kit": KIT_COMPAT_VERSION,
            "X-Hub-Contract": CONTRACT, "X-Hub-Db": str(store.db_version())}


def build_app(store: Store, *, public_url: str, exposure: str = "loopback", clock: Clock = utc_now,
              web_token_name: str | None = None) -> Starlette:
    """허브 앱. ``exposure`` 는 healthz 에 싣는 노출 상태 (요구 R13.3).

    ``web_token_name`` 은 화면 공용 ``web`` 토큰의 이름 — 주면 토큰 없는 화면 요청이 그 권한으로 돈다 (R13.2a, 기본 꺼짐).
    """
    # 제네릭 인자 수 · 모델 키워드 이름이 mcp 1.x 와 2.x 에서 다르다 (2.x: `Server[L]`, `structured_content`) — 서버는 Any 로
    # 받고, 결과 모델은 **wire 이름**(camelCase)으로 `model_validate` 해 두 판에서 같은 코드가 타입 검사를 지난다 (main-022).
    server: Any = Server("workflow-hub", version=HUB_VERSION, instructions=f"kit compatibility {KIT_COMPAT_VERSION}")

    def principal_from_request(req: Any) -> tuple[Principal | None, bool]:
        token = _bearer(req.headers) if req is not None else None
        client = req.headers.get("x-hub-client") if req is not None else None
        principal = store.authenticate(token, clock(), client) if token else None
        return principal, token is not None

    waiting = {"n": 0}

    async def wait_async(principal: Principal | None, args: dict[str, Any], via: str,
                         client_version: str | None) -> dict[str, Any]:
        """``hub_wait`` — 스레드 풀 밖에서 기다린다 (스펙 §6.2 · DO3). 들여다보기만 스레드 풀에서 짧게 돈다.

        도구를 스레드 풀에서 막아 두면 기다리는 세션 수만큼 스레드를 쥐어(anyio 기본 40) 다른 도구가 멈춘다.
        """
        def ctx() -> Ctx:
            return Ctx(now=clock(), via=via, principal=principal, client_version=client_version, public_url=public_url)

        _spec, clean = await run_in_threadpool(hubtools.prepare, store, "hub_wait", args, ctx())
        timeout = clean.get("timeout_s") or WAIT_CAP_S
        if not 1 <= timeout:
            raise HubError(400, "invalid_field", "timeout_s: 1 이상", {"field": "timeout_s"})
        timeout = min(timeout, WAIT_CAP_S)
        if waiting["n"] >= WAIT_CAPACITY:
            raise HubError(429, "wait_capacity", f"허브의 동시 대기 상한 {WAIT_CAPACITY} — 잠시 뒤 다시 부른다",
                           {"limit": WAIT_CAPACITY})
        orch = Orchestration(store)
        sid = clean["session"]
        waiting["n"] += 1
        start = time.monotonic()
        try:
            got = await run_in_threadpool(lambda: orch.wait_poll(ctx(), sid, first=True))
            while got is None and time.monotonic() - start < timeout:
                await asyncio.sleep(WAIT_POLL_S)
                got = await run_in_threadpool(lambda: orch.wait_poll(ctx(), sid, first=False))
            waited = int(time.monotonic() - start)
            if got is None:
                return await run_in_threadpool(lambda: orch.wait_timeout(ctx(), sid, waited))
            return {**got, "waited_s": waited}
        except asyncio.CancelledError:
            # 클라이언트가 끊었다 — '대기 중' 표시를 남기지 않는다. 실린 메시지는 ack 전까지 다시 실린다 (DO13).
            orch.wait_clear(ctx(), sid)
            raise
        finally:
            waiting["n"] -= 1

    async def list_tools_for(req: Any) -> list[mtypes.Tool]:
        principal, _ = await run_in_threadpool(principal_from_request, req)
        caller_kind = principal.kind if principal is not None else None
        return [
            mtypes.Tool.model_validate({"name": t.name, "description": t.description, "inputSchema": t.schema()})
            for t in hubtools.visible_tools(caller_kind)
        ]

    async def call_tool_for(req: Any, name: str, arguments: dict[str, Any] | None) -> mtypes.CallToolResult:
        def run() -> dict[str, Any]:
            principal, sent = principal_from_request(req)
            spec = hubtools.TOOLS.get(name)
            if sent and principal is None and spec is not None and spec.bundle != "bootstrap":
                raise HubError(401, "unauthorized", "토큰이 틀렸거나 거둔 토큰이다")
            ctx = Ctx(now=clock(), via="mcp", principal=principal, public_url=public_url)
            return hubtools.call(store, name, arguments or {}, ctx)

        try:
            if name == "hub_wait":
                principal, sent = await run_in_threadpool(principal_from_request, req)
                if sent and principal is None:
                    raise HubError(401, "unauthorized", "토큰이 틀렸거나 거둔 토큰이다")
                result = await wait_async(principal, arguments or {}, "mcp", None)
            else:
                result = await run_in_threadpool(run)
            return mtypes.CallToolResult.model_validate({
                "content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}],
                "structuredContent": result,
            })
        except HubError as e:
            payload = e.payload()
            return mtypes.CallToolResult.model_validate({
                "content": [{"type": "text", "text": json.dumps(payload, ensure_ascii=False)}],
                "structuredContent": payload,
                "isError": True,
            })

    # mcp 1.x 는 decorator 형, 2.x 는 처리기 등록형 (2.0 이 `list_tools` · `call_tool` decorator 를 없앴다) — 판 문자열이 아니라
    # **계약의 존재**로 가른다 (1.x kit `server/read_only_mcp_sdk.uses_handler_registration` 과 같은 기준, TASK-2026-11-22-main-022).
    # HTTP 요청은 1.x 에서 `server.request_context`, 2.x 에서 처리기 인자 `ctx.request` 로 온다.
    srv = server
    if hasattr(srv, "add_request_handler"):  # mcp >= 2.0
        async def on_list_tools(ctx: Any, params: Any) -> Any:
            return mtypes.ListToolsResult(tools=await list_tools_for(ctx.request))

        async def on_call_tool(ctx: Any, params: Any) -> Any:
            return await call_tool_for(ctx.request, params.name, getattr(params, "arguments", None))

        srv.add_request_handler("tools/list", getattr(mtypes, "PaginatedRequestParams"), on_list_tools)
        srv.add_request_handler("tools/call", mtypes.CallToolRequestParams, on_call_tool)
    else:  # mcp 1.x
        @srv.list_tools()  # type: ignore[untyped-decorator]
        async def _list_tools() -> list[mtypes.Tool]:
            return await list_tools_for(server.request_context.request)

        @srv.call_tool(validate_input=False)  # type: ignore[untyped-decorator]
        async def _call_tool(name: str, arguments: dict[str, Any]) -> mtypes.CallToolResult:
            return await call_tool_for(server.request_context.request, name, arguments)

    manager = StreamableHTTPSessionManager(app=server, stateless=True, json_response=True)

    class _McpEndpoint:
        """클래스 인스턴스라 Starlette 가 ASGI 앱으로 부른다 (함수면 요청 처리기로 본다)."""

        async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
            await manager.handle_request(scope, receive, send)

    async def guide_page(request: Request) -> Response:
        from workflow_kit.hub.guide_page import render_page

        return HTMLResponse(render_page(public_url), headers={
            **_hub_headers(store),
            "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; frame-ancestors 'none'",
            "Referrer-Policy": "same-origin",
        })

    async def setup_md(request: Request) -> Response:
        # 에이전트용 셋업 절차 (M-039 WBS-39.1) — 토큰 없이. 비밀이 없다.
        from workflow_kit.hub.guide_page import render_setup_md

        return Response(render_setup_md(public_url), media_type="text/markdown; charset=utf-8", headers=_hub_headers(store))

    async def hub_client_source(request: Request) -> Response:
        # 선택 클라이언트 원문 (hub_spec §7) — 토큰 없이 받는다: 비밀이 없고, 토큰은 .workflow-hub/env 에서 읽는다.
        src = (Path(__file__).resolve().parent / "client" / "hub_client.py").read_text(encoding="utf-8")
        return Response(src, media_type="text/x-python; charset=utf-8")

    async def healthz(request: Request) -> Response:
        return JSONResponse(
            {"ok": True, "hub_version": HUB_VERSION, "kit_version": KIT_COMPAT_VERSION,
             "contract": CONTRACT, "db_version": store.db_version(),
             "exposure": exposure, "public_url": public_url, "web_token": bool(web_token_name)},
            headers=_hub_headers(store),
        )

    async def tool_http(request: Request) -> Response:
        name = request.path_params["name"]
        headers = _hub_headers(store)
        try:
            contract = request.headers.get("x-hub-contract")
            if contract is not None and contract != CONTRACT:
                raise HubError(400, "unknown_contract", f"모르는 계약 판: {contract!r} — 이 허브는 {CONTRACT}")
            body = await request.body()
            limit = BIG_BODY_TOOLS.get(name, MAX_BODY)
            if len(body) > limit:
                raise HubError(413, "payload_too_large", f"본문 상한 {limit} 바이트", {"limit": limit})
            try:
                args = json.loads(body.decode("utf-8")) if body.strip() else {}
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise HubError(400, "invalid_json", f"본문이 JSON 이 아니다: {exc}") from exc
            token = _bearer(request.headers)
            now = clock()

            def run() -> dict[str, Any]:
                principal = store.authenticate(token, now, request.headers.get("x-hub-client")) if token else None
                spec = hubtools.TOOLS.get(name)
                if token and principal is None and spec is not None and spec.bundle != "bootstrap":
                    raise HubError(401, "unauthorized", "토큰이 틀렸거나 거둔 토큰이다")
                ctx = Ctx(now=now, via="http", principal=principal,
                          client_version=request.headers.get("x-hub-client"), public_url=public_url)
                return hubtools.call(store, name, args, ctx)

            if name == "hub_wait":
                principal = await run_in_threadpool(
                    lambda: store.authenticate(token, now, request.headers.get("x-hub-client")) if token else None)
                if token and principal is None:
                    raise HubError(401, "unauthorized", "토큰이 틀렸거나 거둔 토큰이다")
                result = await wait_async(principal, args, "http", request.headers.get("x-hub-client"))
            else:
                result = await run_in_threadpool(run)
            return JSONResponse(result, headers=headers)
        except HubError as e:
            return JSONResponse(e.payload(), status_code=e.status, headers=headers)

    relays = Relays(store)

    async def _relay_body(request: Request) -> Any:
        body = await request.body()
        if len(body) > MAX_BODY:
            raise HubError(413, "payload_too_large", f"본문 상한 {MAX_BODY} 바이트", {"limit": MAX_BODY})
        try:
            return json.loads(body.decode("utf-8")) if body.strip() else {}
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise HubError(400, "invalid_json", f"본문이 JSON 이 아니다: {exc}") from exc

    async def _relay_host(request: Request) -> Any:
        host = await run_in_threadpool(relays.authenticate, _bearer(request.headers))
        if host is None:
            raise HubError(401, "unauthorized", "중계 토큰이 없거나 틀렸거나 거둔 토큰이다")
        return host

    async def relay_register(request: Request) -> Response:
        """``relay init`` — 초대 코드 → host_id · 중계 토큰 (스펙 §9.1, DO8)."""
        headers = _hub_headers(store)
        try:
            args = await _relay_body(request)
            result = await run_in_threadpool(relays.register, clock(), args)
            return JSONResponse(result, headers=headers)
        except HubError as e:
            return JSONResponse(e.payload(), status_code=e.status, headers=headers)

    async def relay_poll(request: Request) -> Response:
        """긴 폴링 — 중계가 나가는 연결로 가져간다 (스펙 §9.2, 요구 R21.2). 일이 생기면 바로, 없으면 상한에서 빈 응답."""
        headers = _hub_headers(store)
        try:
            host = await _relay_host(request)
            args = await _relay_body(request)
            if not isinstance(args, dict) or set(args) - {"wait_s", "sessions", "allow_digest"}:
                raise HubError(400, "unknown_field", "wait_s · sessions · allow_digest 만 받는다")
            wait_s = args.get("wait_s", POLL_CAP_S)
            if not isinstance(wait_s, int) or isinstance(wait_s, bool) or wait_s < 0:
                raise HubError(400, "invalid_field", "wait_s: 0 이상 정수", {"field": "wait_s"})
            wait_s = min(wait_s, POLL_CAP_S)
            start = time.monotonic()
            got = await run_in_threadpool(relays.poll_once, clock(), host, args)
            light = {k: v for k, v in args.items() if k == "allow_digest"}  # 상태 보고는 첫 번에만 반영
            while not (got["dispatch"] or got["deliver"]) and time.monotonic() - start < wait_s:
                await asyncio.sleep(WAIT_POLL_S)
                got = await run_in_threadpool(relays.poll_once, clock(), host, light)
            return JSONResponse({**got, "waited_s": int(time.monotonic() - start)}, headers=headers)
        except HubError as e:
            return JSONResponse(e.payload(), status_code=e.status, headers=headers)

    async def relay_result(request: Request) -> Response:
        headers = _hub_headers(store)
        try:
            host = await _relay_host(request)
            args = await _relay_body(request)
            result = await run_in_threadpool(relays.result, clock(), host, args)
            return JSONResponse(result, headers=headers)
        except HubError as e:
            return JSONResponse(e.payload(), status_code=e.status, headers=headers)

    @contextlib.asynccontextmanager
    async def lifespan(_app: Starlette) -> AsyncIterator[None]:
        async with manager.run():
            yield

    from workflow_kit.hub.ui import build_routes

    ui_routes = build_routes(store, clock=clock, web_token_name=web_token_name,
                             hub_headers=lambda: _hub_headers(store), max_body=MAX_BODY, public_url=public_url)

    return Starlette(
        routes=[
            *ui_routes,
            Route("/", guide_page, methods=["GET"]),
            Route("/healthz", healthz, methods=["GET"]),
            Route("/setup.md", setup_md, methods=["GET"]),
            Route("/v1/bootstrap/hub_client.py", hub_client_source, methods=["GET"]),
            Route("/v1/tools/{name}", tool_http, methods=["POST"]),
            Route("/v1/relay/register", relay_register, methods=["POST"]),
            Route("/v1/relay/poll", relay_poll, methods=["POST"]),
            Route("/v1/relay/result", relay_result, methods=["POST"]),
            Route("/mcp", _McpEndpoint(), methods=["GET", "POST", "DELETE"]),
        ],
        lifespan=lifespan,
    )
