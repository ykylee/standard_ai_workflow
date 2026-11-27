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
from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlsplit
from typing import Any

from starlette.concurrency import run_in_threadpool
from starlette.requests import Request
from starlette.responses import FileResponse, JSONResponse, RedirectResponse, Response
from starlette.routing import BaseRoute, Route

from workflow_kit.common import plan_claims, plan_responses
from workflow_kit.common.schemas.roadmap import RoadmapIssue, TaskWbsLink
from workflow_kit.common.state import roadmap as rm
from workflow_kit.hub.errors import HubError, forbidden, invalid_field, not_found, unauthorized
from workflow_kit.hub.account_auth import HubAccounts
from workflow_kit.hub.confirmations import Confirmations
from workflow_kit.hub.guide import Guides
from workflow_kit.hub.harness_intake import HarnessIntake
from workflow_kit.hub.ideas import Ideas
from workflow_kit.hub.judge import _NO_TREE, INDEX, Judge, task_lines
from workflow_kit.hub.knowledge import Knowledge
from workflow_kit.hub.memory import Memory
from workflow_kit.hub.orchestration import Orchestration
from workflow_kit.hub.relay import Relays
from workflow_kit.hub.store import Ctx, Principal, Store
from workflow_kit.hub.wiki import Wiki

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


def screen_origin(request: Request, public_url: str) -> tuple[bool, str] | None:
    """브라우저 요청의 출처가 맞으면 (쿠키 Secure, 쿠키 Path), 아니면 None.

    설정한 공개 주소이거나 요청이 온 호스트다. 리버스 프록시는 Host 를 바꾸고 X-Forwarded-Proto 를 빠뜨릴 수 있어
    공개 주소는 머리가 아니라 설정과 견준다. 자기 Origin 의 scheme 을 바꾸는 프록시(https → http)는 브라우저가 붙이고 페이지가
    위조할 수 없는 ``Sec-Fetch-Site: same-origin`` 이 함께 있을 때만 받는다. 하위 경로면 쿠키를 그 경로로 좁힌다 — 같은 호스트의 다른 앱에 보내지 않는다.
    """
    origin = request.headers.get("origin", "").rstrip("/")
    if not origin:
        return None
    u = urlsplit(public_url)
    rewritten = (u.scheme == "https" and origin.lower() == f"http://{u.netloc}".lower()
                 and request.headers.get("sec-fetch-site") == "same-origin")
    if u.netloc and (origin.lower() == f"{u.scheme}://{u.netloc}".lower() or rewritten):
        return u.scheme == "https", u.path.rstrip("/") or "/"
    scheme = request.headers.get("x-forwarded-proto", "").split(",", 1)[0].strip() or request.url.scheme
    if origin != f"{scheme}://{request.headers.get('host', '')}":
        return None
    return scheme == "https", "/"


def _principal_summary(p: Principal) -> dict[str, Any]:
    is_owner = p.kind == "callsign" and p.callsign_kind == "human" and p.human_approved and p.role == "owner"
    return {"kind": p.kind, "project_id": p.project_id, "callsign": p.callsign, "callsign_kind": p.callsign_kind,
            "human_approved": p.human_approved, "role": p.role, "name": p.name,
            "can_answer": p.kind == "callsign" and p.callsign_kind == "human" and p.human_approved,
            "can_manage": is_owner}


def _decision(d: plan_claims.Decision, state: str | None) -> dict[str, Any]:
    return {"id": d.id, "claim_id": d.claim_id, "question": d.question, "default": d.default,
            "options": [list(o) for o in d.options], "state": state or d.state, "problems": list(d.problems)}


def build_routes(store: Store, *, clock: Callable[[], datetime], web_token_name: str | None,
                 hub_headers: Callable[[], dict[str, str]], max_body: int, public_url: str = "") -> list[BaseRoute]:
    judge = Judge(store)
    memory = Memory(store)
    guides = Guides(store)
    wiki = Wiki(store)
    knowledge = Knowledge(store)
    orch = Orchestration(store)
    relays = Relays(store)
    harness_intake = HarnessIntake(store)
    accounts = HubAccounts(store)

    async def account_endpoint(request: Request) -> Response:
        headers = {**hub_headers(), **SCREEN_HEADERS, "Cache-Control": "no-store"}
        try:
            if request.method != "POST":
                raise HubError(405, "method_not_allowed", "POST 만 지원해요")
            allowed = screen_origin(request, public_url)
            if allowed is None:
                raise HubError(403, "origin_mismatch", "같은 출처의 브라우저 요청만 허용해요")
            ctype = (request.headers.get("content-type") or "").split(";", 1)[0].strip().lower()
            if ctype != "application/json":
                raise HubError(415, "unsupported_media_type", "본문은 application/json 이어야 해요")
            raw = await request.body()
            if len(raw) > max_body:
                raise HubError(413, "payload_too_large", f"본문 상한 {max_body} 바이트")
            payload = json.loads(raw.decode("utf-8")) if raw.strip() else {}
            if not isinstance(payload, dict):
                raise HubError(400, "invalid_json", "본문은 JSON 객체예요")
            now = clock()
            action = request.path_params["action"]
            cookie = request.cookies.get("workflow_hub_session")
            if action == "login":
                session, account = accounts.login(payload.get("username", ""), payload.get("password", ""), now)
            elif action == "enroll":
                session, account = accounts.enroll(_bearer(request) or "", payload.get("username", ""),
                                                    payload.get("display_name", ""), payload.get("password", ""), now)
            elif action == "link":
                linked_account = accounts.account(cookie, now)
                if not linked_account:
                    raise unauthorized("허브 계정에 로그인해야 콜사인을 연결할 수 있어요")
                linked = accounts.link(linked_account["id"], _bearer(request) or "", now)
                return JSONResponse({"account": linked_account, "linked": linked}, headers=headers)
            elif action == "join":
                joiner = accounts.account(cookie, now)
                if not joiner:
                    raise unauthorized("허브 계정에 로그인해야 프로젝트에 참여할 수 있어요")
                joined = accounts.join(joiner["id"], payload.get("project", ""), payload.get("callsign", ""), now)
                return JSONResponse({"account": joiner, "joined": joined}, headers=headers)
            elif action == "logout":
                accounts.logout(cookie, now)
                session, account = "", None
            else:
                raise HubError(404, "not_found", "계정 API 경로가 없어요")
            response = JSONResponse({"account": account}, headers=headers)
            secure, cookie_path = allowed
            if session:
                response.set_cookie("workflow_hub_session", session, max_age=30 * 24 * 3600, path=cookie_path,
                                    httponly=True, secure=secure, samesite="strict")
            else:
                response.delete_cookie("workflow_hub_session", path=cookie_path, httponly=True, secure=secure, samesite="strict")
            return response
        except HubError as exc:
            return JSONResponse(exc.payload(), status_code=exc.status, headers=headers)
        except (UnicodeDecodeError, json.JSONDecodeError):
            return JSONResponse(HubError(400, "invalid_json", "본문이 올바른 JSON이 아니에요").payload(), status_code=400, headers=headers)

    def resolve(request: Request, now: datetime) -> Principal:
        token = _bearer(request)
        if token:
            p = store.authenticate(token, now)
            if p is None:
                raise unauthorized("토큰이 틀렸거나 거둔 토큰이에요 — 이 브라우저에서 지운 뒤 다시 등록해요")
            return p
        account = accounts.account(request.cookies.get("workflow_hub_session"), now)
        if account:
            # 관리자 계정 = admin 토큰과 같은 권한. 프로젝트 화면은 연결된 사람 콜사인을 먼저 쓴다 (승인 · 응답은 콜사인의 일).
            admin = Principal(kind="admin", name=account["display_name"], auth_mode="account",
                              account_name=account["username"]) if account["is_admin"] else None
            pid = request.path_params.get("pid")
            if pid:
                linked = accounts.callsign(account["id"], pid, now)
                if linked:
                    return linked
                if admin:
                    return admin
                raise forbidden("이 허브 계정에 해당 프로젝트의 사람 콜사인이 연결되어 있지 않아요")
            return admin or Principal(kind="account", name=account["display_name"])
        if web_token_name:
            p = store.web_principal(web_token_name)
            if p is not None:
                return p
        raise unauthorized("토큰이 없어요 — 화면 공용 토큰이 꺼져 있어요. 콜사인 토큰을 넣어요")

    def scope(p: Principal, project_id: str) -> Principal:
        """프로젝트 하나로 좁힌 읽기 주체. 콜사인 토큰은 자기 프로젝트만 (R4.6 의 범위)."""
        if p.kind == "callsign" and p.project_id != project_id:
            raise forbidden("이 토큰의 프로젝트가 아니에요")
        if not store.projects(project_id):
            raise not_found(f"프로젝트가 없어요: {project_id}")
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
                        raise HubError(415, "unsupported_media_type", "본문은 application/json 이어야 해요")
                    raw = await request.body()
                    if len(raw) > max_body:
                        raise HubError(413, "payload_too_large", f"본문 상한 {max_body} 바이트")
                    try:
                        payload = json.loads(raw.decode("utf-8")) if raw.strip() else {}
                    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                        raise HubError(400, "invalid_json", f"본문이 JSON 이 아니에요: {exc}") from exc
                    if not isinstance(payload, dict):
                        raise HubError(400, "invalid_json", "본문은 JSON 객체예요")
                    if request.cookies.get("workflow_hub_session") and not _bearer(request):
                        if screen_origin(request, public_url) is None:
                            raise HubError(403, "origin_mismatch", "같은 출처의 브라우저 요청만 허용해요")
                now = clock()

                def run() -> dict[str, Any]:
                    principal = resolve(request, now)
                    pid = request.path_params.get("pid") or principal.project_id
                    to = store.project_moved(pid)
                    if to:  # 봉인된 프로젝트 — 화면도 410 + 새 주소 (M-039 WBS-39.4)
                        from workflow_kit.hub.transfer import moved_error  # noqa: PLC0415

                        raise moved_error(str(pid), to)
                    return handler(request, principal, now, payload)

                return JSONResponse(await run_in_threadpool(run), headers=headers)
            except HubError as e:
                return JSONResponse(e.payload(), status_code=e.status, headers=headers)

        return endpoint

    # --- 읽기 ---------------------------------------------------------------------

    def get_session(request: Request, p: Principal, now: datetime, _b: Any) -> dict[str, Any]:
        account = accounts.account(request.cookies.get("workflow_hub_session"), now)
        return {"principal": _principal_summary(p), "account": account, "web_token": bool(web_token_name)}

    def get_projects(request: Request, p: Principal, now: datetime, _b: Any) -> dict[str, Any]:
        account = accounts.account(request.cookies.get("workflow_hub_session"), now)
        if account and p.kind == "admin" and p.auth_mode == "account":
            return {"projects": store.projects(None), "principal": _principal_summary(p), "account": account}
        if account:
            rows = [project for pid in accounts.projects(account["id"]) for project in store.projects(pid)]
            return {"projects": rows, "principal": {"kind": "account", "name": account["display_name"]}, "account": account}
        rows = store.projects(p.project_id if p.kind == "callsign" else None)
        return {"projects": rows, "principal": _principal_summary(p)}

    def _admin_only(p: Principal) -> None:
        if p.kind != "admin":
            raise forbidden("허브 관리자(admin 토큰 또는 관리자 계정)만 할 수 있어요")

    def _actor(p: Principal) -> str:
        return f"account:{p.account_name}" if p.auth_mode == "account" else f"admin:{p.name}"

    def get_accounts(request: Request, p: Principal, now: datetime, _b: Any) -> dict[str, Any]:
        _admin_only(p)
        return {"accounts": accounts.list_accounts()}

    def post_account_admin(request: Request, p: Principal, now: datetime, b: dict[str, Any]) -> dict[str, Any]:
        _admin_only(p)
        return accounts.set_admin(request.path_params["username"], b.get("admin"), now, _actor(p))

    def get_harness_reports(request: Request, p: Principal, now: datetime, _b: Any) -> dict[str, Any]:
        _admin_only(p)
        return harness_intake.list_reports(Ctx(now=now, via="ui", principal=p), request.query_params.get("status", "pending"))

    def post_harness_decision(request: Request, p: Principal, now: datetime, b: dict[str, Any]) -> dict[str, Any]:
        _admin_only(p)
        return harness_intake.decide(Ctx(now=now, via="ui", principal=p), request.path_params["rid"],
                                    b.get("decision", ""), b.get("note", ""), b.get("owner_ids"),
                                    b.get("setup_profile"))

    def get_harness_people(request: Request, p: Principal, now: datetime, _b: Any) -> dict[str, Any]:
        _admin_only(p)
        return harness_intake.list_people(Ctx(now=now, via="ui", principal=p))

    def get_harness_registry(request: Request, p: Principal, now: datetime, _b: Any) -> dict[str, Any]:
        _admin_only(p)
        return harness_intake.registry_list(Ctx(now=now, via="ui", principal=p), include_inactive=True)

    def post_harness_people(request: Request, p: Principal, now: datetime, b: dict[str, Any]) -> dict[str, Any]:
        _admin_only(p)
        return harness_intake.create_person(Ctx(now=now, via="ui", principal=p), b.get("display_name", ""))

    def _project_summary(pid: str, v: Principal, now: datetime) -> dict[str, Any]:
        ctx = Ctx(now=now, via="ui", principal=v)
        with store.write() as conn:
            orch._expire(conn, ctx, pid)
        s_out = orch.session_list(ctx, {})
        with store.read() as conn:
            pending_approvals = int(conn.execute(
                "SELECT COUNT(*) FROM session_request WHERE project_id = ? AND state = 'pending_approval'",
                (pid,),
            ).fetchone()[0])
            unacknowledged = int(conn.execute(
                "SELECT COUNT(*) FROM inbox_message WHERE project_id = ? AND state = 'unacknowledged'",
                (pid,),
            ).fetchone()[0])
            open_assignments = int(conn.execute(
                "SELECT COUNT(*) FROM assignment WHERE project_id = ? AND state IN ('offered', 'accepted')",
                (pid,),
            ).fetchone()[0])
            # 사람이 아직 안 본 아이디어 회신 (I2a)
            ideas_unread = int(conn.execute(
                "SELECT COUNT(*) FROM idea_entry e JOIN idea i ON i.project_id=e.project_id AND i.id=e.idea_id WHERE e.project_id=? AND e.kind='reply' AND e.seq>i.seen_seq",
                (pid,),
            ).fetchone()[0])
            plan_task_ids = [
                r["id"]
                for r in conn.execute(
                    "SELECT id FROM task WHERE project_id = ? AND status != 'done' AND plan_md != '' ORDER BY id",
                    (pid,),
                ).fetchall()
            ]
        # 화면이 '사람이 결정할 일' 에서 그 task 로 바로 보낸다 — 수만 주면 어느 task 인지 다시 찾아야 한다.
        open_decision_task_ids = [tid for tid in plan_task_ids if judge.plan_status(ctx, tid)["open_decisions"]]
        return {
            "open_decision_tasks": len(open_decision_task_ids),
            "open_decision_task_ids": open_decision_task_ids,
            "pending_approvals": pending_approvals,
            "unacknowledged": unacknowledged,
            "open_assignments": open_assignments,
            "ideas_unread": ideas_unread,
            "session_counts": s_out["counts"],
            "unknown_sessions": s_out["unknown"],
            "sessions_total": len(s_out["sessions"]),
            "orchestrator": s_out["orchestrator"],
        }

    def get_project(request: Request, p: Principal, now: datetime, _b: Any) -> dict[str, Any]:
        pid = request.path_params["pid"]
        v = scope(p, pid)
        project = store.projects(pid)[0]
        me = _principal_summary(p)
        me["can_answer"] = me["can_answer"] and p.project_id == pid
        me["can_manage"] = me["can_manage"] and p.project_id == pid
        account = accounts.account(request.cookies.get("workflow_hub_session"), now)
        if account:
            me["auth_mode"] = "account"
            me["account"] = account
        return {"project": project, "principal": me, "summary": _project_summary(pid, v, now)}

    def get_tasks(request: Request, p: Principal, now: datetime, _b: Any) -> dict[str, Any]:
        v = scope(p, request.path_params["pid"])
        q = request.query_params
        try:
            limit, offset = int(q.get("limit") or 25), int(q.get("offset") or 0)
        except ValueError as exc:
            raise invalid_field("limit", "limit · offset 는 정수여야 해요") from exc
        filters = {key: q.get(key, "") for key in
                   ("status", "roadmap", "milestone", "wbs", "category_level_1", "category_level_2", "category_level_3")}
        return store.task_list_page(Ctx(now=now, via="ui", principal=v), filters, limit=limit, offset=offset)

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

    def get_callsigns(request: Request, p: Principal, now: datetime, _b: Any) -> dict[str, Any]:
        """콜사인 표 — 지금 누가 무엇을 · 마지막 활동 · 받은 지침 판 (WBS-37.2)."""
        scope(p, request.path_params["pid"])
        return store.callsign_board(request.path_params["pid"])

    def get_callsign(request: Request, p: Principal, now: datetime, _b: Any) -> dict[str, Any]:
        """콜사인 하나 — 표의 줄 + handoff (읽기는 프로젝트 안 누구나, G3)."""
        pid, cs = request.path_params["pid"], request.path_params["cs"]
        v = scope(p, pid)
        board = store.callsign_board(pid)
        row = next((c for c in board["callsigns"] if c["id"] == cs), None)
        if row is None:
            raise not_found(f"콜사인이 없어요: {cs}")
        handoff = memory.handoff_get(Ctx(now=now, via="ui", principal=v), cs)
        return {"guide_current": board["guide_current"], "callsign": row, "handoff": handoff}

    def get_guide(request: Request, p: Principal, now: datetime, _b: Any) -> dict[str, Any]:
        """지침 — 지금 판 · 판 이력 · 제안과 diff (WBS-37.3)."""
        pid = request.path_params["pid"]
        out = guides.get(Ctx(now=now, via="ui", principal=scope(p, pid)))
        me = _principal_summary(p)
        out["can_decide"] = me["can_answer"] and p.project_id == pid
        out["can_propose"] = p.kind == "callsign" and p.project_id == pid
        return out

    def get_wiki(request: Request, p: Principal, now: datetime, _b: Any) -> dict[str, Any]:
        """위키 — ``q`` 가 있으면 검색, 아니면 목록 (``prefix``)."""
        ctx = Ctx(now=now, via="ui", principal=scope(p, request.path_params["pid"]))
        q = request.query_params
        if (q.get("q") or "").strip():
            return knowledge.search(ctx, q["q"], int(q.get("limit") or 50))
        return wiki.list_pages(ctx, q.get("prefix") or "")

    def get_knowledge_ref(request: Request, p: Principal, now: datetime, _b: Any) -> dict[str, Any]:
        ref = request.query_params.get("ref") or ""
        if not ref:
            raise invalid_field("ref", "필수")
        return knowledge.get(Ctx(now=now, via="ui", principal=scope(p, request.path_params["pid"])), ref)

    def get_dcrs(request: Request, p: Principal, now: datetime, _b: Any) -> dict[str, Any]:
        return knowledge.dcr_list(Ctx(now=now, via="ui", principal=scope(p, request.path_params["pid"])), request.query_params.get("status"))

    def get_dcr(request: Request, p: Principal, now: datetime, _b: Any) -> dict[str, Any]:
        return knowledge.dcr_get(Ctx(now=now, via="ui", principal=scope(p, request.path_params["pid"])), request.path_params["did"])

    def get_wiki_page(request: Request, p: Principal, now: datetime, _b: Any) -> dict[str, Any]:
        path = request.query_params.get("path") or ""
        if not path:
            raise invalid_field("path", "필수")
        return wiki.get(Ctx(now=now, via="ui", principal=scope(p, request.path_params["pid"])), path)

    def get_roadmap(request: Request, p: Principal, now: datetime, _b: Any) -> dict[str, Any]:
        """로드맵 파생 상태 — 마일스톤 · WBS · 연결 task (viewer 도 읽기 가능)."""
        pid = request.path_params["pid"]
        scope(p, pid)
        with store.read() as conn:
            roadmap, _, issues = judge.roadmap(conn, pid)
            if roadmap is None:
                return {"roadmap_state": None, "reason": "로드맵이 없다 (index.md 없음)"}
            links = [
                TaskWbsLink(
                    task_id=r["id"], task_status=r["status"], wbs_ref=r["wbs"],
                    exempt_reason=r["wbs_exempt_reason"], source_path=r["id"],
                )
                for r in conn.execute(
                    "SELECT id, status, wbs, wbs_exempt_reason FROM task WHERE project_id = ? AND wbs != ''",
                    (pid,),
                )
            ]
        declared = sorted({d for m in roadmap.milestones for d in m.deliverables})
        if declared:
            issues.append(RoadmapIssue(
                code="deliverables_unmeasured",
                detail=f"허브는 저장소를 보지 않아 산출물 {len(declared)}개의 존재를 재지 않았다 — 미측정",
                where=INDEX,
            ))
        state = rm.derive_state(
            roadmap, links, _NO_TREE, issues, deliverable_exists=lambda _d: True,
            generated_at=now.strftime("%Y-%m-%d"),
        )
        return {"roadmap_state": state.model_dump(mode="json")}

    def get_orchestration(request: Request, p: Principal, now: datetime, _b: Any) -> dict[str, Any]:
        """2.1 오케스트레이션 현황 — 세션 5상태 · unknown · 배정 · 미전달 · 세션 요청 · 중계 호스트."""
        pid = request.path_params["pid"]
        v = scope(p, pid)
        ctx = Ctx(now=now, via="ui", principal=v)
        with store.write() as conn:
            orch._expire(conn, ctx, pid)
        s_out = orch.session_list(ctx, {"status": request.query_params.get("status") or None})
        with store.read() as conn:
            meta_by_sid = {
                r["id"]: (r["host_id"] or None, r["guide_version"] or None)
                for r in conn.execute("SELECT id, host_id, guide_version FROM session WHERE project_id = ?", (pid,))
            }
            assign_rows = conn.execute(
                "SELECT a.*, t.title AS task_title, t.status AS task_status, t.progress_note, "
                "m.state AS message_state, m.delivered_via, m.delivered_at, m.last_delivered_at, m.delivery_count "
                "FROM assignment a "
                "LEFT JOIN task t ON t.project_id = a.project_id AND t.id = a.task_id "
                "LEFT JOIN inbox_message m ON m.project_id = a.project_id AND m.id = a.message_id "
                "WHERE a.project_id = ? ORDER BY a.offered_at DESC, a.rowid DESC LIMIT 200",
                (pid,),
            ).fetchall()
            unack_rows = conn.execute(
                "SELECT id, to_kind, to_id, kind, ref_task, delivered_via, delivered_at, created_at, body_json "
                "FROM inbox_message WHERE project_id = ? AND state = 'unacknowledged' "
                "ORDER BY created_at DESC, rowid DESC LIMIT 100",
                (pid,),
            ).fetchall()
            req_rows = conn.execute(
                "SELECT * FROM session_request WHERE project_id = ? "
                "ORDER BY created_at DESC, rowid DESC LIMIT 100",
                (pid,),
            ).fetchall()
        sessions = []
        for s in s_out["sessions"]:
            host_id, guide_ver = meta_by_sid.get(s["id"], (None, None))
            sessions.append({**s, "host_id": host_id, "guide_version": guide_ver})
        assignments = [
            {
                "task_id": r["task_id"],
                "task_title": r["task_title"] or "",
                "task_status": r["task_status"] or "",
                "progress_note": r["progress_note"] or "",
                "session_id": r["session_id"],
                "callsign": r["callsign"],
                "message_id": r["message_id"],
                "state": r["state"],
                "return_reason": r["return_reason"],
                "offered_at": r["offered_at"],
                "accepted_at": r["accepted_at"],
                "reported_at": r["reported_at"],
                "report": json.loads(r["report_json"] or "{}"),
                "message_state": r["message_state"] or None,
                "delivered_via": r["delivered_via"] or None,
                "delivered_at": r["delivered_at"],
                "last_delivered_at": r["last_delivered_at"],
                "delivery_count": int(r["delivery_count"] or 0),
            }
            for r in assign_rows
        ]
        unacknowledged = [
            {
                "id": r["id"],
                "to_kind": r["to_kind"],
                "to_id": r["to_id"],
                "kind": r["kind"],
                "ref_task": r["ref_task"] or None,
                "delivered_via": r["delivered_via"] or None,
                "delivered_at": r["delivered_at"],
                "created_at": r["created_at"],
                "body": json.loads(r["body_json"]),
            }
            for r in unack_rows
        ]
        requests = [
            {
                "id": r["id"],
                "kind": r["kind"],
                "host_id": r["host_id"],
                "target": json.loads(r["target_json"]),
                "requested_by": r["requested_by"],
                "state": r["state"],
                "decided_by": r["decided_by"] or None,
                "decided_at": r["decided_at"],
                "result": json.loads(r["result_json"] or "{}"),
                "created_at": r["created_at"],
            }
            for r in req_rows
        ]
        hosts = relays.list_hosts(ctx, {})["hosts"]
        me = _principal_summary(p)
        me["can_answer"] = me["can_answer"] and p.project_id == pid
        me["can_manage"] = me["can_manage"] and p.project_id == pid
        return {
            "principal": me,
            "orchestrator": s_out["orchestrator"],
            "sessions": sessions,
            "session_counts": s_out["counts"],
            "unknown_sessions": s_out["unknown"],
            "assignments": assignments,
            "unacknowledged": unacknowledged,
            "requests": requests,
            "hosts": hosts,
        }

    def get_confirmations(request: Request, p: Principal, now: datetime, _b: Any) -> dict[str, Any]:
        pid = request.path_params["pid"]
        return Confirmations(store).list_pending(Ctx(now=now, via="ui", principal=_own(p, pid)))

    def get_ideas(request: Request, p: Principal, now: datetime, _b: Any) -> dict[str, Any]:
        return Ideas(store).list_ideas(Ctx(now=now, via="ui", principal=scope(p, request.path_params["pid"])), request.query_params.get("status"))

    def get_idea(request: Request, p: Principal, now: datetime, _b: Any) -> dict[str, Any]:
        return Ideas(store).get(Ctx(now=now, via="ui", principal=scope(p, request.path_params["pid"])), request.path_params["iid"])

    def post_idea(request: Request, p: Principal, now: datetime, b: dict[str, Any]) -> dict[str, Any]:
        ctx = Ctx(now=now, via="ui", principal=_own(p, request.path_params["pid"]))
        return Ideas(store).add(ctx, b.get("body"), b.get("request_id"), web=True)

    def post_idea_action(request: Request, p: Principal, now: datetime, b: dict[str, Any]) -> dict[str, Any]:
        ctx = Ctx(now=now, via="ui", principal=_own(p, request.path_params["pid"]))
        return Ideas(store).act(ctx, request.path_params["iid"], b)

    def post_confirmation_decision(request: Request, p: Principal, now: datetime, b: dict[str, Any]) -> dict[str, Any]:
        pid = request.path_params["pid"]
        note = b.get("note", "")
        if not isinstance(note, str):
            raise invalid_field("note", "문자열")
        decision = b.get("decision")
        if not isinstance(decision, str):
            raise invalid_field("decision", "approve · reject")
        ctx = Ctx(now=now, via="ui", principal=_own(p, pid))
        return Confirmations(store).decide(ctx, request.path_params["rid"], decision, note)

    # --- 쓰기 ---------------------------------------------------------------------

    def _own(p: Principal, pid: str) -> Principal:
        if p.kind != "callsign" or p.project_id != pid:
            raise forbidden("쓰기는 이 프로젝트의 콜사인 토큰으로만 해요 (화면 공용 토큰은 읽기 · 등록만)")
        return p

    def post_guide(request: Request, p: Principal, now: datetime, b: dict[str, Any]) -> dict[str, Any]:
        """지침 변경 — 승인된 human 은 판 +1, 그 밖은 제안 (``hub_guide_propose`` 와 같은 함수)."""
        pid = request.path_params["pid"]
        base = b.get("base_version")
        if not isinstance(base, int) or isinstance(base, bool):
            raise invalid_field("base_version", "정수")
        return guides.propose(Ctx(now=now, via="ui", principal=_own(p, pid)), base, b.get("body", ""), b.get("note", ""))

    def post_decide(request: Request, p: Principal, now: datetime, b: dict[str, Any]) -> dict[str, Any]:
        pid = request.path_params["pid"]
        if not isinstance(b.get("approve"), bool):
            raise invalid_field("approve", "true · false")
        return guides.decide(Ctx(now=now, via="ui", principal=_own(p, pid)), request.path_params["gid"], b["approve"])

    def post_dcr_decision(request: Request, p: Principal, now: datetime, b: dict[str, Any]) -> dict[str, Any]:
        """DCR 승인 · 거절 — ``hub_dcr_decide`` 와 같은 함수 (소유자만, 판단 근거 필수, 낡은 판 409)."""
        pid = request.path_params["pid"]
        version = b.get("expected_version")
        if not isinstance(version, int) or isinstance(version, bool):
            raise invalid_field("expected_version", "정수")
        rationale = b.get("rationale")
        return knowledge.dcr_decide(Ctx(now=now, via="ui", principal=_own(p, pid)), request.path_params["did"], version,
                                    str(b.get("decision") or ""), rationale if isinstance(rationale, str) else "")

    def post_approve(request: Request, p: Principal, now: datetime, _b: Any) -> dict[str, Any]:
        """사람 콜사인 승인 — ``hub_callsign_approve`` 와 같은 함수 (승인된 human 소유자만)."""
        pid = request.path_params["pid"]
        if p.kind != "callsign" or p.project_id != pid:
            raise forbidden("승인은 이 프로젝트의 소유자 콜사인 토큰으로만 해요")
        return store.approve_callsign(Ctx(now=now, via="ui", principal=p), request.path_params["cs"])

    def post_callsign_delete(request: Request, p: Principal, now: datetime, b: dict[str, Any]) -> dict[str, Any]:
        """콜사인 삭제 — 허브 관리자만, 활동 없는 콜사인만. ``confirm`` 은 콜사인 이름."""
        pid = request.path_params["pid"]
        if p.kind != "admin":
            raise forbidden("콜사인 삭제는 허브 관리자만 해요")
        scope(p, pid)
        return store.delete_callsign(Ctx(now=now, via="ui", principal=p), pid, request.path_params["cs"], str(b.get("confirm") or ""))

    def post_callsign(request: Request, p: Principal, now: datetime, b: dict[str, Any]) -> dict[str, Any]:
        """콜사인 등록 (R13.2a) — web · 콜사인 토큰 · admin 이 부를 수 있다. 토큰은 이 응답에서 한 번만."""
        pid = request.path_params["pid"]
        scope(p, pid)
        for key in ("callsign", "kind", "label"):
            if key in b and not isinstance(b[key], str):
                raise invalid_field(key, "문자열이어야 해요")
        return store.register_callsign(Ctx(now=now, via="ui", principal=p), pid, b.get("callsign", ""),
                                       b.get("kind", ""), b.get("label", ""), "browser")

    def post_orch_halt(request: Request, p: Principal, now: datetime, b: dict[str, Any]) -> dict[str, Any]:
        pid = request.path_params["pid"]
        if not isinstance(b.get("on"), bool):
            raise invalid_field("on", "true · false")
        return orch.halt(Ctx(now=now, via="ui", principal=_own(p, pid)), {"on": b["on"]})

    def post_orch_lease(request: Request, p: Principal, now: datetime, b: dict[str, Any]) -> dict[str, Any]:
        pid = request.path_params["pid"]
        ctx = Ctx(now=now, via="ui", principal=_own(p, pid))
        action = b.get("action")
        if action == "declare":
            return orch.declare(ctx, {"session": b.get("session")})
        if action == "transfer":
            return orch.transfer(ctx, {"session": b.get("session")})
        if action == "release":
            orch._need_owner(ctx)
            return orch.release_lease(ctx, {})
        raise invalid_field("action", "declare · transfer · release 중 하나")

    def post_orch_decide(request: Request, p: Principal, now: datetime, b: dict[str, Any]) -> dict[str, Any]:
        pid = request.path_params["pid"]
        rid = request.path_params["rid"]
        note = b.get("note") or ""
        if not isinstance(note, str):
            raise invalid_field("note", "문자열")
        return relays.decide(Ctx(now=now, via="ui", principal=_own(p, pid)),
                             {"request_id": rid, "decision": b.get("decision"), "note": note})

    def post_orch_message_close(request: Request, p: Principal, now: datetime, _b: Any) -> dict[str, Any]:
        pid = request.path_params["pid"]
        return orch.close_message(Ctx(now=now, via="ui", principal=_own(p, pid)), request.path_params["mid"])

    def post_orch_relay_invite(request: Request, p: Principal, now: datetime, _b: Any) -> dict[str, Any]:
        pid = request.path_params["pid"]
        public = str(request.base_url).rstrip("/")
        return relays.invite(Ctx(now=now, via="ui", principal=_own(p, pid), public_url=public), {})

    def post_orch_relay_revoke(request: Request, p: Principal, now: datetime, _b: Any) -> dict[str, Any]:
        pid = request.path_params["pid"]
        return relays.revoke(Ctx(now=now, via="ui", principal=_own(p, pid)), request.path_params["hid"])

    def post_response(request: Request, p: Principal, now: datetime, b: dict[str, Any]) -> dict[str, Any]:
        """결정 답 — 폼 값으로 response/1 본문을 만들어 :meth:`Judge.plan_respond` 에 넘긴다."""
        pid, tid = request.path_params["pid"], request.path_params["tid"]
        if p.kind != "callsign":
            raise forbidden("결정 답은 콜사인 토큰으로만 써요 (화면 공용 토큰은 읽기 · 등록만)")
        if p.project_id != pid:
            raise forbidden("이 토큰의 프로젝트가 아니에요")
        ctx = Ctx(now=now, via="ui", principal=p, client_version=CLIENT_TAG)
        task = store.task_get(ctx, tid)["task"]
        plan = plan_claims.parse_plan(task_lines(task["plan_md"], task["fields"])[0])
        if b.get("plan_digest") != plan_claims.plan_digest(plan):
            raise HubError(409, "version_conflict", "계획이 바뀌었어요 — 다시 열어라",
                           {"current_digest": plan_claims.plan_digest(plan)})
        values_in, opened_in, comments_in = b.get("values") or {}, b.get("opened") or {}, b.get("comments") or {}
        if not all(isinstance(x, dict) for x in (values_in, opened_in, comments_in)):
            raise invalid_field("values", "values · opened · comments 는 객체예요")
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
        Route("/api/account/{action}", account_endpoint, methods=["POST"]),
        Route("/api/projects", api(get_projects), methods=["GET"]),
        Route("/api/accounts", api(get_accounts), methods=["GET"]),
        Route("/api/accounts/{username}/admin", api(post_account_admin, body=True), methods=["POST"]),
        Route("/api/harness-reports", api(get_harness_reports), methods=["GET"]),
        Route("/api/harness-reports/{rid}/decision", api(post_harness_decision, body=True), methods=["POST"]),
        Route("/api/harness-people", api(get_harness_people), methods=["GET"]),
        Route("/api/harness-people", api(post_harness_people, body=True), methods=["POST"]),
        Route("/api/harness-registry", api(get_harness_registry), methods=["GET"]),
        Route("/api/projects/{pid}", api(get_project), methods=["GET"]),
        Route("/api/projects/{pid}/tasks", api(get_tasks), methods=["GET"]),
        Route("/api/projects/{pid}/tasks/{tid}", api(get_task), methods=["GET"]),
        Route("/api/projects/{pid}/events", api(get_events), methods=["GET"]),
        Route("/api/projects/{pid}/guide", api(get_guide), methods=["GET"]),
        Route("/api/projects/{pid}/guide", api(post_guide, body=True), methods=["POST"]),
        Route("/api/projects/{pid}/guide/proposals/{gid}", api(post_decide, body=True), methods=["POST"]),
        Route("/api/projects/{pid}/wiki", api(get_wiki), methods=["GET"]),
        Route("/api/projects/{pid}/wiki/page", api(get_wiki_page), methods=["GET"]),
        Route("/api/projects/{pid}/knowledge/ref", api(get_knowledge_ref), methods=["GET"]),
        Route("/api/projects/{pid}/dcr", api(get_dcrs), methods=["GET"]),
        Route("/api/projects/{pid}/dcr/{did}", api(get_dcr), methods=["GET"]),
        Route("/api/projects/{pid}/dcr/{did}/decision", api(post_dcr_decision, body=True), methods=["POST"]),
        Route("/api/projects/{pid}/callsigns", api(get_callsigns), methods=["GET"]),
        Route("/api/projects/{pid}/callsigns", api(post_callsign, body=True), methods=["POST"]),
        Route("/api/projects/{pid}/callsigns/{cs}", api(get_callsign), methods=["GET"]),
        Route("/api/projects/{pid}/callsigns/{cs}/approve", api(post_approve, body=True), methods=["POST"]),
        Route("/api/projects/{pid}/callsigns/{cs}/delete", api(post_callsign_delete, body=True), methods=["POST"]),
        Route("/api/projects/{pid}/tasks/{tid}/responses", api(post_response, body=True), methods=["POST"]),
        Route("/api/projects/{pid}/roadmap", api(get_roadmap), methods=["GET"]),
        Route("/api/projects/{pid}/orchestration", api(get_orchestration), methods=["GET"]),
        Route("/api/projects/{pid}/ideas", api(get_ideas), methods=["GET"]),
        Route("/api/projects/{pid}/ideas", api(post_idea, body=True), methods=["POST"]),
        Route("/api/projects/{pid}/ideas/{iid}", api(get_idea), methods=["GET"]),
        Route("/api/projects/{pid}/ideas/{iid}", api(post_idea_action, body=True), methods=["POST"]),
        Route("/api/projects/{pid}/confirmations", api(get_confirmations), methods=["GET"]),
        Route("/api/projects/{pid}/confirmations/{rid}", api(post_confirmation_decision, body=True), methods=["POST"]),
        Route("/api/projects/{pid}/orchestration/halt", api(post_orch_halt, body=True), methods=["POST"]),
        Route("/api/projects/{pid}/orchestration/lease", api(post_orch_lease, body=True), methods=["POST"]),
        Route("/api/projects/{pid}/orchestration/approvals/{rid}", api(post_orch_decide, body=True), methods=["POST"]),
        Route("/api/projects/{pid}/orchestration/messages/{mid}/close", api(post_orch_message_close, body=True), methods=["POST"]),
        Route("/api/projects/{pid}/orchestration/relays/invite", api(post_orch_relay_invite, body=True), methods=["POST"]),
        Route("/api/projects/{pid}/orchestration/relays/{hid}/revoke", api(post_orch_relay_revoke, body=True), methods=["POST"]),
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
