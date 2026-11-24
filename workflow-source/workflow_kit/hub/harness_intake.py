"""Untrusted client reports and the hub-admin reviewed global harness registry (M-060)."""

from __future__ import annotations

import json
import re
import secrets
from typing import Any
from urllib.parse import urlparse

from workflow_kit.hub.errors import HubError, invalid_field, unauthorized
from workflow_kit.hub.store import Ctx, Principal, Store, _iso, _json, scan_secrets

_ID = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,62}[a-z0-9])?$")
_SAFE_PATH = re.compile(r"^[A-Za-z0-9._/-]{1,160}$")
_FIELDS = {
    "harness_id", "display_name", "version", "platforms", "mcp_transports", "config_formats",
    "entry_file_candidates", "documentation_url", "notes",
}


def _bounded_text(value: Any, name: str, maximum: int, *, required: bool = False) -> str:
    if not isinstance(value, str) or len(value) > maximum or (required and not value.strip()):
        raise invalid_field(f"report.{name}", f"{('필수, ' if required else '')}{maximum}자 이하 문자열")
    return value.strip()


def _string_list(value: Any, name: str, maximum_items: int = 8) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or len(value) > maximum_items:
        raise invalid_field(f"report.{name}", f"문자열 목록 0~{maximum_items}개")
    out: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item or len(item) > 160:
            raise invalid_field(f"report.{name}", "각 항목은 1~160자 문자열")
        if item not in out:
            out.append(item)
    return out


def normalize_report(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise invalid_field("report", "하네스 프로필 객체")
    extra = set(raw) - _FIELDS
    if extra:
        raise HubError(400, "unknown_field", f"report 의 모르는 칸: {', '.join(sorted(extra))}",
                       {"fields": sorted(extra)})
    scan_secrets(raw, "report")
    harness_id = _bounded_text(raw.get("harness_id"), "harness_id", 64, required=True).lower()
    if not _ID.fullmatch(harness_id):
        raise invalid_field("report.harness_id", "소문자 영문·숫자와 내부 하이픈만 허용")
    paths = _string_list(raw.get("entry_file_candidates", []), "entry_file_candidates")
    for path in paths:
        if not _SAFE_PATH.fullmatch(path) or path.startswith(("/", "~")) or ".." in path.split("/") or "\\" in path or ":" in path:
            raise invalid_field("report.entry_file_candidates", "안전한 상대 경로만 허용")
    doc_url = _bounded_text(raw.get("documentation_url", ""), "documentation_url", 500)
    if doc_url:
        parsed = urlparse(doc_url)
        if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
            raise invalid_field("report.documentation_url", "인증 정보 없는 HTTPS URL")
    return {
        "harness_id": harness_id,
        "display_name": _bounded_text(raw.get("display_name"), "display_name", 100, required=True),
        "version": _bounded_text(raw.get("version", ""), "version", 80),
        "platforms": _string_list(raw.get("platforms", []), "platforms"),
        "mcp_transports": _string_list(raw.get("mcp_transports", []), "mcp_transports"),
        "config_formats": _string_list(raw.get("config_formats", []), "config_formats"),
        "entry_file_candidates": paths,
        "documentation_url": doc_url,
        "notes": _bounded_text(raw.get("notes", ""), "notes", 1000),
    }


def _callsign(ctx: Ctx) -> Principal:
    p = ctx.principal
    if p is None or p.kind != "callsign" or not p.project_id or not p.callsign:
        raise unauthorized("프로젝트 콜사인 토큰이 필요하다")
    return p


def _admin(ctx: Ctx) -> Principal:
    p = ctx.principal
    if p is None or p.kind != "admin":
        raise HubError(403, "forbidden", "hub admin 토큰만 전역 하네스 제보를 검토할 수 있다")
    return p


class HarnessIntake:
    def __init__(self, store: Store) -> None:
        self.store = store

    def submit(self, ctx: Ctx, raw: Any) -> dict[str, Any]:
        p = _callsign(ctx)
        report = normalize_report(raw)
        with self.store.write() as conn:
            existing = conn.execute(
                "SELECT id,status,submitted_at FROM harness_report WHERE project_id=? AND harness_id=? AND status='pending' "
                "ORDER BY submitted_at DESC LIMIT 1", (p.project_id, report["harness_id"]),
            ).fetchone()
            if existing:
                return {"report_id": existing["id"], "status": existing["status"], "replayed": True}
            report_id = "HR-" + secrets.token_hex(6)
            conn.execute(
                "INSERT INTO harness_report(id,project_id,harness_id,report_json,submitted_by,client_version,submitted_at,status) "
                "VALUES(?,?,?,?,?,?,?,'pending')",
                (report_id, p.project_id, report["harness_id"], _json(report), p.callsign, ctx.client_version or "", _iso(ctx.now)),
            )
            self.store._event(conn, ctx, p.project_id, "harness_report", report_id, "submit", None,
                              {"harness_id": report["harness_id"], "status": "pending"}, p.callsign)
        return {"report_id": report_id, "harness_id": report["harness_id"], "status": "pending",
                "registered": False, "next": "hub admin 검토 후 등록 여부가 결정된다"}

    def list_reports(self, ctx: Ctx, status: str = "") -> dict[str, Any]:
        p = ctx.principal
        if p is None or p.kind not in {"callsign", "admin"}:
            raise unauthorized()
        if status and status not in {"pending", "approved", "rejected"}:
            raise invalid_field("status", "pending · approved · rejected")
        with self.store.read() as conn:
            if p.kind == "admin":
                sql = "SELECT id,project_id,harness_id,report_json,submitted_by,client_version,submitted_at,status,reviewed_by,reviewed_at,decision_note FROM harness_report"
                params: tuple[Any, ...] = ()
            else:
                _callsign(ctx)
                sql = "SELECT id,project_id,harness_id,report_json,submitted_by,client_version,submitted_at,status,reviewed_by,reviewed_at,decision_note FROM harness_report WHERE project_id=?"
                params = (p.project_id,)
            if status:
                sql += " AND " if " WHERE " in sql else " WHERE "
                sql += "status=?"
                params += (status,)
            sql += " ORDER BY submitted_at DESC LIMIT 200"
            rows = conn.execute(sql, params).fetchall()
        reports = []
        for row in rows:
            item = dict(row)
            item["report"] = json.loads(item.pop("report_json"))
            reports.append(item)
        return {"reports": reports}

    def registry_list(self, ctx: Ctx, include_inactive: bool = False) -> dict[str, Any]:
        p = ctx.principal
        if p is None or p.kind not in {"callsign", "admin"}:
            raise unauthorized()
        if include_inactive and p.kind != "admin":
            raise HubError(403, "forbidden", "비활성 등록부 조회는 hub admin만 가능하다")
        query = "SELECT harness_id,display_name,profile_json,source_report_id,version,active,registered_by,registered_at FROM harness_registry"
        if not include_inactive:
            query += " WHERE active=1"
        query += " ORDER BY harness_id"
        with self.store.read() as conn:
            rows = conn.execute(query).fetchall()
        items = []
        for row in rows:
            item = dict(row)
            item["active"] = bool(item["active"])
            item["profile"] = json.loads(item.pop("profile_json"))
            item["owners"] = self._owners(item["harness_id"])
            item["setup_ready"] = False
            items.append(item)
        return {"harnesses": items}

    def _owners(self, harness_id: str) -> list[dict[str, Any]]:
        with self.store.read() as conn:
            rows = conn.execute(
                "SELECT p.id,p.display_name FROM harness_registry_person rp JOIN harness_person p ON p.id=rp.person_id "
                "WHERE rp.harness_id=? AND p.active=1 ORDER BY p.display_name,p.id", (harness_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def list_people(self, ctx: Ctx) -> dict[str, Any]:
        _admin(ctx)
        with self.store.read() as conn:
            rows = conn.execute(
                "SELECT id,display_name,created_by,created_at FROM harness_person WHERE active=1 ORDER BY display_name,id"
            ).fetchall()
        return {"people": [dict(row) for row in rows]}

    def create_person(self, ctx: Ctx, display_name: str) -> dict[str, Any]:
        p = _admin(ctx)
        display_name = _bounded_text(display_name, "display_name", 100, required=True)
        scan_secrets({"display_name": display_name}, "person")
        person_id = "HP-" + secrets.token_hex(6)
        with self.store.write() as conn:
            conn.execute(
                "INSERT INTO harness_person(id,display_name,created_by,created_at) VALUES(?,?,?,?)",
                (person_id, display_name, p.name or "hub-admin", _iso(ctx.now)),
            )
        return {"person": {"id": person_id, "display_name": display_name}}

    def decide(self, ctx: Ctx, report_id: str, decision: str, note: str = "",
               owner_ids: Any = None) -> dict[str, Any]:
        p = _admin(ctx)
        if decision not in {"approve", "reject"}:
            raise invalid_field("decision", "approve · reject")
        note = _bounded_text(note, "note", 1000)
        if decision == "approve":
            if not isinstance(owner_ids, list) or not owner_ids or len(owner_ids) > 20:
                raise invalid_field("owner_ids", "승인 등록에 사람 담당자 1~20명을 지정해야 한다")
            if any(not isinstance(item, str) or not item for item in owner_ids) or len(set(owner_ids)) != len(owner_ids):
                raise invalid_field("owner_ids", "등록된 사람 ID의 중복 없는 목록이어야 한다")
        with self.store.write() as conn:
            row = conn.execute(
                "SELECT project_id,harness_id,report_json,status FROM harness_report WHERE id=?", (report_id,),
            ).fetchone()
            if row is None:
                raise HubError(404, "not_found", f"하네스 제보가 없다: {report_id}")
            if row["status"] != "pending":
                raise HubError(409, "version_conflict", "이미 검토가 끝난 제보다", {"status": row["status"]})
            if decision == "approve":
                placeholders = ",".join("?" for _ in owner_ids)
                people = conn.execute(
                    f"SELECT id FROM harness_person WHERE active=1 AND id IN ({placeholders})", tuple(owner_ids),
                ).fetchall()
                if len(people) != len(owner_ids):
                    raise invalid_field("owner_ids", "활성 사람 명부에서 담당자를 선택해야 한다")
                report = json.loads(row["report_json"])
                conn.execute(
                    "INSERT INTO harness_registry(harness_id,display_name,profile_json,source_report_id,version,active,registered_by,registered_at) "
                    "VALUES(?,?,?,?,1,1,?,?) ON CONFLICT(harness_id) DO UPDATE SET display_name=excluded.display_name, "
                    "profile_json=excluded.profile_json,source_report_id=excluded.source_report_id,version=harness_registry.version+1, "
                    "active=1,registered_by=excluded.registered_by,registered_at=excluded.registered_at",
                    (row["harness_id"], report["display_name"], _json(report), report_id, p.name or "hub-admin", _iso(ctx.now)),
                )
                conn.execute("DELETE FROM harness_registry_person WHERE harness_id=?", (row["harness_id"],))
                conn.executemany(
                    "INSERT INTO harness_registry_person(harness_id,person_id,assigned_by,assigned_at) VALUES(?,?,?,?)",
                    [(row["harness_id"], person_id, p.name or "hub-admin", _iso(ctx.now)) for person_id in owner_ids],
                )
            conn.execute("UPDATE harness_report SET status=?,reviewed_by=?,reviewed_at=?,decision_note=? WHERE id=? AND status='pending'",
                         ("approved" if decision == "approve" else "rejected", p.name or "hub-admin", _iso(ctx.now), note, report_id))
            self.store._event(conn, ctx, row["project_id"], "harness_report", report_id, decision,
                              {"status": "pending"}, {"status": "approved" if decision == "approve" else "rejected",
                                                        "harness_id": row["harness_id"], "note": note}, p.name or "hub-admin")
        return {"report_id": report_id, "harness_id": row["harness_id"],
                "status": "approved" if decision == "approve" else "rejected",
                "registered": decision == "approve", "setup_ready": False,
                "owners": self._owners(row["harness_id"]) if decision == "approve" else []}
