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


def test_knowledge_lifecycle() -> int:
    root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(root / "workflow-source"))
    from workflow_kit.hub import db as hubdb  # noqa: E402

    with tempfile.TemporaryDirectory(prefix="hub-knowledge-") as td:
        db = Path(td) / "hub.sqlite"
        hubdb.open_db(db, now=datetime.now(timezone.utc))
        binary = os.environ.get("WORKFLOW_HUB_TEST_BIN")
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
            path = "ai-workflow/wiki/decisions/adr-037-test-choice.md"
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
            checks.append(
                st == 200
                and approved["status"] == "approved_pending_export"
                and approved["adr_path"] == path
            )
            st, _, _ = hub.call(
                "hub_knowledge_sync",
                {
                    "source_id": "repo-docs",
                    "commit_sha": "b" * 40,
                    "documents": [
                        {"path": path, "title": "ADR-037 Test Choice", "body": approved["content"]}
                    ],
                },
                agent,
            )
            checks.append(st == 200)
            st, dcr_after, _ = hub.call("hub_dcr_get", {"id": dcr["id"]}, agent)
            checks.append(
                st == 200 and dcr_after["status"] == "accepted" and dcr_after["adr_path"] == path
            )
            st, adr_hits, _ = hub.call("hub_knowledge_search", {"query": "Test Choice"}, agent)
            checks.append(
                st == 200
                and any(h["kind"] == "adr" and h["status"] == "accepted" for h in adr_hits["hits"])
            )
            st, historical, _ = hub.call("hub_knowledge_get", {"ref": old_ref}, agent)
            checks.append(st == 200 and historical["status"] == "superseded")
            st, listed, _ = hub.call("hub_dcr_list", {"status": "accepted"}, agent)
            checks.append(st == 200 and listed["dcrs"][0]["id"] == dcr["id"])
        finally:
            hub.stop()
    passed = sum(checks)
    print(f"hub knowledge lifecycle: {passed}/{len(checks)} passed")
    if passed != len(checks):
        print(f"failed case indexes: {[i + 1 for i, ok in enumerate(checks) if not ok]}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(test_knowledge_lifecycle())
