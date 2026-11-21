"""허브 위키 (M-036 WBS-36.1) — 페이지 · ingest 묶음 · index/log 생성 · 읽기 · lint.

정본: ``core/hub_spec.md`` §3.3 · §4.5 · §6.7 (요구 R8.1 · R8.2 · R8.3 · R8.5, concept §11.3 · E1 · E2 · E4).

- **ingest 묶음 하나 = 트랜잭션 하나** — 페이지마다 ``expected_version`` 을 대조하고(새 페이지는 0),
  하나라도 어긋나면 묶음 전체를 409 로 거절한다 (부분 반영 0). ``log`` 항목은 허브가 만든다.
- **index.md · log.md 는 생성물** — 저장하지 않고, 페이지와 ingest 기록에서 그때그때 만든다.
  손으로 쓰려 하면 거절한다 (anchor 구조는 허브가 지킨다 — 1.x R4 · V-4).
- **lint** — 페이지를 임시 디렉터리에 ``ai-workflow/wiki/…`` 배치로 펼쳐, 1.x 검사와 **같은 함수**
  (``common.wiki_rules``) 로 V-1 정위치 · V-4 index 구조를 재고, 깨진 위키 링크를 새로 잰다.
  저장소 참조 · freshness 는 원격 읽기(R8.4, WBS-36.2) 전이라 **'미측정'** 이다 — 통과가 아니다.
"""

from __future__ import annotations

import json
import re
import sqlite3
import tempfile
from pathlib import Path
from typing import Any

from workflow_kit.common.wiki_rules import check_canonical_location, classify_wikilinks, validate_index
from workflow_kit.hub.errors import HubError, invalid_field
from workflow_kit.hub.store import Ctx, Store, _iso, scan_secrets

#: 생성물 — 페이지로 쓸 수 없다.
GENERATED = ("index.md", "log.md")
#: 위키 안 상대 경로 — 조각마다 영숫자로 시작, ``..`` · 절대 경로 · 백슬래시 없음, ``.md`` 로 끝.
_PATH = re.compile(r"^(?:[A-Za-z0-9_][A-Za-z0-9_.-]*/)*[A-Za-z0-9_][A-Za-z0-9_.-]*\.md$")
MAX_PAGES = 200
#: 페이지 하나 — HTTP 요청 본문 상한(256KB) 아래. 더 큰 묶음은 여러 ingest 로 나눈다.
MAX_BODY = 192 * 1024
INDEX_TITLE = "# Master Knowledge Index"
#: 1.x SCHEMA 의 종류 디렉터리 → index 절 제목. 목록 밖 디렉터리는 이름을 그대로 절 제목으로 쓴다.
SECTION_TITLES = {
    "concepts": "Concepts", "decisions": "Decisions", "entities": "Entities", "patterns": "Patterns",
    "queries": "Queries", "sources": "Sources", "topics": "Topics", "": "Meta",
}
_FM_TITLE = re.compile(r"^title:\s*(.+?)\s*$", re.M)
_H1 = re.compile(r"^# (.+)$", re.M)


def check_path(path: Any, field: str = "path") -> str:
    if not isinstance(path, str) or not _PATH.match(path) or ".." in path.split("/"):
        raise invalid_field(field, "위키 안 상대 경로 · .md (예: concepts/foo.md)")
    if path in GENERATED:
        raise invalid_field(field, f"{path} 는 허브가 생성한다 — 쓸 수 없다")
    return path


def page_title(path: str, body: str) -> str:
    """frontmatter ``title:`` → 첫 ``# `` 제목 → 경로."""
    if body.startswith("---\n"):
        end = body.find("\n---", 4)
        if end > 0:
            m = _FM_TITLE.search(body[4:end])
            if m:
                return m.group(1).strip().strip("\"'")
    m = _H1.search(body)
    return m.group(1).strip() if m else path[:-3]


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "page"


def render_index(paths: list[str]) -> str:
    """R4 anchor 구조 index — 절은 첫 디렉터리(SCHEMA 종류), 항목은 경로 순. anchor 는 파일 이름,
    겹치면 경로 전체를 slug 로 (V-4 의 anchor 유일 규칙)."""
    stems = [p[:-3] for p in sorted(paths)]
    base_count: dict[str, int] = {}
    for st in stems:
        base_count[_slug(st.rsplit("/", 1)[-1])] = base_count.get(_slug(st.rsplit("/", 1)[-1]), 0) + 1
    sections: dict[str, list[str]] = {}
    for st in stems:
        top = st.split("/", 1)[0] if "/" in st else ""
        base = _slug(st.rsplit("/", 1)[-1])
        anchor = base if base_count[base] == 1 else _slug(st)
        sections.setdefault(top, []).append(f"### [[{st}]] {{#{anchor}}}")
    order = sorted(sections, key=lambda k: (k == "", list(SECTION_TITLES).index(k) if k in SECTION_TITLES else 99, k))
    out = [INDEX_TITLE, ""]
    for key in order:
        out += [f"## {SECTION_TITLES.get(key, key)}", "", *sections[key], ""]
    return "\n".join(out).rstrip("\n") + "\n"


def render_log(ingests: list[dict[str, Any]]) -> str:
    """ingest 기록 → log.md (오래된 것부터 — 1.x log 의 append-only 순서)."""
    out = ["# Wiki Ingest Log", "", "- 허브가 ingest 기록에서 생성한다 — 손으로 고치지 않는다.", ""]
    for ing in ingests:
        pages = json.loads(ing["pages_json"])
        out += [ing["log_line"], "",
                f"- {ing['id']} · {ing['callsign']} · {ing['at']}",
                "- " + ", ".join(f"{p['path']} ({'삭제' if p.get('deleted') else 'v' + str(p['version'])})" for p in pages),
                ""]
    return "\n".join(out).rstrip("\n") + "\n"


class Wiki:
    def __init__(self, store: Store) -> None:
        self.store = store

    def _pid(self, ctx: Ctx) -> str:
        pid = self.store._need_callsign(ctx).project_id
        assert pid is not None
        return pid

    # --- 쓰기 -------------------------------------------------------------------

    def ingest(self, ctx: Ctx, pages: list[Any], summary: str, request_id: str | None = None) -> dict[str, Any]:
        p = self.store._need_callsign(ctx)
        pid = p.project_id
        assert pid is not None
        if not isinstance(summary, str) or not summary.strip() or "\n" in summary.strip():
            raise invalid_field("summary", "한 줄 요약이 필요하다")
        if not isinstance(pages, list) or not pages:
            raise invalid_field("pages", "페이지가 하나 이상 필요하다")
        if len(pages) > MAX_PAGES:
            raise invalid_field("pages", f"한 묶음은 {MAX_PAGES} 페이지까지")
        clean: list[dict[str, Any]] = []
        seen: set[str] = set()
        for i, page in enumerate(pages):
            f = f"pages[{i}]"
            if not isinstance(page, dict) or set(page) - {"path", "body", "expected_version", "delete"}:
                raise invalid_field(f, "칸은 path · body · expected_version · delete")
            path = check_path(page.get("path"), f"{f}.path")
            if path in seen:
                raise invalid_field(f"{f}.path", f"묶음 안에서 겹친다: {path}")
            seen.add(path)
            delete = page.get("delete") is True
            body = page.get("body")
            if delete:
                if body is not None:
                    raise invalid_field(f"{f}.body", "delete 와 body 를 같이 줄 수 없다")
            elif not isinstance(body, str) or not body.strip():
                raise invalid_field(f"{f}.body", "본문이 비었다")
            elif len(body.encode("utf-8")) > MAX_BODY:
                raise invalid_field(f"{f}.body", f"{MAX_BODY} 바이트까지")
            else:
                scan_secrets(body, f"{f}.body")
            ev = page.get("expected_version", 0)
            if not isinstance(ev, int) or isinstance(ev, bool) or ev < 0:
                raise invalid_field(f"{f}.expected_version", "0 이상 정수 (새 페이지는 0)")
            clean.append({"path": path, "body": body, "expected_version": ev, "delete": delete})
        summary = summary.strip()
        scan_secrets(summary, "summary")
        now = _iso(ctx.now)

        def do(conn: sqlite3.Connection) -> dict[str, Any]:
            conflicts = []
            current: dict[str, int] = {}
            for page in clean:
                row = conn.execute("SELECT version FROM wiki_page WHERE project_id = ? AND path = ?",
                                   (pid, page["path"])).fetchone()
                cur = row["version"] if row else 0
                current[page["path"]] = cur
                if page["expected_version"] != cur or (page["delete"] and cur == 0):
                    conflicts.append({"path": page["path"], "expected_version": page["expected_version"],
                                      "current_version": cur})
            if conflicts:
                # 하나라도 어긋나면 묶음 전체를 거절 — 트랜잭션이 되돌린다 (부분 반영 0, 요구 R8.2).
                raise HubError(409, "version_conflict",
                               f"묶음 안 {len(conflicts)} 페이지의 version 이 다르다 — 묶음 전체를 거절했다",
                               {"conflicts": conflicts})
            seq = conn.execute("SELECT COALESCE(MAX(seq), 0) + 1 AS n FROM wiki_ingest WHERE project_id = ?",
                               (pid,)).fetchone()["n"]
            ing_id = f"ING-{seq:05d}"
            written = []
            for page in clean:
                cur = current[page["path"]]
                if page["delete"]:
                    conn.execute("DELETE FROM wiki_page WHERE project_id = ? AND path = ?", (pid, page["path"]))
                    written.append({"path": page["path"], "version": cur, "deleted": True})
                    continue
                conn.execute(
                    "INSERT INTO wiki_page (project_id, path, body_md, version, updated_by, updated_at, last_ingest) "
                    "VALUES (?, ?, ?, 1, ?, ?, ?) ON CONFLICT(project_id, path) DO UPDATE SET "
                    "body_md = excluded.body_md, version = wiki_page.version + 1, updated_by = excluded.updated_by, "
                    "updated_at = excluded.updated_at, last_ingest = excluded.last_ingest",
                    (pid, page["path"], page["body"], p.callsign, now, ing_id))
                written.append({"path": page["path"], "version": cur + 1})
            log_line = f"## [{ctx.now.strftime('%Y-%m-%d')}] ingest | {summary}"
            conn.execute(
                "INSERT INTO wiki_ingest (project_id, id, seq, callsign, at, log_line, pages_json) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (pid, ing_id, seq, p.callsign, now, log_line, json.dumps(written, ensure_ascii=False)))
            self.store._event(conn, ctx, pid, "wiki_ingest", ing_id, "ingest", None, {"pages": written})
            return {"ingest_id": ing_id, "log_line": log_line, "pages": written}

        return self.store.idempotent(ctx, request_id, do)

    # --- 읽기 -------------------------------------------------------------------

    def _pages(self, conn: sqlite3.Connection, pid: str) -> list[sqlite3.Row]:
        return list(conn.execute(
            "SELECT path, body_md, version, updated_by, updated_at, last_ingest, source_repo_key, source_sha "
            "FROM wiki_page WHERE project_id = ? ORDER BY path", (pid,)))

    def _ingests(self, conn: sqlite3.Connection, pid: str) -> list[dict[str, Any]]:
        return [dict(r) for r in conn.execute(
            "SELECT id, callsign, at, log_line, pages_json FROM wiki_ingest WHERE project_id = ? ORDER BY seq", (pid,))]

    def get(self, ctx: Ctx, path: str) -> dict[str, Any]:
        pid = self._pid(ctx)
        with self.store.read() as conn:
            if path == "index.md":
                return {"path": path, "generated": True, "body": render_index([r["path"] for r in self._pages(conn, pid)])}
            if path == "log.md":
                return {"path": path, "generated": True, "body": render_log(self._ingests(conn, pid))}
            check_path(path)
            row = conn.execute(
                "SELECT path, body_md, version, updated_by, updated_at, last_ingest, source_repo_key, source_sha "
                "FROM wiki_page WHERE project_id = ? AND path = ?", (pid, path)).fetchone()
        if row is None:
            raise HubError(404, "not_found", f"위키 페이지가 없다: {path}", {"path": path})
        return {"path": row["path"], "body": row["body_md"], "version": row["version"], "updated_by": row["updated_by"],
                "updated_at": row["updated_at"], "last_ingest": row["last_ingest"],
                "source": {"repo_key": row["source_repo_key"], "sha": row["source_sha"]}}

    def list(self, ctx: Ctx, prefix: str = "") -> dict[str, Any]:
        pid = self._pid(ctx)
        with self.store.read() as conn:
            rows = [r for r in self._pages(conn, pid) if r["path"].startswith(prefix or "")]
        return {"pages": [{"path": r["path"], "title": page_title(r["path"], r["body_md"]), "version": r["version"],
                           "updated_by": r["updated_by"], "updated_at": r["updated_at"]} for r in rows],
                "generated": list(GENERATED)}

    def search(self, ctx: Ctx, query: str, limit: int = 20) -> dict[str, Any]:
        pid = self._pid(ctx)
        if not isinstance(query, str) or not query.strip():
            raise invalid_field("query", "비었다")
        words = [w.lower() for w in query.split()]
        hits = []
        with self.store.read() as conn:
            for r in self._pages(conn, pid):
                title = page_title(r["path"], r["body_md"])
                hay = f"{r['path']}\n{title}\n{r['body_md']}".lower()
                if not all(w in hay for w in words):
                    continue
                score = sum(3 * (w in r["path"].lower() or w in title.lower()) + hay.count(w) for w in words)
                body = r["body_md"]
                at = body.lower().find(words[0])
                snippet = body[max(0, at - 60): at + 120].replace("\n", " ") if at >= 0 else ""
                hits.append({"path": r["path"], "title": title, "score": score, "snippet": snippet})
        hits.sort(key=lambda h: (-h["score"], h["path"]))
        return {"query": query, "hits": hits[: max(1, min(int(limit), 100))], "total": len(hits)}

    # --- lint -------------------------------------------------------------------

    def lint(self, ctx: Ctx) -> dict[str, Any]:
        pid = self._pid(ctx)
        with self.store.read() as conn:
            pages = [(r["path"], r["body_md"]) for r in self._pages(conn, pid)]
            ingests = self._ingests(conn, pid)
        if not pages:
            # 잴 것이 없음은 통과가 아니다 — ok 를 비워 둔다.
            return {"ok": None, "status": "empty", "pages": 0}
        with tempfile.TemporaryDirectory(prefix="hubwiki-") as d:
            root = Path(d) / "ai-workflow" / "wiki"
            root.mkdir(parents=True)
            for path, body in pages:
                f = root / path
                f.parent.mkdir(parents=True, exist_ok=True)
                f.write_text(body, encoding="utf-8")
            index = render_index([path for path, _ in pages])
            (root / "index.md").write_text(index, encoding="utf-8")
            (root / "log.md").write_text(render_log(ingests), encoding="utf-8")
            location = check_canonical_location(root)
            index_errors, entries = validate_index(index.splitlines(), root)
            broken, repo_refs = classify_wikilinks(root)
        ok = not location and not index_errors and not broken
        return {
            "ok": ok,
            "status": "ok" if ok else "violations",
            "pages": len(pages),
            "location": {"errors": location},
            "index": {"errors": index_errors, "entries": entries},
            "broken_links": [{"page": a, "target": b} for a, b in broken],
            # 원격 읽기(R8.4, WBS-36.2) 전 — 재지 못한 것은 통과가 아니라 미측정이다.
            "repo_references": {"status": "unmeasured", "count": len(repo_refs),
                                "reason": "저장소 원격 읽기 미설정 (R8.4)"},
            "freshness": {"status": "unmeasured", "targets": 0, "reason": "소스 시각 없음 — 원격 읽기 미설정 (R8.4)"},
        }
