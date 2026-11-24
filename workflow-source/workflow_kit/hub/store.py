"""허브 저장 계층 — 등록 · 콜사인 · 토큰 · task · 이력 (hub_spec §3, M-033).

규칙 (hub_spec §3.1):
    - 쓰기는 ``BEGIN IMMEDIATE`` 트랜잭션 하나, 같은 트랜잭션에서 ``event`` 한 줄.
    - 고칠 수 있는 레코드는 ``expected_version`` 이 다르면 409 — 자동 병합하지 않는다.
    - ``request_id`` 가 같은 쓰기를 두 번 받으면 처음 결과를 돌려주고 다시 쓰지 않는다.
    - 시각은 호출자가 정해 넘긴다 — 이 모듈은 시계를 읽지 않는다 (hub_spec §1-7).
    - 토큰 원문은 저장하지 않는다 (sha256 만).
"""

from __future__ import annotations

import hashlib
import json
import re
import secrets
import sqlite3
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from workflow_kit.hub import db as hubdb
from workflow_kit.hub import gitkey
from workflow_kit.hub.errors import (
    HubError,
    forbidden,
    invalid_field,
    not_found,
    version_conflict,
)

CALLSIGN_PATTERN = re.compile(r"^[a-z][a-z0-9-]{1,30}[a-z0-9]$")
RESERVED_CALLSIGNS = frozenset({"hub"})
TOKEN_PREFIX = "wfh_"
#: 토큰 모양 — 기록에 실리면 거절한다 (hub_spec §1-4, 요구 R0.5).
TOKEN_SHAPE = re.compile(r"wfh_[A-Za-z0-9_-]{20,}")
STATUSES = ("planned", "in_progress", "blocked", "done")
PRIORITIES = ("high", "medium", "low")
TITLE_MAX = 200
SHA_PATTERN = re.compile(r"^[0-9a-f]{7,40}$")
#: task 의 ``fields_json`` 이 받는 칸 (1.x task 파일의 Description 칸 — hub_spec §3.3 DS2).
TASK_FIELD_KEYS = frozenset({
    "affected_documents", "done_criteria", "result", "risks", "follow_up", "validation_result", "next_step",
    "category", "tests",
})


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def new_token() -> str:
    return TOKEN_PREFIX + secrets.token_urlsafe(32)


@dataclass(frozen=True)
class Principal:
    """요청한 쪽. ``kind`` = ``callsign`` (프로젝트 범위) · ``web`` · ``admin`` (허브 토큰) · ``viewer``.

    ``viewer`` 는 화면(``hub/ui.py``)이 읽기 권한을 확인한 뒤 한 프로젝트로 좁혀 만드는 읽기 전용 주체다 —
    도구 입구(:func:`workflow_kit.hub.tools.call`)는 받지 않고, 읽기 함수(:meth:`Store._need_reader`)만 받는다.
    """

    kind: str
    project_id: str | None = None
    callsign: str | None = None
    callsign_kind: str | None = None
    human_approved: bool = False
    role: str | None = None
    name: str | None = None


@dataclass(frozen=True)
class Ctx:
    """도구 호출 문맥 — 시각과 경로는 앱이 한 번 정한다."""

    now: datetime
    via: str
    principal: Principal | None = None
    client_version: str | None = None
    #: 허브의 공개 주소 (hub_spec §2.1) — 셋업 지시 · 안내가 이 값에서 나온다.
    public_url: str = ""


def _iso(now: datetime) -> str:
    return now.isoformat()


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def scan_secrets(value: Any, path: str = "") -> None:
    """토큰 모양의 문자열이 있으면 거절한다 (요구 R0.5)."""
    if isinstance(value, str):
        if TOKEN_SHAPE.search(value):
            raise HubError(400, "secret_in_payload", f"토큰으로 보이는 문자열이 있다: {path or '값'}", {"field": path})
    elif isinstance(value, dict):
        for k, v in value.items():
            scan_secrets(v, f"{path}.{k}" if path else str(k))
    elif isinstance(value, list):
        for i, v in enumerate(value):
            scan_secrets(v, f"{path}[{i}]")


class Store:
    def __init__(self, path: Path) -> None:
        self.path = path

    # --- 연결 · 트랜잭션 ----------------------------------------------------------

    @contextmanager
    def read(self) -> Iterator[sqlite3.Connection]:
        conn = hubdb.connect(self.path)
        try:
            yield conn
        finally:
            conn.close()

    @contextmanager
    def write(self) -> Iterator[sqlite3.Connection]:
        conn = hubdb.connect(self.path)
        try:
            conn.execute("BEGIN IMMEDIATE")
            try:
                yield conn
            except BaseException:
                conn.execute("ROLLBACK")
                raise
            conn.execute("COMMIT")
        finally:
            conn.close()

    def db_version(self) -> int:
        with self.read() as conn:
            return hubdb.schema_version(conn)

    @staticmethod
    def _event(conn: sqlite3.Connection, ctx: Ctx, project_id: str | None, target_kind: str, target_id: str,
               op: str, before: Any, after: Any, callsign: str | None = None) -> None:
        who = callsign if callsign is not None else (ctx.principal.callsign if ctx.principal else None)
        conn.execute(
            "INSERT INTO event (project_id, at, callsign, target_kind, target_id, op, before_json, after_json, via, client_version) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (project_id, _iso(ctx.now), who, target_kind, target_id, op,
             None if before is None else _json(before), None if after is None else _json(after),
             ctx.via, ctx.client_version),
        )

    def idempotent(self, ctx: Ctx, request_id: str | None, fn: Callable[[sqlite3.Connection], dict[str, Any]]) -> dict[str, Any]:
        """``request_id`` 멱등 쓰기 (hub_spec §3.1). 콜사인 요청에만 쓴다."""
        p = ctx.principal
        with self.write() as conn:
            if request_id and p and p.project_id and p.callsign:
                row = conn.execute(
                    "SELECT result_json FROM applied_request WHERE project_id = ? AND callsign = ? AND request_id = ?",
                    (p.project_id, p.callsign, request_id),
                ).fetchone()
                if row:
                    result: dict[str, Any] = json.loads(row["result_json"])
                    result["replayed"] = True
                    return result
            result = fn(conn)
            if request_id and p and p.project_id and p.callsign:
                conn.execute(
                    "INSERT INTO applied_request (project_id, callsign, request_id, result_json, at) VALUES (?, ?, ?, ?, ?)",
                    (p.project_id, p.callsign, request_id, _json(result), _iso(ctx.now)),
                )
            return result

    # --- 인증 ---------------------------------------------------------------------

    def authenticate(self, token: str | None, now: datetime | None = None,
                     client_version: str | None = None) -> Principal | None:
        """토큰 → 주체. ``now`` 가 있으면 콜사인의 마지막 활동을, ``client_version`` (``X-Hub-Client`` 머리)이 있으면
        받은 클라이언트 판을 적는다 (요구 R4.7 · R7.8 — 화면의 '마지막 활동' · 환경 판)."""
        if not token:
            return None
        h = hash_token(token)
        with self.read() as conn:
            row = conn.execute(
                "SELECT project_id, id, kind, human_approved, role FROM callsign WHERE token_hash = ? AND revoked_at IS NULL",
                (h,),
            ).fetchone()
            if row:
                if now is not None:
                    conn.execute(
                        "UPDATE callsign SET last_seen_at = ? WHERE project_id = ? AND id = ?",
                        (_iso(now), row["project_id"], row["id"]),
                    )
                if client_version:
                    conn.execute(
                        "UPDATE callsign SET client_version_seen = ? WHERE project_id = ? AND id = ?",
                        (client_version[:80], row["project_id"], row["id"]),
                    )
                return Principal(
                    kind="callsign", project_id=row["project_id"], callsign=row["id"],
                    callsign_kind=row["kind"], human_approved=bool(row["human_approved"]), role=row["role"],
                )
            hub = conn.execute(
                "SELECT role, name FROM hub_token WHERE token_hash = ? AND revoked_at IS NULL", (h,)
            ).fetchone()
            if hub:
                return Principal(kind=hub["role"], name=hub["name"])
        return None

    def web_principal(self, name: str) -> Principal | None:
        """화면 공용 ``web`` 토큰 (요구 R13.2a) — ``hub serve --web-token-name`` 이 켠 이름. 거두면 즉시 꺼진다."""
        with self.read() as conn:
            row = conn.execute(
                "SELECT name FROM hub_token WHERE name = ? AND role = 'web' AND revoked_at IS NULL", (name,)
            ).fetchone()
        return Principal(kind="web", name=row["name"]) if row else None

    def projects(self, project_id: str | None = None) -> list[dict[str, Any]]:
        """프로젝트 목록 (화면) — ``project_id`` 를 주면 그 하나로 좁힌다. status 별 task 수를 싣는다."""
        sql = "SELECT id, display_name, owner_callsign, created_at FROM project"
        args: list[Any] = []
        if project_id is not None:
            sql += " WHERE id = ?"
            args.append(project_id)
        out = []
        with self.read() as conn:
            for r in conn.execute(sql + " ORDER BY created_at, id", args):
                d = dict(r)
                d["task_counts"] = {row["status"]: row["n"] for row in conn.execute(
                    "SELECT status, COUNT(*) AS n FROM task WHERE project_id = ? GROUP BY status", (d["id"],))}
                out.append(d)
        return out

    def issue_hub_token(self, role: str, name: str, now: datetime) -> str:
        if role not in ("web", "admin"):
            raise invalid_field("role", "web · admin 가운데 하나")
        token = new_token()
        with self.write() as conn:
            if conn.execute("SELECT 1 FROM hub_token WHERE name = ?", (name,)).fetchone():
                raise HubError(409, "token_name_taken", f"이미 쓰는 토큰 이름이다: {name}")
            conn.execute(
                "INSERT INTO hub_token (token_hash, role, name, created_at) VALUES (?, ?, ?, ?)",
                (hash_token(token), role, name, _iso(now)),
            )
            self._event(conn, Ctx(now=now, via="admin"), None, "hub_token", name, "issue", None, {"role": role}, "hub")
        return token

    def revoke_hub_token(self, name: str, now: datetime) -> None:
        with self.write() as conn:
            cur = conn.execute(
                "UPDATE hub_token SET revoked_at = ? WHERE name = ? AND revoked_at IS NULL", (_iso(now), name)
            )
            if cur.rowcount == 0:
                raise not_found(f"거둘 토큰이 없다: {name}")
            self._event(conn, Ctx(now=now, via="admin"), None, "hub_token", name, "revoke", None, None, "hub")

    # --- 프로젝트 · 콜사인 (WBS-33.2) ---------------------------------------------

    def project_moved(self, project_id: str | None) -> str | None:
        """봉인된(다른 허브로 옮긴) 프로젝트면 새 주소 (M-039 WBS-39.4)."""
        if not project_id:
            return None
        from workflow_kit.hub.transfer import moved_to  # noqa: PLC0415

        with self.read() as conn:
            return moved_to(conn, project_id)

    def lookup_project(self, remote_url: str) -> dict[str, Any]:
        key = gitkey.normalize(remote_url)
        with self.read() as conn:
            row = conn.execute(
                "SELECT p.id, p.display_name FROM project_alias a JOIN project p ON p.id = a.project_id WHERE a.key = ?",
                (key,),
            ).fetchone()
        if not row:
            return {"key": key, "project_id": None, "display_name": None}
        out = {"key": key, "project_id": row["id"], "display_name": row["display_name"]}
        to = self.project_moved(row["id"])
        if to:  # 옮긴 프로젝트 — 조회는 거절하지 않고 새 주소를 알린다 (부트스트랩이 새 허브로 가게)
            out["moved_to"] = to
        return out

    @staticmethod
    def _check_callsign(callsign: str, kind: str) -> None:
        if callsign in RESERVED_CALLSIGNS:
            raise invalid_field("callsign", f"예약한 이름이다: {callsign!r}")
        if not CALLSIGN_PATTERN.match(callsign):
            raise invalid_field("callsign", "소문자 · 숫자 · '-' 3~32 자, 글자로 시작하고 '-' 로 끝나지 않는다 (예: claude-macmini)")
        if kind not in ("human", "agent"):
            raise invalid_field("kind", "human · agent 가운데 하나")

    def register_project(self, ctx: Ctx, remote_url: str, display_name: str, callsign: str, kind: str,
                         label: str = "", host: str = "") -> dict[str, Any]:
        # 원격이 없는 저장소 (소유자 2026-11-21 '로컬 키 발급 · 나중에 묶기') — 허브가 로컬 키를 낸다. 원격이 생기면
        # 소유자가 hub_project_bind_remote 로 묶는다. 그 전에는 주소 조회로 찾을 수 없어 다른 환경은 합류할 수 없다.
        local = not (remote_url or "").strip()
        key = gitkey.local_key() if local else gitkey.normalize(remote_url)
        self._check_callsign(callsign, kind)
        if not display_name.strip():
            raise invalid_field("display_name", "비었다")
        token = new_token()
        project_id = f"P-{ctx.now.strftime('%Y%m%d')}-{secrets.token_hex(4)}"
        with self.write() as conn:
            existing = conn.execute("SELECT project_id FROM project_alias WHERE key = ?", (key,)).fetchone()
            if existing:
                raise HubError(409, "project_exists", "이미 등록된 프로젝트다 — hub_callsign_register 로 합류한다",
                               {"project_id": existing["project_id"], "key": key})
            conn.execute(
                "INSERT INTO project (id, display_name, owner_callsign, created_at) VALUES (?, ?, ?, ?)",
                (project_id, display_name.strip(), callsign, _iso(ctx.now)),
            )
            conn.execute(
                "INSERT INTO project_alias (key, project_id, kind, added_by, added_at) VALUES (?, ?, 'primary', ?, ?)",
                (key, project_id, callsign, _iso(ctx.now)),
            )
            # 등록자 = 소유자. 첫 콜사인은 소유자이므로 human 이 바로 선다 (Q3).
            conn.execute(
                "INSERT INTO callsign (project_id, id, kind, human_approved, role, label, host, token_hash, created_at) "
                "VALUES (?, ?, ?, ?, 'owner', ?, ?, ?, ?)",
                (project_id, callsign, kind, 1 if kind == "human" else 0, label, host, hash_token(token), _iso(ctx.now)),
            )
            self._event(conn, ctx, project_id, "project", project_id, "register", None,
                        {"key": key, "display_name": display_name.strip(), "owner": callsign}, callsign)
            self._event(conn, ctx, project_id, "callsign", callsign, "register", None,
                        {"kind": kind, "role": "owner"}, callsign)
        out: dict[str, Any] = {"project_id": project_id, "key": key, "callsign": callsign, "role": "owner", "token": token}
        if local:
            out["local_key"] = True
            out["next"] = ("원격이 없어 로컬 키로 등록했다 — 주소 조회로는 찾을 수 없다. git 원격을 만든 뒤 "
                           "hub_project_bind_remote(remote_url) 로 묶어야 다른 환경이 합류한다")
        return out

    def bind_remote(self, ctx: Ctx, remote_url: str) -> dict[str, Any]:
        """프로젝트에 git 원격 주소를 묶는다 (별칭 키) — 원격 없이 등록한 프로젝트 · 같은 저장소의 다른 표기.

        승인된 human 소유자만. 이미 이 프로젝트의 키면 그대로 (already), 다른 프로젝트의 키면 409 ``alias_taken``.
        """
        p = self._need_callsign(ctx)
        if p.role != "owner" or p.callsign_kind != "human" or not p.human_approved:
            raise forbidden("원격 묶기는 승인된 human 소유자만 한다")
        key = gitkey.normalize(remote_url)
        with self.write() as conn:
            row = conn.execute("SELECT project_id FROM project_alias WHERE key = ?", (key,)).fetchone()
            if row and row["project_id"] == p.project_id:
                return {"project_id": p.project_id, "key": key, "already": True}
            if row:
                raise HubError(409, "alias_taken",
                               "다른 프로젝트가 이 저장소 주소로 등록돼 있다 — 묶지 않는다. 두 프로젝트를 합치는 길은 없다: "
                               "사람이 어느 쪽을 쓸지 정한다", {"key": key})
            conn.execute(
                "INSERT INTO project_alias (key, project_id, kind, added_by, added_at) VALUES (?, ?, 'alias', ?, ?)",
                (key, p.project_id, p.callsign, _iso(ctx.now)),
            )
            self._event(conn, ctx, p.project_id, "project", p.project_id or "", "bind_remote", None, {"key": key}, p.callsign)
        return {"project_id": p.project_id, "key": key, "already": False}

    def register_callsign(self, ctx: Ctx, project_id: str, callsign: str, kind: str,
                          label: str = "", host: str = "") -> dict[str, Any]:
        self._check_callsign(callsign, kind)
        token = new_token()
        with self.write() as conn:
            if not conn.execute("SELECT 1 FROM project WHERE id = ?", (project_id,)).fetchone():
                raise not_found(f"프로젝트가 없다: {project_id}")
            row = conn.execute(
                "SELECT revoked_at FROM callsign WHERE project_id = ? AND id = ?", (project_id, callsign)
            ).fetchone()
            if row and row["revoked_at"] is None:
                raise HubError(409, "callsign_taken",
                               f"이미 쓰는 콜사인이다: {callsign} — 그 환경의 .workflow-hub/env 를 찾거나 다른 이름을 쓴다",
                               {"callsign": callsign})
            if row:
                # 거둔 콜사인의 기록(handoff · 계정 연결)을 새 등록자가 이어받지 않는다
                for table in ("handoff", "hub_account_callsign"):
                    if conn.execute(f"SELECT 1 FROM {table} WHERE project_id = ? AND callsign = ?", (project_id, callsign)).fetchone():
                        raise HubError(409, "callsign_taken", f"기록이 남은 거둔 콜사인이다: {callsign} — 다른 이름을 쓴다",
                                       {"callsign": callsign})
                conn.execute("DELETE FROM setup_step WHERE project_id = ? AND callsign = ?", (project_id, callsign))
                conn.execute("DELETE FROM callsign WHERE project_id = ? AND id = ?", (project_id, callsign))
            conn.execute(
                "INSERT INTO callsign (project_id, id, kind, human_approved, role, label, host, token_hash, created_at) "
                "VALUES (?, ?, ?, 0, 'editor', ?, ?, ?, ?)",
                (project_id, callsign, kind, label, host, hash_token(token), _iso(ctx.now)),
            )
            self._event(conn, ctx, project_id, "callsign", callsign, "register", None,
                        {"kind": kind, "role": "editor"}, callsign)
        return {"project_id": project_id, "callsign": callsign, "role": "editor", "token": token,
                "human_pending": kind == "human"}

    def callsign_board(self, project_id: str) -> dict[str, Any]:
        """콜사인 표 (화면, 요구 R4.7 · R7.8 · R5.7) — 마지막 활동 · 받은 지침 판 · 클라이언트 판 · 맡은 열린 task.

        지침 판 비교는 세션 시작이 쓰는 :func:`render.guide_version` 과 같은 값이다. 아직 한 번도 받지 않은
        콜사인(``guide_version_seen`` 비어 있음)은 '옛 지침' 이 아니라 '받은 적 없음' 이다.
        """
        from workflow_kit.hub import render

        with self.read() as conn:
            row = conn.execute("SELECT MAX(version) AS v FROM guide WHERE project_id = ?", (project_id,)).fetchone()
            current = render.guide_version(row["v"] or 0)
            open_tasks: dict[str, list[dict[str, Any]]] = {}
            for t in conn.execute(
                "SELECT assignee, id, title, status, progress_note, progress_at, updated_at FROM task "
                "WHERE project_id = ? AND assignee IS NOT NULL AND status != 'done' ORDER BY updated_at DESC, id",
                (project_id,),
            ):
                task = dict(t)
                open_tasks.setdefault(task.pop("assignee"), []).append(task)
            handoffs = {r["callsign"]: r["updated_at"] for r in conn.execute(
                "SELECT callsign, updated_at FROM handoff WHERE project_id = ?", (project_id,))}
            out = []
            for r in conn.execute(
                "SELECT id, kind, human_approved, role, label, host, created_at, last_seen_at, revoked_at, "
                "guide_version_seen, client_version_seen, setup_complete FROM callsign WHERE project_id = ? "
                "ORDER BY revoked_at IS NOT NULL, COALESCE(last_seen_at, created_at) DESC, id",
                (project_id,),
            ):
                d = dict(r)
                d["human_approved"] = bool(d["human_approved"])
                d["setup_complete"] = bool(d["setup_complete"])
                seen = d["guide_version_seen"]
                d["guide_state"] = "never" if not seen else ("current" if seen == current else "stale")
                d["archived"] = d["revoked_at"] is not None
                d["handoff_updated_at"] = handoffs.get(d["id"])
                d["open_tasks"] = open_tasks.get(d["id"], [])
                out.append(d)
        return {"guide_current": current, "callsigns": out}

    def approve_callsign(self, ctx: Ctx, callsign: str) -> dict[str, Any]:
        """사람 콜사인 승인 (요구 Q3 · R7.7) — 승인된 human 소유자만. 승인 전 human 은 agent 권한이다."""
        p = self._need_callsign(ctx)
        if p.role != "owner" or p.callsign_kind != "human" or not p.human_approved:
            raise forbidden("콜사인 승인은 승인된 human 소유자만 한다")
        with self.write() as conn:
            row = conn.execute(
                "SELECT kind, human_approved FROM callsign WHERE project_id = ? AND id = ? AND revoked_at IS NULL",
                (p.project_id, callsign),
            ).fetchone()
            if row is None:
                raise not_found(f"콜사인이 없다: {callsign}")
            if row["kind"] != "human":
                raise invalid_field("callsign", "agent 콜사인은 승인 대상이 아니다")
            if row["human_approved"]:
                return {"callsign": callsign, "human_approved": True, "changed": False}
            conn.execute(
                "UPDATE callsign SET human_approved = 1, version = version + 1 WHERE project_id = ? AND id = ?",
                (p.project_id, callsign),
            )
            self._event(conn, ctx, p.project_id, "callsign", callsign, "approve", {"human_approved": False},
                        {"human_approved": True})
        return {"callsign": callsign, "human_approved": True, "changed": True}

    def revoke_callsign(self, ctx: Ctx, project_id: str, callsign: str) -> dict[str, Any]:
        """거두기 (요구 R4.7) — 토큰 무효 · 맡던 열린 task 의 맡은 이를 비운다."""
        with self.write() as conn:
            cur = conn.execute(
                "UPDATE callsign SET revoked_at = ?, version = version + 1 "
                "WHERE project_id = ? AND id = ? AND revoked_at IS NULL",
                (_iso(ctx.now), project_id, callsign),
            )
            if cur.rowcount == 0:
                raise not_found(f"거둘 콜사인이 없다: {project_id}/{callsign}")
            released = [r["id"] for r in conn.execute(
                "SELECT id FROM task WHERE project_id = ? AND assignee = ? AND status != 'done'", (project_id, callsign)
            )]
            for tid in released:
                conn.execute(
                    "UPDATE task SET assignee = NULL, version = version + 1, updated_at = ? WHERE project_id = ? AND id = ?",
                    (_iso(ctx.now), project_id, tid),
                )
                self._event(conn, ctx, project_id, "task", tid, "release", {"assignee": callsign}, {"assignee": None}, "hub")
            self._event(conn, ctx, project_id, "callsign", callsign, "revoke", None, {"released_tasks": released}, "hub")
        return {"callsign": callsign, "released_tasks": released}

    #: 콜사인의 활동으로 세는 것 — 하나라도 있으면 지우지 않는다 (거두기를 쓴다).
    CALLSIGN_USE: tuple[tuple[str, str], ...] = (
        ("events", "SELECT COUNT(*) FROM event WHERE project_id = ? AND callsign = ? "
                   "AND NOT (target_kind = 'callsign' AND target_id = callsign)"),
        ("tasks", "SELECT COUNT(*) FROM task WHERE project_id = ? AND assignee = ?"),
        ("handoffs", "SELECT COUNT(*) FROM handoff WHERE project_id = ? AND callsign = ?"),
        ("sessions", "SELECT COUNT(*) FROM session WHERE project_id = ? AND callsign = ?"),
        ("accounts", "SELECT COUNT(*) FROM hub_account_callsign WHERE project_id = ? AND callsign = ?"),
        ("messages", "SELECT COUNT(*) FROM inbox_message WHERE project_id = ? AND to_kind = 'callsign' AND to_id = ?"),
    )

    def delete_callsign(self, ctx: Ctx, project_id: str, callsign: str, confirm: str) -> dict[str, Any]:
        """관리자 삭제 — 등록 · 셋업 말고 활동이 없는 콜사인만. 활동이 있으면 409 (이력은 지우지 않는다)."""
        if ctx.via != "admin" and (ctx.principal is None or ctx.principal.kind != "admin"):
            raise forbidden("콜사인 삭제는 허브 관리자만 한다")
        if confirm != callsign:
            raise invalid_field("confirm", "지울 콜사인 이름을 그대로 적는다")
        with self.write() as conn:
            row = conn.execute("SELECT role, kind FROM callsign WHERE project_id = ? AND id = ?", (project_id, callsign)).fetchone()
            if row is None:
                raise not_found(f"콜사인이 없다: {project_id}/{callsign}")
            owner = conn.execute("SELECT 1 FROM project WHERE id = ? AND owner_callsign = ?", (project_id, callsign)).fetchone()
            if owner or row["role"] == "owner":
                raise HubError(409, "callsign_is_owner", f"프로젝트 소유자 콜사인은 지울 수 없다: {callsign}", {"callsign": callsign})
            used = {name: n for name, sql in self.CALLSIGN_USE
                    if (n := conn.execute(sql, (project_id, callsign)).fetchone()[0])}
            if used:
                raise HubError(409, "callsign_in_use", f"활동 기록이 있어 지우지 않는다: {callsign} — 거두기(callsign revoke)를 쓴다",
                               {"callsign": callsign, "used": used})
            conn.execute("DELETE FROM setup_step WHERE project_id = ? AND callsign = ?", (project_id, callsign))
            conn.execute("DELETE FROM callsign WHERE project_id = ? AND id = ?", (project_id, callsign))
            actor = ctx.principal.name if ctx.principal is not None and ctx.principal.name else "hub"
            self._event(conn, ctx, project_id, "callsign", callsign, "delete", {"kind": row["kind"], "role": row["role"]},
                        None, f"admin:{actor}")
        return {"callsign": callsign, "deleted": True}

    # --- task (WBS-33.3) ---------------------------------------------------------

    @staticmethod
    def _task_row(row: sqlite3.Row) -> dict[str, Any]:
        d = dict(row)
        d["fields"] = json.loads(d.pop("fields_json") or "{}")
        return d

    def _get_task(self, conn: sqlite3.Connection, project_id: str, task_id: str) -> dict[str, Any]:
        row = conn.execute("SELECT * FROM task WHERE project_id = ? AND id = ?", (project_id, task_id)).fetchone()
        if not row:
            raise not_found(f"task 가 없다: {task_id}")
        return self._task_row(row)

    @staticmethod
    def _validate_task_fields(values: dict[str, Any]) -> None:
        if "title" in values:
            title = values["title"]
            if not isinstance(title, str) or not title.strip():
                raise invalid_field("title", "비었다")
            if len(title) > TITLE_MAX:
                raise invalid_field("title", f"String should have at most {TITLE_MAX} characters (지금 {len(title)})")
        if "status" in values and values["status"] not in STATUSES:
            raise invalid_field("status", f"{' · '.join(STATUSES)} 가운데 하나")
        if values.get("status") == "done":
            raise HubError(422, "gate_denied", "done 은 done 게이트를 거치는 hub_task_close 로만 닫는다",
                           {"kit_error_code": "done_requires_gate"})
        if "priority" in values and values["priority"] not in PRIORITIES:
            raise invalid_field("priority", f"{' · '.join(PRIORITIES)} 가운데 하나")
        fields = values.get("fields")
        if fields is not None:
            if not isinstance(fields, dict):
                raise invalid_field("fields", "객체여야 한다")
            extra = set(fields) - TASK_FIELD_KEYS
            if extra:
                raise HubError(400, "unknown_field", f"fields 의 모르는 칸: {', '.join(sorted(extra))}",
                               {"fields": sorted(extra)})
            if "category" in fields:
                category = fields["category"]
                levels = ("level_1", "level_2", "level_3")
                if not isinstance(category, dict) or set(category) != set(levels) or any(
                    not isinstance(category.get(level), str) or not category[level].strip() for level in levels
                ):
                    raise invalid_field("fields.category", "level_1 · level_2 · level_3 문자열이 모두 필요하다")
            if "tests" in fields:
                tests = fields["tests"]
                if not isinstance(tests, list):
                    raise invalid_field("fields.tests", "테스트 정의 배열이어야 한다")
                seen: set[str] = set()
                for test in tests:
                    if not isinstance(test, dict) or not isinstance(test.get("id"), str) or not test["id"].strip():
                        raise invalid_field("fields.tests", "각 테스트에 id가 필요하다")
                    if test["id"] in seen:
                        raise invalid_field("fields.tests", f"중복 테스트 id: {test['id']}")
                    seen.add(test["id"])
                    if not isinstance(test.get("name"), str) or not test["name"].strip() or not isinstance(test.get("required"), bool):
                        raise invalid_field("fields.tests", "각 테스트에 name 문자열과 required 불리언이 필요하다")
                    runs = test.get("runs", [])
                    if not isinstance(runs, list) or any(
                        not isinstance(run, dict) or run.get("status") not in ("passed", "failed", "skipped")
                        for run in runs
                    ):
                        raise invalid_field("fields.tests.runs", "status는 passed · failed · skipped 중 하나여야 한다")
        for key in ("branch", "wbs", "wbs_exempt_reason", "description", "plan_md"):
            if key in values and not isinstance(values[key], str):
                raise invalid_field(key, "문자열이어야 한다")

    @staticmethod
    def _need_callsign(ctx: Ctx) -> Principal:
        p = ctx.principal
        if p is None or p.kind != "callsign" or not p.project_id or not p.callsign:
            raise forbidden("콜사인 토큰이 필요하다")
        return p

    @staticmethod
    def _need_reader(ctx: Ctx) -> Principal:
        """읽기 — 콜사인 토큰 또는 화면의 viewer (프로젝트로 좁힌 web · admin · 콜사인)."""
        p = ctx.principal
        if p is None or p.kind not in ("callsign", "viewer") or not p.project_id:
            raise forbidden("콜사인 토큰이 필요하다")
        return p

    def task_create(self, ctx: Ctx, values: dict[str, Any], request_id: str | None = None,
                    prepare: Callable[[sqlite3.Connection, str, str, dict[str, Any]], dict[str, Any]] | None = None
                    ) -> dict[str, Any]:
        p = self._need_callsign(ctx)
        scan_secrets(values)
        if "title" not in values:
            raise invalid_field("title", "필수")
        self._validate_task_fields(values)
        date = ctx.now.strftime("%Y-%m-%d")
        pid, cs = p.project_id, p.callsign
        assert pid is not None and cs is not None

        def do(conn: sqlite3.Connection) -> dict[str, Any]:
            row = conn.execute(
                "SELECT next FROM task_seq WHERE project_id = ? AND date = ? AND namespace = ?", (pid, date, cs)
            ).fetchone()
            n = row["next"] if row else 1
            conn.execute(
                "INSERT INTO task_seq (project_id, date, namespace, next) VALUES (?, ?, ?, ?) "
                "ON CONFLICT(project_id, date, namespace) DO UPDATE SET next = excluded.next",
                (pid, date, cs, n + 1),
            )
            task_id = f"TASK-{date}-{cs}-{n:03d}"
            vals = prepare(conn, pid, task_id, values) if prepare else values
            conn.execute(
                "INSERT INTO task (project_id, id, title, status, priority, branch, wbs, wbs_exempt_reason, description, "
                "plan_md, fields_json, created_by, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (pid, task_id, vals["title"].strip(), vals.get("status", "planned"), vals.get("priority", "high"),
                 vals.get("branch", ""), vals.get("wbs", ""), vals.get("wbs_exempt_reason", ""),
                 vals.get("description", ""), vals.get("plan_md", ""), _json(vals.get("fields") or {}),
                 cs, _iso(ctx.now), _iso(ctx.now)),
            )
            task = self._get_task(conn, pid, task_id)
            self._event(conn, ctx, pid, "task", task_id, "create", None, task)
            return {"task": task}

        return self.idempotent(ctx, request_id, do)

    def task_get(self, ctx: Ctx, task_id: str) -> dict[str, Any]:
        p = self._need_reader(ctx)
        assert p.project_id is not None
        with self.read() as conn:
            task = self._get_task(conn, p.project_id, task_id)
            task["commits"] = [dict(r) for r in conn.execute(
                "SELECT sha, branch, added_by, added_at FROM task_commit WHERE project_id = ? AND task_id = ? ORDER BY added_at",
                (p.project_id, task_id),
            )]
        return {"task": task}

    def task_list(self, ctx: Ctx, status: str | None = None, assignee: str | None = None, limit: int = 100,
                  newest_first: bool = False) -> dict[str, Any]:
        p = self._need_reader(ctx)
        if status is not None and status not in STATUSES:
            raise invalid_field("status", f"{' · '.join(STATUSES)} 가운데 하나")
        if not 1 <= limit <= 500:
            raise invalid_field("limit", "1~500")
        sql = "SELECT * FROM task WHERE project_id = ?"
        args: list[Any] = [p.project_id]
        if status is not None:
            sql += " AND status = ?"
            args.append(status)
        if assignee is not None:
            if assignee == "":
                sql += " AND assignee IS NULL"
            else:
                sql += " AND assignee = ?"
                args.append(assignee)
        # 화면은 최근 것부터 (테스트베드 실측: 649개 저장소에서 가장 오래된 200개만 보였다)
        sql += " ORDER BY created_at DESC, id DESC LIMIT ?" if newest_first else " ORDER BY created_at, id LIMIT ?"
        args.append(limit)
        with self.read() as conn:
            return {"tasks": [self._task_row(r) for r in conn.execute(sql, args)]}

    def task_list_page(self, ctx: Ctx, filters: dict[str, str], *, limit: int = 25, offset: int = 0) -> dict[str, Any]:
        """Filtered task page plus project facets; UI pagination and category filters (M-061)."""
        p = self._need_reader(ctx)
        if not 1 <= limit <= 100:
            raise invalid_field("limit", "1~100")
        if not 0 <= offset <= 1_000_000:
            raise invalid_field("offset", "0~1000000")
        status = filters.get("status", "")
        if status and status not in STATUSES:
            raise invalid_field("status", f"{' · '.join(STATUSES)} 가운데 하나")
        roadmap = filters.get("roadmap", "")
        if roadmap not in {"", "linked", "unlinked"}:
            raise invalid_field("roadmap", "linked · unlinked")
        milestone = filters.get("milestone", "")
        if milestone and not re.fullmatch(r"M-[0-9]{3}", milestone):
            raise invalid_field("milestone", "M-001 형식")
        wbs = filters.get("wbs", "")
        if wbs and (len(wbs) > 80 or ".." in wbs or "\\" in wbs):
            raise invalid_field("wbs", "80자 이하 WBS 키")
        where = ["project_id = ?"]
        args: list[Any] = [p.project_id]
        if status:
            where.append("status = ?")
            args.append(status)
        if roadmap == "linked":
            where.append("wbs != ''")
        elif roadmap == "unlinked":
            where.append("wbs = ''")
        if milestone:
            where.append("wbs LIKE ?")
            args.append(milestone + "/%")
        if wbs:
            where.append("wbs = ?")
            args.append(wbs)
        category_expr = ("fields_json::jsonb #>> '{category,%s}'" if hubdb.is_postgres(self.path)
                         else "json_extract(fields_json, '$.category.%s')")
        for key in ("level_1", "level_2", "level_3"):
            value = filters.get("category_" + key, "")
            if value:
                where.append(category_expr % key + " = ?")
                args.append(value)
        clause = " AND ".join(where)
        with self.read() as conn:
            total = int(conn.execute("SELECT COUNT(*) FROM task WHERE " + clause, args).fetchone()[0])
            rows = conn.execute("SELECT * FROM task WHERE " + clause +
                                " ORDER BY created_at DESC, id DESC LIMIT ? OFFSET ?", (*args, limit, offset)).fetchall()
            facet_rows = conn.execute("SELECT wbs,fields_json FROM task WHERE project_id=?", (p.project_id,)).fetchall()
        milestones: set[str] = set()
        wbss: set[str] = set()
        categories: list[set[str]] = [set(), set(), set()]
        for row in facet_rows:
            task_wbs = row["wbs"] or ""
            if task_wbs:
                wbss.add(task_wbs)
                milestones.add(task_wbs.split("/", 1)[0])
            try:
                category = json.loads(row["fields_json"] or "{}").get("category") or {}
            except (ValueError, TypeError):
                category = {}
            if isinstance(category, dict):
                for index, key in enumerate(("level_1", "level_2", "level_3")):
                    category_value = category.get(key)
                    if isinstance(category_value, str) and category_value:
                        categories[index].add(category_value)
        return {"tasks": [self._task_row(row) for row in rows], "total": total, "limit": limit, "offset": offset,
                "facets": {"roadmaps": ["linked", "unlinked"], "milestones": sorted(milestones), "wbs": sorted(wbss),
                           "category_level_1": sorted(categories[0]), "category_level_2": sorted(categories[1]),
                           "category_level_3": sorted(categories[2])}}

    def _versioned_update(self, ctx: Ctx, task_id: str, expected_version: int | None, op: str,
                          mutate: Callable[[dict[str, Any], Principal, sqlite3.Connection], dict[str, Any]],
                          request_id: str | None) -> dict[str, Any]:
        p = self._need_callsign(ctx)
        return self.idempotent(ctx, request_id,
                               lambda conn: self.versioned_update_in(conn, ctx, p, task_id, expected_version, op, mutate))

    def versioned_update_in(self, conn: sqlite3.Connection, ctx: Ctx, p: Principal, task_id: str,
                            expected_version: int | None, op: str,
                            mutate: Callable[[dict[str, Any], Principal, sqlite3.Connection], dict[str, Any]]
                            ) -> dict[str, Any]:
        """열린 트랜잭션 안의 task 갱신 — 다른 쓰기와 한 트랜잭션으로 묶을 때 (2.1 배정 수락 = 맡기, DO6)."""
        pid = p.project_id
        assert pid is not None
        before = self._get_task(conn, pid, task_id)
        if expected_version is not None and before["version"] != expected_version:
            raise version_conflict(before["version"], before)
        changes = mutate(before, p, conn)
        if not changes:
            return {"task": before, "changed": False}
        sets = ", ".join(f"{k} = ?" for k in changes)
        vals = [(_json(v) if k == "fields_json" else v) for k, v in changes.items()]
        cur = conn.execute(
            f"UPDATE task SET {sets}, version = version + 1, updated_at = ? WHERE project_id = ? AND id = ? AND version = ?",
            (*vals, _iso(ctx.now), pid, task_id, before["version"]),
        )
        if cur.rowcount != 1:  # BEGIN IMMEDIATE 아래라 나지 않지만, 조용히 넘어가지 않는다
            raise version_conflict(before["version"], before)
        after = self._get_task(conn, pid, task_id)
        delta_before = {k.removesuffix("_json"): before.get(k.removesuffix("_json"), None) for k in changes}
        delta_after = {k.removesuffix("_json"): after.get(k.removesuffix("_json"), None) for k in changes}
        self._event(conn, ctx, pid, "task", task_id, op, delta_before, delta_after)
        return {"task": after, "changed": True}

    def task_update(self, ctx: Ctx, task_id: str, expected_version: int, values: dict[str, Any],
                    request_id: str | None = None,
                    prepare: Callable[[sqlite3.Connection, dict[str, Any], dict[str, Any]], dict[str, Any]] | None = None
                    ) -> dict[str, Any]:
        scan_secrets(values)
        allowed = {"title", "status", "priority", "branch", "wbs", "wbs_exempt_reason", "description", "plan_md", "fields"}
        extra = set(values) - allowed
        if extra:
            raise HubError(400, "unknown_field", f"고칠 수 없는 칸: {', '.join(sorted(extra))}", {"fields": sorted(extra)})
        self._validate_task_fields(values)

        def mutate(before: dict[str, Any], _p: Principal, conn: sqlite3.Connection) -> dict[str, Any]:
            vals = prepare(conn, before, values) if prepare else values
            out: dict[str, Any] = {}
            for k, v in vals.items():
                if k == "fields":
                    merged = {**before["fields"], **v}
                    if merged != before["fields"]:
                        out["fields_json"] = merged
                elif before.get(k) != v:
                    out[k] = v.strip() if k == "title" else v
            return out

        return self._versioned_update(ctx, task_id, expected_version, "update", mutate, request_id)

    @staticmethod
    def claim_mutate(before: dict[str, Any], p: Principal, _c: sqlite3.Connection) -> dict[str, Any]:
        """맡기 판정 — ``hub_task_claim`` 과 2.1 배정 수락이 같은 함수를 쓴다 (정본 하나)."""
        if before["assignee"] == p.callsign:
            return {}
        if before["assignee"]:
            raise HubError(409, "already_claimed", f"{before['assignee']} 가 맡고 있다",
                           {"assignee": before["assignee"], "current_version": before["version"]})
        if before["status"] == "done":
            raise HubError(409, "task_done", "닫힌 task 는 맡을 수 없다")
        # 맡는 순간 시작이다 — planned 면 in_progress 로 (소유자 2026-11-21, 테스트베드 실측). blocked 는 그대로.
        return {"assignee": p.callsign, **({"status": "in_progress"} if before["status"] == "planned" else {})}

    def task_claim(self, ctx: Ctx, task_id: str, request_id: str | None = None) -> dict[str, Any]:
        return self._versioned_update(ctx, task_id, None, "claim", self.claim_mutate, request_id)

    def task_release(self, ctx: Ctx, task_id: str, request_id: str | None = None) -> dict[str, Any]:
        def mutate(before: dict[str, Any], p: Principal, _c: sqlite3.Connection) -> dict[str, Any]:
            if before["assignee"] is None:
                return {}
            if before["assignee"] != p.callsign and p.role != "owner":
                raise forbidden("맡은 콜사인이나 프로젝트 소유자만 놓을 수 있다")
            return {"assignee": None}

        return self._versioned_update(ctx, task_id, None, "release", mutate, request_id)

    def task_progress(self, ctx: Ctx, task_id: str, note: str, request_id: str | None = None) -> dict[str, Any]:
        scan_secrets(note, "note")
        if not isinstance(note, str) or not note.strip():
            raise invalid_field("note", "비었다")
        stamp = ctx.now.strftime("%Y-%m-%d %H:%M")

        def mutate(_before: dict[str, Any], _p: Principal, _c: sqlite3.Connection) -> dict[str, Any]:
            return {"progress_note": f"[{stamp}] {note.strip()}", "progress_at": _iso(ctx.now)}

        return self._versioned_update(ctx, task_id, None, "progress", mutate, request_id)

    def task_link_commit(self, ctx: Ctx, task_id: str, sha: str, branch: str = "",
                         request_id: str | None = None) -> dict[str, Any]:
        p = self._need_callsign(ctx)
        sha = (sha or "").strip().lower()
        if not SHA_PATTERN.match(sha):
            raise invalid_field("sha", "16진 7~40 자")
        pid = p.project_id
        assert pid is not None

        def do(conn: sqlite3.Connection) -> dict[str, Any]:
            self._get_task(conn, pid, task_id)
            cur = conn.execute(
                "INSERT OR IGNORE INTO task_commit (project_id, task_id, sha, branch, added_by, added_at) VALUES (?, ?, ?, ?, ?, ?)",
                (pid, task_id, sha, branch, p.callsign, _iso(ctx.now)),
            )
            if cur.rowcount:
                self._event(conn, ctx, pid, "task", task_id, "link_commit", None, {"sha": sha, "branch": branch})
            return {"task_id": task_id, "sha": sha, "linked": bool(cur.rowcount)}

        return self.idempotent(ctx, request_id, do)

    def events(self, ctx: Ctx, target_kind: str | None = None, target_id: str | None = None,
               after_seq: int = 0, limit: int = 200) -> dict[str, Any]:
        p = self._need_reader(ctx)
        if not 1 <= limit <= 1000:
            raise invalid_field("limit", "1~1000")
        sql = "SELECT * FROM event WHERE project_id = ? AND seq > ?"
        args: list[Any] = [p.project_id, after_seq]
        if target_kind:
            sql += " AND target_kind = ?"
            args.append(target_kind)
        if target_id:
            sql += " AND target_id = ?"
            args.append(target_id)
        sql += " ORDER BY seq LIMIT ?"
        args.append(limit)
        out = []
        with self.read() as conn:
            for r in conn.execute(sql, args):
                d = dict(r)
                before_raw, after_raw = d.pop("before_json"), d.pop("after_json")
                d["before"] = json.loads(before_raw) if before_raw is not None else None
                d["after"] = json.loads(after_raw) if after_raw is not None else None
                out.append(d)
        return {"events": out}
