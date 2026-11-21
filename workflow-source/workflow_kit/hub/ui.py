"""허브 화면 — ``/ui/`` 정적 화면 · ``/api/…`` JSON (hub_spec §4.6 · §4.7, M-037 WBS-37.1).

인증은 요구 R13.2a (arcturus 과제 대시보드 방식): 로그인이 없고, 브라우저 저장소의 콜사인 토큰을
``Authorization: Bearer`` 로 싣는다. 토큰 없는 요청은 ``hub serve --web-token-name`` 이 켠 화면 공용
``web`` 토큰의 권한(읽기 · 콜사인 등록)으로만 돈다 — 기본 꺼짐이면 401.

읽기는 권한을 확인한 뒤 한 프로젝트로 좁힌 ``viewer`` 주체로 store 의 읽기 함수를 부른다
(:meth:`Store._need_reader`). 쓰기(결정 답)는 그 프로젝트의 콜사인 토큰이어야 하고, 판정은 도구와
같은 함수(:meth:`Judge.plan_respond`)다 — 화면은 응답 본문(response/1)을 응답자 = 그 콜사인으로 만들 뿐이다.

정적 자산은 데이터가 없어 인증 없이 내린다. 화면 응답은 인라인 스크립트를 막는 CSP 를 싣고,
링크 · API 호출은 상대 경로다 (R13.4 — 접두사 프록시 뒤에서 그대로 돈다).
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Awaitable, Callable

from starlette.concurrency import run_in_threadpool
from starlette.requests import Request
from starlette.responses import FileResponse, JSONResponse, RedirectResponse, Response
from starlette.routing import BaseRoute, Route

from workflow_kit.common import plan_claims, plan_responses
from workflow_kit.hub.errors import HubError, forbidden, invalid_field, not_found, unauthorized
from workflow_kit.hub.judge import Judge, task_lines
from workflow_kit.hub.store import Ctx, Principal, Store

STATIC_DIR = Path(__file__).resolve().parent / "static"

#: 화면 응답 머리 (hub_spec §4.6) — 인라인 스크립트 · 외부 스크립트 · 다른 출처 fetch 를 막는다.
SCREEN_HEADERS = {
    "Content-Security-Policy": (
        "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self'; "
        "object-src 'none'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'"
    ),
    "Referrer-Policy": "same-origin",
    "X-Content-Type-Options": "nosniff",
}

_STATIC = {
    "": ("index.html", "text/html; charset=utf-8"),
    "hub.js": ("hub.js", "text/javascript; charset=utf-8"),
    "hub.css": ("hub.css", "text/css; charset=utf-8"),
    "favicon.svg": ("favicon.svg", "image/svg+xml"),
}

#: 응답 본문의 ``client`` 칸 — 이 응답이 화면에서 왔다는 표식.
CLIENT_TAG = "hub-ui"


def _bearer(request: Request) -> str | None:
    raw = request.headers.get("authorization") or ""
    if raw.lower().startswith("bearer "):
        return raw[7:].strip() or None
    return None


def _principal_summary(p: Principal) -> dict[str, Any]:
    return {"kind": p.kind, "project_id": p.project_id, "callsign": p.callsign, "callsign_kind": p.callsign_kind,
            "human_approved": p.human_approved, "role": p.role, "name": p.name,
            "can_answer": p.kind == "callsign" and p.callsign_kind == "human" and p.human_approved}


def _decision(d: plan_claims.Decision, state: str | None) -> dict[str, Any]:
    return {"id": d.id, "claim_id": d.claim_id, "question": d.question, "default": d.default,
            "options": [list(o) for o in d.options], "state": state or d.state, "problems": list(d.problems)}


def build_routes(store: Store, *, clock: Callable[[], datetime], web_token_name: str | None,
                 hub_headers: Callable[[], dict[str, str]], max_body: int) -> list[BaseRoute]:
    judge = Judge(store)

    def resolve(request: Request, now: datetime) -> Principal:
        token = _bearer(request)
        if token:
            p = store.authenticate(token, now)
            if p is None:
                raise unauthorized("토큰이 틀렸거나 거둔 토큰이다 — 이 브라우저에서 지운 뒤 다시 등록한다")
            return p
        if web_token_name:
            p = store.web_principal(web_token_name)
            if p is not None:
                return p
        raise unauthorized("토큰이 없다 — 화면 공용 토큰이 꺼져 있다. 콜사인 토큰을 넣는다")

    def scope(p: Principal, project_id: str) -> Principal:
        """프로젝트 하나로 좁힌 읽기 주체. 콜사인 토큰은 자기 프로젝트만 (R4.6 의 범위)."""
        if p.kind == "callsign" and p.project_id != project_id:
            raise forbidden("이 토큰의 프로젝트가 아니다")
        if not store.projects(project_id):
            raise not_found(f"프로젝트가 없다: {project_id}")
        return Principal(kind="viewer", project_id=project_id, callsign=p.callsign, callsign_kind=p.callsign_kind,
                         human_approved=p.human_approved, role=p.role, name=p.name)

    def api(handler: Callable[[Request, Principal, datetime, Any], dict[str, Any]], *, body: bool = False
            ) -> Callable[[Request], Awaitable[Response]]:
        async def endpoint(request: Request) -> Response:
            headers = {**hub_headers(), **SCREEN_HEADERS, "Cache-Control": "no-store"}
            try:
                payload: Any = None
                if body:
                    # 다른 출처의 폼은 application/json 을 보낼 수 없다 (text/plain 본문으로 JSON 을 흉내 내도) —
                    # 공용 web 토큰이 켜진 허브에서 머리 없는 위조 POST 가 콜사인을 등록하지 못하게.
                    ctype = (request.headers.get("content-type") or "").split(";", 1)[0].strip().lower()
                    if ctype != "application/json":
                        raise HubError(415, "unsupported_media_type", "본문은 application/json 이어야 한다")
                    raw = await request.body()
                    if len(raw) > max_body:
                        raise HubError(413, "payload_too_large", f"본문 상한 {max_body} 바이트")
                    try:
                        payload = json.loads(raw.decode("utf-8")) if raw.strip() else {}
                    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                        raise HubError(400, "invalid_json", f"본문이 JSON 이 아니다: {exc}") from exc
                    if not isinstance(payload, dict):
                        raise HubError(400, "invalid_json", "본문은 JSON 객체다")
                now = clock()

                def run() -> dict[str, Any]:
                    return handler(request, resolve(request, now), now, payload)

                return JSONResponse(await run_in_threadpool(run), headers=headers)
            except HubError as e:
                return JSONResponse(e.payload(), status_code=e.status, headers=headers)

        return endpoint

    # --- 읽기 ---------------------------------------------------------------------

    def get_session(request: Request, p: Principal, now: datetime, _b: Any) -> dict[str, Any]:
        return {"principal": _principal_summary(p), "web_token": bool(web_token_name)}

    def get_projects(request: Request, p: Principal, now: datetime, _b: Any) -> dict[str, Any]:
        rows = store.projects(p.project_id if p.kind == "callsign" else None)
        return {"projects": rows, "principal": _principal_summary(p)}

    def get_project(request: Request, p: Principal, now: datetime, _b: Any) -> dict[str, Any]:
        pid = request.path_params["pid"]
        scope(p, pid)
        project = store.projects(pid)[0]
        me = _principal_summary(p)
        me["can_answer"] = me["can_answer"] and p.project_id == pid
        return {"project": project, "principal": me}

    def get_tasks(request: Request, p: Principal, now: datetime, _b: Any) -> dict[str, Any]:
        v = scope(p, request.path_params["pid"])
        q = request.query_params
        assignee = q.get("assignee")
        return store.task_list(Ctx(now=now, via="ui", principal=v), q.get("status") or None, assignee,
                               int(q.get("limit") or 200))

    def get_task(request: Request, p: Principal, now: datetime, _b: Any) -> dict[str, Any]:
        pid, tid = request.path_params["pid"], request.path_params["tid"]
        v = scope(p, pid)
        ctx = Ctx(now=now, via="ui", principal=v)
        task = store.task_get(ctx, tid)["task"]
        lines, _ = task_lines(task["plan_md"], task["fields"])
        plan = plan_claims.parse_plan(lines)
        status = judge.plan_status(ctx, tid)
        issues = plan_claims.lint_plan(plan)
        events = store.events(ctx, "task", tid, 0, 1000)["events"]
        return {
            "task": task,
            "plan": {
                "digest": status["plan_digest"],
                "claims": [{"id": c.id, "text": c.text} for c in plan.claims],
                "decisions": [_decision(d, status["states"].get(d.id)) for d in plan.decisions],
                "open_decisions": status["open_decisions"],
                "responses": status["responses"],
                "has_errors": plan_claims.has_error_rules(plan),
                "lint": [{"rule": i.rule, "severity": i.severity, "message": i.message, "ref": i.ref} for i in issues],
            },
            "events": events,
        }

    def get_events(request: Request, p: Principal, now: datetime, _b: Any) -> dict[str, Any]:
        v = scope(p, request.path_params["pid"])
        q = request.query_params
        return store.events(Ctx(now=now, via="ui", principal=v), q.get("target_kind") or None,
                            q.get("target_id") or None, int(q.get("after_seq") or 0), int(q.get("limit") or 200))

    # --- 쓰기 ---------------------------------------------------------------------

    def post_callsign(request: Request, p: Principal, now: datetime, b: dict[str, Any]) -> dict[str, Any]:
        """콜사인 등록 (R13.2a) — web · 콜사인 토큰 · admin 이 부를 수 있다. 토큰은 이 응답에서 한 번만."""
        pid = request.path_params["pid"]
        scope(p, pid)
        for key in ("callsign", "kind", "label"):
            if key in b and not isinstance(b[key], str):
                raise invalid_field(key, "문자열이어야 한다")
        return store.register_callsign(Ctx(now=now, via="ui", principal=p), pid, b.get("callsign", ""),
                                       b.get("kind", ""), b.get("label", ""), "browser")

    def post_response(request: Request, p: Principal, now: datetime, b: dict[str, Any]) -> dict[str, Any]:
        """결정 답 — 폼 값으로 response/1 본문을 만들어 :meth:`Judge.plan_respond` 에 넘긴다."""
        pid, tid = request.path_params["pid"], request.path_params["tid"]
        if p.kind != "callsign":
            raise forbidden("결정 답은 콜사인 토큰으로만 쓴다 (화면 공용 토큰은 읽기 · 등록만)")
        if p.project_id != pid:
            raise forbidden("이 토큰의 프로젝트가 아니다")
        ctx = Ctx(now=now, via="ui", principal=p, client_version=CLIENT_TAG)
        task = store.task_get(ctx, tid)["task"]
        plan = plan_claims.parse_plan(task_lines(task["plan_md"], task["fields"])[0])
        if b.get("plan_digest") != plan_claims.plan_digest(plan):
            raise HubError(409, "version_conflict", "계획이 바뀌었다 — 다시 열어라",
                           {"current_digest": plan_claims.plan_digest(plan)})
        values_in, opened_in, comments_in = b.get("values") or {}, b.get("opened") or {}, b.get("comments") or {}
        if not all(isinstance(x, dict) for x in (values_in, opened_in, comments_in)):
            raise invalid_field("values", "values · opened · comments 는 객체다")
        open_ids = set(judge.plan_status(ctx, tid)["open_decisions"])
        values: dict[str, str] = {}
        opened: dict[str, bool] = {}
        for d in plan.decisions:
            if d.id not in open_ids:
                values[d.id], opened[d.id] = d.default, False
                continue
            value = values_in.get(d.id)
            if not isinstance(value, str) or value not in d.option_values:
                raise invalid_field(f"values.{d.id}", "선택지 가운데 하나")
            values[d.id], opened[d.id] = value, opened_in.get(d.id) is True
        targets = {"-", *(c.id for c in plan.claims), *(d.id for d in plan.decisions)}
        comments: list[tuple[str, str]] = []
        for target in sorted(comments_in):
            text = comments_in[target]
            if not isinstance(text, str):
                raise invalid_field(f"comments.{target}", "문자열")
            text = text.replace("\r\n", "\n").replace("\r", "\n")
            if not text.strip():
                continue
            if target not in targets:
                raise invalid_field(f"comments.{target}", "계획에 없는 대상")
            if any((ord(ch) < 0x20 and ch not in "\n\t") or ord(ch) == 0x7F for ch in text):
                raise invalid_field(f"comments.{target}", "제어 문자")
            comments.append((target, text))
        received = _received_at(store, pid, tid, p.callsign or "")
        body_text = plan_responses.render_response(
            task_id=tid, plan=plan, responder=p.callsign or "", received_at=received,
            values=values, opened=opened, comments=comments, client=CLIENT_TAG)
        return judge.plan_respond(ctx, tid, body_text)

    async def static(request: Request) -> Response:
        name = request.path_params.get("name", "")
        if name not in _STATIC:
            return JSONResponse({"error_code": "not_found", "message": "없는 자산", "detail": {}}, status_code=404)
        file, media = _STATIC[name]
        return FileResponse(STATIC_DIR / file, media_type=media, headers={**SCREEN_HEADERS, "Cache-Control": "no-cache"})

    async def ui_redirect(request: Request) -> Response:
        # 상대 리다이렉트 — 접두사 프록시 뒤에서도 그 접두사의 ui/ 로 간다 (R13.4).
        return RedirectResponse("ui/", status_code=307)

    return [
        Route("/ui", ui_redirect, methods=["GET"]),
        Route("/ui/", static, methods=["GET"]),
        Route("/ui/{name}", static, methods=["GET"]),
        Route("/api/session", api(get_session), methods=["GET"]),
        Route("/api/projects", api(get_projects), methods=["GET"]),
        Route("/api/projects/{pid}", api(get_project), methods=["GET"]),
        Route("/api/projects/{pid}/tasks", api(get_tasks), methods=["GET"]),
        Route("/api/projects/{pid}/tasks/{tid}", api(get_task), methods=["GET"]),
        Route("/api/projects/{pid}/events", api(get_events), methods=["GET"]),
        Route("/api/projects/{pid}/callsigns", api(post_callsign, body=True), methods=["POST"]),
        Route("/api/projects/{pid}/tasks/{tid}/responses", api(post_response, body=True), methods=["POST"]),
    ]


def _received_at(store: Store, project_id: str, task_id: str, responder: str) -> str:
    """응답 시각 — 같은 응답자의 앞선 응답보다 늦게 (워크벤치 respond §6-6 과 같은 단조 규칙)."""
    moment = datetime.now(timezone.utc).astimezone()
    with store.read() as conn:
        rows = conn.execute(
            "SELECT received_at FROM plan_response WHERE project_id = ? AND task_id = ? AND responder = ?",
            (project_id, task_id, responder)).fetchall()
    latest = max((m for m in (plan_responses.received_micros(r["received_at"]) for r in rows) if m is not None),
                 default=None)
    current = plan_responses.received_micros(moment.isoformat(timespec="microseconds"))
    if latest is not None and current is not None and current <= latest:
        epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
        moment = (epoch + timedelta(microseconds=latest + 1)).astimezone(moment.tzinfo)
    return moment.isoformat(timespec="microseconds")
