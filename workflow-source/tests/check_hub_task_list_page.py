#!/usr/bin/env python3
"""Hub task classification facets, exact filters, and stable page boundaries (M-061)."""

from __future__ import annotations

import json
import sys
import tempfile
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "workflow-source"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_hub_core import Hub  # noqa: E402

from workflow_kit.hub import db  # noqa: E402
from workflow_kit.hub.store import Ctx, Store  # noqa: E402


def test_task_list_page() -> None:
    now = datetime.now(timezone.utc).replace(microsecond=0)
    with tempfile.TemporaryDirectory(prefix="hub-task-page-") as td:
        path = Path(td) / "hub.db"
        db.open_db(path, now=now)
        store = Store(path)
        registered = store.register_project(Ctx(now=now, via="test"), "https://github.com/acme/task-page",
                                            "Task page", "owner-human", "human")
        principal = store.authenticate(registered["token"], now)
        assert principal is not None
        ctx = Ctx(now=now, via="test", principal=principal)
        category = {"category": {"level_1": "Product", "level_2": "Hub", "level_3": "Listing"}}
        for values in (
            {"title": "page one", "wbs": "M-061/WBS-61.1", "fields": category},
            {"title": "page two", "wbs": "M-061/WBS-61.2", "fields": category},
            {"title": "unlinked", "fields": {"category": {"level_1": "Operations", "level_2": "Support", "level_3": "Triage"}}},
        ):
            store.task_create(ctx, values)
        filters = {"roadmap": "linked", "milestone": "M-061", "category_level_1": "Product"}
        first = store.task_list_page(ctx, filters, limit=1, offset=0)
        second = store.task_list_page(ctx, filters, limit=1, offset=1)
        assert first["total"] == second["total"] == 2
        assert first["tasks"][0]["id"] != second["tasks"][0]["id"]
        assert {"M-061/WBS-61.1", "M-061/WBS-61.2"}.issubset(first["facets"]["wbs"])
        exact = store.task_list_page(ctx, {"wbs": "M-061/WBS-61.1", "category_level_3": "Listing"})
        assert exact["total"] == 1 and exact["tasks"][0]["title"] == "page one"
        assert store.task_list_page(ctx, {"roadmap": "unlinked"})["total"] == 1

        live = Hub(path, cmd_prefix=[sys.executable, "-m", "workflow_kit", "hub"])
        try:
            query = urlencode({**filters, "limit": 1, "offset": 1})
            request = urllib.request.Request(live.base + f"/api/projects/{registered['project_id']}/tasks?{query}",
                                             headers={"Authorization": f"Bearer {registered['token']}"})
            with urllib.request.urlopen(request, timeout=5) as response:
                api_result = json.loads(response.read())
            assert api_result["total"] == 2 and len(api_result["tasks"]) == 1 and api_result["offset"] == 1
        finally:
            live.stop()


if __name__ == "__main__":
    test_task_list_page()
    print("hub task list page: filters + pagination PASS")
