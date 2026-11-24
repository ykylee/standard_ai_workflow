"""허브 서버 간 프로젝트 이전 — 묶음 · export · import · 봉인 (M-039 WBS-39.4, 소유자 2026-11-21).

결정 (소유자):

- **토큰은 그대로 이어받는다** — 콜사인 행(토큰 해시 포함)을 옮기므로 기존 환경의 토큰이 새 허브에서도 유효하다.
  환경은 주소만 바꾼다 (새 허브의 ``hub_setup_plan`` 이 ``.workflow-hub/env`` · ``.mcp.json`` 을 새 주소로 다시 쓴다).
- **원본은 봉인한다** — 데이터는 지우지 않고, 그 프로젝트의 모든 호출에 ``410 project_moved`` + 새 주소를 돌려준다.
  두 정본이 생기지 않고, 봉인만 풀면 되돌릴 수 있다.
- **운반은 관리자 CLI 파일 묶음 먼저** (``hub admin export-project`` · ``import-project`` · ``seal-project``),
  HTTP 경로는 같은 묶음 형식으로 뒤에 더한다.

묶음 ``workflow-hub-project-bundle/1``: 프로젝트 행 + 프로젝트에 묶인 표 전부(표별 열 이름 · 행)와 표별 행 수 ·
전체 sha256. 이력(``event``)은 순서를 지키고 번호(``seq``)는 대상 허브에서 새로 매긴다.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from workflow_kit.hub import KIT_COMPAT_VERSION as KIT_VERSION
from workflow_kit.hub import db as hubdb
from workflow_kit.hub.errors import HubError, not_found
from workflow_kit.hub.store import Ctx, Store, _iso, _json

BUNDLE_FORMAT = "workflow-hub-project-bundle/1"
#: 허브 전역 표 — 프로젝트와 함께 옮기지 않는다. 그 밖의 표는 전부 '프로젝트 표' 여야 한다 (검사가 대조한다).
HUB_SCOPED_TABLES = frozenset(
    {
        "meta", "hub_token", "sqlite_sequence", "project", "hub_invite", "relay_host", "relay_invite",
        "harness_registry", "harness_person", "harness_registry_person",
        "hub_account", "hub_account_callsign", "hub_account_session", "hub_account_login_attempt",
        "approval_grant", "a2a_task",  # 실행 승인은 그 허브의 로그인에 묶인다 — 옮기지 않는다
    }
)
#: 봉인된 프로젝트에서도 받는 도구 — 조회(새 주소를 알림) · 소유자의 다시 뜨기 · 봉인 풀기 (이전 실패 복구).
SEALED_ALLOWED = frozenset({"hub_project_lookup", "hub_project_export", "hub_project_unseal"})
INVITE_HOURS = 24


def _is_postgres(conn: Any) -> bool:
    return getattr(conn, "dialect", "sqlite") == "postgresql"


def project_tables(conn: Any) -> list[str]:
    """``project_id`` 열을 가진 표 — DB 에서 파생한다 (새 표가 생기면 저절로 따라온다)."""
    out = []
    if _is_postgres(conn):
        tables = [
            r[0]
            for r in conn.execute(
                "SELECT table_name FROM information_schema.tables WHERE table_schema='public' "
                "AND table_type='BASE TABLE' ORDER BY table_name"
            )
        ]
    else:
        tables = [
            r[0]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name"
            )
        ]
    for name in tables:
        cols = _columns(conn, name)
        if "project_id" in cols:
            out.append(name)
    return out


def _columns(conn: Any, table: str) -> list[str]:
    if _is_postgres(conn):
        return [
            r[0]
            for r in conn.execute(
                "SELECT column_name FROM information_schema.columns WHERE table_schema='public' AND table_name=? ORDER BY ordinal_position",
                (table,),
            )
        ]
    return [r[1] for r in conn.execute(f'PRAGMA table_info("{table}")')]


def _foreign_key_order(conn: Any, tables: set[str]) -> list[str]:
    """Stable parent-before-child order for immediate PostgreSQL foreign keys."""
    parents: dict[str, set[str]] = {name: set() for name in tables}
    if _is_postgres(conn):
        rows = conn.execute(
            "SELECT child.relname AS child, parent.relname AS parent FROM pg_constraint fk "
            "JOIN pg_class child ON child.oid=fk.conrelid "
            "JOIN pg_class parent ON parent.oid=fk.confrelid "
            "JOIN pg_namespace ns ON ns.oid=child.relnamespace "
            "WHERE fk.contype='f' AND ns.nspname='public'"
        )
        for row in rows:
            child, parent = row[0], row[1]
            if child in tables and parent in tables:
                parents[child].add(parent)
    else:
        for child in tables:
            for row in conn.execute(f'PRAGMA foreign_key_list("{child}")'):
                if row[2] in tables:
                    parents[child].add(row[2])
    ordered: list[str] = []
    pending = set(tables)
    while pending:
        ready = sorted(name for name in pending if not (parents[name] & pending))
        if not ready:
            raise HubError(
                409,
                "bundle_schema_cycle",
                "표 사이 외래 키 순환이 있어 이 PostgreSQL backend에서 이전할 수 없다",
            )
        ordered.extend(ready)
        pending.difference_update(ready)
    return ordered


def _digest(project: dict[str, Any], tables: dict[str, Any]) -> str:
    raw = json.dumps(
        {"project": project, "tables": tables},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


def moved_to(conn: sqlite3.Connection, project_id: str) -> str | None:
    row = conn.execute("SELECT settings_json FROM project WHERE id = ?", (project_id,)).fetchone()
    if row is None:
        return None
    settings = json.loads(row["settings_json"] or "{}")
    moved = settings.get("moved")
    return str(moved.get("to")) if isinstance(moved, dict) and moved.get("to") else None


def moved_error(project_id: str, to: str) -> HubError:
    return HubError(
        410,
        "project_moved",
        f"이 프로젝트는 다른 허브로 옮겨졌다: {to} — 환경의 허브 주소를 바꾸고(토큰은 그대로) 새 허브에서 "
        "hub_setup_plan 으로 .workflow-hub/env · .mcp.json 을 다시 쓴다",
        {"project_id": project_id, "moved_to": to},
    )


class Transfer:
    def __init__(self, store: Store) -> None:
        self.store = store

    def export(self, project_id: str, now: datetime, public_url: str = "") -> dict[str, Any]:
        with self.store.read() as conn:
            prow = conn.execute("SELECT * FROM project WHERE id = ?", (project_id,)).fetchone()
            if prow is None:
                raise not_found(f"프로젝트가 없다: {project_id}")
            project = dict(prow)
            tables: dict[str, Any] = {}
            for name in project_tables(conn):
                cols = _columns(conn, name)
                order = "seq" if name == "event" else "rowid"
                rows = [
                    list(r)
                    for r in conn.execute(
                        f'SELECT * FROM "{name}" WHERE project_id = ? ORDER BY {order}',
                        (project_id,),
                    )
                ]
                tables[name] = {"columns": cols, "rows": rows}
        return {
            "format": BUNDLE_FORMAT,
            "source": {
                "public_url": public_url,
                "kit_version": KIT_VERSION,
                "db_version": self.store.db_version(),
                "exported_at": _iso(now),
            },
            "project": project,
            "tables": tables,
            "counts": {k: len(v["rows"]) for k, v in tables.items()},
            "digest": _digest(project, tables),
        }

    def import_bundle(self, bundle: dict[str, Any], now: datetime) -> dict[str, Any]:
        if not isinstance(bundle, dict) or bundle.get("format") != BUNDLE_FORMAT:
            raise HubError(400, "invalid_bundle", f"묶음 형식이 {BUNDLE_FORMAT} 이 아니다")
        project, tables = bundle.get("project"), bundle.get("tables")
        if not isinstance(project, dict) or not isinstance(tables, dict):
            raise HubError(400, "invalid_bundle", "project · tables 가 없다")
        if _digest(project, tables) != bundle.get("digest"):
            raise HubError(
                400, "bundle_digest_mismatch", "묶음 내용이 digest 와 다르다 — 바뀌었거나 잘렸다"
            )
        src_db = int((bundle.get("source") or {}).get("db_version", 0))
        if src_db > hubdb.latest_version():
            raise HubError(
                409,
                "bundle_newer_than_hub",
                f"묶음의 DB 판 {src_db} 이 이 허브가 아는 {hubdb.latest_version()} 보다 새롭다 — 허브를 올린다",
                {"bundle_db_version": src_db, "hub_db_version": hubdb.latest_version()},
            )
        pid = str(project.get("id") or "")
        replaced = False
        with self.store.write() as conn:
            # 표 사이 외래 키는 커밋 때 한꺼번에 본다 — 넣는 순서와 상관없이 끝 상태가 맞아야 한다
            if not _is_postgres(conn):
                conn.execute("PRAGMA defer_foreign_keys = ON")
            known = set(project_tables(conn))
            ordered_known = _foreign_key_order(conn, known)
            unknown = sorted(set(tables) - known)
            if unknown:
                raise HubError(
                    409,
                    "bundle_unknown_table",
                    f"이 허브에 없는 표: {', '.join(unknown)}",
                    {"tables": unknown},
                )
            existing = conn.execute("SELECT id FROM project WHERE id = ?", (pid,)).fetchone()
            if existing is not None:
                if moved_to(conn, pid) is None:
                    raise HubError(
                        409,
                        "project_exists",
                        f"이 허브에 같은 프로젝트가 이미 있다: {pid} (봉인되지 않음)",
                        {"project_id": pid},
                    )
                # 되옮기기 — 이 허브의 봉인된 사본을 새 묶음으로 바꾼다 (봉인된 사본은 정본이 아니다)
                for name in reversed(ordered_known):
                    conn.execute(f'DELETE FROM "{name}" WHERE project_id = ?', (pid,))
                conn.execute("DELETE FROM project WHERE id = ?", (pid,))
                replaced = True
            keys = [r[0] for r in tables.get("project_alias", {}).get("rows", [])]
            clash = [
                k
                for k in keys
                if conn.execute("SELECT 1 FROM project_alias WHERE key = ?", (k,)).fetchone()
            ]
            if clash:
                raise HubError(
                    409,
                    "alias_taken",
                    f"이 허브에서 다른 프로젝트가 쓰는 저장소 주소: {', '.join(clash)}",
                    {"keys": clash},
                )
            pcols = _columns(conn, "project")
            settings = json.loads(project.get("settings_json") or "{}")
            settings.pop("moved", None)  # 옮겨 온 정본은 봉인 상태가 아니다
            prow = {
                **{k: project.get(k) for k in pcols if k in project},
                "settings_json": _json(settings),
            }
            conn.execute(
                f"INSERT INTO project ({', '.join(prow)}) VALUES ({', '.join('?' for _ in prow)})",
                list(prow.values()),
            )
            counts: dict[str, int] = {}
            for name in _foreign_key_order(conn, set(tables)):
                spec = tables[name]
                cols = [c for c in spec.get("columns", []) if not (name == "event" and c == "seq")]
                have = set(_columns(conn, name))
                missing = sorted(set(cols) - have)
                if missing:
                    raise HubError(
                        409,
                        "bundle_unknown_column",
                        f"{name} 에 없는 열: {', '.join(missing)}",
                        {"table": name, "columns": missing},
                    )
                idx = [spec["columns"].index(c) for c in cols]
                sql = f'INSERT INTO "{name}" ({", ".join(cols)}) VALUES ({", ".join("?" for _ in cols)})'
                for row in spec.get("rows", []):
                    conn.execute(sql, [row[i] for i in idx])
                counts[name] = len(spec.get("rows", []))
            self.store._event(
                conn,
                Ctx(now=now, via="admin"),
                pid,
                "project",
                pid,
                "project_imported",
                None,
                {
                    "source": bundle.get("source"),
                    "digest": bundle.get("digest"),
                    "replaced": replaced,
                },
                "hub",
            )
        return {
            "project_id": pid,
            "counts": counts,
            "replaced_sealed_copy": replaced,
            "digest": bundle.get("digest"),
        }

    def seal(self, project_id: str, to: str, now: datetime) -> dict[str, Any]:
        if not to.strip():
            raise HubError(400, "invalid_field", "moved_to: 새 허브 주소가 필요하다")
        with self.store.write() as conn:
            row = conn.execute(
                "SELECT settings_json FROM project WHERE id = ?", (project_id,)
            ).fetchone()
            if row is None:
                raise not_found(f"프로젝트가 없다: {project_id}")
            settings = json.loads(row["settings_json"] or "{}")
            settings["moved"] = {"to": to.strip(), "at": _iso(now)}
            conn.execute(
                "UPDATE project SET settings_json = ?, version = version + 1 WHERE id = ?",
                (_json(settings), project_id),
            )
            self.store._event(
                conn,
                Ctx(now=now, via="admin"),
                project_id,
                "project",
                project_id,
                "sealed",
                None,
                {"moved_to": to.strip()},
                "hub",
            )
        return {"project_id": project_id, "sealed": True, "moved_to": to.strip()}

    def unseal(self, project_id: str, now: datetime) -> dict[str, Any]:
        with self.store.write() as conn:
            row = conn.execute(
                "SELECT settings_json FROM project WHERE id = ?", (project_id,)
            ).fetchone()
            if row is None:
                raise not_found(f"프로젝트가 없다: {project_id}")
            settings = json.loads(row["settings_json"] or "{}")
            was = settings.pop("moved", None)
            conn.execute(
                "UPDATE project SET settings_json = ?, version = version + 1 WHERE id = ?",
                (_json(settings), project_id),
            )
            self.store._event(
                conn,
                Ctx(now=now, via="admin"),
                project_id,
                "project",
                project_id,
                "unsealed",
                was,
                None,
                "hub",
            )
        return {"project_id": project_id, "sealed": False}


# --- HTTP 경로 (소유자 2026-11-21 '둘 다' · 대상 허브 일회용 초대 코드) ---------------------------------


def _owner(ctx: Ctx) -> str:
    p = ctx.principal
    if (
        p is None
        or p.kind != "callsign"
        or p.role != "owner"
        or p.callsign_kind != "human"
        or not p.human_approved
    ):
        raise HubError(
            403, "forbidden", "프로젝트 이전은 그 프로젝트의 소유자(승인된 human)가 한다"
        )
    return p.project_id or ""


def tool_export(store: Store, ctx: Ctx, seal_to: str | None) -> dict[str, Any]:
    """소유자가 자기 프로젝트를 뜬다 — ``seal_to`` 가 있으면 먼저 봉인 (그 뒤 쓰기를 막는다)."""
    pid = _owner(ctx)
    if seal_to and ctx.public_url and seal_to.rstrip("/") == ctx.public_url.rstrip("/"):
        raise HubError(400, "invalid_field", "seal_to: 지금 허브와 같은 주소다")
    t = Transfer(store)
    was = store.project_moved(pid)  # 이미 봉인돼 있었나 — 실패 복구 때 이 실행이 건 봉인만 푼다
    sealed = t.seal(pid, seal_to, ctx.now) if seal_to else None
    return {
        "sealed": sealed,
        "was_sealed": was is not None,
        "bundle": t.export(pid, ctx.now, ctx.public_url),
    }


def tool_unseal(store: Store, ctx: Ctx) -> dict[str, Any]:
    """소유자가 봉인을 푼다 — 이전이 실패했을 때 되돌리는 길."""
    return Transfer(store).unseal(_owner(ctx), ctx.now)


def issue_invite(
    store: Store, project_id: str, now: datetime, hours: int = INVITE_HOURS, note: str = ""
) -> dict[str, Any]:
    """대상 허브 관리자가 만드는 일회용 초대 코드 — 그 프로젝트 ID 하나 · 만료 시각. 코드는 해시만 남긴다."""
    import secrets  # noqa: PLC0415
    from datetime import timedelta  # noqa: PLC0415

    from workflow_kit.hub.store import hash_token  # noqa: PLC0415

    if not project_id.strip():
        raise HubError(400, "invalid_field", "project: 들일 프로젝트 ID")
    code = "wfi_" + secrets.token_urlsafe(24)
    expires = now + timedelta(hours=hours)
    with store.write() as conn:
        conn.execute(
            "INSERT INTO hub_invite (code_hash, for_project, created_at, expires_at, note) VALUES (?, ?, ?, ?, ?)",
            (hash_token(code), project_id, _iso(now), _iso(expires), note),
        )
        store._event(
            conn,
            Ctx(now=now, via="admin"),
            None,
            "hub_invite",
            project_id,
            "issue",
            None,
            {"expires_at": _iso(expires)},
            "hub",
        )
    return {"code": code, "project_id": project_id, "expires_at": _iso(expires)}


def tool_import(store: Store, ctx: Ctx, invite: str, bundle: Any) -> dict[str, Any]:
    """초대 코드로 묶음을 들인다 (토큰 없이 — 코드가 권한). 코드는 한 번 · 그 프로젝트만 · 만료 전."""
    from workflow_kit.hub.store import hash_token  # noqa: PLC0415

    if not isinstance(bundle, dict):
        raise HubError(400, "invalid_bundle", "bundle 이 객체가 아니다")
    h = hash_token(str(invite or ""))
    with store.read() as conn:
        row = conn.execute(
            "SELECT for_project, expires_at, used_at FROM hub_invite WHERE code_hash = ?", (h,)
        ).fetchone()
    if row is None:
        raise HubError(403, "invalid_invite", "초대 코드가 없다")
    if row["used_at"]:
        raise HubError(403, "invite_used", "이미 쓴 초대 코드다")
    if row["expires_at"] <= _iso(ctx.now):
        raise HubError(403, "invite_expired", "초대 코드가 만료됐다")
    pid = str((bundle.get("project") or {}).get("id") or "")
    if pid != row["for_project"]:
        raise HubError(
            403,
            "invite_wrong_project",
            f"이 초대 코드는 {row['for_project']} 용이다 (묶음: {pid})",
            {"invite_project": row["for_project"], "bundle_project": pid},
        )
    out = Transfer(store).import_bundle(bundle, ctx.now)
    with store.write() as conn:
        conn.execute("UPDATE hub_invite SET used_at = ? WHERE code_hash = ?", (_iso(ctx.now), h))
    return out


def write_bundle(bundle: dict[str, Any], out: Path) -> None:
    out.write_text(json.dumps(bundle, ensure_ascii=False) + "\n", encoding="utf-8")
    try:
        out.chmod(0o600)  # 토큰 해시 · 프로젝트 기록 — 공유 디렉터리에 두지 않는다
    except OSError:
        pass
