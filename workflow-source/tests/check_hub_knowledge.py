#!/usr/bin/env python3
"""Project-scoped knowledge snapshots and DCR/ADR publication checks."""

from __future__ import annotations

import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_hub_core import Hub  # noqa: E402


def test_knowledge_lifecycle(binary: str | None = None) -> int:
    root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(root / "workflow-source"))
    from workflow_kit.hub import db as hubdb  # noqa: E402

    with tempfile.TemporaryDirectory(prefix="hub-knowledge-") as td:
        db = Path(td) / "hub.sqlite"
        hubdb.open_db(db, now=datetime.now(timezone.utc))
        binary = binary or os.environ.get("WORKFLOW_HUB_TEST_BIN")
        hub = Hub(db, cmd_prefix=[binary] if binary else None)
        try:
            reg = hub.call(
                "hub_project_register",
                {
                    "remote_url": "git@github.com:acme/knowledge.git",
                    "display_name": "Knowledge",
                    "callsign": "owner-human",
                    "kind": "human",
                },
            )[1]
            owner = reg["token"]
            agent = hub.call(
                "hub_callsign_register",
                {"project_id": reg["project_id"], "callsign": "agent-writer", "kind": "agent"},
                owner,
            )[1]["token"]
            old_path = "ai-workflow/wiki/decisions/adr-036-old-choice.md"
            path = "decisions/adr-037-test-choice.md"  # 승인 = 허브 위키 (소유자 2026-11-26)
            code = "a" * 40
            checks = []

            st, source, _ = hub.call(
                "hub_knowledge_source_register",
                {
                    "source_id": "repo-docs",
                    "repo_key": "github.com/acme/knowledge",
                    "allowlist": ["docs/design.md", old_path, path],
                },
                owner,
            )
            checks.append(st == 200 and source["authority"] == "git")
            st, _, _ = hub.call(
                "hub_knowledge_source_register",
                {
                    "source_id": "agent-source",
                    "repo_key": "github.com/acme/knowledge",
                    "allowlist": ["docs/design.md"],
                },
                agent,
            )
            checks.append(st == 403)
            st, synced, _ = hub.call(
                "hub_knowledge_sync",
                {
                    "source_id": "repo-docs",
                    "commit_sha": code,
                    "documents": [
                        {
                            "path": "docs/design.md",
                            "title": "Design",
                            "body": "# Design\nShared project knowledge baseline.\n",
                        },
                        {
                            "path": old_path,
                            "title": "ADR-036 Old Choice",
                            "body": "---\nadr_id: ADR-036\nstatus: accepted\n---\n\n# Old Choice\n",
                        },
                    ],
                },
                agent,
            )
            checks.append(st == 200 and synced["documents"][0]["revision"] == 1)
            ref = f"git:github.com/acme/knowledge:docs/design.md@{code}"
            st, found, _ = hub.call("hub_knowledge_search", {"query": "shared baseline"}, agent)
            checks.append(st == 200 and len(found["hits"]) == 1 and found["hits"][0]["ref"] == ref)
            st, read, _ = hub.call("hub_knowledge_get", {"ref": ref}, agent)
            checks.append(st == 200 and "baseline" in read["body"])
            st, _, _ = hub.call(
                "hub_wiki_ingest",
                {
                    "summary": "knowledge snapshot",
                    "pages": [
                        {
                            "path": "concepts/knowledge.md",
                            "body": "# Knowledge UI page\nUnique wiki-snapshot phrase.\n",
                            "expected_version": 0,
                        }
                    ],
                },
                agent,
            )
            checks.append(st == 200)
            st, wiki_hits, _ = hub.call("hub_knowledge_search", {"query": "wiki-snapshot"}, agent)
            checks.append(st == 200 and wiki_hits["hits"][0]["kind"] == "wiki")
            st, wiki_read, _ = hub.call(
                "hub_knowledge_get", {"ref": wiki_hits["hits"][0]["ref"]}, agent
            )
            checks.append(st == 200 and "Unique wiki-snapshot" in wiki_read["body"])
            old_ref = f"git:github.com/acme/knowledge:{old_path}@{code}"
            st, dcr, _ = hub.call(
                "hub_dcr_create",
                {
                    "title": "Test Choice",
                    "rationale": "Current rule is insufficient.",
                    "proposal": "Adopt the new rule.",
                    "target_refs": [old_ref],
                },
                agent,
            )
            checks.append(st == 200 and dcr["status"] == "open")
            st, dcr_hits, _ = hub.call("hub_knowledge_search", {"query": "Adopt new rule"}, agent)
            checks.append(st == 200 and any(h["kind"] == "dcr" for h in dcr_hits["hits"]))
            st, _, _ = hub.call(
                "hub_dcr_decide",
                {
                    "id": dcr["id"],
                    "expected_version": 1,
                    "outcome": "approve",
                    "rationale": "Approved by owner.",
                },
                agent,
            )
            checks.append(st == 403)
            st, approved, _ = hub.call(
                "hub_dcr_decide",
                {
                    "id": dcr["id"],
                    "expected_version": 1,
                    "outcome": "approve",
                    "rationale": "Approved by owner.",
                },
                owner,
            )
            # 승인이 곧 확정 — 같은 트랜잭션에서 위키 ADR 이 생기고 DCR 은 accepted, 대상 Git ADR 은 superseded
            checks.append(
                st == 200
                and approved["status"] == "accepted"
                and approved["adr_id"] == "ADR-037"
                and approved["adr_path"] == path
                and approved["wiki"]["path"] == path
                and approved["wiki"]["version"] == 1
                and "instruction" not in approved
            )
            st, page, _ = hub.call("hub_wiki_get", {"path": path}, agent)
            front = page.get("body", "").split("---", 2)[1] if page.get("body", "").startswith("---") else ""
            checks.append(
                st == 200
                and page["body"] == approved["content"]
                and all(k in front for k in ("type: decision", "status: accepted", "adr_id: ADR-037", "decided_at:", "alternatives_considered:", "related_pages:", f"dcr: {dcr['id']}"))
                and "# ADR-037: Test Choice" in page["body"]
            )
            st, dcr_after, _ = hub.call("hub_dcr_get", {"id": dcr["id"]}, agent)
            checks.append(
                st == 200 and dcr_after["status"] == "accepted" and dcr_after["adr_path"] == path
            )
            st, lint, _ = hub.call("hub_wiki_lint", {}, agent)
            checks.append(st == 200 and path not in str(lint))
            # 번호는 위키 ADR 까지 본다 — 위키에 adr-050 이 있으면 다음 승인은 051
            st, _, _ = hub.call("hub_wiki_ingest", {"summary": "manual adr", "pages": [
                {"path": "decisions/adr-050-manual.md", "expected_version": 0,
                 "body": "---\ntype: decision\nstatus: accepted\nadr_id: ADR-050\n---\n\n# ADR-050\n"}]}, agent)
            st2, dcr2, _ = hub.call("hub_dcr_create", {"title": "Next Choice", "rationale": "r", "proposal": "p", "target_refs": []}, agent)
            st3, approved2, _ = hub.call("hub_dcr_decide", {"id": dcr2["id"], "expected_version": 1, "outcome": "approve", "rationale": "ok"}, owner)
            checks.append(st == 200 and st3 == 200 and approved2["adr_id"] == "ADR-051" and approved2["adr_path"] == "decisions/adr-051-next-choice.md")
            hub.call("hub_wiki_ingest", {"summary": "squat", "pages": [
                {"path": "decisions/adr-052-third-choice.md", "expected_version": 0, "body": "# squat\n"}]}, agent)
            # 052 를 미리 차지하면 번호는 053 — 충돌 대신 다음 번호를 쓴다
            st4, dcr3, _ = hub.call("hub_dcr_create", {"title": "Third Choice", "rationale": "r", "proposal": "p", "target_refs": []}, agent)
            st5, approved3, _ = hub.call("hub_dcr_decide", {"id": dcr3["id"], "expected_version": 1, "outcome": "approve", "rationale": "ok"}, owner)
            checks.append(st5 == 200 and approved3["adr_id"] == "ADR-053")
            # 3.6.1 이하에서 승인돼 approved_pending_export 에 남은 DCR 은 예전 sync 로 끝난다
            st, historical, _ = hub.call("hub_knowledge_get", {"ref": old_ref}, agent)
            checks.append(st == 200 and historical["status"] == "superseded")
            legacy_path = "docs/design.md"  # allowlist 안의 옛 ADR 이 아닌 경로 — 위의 superseded 확인을 덮지 않는다
            st6, dcr4, _ = hub.call("hub_dcr_create", {"title": "Legacy", "rationale": "r", "proposal": "p", "target_refs": []}, agent)
            legacy_body = "---\nadr_id: ADR-099\nstatus: accepted\n---\n\n# Legacy\n"
            import hashlib  # noqa: PLC0415
            import sqlite3  # noqa: PLC0415
            with sqlite3.connect(db) as c:
                c.execute("UPDATE decision_change SET status='approved_pending_export', adr_path=?, adr_sha256=? WHERE id=?",
                          (legacy_path, hashlib.sha256(legacy_body.encode()).hexdigest(), dcr4["id"]))
            st7, _, _ = hub.call("hub_knowledge_sync", {"source_id": "repo-docs", "commit_sha": "c" * 40,
                                                         "documents": [{"path": legacy_path, "title": "Legacy", "body": legacy_body}]}, agent)
            st8, legacy_after, _ = hub.call("hub_dcr_get", {"id": dcr4["id"]}, agent)
            checks.append(st6 == 200 and st7 == 200 and legacy_after["status"] == "accepted")
            st, listed, _ = hub.call("hub_dcr_list", {"status": "accepted"}, agent)
            checks.append(st == 200 and {dcr["id"], dcr2["id"], dcr3["id"], dcr4["id"]} <= {x["id"] for x in listed["dcrs"]})
        finally:
            hub.stop()
    passed = sum(checks)
    print(f"hub knowledge lifecycle [{'go' if binary else 'python'}]: {passed}/{len(checks)} passed")
    if passed != len(checks):
        print(f"failed case indexes: {[i + 1 for i, ok in enumerate(checks) if not ok]}")
        return 1
    return 0


def main() -> int:
    rc = test_knowledge_lifecycle()
    from check_hub_core import _resolve_go_hub  # noqa: PLC0415
    with tempfile.TemporaryDirectory(prefix="hub-knowledge-go-") as td:
        cmd, why = _resolve_go_hub(Path(td))
        if cmd is None:
            print(f"    [unmeasured] Go 허브 미측정: {why}")
            return rc
        return rc | test_knowledge_lifecycle(cmd[0])


if __name__ == "__main__":
    raise SystemExit(main())
