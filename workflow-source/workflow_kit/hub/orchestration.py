"""허브 오케스트레이션 — 세션 · 받은편지함 · 편승 · 대기 · 수신 확인 (``core/hub_orchestration_spec.md``, M-044).

규칙 (스펙 §1 · §6 · §7):
    - 2.0 저장 규칙 그대로 — 쓰기는 ``BEGIN IMMEDIATE`` 하나, 같은 트랜잭션에 ``event`` 한 줄, 시계는 호출자가 넘긴다.
    - 받은편지함이 정본이다. **실림은 소비가 아니다** (DO13) — 실린 메시지는 ack 전까지 60초마다 다시 실리고,
      처음 실린 지 10분 안에 ack 가 없으면 ``unacknowledged`` 다. 시간 판정은 호출 때 게으르게 한다 (DO7).
    - 세션 상태는 저장하지 않고 읽을 때 신호 시각에서 계산한다 — 재지 못하면 ``unknown`` (스펙 §7.1).
"""

from __future__ import annotations

import json
import re
import secrets
import sqlite3
from datetime import datetime, timedelta
from typing import Any

from workflow_kit.hub.errors import HubError, forbidden, invalid_field, not_found
from workflow_kit.hub.store import Ctx, Principal, Store, _iso, _json, scan_secrets

SESSION_ID = re.compile(r"^S-\d{8}-[0-9a-f]{8}$")
MESSAGE_ID = re.compile(r"^MSG-\d{8}-[0-9a-f]{12}$")
SESSION_KINDS = ("interactive", "worker")
MESSAGE_KINDS = ("assignment", "note", "release", "report", "approval")
ACK_DECISIONS = {"accept": "acked", "seen": "acked", "decline": "declined"}
#: 전달 경로 이름 (스펙 §6) — 세션이 ``delivery`` 로 알린다.
DELIVERY_PATHS = ("piggyback", "wait", "file", "adapter", "hook")

SIGNAL_STALE = timedelta(minutes=15)       # 상태 unknown (요구 R17.3)
REDELIVER_AFTER = timedelta(seconds=60)    # 실림 ≠ 소비 (DO13)
UNACK_AFTER = timedelta(minutes=10)        # 미확인 (요구 R18.8)
PIGGYBACK_MAX = 3                          # 편승 상한 (요구 R18.2 · Q4)
PIGGYBACK_BYTES = 8192
BODY_MAX = 8192
WAIT_CAP_S = 50                            # 대기 상한 — Claude Code HTTP MCP 가 약 60초에 끊는다 (스펙 §6.6)
WAIT_BUDGET = 70                           # 일 없이 연속 대기 (≈ 1시간, 스펙 §6.2)


def _ts(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value else None


def _new_id(prefix: str, now: datetime, nbytes: int) -> str:
    return f"{prefix}-{now.strftime('%Y%m%d')}-{secrets.token_hex(nbytes)}"


def _message_view(row: sqlite3.Row) -> dict[str, Any]:
    """편승 · 대기 · 목록이 함께 쓰는 메시지 꼴 (스펙 §6.1)."""
    out: dict[str, Any] = {
        "id": row["id"], "kind": row["kind"],
        "from": {"callsign": row["from_callsign"], "session": row["from_session"] or None,
                 "orchestrator": bool(row["from_orchestrator"])},
        "body": json.loads(row["body_json"]),
        "ack_with": "hub_inbox_ack",
    }
    if row["ref_task"]:
        out["task_id"] = row["ref_task"]
    if row["delivery_count"]:
        out["redelivery"] = True  # 같은 id 를 다시 받았다 — ack 는 멱등이다
    return out


class Orchestration:
    def __init__(self, store: Store) -> None:
        self.store = store

    # --- 공통 ------------------------------------------------------------------

    @staticmethod
    def _callsign(ctx: Ctx) -> Principal:
        p = ctx.principal
        if p is None or p.kind != "callsign" or not p.project_id or not p.callsign:
            raise forbidden("콜사인 토큰이 필요하다")
        return p

    @staticmethod
    def _session_row(conn: sqlite3.Connection, p: Principal, session_id: Any) -> sqlite3.Row:
        if not isinstance(session_id, str) or not SESSION_ID.match(session_id):
            raise invalid_field("session", "S-YYYYMMDD-xxxxxxxx 꼴이어야 한다")
        row: sqlite3.Row | None = conn.execute("SELECT * FROM session WHERE project_id = ? AND id = ?",
                                               (p.project_id, session_id)).fetchone()
        if row is None:
            raise not_found(f"세션이 없다: {session_id}")
        if row["callsign"] != p.callsign:
            raise HubError(403, "session_not_yours", "이 콜사인의 세션이 아니다", {"session": session_id})
        if row["status"] == "ended":
            raise HubError(410, "session_ended", "끝난 세션이다 — 세션 시작으로 새 세션을 연다", {"session": session_id})
        return row

    # --- 세션 (스펙 §4 · §7.1) ----------------------------------------------------

    def register(self, ctx: Ctx, spec: Any) -> dict[str, Any]:
        """``hub_session_start(session={…})`` — 세션을 만들거나 이어 붙인다 (스펙 §4-1)."""
        p = self._callsign(ctx)
        if not isinstance(spec, dict):
            raise invalid_field("session", "객체여야 한다")
        extra = set(spec) - {"harness", "harness_session_id", "kind", "delivery", "resume", "guide_version"}
        if extra:
            raise HubError(400, "unknown_field", f"모르는 필드: session.{', session.'.join(sorted(extra))}",
                           {"fields": sorted(f"session.{k}" for k in extra)})
        scan_secrets(spec, "session")
        harness = spec.get("harness")
        if not isinstance(harness, str) or not harness.strip():
            raise invalid_field("session.harness", "필수 (예: claude-code · codex)")
        hsid = spec.get("harness_session_id") or ""
        kind = spec.get("kind") or "interactive"
        if kind not in SESSION_KINDS:
            raise invalid_field("session.kind", f"{' · '.join(SESSION_KINDS)} 중 하나")
        delivery = spec.get("delivery") or ["piggyback"]
        if not isinstance(delivery, list) or not all(d in DELIVERY_PATHS for d in delivery):
            raise invalid_field("session.delivery", f"{' · '.join(DELIVERY_PATHS)} 의 목록")
        if not isinstance(hsid, str) or len(hsid) > 200:
            raise invalid_field("session.harness_session_id", "200자 이하 문자열")
        now = _iso(ctx.now)
        with self.store.write() as conn:
            row = None
            resume = spec.get("resume")
            if resume:
                row = self._session_row(conn, p, resume)
            elif hsid:
                row = conn.execute(
                    "SELECT * FROM session WHERE project_id = ? AND callsign = ? AND harness = ? AND harness_session_id = ? "
                    "AND status = 'active'", (p.project_id, p.callsign, harness, hsid)).fetchone()
            if row is not None:
                conn.execute(
                    "UPDATE session SET last_signal_at = ?, delivery_json = ?, guide_version = ?, idle_waits = 0, "
                    "waiting_since = NULL, version = version + 1 WHERE project_id = ? AND id = ?",
                    (now, _json(delivery), str(spec.get("guide_version") or row["guide_version"]), p.project_id, row["id"]))
                sid, resumed = row["id"], True
            else:
                sid, resumed = _new_id("S", ctx.now, 4), False
                allow_wait = 1 if kind == "worker" else 0  # Q1 — 사람이 보는 세션은 기본 꺼짐
                conn.execute(
                    "INSERT INTO session (project_id, id, callsign, harness, harness_session_id, kind, allow_wait, "
                    "delivery_json, guide_version, last_signal_at, started_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (p.project_id, sid, p.callsign, harness, hsid, kind, allow_wait, _json(delivery),
                     str(spec.get("guide_version") or ""), now, now))
            self.store._event(conn, ctx, p.project_id, "session", sid, "resume" if resumed else "start", None,
                              {"harness": harness, "kind": kind, "delivery": delivery})
            out = self._session_view(conn, ctx, conn.execute(
                "SELECT * FROM session WHERE project_id = ? AND id = ?", (p.project_id, sid)).fetchone())
        out["resumed"] = resumed
        return out

    def signal(self, ctx: Ctx, session_id: Any) -> None:
        """도구 호출에 실린 ``session`` — 그 세션의 신호 시각을 갱신한다 (스펙 §4-2). 대기 아닌 호출은 일하는 중이다."""
        p = self._callsign(ctx)
        with self.store.write() as conn:
            self._session_row(conn, p, session_id)
            conn.execute("UPDATE session SET last_signal_at = ?, idle_waits = 0 WHERE project_id = ? AND id = ?",
                         (_iso(ctx.now), p.project_id, session_id))

    def _session_view(self, conn: sqlite3.Connection, ctx: Ctx, row: sqlite3.Row) -> dict[str, Any]:
        open_n = conn.execute(
            "SELECT COUNT(*) FROM assignment WHERE project_id = ? AND session_id = ? AND state IN ('offered', 'accepted')",
            (row["project_id"], row["id"])).fetchone()[0]
        return {
            "id": row["id"], "callsign": row["callsign"], "harness": row["harness"],
            "harness_session_id": row["harness_session_id"] or None, "kind": row["kind"],
            "allow_wait": bool(row["allow_wait"]), "delivery": json.loads(row["delivery_json"]),
            "status": self.status(row, ctx.now, open_n), "last_signal_at": row["last_signal_at"],
            "open_assignments": open_n, "started_at": row["started_at"],
        }

    @staticmethod
    def status(row: sqlite3.Row, now: datetime, open_assignments: int) -> str:
        """스펙 §7.1 — 위에서부터 먼저. 신호가 15분을 넘으면 ``unknown`` (``idle`` 로 세지 않는다)."""
        if row["status"] == "ended":
            return "ended"
        if row["waiting_since"]:
            return "waiting"
        last = _ts(row["last_signal_at"])
        if last is None or now - last > SIGNAL_STALE:
            return "unknown"
        return "working" if open_assignments else "idle"

    def session_update(self, ctx: Ctx, a: dict[str, Any]) -> dict[str, Any]:
        p = self._callsign(ctx)
        values = {k: a[k] for k in ("kind", "allow_wait", "delivery", "harness_session_id") if k in a}
        if not values:
            raise invalid_field("session", "고칠 칸이 없다 (kind · allow_wait · delivery · harness_session_id)")
        if "kind" in values and values["kind"] not in SESSION_KINDS:
            raise invalid_field("kind", f"{' · '.join(SESSION_KINDS)} 중 하나")
        if "delivery" in values and (not isinstance(values["delivery"], list)
                                     or not all(d in DELIVERY_PATHS for d in values["delivery"])):
            raise invalid_field("delivery", f"{' · '.join(DELIVERY_PATHS)} 의 목록")
        # 대기 켜기는 사람만 (Q1) — 에이전트 세션이 스스로 턴을 붙잡게 하지 않는다.
        if values.get("allow_wait") is True and not (p.callsign_kind == "human" and p.human_approved):
            raise forbidden("대기 도구 켜기는 승인된 human 콜사인만 — 일하는 세션은 kind=worker 로 시작한다")
        scan_secrets(values)
        with self.store.write() as conn:
            row = self._session_row(conn, p, a["session"])
            before = {k: row[k] for k in ("kind", "allow_wait", "delivery_json", "harness_session_id")}
            sets = {"kind": values.get("kind", row["kind"]),
                    "allow_wait": int(values.get("allow_wait", bool(row["allow_wait"]))),
                    "delivery_json": _json(values["delivery"]) if "delivery" in values else row["delivery_json"],
                    "harness_session_id": values.get("harness_session_id", row["harness_session_id"])}
            conn.execute("UPDATE session SET kind = ?, allow_wait = ?, delivery_json = ?, harness_session_id = ?, "
                         "last_signal_at = ?, version = version + 1 WHERE project_id = ? AND id = ?",
                         (sets["kind"], sets["allow_wait"], sets["delivery_json"], sets["harness_session_id"],
                          _iso(ctx.now), p.project_id, a["session"]))
            self.store._event(conn, ctx, p.project_id, "session", a["session"], "update", before, sets)
            return {"session": self._session_view(conn, ctx, conn.execute(
                "SELECT * FROM session WHERE project_id = ? AND id = ?", (p.project_id, a["session"])).fetchone())}

    def session_list(self, ctx: Ctx, a: dict[str, Any]) -> dict[str, Any]:
        p = self.store._need_reader(ctx)
        with self.store.read() as conn:
            q, args = "SELECT * FROM session WHERE project_id = ?", [p.project_id]
            if a.get("callsign"):
                q, args = q + " AND callsign = ?", [*args, a["callsign"]]
            rows = conn.execute(q + " ORDER BY started_at, id", args).fetchall()
            views = [self._session_view(conn, ctx, r) for r in rows]
        if a.get("status"):
            views = [v for v in views if v["status"] == a["status"]]
        counts: dict[str, int] = {}
        for v in views:
            counts[v["status"]] = counts.get(v["status"], 0) + 1
        # unknown 은 따로 센다 — idle 로 섞지 않는다 (요구 R17.3)
        return {"sessions": views, "counts": counts, "unknown": counts.get("unknown", 0)}

    # --- 받은편지함 (스펙 §6.1 · §8) ---------------------------------------------

    def enqueue(self, conn: sqlite3.Connection, ctx: Ctx, project_id: str, *, to_kind: str, to_id: str, kind: str,
                body: Any, from_callsign: str, from_session: str = "", from_orchestrator: bool = False,
                ref_task: str = "", ref_request: str = "") -> str:
        """메시지 한 건을 쌓는다 — 같은 트랜잭션 안에서 부른다 (배정 · 보고가 함께 쓰므로)."""
        if to_kind not in ("session", "callsign") or kind not in MESSAGE_KINDS:
            raise invalid_field("to/kind", "모르는 주소 종류 · 메시지 종류")
        scan_secrets(body, "body")
        raw = _json(body)
        if len(raw.encode("utf-8")) > BODY_MAX:
            raise HubError(413, "payload_too_large", f"메시지 본문 상한 {BODY_MAX} 바이트", {"limit": BODY_MAX})
        mid = _new_id("MSG", ctx.now, 6)
        conn.execute(
            "INSERT INTO inbox_message (project_id, id, to_kind, to_id, from_callsign, from_session, from_orchestrator, "
            "kind, body_json, ref_task, ref_request, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (project_id, mid, to_kind, to_id, from_callsign, from_session, int(from_orchestrator), kind, raw,
             ref_task, ref_request, _iso(ctx.now)))
        self.store._event(conn, ctx, project_id, "inbox_message", mid, "enqueue", None,
                          {"to": f"{to_kind}:{to_id}", "kind": kind}, callsign=from_callsign)
        return mid

    def _expire(self, conn: sqlite3.Connection, ctx: Ctx, project_id: str) -> None:
        """처음 실린 지 10분 넘게 ack 가 없는 메시지 → ``unacknowledged`` (요구 R18.8, 게으른 판정 DO7)."""
        cutoff = _iso(ctx.now - UNACK_AFTER)
        rows = conn.execute("SELECT id FROM inbox_message WHERE project_id = ? AND state = 'delivered' AND delivered_at <= ?",
                            (project_id, cutoff)).fetchall()
        for r in rows:
            conn.execute("UPDATE inbox_message SET state = 'unacknowledged', version = version + 1 "
                         "WHERE project_id = ? AND id = ?", (project_id, r["id"]))
            self.store._event(conn, ctx, project_id, "inbox_message", r["id"], "unacknowledged", None, None, callsign="hub")

    def _eligible(self, conn: sqlite3.Connection, ctx: Ctx, p: Principal, session_id: str | None) -> list[sqlite3.Row]:
        redeliver = _iso(ctx.now - REDELIVER_AFTER)
        targets = [("callsign", p.callsign)] + ([("session", session_id)] if session_id else [])
        where = " OR ".join("(to_kind = ? AND to_id = ?)" for _ in targets)
        args: list[Any] = [p.project_id]
        for t in targets:
            args.extend(t)
        return list(conn.execute(
            f"SELECT * FROM inbox_message WHERE project_id = ? AND ({where}) "
            "AND (state = 'queued' OR (state = 'delivered' AND last_delivered_at <= ?)) ORDER BY created_at, rowid",
            [*args, redeliver]).fetchall())

    def take(self, ctx: Ctx, session_id: str | None, via: str) -> tuple[list[dict[str, Any]], int]:
        """수신자에게 실을 메시지를 고르고 ``delivered`` 로 표시한다 — 소비가 아니다 (DO13)."""
        p = self._callsign(ctx)
        assert p.project_id is not None
        with self.store.write() as conn:
            self._expire(conn, ctx, p.project_id)
            rows = self._eligible(conn, ctx, p, session_id)
            picked: list[dict[str, Any]] = []
            size = 0
            for r in rows:
                view = _message_view(r)
                n = len(_json(view).encode("utf-8"))
                if len(picked) >= PIGGYBACK_MAX or (picked and size + n > PIGGYBACK_BYTES):
                    break
                picked.append(view)
                size += n
                conn.execute(
                    "UPDATE inbox_message SET state = 'delivered', delivered_via = ?, delivered_at = COALESCE(delivered_at, ?), "
                    "last_delivered_at = ?, delivery_count = delivery_count + 1, version = version + 1 "
                    "WHERE project_id = ? AND id = ?", (via, _iso(ctx.now), _iso(ctx.now), p.project_id, r["id"]))
            return picked, len(rows) - len(picked)

    def attach(self, ctx: Ctx, session_id: str | None, result: dict[str, Any]) -> dict[str, Any]:
        """편승 (M1, 스펙 §6.1) — 실을 것이 없으면 칸을 붙이지 않는다 (2.0 응답과 같은 바이트, DO5)."""
        msgs, remaining = self.take(ctx, session_id, "piggyback")
        if not msgs:
            return result
        return {**result, "hub_inbox": {"for_session": session_id, "messages": msgs, "remaining": remaining}}

    def ack(self, ctx: Ctx, a: dict[str, Any]) -> dict[str, Any]:
        p = self._callsign(ctx)
        decision = a["decision"]
        if decision not in ACK_DECISIONS:
            raise invalid_field("decision", "accept · decline · seen 중 하나")
        if not isinstance(a["message_id"], str) or not MESSAGE_ID.match(a["message_id"]):
            raise invalid_field("message_id", "MSG-YYYYMMDD-xxxxxxxxxxxx 꼴이어야 한다")
        reason = a.get("reason") or ""
        scan_secrets(reason, "reason")
        target = ACK_DECISIONS[decision]

        def do(conn: sqlite3.Connection) -> dict[str, Any]:
            self._session_row(conn, p, a["session"])
            m = conn.execute("SELECT * FROM inbox_message WHERE project_id = ? AND id = ?",
                             (p.project_id, a["message_id"])).fetchone()
            if m is None:
                raise not_found(f"메시지가 없다: {a['message_id']}")
            mine = (m["to_kind"] == "session" and m["to_id"] == a["session"]) or \
                   (m["to_kind"] == "callsign" and m["to_id"] == p.callsign)
            if not mine:
                raise HubError(403, "message_not_yours", "이 세션 · 콜사인 앞 메시지가 아니다")
            if m["state"] in ("acked", "declined"):
                if m["state"] == target and m["ack_by_session"] == a["session"]:
                    return {"message_id": m["id"], "state": m["state"], "unchanged": True}  # 멱등 (DO13)
                raise HubError(409, "already_acked", "이미 확인한 메시지다",
                               {"state": m["state"], "by_session": m["ack_by_session"]})
            if m["state"] in ("unacknowledged", "expired"):
                raise HubError(409, "ack_too_late", "확인 상한(10분)이 지나 오케스트레이터에게 되돌아간 메시지다",
                               {"state": m["state"]})
            conn.execute("UPDATE inbox_message SET state = ?, acked_at = ?, ack_by_session = ?, ack_reason = ?, "
                         "version = version + 1 WHERE project_id = ? AND id = ?",
                         (target, _iso(ctx.now), a["session"], reason, p.project_id, m["id"]))
            conn.execute("UPDATE session SET last_signal_at = ?, idle_waits = 0 WHERE project_id = ? AND id = ?",
                         (_iso(ctx.now), p.project_id, a["session"]))
            self.store._event(conn, ctx, p.project_id, "inbox_message", m["id"], f"ack:{decision}",
                              {"state": m["state"]}, {"state": target, "reason": reason})
            return {"message_id": m["id"], "state": target}

        return self.store.idempotent(ctx, a.get("request_id"), do)

    def inbox_list(self, ctx: Ctx, a: dict[str, Any]) -> dict[str, Any]:
        """받은편지함 읽기 — 상태를 바꾸지 않는다 (편승을 못 받는 경로의 보조, 스펙 §5)."""
        p = self._callsign(ctx)
        with self.store.read() as conn:
            sid = a.get("session")
            if sid:
                self._session_row(conn, p, sid)
            targets = [("callsign", p.callsign)] + ([("session", sid)] if sid else [])
            where = " OR ".join("(to_kind = ? AND to_id = ?)" for _ in targets)
            args: list[Any] = [p.project_id]
            for t in targets:
                args.extend(t)
            q = f"SELECT * FROM inbox_message WHERE project_id = ? AND ({where})"
            if a.get("state"):
                q, args = q + " AND state = ?", [*args, a["state"]]
            rows = conn.execute(q + " ORDER BY created_at, rowid", args).fetchall()
        return {"messages": [{**_message_view(r), "state": r["state"], "delivered_via": r["delivered_via"] or None}
                             for r in rows]}

    # --- 대기 (스펙 §6.2) ------------------------------------------------------------

    def wait_poll(self, ctx: Ctx, session_id: Any, *, first: bool) -> dict[str, Any] | None:
        """대기 한 번 들여다보기 — 일이 있으면 응답 꼴, 없으면 None (대기 상태 표시). 막지 않는다."""
        p = self._callsign(ctx)
        with self.store.write() as conn:
            row = self._session_row(conn, p, session_id)
            if not row["allow_wait"]:
                raise HubError(409, "wait_disabled",
                               "이 세션은 대기 도구가 꺼져 있다 — 사람이 보는 세션은 편승(M1)만 쓴다 (Q1). "
                               "일하는 세션은 kind=worker 로 시작한다", {"session": session_id})
            if first and row["idle_waits"] >= WAIT_BUDGET:
                raise HubError(409, "wait_budget", f"일 없이 {WAIT_BUDGET}번 연속 기다렸다 — 턴을 끝낸다",
                               {"session": session_id, "idle_waits": row["idle_waits"]})
            conn.execute("UPDATE session SET waiting_since = COALESCE(waiting_since, ?), last_signal_at = ? "
                         "WHERE project_id = ? AND id = ?", (_iso(ctx.now), _iso(ctx.now), p.project_id, session_id))
        msgs, remaining = self.take(ctx, session_id, "wait")
        if not msgs:
            return None
        with self.store.write() as conn:
            conn.execute("UPDATE session SET waiting_since = NULL, idle_waits = 0 WHERE project_id = ? AND id = ?",
                         (p.project_id, session_id))
        return {"work": msgs, "remaining": remaining, "call_again": False}

    def wait_timeout(self, ctx: Ctx, session_id: str, waited_s: int) -> dict[str, Any]:
        """대기 상한에 닿음 — 빈 응답 + 다시 부르라 (스펙 §6.2)."""
        p = self._callsign(ctx)
        with self.store.write() as conn:
            conn.execute("UPDATE session SET waiting_since = NULL, idle_waits = idle_waits + 1, last_signal_at = ? "
                         "WHERE project_id = ? AND id = ?", (_iso(ctx.now), p.project_id, session_id))
        return {"work": [], "call_again": True, "waited_s": waited_s,
                "note": "일이 아직 없다 — hub_wait 를 다시 부른다 (release 를 받으면 턴을 끝낸다)"}

    def wait_clear(self, ctx: Ctx, session_id: str) -> None:
        """끊긴 대기 — '대기 중' 표시만 지운다 (세는 것 없음)."""
        p = self._callsign(ctx)
        with self.store.write() as conn:
            conn.execute("UPDATE session SET waiting_since = NULL WHERE project_id = ? AND id = ?",
                         (p.project_id, session_id))
