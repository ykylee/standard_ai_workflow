"""사람이 웹에서 로그인해 여는 실행 승인 — 대상에 묶이고, 만료되고, 한 번 쓰면 끝난다.

에이전트가 ``hub_approval_request(action=…)`` 로 요청하면 승인 기록을 ``pending`` 으로 남긴다. 화면에 보이는 실행 내용은
허브가 자기 데이터로 계산한다 — 에이전트가 쓴 설명은 참고일 뿐이다. 승인은 **계정 로그인 세션**만 한다: 소유자 콜사인
토큰은 에이전트도 들고 있을 수 있어 '사람이 봤다' 의 증거가 못 된다. 받은편지함 상태는 권한 근거로 쓰지 않는다.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import timedelta
from typing import Any

from workflow_kit.hub.errors import HubError, forbidden, invalid_field, not_found
from workflow_kit.hub.store import Ctx, Principal, Store, _iso, _json

GRANT_HOURS = 24
MARKER_SCOPE = {"issue": ("issue", "confirm"), "revert": ("revert", "confirm_revert")}
ACTION_FORM = "{type: migrate_import, migration_id, kinds} · {type: migrate_marker, migration_id, marker: issue|revert}"


def prepare(conn: sqlite3.Connection, project_id: str, raw: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    """요청한 실행 → (묶을 값, 화면에 보일 요약). 대상이 없거나 지금 할 수 없으면 거절한다."""
    from workflow_kit.hub.migrate1x import KINDS

    if not isinstance(raw, dict) or not isinstance(raw.get("migration_id"), str):
        raise invalid_field("action", ACTION_FORM)
    kind, mig = raw.get("type"), raw["migration_id"]
    allowed = {"migrate_import": {"type", "migration_id", "kinds"}, "migrate_marker": {"type", "migration_id", "marker"}}
    if not isinstance(kind, str) or kind not in allowed or set(raw) != allowed[kind]:
        raise invalid_field("action", ACTION_FORM)
    row = conn.execute("SELECT status, plan_json, callsign FROM migration_1x WHERE project_id = ? AND id = ?",
                       (project_id, mig)).fetchone()
    if row is None:
        raise not_found(f"전환 계획이 없다: {mig}")
    detected = json.loads(row["plan_json"])["detected"]
    summary: dict[str, Any] = {"migration_id": mig, "planned_by": row["callsign"], "branch": detected.get("branch", ""),
                               "head": detected.get("head", ""), "uncommitted": len(detected.get("uncommitted", []))}
    if kind == "migrate_import":
        kinds = raw["kinds"]
        if not isinstance(kinds, list) or not kinds or any(k not in KINDS for k in kinds):
            raise invalid_field("action.kinds", " · ".join(KINDS) + " 가운데 하나 이상")
        if row["status"] == "done":
            raise HubError(409, "already_done", f"{mig} 는 이미 끝난 전환이다")
        chosen = sorted(set(kinds))
        summary["files"] = {k: detected.get("counts", {}).get(k, 0) for k in chosen}
        return {"type": kind, "migration_id": mig, "kinds": chosen}, summary
    if raw["marker"] not in MARKER_SCOPE:
        raise invalid_field("action.marker", "issue · revert")
    if row["status"] != "done":
        raise HubError(409, "migration_not_done", f"{mig} 가 아직 끝나지 않았다")
    summary["marker"] = raw["marker"]
    return {"type": kind, "migration_id": mig, "marker": raw["marker"]}, summary


def insert(conn: sqlite3.Connection, ctx: Ctx, project_id: str, request_id: str, callsign: str, params: dict[str, Any],
           summary: dict[str, Any]) -> None:
    conn.execute("INSERT INTO approval_grant (id, project_id, action, params_json, summary_json, requested_by, state, created_at) "
                 "VALUES (?, ?, ?, ?, ?, ?, 'pending', ?)",
                 (request_id, project_id, params["type"], _json(params), _json(summary), callsign, _iso(ctx.now)))


def decide(conn: sqlite3.Connection, ctx: Ctx, request_id: str, approve: bool) -> bool:
    """승인 기록이 있는 요청이면 결정을 적는다 (없으면 False). 승인은 계정 로그인만 — 거절은 소유자면 된다."""
    p = ctx.principal
    assert p is not None
    row = conn.execute("SELECT state FROM approval_grant WHERE project_id = ? AND id = ?", (p.project_id, request_id)).fetchone()
    if row is None:
        return False
    if approve and (ctx.via != "ui" or p.auth_mode != "account"):
        raise HubError(403, "account_login_required", "실행을 여는 승인은 허브 계정으로 로그인한 화면에서만 한다")
    if row["state"] != "pending":
        raise HubError(409, "already_decided", "이미 결정한 실행 승인이다", {"state": row["state"]})
    conn.execute("UPDATE approval_grant SET state = ?, decided_by = ?, decided_account = ?, decided_at = ?, expires_at = ? "
                 "WHERE project_id = ? AND id = ?",
                 ("approved" if approve else "rejected", p.callsign, p.account_name, _iso(ctx.now),
                  _iso(ctx.now + timedelta(hours=GRANT_HOURS)) if approve else None, p.project_id, request_id))
    return True


def summaries(conn: sqlite3.Connection, project_id: str) -> dict[str, dict[str, Any]]:
    return {r["id"]: {"type": r["action"], "params": json.loads(r["params_json"]), "summary": json.loads(r["summary_json"])}
            for r in conn.execute("SELECT id, action, params_json, summary_json FROM approval_grant "
                                  "WHERE project_id = ? AND state = 'pending'", (project_id,))}


def authorize(store: Store, ctx: Ctx, approval_id: Any, action: str, **want: Any) -> Principal:
    """승인 기록으로 이 호출을 허용하는가 — 요청한 콜사인 · 대상 · 만료 · 승인자 자격을 모두 본다."""
    p = store._need_callsign(ctx)
    if not isinstance(approval_id, str) or not approval_id:
        raise forbidden("프로젝트 소유자(승인된 human)이거나, hub_approval_request(action=…) 로 받은 approval_id 가 필요하다")
    with store.read() as conn:
        row = conn.execute("SELECT * FROM approval_grant WHERE project_id = ? AND id = ?", (p.project_id, approval_id)).fetchone()
        owner = None if row is None or row["decided_by"] is None else conn.execute(
            "SELECT 1 FROM callsign WHERE project_id = ? AND id = ? AND revoked_at IS NULL AND role = 'owner' "
            "AND kind = 'human' AND human_approved = 1", (p.project_id, row["decided_by"])).fetchone()
    if row is None:
        raise not_found(f"실행 승인 요청이 없다: {approval_id}")
    params = json.loads(row["params_json"])
    scope = {k: v for k, v in params.items() if k != "type"}
    if row["requested_by"] != p.callsign or row["action"] != action or scope != want:
        raise HubError(403, "approval_mismatch", "승인한 콜사인 · 실행 · 대상과 다르다", {"approved": params})
    if row["state"] != "approved":
        raise HubError(403, f"approval_{row['state']}", f"실행 승인 상태: {row['state']}", {"state": row["state"]})
    if row["expires_at"] <= _iso(ctx.now):
        raise HubError(403, "approval_expired", "승인한 지 24시간이 지났다 — 다시 요청한다")
    if owner is None:
        raise HubError(403, "approval_revoked", "승인한 사람이 더 이상 프로젝트 소유자가 아니다")
    return p


def consume(conn: sqlite3.Connection, ctx: Ctx, project_id: str, approval_id: str) -> None:
    conn.execute("UPDATE approval_grant SET state = 'used', used_at = ? WHERE project_id = ? AND id = ?",
                 (_iso(ctx.now), project_id, approval_id))


__all__ = ["GRANT_HOURS", "MARKER_SCOPE", "authorize", "consume", "decide", "insert", "prepare", "summaries"]
