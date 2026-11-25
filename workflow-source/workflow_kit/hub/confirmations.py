"""Agent confirmation requests stored and delivered through the hub inbox."""

from __future__ import annotations

import json
import sqlite3
from typing import Any

from workflow_kit.hub import approval_grants
from workflow_kit.hub.errors import HubError, invalid_field, not_found
from workflow_kit.hub.orchestration import Orchestration
from workflow_kit.hub.store import Ctx, Principal, Store, _iso, scan_secrets


class Confirmations:
    def __init__(self, store: Store) -> None:
        self.store = store
        self.orch = Orchestration(store)

    @staticmethod
    def validate(args: dict[str, Any]) -> tuple[str, str, str]:
        title = args.get("title")
        question = args.get("question")
        details = args.get("details") or ""
        if not isinstance(title, str) or not title.strip() or len(title) > 160:
            raise invalid_field("title", "1~160자 문자열")
        if not isinstance(question, str) or not question.strip() or len(question) > 2000:
            raise invalid_field("question", "1~2000자 문자열")
        if not isinstance(details, str) or len(details) > 4000:
            raise invalid_field("details", "4000자 이하 문자열")
        scan_secrets({"title": title, "question": question, "details": details}, "confirmation")
        return title.strip(), question.strip(), details

    def create(self, conn: sqlite3.Connection, ctx: Ctx, p: Principal, title: str, question: str, details: str,
               action: Any, session_id: str) -> tuple[str, tuple[dict[str, Any], dict[str, Any]] | None]:
        """확인 요청 한 건을 쌓는다 — MCP 도구와 A2A 가 같은 함수를 쓴다 (세션은 있을 때만)."""
        callsign = str(p.callsign)
        row = conn.execute("SELECT owner_callsign FROM project WHERE id=?", (p.project_id,)).fetchone()
        if row is None:
            raise not_found(f"프로젝트가 없다: {p.project_id}")
        prepared = approval_grants.prepare(conn, str(p.project_id), action) if action is not None else None
        request_id = self.orch.enqueue(
            conn, ctx, str(p.project_id), to_kind="callsign", to_id=row["owner_callsign"],
            kind="approval", body={"request_type": "agent_confirmation", "title": title,
                                   "question": question, "details": details,
                                   "requested_by": callsign, "requested_by_session": session_id,
                                   "state": "pending"},
            from_callsign=callsign, from_session=session_id,
        )
        if prepared is not None:
            approval_grants.insert(conn, ctx, str(p.project_id), request_id, callsign, *prepared)
        self.store._event(conn, ctx, str(p.project_id), "confirmation_request", request_id, "request", None,
                          {"state": "pending", "requested_by": callsign, "action": prepared[0] if prepared else None})
        return request_id, prepared

    def request(self, ctx: Ctx, args: dict[str, Any]) -> dict[str, Any]:
        title, question, details = self.validate(args)
        p = self.orch._callsign(ctx)
        if not p.callsign:
            raise invalid_field("callsign", "콜사인 토큰이 필요하다")
        session_id = args.get("session")
        if not isinstance(session_id, str):
            raise invalid_field("session", "세션 식별자가 필요하다")
        with self.store.write() as conn:
            self.orch._session_row(conn, p, session_id)
            request_id, prepared = self.create(conn, ctx, p, title, question, details, args.get("action"), session_id)
        if prepared is not None:
            return {"request": {"id": request_id, "state": "pending", "title": title, "action": prepared[0]},
                    "approval_id": request_id,
                    "next": "사람이 허브 계정으로 로그인해 확인 요청에서 승인하면, 같은 콜사인으로 실행 도구에 approval_id 를 싣는다 (승인 뒤 24시간)."}
        return {"request": {"id": request_id, "state": "pending", "title": title},
                "next": "사람이 웹 허브의 확인 요청 메뉴에서 결정할 때까지 대기한다. 결과는 허브 받은편지함으로 온다."}

    def list_pending(self, ctx: Ctx) -> dict[str, Any]:
        p = self.orch._need_owner(ctx)
        if not p.callsign or not p.project_id:
            raise invalid_field("owner", "프로젝트 사람 소유자 콜사인이 필요하다")
        with self.store.read() as conn:
            rows = conn.execute(
                "SELECT id,from_callsign,from_session,body_json,created_at,state FROM inbox_message "
                "WHERE project_id=? AND to_kind='callsign' AND to_id=? AND kind='approval' "
                "AND state IN ('queued','delivered','unacknowledged') ORDER BY created_at DESC LIMIT 200",
                (p.project_id, p.callsign),
            ).fetchall()
            actions = approval_grants.summaries(conn, p.project_id)
        requests = []
        for row in rows:
            body = json.loads(row["body_json"])
            if not isinstance(body, dict) or body.get("request_type") != "agent_confirmation":
                continue
            requests.append({"id": row["id"], "requested_by": row["from_callsign"],
                             "requested_by_session": row["from_session"], "created_at": row["created_at"],
                             "title": body.get("title", ""), "question": body.get("question", ""),
                             "details": body.get("details", ""), "action": actions.get(row["id"])})
        return {"requests": requests}

    def decide(self, ctx: Ctx, request_id: str, decision: str, note: str = "") -> dict[str, Any]:
        p = self.orch._need_owner(ctx)
        if not p.callsign or not p.project_id:
            raise invalid_field("owner", "프로젝트 사람 소유자 콜사인이 필요하다")
        if decision not in {"approve", "reject"}:
            raise invalid_field("decision", "approve · reject")
        if not isinstance(note, str) or len(note) > 1000:
            raise invalid_field("note", "1000자 이하 문자열")
        scan_secrets(note, "note")
        target_state = "acked" if decision == "approve" else "declined"
        with self.store.write() as conn:
            row = conn.execute(
                "SELECT * FROM inbox_message WHERE project_id=? AND id=? AND to_kind='callsign' AND to_id=? AND kind='approval'",
                (p.project_id, request_id, p.callsign),
            ).fetchone()
            if row is None:
                raise not_found(f"확인 요청이 없다: {request_id}")
            body = json.loads(row["body_json"])
            if not isinstance(body, dict) or body.get("request_type") != "agent_confirmation":
                raise not_found(f"에이전트 확인 요청이 아니다: {request_id}")
            if row["state"] in {"acked", "declined"}:
                if row["state"] == target_state:
                    return {"request": {"id": request_id, "state": "approved" if decision == "approve" else "rejected"},
                            "unchanged": True}
                raise HubError(409, "already_decided", "이미 다른 결정을 내린 요청이다", {"state": row["state"]})
            if row["state"] == "expired":
                raise HubError(409, "request_expired", "만료된 확인 요청이다")
            approval_grants.decide(conn, ctx, request_id, decision == "approve")
            conn.execute(
                "UPDATE inbox_message SET state=?,acked_at=?,ack_by_session=?,ack_reason=?,version=version+1 "
                "WHERE project_id=? AND id=?",
                (target_state, _iso(ctx.now), "web:" + p.callsign, note, p.project_id, request_id),
            )
            state = "approved" if decision == "approve" else "rejected"
            self.store._event(conn, ctx, str(p.project_id), "confirmation_request", request_id, decision,
                              {"state": "pending"}, {"state": state, "note": note})
            reply_id = self.orch.enqueue(
                conn, ctx, str(p.project_id), to_kind="callsign", to_id=body["requested_by"], kind="note",
                body={"event": "confirmation_result", "request_id": request_id, "decision": decision,
                      "state": state, "title": body["title"], "note": note},
                from_callsign=p.callsign, ref_request=request_id,
            )
        return {"request": {"id": request_id, "state": state}, "message_id": reply_id}
