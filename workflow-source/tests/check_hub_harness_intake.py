#!/usr/bin/env python3
"""Client report → hub-admin review → global metadata registry contract."""

from __future__ import annotations

import json
import sys
import tempfile
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "workflow-source"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_hub_core import Hub, _mcp_session  # noqa: E402

from workflow_kit.hub import db, tools  # noqa: E402
from workflow_kit.hub.errors import HubError  # noqa: E402
from workflow_kit.hub.harness_intake import HarnessIntake  # noqa: E402
from workflow_kit.hub.store import Ctx, Store  # noqa: E402


def test_intake_review() -> int:
    now = datetime.now(timezone.utc)
    with tempfile.TemporaryDirectory(prefix="hub-harness-intake-") as td:
        path = Path(td) / "hub.db"
        db.open_db(path, now=now)
        store = Store(path)
        owner_data = store.register_project(Ctx(now=now, via="test"), "https://github.com/acme/harness",
                                            "Harness", "owner-human", "human")
        owner = store.authenticate(owner_data["token"], now)
        assert owner is not None
        admin_token = store.issue_hub_token("admin", "test-reviewer", now)
        admin = store.authenticate(admin_token, now)
        assert admin is not None and admin.kind == "admin"
        owner_ctx = Ctx(now=now, via="mcp", principal=owner, client_version="client-test")
        intake = HarnessIntake(store)
        report = {
            "harness_id": "new-agent",
            "display_name": "New Agent",
            "version": "1.2.3",
            "platforms": ["windows"],
            "mcp_transports": ["streamable-http"],
            "config_formats": ["mcp-http-json-v1"],
            "entry_file_candidates": ["AGENTS.md"],
            "mcp_config_candidates": ["harness-mcp.json"],
            "documentation_url": "https://example.com/docs",
            "notes": "Client observed MCP support.",
        }
        started = tools.call(store, "hub_session_start", {
            "session": {"harness": "new-agent", "kind": "worker", "delivery": ["wait"]},
        }, owner_ctx)
        assert started["hub"]["harness_support"]["status"] == "unknown"
        assert started["hub"]["harness_support"]["report_tool"] == "hub_harness_report"
        with store.read() as conn:
            setup_before = conn.execute("SELECT COUNT(*) FROM setup_step").fetchone()[0]
        unsupported = tools.call(store, "hub_setup_plan", {
            "project_id": owner.project_id, "token": owner_data["token"], "harnesses": ["new-agent"],
            "scan": {"files": {}},
        }, owner_ctx)
        assert unsupported["stage"] == "harness_support" and unsupported["steps"] == []
        with store.read() as conn:
            assert conn.execute("SELECT COUNT(*) FROM setup_step").fetchone()[0] == setup_before
        submitted = tools.call(store, "hub_harness_report", {"report": report}, owner_ctx)
        assert submitted["status"] == "pending" and submitted["registered"] is False
        replay = tools.call(store, "hub_harness_report", {"report": report}, owner_ctx)
        assert replay["report_id"] == submitted["report_id"] and replay["replayed"] is True
        assert intake.registry_list(owner_ctx)["harnesses"] == []
        assert "hub_harness_admin_decide" not in {t.name for t in tools.visible_tools("admin")}
        assert "hub_harness_admin_decide" not in {t.name for t in tools.visible_tools("callsign")}
        assert "hub_harness_admin_decide" not in {t.name for t in tools.visible_tools(None)}
        try:
            tools.call(store, "hub_harness_report", {"report": {**report, "entry_file_candidates": ["../../secret"]}}, owner_ctx)
        except HubError as exc:
            assert exc.status == 400
        else:
            raise AssertionError("unsafe relative path was accepted")
        try:
            tools.call(store, "hub_harness_report", {"report": {**report, "notes": "wfh_" + "a" * 24}}, owner_ctx)
        except HubError as exc:
            assert exc.code == "secret_in_payload"
        else:
            raise AssertionError("secret-shaped text was accepted")
        live = Hub(path, cmd_prefix=[sys.executable, "-m", "workflow_kit", "hub"])
        try:
            def ui_call(path: str, *, method: str = "GET", body: dict | None = None, token: str = admin_token):
                data = json.dumps(body).encode() if body is not None else None
                request = urllib.request.Request(live.base + path, data=data, method=method,
                                                 headers={"Authorization": f"Bearer {token}",
                                                          **({"Content-Type": "application/json"} if body is not None else {})})
                try:
                    with urllib.request.urlopen(request, timeout=5) as response:
                        return response.status, json.loads(response.read())
                except urllib.error.HTTPError as exc:
                    return exc.code, json.loads(exc.read())

            admin_names, _ = _mcp_session(live.base, admin_token, [])
            owner_names, _ = _mcp_session(live.base, owner_data["token"], [])
            assert "hub_harness_admin_decide" not in admin_names
            assert "hub_harness_admin_decide" not in owner_names
            assert ui_call("/api/harness-reports?status=pending", token=owner_data["token"])[0] == 403
            assert ui_call(f"/api/harness-reports/{submitted['report_id']}/decision", method="POST",
                           body={"decision": "approve"})[0] == 400
            p1 = ui_call("/api/harness-people", method="POST", body={"display_name": "Harness Steward"})
            p2 = ui_call("/api/harness-people", method="POST", body={"display_name": "Compatibility Reviewer"})
            assert p1[0] == 200 and p2[0] == 200
            owner_ids = [p1[1]["person"]["id"], p2[1]["person"]["id"]]
            decision = ui_call(f"/api/harness-reports/{submitted['report_id']}/decision", method="POST",
                               body={"decision": "approve", "note": "setup profile reviewed", "owner_ids": owner_ids,
                                     "setup_profile": {"kind": "mcp-http-json-v1", "entry_file": "AGENTS.md",
                                                       "mcp_config_path": "harness-mcp.json"}})
            assert decision[0] == 200 and decision[1]["registered"] is True and decision[1]["setup_ready"] is True
            with store.read() as conn:
                notices = conn.execute("SELECT body_json FROM inbox_message WHERE project_id=? AND to_kind='callsign' AND to_id=? AND kind='approval'",
                                       (owner.project_id, owner.callsign)).fetchall()
            harness_results = [json.loads(row["body_json"]) for row in notices
                               if json.loads(row["body_json"]).get("event") == "harness_support_result"]
            assert len(harness_results) == 1 and harness_results[0]["state"] == "approved"
            queue = ui_call("/api/harness-reports?status=approved")
            assert queue[0] == 200 and len(queue[1]["reports"]) == 1
            listing = tools.call(store, "hub_harness_registry_list", {}, owner_ctx)
            assert listing["harnesses"][0]["harness_id"] == "new-agent"
            assert listing["harnesses"][0]["setup_ready"] is True
            assert len(listing["harnesses"][0]["owners"]) == 2
            supported = tools.call(store, "hub_session_start", {
                "session": {"harness": "new-agent", "kind": "worker", "delivery": ["wait"]},
            }, owner_ctx)
            assert supported["hub"]["harness_support"]["status"] == "setup_supported"
            rendered = tools.call(store, "hub_guide_render", {"harness": "new-agent"}, owner_ctx)
            assert rendered["path"] == "AGENTS.md" and rendered["blocked"] is False
            setup_args = {"project_id": owner.project_id, "token": owner_data["token"],
                          "harnesses": ["new-agent"],
                          "scan": {"files": {".gitignore": "/.workflow-hub/\n", "AGENTS.md": None,
                                              "harness-mcp.json": "{}"}}}
            first_plan = tools.call(store, "hub_setup_plan", setup_args, owner_ctx)
            assert first_plan["stage"] == "gitignore"
            confirmation = tools.call(store, "hub_setup_confirm", {
                "project_id": owner.project_id, "token": owner_data["token"], "files": [],
                "checks": [{"name": "check_ignore", "rc": 0,
                            "output": ".gitignore:1:/.workflow-hub/ .workflow-hub/env"}],
            }, owner_ctx)
            assert "gitignore" in confirmation["confirmed"]
            file_plan = tools.call(store, "hub_setup_plan", setup_args, owner_ctx)
            config_step = next(step for step in file_plan["steps"] if step.get("path") == "harness-mcp.json")
            assert file_plan["stage"] == "files"
            assert "${WORKFLOW_HUB_TOKEN}" in config_step["content"]
            # .mcp.json 이 아닌 승인 설정 파일도 해시로 확인되고 셋업이 끝난다
            written = [{"path": step["path"], "sha256": step["sha256_after"]} for step in file_plan["steps"]]
            wrong = [{**item, "sha256": "0" * 64} if item["path"] == "harness-mcp.json" else item for item in written]
            partial = tools.call(store, "hub_setup_confirm", {
                "project_id": owner.project_id, "token": owner_data["token"], "files": wrong, "checks": []}, owner_ctx)
            assert partial["setup_complete"] is False and partial["unconfirmed"][0]["id"] == config_step["id"]
            finished = tools.call(store, "hub_setup_confirm", {
                "project_id": owner.project_id, "token": owner_data["token"], "files": written, "checks": []}, owner_ctx)
            assert finished["setup_complete"] is True, finished
        finally:
            live.stop()
    return 21


if __name__ == "__main__":
    count = test_intake_review()
    print(f"hub harness intake: {count}/{count} PASS")
