"""프로젝트 지침 — 판 · 제안 · 승인 (hub_spec §6.5, 요구 R7.5 · R7.7 · D11 · Q3).

- 판을 올리는 것은 **승인된 사람 콜사인**뿐이다. 그가 고치면 제안이 곧 승인돼 판이 하나 오른다.
- 에이전트 · 승인 전 사람의 변경은 ``open`` 제안으로 남고, 승인된 사람이 승인해야 판이 오른다.
- 제안 · 승인은 기준 판(``base_version``)이 지금 판과 같을 때만 — 아니면 409 (그 사이 판이 오른 제안은
  새 판 위에서 다시 낸다, 자동 병합하지 않는다).
- 새 판이 될 본문은 지원 하네스 넷 모두에 렌더해 예산(R7.2)을 넘지 않는지 **판을 올리기 전에** 잰다 —
  넘는 판이 서면 그 뒤 모든 렌더 · 세션 시작이 깨진다.
"""

from __future__ import annotations

import difflib
import sqlite3
from typing import Any

from workflow_kit.hub import render
from workflow_kit.hub.errors import HubError, forbidden, invalid_field, not_found
from workflow_kit.hub.store import Ctx, Principal, Store, _iso, scan_secrets

#: 지침 본문 상한 — 렌더 예산(8KB)보다 넉넉한 입력 상한. 실제 판정은 렌더 예산이다.
BODY_MAX = 64 * 1024
NOTE_MAX = 500


def _is_editor(p: Principal) -> bool:
    return p.kind == "callsign" and p.callsign_kind == "human" and p.human_approved


def check_renderable(project_id: str, display: str, body: str) -> None:
    """새 판의 본문을 하네스 넷 모두에 렌더해 본다 — 예산을 넘으면 ``entry_budget_exceeded`` 422."""
    for harness in render.SUPPORTED_HARNESSES:
        render.render_region(harness, project_id, display, body, 0)


def _diff_lines(body: str) -> list[str]:
    """줄바꿈(\\n)으로만 나눈다. 끝에 줄바꿈이 없으면 표시를 붙여 그 차이도 보이게 한다."""
    if not body:
        return []
    lines = [f"{line}\n" for line in body.removesuffix("\n").split("\n")]
    if not body.endswith("\n"):
        lines[-1] += "\\ No newline at end of file\n"
    return lines


def unified(old: str, new: str, old_name: str, new_name: str) -> str:
    return "".join(difflib.unified_diff(_diff_lines(old), _diff_lines(new), fromfile=old_name, tofile=new_name))


class Guides:
    def __init__(self, store: Store) -> None:
        self.store = store

    # --- 읽기 -------------------------------------------------------------------------

    @staticmethod
    def _current(conn: sqlite3.Connection, project_id: str) -> tuple[int, str]:
        row = conn.execute("SELECT version, body_md FROM guide WHERE project_id = ? ORDER BY version DESC LIMIT 1",
                           (project_id,)).fetchone()
        return (row["version"], row["body_md"]) if row else (0, "")

    def get(self, ctx: Ctx) -> dict[str, Any]:
        """지금 판 · 판 이력 · 제안 (열린 제안은 지금 판 대비 diff 를 싣는다)."""
        p = self.store._need_reader(ctx)
        pid = p.project_id or ""
        with self.store.read() as conn:
            version, body = self._current(conn, pid)
            history = [dict(r) for r in conn.execute(
                "SELECT version, updated_by, updated_at, length(body_md) AS size FROM guide WHERE project_id = ? "
                "ORDER BY version DESC", (pid,))]
            proposals = [dict(r) for r in conn.execute(
                "SELECT id, base_version, body_md, note, proposed_by, proposed_at, status, decided_by, decided_at, "
                "applied_version FROM guide_proposal WHERE project_id = ? ORDER BY proposed_at DESC, id DESC LIMIT 100",
                (pid,))]
            bodies = {r["version"]: r["body_md"] for r in conn.execute(
                "SELECT version, body_md FROM guide WHERE project_id = ?", (pid,))}
        for prop in proposals:
            base = bodies.get(prop["base_version"], "")
            prop["diff"] = unified(base, prop["body_md"], f"v{prop['base_version']}", prop["id"])
            prop["stale"] = prop["status"] == "open" and prop["base_version"] != version
        return {"version": version, "guide_version": render.guide_version(version), "body": body,
                "history": history, "proposals": proposals}

    # --- 쓰기 -------------------------------------------------------------------------

    def _apply(self, conn: sqlite3.Connection, ctx: Ctx, pid: str, body: str, actor: str) -> int:
        version = self._current(conn, pid)[0] + 1
        conn.execute("INSERT INTO guide (project_id, version, body_md, updated_by, updated_at) VALUES (?, ?, ?, ?, ?)",
                     (pid, version, body, actor, _iso(ctx.now)))
        self.store._event(conn, ctx, pid, "guide", str(version), "set", None, {"version": version}, actor)
        return version

    def propose(self, ctx: Ctx, base_version: int, body: str, note: str = "") -> dict[str, Any]:
        """지침 변경 — 승인된 사람이면 바로 판 +1, 아니면 열린 제안 (R7.7)."""
        p = self.store._need_callsign(ctx)
        pid = p.project_id or ""
        if not isinstance(body, str) or len(body.encode("utf-8")) > BODY_MAX:
            raise invalid_field("body", f"문자열 · {BODY_MAX} 바이트 이하")
        if not isinstance(note, str) or len(note) > NOTE_MAX or "\n" in note:
            raise invalid_field("note", f"한 줄 · {NOTE_MAX}자 이하")
        scan_secrets({"body": body, "note": note})
        with self.store.write() as conn:
            current, current_body = self._current(conn, pid)
            if base_version != current:
                raise HubError(409, "version_conflict", f"지침 판이 그 사이 올랐다 — 지금 {current}",
                               {"current_version": current, "current": current_body})
            if body == current_body:
                raise invalid_field("body", "지금 판과 같다")
            display = conn.execute("SELECT display_name FROM project WHERE id = ?", (pid,)).fetchone()["display_name"]
            check_renderable(pid, display, body)
            n = conn.execute("SELECT COUNT(*) AS n FROM guide_proposal WHERE project_id = ?", (pid,)).fetchone()["n"] + 1
            prop_id = f"GP-{n:04d}"
            editor = _is_editor(p)
            conn.execute(
                "INSERT INTO guide_proposal (project_id, id, base_version, body_md, note, proposed_by, proposed_at, status, "
                "decided_by, decided_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (pid, prop_id, base_version, body, note, p.callsign, _iso(ctx.now), "approved" if editor else "open",
                 p.callsign if editor else None, _iso(ctx.now) if editor else None))
            self.store._event(conn, ctx, pid, "guide_proposal", prop_id, "propose", None,
                              {"base_version": base_version, "note": note, "direct": editor})
            applied = None
            if editor:
                applied = self._apply(conn, ctx, pid, body, p.callsign or "")
                conn.execute("UPDATE guide_proposal SET applied_version = ? WHERE project_id = ? AND id = ?",
                             (applied, pid, prop_id))
        return {"proposal_id": prop_id, "status": "approved" if editor else "open", "applied_version": applied,
                "guide_version": render.guide_version(applied) if applied else None,
                "next": None if editor else "승인된 human 콜사인이 hub_guide_decide 로 승인해야 판이 오른다"}

    def decide(self, ctx: Ctx, proposal_id: str, approve: bool) -> dict[str, Any]:
        """열린 제안의 승인 · 거절 — 승인된 사람 콜사인만 (R7.7 · D11)."""
        p = self.store._need_callsign(ctx)
        pid = p.project_id or ""
        if not _is_editor(p):
            raise forbidden("지침 제안의 승인 · 거절은 승인된 human 콜사인만 한다")
        with self.store.write() as conn:
            row = conn.execute("SELECT * FROM guide_proposal WHERE project_id = ? AND id = ?", (pid, proposal_id)).fetchone()
            if row is None:
                raise not_found(f"지침 제안이 없다: {proposal_id}")
            if row["status"] != "open":
                raise HubError(409, "already_decided", f"이미 {row['status']} 된 제안이다", {"status": row["status"]})
            applied = None
            if approve:
                current, current_body = self._current(conn, pid)
                if row["base_version"] != current:
                    raise HubError(409, "version_conflict",
                                   f"제안의 기준 판 {row['base_version']} 이 지금 판 {current} 이 아니다 — 새 판 위에서 다시 제안한다",
                                   {"current_version": current, "current": current_body})
                display = conn.execute("SELECT display_name FROM project WHERE id = ?", (pid,)).fetchone()["display_name"]
                check_renderable(pid, display, row["body_md"])
                applied = self._apply(conn, ctx, pid, row["body_md"], p.callsign or "")
            status = "approved" if approve else "rejected"
            conn.execute("UPDATE guide_proposal SET status = ?, decided_by = ?, decided_at = ?, applied_version = ? "
                         "WHERE project_id = ? AND id = ?", (status, p.callsign, _iso(ctx.now), applied, pid, proposal_id))
            self.store._event(conn, ctx, pid, "guide_proposal", proposal_id, "decide", {"status": "open"},
                              {"status": status, "applied_version": applied})
        return {"proposal_id": proposal_id, "status": status, "applied_version": applied,
                "guide_version": render.guide_version(applied) if applied else None}
