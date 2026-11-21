"""콜사인별 작업 기억 — handoff · 세션 끝 · compact 체크포인트 · 상태 요약 (hub_spec §3.3 · §6.3 · §6.4,
요구 R4.5 · R4.6 · R6 · R11 · G1 · G2).

- handoff 는 **콜사인 하나에 하나** (G1). 쓰기는 그 콜사인만, 읽기는 프로젝트 안 누구나 (G3).
- 최근 완료는 ``TASK-`` 로 시작하고 10건까지 — 넘친 것은 지우지 않고 ``memory_note(handoff_rollover)`` 로
  **옮긴다** (R6.2, 1.x 규칙).
- 상태 요약(``state.json`` v1)은 허브 데이터를 임시 디렉터리에 **1.x 배치로 펼쳐** 1.x 생성기
  ``build_workflow_state_payload`` 로 만든다 — 같은 함수 · 같은 형식 (R0.1 · R0.7 · R6.3).
"""

from __future__ import annotations

import json
import re
import sqlite3
import tempfile
from pathlib import Path
from typing import Any

from workflow_kit.common.paths import HANDOFF_FILENAME, memory_active_dir, path_in_active
from workflow_kit.common.project_docs import TASK_ID_PATTERN
from workflow_kit.hub.errors import HubError, forbidden, invalid_field, not_found
from workflow_kit.hub.store import Ctx, Store, _iso, _json, scan_secrets

RECENT_DONE_MAX = 10
#: 프로젝트 문서 이름 (판 9) — 1.x 의 PURPOSE.md · PROJECT_PROFILE.md.
PROJECT_DOCS = ("purpose", "profile")
_LIST_KEYS = ("in_progress", "blocked", "recent_done", "next", "risks")
_STR_KEYS = ("baseline", "focus")
_TASK_ID = re.compile(TASK_ID_PATTERN)
_IDENT = re.compile(r"`([^`]{2,80})`")


def _validate_sections(sections: Any) -> dict[str, Any]:
    if not isinstance(sections, dict):
        raise invalid_field("handoff", "객체여야 한다")
    extra = set(sections) - set(_LIST_KEYS) - set(_STR_KEYS)
    if extra:
        raise HubError(400, "unknown_field", f"handoff 의 모르는 칸: {', '.join(sorted(extra))}", {"fields": sorted(extra)})
    out: dict[str, Any] = {}
    for k in _STR_KEYS:
        v = sections.get(k, "")
        if not isinstance(v, str):
            raise invalid_field(f"handoff.{k}", "문자열")
        out[k] = v
    for k in _LIST_KEYS:
        v = sections.get(k, [])
        if not isinstance(v, list) or not all(isinstance(x, str) and x.strip() for x in v):
            raise invalid_field(f"handoff.{k}", "비지 않은 문자열 목록")
        out[k] = [x.strip() for x in v]
    for k in ("in_progress", "blocked", "recent_done"):
        bad = [x for x in out[k] if not x.startswith("TASK-")]
        if bad:
            raise invalid_field(f"handoff.{k}", f"항목은 TASK- 로 시작한다 (R6.2): {bad[0]!r}")
    scan_secrets(out, "handoff")
    return out


class Memory:
    def __init__(self, store: Store) -> None:
        self.store = store

    # --- 프로젝트 문서 (PURPOSE · PROJECT_PROFILE) ---------------------------------------------

    def doc_get(self, ctx: Ctx, name: str) -> dict[str, Any]:
        p = self.store._need_reader(ctx)
        if name not in PROJECT_DOCS:
            raise invalid_field("name", " · ".join(PROJECT_DOCS))
        with self.store.read() as conn:
            row = conn.execute("SELECT body_md, version, updated_by, updated_at FROM project_doc WHERE project_id = ? AND name = ?",
                               (p.project_id, name)).fetchone()
        if row is None:
            return {"name": name, "body": None, "version": 0}
        return {"name": name, "body": row["body_md"], "version": row["version"], "updated_by": row["updated_by"],
                "updated_at": row["updated_at"]}

    def doc_put(self, ctx: Ctx, name: str, body: str, expected_version: int | None, *, actor: str | None = None,
                conn: sqlite3.Connection | None = None) -> dict[str, Any]:
        """프로젝트 문서 쓰기 — 승인된 human 만 (지침과 같은 기준: 모든 환경의 방향을 바꾼다). 새 문서는 0."""
        p = self.store._need_callsign(ctx)
        if conn is None and (p.callsign_kind != "human" or not p.human_approved):
            raise forbidden("프로젝트 문서는 승인된 human 콜사인이 쓴다")
        if name not in PROJECT_DOCS:
            raise invalid_field("name", " · ".join(PROJECT_DOCS))
        if not isinstance(body, str) or not body.strip() or len(body.encode("utf-8")) > 192 * 1024:
            raise invalid_field("body", "비지 않은 문자열 · 192KB 이하")
        scan_secrets(body, "body")

        def do(c: sqlite3.Connection) -> dict[str, Any]:
            row = c.execute("SELECT version FROM project_doc WHERE project_id = ? AND name = ?", (p.project_id, name)).fetchone()
            current = row["version"] if row else 0
            if expected_version is not None and expected_version != current:
                raise HubError(409, "version_conflict", f"version 이 다르다 — 지금 {current}", {"current_version": current})
            c.execute("INSERT INTO project_doc (project_id, name, body_md, version, updated_by, updated_at) VALUES (?, ?, ?, 1, ?, ?) "
                      "ON CONFLICT(project_id, name) DO UPDATE SET body_md = excluded.body_md, version = project_doc.version + 1, "
                      "updated_by = excluded.updated_by, updated_at = excluded.updated_at",
                      (p.project_id, name, body, actor or p.callsign, _iso(ctx.now)))
            self.store._event(c, ctx, p.project_id, "project_doc", name, "put", {"version": current}, {"version": current + 1})
            return {"name": name, "version": current + 1}

        if conn is not None:
            return do(conn)
        with self.store.write() as c:
            return do(c)

    # --- handoff ----------------------------------------------------------------------

    def handoff_get(self, ctx: Ctx, callsign: str | None) -> dict[str, Any]:
        p = self.store._need_reader(ctx)
        who = callsign or p.callsign
        if not who:
            raise invalid_field("callsign", "필수 (화면에서 읽을 때)")
        with self.store.read() as conn:
            row = conn.execute("SELECT sections_json, version, updated_at FROM handoff WHERE project_id = ? AND callsign = ?",
                               (p.project_id, who)).fetchone()
            cs = conn.execute("SELECT revoked_at FROM callsign WHERE project_id = ? AND id = ?", (p.project_id, who)).fetchone()
        if cs is None:
            raise not_found(f"콜사인이 없다: {who}")
        if row is None:
            return {"callsign": who, "handoff": None, "version": 0, "archived": cs["revoked_at"] is not None}
        return {"callsign": who, "handoff": json.loads(row["sections_json"]), "version": row["version"],
                "updated_at": row["updated_at"], "archived": cs["revoked_at"] is not None}

    def _put(self, conn: sqlite3.Connection, ctx: Ctx, expected_version: int | None, sections: dict[str, Any]) -> dict[str, Any]:
        p = self.store._need_callsign(ctx)
        row = conn.execute("SELECT sections_json, version FROM handoff WHERE project_id = ? AND callsign = ?",
                           (p.project_id, p.callsign)).fetchone()
        current = row["version"] if row else 0
        if expected_version is not None and expected_version != current:
            raise HubError(409, "version_conflict", f"version 이 다르다 — 지금 {current}",
                           {"current_version": current, "current": json.loads(row["sections_json"]) if row else None})
        moved = sections["recent_done"][RECENT_DONE_MAX:]
        sections = {**sections, "recent_done": sections["recent_done"][:RECENT_DONE_MAX]}
        for item in moved:
            conn.execute(
                "INSERT INTO memory_note (project_id, callsign, kind, title, body_md, meta_json, created_at) "
                "VALUES (?, ?, 'handoff_rollover', ?, ?, '{}', ?)",
                (p.project_id, p.callsign, item.split()[0], item, _iso(ctx.now)))
        conn.execute(
            "INSERT INTO handoff (project_id, callsign, sections_json, updated_at, version) VALUES (?, ?, ?, ?, 1) "
            "ON CONFLICT(project_id, callsign) DO UPDATE SET sections_json = excluded.sections_json, "
            "updated_at = excluded.updated_at, version = handoff.version + 1",
            (p.project_id, p.callsign, _json(sections), _iso(ctx.now)))
        self.store._event(conn, ctx, p.project_id, "handoff", p.callsign or "", "put", {"version": current},
                          {"version": current + 1, "rolled_over": len(moved)})
        return {"callsign": p.callsign, "version": current + 1, "rolled_over": moved}

    def handoff_put(self, ctx: Ctx, expected_version: int | None, sections: Any, callsign: str | None = None) -> dict[str, Any]:
        p = self.store._need_callsign(ctx)
        if callsign and callsign != p.callsign:
            raise forbidden("다른 콜사인의 handoff 는 쓸 수 없다 (G3)")
        clean = _validate_sections(sections)
        with self.store.write() as conn:
            return self._put(conn, ctx, expected_version, clean)

    def session_end(self, ctx: Ctx, handoff: Any, expected_version: int | None, progress: Any) -> dict[str, Any]:
        """handoff 와 진행 한 줄들을 **한 트랜잭션**으로 (hub_spec §6.3, R6.4)."""
        p = self.store._need_callsign(ctx)
        clean = _validate_sections(handoff)
        if not isinstance(progress, list) or not all(isinstance(x, dict) and set(x) == {"task_id", "note"} for x in progress):
            raise invalid_field("progress", "[{task_id, note}]")
        stamp = ctx.now.strftime("%Y-%m-%d %H:%M")
        with self.store.write() as conn:
            for item in progress:
                scan_secrets(item["note"], "progress.note")
                task = self.store._get_task(conn, p.project_id or "", item["task_id"])
                conn.execute("UPDATE task SET progress_note = ?, progress_at = ?, version = version + 1, updated_at = ? "
                             "WHERE project_id = ? AND id = ?",
                             (f"[{stamp}] {item['note'].strip()}", _iso(ctx.now), _iso(ctx.now), p.project_id, item["task_id"]))
                self.store._event(conn, ctx, p.project_id, "task", item["task_id"], "progress",
                                  {"progress_note": task["progress_note"]}, {"progress_note": item["note"].strip()})
            out = self._put(conn, ctx, expected_version, clean)
        return {**out, "progress_written": len(progress),
                "next": "커밋 → push. 진입 파일의 허브 렌더 영역이 바뀌었으면 그 변경도 커밋한다 (D10)"}

    # --- compact (R11) ----------------------------------------------------------------

    def checkpoint_put(self, ctx: Ctx, body: Any) -> dict[str, Any]:
        p = self.store._need_callsign(ctx)
        allowed = {"next", "unverified", "verified", "rejected", "tasks", "branch"}
        if not isinstance(body, dict) or set(body) - allowed:
            raise invalid_field("body", f"칸은 {', '.join(sorted(allowed))} (compact_relay_spec §3)")
        scan_secrets(body, "checkpoint")
        with self.store.write() as conn:
            conn.execute("INSERT INTO checkpoint (project_id, callsign, created_at, body_json) VALUES (?, ?, ?, ?)",
                         (p.project_id, p.callsign, _iso(ctx.now), _json(body)))
            self.store._event(conn, ctx, p.project_id, "checkpoint", p.callsign or "", "put", None,
                              {"keys": sorted(body)})
        return {"callsign": p.callsign, "created_at": _iso(ctx.now)}

    def compact_resume(self, ctx: Ctx, summary_ids: list[str] | None) -> dict[str, Any]:
        p = self.store._need_callsign(ctx)
        with self.store.read() as conn:
            row = conn.execute("SELECT created_at, body_json FROM checkpoint WHERE project_id = ? AND callsign = ? "
                               "ORDER BY created_at DESC, rowid DESC LIMIT 1", (p.project_id, p.callsign)).fetchone()
            mine = [dict(r) for r in conn.execute(
                "SELECT id, title, status, version, progress_note FROM task WHERE project_id = ? AND assignee = ? AND status != 'done'",
                (p.project_id, p.callsign))]
            # '그 사이' 는 시각이 아니라 이벤트 순번으로 잰다 — 초 단위 시각은 같은 초의 변경을 놓친다.
            mark = conn.execute("SELECT MAX(seq) AS s FROM event WHERE project_id = ? AND target_kind = 'checkpoint' "
                                "AND callsign = ?", (p.project_id, p.callsign)).fetchone()
            since_seq = mark["s"] if mark and mark["s"] is not None else 0
            others = [dict(r) for r in conn.execute(
                "SELECT seq, at, callsign, target_id, op FROM event WHERE project_id = ? AND target_kind = 'task' AND seq > ? "
                "AND callsign IS NOT ? AND target_id IN (SELECT id FROM task WHERE project_id = ? AND assignee = ?) ORDER BY seq",
                (p.project_id, since_seq, p.callsign, p.project_id, p.callsign))] if row else []
        if row is None:
            return {"checkpoint": None, "my_tasks": mine, "changed_by_others": [],
                    "missing_from_summary": None, "note": "체크포인트가 없다 — 진행 기록과 내 task 에서 잇는다"}
        body = json.loads(row["body_json"])
        text = json.dumps(body, ensure_ascii=False)
        idents = sorted(set(_TASK_ID.findall(text)) | set(_IDENT.findall(text)))
        missing: list[str] | None
        if summary_ids is None:
            missing = None
        else:
            have = set(summary_ids)
            missing = [i for i in idents if i not in have]
        return {
            "checkpoint": {"created_at": row["created_at"], **body},
            "my_tasks": mine,
            "changed_by_others": others,
            "missing_from_summary": missing,
            "compare": "대조 불가 — 요약 식별자를 받지 못했다" if missing is None else "대조함",
            "rule": "끝난 것으로 기록된 일을 다시 하지 않고, unverified 는 미검증으로 보고한다",
        }

    # --- 상태 요약 (state.json v1) ------------------------------------------------------

    def state(self, ctx: Ctx, callsign: str | None) -> dict[str, Any]:
        p = self.store._need_callsign(ctx)
        who = callsign or p.callsign or ""
        with self.store.read() as conn:
            tasks = [self.store._task_row(r) for r in conn.execute(
                "SELECT * FROM task WHERE project_id = ? ORDER BY created_at, id", (p.project_id,))]
            row = conn.execute("SELECT sections_json FROM handoff WHERE project_id = ? AND callsign = ?",
                               (p.project_id, who)).fetchone()
            proj = conn.execute("SELECT display_name FROM project WHERE id = ?", (p.project_id,)).fetchone()
            docs = {r["name"]: r["body_md"] for r in conn.execute(
                "SELECT name, body_md FROM project_doc WHERE project_id = ?", (p.project_id,))}
        sections = json.loads(row["sections_json"]) if row else None
        with tempfile.TemporaryDirectory(prefix="hub-state-") as d:
            root = Path(d)
            profile = materialize(root, who, proj["display_name"], sections, tasks, docs)
            from workflow_kit.common.state.builder import build_workflow_state_payload

            handoff_path = path_in_active(memory_active_dir(root), HANDOFF_FILENAME, who)
            branch_dir = handoff_path.parent
            backlogs = sorted((branch_dir / "backlog").glob("*.md"))
            payload = build_workflow_state_payload(
                project_profile_path=profile,
                session_handoff_path=handoff_path,
                daily_backlog_dir=branch_dir / "backlog",
                tasks_dir=branch_dir / "backlog" / "tasks",
                sessions_dir=branch_dir / "sessions",
                latest_backlog_path=backlogs[-1] if backlogs else None,
                generated_at=ctx.now.strftime("%Y-%m-%d"),
                workspace_root=root,
            )
        return {"callsign": who, "state": json.loads(json.dumps(payload, ensure_ascii=False, default=str).replace(str(root), "<hub>"))}


def render_handoff(sections: dict[str, Any] | None, titles: dict[str, str]) -> str:
    s = sections or {k: ([] if k in _LIST_KEYS else "") for k in (*_LIST_KEYS, *_STR_KEYS)}

    def items(key: str) -> str:
        vals = s.get(key) or []
        return "".join(f"- {v}{(' — ' + titles[v]) if v in titles else ''}\n" for v in vals) or "-\n"

    return (
        "# Session Handoff\n\n"
        f"## 1. 현재 작업 요약\n\n- 현재 기준선: {s.get('baseline') or '-'}\n- 현재 주 작업 축: {s.get('focus') or '-'}\n\n"
        f"## 2. 진행 중 작업\n\n- 현재 `in_progress` 작업:\n{items('in_progress')}\n"
        f"## 3. 차단 작업\n\n- 현재 `blocked` 작업:\n{items('blocked')}\n"
        f"## 4. 최근 완료 작업\n\n- 최근 완료 작업 목록:\n{items('recent_done')}\n"
        f"## 5. 다음 세션 시작 포인트\n\n" + "".join(f"- {v}\n" for v in s.get("next") or ["-"]) + "\n"
        f"## 6. 남은 리스크\n\n" + "".join(f"- {v}\n" for v in s.get("risks") or ["-"])
    )


def render_task(t: dict[str, Any]) -> str:
    date = t["id"].split("-")[1:4]
    created = "-".join(date)
    fm = [f"id: {t['id']}", f"status: {t['status']}", f"created_at: {created}",
          f"source_anchor: generic-{t['id'].lower()}", f"source_path: backlog/{created}.md", "kind: generic"]
    if t.get("wbs"):
        fm.append(f"wbs: {t['wbs']}")
    body = f"---\n" + "\n".join(fm) + f"\n---\n\n# {t['id']} — {t['title']}\n\n## 📝 Description\n\n- Status: {t['status']}\n"
    if t.get("plan_md", "").strip():
        body += "\n## 🧭 Plan\n\n" + t["plan_md"].rstrip() + "\n"
    if t.get("progress_note"):
        body += f"\n## 🛠️ Implementation / Content\n\n- Progress: {t['progress_note']}\n"
    return body


def materialize(root: Path, callsign: str, display: str, sections: dict[str, Any] | None,
                tasks: list[dict[str, Any]], docs: dict[str, str] | None = None) -> Path:
    """허브 데이터 → 1.x 배치 (state 생성기 입력). 프로필 경로를 돌려준다.

    프로젝트 문서(``project_doc`` — PURPOSE · PROJECT_PROFILE)가 있으면 1.x 자리에 펼쳐 목적 · 프로젝트 칸이 찬다.
    """
    docs = docs or {}
    (root / "docs").mkdir(parents=True)
    profile = root / "docs" / "PROJECT_PROFILE.md"
    profile.write_text(docs.get("profile") or f"# {display}\n", encoding="utf-8")
    if docs.get("purpose"):
        purpose = memory_active_dir(root) / "PURPOSE.md"
        purpose.parent.mkdir(parents=True, exist_ok=True)
        purpose.write_text(docs["purpose"], encoding="utf-8")
    handoff_path = path_in_active(memory_active_dir(root), HANDOFF_FILENAME, callsign)
    branch_dir = handoff_path.parent
    (branch_dir / "backlog" / "tasks").mkdir(parents=True)
    (branch_dir / "sessions").mkdir(parents=True)
    titles = {t["id"]: t["title"] for t in tasks}
    handoff_path.write_text(render_handoff(sections, titles), encoding="utf-8")
    by_date: dict[str, list[dict[str, Any]]] = {}
    for t in tasks:
        by_date.setdefault("-".join(t["id"].split("-")[1:4]), []).append(t)
        (branch_dir / "backlog" / "tasks" / f"{t['id']}.md").write_text(render_task(t), encoding="utf-8")
    for date, items in sorted(by_date.items()):
        lines = [f"# Daily Backlog — {date}\n\n"]
        for t in items:
            lines.append(f"- **{t['id']}** [generic] {t['title']}\n"
                         f"  - path: [`./tasks/{t['id']}.md`](./tasks/{t['id']}.md)\n  - status: {t['status']}\n")
        (branch_dir / "backlog" / f"{date}.md").write_text("".join(lines), encoding="utf-8")
    return profile
