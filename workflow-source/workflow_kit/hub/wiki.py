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

import hashlib
import json
import re
import sqlite3
import tempfile
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from workflow_kit.common.schemas.memory_index import MemoryEntry
from workflow_kit.common.state.bidir_link import audit_bidirectional_links
from workflow_kit.common.state.memory_index import entries_dir
from workflow_kit.common.wiki_rules import (
    check_canonical_location,
    classify_wikilinks,
    validate_index,
)
from workflow_kit.hub import wiki_remote
from workflow_kit.hub.errors import HubError, forbidden, invalid_field
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
_SHA = re.compile(r"^[0-9a-f]{7,40}$")


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

    def _read_pid(self, ctx: Ctx) -> str:
        """읽기 전용 입구 (get · list · search) — 화면의 viewer 도 받는다 (hub_spec §4.7)."""
        pid = self.store._need_reader(ctx).project_id
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
            if not isinstance(page, dict) or set(page) - {"path", "body", "expected_version", "delete", "source"}:
                raise invalid_field(f, "칸은 path · body · expected_version · delete · source")
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
            source = page.get("source")
            if source is not None:
                if delete or not isinstance(source, dict) or set(source) != {"repo_key", "sha"} \
                        or not isinstance(source["repo_key"], str) or not isinstance(source["sha"], str) \
                        or not _SHA.match(source["sha"].lower()):
                    raise invalid_field(f"{f}.source", "{repo_key, sha(16진 7~40)} — 삭제에는 줄 수 없다")
                source = {"repo_key": source["repo_key"], "sha": source["sha"].lower()}
            clean.append({"path": path, "body": body, "expected_version": ev, "delete": delete, "source": source})
        summary = summary.strip()
        scan_secrets(summary, "summary")

        def do(conn: sqlite3.Connection) -> dict[str, Any]:
            keys = {r["key"] for r in conn.execute("SELECT key FROM project_alias WHERE project_id = ?", (pid,))}
            for i, page in enumerate(clean):
                if page["source"] and page["source"]["repo_key"] not in keys:
                    raise invalid_field(f"pages[{i}].source.repo_key", f"이 프로젝트의 저장소 키가 아니다 (등록된 키: {sorted(keys)})")
            return self.write_pages(conn, ctx, pid, str(p.callsign), clean, summary)

        return self.store.idempotent(ctx, request_id, do)

    def write_pages(self, conn: sqlite3.Connection, ctx: Ctx, pid: str, callsign: str, clean: list[dict[str, Any]],
                    summary: str) -> dict[str, Any]:
        """검증을 마친 페이지 묶음을 열린 쓰기 트랜잭션 안에서 쓴다 — ingest 와 DCR 승인(ADR)이 같은 길로 쓴다.

        ``clean`` 항목: ``{path, body, expected_version, delete, source}``. version 이 하나라도 어긋나면 409 로 전부 거절한다."""
        now = _iso(ctx.now)
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
                conn.execute("INSERT INTO wiki_page_revision(project_id,path,revision,body_md,status,updated_by,updated_at) VALUES(?,?,?,'','tombstone',?,?)",
                             (pid, page["path"], cur + 1, callsign, now))
                conn.execute("DELETE FROM wiki_page WHERE project_id = ? AND path = ?", (pid, page["path"]))
                written.append({"path": page["path"], "version": cur + 1, "deleted": True})
                continue
            # 출처는 이번 쓰기가 말하는 것 — 주지 않으면 지운다 (옛 sha 가 새 본문의 출처인 척하지 않게).
            src = page["source"] or {"repo_key": "", "sha": ""}
            conn.execute(
                "INSERT INTO wiki_page (project_id, path, body_md, version, updated_by, updated_at, last_ingest, "
                "source_repo_key, source_sha) VALUES (?, ?, ?, 1, ?, ?, ?, ?, ?) ON CONFLICT(project_id, path) DO UPDATE SET "
                "body_md = excluded.body_md, version = wiki_page.version + 1, updated_by = excluded.updated_by, "
                "updated_at = excluded.updated_at, last_ingest = excluded.last_ingest, "
                "source_repo_key = excluded.source_repo_key, source_sha = excluded.source_sha",
                (pid, page["path"], page["body"], callsign, now, ing_id, src["repo_key"], src["sha"]))
            revision = cur + 1
            conn.execute("INSERT INTO wiki_page_revision(project_id,path,revision,body_md,status,updated_by,updated_at) VALUES(?,?,?,?,'active',?,?)",
                         (pid, page["path"], revision, page["body"], callsign, now))
            written.append({"path": page["path"], "version": revision})
        log_line = f"## [{ctx.now.strftime('%Y-%m-%d')}] ingest | {summary}"
        conn.execute(
            "INSERT INTO wiki_ingest (project_id, id, seq, callsign, at, log_line, pages_json) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (pid, ing_id, seq, callsign, now, log_line, json.dumps(written, ensure_ascii=False)))
        self.store._event(conn, ctx, pid, "wiki_ingest", ing_id, "ingest", None, {"pages": written})
        return {"ingest_id": ing_id, "log_line": log_line, "pages": written}

    # --- 읽기 -------------------------------------------------------------------

    def _pages(self, conn: sqlite3.Connection, pid: str) -> list[sqlite3.Row]:
        return list(conn.execute(
            "SELECT path, body_md, version, updated_by, updated_at, last_ingest, source_repo_key, source_sha "
            "FROM wiki_page WHERE project_id = ? ORDER BY path", (pid,)))

    def _ingests(self, conn: sqlite3.Connection, pid: str) -> list[dict[str, Any]]:
        return [dict(r) for r in conn.execute(
            "SELECT id, callsign, at, log_line, pages_json FROM wiki_ingest WHERE project_id = ? ORDER BY seq", (pid,))]

    def get(self, ctx: Ctx, path: str) -> dict[str, Any]:
        pid = self._read_pid(ctx)
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

    def list_pages(self, ctx: Ctx, prefix: str = "") -> dict[str, Any]:
        pid = self._read_pid(ctx)
        with self.store.read() as conn:
            rows = [r for r in self._pages(conn, pid) if r["path"].startswith(prefix or "")]
        return {"pages": [{"path": r["path"], "title": page_title(r["path"], r["body_md"]), "version": r["version"],
                           "updated_by": r["updated_by"], "updated_at": r["updated_at"]} for r in rows],
                "generated": list(GENERATED)}

    def search(self, ctx: Ctx, query: str, limit: int = 20) -> dict[str, Any]:
        pid = self._read_pid(ctx)
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

    # --- 들여오기 · 내보내기 (R8.6 — 소유자 결정 2026-11-21: 운반 = 1.x 위키 디렉터리 그대로) -----

    def import_dir(self, ctx: Ctx, files: list[Any], summary: str, overwrite: bool = False,
                   request_id: str | None = None) -> dict[str, Any]:
        """1.x ``ai-workflow/wiki/`` 배치를 무손실로 들인다 — 경로는 위키 뿌리 상대.

        페이지(``.md``)는 바이트 그대로 ingest 묶음 하나로 쓴다. ``index.md`` · ``log.md`` 는 허브가 생성하므로
        페이지로 쓰지 않고 원문을 보관 기록(``memory_note`` ``archive_1x``)에 남긴다 — 1.x log 는 이력이다.
        ``.md`` 가 아닌 파일(``.gitkeep`` 등)은 위키 페이지가 아니라 건너뛰고 목록으로 보인다.
        ``overwrite`` 가 아니면 이미 있는 페이지는 409 (묶음 전체 거절).
        """
        p = self.store._need_callsign(ctx)
        pid = p.project_id
        assert pid is not None
        if not isinstance(files, list) or not files:
            raise invalid_field("files", "[{path, content}] 하나 이상")
        pages, archived, skipped = [], [], []
        for i, f in enumerate(files):
            if not isinstance(f, dict) or set(f) != {"path", "content"} or not isinstance(f["content"], str):
                raise invalid_field(f"files[{i}]", "{path, content(문자열)}")
            path = f["path"]
            if not isinstance(path, str) or path.startswith("/") or ".." in path.split("/"):
                raise invalid_field(f"files[{i}].path", "위키 뿌리 상대 경로")
            if path in GENERATED:
                archived.append((path, f["content"]))
            elif not path.endswith(".md"):
                skipped.append(path)
            else:
                pages.append({"path": check_path(path, f"files[{i}].path"), "body": f["content"]})
        if not pages and not archived:
            raise invalid_field("files", "들일 위키 페이지가 없다")
        if overwrite:
            with self.store.read() as conn:
                cur = {r["path"]: r["version"] for r in conn.execute(
                    "SELECT path, version FROM wiki_page WHERE project_id = ?", (pid,))}
            for page in pages:
                page["expected_version"] = cur.get(page["path"], 0)
        result: dict[str, Any] = {"pages": [], "archived_1x": [a for a, _ in archived], "skipped_non_page": skipped}
        if pages:
            result.update(self.ingest(ctx, pages, summary, request_id))
        if archived:
            with self.store.write() as conn:
                for path, content in archived:
                    scan_secrets(content, f"files.{path}")
                    conn.execute(
                        "INSERT INTO memory_note (project_id, callsign, kind, title, body_md, meta_json, created_at) "
                        "VALUES (?, ?, 'archive_1x', ?, ?, ?, ?)",
                        (pid, p.callsign, f"wiki/{path} (1.x 원문)", content,
                         json.dumps({"source": "hub_wiki_import_dir", "path": path}, ensure_ascii=False), _iso(ctx.now)))
        return result

    def export(self, ctx: Ctx, fmt: str, out_dir: str | None = None, cursor: int = 0) -> dict[str, Any]:
        """쓰기 지시(hub_spec §5.1)로 돌려준다 — 허브는 저장소에 쓰지 않는다 (R15.1 · D6).

        ``dir``: 1.x 위키 배치 (페이지 바이트 그대로 + 생성 index · log + 내보내기 표식, R15.2).
        ``okf``: 1.x ``export_wiki_to_okf`` 그대로 (출판 변환 — 5종 디렉터리만, 빠진 페이지를 목록으로).
        응답이 크면 ``cursor`` 로 나눈다 (지시 순서는 경로 순으로 고정).
        """
        pid = self._pid(ctx)
        if fmt not in ("dir", "okf"):
            raise invalid_field("format", "dir · okf")
        base = out_dir if out_dir is not None else ("ai-workflow/wiki" if fmt == "dir" else "okf-export")
        if not isinstance(base, str) or base.startswith(("/", "~")) or ".." in base.split("/"):
            raise invalid_field("out_dir", "저장소 뿌리 상대 경로")
        base = base.rstrip("/")
        with self.store.read() as conn:
            rows = self._pages(conn, pid)
            pages = [(r["path"], r["body_md"]) for r in rows]
            ingests = self._ingests(conn, pid)
        files: list[tuple[str, str]] = []
        report: dict[str, Any] = {"format": fmt, "pages": len(pages)}
        last_ing = ingests[-1]["id"] if ingests else None
        if fmt == "dir":
            files = list(pages)
            if pages:
                files += [("index.md", render_index([path for path, _ in pages])), ("log.md", render_log(ingests))]
            files.append((".hub-export.json", json.dumps(
                {"canonical": "hub", "project_id": pid, "exported_at": _iso(ctx.now), "last_ingest": last_ing,
                 "note": "허브 위키의 사본이다 — 정본은 허브. 여기를 고쳐도 허브에 반영되지 않는다 (R15.2)."},
                ensure_ascii=False, indent=2) + "\n"))
        else:
            from workflow_kit.okf_export import _is_wiki_page, export_wiki_to_okf
            with tempfile.TemporaryDirectory(prefix="hubwiki-okf-") as d:
                root = Path(d) / "wiki"
                for path, body in pages:
                    f = root / path
                    f.parent.mkdir(parents=True, exist_ok=True)
                    f.write_text(body, encoding="utf-8")
                out = Path(d) / "bundle"
                rep = export_wiki_to_okf(root, out, resolve=False, emit_manifest=True)
                files = sorted((q.relative_to(out).as_posix(), q.read_text(encoding="utf-8"))
                               for q in out.rglob("*") if q.is_file())
                # 묶음에 없는 페이지는 이유와 상관없이 전부 — 디렉터리 밖(5종 외)이든 변환 오류든 (조용히 사라지지 않게).
                excluded = [path for path, _ in pages if not (out / path).is_file()]
                not_type_dir = sum(1 for path, _ in pages if not _is_wiki_page((root / path).resolve(), root.resolve()))
            # 출판 변환은 손실이 있다 — 빠진 페이지를 숫자와 목록으로 보인다 (조용히 사라지지 않게).
            report.update({"pages_exported": rep.pages_exported, "excluded": excluded, "excluded_not_type_dir": not_type_dir,
                           "excluded_by_error": len(excluded) - not_type_dir, "errors": list(rep.errors),
                           "lossy": True, "note": "OKF 는 출판 형식이다 — 5종 디렉터리만 · 본문 · frontmatter 변환. 운반은 format=dir"})
        files.sort(key=lambda x: x[0])
        budget, i = 150_000, max(0, int(cursor))
        steps: list[dict[str, str]] = []
        while i < len(files):
            path, content = files[i]
            size = len(content.encode("utf-8"))
            if steps and sum(len(s_["content"].encode("utf-8")) for s_ in steps) + size > budget:
                break
            steps.append({"op": "write", "path": f"{base}/{path}", "content": content,
                          "sha256": hashlib.sha256(content.encode("utf-8")).hexdigest()})
            i += 1
        report.update({"steps": steps, "total_files": len(files), "next_cursor": i if i < len(files) else None})
        return report

    def import_okf(self, ctx: Ctx, files: list[Any], summary: str, request_id: str | None = None) -> dict[str, Any]:
        """남의 OKF 묶음을 들인다 — loose 한 방향 (1.x ``import_okf_bundle`` 그대로). 경로는 묶음 뿌리 상대.
        OKF 형태 그대로 페이지가 된다 (역변환 없음). 같은 경로가 있으면 409."""
        from workflow_kit.okf_import import import_okf_bundle
        if not isinstance(files, list) or not files:
            raise invalid_field("files", "[{path, content}] 하나 이상")
        with tempfile.TemporaryDirectory(prefix="hubwiki-okfin-") as d:
            bundle, staging = Path(d) / "bundle", Path(d) / "staging"
            for i, f in enumerate(files):
                if not isinstance(f, dict) or set(f) != {"path", "content"} or not isinstance(f["content"], str):
                    raise invalid_field(f"files[{i}]", "{path, content(문자열)}")
                rel = f["path"]
                if not isinstance(rel, str) or rel.startswith("/") or ".." in rel.split("/") or not rel:
                    raise invalid_field(f"files[{i}].path", "묶음 뿌리 상대 경로")
                (bundle / rel).parent.mkdir(parents=True, exist_ok=True)
                (bundle / rel).write_text(f["content"], encoding="utf-8")
            rep = import_okf_bundle(bundle, staging=staging, mode="loose")
            staged = sorted((q.relative_to(staging).as_posix(), q.read_text(encoding="utf-8")) for q in staging.rglob("*.md"))
        if not staged:
            raise HubError(400, "invalid_field", "들일 페이지가 없다 (loose 들여오기가 하나도 받지 않았다)",
                           {"field": "files", "errors": list(rep.errors)})
        result = self.ingest(ctx, [{"path": path, "body": body} for path, body in staged], summary, request_id)
        result.update({"okf_version": rep.okf_version, "pages_total": rep.pages_total, "pages_staged": rep.pages_staged,
                       "warnings": sum(1 for x in rep.issues if x.severity == "warn"),
                       "errors": sum(1 for x in rep.issues if x.severity == "error"), "mode": "loose"})
        return result

    # --- lint -------------------------------------------------------------------

    # --- memory_index (E5) --------------------------------------------------------

    def memory_put(self, ctx: Ctx, entry: Any, expected_version: int | None) -> dict[str, Any]:
        p = self.store._need_callsign(ctx)
        pid = p.project_id
        assert pid is not None
        if not isinstance(entry, dict):
            raise invalid_field("entry", "객체여야 한다")
        scan_secrets(entry, "entry")
        try:
            model = MemoryEntry.model_validate(entry)
        except ValidationError as exc:
            first = exc.errors()[0]
            loc = ".".join(str(x) for x in first.get("loc", ())) or "entry"
            raise invalid_field(f"entry.{loc}", f"1.x memory entry 스키마 — {first.get('msg', '')}") from None
        body = model.model_dump(mode="json")
        with self.store.write() as conn:
            row = conn.execute("SELECT version FROM memory_entry WHERE project_id = ? AND id = ?", (pid, model.id)).fetchone()
            cur = row["version"] if row else 0
            if (expected_version or 0) != cur:
                raise HubError(409, "version_conflict", f"version 이 다르다 — 지금 {cur} (새 entry 는 0)",
                               {"current_version": cur, "id": model.id})
            conn.execute(
                "INSERT INTO memory_entry (project_id, id, body_json, version, updated_by, updated_at) VALUES (?, ?, ?, 1, ?, ?) "
                "ON CONFLICT(project_id, id) DO UPDATE SET body_json = excluded.body_json, version = memory_entry.version + 1, "
                "updated_by = excluded.updated_by, updated_at = excluded.updated_at",
                (pid, model.id, json.dumps(body, ensure_ascii=False), p.callsign, _iso(ctx.now)))
            self.store._event(conn, ctx, pid, "memory_entry", model.id, "put", {"version": cur}, {"version": cur + 1})
        return {"id": model.id, "version": cur + 1}

    def memory_get(self, ctx: Ctx, entry_id: str) -> dict[str, Any]:
        pid = self._pid(ctx)
        with self.store.read() as conn:
            row = conn.execute("SELECT body_json, version, updated_by, updated_at FROM memory_entry "
                               "WHERE project_id = ? AND id = ?", (pid, entry_id)).fetchone()
        if row is None:
            raise HubError(404, "not_found", f"memory entry 가 없다: {entry_id}", {"id": entry_id})
        return {"id": entry_id, "entry": json.loads(row["body_json"]), "version": row["version"],
                "updated_by": row["updated_by"], "updated_at": row["updated_at"]}

    def memory_list(self, ctx: Ctx) -> dict[str, Any]:
        pid = self._pid(ctx)
        with self.store.read() as conn:
            rows = list(conn.execute("SELECT id, body_json, version FROM memory_entry WHERE project_id = ? ORDER BY id", (pid,)))
        return {"entries": [{"id": r["id"], "version": r["version"],
                             "primary_abstraction": json.loads(r["body_json"]).get("primary_abstraction", "")} for r in rows]}

    # --- 원격 읽기 설정 (R8.4 · E3) ---------------------------------------------------

    def remote_set(self, ctx: Ctx, fetch_url: str) -> dict[str, Any]:
        p = self.store._need_callsign(ctx)
        pid = p.project_id
        assert pid is not None
        if p.role != "owner":
            raise forbidden("위키 원격 읽기는 소유자만 켜고 끈다 — 허브가 외부에 접속하는 유일한 설정이다 (R3.7 · R8.4)")
        if fetch_url and not self.store.wiki_remote_allowed:
            raise HubError(403, "wiki_remote_disabled", "바깥에 노출된 허브라 위키 원격 읽기가 꺼져 있다 — 운영자가 serve --allow-wiki-remote 로 켠다")
        if fetch_url:
            try:
                wiki_remote.check_fetch_url(fetch_url)
            except ValueError as exc:
                raise invalid_field("fetch_url", str(exc)) from None
        with self.store.write() as conn:
            row = conn.execute("SELECT settings_json FROM project WHERE id = ?", (pid,)).fetchone()
            settings = json.loads(row["settings_json"] or "{}")
            before = settings.get("wiki_remote")
            if fetch_url:
                settings["wiki_remote"] = {"fetch_url": fetch_url}
            else:
                settings.pop("wiki_remote", None)
            conn.execute("UPDATE project SET settings_json = ? WHERE id = ?", (json.dumps(settings, ensure_ascii=False), pid))
            self.store._event(conn, ctx, pid, "project", pid, "wiki_remote", before, settings.get("wiki_remote"))
        return {"wiki_remote": settings.get("wiki_remote"), "enabled": bool(fetch_url)}

    # --- lint -------------------------------------------------------------------

    def lint(self, ctx: Ctx) -> dict[str, Any]:
        pid = self._pid(ctx)
        with self.store.read() as conn:
            rows = self._pages(conn, pid)
            pages = [(r["path"], r["body_md"]) for r in rows]
            shas = {r["path"]: r["source_sha"] for r in rows}
            ingests = self._ingests(conn, pid)
            entries = [(r["id"], r["body_json"]) for r in conn.execute(
                "SELECT id, body_json FROM memory_entry WHERE project_id = ? ORDER BY id", (pid,))]
            settings = json.loads(conn.execute("SELECT settings_json FROM project WHERE id = ?", (pid,)).fetchone()["settings_json"] or "{}")
        if not pages:
            # 잴 것이 없음은 통과가 아니다 — ok 를 비워 둔다.
            return {"ok": None, "status": "empty", "pages": 0, "memory_entries": len(entries)}
        with tempfile.TemporaryDirectory(prefix="hubwiki-") as d:
            workspace = Path(d)
            root = workspace / "ai-workflow" / "wiki"
            root.mkdir(parents=True)
            for path, body in pages:
                f = root / path
                f.parent.mkdir(parents=True, exist_ok=True)
                f.write_text(body, encoding="utf-8")
            index = render_index([path for path, _ in pages])
            (root / "index.md").write_text(index, encoding="utf-8")
            (root / "log.md").write_text(render_log(ingests), encoding="utf-8")
            # 1.x audit 가 읽는 자리를 1.x 정본 함수로 — 펼침과 읽기가 같은 경로 규약을 쓴다.
            ed = entries_dir(workspace_root=workspace)
            ed.mkdir(parents=True)
            for eid, body_json in entries:
                (ed / f"{eid}.json").write_text(body_json, encoding="utf-8")
            location = check_canonical_location(root)
            index_errors, n_entries = validate_index(index.splitlines(), root)
            broken, repo_refs = classify_wikilinks(root)
            bidir = audit_bidirectional_links(workspace)
        remote = wiki_remote.measure((settings.get("wiki_remote") or {}).get("fetch_url") if self.store.wiki_remote_allowed else None,
                                     [{"path": path, "body": body, "source_sha": shas.get(path, "")} for path, body in pages],
                                     repo_refs)
        ok = not location and not index_errors and not broken and bidir.is_symmetric
        return {
            "ok": ok,
            "status": "ok" if ok else "violations",
            "pages": len(pages),
            "location": {"errors": location},
            "index": {"errors": index_errors, "entries": n_entries},
            "broken_links": [{"page": a, "target": b} for a, b in broken],
            "bidir": {"memory_entries": bidir.total_memory_entries, "symmetric": bidir.symmetric_links,
                      "asymmetric": [{"entry": x.memory_entry_id, "page": x.wiki_page, "direction": x.direction}
                                     for x in bidir.asymmetric]},
            # 원격 읽기(R8.4)를 못 하면 미측정 — 통과가 아니다. ok 판정에 넣지 않고 따로 보인다.
            **remote,
        }
