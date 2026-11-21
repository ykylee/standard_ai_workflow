"""허브 ASGI 앱 — ``/healthz`` · ``POST /v1/tools/<name>`` · ``/mcp`` (hub_spec §4.1, DS1 · DS5).

MCP 와 HTTP 는 :func:`workflow_kit.hub.tools.call` 하나를 부른다. MCP 는 공식 SDK 의
lowlevel 서버를 stateless streamable HTTP 로 연다 — 도구 목록 · 호출 처리기가 요청의
``Authorization`` 머리를 읽어 인증 경계(토큰 없으면 부트스트랩 묶음만, 요구 R2.3)를 긋는다.

시각은 요청마다 한 번 :data:`clock` 으로 정해 도구에 넘긴다 (hub_spec §1-7).
"""

from __future__ import annotations

import contextlib
import json
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

from workflow_kit import __version__ as KIT_VERSION
from workflow_kit.hub import CONTRACT
from workflow_kit.hub import tools as hubtools
from workflow_kit.hub.errors import HubError
from workflow_kit.hub.store import Ctx, Principal, Store

#: 요청 본문 상한 (요구 R13.5).
MAX_BODY = 256 * 1024
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
    return {"X-Hub-Kit": KIT_VERSION, "X-Hub-Contract": CONTRACT, "X-Hub-Db": str(store.db_version())}


def build_app(store: Store, *, public_url: str, exposure: str = "loopback", clock: Clock = utc_now,
              web_token_name: str | None = None) -> Starlette:
    """허브 앱. ``exposure`` 는 healthz 에 싣는 노출 상태 (요구 R13.3).

    ``web_token_name`` 은 화면 공용 ``web`` 토큰의 이름 — 주면 토큰 없는 화면 요청이 그 권한으로 돈다 (R13.2a, 기본 꺼짐).
    """
    server: Server[Any, Any] = Server("workflow-hub", version=KIT_VERSION)

    def principal_from_mcp() -> tuple[Principal | None, bool]:
        req = server.request_context.request
        token = _bearer(req.headers) if req is not None else None
        client = req.headers.get("x-hub-client") if req is not None else None
        principal = store.authenticate(token, clock(), client) if token else None
        return principal, token is not None

    @server.list_tools()  # type: ignore[no-untyped-call, untyped-decorator]
    async def _list_tools() -> list[mtypes.Tool]:
        principal, _ = await run_in_threadpool(principal_from_mcp)
        authed = principal is not None and principal.kind == "callsign"
        return [
            mtypes.Tool(name=t.name, description=t.description, inputSchema=t.schema())
            for t in hubtools.visible_tools(authed)
        ]

    @server.call_tool(validate_input=False)  # type: ignore[untyped-decorator]
    async def _call_tool(name: str, arguments: dict[str, Any]) -> mtypes.CallToolResult:
        def run() -> dict[str, Any]:
            principal, sent = principal_from_mcp()
            spec = hubtools.TOOLS.get(name)
            if sent and principal is None and spec is not None and spec.bundle != "bootstrap":
                raise HubError(401, "unauthorized", "토큰이 틀렸거나 거둔 토큰이다")
            ctx = Ctx(now=clock(), via="mcp", principal=principal, public_url=public_url)
            return hubtools.call(store, name, arguments or {}, ctx)

        try:
            result = await run_in_threadpool(run)
            return mtypes.CallToolResult(
                content=[mtypes.TextContent(type="text", text=json.dumps(result, ensure_ascii=False))],
                structuredContent=result,
            )
        except HubError as e:
            payload = e.payload()
            return mtypes.CallToolResult(
                content=[mtypes.TextContent(type="text", text=json.dumps(payload, ensure_ascii=False))],
                structuredContent=payload,
                isError=True,
            )

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

    async def hub_client_source(request: Request) -> Response:
        # 선택 클라이언트 원문 (hub_spec §7) — 토큰 없이 받는다: 비밀이 없고, 토큰은 .workflow-hub/env 에서 읽는다.
        src = (Path(__file__).resolve().parent / "client" / "hub_client.py").read_text(encoding="utf-8")
        return Response(src, media_type="text/x-python; charset=utf-8")

    async def healthz(request: Request) -> Response:
        return JSONResponse(
            {"ok": True, "kit_version": KIT_VERSION, "contract": CONTRACT, "db_version": store.db_version(),
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

            result = await run_in_threadpool(run)
            return JSONResponse(result, headers=headers)
        except HubError as e:
            return JSONResponse(e.payload(), status_code=e.status, headers=headers)

    @contextlib.asynccontextmanager
    async def lifespan(_app: Starlette) -> AsyncIterator[None]:
        async with manager.run():
            yield

    from workflow_kit.hub.ui import build_routes

    ui_routes = build_routes(store, clock=clock, web_token_name=web_token_name,
                             hub_headers=lambda: _hub_headers(store), max_body=MAX_BODY)

    return Starlette(
        routes=[
            *ui_routes,
            Route("/", guide_page, methods=["GET"]),
            Route("/healthz", healthz, methods=["GET"]),
            Route("/v1/bootstrap/hub_client.py", hub_client_source, methods=["GET"]),
            Route("/v1/tools/{name}", tool_http, methods=["POST"]),
            Route("/mcp", _McpEndpoint(), methods=["GET", "POST", "DELETE"]),
        ],
        lifespan=lifespan,
    )
