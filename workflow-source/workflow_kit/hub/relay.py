"""허브 쪽 PC 중계 — 등록(초대 코드) · 긴 폴링 · 실행 결과 · 세션 요청과 owner 승인 (``core/hub_orchestration_spec.md`` §9, M-046).

규칙:
    - 중앙은 PC 로 들어가지 않는다 — 중계가 나가는 연결로 가져간다 (요구 R21.2). 이 모듈은 중계가 부르는 쪽만 가진다.
    - 중계 토큰은 콜사인 토큰이 아니다 — ``relay_host.token_hash``, 권한은 ``/v1/relay/…`` 뿐 (DO8).
    - 허용 목록 내용은 PC 에만 있다 — 허브는 별칭 · 해시만 받는다 (DO9). 허브는 승인된 요청을 내줄 뿐, 실행 여부는 중계가 정한다.
    - 세션 요청 · 멈춤 요청은 요청마다 owner 승인 (O4 · 요구 R19.4).
"""

from __future__ import annotations

import json
import secrets
import sqlite3
from datetime import datetime, timedelta
from typing import Any

from workflow_kit.hub.errors import HubError, forbidden, invalid_field, not_found
from workflow_kit.hub.orchestration import Orchestration
from workflow_kit.hub.store import Ctx, Principal, Store, _iso, _json, hash_token, new_token, scan_secrets

INVITE_TTL = timedelta(hours=24)
POLL_CAP_S = 25                                     # 긴 폴링 한 번 상한 — 프록시 · 하네스 기본 상한 아래
PERMISSION_MODES = ("default", "acceptEdits", "plan")  # bypass 계열은 허브도 받지 않는다 (중계도 거부 — 이중)
SESSION_REQUESTS_PER_DAY = 10                       # 요구 R23.1 · Q4
NAME_MAX = 80


def _code() -> str:
    return "wri_" + secrets.token_urlsafe(18)


class Relays:
    def __init__(self, store: Store) -> None:
        self.store = store
        self.orch = Orchestration(store)

    # --- 초대 · 등록 · 인증 ----------------------------------------------------------

    def invite(self, ctx: Ctx, a: dict[str, Any]) -> dict[str, Any]:
        """owner 가 중계 초대 코드를 만든다 — 한 번 · 24시간. 코드는 이 응답에만 있다."""
        p = self.orch._need_owner(ctx)
        code = _code()
        with self.store.write() as conn:
            conn.execute("INSERT INTO relay_invite (code_hash, for_project, owner_callsign, created_at, expires_at) "
                         "VALUES (?, ?, ?, ?, ?)", (hash_token(code), p.project_id, p.callsign, _iso(ctx.now),
                                                    _iso(ctx.now + INVITE_TTL)))
            self.store._event(conn, ctx, p.project_id, "relay_invite", "-", "issue", None,
                              {"expires_at": _iso(ctx.now + INVITE_TTL)})
        base = ctx.public_url or "<허브 주소>"
        return {"invite": code, "expires_at": _iso(ctx.now + INVITE_TTL),
                "command": f"python -m workflow_kit relay init --hub {base} --invite <위 코드> --name <이 PC 이름>",
                "note": "코드는 이 응답에만 있다 — 그 PC 의 사람에게 직접 건넨다. 한 번 쓰면 끝이다."}

    def register(self, now: datetime, a: Any) -> dict[str, Any]:
        """중계 등록 — 초대 코드 → host_id · 중계 토큰 (토큰은 이 응답에만)."""
        if not isinstance(a, dict) or set(a) - {"invite", "name", "harnesses"}:
            raise HubError(400, "unknown_field", "invite · name · harnesses 만 받는다")
        code, name, harnesses = a.get("invite"), a.get("name"), a.get("harnesses") or []
        if not isinstance(code, str) or not code:
            raise invalid_field("invite", "필수")
        if not isinstance(name, str) or not name.strip() or len(name) > NAME_MAX:
            raise invalid_field("name", f"1~{NAME_MAX}자")
        if not isinstance(harnesses, list) or not all(isinstance(h, str) and h for h in harnesses):
            raise invalid_field("harnesses", "하네스 이름 목록")
        scan_secrets({"name": name, "harnesses": harnesses})
        token = new_token()
        host_id = f"H-{now.strftime('%Y%m%d')}-{secrets.token_hex(4)}"
        ctx = Ctx(now=now, via="relay")
        with self.store.write() as conn:
            row = conn.execute("SELECT * FROM relay_invite WHERE code_hash = ?", (hash_token(code),)).fetchone()
            if row is None or row["used_at"] or row["expires_at"] <= _iso(now):
                raise HubError(403, "invite_invalid", "초대 코드가 없거나 · 썼거나 · 만료됐다")
            conn.execute("UPDATE relay_invite SET used_at = ?, host_id = ? WHERE code_hash = ?",
                         (_iso(now), host_id, row["code_hash"]))
            conn.execute("INSERT INTO relay_host (host_id, name, token_hash, owner_callsign, projects_json, harnesses_json, "
                         "last_seen_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                         (host_id, name.strip(), hash_token(token), row["owner_callsign"], _json([row["for_project"]]),
                          _json(harnesses), _iso(now)))
            self.store._event(conn, ctx, row["for_project"], "relay_host", host_id, "register", None,
                              {"name": name.strip(), "harnesses": harnesses}, callsign=row["owner_callsign"])
        return {"host_id": host_id, "token": token, "project_id": row["for_project"]}

    def authenticate(self, token: str | None) -> sqlite3.Row | None:
        if not token:
            return None
        with self.store.read() as conn:
            row: sqlite3.Row | None = conn.execute(
                "SELECT * FROM relay_host WHERE token_hash = ? AND revoked_at IS NULL", (hash_token(token),)).fetchone()
            return row

    def list_hosts(self, ctx: Ctx, a: dict[str, Any]) -> dict[str, Any]:
        p = self.store._need_reader(ctx)
        with self.store.read() as conn:
            rows = conn.execute("SELECT * FROM relay_host WHERE revoked_at IS NULL ORDER BY host_id").fetchall()
        out = []
        for r in rows:
            if p.project_id in json.loads(r["projects_json"]):
                out.append({"host_id": r["host_id"], "name": r["name"], "harnesses": json.loads(r["harnesses_json"]),
                            "allow_digest": r["allow_digest"] or None, "last_seen_at": r["last_seen_at"]})
        return {"hosts": out}

    # --- 세션 요청 · 멈춤 요청 · 승인 (요구 R19.4) ----------------------------------------

    def _host_for(self, conn: sqlite3.Connection, project_id: str, host_id: Any) -> sqlite3.Row:
        row: sqlite3.Row | None = conn.execute("SELECT * FROM relay_host WHERE host_id = ? AND revoked_at IS NULL",
                                               (host_id,)).fetchone()
        if row is None or project_id not in json.loads(row["projects_json"]):
            raise not_found(f"이 프로젝트의 중계가 아니다: {host_id}")
        return row

    def _next_request_id(self, conn: sqlite3.Connection, project_id: str) -> str:
        n = conn.execute("SELECT COUNT(*) FROM session_request WHERE project_id = ?", (project_id,)).fetchone()[0]
        return f"SR-{n + 1:04d}"

    def _count(self, conn: sqlite3.Connection, project_id: str, now: datetime, name: str, limit: int) -> None:
        day = now.strftime("%Y-%m-%d")
        conn.execute("INSERT INTO orch_counter (project_id, day, name, n) VALUES (?, ?, ?, 0) "
                     "ON CONFLICT(project_id, day, name) DO NOTHING", (project_id, day, name))
        n = conn.execute("SELECT n FROM orch_counter WHERE project_id = ? AND day = ? AND name = ?",
                         (project_id, day, name)).fetchone()[0]
        if n >= limit:
            raise HubError(429, "limit_reached", f"오늘 {name} 상한 {limit} — 사람에게 알린다", {"limit": limit, "name": name})
        conn.execute("UPDATE orch_counter SET n = n + 1 WHERE project_id = ? AND day = ? AND name = ?",
                     (project_id, day, name))

    def _approval_note(self, conn: sqlite3.Connection, ctx: Ctx, project_id: str, rid: str, body: dict[str, Any]) -> None:
        owner = conn.execute("SELECT owner_callsign FROM project WHERE id = ?", (project_id,)).fetchone()
        self.orch.enqueue(conn, ctx, project_id, to_kind="callsign", to_id=owner["owner_callsign"], kind="approval",
                          ref_request=rid, body={**body, "decide_with": "hub_approval_decide"}, from_callsign="hub")

    def request_session(self, ctx: Ctx, a: dict[str, Any]) -> dict[str, Any]:
        mode = a.get("permission_mode") or "default"
        if mode not in PERMISSION_MODES:
            raise invalid_field("permission_mode", f"{' · '.join(PERMISSION_MODES)} 중 하나 (bypass 계열은 받지 않는다)")
        prompt = a.get("prompt") or ""
        scan_secrets({"prompt": prompt, "dir_alias": a["dir_alias"]})

        def do(conn: sqlite3.Connection) -> dict[str, Any]:
            p, lease = self.orch._need_orch(conn, ctx, a.get("session"))
            pid = str(p.project_id)
            if lease["halted"]:
                raise HubError(423, "halted", "오케스트레이션이 정지돼 있다")
            host = self._host_for(conn, pid, a["host_id"])
            if a["harness"] not in json.loads(host["harnesses_json"]):
                raise HubError(409, "harness_not_on_host", f"그 중계에 {a['harness']} 어댑터가 없다",
                               {"harnesses": json.loads(host["harnesses_json"])})
            self._count(conn, pid, ctx.now, "session_requests", SESSION_REQUESTS_PER_DAY)
            rid = self._next_request_id(conn, pid)
            target = {"dir_alias": a["dir_alias"], "harness": a["harness"], "permission_mode": mode, "prompt": prompt}
            conn.execute("INSERT INTO session_request (project_id, id, kind, host_id, target_json, requested_by, state, "
                         "created_at) VALUES (?, ?, 'spawn', ?, ?, ?, 'pending_approval', ?)",
                         (pid, rid, host["host_id"], _json(target), lease["session_id"], _iso(ctx.now)))
            self.store._event(conn, ctx, pid, "session_request", rid, "request", None, {"kind": "spawn", **target})
            self._approval_note(conn, ctx, pid, rid, {"request": rid, "kind": "spawn", "host": host["name"], **target})
            return {"request": {"id": rid, "state": "pending_approval", "kind": "spawn"}}

        return self.store.idempotent(ctx, a.get("request_id"), do)

    def request_stop(self, ctx: Ctx, a: dict[str, Any]) -> dict[str, Any]:
        reason = a.get("reason") or ""
        scan_secrets(reason, "reason")
        with self.store.write() as conn:
            p, lease = self.orch._need_orch(conn, ctx, a.get("session"))
            pid = str(p.project_id)
            target = self.orch._active_session(conn, pid, a["target_session"])
            if not target["host_id"]:
                raise HubError(409, "not_relay_session", "중계가 띄운 세션이 아니다 — 사람이 보는 세션은 멈출 수 없다 (메시지로 release)")
            rid = self._next_request_id(conn, pid)
            conn.execute("INSERT INTO session_request (project_id, id, kind, host_id, target_json, requested_by, state, "
                         "created_at) VALUES (?, ?, 'stop', ?, ?, ?, 'pending_approval', ?)",
                         (pid, rid, target["host_id"], _json({"session": target["id"], "reason": reason}),
                          lease["session_id"], _iso(ctx.now)))
            self.store._event(conn, ctx, pid, "session_request", rid, "request", None, {"kind": "stop", "session": target["id"]})
            self._approval_note(conn, ctx, pid, rid, {"request": rid, "kind": "stop", "session": target["id"], "reason": reason})
            return {"request": {"id": rid, "state": "pending_approval", "kind": "stop"}}

    def decide(self, ctx: Ctx, a: dict[str, Any]) -> dict[str, Any]:
        p = self.orch._need_owner(ctx)
        pid = str(p.project_id)
        if a["decision"] not in ("approve", "reject"):
            raise invalid_field("decision", "approve · reject 중 하나")
        state = "approved" if a["decision"] == "approve" else "rejected"
        with self.store.write() as conn:
            row = conn.execute("SELECT * FROM session_request WHERE project_id = ? AND id = ?", (pid, a["request_id"])).fetchone()
            if row is None:
                raise not_found(f"요청이 없다: {a['request_id']}")
            if row["state"] != "pending_approval":
                raise HubError(409, "request_not_pending", f"이미 {row['state']} 인 요청이다", {"state": row["state"]})
            conn.execute("UPDATE session_request SET state = ?, decided_by = ?, decided_at = ?, version = version + 1 "
                         "WHERE project_id = ? AND id = ?", (state, p.callsign, _iso(ctx.now), pid, row["id"]))
            self.store._event(conn, ctx, pid, "session_request", row["id"], a["decision"], {"state": row["state"]},
                              {"state": state, "note": a.get("note") or ""})
            kind, to = self.orch._to_orchestrator(conn, ctx, pid)
            self.orch.enqueue(conn, ctx, pid, to_kind=kind, to_id=to, kind="note", ref_request=row["id"],
                              body={"event": f"request_{state}", "request": row["id"], "note": a.get("note") or ""},
                              from_callsign=str(p.callsign))
            return {"request": {"id": row["id"], "state": state}}

    # --- 중계가 부르는 쪽 (``/v1/relay/…``) ------------------------------------------------

    def poll_once(self, now: datetime, host: sqlite3.Row, a: dict[str, Any]) -> dict[str, Any]:
        """한 번 들여다보기 — 승인된 요청 · 중계 세션 앞 메시지 · 정지 상태. 내준 요청은 ``dispatched``."""
        ctx = Ctx(now=now, via="relay")
        projects = json.loads(host["projects_json"])
        digest = a.get("allow_digest")
        dispatch: list[dict[str, Any]] = []
        sessions: list[dict[str, Any]] = []
        halted: list[str] = []
        with self.store.write() as conn:
            conn.execute("UPDATE relay_host SET last_seen_at = ?, allow_digest = COALESCE(?, allow_digest) WHERE host_id = ?",
                         (_iso(now), digest if isinstance(digest, str) else None, host["host_id"]))
            for pid in projects:
                if self.orch._halted(conn, pid):
                    halted.append(pid)
                    continue
                for r in conn.execute("SELECT * FROM session_request WHERE project_id = ? AND host_id = ? AND state = 'approved' "
                                      "ORDER BY created_at, rowid", (pid, host["host_id"])).fetchall():
                    conn.execute("UPDATE session_request SET state = 'dispatched', version = version + 1 "
                                 "WHERE project_id = ? AND id = ?", (pid, r["id"]))
                    self.store._event(conn, ctx, pid, "session_request", r["id"], "dispatch", None, None, callsign="hub")
                    dispatch.append({"project_id": pid, "request": r["id"], "kind": r["kind"],
                                     "target": json.loads(r["target_json"])})
            rows = conn.execute("SELECT * FROM session WHERE host_id = ? AND status = 'active'", (host["host_id"],)).fetchall()
        reported = {s.get("session"): s.get("status") for s in (a.get("sessions") or []) if isinstance(s, dict)}
        for s in rows:
            principal = Principal(kind="callsign", project_id=s["project_id"], callsign=s["callsign"])
            sctx = Ctx(now=now, via="relay", principal=principal)
            if reported.get(s["id"]) == "ended":
                self.orch.end_session(sctx, s["id"])  # 중계가 본 프로세스 종료 (요구 R17.4)
                continue
            if reported.get(s["id"]) in ("idle", "busy"):
                with self.store.write() as conn:
                    conn.execute("UPDATE session SET last_signal_at = ? WHERE project_id = ? AND id = ?",
                                 (_iso(now), s["project_id"], s["id"]))
            msgs, remaining = self.orch.take(sctx, s["id"], "adapter")
            if msgs:
                sessions.append({"session": s["id"], "project_id": s["project_id"], "messages": msgs, "remaining": remaining})
        # 요청 ↔ 세션 대응 — 중계는 요청으로 띄운 프로세스를 세션 ID 로 찾는다 (세션 등록은 세션 자신, DO11)
        linked = []
        for s in rows:
            with self.store.read() as conn:
                r = conn.execute("SELECT id, result_json FROM session_request WHERE project_id = ? AND host_id = ? "
                                 "AND kind = 'spawn' AND json_extract(result_json, '$.session') = ?",
                                 (s["project_id"], host["host_id"], s["id"])).fetchone()
            if r is not None:
                linked.append({"session": s["id"], "request": r["id"], "project_id": s["project_id"]})
        return {"dispatch": dispatch, "deliver": sessions, "halted": halted, "sessions": linked}

    def result(self, now: datetime, host: sqlite3.Row, a: Any) -> dict[str, Any]:
        if not isinstance(a, dict) or set(a) - {"project_id", "request", "state", "result"}:
            raise HubError(400, "unknown_field", "project_id · request · state · result 만 받는다")
        if a.get("state") not in ("done", "refused_by_host", "failed"):
            raise invalid_field("state", "done · refused_by_host · failed 중 하나")
        scan_secrets(a.get("result"), "result")
        ctx = Ctx(now=now, via="relay")
        with self.store.write() as conn:
            row = conn.execute("SELECT * FROM session_request WHERE project_id = ? AND id = ? AND host_id = ?",
                               (a.get("project_id"), a.get("request"), host["host_id"])).fetchone()
            if row is None:
                raise not_found("이 중계 앞 요청이 아니다")
            if row["state"] != "dispatched":
                raise HubError(409, "request_not_dispatched", f"{row['state']} 인 요청이다", {"state": row["state"]})
            merged = {**json.loads(row["result_json"]), **(a.get("result") or {})}
            conn.execute("UPDATE session_request SET state = ?, result_json = ?, version = version + 1 "
                         "WHERE project_id = ? AND id = ?", (a["state"], _json(merged), row["project_id"], row["id"]))
            self.store._event(conn, ctx, row["project_id"], "session_request", row["id"], f"result:{a['state']}", None,
                              merged, callsign="hub")
            kind, to = self.orch._to_orchestrator(conn, ctx, row["project_id"])
            self.orch.enqueue(conn, ctx, row["project_id"], to_kind=kind, to_id=to, kind="note", ref_request=row["id"],
                              body={"event": f"request_{a['state']}", "request": row["id"], "result": merged},
                              from_callsign="hub")
        return {"request": row["id"], "state": a["state"]}

    def link_spawned(self, conn: sqlite3.Connection, ctx: Ctx, p: Principal, session_id: str, request_id: Any) -> None:
        """중계가 띄운 세션이 등록하며 실은 요청 ID — 세션을 그 중계에 묶는다 (DO11 — 등록은 세션 자신)."""
        if not isinstance(request_id, str):
            raise invalid_field("session.spawn_request", "SR-NNNN")
        row = conn.execute("SELECT * FROM session_request WHERE project_id = ? AND id = ? AND kind = 'spawn'",
                           (p.project_id, request_id)).fetchone()
        if row is None or row["state"] not in ("dispatched", "done"):
            raise HubError(409, "spawn_request_invalid", "실행 중인 세션 요청이 아니다", {"request": request_id})
        if json.loads(row["result_json"]).get("session"):
            raise HubError(409, "spawn_request_used", "이미 세션이 묶인 요청이다", {"request": request_id})
        conn.execute("UPDATE session SET host_id = ?, kind = 'worker', allow_wait = 1 WHERE project_id = ? AND id = ?",
                     (row["host_id"], p.project_id, session_id))
        conn.execute("UPDATE session_request SET result_json = ?, version = version + 1 WHERE project_id = ? AND id = ?",
                     (_json({**json.loads(row["result_json"]), "session": session_id}), p.project_id, request_id))
        self.store._event(conn, ctx, p.project_id, "session", session_id, "link_spawn", None,
                          {"request": request_id, "host": row["host_id"]})

    def revoke(self, ctx: Ctx, host_id: str) -> dict[str, Any]:
        p = self.orch._need_owner(ctx)
        with self.store.write() as conn:
            host = self._host_for(conn, str(p.project_id), host_id)
            if host["owner_callsign"] != p.callsign:
                raise forbidden("그 중계를 초대한 owner 만")
            conn.execute("UPDATE relay_host SET revoked_at = ? WHERE host_id = ?", (_iso(ctx.now), host_id))
            self.store._event(conn, ctx, p.project_id, "relay_host", host_id, "revoke", None, None)
        return {"host_id": host_id, "revoked": True}

