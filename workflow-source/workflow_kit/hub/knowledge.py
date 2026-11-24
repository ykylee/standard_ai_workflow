"""Project-scoped knowledge snapshots and decision change records."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from workflow_kit.hub.errors import HubError, forbidden, invalid_field, not_found, version_conflict
from workflow_kit.hub.store import Ctx, Store, _iso, _json, scan_secrets

_ID = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._-]{0,79}$")
_SHA = re.compile(r"^[0-9a-f]{7,40}$")
_PATH = re.compile(r"^(?:[A-Za-z0-9_.-]+/)*[A-Za-z0-9_.-]+\.md$")
_ADR_PATH = re.compile(r"(?:^|/)adr-\d{3,}-.+\.md$", re.I)
_ADR_STATUS = re.compile(r"^status:\s*([a-z_-]+)\s*$", re.M | re.I)


class Knowledge:
    def __init__(self, store: Store) -> None:
        self.store = store

    def _identity(self, ctx: Ctx, owner: bool = False) -> tuple[Any, str]:
        p = self.store._need_callsign(ctx)
        assert p.project_id and p.callsign
        if owner and (
            p.kind != "callsign"
            or p.callsign_kind != "human"
            or not p.human_approved
            or p.role != "owner"
        ):
            raise forbidden("DCR 결정에는 승인된 human project owner가 필요하다")
        return p, p.project_id

    def _read_identity(self, ctx: Ctx) -> tuple[Any, str]:
        p = self.store._need_reader(ctx)
        assert p.project_id
        return p, p.project_id

    def source_register(
        self, ctx: Ctx, source_id: str, repo_key: str, allowlist: list[Any]
    ) -> dict[str, Any]:
        p, pid = self._identity(ctx, owner=True)
        if not _ID.fullmatch(source_id or ""):
            raise invalid_field("source_id", "영문·숫자·._- 1~80자")
        if not isinstance(allowlist, list) or not allowlist or len(allowlist) > 500:
            raise invalid_field("allowlist", "허용할 markdown 경로가 하나 이상 필요하다")
        paths = []
        for raw in allowlist:
            if not isinstance(raw, str) or not _PATH.fullmatch(raw) or ".." in raw.split("/"):
                raise invalid_field("allowlist", f"안전한 상대 .md 경로가 아니다: {raw!r}")
            if raw not in paths:
                paths.append(raw)
        with self.store.write() as conn:
            aliases = {
                r[0]
                for r in conn.execute("SELECT key FROM project_alias WHERE project_id=?", (pid,))
            }
            if repo_key not in aliases:
                raise invalid_field("repo_key", "프로젝트에 등록된 저장소 키가 아니다")
            existing = conn.execute(
                "SELECT version FROM knowledge_source WHERE project_id=? AND id=?", (pid, source_id)
            ).fetchone()
            if existing:
                raise version_conflict(existing[0], {"source_id": source_id})
            now = _iso(ctx.now)
            conn.execute(
                "INSERT INTO knowledge_source(project_id,id,kind,authority,repo_key,allowlist_json,created_by,created_at) VALUES(?,?,'git','git',?,?,?,?)",
                (pid, source_id, repo_key, _json(paths), p.callsign, now),
            )
            self.store._event(
                conn,
                ctx,
                pid,
                "knowledge_source",
                source_id,
                "register",
                None,
                {"repo_key": repo_key, "allowlist": paths},
            )
        return {
            "source_id": source_id,
            "repo_key": repo_key,
            "allowlist": paths,
            "authority": "git",
            "version": 1,
        }

    def sync(
        self, ctx: Ctx, source_id: str, commit_sha: str, documents: list[Any]
    ) -> dict[str, Any]:
        p, pid = self._identity(ctx)
        if not isinstance(commit_sha, str) or not _SHA.fullmatch(commit_sha.lower()):
            raise invalid_field("commit_sha", "40자리 이하 16진 커밋 SHA가 필요하다")
        if not isinstance(documents, list) or not documents or len(documents) > 500:
            raise invalid_field("documents", "문서가 1~500개 필요하다")
        with self.store.read() as conn:
            source = conn.execute(
                "SELECT * FROM knowledge_source WHERE project_id=? AND id=? AND enabled=1",
                (pid, source_id),
            ).fetchone()
        if not source:
            raise not_found(f"knowledge source가 없다: {source_id}")
        allowed = set(json.loads(source["allowlist_json"]))
        clean = []
        for i, item in enumerate(documents):
            if not isinstance(item, dict) or set(item) - {"path", "title", "body"}:
                raise invalid_field(f"documents[{i}]", "path, title, body 필드만 허용한다")
            path, title, body = item.get("path"), item.get("title"), item.get("body")
            if path not in allowed:
                raise forbidden(f"source allowlist에 없는 경로: {path}")
            if (
                not isinstance(title, str)
                or not title.strip()
                or not isinstance(body, str)
                or not body.strip()
                or len(body.encode()) > 192 * 1024
            ):
                raise invalid_field(
                    f"documents[{i}]", "title/body가 비었거나 본문이 192KB를 넘는다"
                )
            scan_secrets(body, f"documents[{i}].body")
            clean.append((path, title.strip(), body))
        now = _iso(ctx.now)
        added = []
        with self.store.write() as conn:
            for path, title, body in clean:
                digest = hashlib.sha256(body.encode()).hexdigest()
                last = conn.execute(
                    "SELECT revision,content_sha256,commit_sha FROM knowledge_revision WHERE project_id=? AND source_id=? AND path=? ORDER BY revision DESC LIMIT 1",
                    (pid, source_id, path),
                ).fetchone()
                pending = conn.execute(
                    "SELECT id,target_refs_json FROM decision_change WHERE project_id=? AND status='approved_pending_export' AND adr_path=? AND adr_sha256=?",
                    (pid, path, digest),
                ).fetchall()
                for dcr in pending:
                    conn.execute(
                        "UPDATE decision_change SET status='accepted',version=version+1,updated_at=? WHERE project_id=? AND id=?",
                        (now, pid, dcr["id"]),
                    )
                    for target in json.loads(dcr["target_refs_json"]):
                        if (
                            isinstance(target, str)
                            and target.startswith("git:")
                            and ":" in target[4:]
                        ):
                            old_path = target[4:].split(":", 1)[1].split("@", 1)[0]
                            if re.search(r"(?:^|/)adr-[^/]+\.md$", old_path):
                                conn.execute(
                                    "UPDATE knowledge_revision SET status='superseded' WHERE project_id=? AND path=? AND status='active'",
                                    (pid, old_path),
                                )
                    conn.execute(
                        "INSERT INTO decision_event(project_id,dcr_id,at,actor,op,after_json) VALUES(?,?,?,?,?,?)",
                        (
                            pid,
                            dcr["id"],
                            now,
                            p.callsign,
                            "publish_confirmed",
                            _json(
                                {
                                    "path": path,
                                    "content_sha256": digest,
                                    "commit_sha": commit_sha.lower(),
                                }
                            ),
                        ),
                    )
                if (
                    last
                    and last["content_sha256"] == digest
                    and last["commit_sha"] == commit_sha.lower()
                ):
                    added.append({"path": path, "revision": last["revision"], "unchanged": True})
                    continue
                if last and "/decisions/adr-" in f"/{path}" and not pending:
                    raise HubError(
                        409, "adr_requires_dcr", f"기존 ADR은 DCR 승인으로만 새 판을 만든다: {path}"
                    )
                if last:
                    conn.execute(
                        "UPDATE knowledge_revision SET status='superseded' WHERE project_id=? AND source_id=? AND path=? AND status='active'",
                        (pid, source_id, path),
                    )
                revision = (last["revision"] if last else 0) + 1
                conn.execute(
                    "INSERT INTO knowledge_revision(project_id,source_id,path,revision,commit_sha,content_sha256,title,body_md,created_by,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)",
                    (
                        pid,
                        source_id,
                        path,
                        revision,
                        commit_sha.lower(),
                        digest,
                        title,
                        body,
                        p.callsign,
                        now,
                    ),
                )
                added.append({"path": path, "revision": revision, "content_sha256": digest})
            self.store._event(
                conn,
                ctx,
                pid,
                "knowledge_source",
                source_id,
                "sync",
                None,
                {"commit_sha": commit_sha.lower(), "documents": added},
            )
        return {"source_id": source_id, "commit_sha": commit_sha.lower(), "documents": added}

    def search(self, ctx: Ctx, query: str, limit: int = 20) -> dict[str, Any]:
        _, pid = self._read_identity(ctx)
        if not isinstance(query, str) or not query.strip():
            raise invalid_field("query", "검색어가 비었다")
        words = query.lower().split()
        hits = []
        with self.store.read() as conn:
            rows = conn.execute(
                "SELECT r.*,s.repo_key FROM knowledge_revision r JOIN knowledge_source s ON s.project_id=r.project_id AND s.id=r.source_id WHERE r.project_id=? AND r.revision=(SELECT MAX(r2.revision) FROM knowledge_revision r2 WHERE r2.project_id=r.project_id AND r2.source_id=r.source_id AND r2.path=r.path) ORDER BY r.path",
                (pid,),
            ).fetchall()
            for r in rows:
                hay = f"{r['path']}\n{r['title']}\n{r['body_md']}".lower()
                if all(w in hay for w in words):
                    is_adr = bool(_ADR_PATH.search(r["path"])) or "adr_id:" in r["body_md"]
                    adr_status = _ADR_STATUS.search(r["body_md"]) if is_adr else None
                    status = (
                        "superseded"
                        if r["status"] == "superseded"
                        else (
                            (adr_status.group(1).lower() if adr_status else r["status"])
                            if is_adr
                            else r["status"]
                        )
                    )
                    hits.append(
                        {
                            "ref": f"git:{r['repo_key']}:{r['path']}@{r['commit_sha']}",
                            "canonical_ref": f"{r['repo_key']}:{r['path']}",
                            "kind": "adr" if is_adr else "design_doc",
                            "title": r["title"],
                            "path": r["path"],
                            "status": status,
                            "authority": "git",
                            "revision": r["revision"],
                            "source_sha": r["commit_sha"],
                            "content_sha256": r["content_sha256"],
                            "updated_at": r["created_at"],
                            "relations": [],
                            "excerpt": r["body_md"][:240],
                        }
                    )
            wiki = conn.execute(
                "SELECT path,body_md,version,updated_at FROM wiki_page WHERE project_id=? ORDER BY path",
                (pid,),
            ).fetchall()
            for r in wiki:
                hay = f"{r['path']}\n{r['body_md']}".lower()
                if all(w in hay for w in words):
                    hits.append(
                        {
                            "ref": f"hub-wiki:{r['path']}@{r['version']}",
                            "canonical_ref": f"hub-wiki:{r['path']}",
                            "kind": "wiki",
                            "title": r["path"],
                            "path": r["path"],
                            "status": "active",
                            "authority": "hub",
                            "revision": r["version"],
                            "source_sha": None,
                            "content_sha256": hashlib.sha256(r["body_md"].encode()).hexdigest(),
                            "updated_at": r["updated_at"],
                            "relations": [],
                            "excerpt": r["body_md"][:240],
                        }
                    )
            for r in conn.execute(
                "SELECT id,title,rationale,proposal_md,status,version,updated_at FROM decision_change WHERE project_id=? ORDER BY created_at",
                (pid,),
            ):
                hay = f"{r['id']}\n{r['title']}\n{r['rationale']}\n{r['proposal_md']}".lower()
                if all(w in hay for w in words):
                    content = f"{r['rationale']}\n{r['proposal_md']}"
                    hits.append(
                        {
                            "ref": f"hub-dcr:{r['id']}@{r['version']}",
                            "canonical_ref": f"hub-dcr:{r['id']}",
                            "kind": "dcr",
                            "title": r["title"],
                            "path": None,
                            "status": r["status"],
                            "authority": "hub",
                            "revision": r["version"],
                            "source_sha": None,
                            "content_sha256": hashlib.sha256(content.encode()).hexdigest(),
                            "updated_at": r["updated_at"],
                            "relations": [],
                            "excerpt": content[:240],
                        }
                    )
            for r in conn.execute(
                "SELECT id,body_json,version,updated_at FROM memory_entry WHERE project_id=? ORDER BY id",
                (pid,),
            ):
                hay = f"{r['id']}\n{r['body_json']}".lower()
                if all(w in hay for w in words):
                    hits.append(
                        {
                            "ref": f"hub-memory:{r['id']}@{r['version']}",
                            "canonical_ref": f"hub-memory:{r['id']}",
                            "kind": "memory",
                            "title": r["id"],
                            "path": None,
                            "status": "active",
                            "authority": "hub",
                            "revision": r["version"],
                            "source_sha": None,
                            "content_sha256": hashlib.sha256(r["body_json"].encode()).hexdigest(),
                            "updated_at": r["updated_at"],
                            "relations": [],
                            "excerpt": r["body_json"][:240],
                        }
                    )
        return {"query": query, "hits": hits[: max(1, min(limit, 100))], "total": len(hits)}

    def get(self, ctx: Ctx, ref: str) -> dict[str, Any]:
        _, pid = self._read_identity(ctx)
        if not isinstance(ref, str):
            raise invalid_field("ref", "문자열이어야 한다")
        with self.store.read() as conn:
            if ref.startswith("hub-dcr:"):
                key, sep, rev = ref[len("hub-dcr:") :].rpartition("@")
                if not sep or not rev.isdigit():
                    raise invalid_field("ref", "hub-dcr:id@version 형식")
                row = conn.execute(
                    "SELECT id,title,status,version,proposal_md FROM decision_change WHERE project_id=? AND id=?",
                    (pid, key),
                ).fetchone()
                if not row or row["version"] != int(rev):
                    raise not_found(f"knowledge ref가 없다: {ref}")
                return self.dcr_get(ctx, key)
            if ref.startswith("hub-memory:"):
                key, sep, rev = ref[len("hub-memory:") :].rpartition("@")
                if not sep or not rev.isdigit():
                    raise invalid_field("ref", "hub-memory:id@version 형식")
                row = conn.execute(
                    "SELECT body_json,version,updated_by,updated_at FROM memory_entry WHERE project_id=? AND id=? AND version=?",
                    (pid, key, int(rev)),
                ).fetchone()
                if not row:
                    raise not_found(f"knowledge ref가 없다: {ref}")
                return {
                    "ref": ref,
                    "kind": "memory",
                    "id": key,
                    "body": json.loads(row["body_json"]),
                    "authority": "hub",
                    "revision": row["version"],
                    "updated_by": row["updated_by"],
                    "updated_at": row["updated_at"],
                }
            if ref.startswith("hub-wiki:"):
                key, sep, rev = ref[len("hub-wiki:") :].rpartition("@")
                if not sep or not rev.isdigit():
                    raise invalid_field("ref", "hub-wiki:path@revision 형식")
                row = conn.execute(
                    "SELECT path,body_md,revision,status,updated_at FROM wiki_page_revision WHERE project_id=? AND path=? AND revision=?",
                    (pid, key, int(rev)),
                ).fetchone()
                if not row:
                    raise not_found(f"knowledge ref가 없다: {ref}")
                if row["status"] == "tombstone":
                    raise not_found(f"위키 revision은 삭제 표식이다: {ref}")
                return {
                    "ref": ref,
                    "kind": "wiki",
                    "path": row["path"],
                    "body": row["body_md"],
                    "revision": row["revision"],
                    "authority": "hub",
                    "updated_at": row["updated_at"],
                }
            m = re.fullmatch(r"git:([^:]+):(.+)@([0-9a-f]{7,40})", ref)
            if not m:
                raise invalid_field(
                    "ref", "git:repo_key:path@commit 또는 hub-wiki:path@revision 형식"
                )
            row = conn.execute(
                "SELECT r.*,s.repo_key FROM knowledge_revision r JOIN knowledge_source s ON s.project_id=r.project_id AND s.id=r.source_id WHERE r.project_id=? AND s.repo_key=? AND r.path=? AND r.commit_sha=? ORDER BY r.revision DESC LIMIT 1",
                (pid, m.group(1), m.group(2), m.group(3)),
            ).fetchone()
            if not row:
                raise not_found(f"knowledge ref가 없다: {ref}")
            return {
                "ref": ref,
                "kind": "design_doc",
                "path": row["path"],
                "title": row["title"],
                "body": row["body_md"],
                "authority": "git",
                "revision": row["revision"],
                "source_sha": row["commit_sha"],
                "content_sha256": row["content_sha256"],
                "status": row["status"],
            }

    def dcr_list(self, ctx: Ctx, status: str | None = None) -> dict[str, Any]:
        _, pid = self._read_identity(ctx)
        with self.store.read() as conn:
            if status:
                rows = conn.execute(
                    "SELECT id,title,status,version,author,reviewer,created_at,updated_at FROM decision_change WHERE project_id=? AND status=? ORDER BY created_at DESC",
                    (pid, status),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT id,title,status,version,author,reviewer,created_at,updated_at FROM decision_change WHERE project_id=? ORDER BY created_at DESC",
                    (pid,),
                ).fetchall()
        return {"dcrs": [dict(r) for r in rows]}

    def dcr_get(self, ctx: Ctx, dcr_id: str) -> dict[str, Any]:
        _, pid = self._read_identity(ctx)
        with self.store.read() as conn:
            row = conn.execute(
                "SELECT * FROM decision_change WHERE project_id=? AND id=?", (pid, dcr_id)
            ).fetchone()
            if not row:
                raise not_found(f"DCR이 없다: {dcr_id}")
            result = dict(row)
            for key in ("target_refs_json", "base_revisions_json", "supersedes_json"):
                result[key.removesuffix("_json")] = json.loads(result.pop(key))
            result["timeline"] = [
                dict(e)
                for e in conn.execute(
                    "SELECT at,actor,op,before_json,after_json FROM decision_event WHERE project_id=? AND dcr_id=? ORDER BY seq",
                    (pid, dcr_id),
                )
            ]
        return result

    def dcr_create(
        self,
        ctx: Ctx,
        title: str,
        rationale: str,
        proposal: str,
        target_refs: list[Any] | None = None,
    ) -> dict[str, Any]:
        p, pid = self._identity(ctx)
        if not all(isinstance(x, str) and x.strip() for x in (title, rationale, proposal)):
            raise invalid_field("DCR", "title, rationale, proposal이 필요하다")
        if len((title + rationale + proposal).encode("utf-8")) > 150 * 1024:
            raise invalid_field("DCR", "DCR 본문 합계는 150KB까지")
        for value, field in ((title, "title"), (rationale, "rationale"), (proposal, "proposal")):
            scan_secrets(value, field)
        refs = target_refs or []
        if not isinstance(refs, list) or any(not isinstance(x, str) for x in refs):
            raise invalid_field("target_refs", "문자열 배열이어야 한다")
        base_revisions: dict[str, Any] = {}
        for ref in refs:
            current = self.get(ctx, ref)
            base_revisions[ref] = {
                "revision": current["revision"],
                "source_sha": current.get("source_sha"),
                "content_sha256": current.get("content_sha256"),
            }
        with self.store.write() as conn:
            row = conn.execute(
                "SELECT COALESCE(MAX(CAST(SUBSTR(id,5) AS INTEGER)),0)+1 FROM decision_change WHERE project_id=?",
                (pid,),
            ).fetchone()
            dcr_id = f"DCR-{row[0]:04d}"
            now = _iso(ctx.now)
            conn.execute(
                "INSERT INTO decision_change(project_id,id,title,rationale,proposal_md,target_refs_json,base_revisions_json,status,author,created_at,updated_at) VALUES(?,?,?,?,?,?,?,'open',?,?,?)",
                (
                    pid,
                    dcr_id,
                    title.strip(),
                    rationale.strip(),
                    proposal,
                    _json(refs),
                    _json(base_revisions),
                    p.callsign,
                    now,
                    now,
                ),
            )
            conn.execute(
                "INSERT INTO decision_event(project_id,dcr_id,at,actor,op,after_json) VALUES(?,?,?,?,?,?)",
                (
                    pid,
                    dcr_id,
                    now,
                    p.callsign,
                    "create",
                    _json({"status": "open", "title": title.strip()}),
                ),
            )
        return {"id": dcr_id, "status": "open", "version": 1, "title": title.strip()}

    def dcr_decide(
        self, ctx: Ctx, dcr_id: str, expected_version: int, outcome: str, rationale: str
    ) -> dict[str, Any]:
        p, pid = self._identity(ctx, owner=True)
        if (
            outcome not in ("approve", "reject")
            or not isinstance(rationale, str)
            or not rationale.strip()
        ):
            raise invalid_field("decision", "approve/reject와 판단 근거가 필요하다")
        with self.store.write() as conn:
            row = conn.execute(
                "SELECT * FROM decision_change WHERE project_id=? AND id=?", (pid, dcr_id)
            ).fetchone()
            if not row:
                raise not_found(f"DCR이 없다: {dcr_id}")
            if row["version"] != expected_version:
                raise version_conflict(row["version"], dict(row))
            if row["status"] != "open":
                raise HubError(
                    409, "invalid_dcr_transition", f"open 상태만 결정할 수 있다: {row['status']}"
                )
            if outcome == "approve":
                bases = json.loads(row["base_revisions_json"])
                for ref, base in bases.items():
                    if ref.startswith("hub-wiki:"):
                        path = ref[len("hub-wiki:") :].rsplit("@", 1)[0]
                        current = conn.execute(
                            "SELECT version FROM wiki_page WHERE project_id=? AND path=?",
                            (pid, path),
                        ).fetchone()
                        if not current or current["version"] != base["revision"]:
                            raise HubError(
                                409, "stale_decision_base", f"DCR target가 바뀌었다: {ref}"
                            )
                    else:
                        match = re.fullmatch(r"git:([^:]+):(.+)@([0-9a-f]{7,40})", ref)
                        if not match:
                            raise invalid_field("target_refs", "유효한 지식 ref가 아니다")
                        current = conn.execute(
                            "SELECT commit_sha,content_sha256 FROM knowledge_revision r JOIN knowledge_source s ON s.project_id=r.project_id AND s.id=r.source_id WHERE r.project_id=? AND s.repo_key=? AND r.path=? AND r.status='active' ORDER BY r.revision DESC LIMIT 1",
                            (pid, match.group(1), match.group(2)),
                        ).fetchone()
                        if (
                            not current
                            or current["commit_sha"] != base.get("source_sha")
                            or current["content_sha256"] != base.get("content_sha256")
                        ):
                            raise HubError(
                                409, "stale_decision_base", f"DCR target가 바뀌었다: {ref}"
                            )
            status = "approved_pending_export" if outcome == "approve" else "rejected"
            now = _iso(ctx.now)
            adr = None
            if outcome == "approve":
                max_adr = 0
                for item in conn.execute(
                    "SELECT path,body_md FROM knowledge_revision WHERE project_id=?", (pid,)
                ):
                    match = re.search(
                        r"(?:adr_id:\s*ADR-|id:\s*ADR-|/adr-)(\d{3,})",
                        item["path"] + "\n" + item["body_md"],
                        re.I,
                    )
                    if match:
                        max_adr = max(max_adr, int(match.group(1)))
                adr_number = max_adr + 1
                adr_id = f"ADR-{adr_number:03d}"
                adr_suffix = f"{adr_number:03d}"
                slug = (
                    re.sub(r"[^a-z0-9]+", "-", row["title"].lower()).strip("-")[:48] or "decision"
                )
                superseded_refs = [
                    r
                    for r in json.loads(row["target_refs_json"])
                    if isinstance(r, str) and re.search(r"(?:^|/)adr-[^/]+\.md(?:@|$)", r)
                ]
                supersedes = json.dumps(superseded_refs, ensure_ascii=False, separators=(",", ":"))
                adr_path = f"ai-workflow/wiki/decisions/adr-{adr_suffix}-{slug}.md"
                adr = (
                    f"---\nadr_id: {adr_id}\nstatus: accepted\nsupersedes: {supersedes}\ndcr: {dcr_id}\n---\n\n"
                    f"# {row['title']}\n\n## Context\n\n{row['rationale']}\n\n## Decision\n\n{row['proposal_md']}\n\n## Approval\n\n{rationale.strip()}\n"
                )
                scan_secrets(adr, "adr")
                digest = hashlib.sha256(adr.encode()).hexdigest()
                conn.execute(
                    "UPDATE decision_change SET status=?,reviewer=?,decision_rationale=?,adr_path=?,adr_sha256=?,version=version+1,updated_at=? WHERE project_id=? AND id=?",
                    (status, p.callsign, rationale.strip(), adr_path, digest, now, pid, dcr_id),
                )
            else:
                conn.execute(
                    "UPDATE decision_change SET status=?,reviewer=?,decision_rationale=?,version=version+1,updated_at=? WHERE project_id=? AND id=?",
                    (status, p.callsign, rationale.strip(), now, pid, dcr_id),
                )
            conn.execute(
                "INSERT INTO decision_event(project_id,dcr_id,at,actor,op,before_json,after_json) VALUES(?,?,?,?,?,?,?)",
                (
                    pid,
                    dcr_id,
                    now,
                    p.callsign,
                    outcome,
                    _json({"status": "open", "version": expected_version}),
                    _json({"status": status, "rationale": rationale.strip()}),
                ),
            )
        result = {"id": dcr_id, "status": status, "version": expected_version + 1}
        if adr is not None:
            result.update(
                {
                    "adr_path": adr_path,
                    "content": adr,
                    "content_sha256": digest,
                    "instruction": "Commit this exact file in Git, then sync the matching commit and document. The DCR becomes accepted only after hash confirmation.",
                }
            )
        return result
