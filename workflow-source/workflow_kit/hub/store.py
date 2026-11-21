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
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Iterator

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
})


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def new_token() -> str:
    return TOKEN_PREFIX + secrets.token_urlsafe(32)


@dataclass(frozen=True)
class Principal:
    """요청한 쪽. ``kind`` = ``callsign`` (프로젝트 범위) · ``web`` · ``admin`` (허브 토큰)."""

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

    def authenticate(self, token: str | None, now: datetime | None = None) -> Principal | None:
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

    def lookup_project(self, remote_url: str) -> dict[str, Any]:
        key = gitkey.normalize(remote_url)
        with self.read() as conn:
            row = conn.execute(
                "SELECT p.id, p.display_name FROM project_alias a JOIN project p ON p.id = a.project_id WHERE a.key = ?",
                (key,),
            ).fetchone()
        if not row:
            return {"key": key, "project_id": None, "display_name": None}
        return {"key": key, "project_id": row["id"], "display_name": row["display_name"]}

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
        key = gitkey.normalize(remote_url)
        self._check_callsign(callsign, kind)
        if not display_name.strip():
            raise invalid_field("display_name", "비었다")
        token = new_token()
        project_id = f"P-{ctx.now.strftime('%Y%m%d')}-{secrets.token_hex(4)}"
        with self.write() as conn:
            existing = conn.execute("SELECT project_id FROM project_alias WHERE key = ?", (key,)).fetchone()
            if existing:
                raise HubError(409, "project_exists", f"이미 등록된 프로젝트다 — hub_callsign_register 로 합류한다",
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
        return {"project_id": project_id, "key": key, "callsign": callsign, "role": "owner", "token": token}

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
        for key in ("branch", "wbs", "wbs_exempt_reason", "description", "plan_md"):
            if key in values and not isinstance(values[key], str):
                raise invalid_field(key, "문자열이어야 한다")

    @staticmethod
    def _need_callsign(ctx: Ctx) -> Principal:
        p = ctx.principal
        if p is None or p.kind != "callsign" or not p.project_id or not p.callsign:
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
        p = self._need_callsign(ctx)
        assert p.project_id is not None
        with self.read() as conn:
            task = self._get_task(conn, p.project_id, task_id)
            task["commits"] = [dict(r) for r in conn.execute(
                "SELECT sha, branch, added_by, added_at FROM task_commit WHERE project_id = ? AND task_id = ? ORDER BY added_at",
                (p.project_id, task_id),
            )]
        return {"task": task}

    def task_list(self, ctx: Ctx, status: str | None = None, assignee: str | None = None, limit: int = 100) -> dict[str, Any]:
        p = self._need_callsign(ctx)
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
        sql += " ORDER BY created_at, id LIMIT ?"
        args.append(limit)
        with self.read() as conn:
            return {"tasks": [self._task_row(r) for r in conn.execute(sql, args)]}

    def _versioned_update(self, ctx: Ctx, task_id: str, expected_version: int | None, op: str,
                          mutate: Callable[[dict[str, Any], Principal, sqlite3.Connection], dict[str, Any]],
                          request_id: str | None) -> dict[str, Any]:
        p = self._need_callsign(ctx)
        pid = p.project_id
        assert pid is not None

        def do(conn: sqlite3.Connection) -> dict[str, Any]:
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

        return self.idempotent(ctx, request_id, do)

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

    def task_claim(self, ctx: Ctx, task_id: str, request_id: str | None = None) -> dict[str, Any]:
        def mutate(before: dict[str, Any], p: Principal, _c: sqlite3.Connection) -> dict[str, Any]:
            if before["assignee"] == p.callsign:
                return {}
            if before["assignee"]:
                raise HubError(409, "already_claimed", f"{before['assignee']} 가 맡고 있다",
                               {"assignee": before["assignee"], "current_version": before["version"]})
            if before["status"] == "done":
                raise HubError(409, "task_done", "닫힌 task 는 맡을 수 없다")
            return {"assignee": p.callsign}

        return self._versioned_update(ctx, task_id, None, "claim", mutate, request_id)

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
        p = self._need_callsign(ctx)
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
