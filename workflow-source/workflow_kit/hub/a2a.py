"""A2A(Agent2Agent) 1.0 서버 — JSON-RPC 바인딩, 승인 Task (docs/planning/a2a-transition-2026-11.md A1).

Task 상태는 저장하지 않고 확인 요청에서 파생한다 (두 벌 두지 않는다). 상태는 권한이 아니다 — 실행 권한은
``approval_grant`` 뿐이고, 사람이 허브 계정으로 로그인해 연다. 신원은 HTTP Bearer 콜사인 토큰만 본다.
"""

from __future__ import annotations

import json
import secrets
import sqlite3
from datetime import datetime, timezone
from typing import Any

from workflow_kit import __version__ as HUB_VERSION
from workflow_kit.hub import a2a_peer, approval_grants
from workflow_kit.hub.confirmations import Confirmations
from workflow_kit.hub.errors import HubError
from workflow_kit.hub.store import Ctx, Principal, Store, _iso

PROTOCOL_VERSION = "1.0"
EXT_APPROVAL = "https://github.com/ykylee/standard_ai_workflow/a2a/ext/execution-approval/v1"
STATES = ("SUBMITTED", "WORKING", "COMPLETED", "FAILED", "CANCELED", "INPUT_REQUIRED", "REJECTED", "AUTH_REQUIRED")
CODES = {
    "TASK_NOT_FOUND": -32001, "TASK_NOT_CANCELABLE": -32002, "PUSH_NOTIFICATION_NOT_SUPPORTED": -32003,
    "UNSUPPORTED_OPERATION": -32004, "CONTENT_TYPE_NOT_SUPPORTED": -32005, "EXTENDED_AGENT_CARD_NOT_CONFIGURED": -32007,
    "VERSION_NOT_SUPPORTED": -32009, "INVALID_REQUEST": -32600, "METHOD_NOT_FOUND": -32601, "INVALID_PARAMS": -32602,
    "PARSE_ERROR": -32700,
}


TERMINAL = frozenset(f"TASK_STATE_{s}" for s in ("COMPLETED", "FAILED", "CANCELED", "REJECTED"))
STREAM_METHODS = ("SendStreamingMessage", "SubscribeToTask")
STREAM_CAP_S = 50       # 소유자 D2 — 닫히면 다시 구독한다
STREAM_POLL_S = 1.0
STREAM_KEEPALIVE_S = 15
STREAM_CAPACITY = 64
STREAM_PER_CALLSIGN = 8


def stream_events(before: dict[str, Any], after: dict[str, Any]) -> list[dict[str, Any]]:
    """두 시점의 Task → 보낼 이벤트. 아티팩트를 먼저 보낸다 (종료 상태가 마지막이 되게)."""
    if before["status"] == after["status"]:
        return []
    ids = {"taskId": after["id"], "contextId": after["contextId"]}
    out: list[dict[str, Any]] = [{"artifactUpdate": {**ids, "artifact": a, "append": False, "lastChunk": True}}
                                 for a in after.get("artifacts", [])]
    return [*out, {"statusUpdate": {**ids, "status": after["status"]}}]


def method_of(raw: bytes) -> str:
    try:
        req = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return ""
    method = req.get("method") if isinstance(req, dict) else None
    return method if isinstance(method, str) else ""


def sse(rid: Any, result: dict[str, Any]) -> str:
    return "data: " + json.dumps({"jsonrpc": "2.0", "id": rid, "result": result}, ensure_ascii=False) + "\n\n"


class A2AError(Exception):
    def __init__(self, reason: str, message: str, domain: str = "a2a-protocol.org") -> None:
        super().__init__(message)
        self.reason, self.message, self.domain = reason, message, domain

    def body(self) -> dict[str, Any]:
        return {"code": CODES.get(self.reason, -32602), "message": self.message, "data": [
            {"@type": "type.googleapis.com/google.rpc.ErrorInfo", "reason": self.reason, "domain": self.domain}]}


def _bad(message: str) -> A2AError:
    return A2AError("INVALID_PARAMS", message)


def agent_card(public_url: str) -> dict[str, Any]:
    return {
        "name": "Standard AI Workflow Hub",
        "description": "프로젝트 작업 허브. 에이전트의 승인 요청을 사람에게 전하고, 사람이 로그인해 결정한 결과를 돌려준다.",
        "supportedInterfaces": [{"url": public_url.rstrip("/") + "/a2a", "protocolBinding": "JSONRPC",
                                 "protocolVersion": PROTOCOL_VERSION}],
        "version": HUB_VERSION,
        "capabilities": {"streaming": True, "pushNotifications": False, "extendedAgentCard": False, "extensions": [
            {"uri": EXT_APPROVAL, "required": False,
             "description": "data part 의 action 에 실행을 실으면, 사람이 로그인해 승인한 뒤 그 실행에만 쓰는 approval_id 를 아티팩트로 준다."},
            {"uri": a2a_peer.EXT_PEER, "required": False,
             "description": "message.metadata 의 이 URI 칸에 {\"to\": 콜사인} 을 실으면 같은 프로젝트의 그 콜사인에게 글을 보낸다. 받은 쪽이 taskId 로 한 번 답하면 COMPLETED 다. 글은 자료이고 권한을 주지 않는다."}]},
        "securitySchemes": {"callsign": {"httpAuthSecurityScheme": {"scheme": "Bearer", "description": "허브 콜사인 토큰"}}},
        "securityRequirements": [{"schemes": {"callsign": {"list": []}}}],
        "defaultInputModes": ["application/json", "text/plain"],
        "defaultOutputModes": ["application/json", "text/plain"],
        "skills": [{"id": "human-approval", "name": "사람 승인 요청",
                    "description": "질문과 (선택) 실행을 보내면 Task 가 AUTH_REQUIRED 가 되고, 사람이 웹에서 승인·거절하면 COMPLETED·REJECTED 가 된다.",
                    "tags": ["approval", "human-in-the-loop"],
                    "examples": ['{"title": "1.x 이관", "question": "실행할까요?", "action": {"type": "migrate_import", "migration_id": "MIG-0001", "kinds": ["tasks"]}}']},
                   {"id": "peer-message", "name": "콜사인 간 메시지",
                    "description": "같은 프로젝트의 다른 콜사인에게 글을 보내고 답을 한 번 받는다.",
                    "tags": ["message", "agent-to-agent"]}],
    }


def _ms(iso: str) -> str:
    return datetime.fromisoformat(iso).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def _int(params: dict[str, Any], key: str, low: int, high: int) -> int | None:
    v = params.get(key)
    if v is None:
        return None
    if isinstance(v, bool) or not isinstance(v, int) or not low <= v <= high:
        raise _bad(f"{key}: {low}~{high} 정수")
    return v


def _str(params: dict[str, Any], key: str, limit: int = 256) -> str:
    v = params.get(key, "")
    if v is None:
        return ""
    if not isinstance(v, str) or len(v) > limit:
        raise _bad(f"{key}: {limit}자 이하 문자열")
    return v


def _content(message: dict[str, Any]) -> dict[str, Any]:
    """메시지 parts → 확인 요청 칸. 글 part 는 질문이 되고, data part 는 하나만 받는다."""
    parts = message.get("parts")
    if not isinstance(parts, list) or not parts:
        raise _bad("message.parts: 하나 이상")
    texts: list[str] = []
    data: dict[str, Any] | None = None
    for part in parts:
        kinds = [k for k in ("text", "raw", "url", "data") if isinstance(part, dict) and k in part]
        if len(kinds) != 1:
            raise _bad("part 는 text · raw · url · data 가운데 정확히 하나")
        if kinds[0] in ("raw", "url"):
            raise A2AError("CONTENT_TYPE_NOT_SUPPORTED", "파일 part 는 받지 않는다 — text 또는 data")
        if kinds[0] == "text":
            if not isinstance(part["text"], str):
                raise _bad("part.text: 문자열")
            texts.append(part["text"])
            continue
        if data is not None or not isinstance(part["data"], dict):
            raise _bad("data part 는 객체 하나")
        data = part["data"]
    out = dict(data or {})
    unknown = sorted(set(out) - {"title", "question", "details", "action"})
    if unknown:
        raise _bad("data 의 모르는 칸: " + ", ".join(unknown))
    text = "\n".join(texts).strip()
    out.setdefault("question", text)
    first = text.split("\n", 1)[0].strip() or str(out["question"]).strip().split("\n", 1)[0]
    out.setdefault("title", first[:160])
    return out


class A2A:
    def __init__(self, store: Store) -> None:
        self.store = store

    # --- JSON-RPC ---------------------------------------------------------------

    def handle(self, ctx: Ctx, raw: bytes, version: str) -> dict[str, Any]:
        rid: Any = None
        try:
            try:
                req = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise A2AError("PARSE_ERROR", "JSON 이 아니다") from exc
            if not isinstance(req, dict) or req.get("jsonrpc") != "2.0" or not isinstance(req.get("method"), str):
                raise A2AError("INVALID_REQUEST", "JSON-RPC 2.0 요청 객체가 아니다")
            got = req.get("id")
            if isinstance(got, bool) or not isinstance(got, (str, int)):
                raise A2AError("INVALID_REQUEST", "id 는 문자열이나 정수")
            rid = got
            params = req.get("params", {})
            if not isinstance(params, dict):
                raise _bad("params: 객체")
            if version != PROTOCOL_VERSION:  # 없거나 비면 0.3 으로 본다 — 이 허브는 1.0 만 말한다
                raise A2AError("VERSION_NOT_SUPPORTED", f"A2A-Version {version or '0.3'} 은 지원하지 않는다 — {PROTOCOL_VERSION}")
            return {"jsonrpc": "2.0", "id": rid, "result": self._call(ctx, req["method"], params)}
        except A2AError as e:
            return {"jsonrpc": "2.0", "id": rid, "error": e.body()}
        except HubError as e:
            err = A2AError(e.code.upper(), e.message, "workflow-hub")
            return {"jsonrpc": "2.0", "id": rid, "error": err.body()}

    def _call(self, ctx: Ctx, method: str, params: dict[str, Any]) -> dict[str, Any]:
        if method == "SendMessage":
            return self.send(ctx, params)
        if method == "GetTask":
            return self.get(ctx, params)
        if method == "ListTasks":
            return self.list(ctx, params)
        if method == "CancelTask":
            return self.cancel(ctx, params)
        if method == "SendStreamingMessage":
            return self.send(ctx, params)
        if method == "SubscribeToTask":
            task = self.get(ctx, {"id": params.get("id")})
            if task["status"]["state"] in TERMINAL:
                raise A2AError("UNSUPPORTED_OPERATION", "끝난 Task 는 구독할 수 없다 — GetTask 로 확인한다")
            return {"task": task}
        if method.endswith("PushNotificationConfig") or method == "ListTaskPushNotificationConfigs":
            raise A2AError("PUSH_NOTIFICATION_NOT_SUPPORTED", "푸시 알림은 제공하지 않는다")
        if method == "GetExtendedAgentCard":
            raise A2AError("EXTENDED_AGENT_CARD_NOT_CONFIGURED", "확장 카드는 없다")
        raise A2AError("METHOD_NOT_FOUND", f"모르는 메서드: {method}")

    # --- Task -------------------------------------------------------------------

    def _rows(self, conn: sqlite3.Connection, p: Principal, task_id: str = "") -> list[sqlite3.Row]:
        q = ("SELECT t.id, t.context_id, t.message_json, t.created_at, t.canceled_at, t.request_id, m.state AS mstate, m.acked_at, "
             "m.ack_reason, g.state AS gstate, g.action, g.params_json, g.summary_json, g.expires_at "
             "FROM a2a_task t JOIN inbox_message m ON m.project_id = t.project_id AND m.id = t.request_id "
             "LEFT JOIN approval_grant g ON g.project_id = t.project_id AND g.id = t.request_id "
             "WHERE t.project_id = ? AND t.callsign = ?")
        args = [p.project_id, p.callsign]
        if task_id:
            q, args = q + " AND t.id = ?", [*args, task_id]
        return list(conn.execute(q, args))

    @staticmethod
    def _state(r: sqlite3.Row) -> tuple[str, str]:
        if r["canceled_at"]:
            return "CANCELED", r["canceled_at"]
        if r["mstate"] == "acked":
            return "COMPLETED", r["acked_at"]
        if r["mstate"] == "declined":
            return "REJECTED", r["acked_at"]
        if r["mstate"] == "expired":
            return "FAILED", r["created_at"]
        return "AUTH_REQUIRED", r["created_at"]

    def _task(self, ctx: Ctx, r: sqlite3.Row, history: int | None, artifacts: bool = True) -> dict[str, Any]:
        state, at = self._state(r)
        p = ctx.principal
        assert p is not None
        note = r["ack_reason"] or ""
        text = {"AUTH_REQUIRED": "사람이 허브 화면에서 로그인해 승인하거나 거절해야 한다.", "COMPLETED": "사람이 승인했다.",
                "REJECTED": "사람이 거절했다.", "CANCELED": "요청한 에이전트가 취소했다.", "FAILED": "요청이 만료됐다."}[state]
        data: dict[str, Any] = {"approval_url": f"{ctx.public_url.rstrip('/')}/ui/#/p/{p.project_id}/confirmations"}
        if note:
            data["note"] = note
        if r["action"]:
            data["action"] = {"params": json.loads(r["params_json"]), "summary": approval_grants.brief(json.loads(r["summary_json"]))}
        task: dict[str, Any] = {
            "id": r["id"], "contextId": r["context_id"],
            "status": {"state": f"TASK_STATE_{state}", "timestamp": _ms(at), "message": {
                "messageId": f"{r['id']}-status", "taskId": r["id"], "contextId": r["context_id"], "role": "ROLE_AGENT",
                "parts": [{"text": text}, {"data": data, "mediaType": "application/json"}]}},
        }
        if state == "COMPLETED" and artifacts:
            result: dict[str, Any] = {"decision": "approve", "note": note}
            if r["action"]:
                result.update({"approval_id": r["request_id"], "approval_state": r["gstate"], "expires_at": r["expires_at"],
                               "action": json.loads(r["params_json"])})
            task["artifacts"] = [{"artifactId": "approval", "name": "승인 결과",
                                  "parts": [{"data": result, "mediaType": "application/json"}]}]
        if history is None or history > 0:
            task["history"] = [json.loads(r["message_json"])]
        return task

    def _need(self, ctx: Ctx) -> Principal:
        return self.store._need_callsign(ctx)

    def _one(self, conn: sqlite3.Connection, p: Principal, task_id: str) -> sqlite3.Row:
        rows = self._rows(conn, p, task_id) if task_id else []
        if not rows:  # 남의 Task 도 같은 답 — 존재를 드러내지 않는다
            raise A2AError("TASK_NOT_FOUND", f"Task 가 없다: {task_id}")
        return rows[0]

    def _peer_task(self, ctx: Ctx, r: sqlite3.Row, history: int | None, artifacts: bool = True) -> dict[str, Any]:
        state, at = a2a_peer.state(r, ctx.now)
        text = {"SUBMITTED": "상대에게 아직 실리지 않았다.", "WORKING": "상대 세션에 실렸다. 답을 기다린다.", "COMPLETED": "상대가 답했다.",
                "CANCELED": "보낸 콜사인이 거뒀다.", "FAILED": "답 없이 7일이 지났다."}[state]
        task: dict[str, Any] = {
            "id": r["id"], "contextId": r["context_id"],
            "status": {"state": f"TASK_STATE_{state}", "timestamp": _ms(at), "message": {
                "messageId": f"{r['id']}-status", "taskId": r["id"], "contextId": r["context_id"], "role": "ROLE_AGENT",
                "parts": [{"text": text}, {"data": {"from": r["from_callsign"], "to": r["to_callsign"], "authority": "none"},
                                           "mediaType": "application/json"}]}},
        }
        if state == "COMPLETED" and artifacts:
            task["artifacts"] = [{"artifactId": "reply", "name": "답", "parts": [{"text": a2a_peer.text_of(json.loads(r["reply_json"]))}]}]
        if history is None or history > 0:
            task["history"] = [json.loads(r["message_json"])]
        return task

    def _peer_one(self, conn: sqlite3.Connection, p: Principal, task_id: str) -> sqlite3.Row:
        found = a2a_peer.rows(conn, p, task_id)
        if not found:
            raise A2AError("TASK_NOT_FOUND", f"Task 가 없다: {task_id}")
        return found[0]

    def _peer_parts(self, message: dict[str, Any]) -> str:
        parts = message.get("parts")
        if not isinstance(parts, list) or not parts:
            raise _bad("message.parts: 하나 이상")
        for part in parts:
            if not isinstance(part, dict) or not isinstance(part.get("text"), str) or any(k in part for k in ("raw", "url", "data")):
                raise _bad("콜사인 간 메시지는 text part 만 받는다")
        text = a2a_peer.text_of(message)
        a2a_peer.check_text(text)
        return text

    def _peer_send(self, ctx: Ctx, p: Principal, message: dict[str, Any], spec: Any, history: int | None) -> dict[str, Any]:
        if not isinstance(spec, dict) or set(spec) != {"to"} or not isinstance(spec["to"], str) or not spec["to"]:
            raise _bad("metadata 의 peer-message: {to: 콜사인}")
        if spec["to"] == p.callsign:
            raise _bad("자신에게 보낼 수 없다")
        self._peer_parts(message)
        canon = json.dumps(message, ensure_ascii=False, sort_keys=True)
        with self.store.write() as conn:
            seen = conn.execute("SELECT id, source_json FROM a2a_peer WHERE project_id = ? AND from_callsign = ? AND message_id = ?",
                                (p.project_id, p.callsign, message["messageId"])).fetchone()
            if seen is not None and seen["source_json"] != canon:
                raise _bad("같은 messageId 를 다른 내용으로 다시 보냈다")
            tid = seen["id"] if seen is not None else a2a_peer.insert(conn, self.store, ctx, p, spec["to"], message, canon)
            return {"task": self._peer_task(ctx, self._peer_one(conn, p, tid), history)}

    def _peer_reply(self, ctx: Ctx, p: Principal, message: dict[str, Any], task_id: str, context: str, history: int | None) -> dict[str, Any]:
        with self.store.write() as conn:
            row = self._peer_one(conn, p, task_id)
            if context and context != row["context_id"]:
                raise _bad("contextId 가 그 Task 의 것과 다르다")
            if row["to_callsign"] != p.callsign:
                raise A2AError("UNSUPPORTED_OPERATION", "답은 받은 콜사인만 한다 — 더 보내려면 새 메시지를 보낸다")
            self._peer_parts(message)
            canon = json.dumps(message, ensure_ascii=False, sort_keys=True)
            if row["reply_message_id"] == message["messageId"]:
                if row["reply_json"] != canon:
                    raise _bad("같은 messageId 를 다른 내용으로 다시 보냈다")
                return {"task": self._peer_task(ctx, row, history)}
            if a2a_peer.state(row, ctx.now)[0] not in ("SUBMITTED", "WORKING"):
                raise A2AError("UNSUPPORTED_OPERATION", "이미 끝난 Task 다 — 답은 한 번이다")
            if a2a_peer.halted(conn, p.project_id):
                raise HubError(423, "halted", "오케스트레이션이 정지돼 있어요")
            conn.execute("UPDATE a2a_peer SET reply_message_id = ?, reply_json = ?, replied_at = ? WHERE project_id = ? AND id = ?",
                         (message["messageId"], canon, _iso(ctx.now), p.project_id, task_id))
            self.store._event(conn, ctx, str(p.project_id), "a2a_peer", task_id, "reply", None, {"to": row["from_callsign"]})
            return {"task": self._peer_task(ctx, self._peer_one(conn, p, task_id), history)}

    def get(self, ctx: Ctx, params: dict[str, Any]) -> dict[str, Any]:
        history = _int(params, "historyLength", 0, 1000)
        p = self._need(ctx)
        tid = _str(params, "id")
        with self.store.read() as conn:
            if tid.startswith("A2M-"):
                return self._peer_task(ctx, self._peer_one(conn, p, tid), history)
            return self._task(ctx, self._one(conn, p, tid), history)

    def list(self, ctx: Ctx, params: dict[str, Any]) -> dict[str, Any]:
        p = self._need(ctx)
        size = _int(params, "pageSize", 1, 100) or 50
        history = _int(params, "historyLength", 0, 1000)
        context, status, token = _str(params, "contextId"), _str(params, "status"), _str(params, "pageToken")
        artifacts = params.get("includeArtifacts", False)
        if not isinstance(artifacts, bool):
            raise _bad("includeArtifacts: true · false")
        if status in ("", "TASK_STATE_UNSPECIFIED"):
            status = ""
        elif status.removeprefix("TASK_STATE_") not in STATES or not status.startswith("TASK_STATE_"):
            raise _bad(f"모르는 status: {status}")
        if token and not (token.isascii() and token.isdigit() and len(token) < 10):
            raise _bad("pageToken 이 올바르지 않다")
        after = _str(params, "statusTimestampAfter")
        since: datetime | None = None
        if after:
            try:
                since = datetime.fromisoformat(after.replace("Z", "+00:00"))
            except ValueError as exc:
                raise _bad("statusTimestampAfter: RFC 3339 시각") from exc
            if since.tzinfo is None:
                raise _bad("statusTimestampAfter: 시간대가 필요하다")
        with self.store.read() as conn:
            found = [(r, self._state(r), self._task) for r in self._rows(conn, p)]
            found += [(r, a2a_peer.state(r, ctx.now), self._peer_task) for r in a2a_peer.rows(conn, p)]
        keep = []
        for r, (state, at), view in found:
            if (context and r["context_id"] != context) or (status and f"TASK_STATE_{state}" != status):
                continue
            if since is not None and datetime.fromisoformat(at) <= since:
                continue
            keep.append((at, r["id"], r, view))
        keep.sort(key=lambda x: (x[0], x[1]), reverse=True)
        start = int(token) if token else 0
        page = keep[start:start + size]
        end = start + size
        return {"tasks": [view(ctx, r, history, artifacts) for _, _, r, view in page],
                "nextPageToken": str(end) if end < len(keep) else "", "pageSize": len(page), "totalSize": len(keep)}

    def send(self, ctx: Ctx, params: dict[str, Any]) -> dict[str, Any]:
        p = self._need(ctx)
        message = params.get("message")
        if not isinstance(message, dict):
            raise _bad("message: 객체")
        config = params.get("configuration") or {}
        if not isinstance(config, dict):
            raise _bad("configuration: 객체")
        if config.get("taskPushNotificationConfig"):
            raise A2AError("PUSH_NOTIFICATION_NOT_SUPPORTED", "푸시 알림은 제공하지 않는다")
        history = _int(config, "historyLength", 0, 1000)
        mid, context, task_id = _str(message, "messageId", 128), _str(message, "contextId", 128), _str(message, "taskId", 128)
        if not mid:
            raise _bad("message.messageId: 필수")
        if message.get("role") != "ROLE_USER":
            raise _bad("message.role: ROLE_USER")
        metadata = message.get("metadata")
        spec = metadata.get(a2a_peer.EXT_PEER) if isinstance(metadata, dict) else None
        if task_id.startswith("A2M-"):
            if spec is not None:
                raise _bad("taskId 와 peer-message 의 to 를 함께 싣지 않는다")
            return self._peer_reply(ctx, p, message, task_id, context, history)
        if task_id:
            with self.store.read() as conn:
                row = self._one(conn, p, task_id)
            if context and context != row["context_id"]:
                raise _bad("contextId 가 그 Task 의 것과 다르다")
            raise A2AError("UNSUPPORTED_OPERATION", "승인 Task 에는 이어서 보낼 수 없다 — 사람이 화면에서 결정한다. 거두려면 CancelTask")
        if spec is not None:
            return self._peer_send(ctx, p, message, spec, history)
        fields = _content(message)
        canon = json.dumps(message, ensure_ascii=False, sort_keys=True)
        conf = Confirmations(self.store)
        title, question, details = conf.validate(fields)
        with self.store.write() as conn:
            seen = conn.execute("SELECT id, source_json FROM a2a_task WHERE project_id = ? AND callsign = ? AND message_id = ?",
                                (p.project_id, p.callsign, mid)).fetchone()
            if seen is not None:
                if seen["source_json"] != canon:
                    raise _bad("같은 messageId 를 다른 내용으로 다시 보냈다")
                return {"task": self._task(ctx, self._one(conn, p, seen["id"]), history)}
            request_id, _prepared = conf.create(conn, ctx, p, title, question, details, fields.get("action"), "")
            tid = f"A2A-{ctx.now.strftime('%Y%m%d')}-{secrets.token_hex(8)}"
            cid = context or f"CTX-{secrets.token_hex(8)}"
            stored = {**message, "taskId": tid, "contextId": cid}
            conn.execute("INSERT INTO a2a_task (project_id, id, context_id, callsign, message_id, request_id, source_json, message_json, created_at) "
                         "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                         (p.project_id, tid, cid, p.callsign, mid, request_id, canon, json.dumps(stored, ensure_ascii=False), _iso(ctx.now)))
            self.store._event(conn, ctx, str(p.project_id), "a2a_task", tid, "create", None, {"request_id": request_id, "context_id": cid})
            return {"task": self._task(ctx, self._one(conn, p, tid), history)}

    def cancel(self, ctx: Ctx, params: dict[str, Any]) -> dict[str, Any]:
        p = self._need(ctx)
        tid = _str(params, "id")
        with self.store.write() as conn:
            if tid.startswith("A2M-"):
                peer = self._peer_one(conn, p, tid)
                if peer["from_callsign"] != p.callsign or a2a_peer.state(peer, ctx.now)[0] not in ("SUBMITTED", "WORKING"):
                    raise A2AError("TASK_NOT_CANCELABLE", "보낸 콜사인이 끝나기 전에만 거둔다")
                conn.execute("UPDATE a2a_peer SET canceled_at = ? WHERE project_id = ? AND id = ?", (_iso(ctx.now), p.project_id, tid))
                self.store._event(conn, ctx, str(p.project_id), "a2a_peer", tid, "cancel", None, None)
                return self._peer_task(ctx, self._peer_one(conn, p, tid), 0)
            row = self._one(conn, p, tid)
            if self._state(row)[0] != "AUTH_REQUIRED":
                raise A2AError("TASK_NOT_CANCELABLE", "이미 끝난 Task 다")
            conn.execute("UPDATE a2a_task SET canceled_at = ? WHERE project_id = ? AND id = ?", (_iso(ctx.now), p.project_id, row["id"]))
            conn.execute("UPDATE inbox_message SET state = 'expired', version = version + 1 WHERE project_id = ? AND id = ?",
                         (p.project_id, row["request_id"]))
            approval_grants.withdraw(conn, ctx, str(p.project_id), row["request_id"])
            self.store._event(conn, ctx, str(p.project_id), "a2a_task", row["id"], "cancel", None, {"request_id": row["request_id"]})
            return self._task(ctx, self._one(conn, p, row["id"]), 0)
