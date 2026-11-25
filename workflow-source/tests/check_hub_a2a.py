#!/usr/bin/env python3
"""허브 A2A 1.0 (M-062 A1) — Agent Card · JSON-RPC 승인 Task 를 Python · Go 실프로세스에서 같은 요청으로 잰다.

1. Agent Card — 토큰 없이 · 공개 주소의 /a2a · 필수 칸 · 구현한 능력만 선언
2. 경계 — 토큰 없음 401 · 허브 토큰 403 · 판 협상 · JSON-RPC 오류 코드 · 미지원 메서드
3. 승인 왕복 — AUTH_REQUIRED → 계정 로그인 승인 → COMPLETED + approval_id → 그 실행이 열림, 상태만으로는 안 열림
4. 거절 · 취소 · 멱등 · 다른 콜사인은 TaskNotFound · 취소한 요청은 승인할 수 없음
5. 목록 — 정렬 · 쪽 · 상태/맥락/시각 거르기 · 아티팩트 · 이력
8. 스트림 — 승인 · 거절 · 취소로 끝나고 남의 Task · 끝난 Task 는 구독 못 함, 거둔 토큰은 닫힘
9. 콜사인 간 메시지 — 받은편지함과 다른 칸 · 자료 표시 · 답 한 번 · 제3자 TaskNotFound · 대기를 깨우지 않음
7. hub_client.py — 이관 요청 → 승인 전 거절 → 로그인 승인 → 같은 Task 로 들여오기
6. Python 과 Go 가 같은 시나리오에서 같은 모양의 답을 낸다 (id · 시각 빼고)
"""

from __future__ import annotations

CHECK_TIMEOUT_S = 240

WATCHES = (
    "workflow-source/workflow_kit/*",
    "hub-go/*",
    "workflow-source/tests/check_hub_core.py",
    "workflow-source/tests/check_hub_migrate.py",
    "workflow-source/tests/check_roadmap_gates.py",
    "workflow-source/pyproject.toml",
)

import json
import re
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import check_hub_migrate as mig  # noqa: E402
from check_hub_core import Hub, _env, _resolve_go_hub  # noqa: E402

PUBLIC = "https://home.example/workflow"
_failures: list[str] = []
_passes: list[str] = []


def _record(case: str, ok: bool, detail: str = "") -> None:
    (_passes if ok else _failures).append(case if ok else f"{case}: {detail}")
    print(f"  {case}: {'PASS' if ok else 'FAIL'}{(' — ' + detail) if detail and not ok else ''}")


def http(base: str, path: str, body: Any = None, *, token: str = "", headers: dict[str, str] | None = None, raw: bytes | None = None) -> tuple[int, Any, Any]:
    h = {"content-type": "application/json", **(headers or {}), **({"authorization": f"Bearer {token}"} if token else {})}
    data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
    req = urllib.request.Request(base + path, data=data, headers=h, method="POST" if data is not None else "GET")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read()), r.headers
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read()), e.headers


def scrub(value: Any) -> Any:
    """두 구현을 견주기 위해 id · 시각을 지운다."""
    if isinstance(value, dict):
        return {k: scrub(v) for k, v in value.items()}
    if isinstance(value, list):
        return [scrub(v) for v in value]
    if isinstance(value, str):
        value = re.sub(r"(A2A|A2M|MSG)-\d{8}-[0-9a-f]+", r"\1-*", value)
        value = re.sub(r"CTX-[0-9a-f]+", "CTX-*", value)
        value = re.sub(r"P-\d{8}-[0-9a-f]+", "P-*", value)
        value = re.sub(r"\b[0-9a-f]{40}\b", "<sha>", value)
        return re.sub(r"\d{4}-\d\d-\d\dT[\d:.]+(?:Z|\+00:00)", "<time>", value)
    return value


def scenario(impl: str, cmd: list[str] | None, tmp: Path) -> dict[str, Any]:
    log: dict[str, Any] = {}
    db = tmp / "hub.db"
    repo = mig.build_repo(tmp)
    hub = Hub(db, extra=("--public-url", PUBLIC), cmd_prefix=cmd)
    prefix = cmd or [sys.executable, "-m", "workflow_kit", "hub"]
    try:
        reg = hub.call("hub_project_register", {"remote_url": "git@github.com:acme/a2a.git", "display_name": "a2a",
                                                 "callsign": "owner-a", "kind": "human"})[1]
        owner, pid = reg["token"], reg["project_id"]
        agent, rival = (hub.call("hub_callsign_register", {"project_id": pid, "callsign": c, "kind": "agent"})[1]["token"]
                        for c in ("agent-a", "rival-a"))
        admin = json.loads(subprocess.run([*prefix, "admin", "--db", str(db), "token", "issue", "--role", "admin", "--name", "ops"],
                                          capture_output=True, encoding="utf-8", env=_env(), timeout=60).stdout)["token"]

        # 1
        st, card, _ = http(hub.base, "/.well-known/agent-card.json")
        log["card"] = card
        required = {"name", "description", "supportedInterfaces", "version", "capabilities", "defaultInputModes", "defaultOutputModes", "skills"}
        face = card["supportedInterfaces"][0]
        _record(f"case 1 (Agent Card) [{impl}]",
                st == 200 and required <= set(card) and face == {"url": PUBLIC + "/a2a", "protocolBinding": "JSONRPC", "protocolVersion": "1.0"}
                and card["capabilities"]["streaming"] is True and card["capabilities"]["pushNotifications"] is False
                and all({"id", "name", "description", "tags"} <= set(s) for s in card["skills"])
                and agent not in json.dumps(card), f"{st} {card}")

        n = {"i": 0}

        def rpc(method: str, params: Any = None, token: str = agent, version: str | None = "1.0", rid: Any = "r") -> Any:
            body = {"jsonrpc": "2.0", "id": rid, "method": method, **({"params": params} if params is not None else {})}
            s, out, _ = http(hub.base, "/a2a", body, token=token, headers={"A2A-Version": version} if version is not None else {})
            return out if s == 200 else (s, out.get("error_code"))

        def code(out: Any) -> Any:
            return out["error"]["code"] if isinstance(out, dict) and "error" in out else out

        def msg(*parts: Any, **kw: Any) -> dict[str, Any]:
            n["i"] += 1
            return {"message": {"messageId": f"m-{n['i']}", "role": "ROLE_USER", "parts": list(parts), **kw}}

        # 2
        plain = msg({"text": "배포할까요?\n지금"})
        got: dict[str, Any] = {
            "no token": rpc("ListTasks", token=""), "bad token": rpc("ListTasks", token="nope"), "admin": rpc("ListTasks", token=admin),
            "no version": code(rpc("ListTasks", version=None)), "0.3": code(rpc("ListTasks", version="0.3")), "1.0.1": code(rpc("ListTasks", version="1.0.1")),
            "unknown": code(rpc("Nope")), "legacy": code(rpc("message/send", plain)), "stream": code(rpc("SendStreamingMessage", {})),
            "subscribe": code(rpc("SubscribeToTask", {"id": "x"})), "push": code(rpc("CreateTaskPushNotificationConfig", {})),
            "push list": code(rpc("ListTaskPushNotificationConfigs", {})), "ext card": code(rpc("GetExtendedAgentCard")),
            "params": code(rpc("GetTask", [])), "missing": code(rpc("GetTask", {"id": "A2A-x"})), "empty id": code(rpc("GetTask", {})),
            "id bool": code(rpc("ListTasks", rid=True)), "id null": code(rpc("ListTasks", rid=None)), "int id": rpc("ListTasks", rid=7)["id"],
            "parse": code(http(hub.base, "/a2a", raw=b"{", token=agent, headers={"A2A-Version": "1.0"})[1]),
            "batch": code(http(hub.base, "/a2a", [], token=agent, headers={"A2A-Version": "1.0"})[1]),
            "query version": code(http(hub.base, "/a2a?A2A-Version=1.0", {"jsonrpc": "2.0", "id": 1, "method": "ListTasks"}, token=agent)[1].get("result", {}).get("totalSize")),
            "no message": code(rpc("SendMessage", {})), "no parts": code(rpc("SendMessage", msg())), "role": code(rpc("SendMessage", msg({"text": "x"}, role="ROLE_AGENT"))),
            "two kinds": code(rpc("SendMessage", msg({"text": "x", "data": {}}))), "file": code(rpc("SendMessage", msg({"url": "https://x"}))),
            "raw": code(rpc("SendMessage", msg({"raw": "eA=="}))), "two data": code(rpc("SendMessage", msg({"data": {}}, {"data": {}}))),
            "unknown key": code(rpc("SendMessage", msg({"data": {"question": "q", "approval": True}}))),
            "empty text": code(rpc("SendMessage", msg({"text": " "}))), "long": code(rpc("SendMessage", msg({"text": "가" * 2001}))),
            "no id": code(rpc("SendMessage", {"message": {"role": "ROLE_USER", "parts": [{"text": "x"}]}})),
            "push cfg": code(rpc("SendMessage", {**msg({"text": "x"}), "configuration": {"taskPushNotificationConfig": {"url": "https://x"}}})),
            "bad action": code(rpc("SendMessage", msg({"data": {"question": "q", "action": {"type": "rm"}}}))),
            "no plan": code(rpc("SendMessage", msg({"data": {"question": "q", "action": {"type": "migrate_import", "migration_id": "MIG-9", "kinds": ["tasks"]}}}))),
            "secret": code(rpc("SendMessage", msg({"text": "token " + agent}))), "none created": rpc("ListTasks")["result"]["totalSize"],
        }
        want = {"no token": (401, "unauthorized"), "bad token": (401, "unauthorized"), "admin": (403, "forbidden"), "no version": -32009, "0.3": -32009,
                "1.0.1": -32009, "unknown": -32601, "legacy": -32601, "stream": -32602, "subscribe": -32001, "push": -32003, "push list": -32003,
                "ext card": -32007, "params": -32602, "missing": -32001, "empty id": -32001, "id bool": -32600, "id null": -32600, "int id": 7,
                "parse": -32700, "batch": -32600, "query version": 0, "no message": -32602, "no parts": -32602, "role": -32602, "two kinds": -32602,
                "file": -32005, "raw": -32005, "two data": -32602, "unknown key": -32602, "empty text": -32602, "long": -32602, "no id": -32602,
                "push cfg": -32003, "bad action": -32602, "no plan": -32602, "secret": -32602, "none created": 0}
        diff = {k: (got[k], want[k]) for k in want if got[k] != want[k]}
        _record(f"case 2 (경계 · 판 협상 · 오류 코드) [{impl}]", not diff, f"diff={diff}")

        # 3
        st, _, head = http(hub.base, "/api/account/enroll", {"username": "owner-x", "display_name": "O", "password": "eight-ch"}, token=owner,
                           headers={"origin": hub.base})
        cookie = head.get("set-cookie", "").split(";", 1)[0]

        def decide(request_id: str, decision: str, *, token: str = "", note: str = "") -> tuple[int, str]:
            s, out, _ = http(hub.base, f"/api/projects/{pid}/confirmations/{request_id}", {"decision": decision, "note": note}, token=token,
                             headers={"origin": hub.base, **({} if token else {"cookie": cookie})})
            return s, out.get("error_code", "")

        def pending() -> dict[str, str]:
            rows = http(hub.base, f"/api/projects/{pid}/confirmations", headers={"cookie": cookie})[1]["requests"]
            return {r["title"]: r["id"] for r in rows}

        plan = hub.call("hub_migrate_plan", {"scan": mig.run_commands(repo)}, agent)[1]
        action = {"type": "migrate_import", "migration_id": plan["migration_id"], "kinds": ["tasks"]}
        files = [{"path": f, "content": (repo / f).read_text(encoding="utf-8")} for f in plan["files"]["tasks"]]

        def run(approval: str, token: str = agent) -> tuple[int, str]:
            s, out, _ = hub.call("hub_migrate_import", {"migration_id": plan["migration_id"], "kinds": ["tasks"], "files": files, "final": True,
                                                        "approval_id": approval}, token)
            return s, out.get("error_code", "")

        send = {**msg({"text": "이관 설명"}, {"data": {"title": "이관", "question": "실행할까요?", "action": action}}, contextId="ctx-mine", metadata={"k": 1})}
        created = rpc("SendMessage", send)["result"]["task"]
        rid = pending()["이관"]
        log["created"] = created
        flow: dict[str, Any] = {
            "state": created["status"]["state"], "context": created["contextId"], "artifacts": "artifacts" in created,
            "history": created["history"][0]["taskId"] == created["id"],
            "url": created["status"]["message"]["parts"][1]["data"]["approval_url"] == f"{PUBLIC}/ui/#/p/{pid}/confirmations",
            "summary": created["status"]["message"]["parts"][1]["data"]["action"]["summary"]["files"] == {"tasks": len(files)},
            "before": run(rid), "owner token": decide(rid, "approve", token=owner), "login": decide(rid, "approve", note="확인"),
        }
        done = rpc("GetTask", {"id": created["id"]})["result"]
        log["done"] = done
        result = done.get("artifacts", [{"parts": [{"data": {}}]}])[0]["parts"][0]["data"]
        flow.update({"done": done["status"]["state"], "approval": result.get("approval_id") == rid, "approval_state": result.get("approval_state"),
                     "rival": run(rid, rival)[1], "run": run(result.get("approval_id", "")), "again": run(rid)[1],
                     "cancel done": code(rpc("CancelTask", {"id": created["id"]})), "follow up": code(rpc("SendMessage", msg({"text": "x"}, taskId=created["id"]))),
                     "used": rpc("GetTask", {"id": created["id"]})["result"]["artifacts"][0]["parts"][0]["data"]["approval_state"]})
        want3 = {"state": "TASK_STATE_AUTH_REQUIRED", "context": "ctx-mine", "artifacts": False, "history": True, "url": True, "summary": True,
                 "before": (403, "approval_pending"), "owner token": (403, "account_login_required"), "login": (200, ""), "done": "TASK_STATE_COMPLETED",
                 "approval": True, "approval_state": "approved", "rival": "approval_mismatch", "run": (200, ""), "again": "approval_used",
                 "cancel done": -32002, "follow up": -32004, "used": "used"}
        diff = {k: (flow[k], want3[k]) for k in want3 if flow[k] != want3[k]}
        _record(f"case 3 (승인 왕복 — 상태는 권한이 아니고 로그인 승인이 연다) [{impl}]", not diff, f"diff={diff}")

        # 4
        one = rpc("SendMessage", plain)["result"]["task"]
        more: dict[str, Any] = {
            "same id": rpc("SendMessage", plain)["result"]["task"]["id"] == one["id"],
            "changed": code(rpc("SendMessage", {"message": {**plain["message"], "parts": [{"text": "다른 내용"}]}})),
            "other callsign same id": rpc("SendMessage", plain, token=rival)["result"]["task"]["id"] != one["id"],
            "title": "배포할까요?" in pending(), "rival get": code(rpc("GetTask", {"id": one["id"]}, token=rival)),
            "rival cancel": code(rpc("CancelTask", {"id": one["id"]}, token=rival)), "rival follow": code(rpc("SendMessage", msg({"text": "x"}, taskId=one["id"]), token=rival)),
            "context mismatch": code(rpc("SendMessage", msg({"text": "x"}, taskId=one["id"], contextId="other"))),
        }
        no = rpc("SendMessage", msg({"text": "거절될 것"}))["result"]["task"]
        more["reject"] = decide(pending()["거절될 것"], "reject", note="안 됨")
        log["rejected"] = rpc("GetTask", {"id": no["id"]})["result"]
        more["rejected"] = (log["rejected"]["status"]["state"], log["rejected"]["status"]["message"]["parts"][1]["data"].get("note"), "artifacts" in log["rejected"])
        plan2 = hub.call("hub_migrate_plan", {"scan": mig.run_commands(repo)}, agent)[1]
        gone = rpc("SendMessage", msg({"data": {"title": "거둘 것", "question": "q", "action": {**action, "migration_id": plan2["migration_id"]}}}))["result"]["task"]
        gone_id = pending()["거둘 것"]
        log["canceled"] = rpc("CancelTask", {"id": gone["id"]})["result"]
        more.update({"canceled": log["canceled"]["status"]["state"], "cancel twice": code(rpc("CancelTask", {"id": gone["id"]})),
                     "gone from screen": "거둘 것" in pending(), "approve canceled": decide(gone_id, "approve")[0],
                     "canceled opens": hub.call("hub_migrate_import", {"migration_id": plan2["migration_id"], "kinds": ["tasks"], "files": files[:1],
                                                                       "approval_id": gone_id}, agent)[1].get("error_code"),
                     "still canceled": rpc("GetTask", {"id": gone["id"]})["result"]["status"]["state"],
                     "ack": hub.call("hub_inbox_ack", {"session": hub.call("hub_session_start", {"session": {"harness": "codex"}}, owner)[1]["session"]["id"],
                                                       "message_id": pending()["배포할까요?"], "decision": "seen"}, owner)[0]})
        want4 = {"same id": True, "changed": -32602, "other callsign same id": True, "title": True, "rival get": -32001, "rival cancel": -32001,
                 "rival follow": -32001, "context mismatch": -32602, "reject": (200, ""), "rejected": ("TASK_STATE_REJECTED", "안 됨", False),
                 "canceled": "TASK_STATE_CANCELED", "cancel twice": -32002, "gone from screen": False, "approve canceled": 409, "canceled opens": "approval_rejected",
                 "still canceled": "TASK_STATE_CANCELED", "ack": 403}
        diff = {k: (more[k], want4[k]) for k in want4 if more[k] != want4[k]}
        _record(f"case 4 (거절 · 취소 · 멱등 · 남의 Task) [{impl}]", not diff, f"diff={diff}")

        # 5
        ls = lambda **p: rpc("ListTasks", p)["result"]  # noqa: E731
        every = ls()
        first = ls(pageSize=3)
        second = ls(pageSize=3, pageToken=first["nextPageToken"])
        stamps = [t["status"]["timestamp"] for t in every["tasks"]]
        listed = {
            "total": every["totalSize"], "last token": every["nextPageToken"], "sorted": stamps == sorted(stamps, reverse=True),
            "pages": [t["id"] for t in first["tasks"] + second["tasks"]] == [t["id"] for t in every["tasks"]], "page": (first["pageSize"], second["pageSize"], second["nextPageToken"]),
            "completed": [t["id"] for t in ls(status="TASK_STATE_COMPLETED")["tasks"]] == [created["id"]], "context": ls(contextId="ctx-mine")["totalSize"],
            "no artifacts": any("artifacts" in t for t in every["tasks"]), "artifacts": any("artifacts" in t for t in ls(includeArtifacts=True)["tasks"]),
            "history 0": any("history" in t for t in ls(historyLength=0)["tasks"]), "after": ls(statusTimestampAfter="2999-01-01T00:00:00Z")["totalSize"],
            "before": ls(statusTimestampAfter="2000-01-01T00:00:00.000Z")["totalSize"],
            "bad": [code(rpc("ListTasks", p)) for p in ({"pageSize": 0}, {"pageSize": 101}, {"pageSize": "5"}, {"pageToken": "x"}, {"status": "done"},
                                                        {"statusTimestampAfter": "yesterday"}, {"includeArtifacts": "yes"}, {"historyLength": -1})],
        }
        want5 = {"total": 4, "last token": "", "sorted": True, "pages": True, "page": (3, 1, ""), "completed": True, "context": 1, "no artifacts": False,
                 "artifacts": True, "history 0": False, "after": 0, "before": 4, "bad": [-32602] * 8}
        diff = {k: (listed[k], want5[k]) for k in want5 if listed[k] != want5[k]}
        _record(f"case 5 (목록 — 정렬 · 쪽 · 거르기) [{impl}]", not diff, f"diff={diff}")
        # 7 — kit 없는 클라이언트가 A2A 로 요청하고 같은 Task 로 들인다 (공개 주소가 아니라 이 허브로 붙는다)
        import os  # noqa: PLC0415

        (repo / ".workflow-hub").mkdir(exist_ok=True)
        (repo / ".workflow-hub/env").write_text(f"WORKFLOW_HUB_URL={hub.base}\nWORKFLOW_HUB_PROJECT={pid}\nWORKFLOW_HUB_CALLSIGN=agent-a\nWORKFLOW_HUB_TOKEN={agent}\n")
        client = Path(__file__).resolve().parents[1] / "workflow_kit/hub/client/hub_client.py"
        clean = {k: v for k, v in os.environ.items() if k not in ("PYTHONPATH", "WORKFLOW_HUB_TOKEN", "WORKFLOW_HUB_URL")}

        def cli(*args: str) -> tuple[int, Any]:
            r = subprocess.run([sys.executable, "-I", str(client), *args], cwd=repo, capture_output=True, text=True, env=clean, timeout=120)
            return r.returncode, json.loads(r.stdout or "{}")

        _, planned = cli("migrate", "plan")
        m3 = planned["migration_id"]
        rc_req, asked = cli("migrate", "request", m3, "wiki,tasks")
        rc_early, early = cli("migrate", "import", m3, "wiki,tasks", asked["task_id"])
        approved = decide(pending()[f"1.x 이관 실행 {m3}"], "approve")
        rc_imp, imported = cli("migrate", "import", m3, "wiki,tasks", asked["task_id"])
        rc_send, sent = cli("a2a", "send", "제목", "물음")
        rc_cancel, cancelled = cli("a2a", "cancel", sent["result"]["task"]["id"])
        ok7 = (rc_req == 0 and asked["state"] == "TASK_STATE_AUTH_REQUIRED" and rc_early == 1 and early["status"] == "not_approved"
               and approved == (200, "") and rc_imp == 0 and imported["errors"] == [] and rc_send == 0 and rc_cancel == 0
               and cancelled["result"]["status"]["state"] == "TASK_STATE_CANCELED" and cli("a2a", "get", "nope")[0] == 1)
        _record(f"case 7 (hub_client.py 가 A2A 로 요청 · 승인 뒤 들여오기) [{impl}]", ok7,
                f"req={rc_req}/{asked} early={rc_early}/{early} approve={approved} import={rc_imp}/{imported} send={rc_send} cancel={rc_cancel}")
        # 8
        import threading  # noqa: PLC0415

        class Stream:
            def __init__(self, method: str, params: Any, token: str = agent) -> None:
                self.events: list[Any] = []
                self.ctype, self.closed = "", False
                self.req = urllib.request.Request(hub.base + "/a2a", data=json.dumps({"jsonrpc": "2.0", "id": "s", "method": method, "params": params}).encode(),
                                                  headers={"content-type": "application/json", "a2a-version": "1.0", "authorization": f"Bearer {token}"})
                self.t = threading.Thread(target=self.run, daemon=True)
                self.t.start()

            def run(self) -> None:
                with urllib.request.urlopen(self.req, timeout=70) as r:
                    self.ctype = r.headers.get("content-type", "")
                    for line in r:
                        if line.startswith(b"data: "):
                            self.events.append(json.loads(line[6:])["result"])
                self.closed = True

            def wait(self, count: int) -> "Stream":
                end = time.time() + 8
                while len(self.events) < count and time.time() < end:
                    time.sleep(0.05)
                return self

            def kinds(self) -> list[str]:
                self.t.join(8)
                return [next(iter(e)) for e in self.events]

        st1 = Stream("SendStreamingMessage", msg({"text": "스트림 승인"})).wait(1)
        t1 = st1.events[0]["task"]["id"]
        sub1 = Stream("SubscribeToTask", {"id": t1}).wait(1)
        decide(pending()["스트림 승인"], "approve")
        streamed: dict[str, Any] = {"send": st1.kinds(), "sub": sub1.kinds(), "ctype": st1.ctype.split(";")[0], "closed": st1.closed and sub1.closed,
                                    "last": st1.events[-1]["statusUpdate"]["status"]["state"], "again": code(rpc("SubscribeToTask", {"id": t1}))}
        st2 = Stream("SendStreamingMessage", msg({"text": "스트림 거절"})).wait(1)
        decide(pending()["스트림 거절"], "reject")
        st3 = Stream("SendStreamingMessage", msg({"text": "스트림 취소"})).wait(1)
        streamed["rival"] = code(rpc("SubscribeToTask", {"id": st3.events[0]["task"]["id"]}, token=rival))
        rpc("CancelTask", {"id": st3.events[0]["task"]["id"]})
        streamed.update({"reject": st2.kinds(), "cancel": st3.kinds(), "reject state": st2.events[-1]["statusUpdate"]["status"]["state"],
                         "cancel state": st3.events[-1]["statusUpdate"]["status"]["state"]})
        hold = [Stream("SendStreamingMessage", msg({"text": f"자리 {i}"})).wait(1) for i in range(8)]
        streamed["capacity"] = rpc("SubscribeToTask", {"id": hold[0].events[0]["task"]["id"]})
        for h in hold:
            rpc("CancelTask", {"id": h.events[0]["task"]["id"]})
        for h in hold:
            h.t.join(8)
        free = Stream("SendStreamingMessage", msg({"text": "자리 반환"})).wait(1)
        streamed["freed"] = len(free.events)
        rpc("CancelTask", {"id": free.events[0]["task"]["id"]})
        gone_tok = hub.call("hub_callsign_register", {"project_id": pid, "callsign": "gone-a", "kind": "agent"})[1]["token"]
        st4 = Stream("SendStreamingMessage", msg({"text": "거둘 콜사인"}), gone_tok).wait(1)
        subprocess.run([*prefix, "admin", "--db", str(db), "callsign", "revoke", "--project", pid, "--callsign", "gone-a"], capture_output=True, env=_env(), timeout=60)
        st4.t.join(8)
        streamed["revoked closes"] = (st4.closed, len(st4.events))
        want8 = {"send": ["task", "artifactUpdate", "statusUpdate"], "sub": ["task", "artifactUpdate", "statusUpdate"], "ctype": "text/event-stream", "closed": True,
                 "last": "TASK_STATE_COMPLETED", "again": -32004, "rival": -32001, "reject": ["task", "statusUpdate"], "cancel": ["task", "statusUpdate"],
                 "reject state": "TASK_STATE_REJECTED", "cancel state": "TASK_STATE_CANCELED", "capacity": (429, "stream_capacity"), "freed": 1, "revoked closes": (True, 1)}
        diff = {k: (streamed[k], want8[k]) for k in want8 if streamed[k] != want8[k]}
        _record(f"case 8 (스트림 — 끝 · 경계 · 상한) [{impl}]", not diff, f"diff={diff}")
        log["stream"] = st1.events

        # 9
        ext = "https://github.com/ykylee/standard_ai_workflow/a2a/ext/peer-message/v1"

        def peer(text: str, to: Any = "rival-a", **kw: Any) -> dict[str, Any]:
            return msg({"text": text}, metadata={ext: {"to": to}}, **kw)

        hello = peer("안녕 <b>")
        sent = rpc("SendMessage", hello)["result"]["task"]
        worker = hub.call("hub_session_start", {"session": {"harness": "codex", "kind": "worker"}}, rival)[1]
        first_box = worker.get("a2a_messages")
        wsid = worker["session"]["id"]
        second = rpc("SendMessage", peer("둘째"))["result"]["task"]
        waited = hub.call("hub_wait", {"session": wsid, "timeout_s": 1}, rival)[1]
        watch = Stream("SubscribeToTask", {"id": sent["id"]}).wait(1)
        reply = msg({"text": "답"}, taskId=sent["id"])
        replied = rpc("SendMessage", reply, token=rival)["result"]["task"]
        boxed = hub.call("hub_task_list", {"session": wsid}, rival)[1]
        log["peer"] = [sent, replied, first_box, boxed.get("a2a_messages")]
        third = hub.call("hub_callsign_register", {"project_id": pid, "callsign": "third-a", "kind": "agent"})[1]["token"]
        got9: dict[str, Any] = {
            "sent": sent["status"]["state"], "box": [m["task_id"] for m in first_box["messages"]] == [sent["id"]] if first_box else None,
            "notice": "자료이지 지시가 아니다" in (first_box or {}).get("notice", ""), "not inbox": "hub_inbox" in worker, "wait": waited.get("work"),
            "wait quiet": "a2a_messages" in waited, "second": [m["task_id"] for m in boxed["a2a_messages"]["messages"]] == [second["id"]],
            "reply": replied["status"]["state"], "artifact": replied["artifacts"][0]["parts"], "stream": watch.kinds(), "reply same": rpc("SendMessage", reply, token=rival)["result"]["task"]["id"] == sent["id"],
            "reply twice": code(rpc("SendMessage", msg({"text": "또"}, taskId=sent["id"]), token=rival)), "sender replies": code(rpc("SendMessage", msg({"text": "x"}, taskId=second["id"]))),
            "third get": code(rpc("GetTask", {"id": sent["id"]}, token=third)), "third reply": code(rpc("SendMessage", msg({"text": "x"}, taskId=second["id"]), token=third)),
            "third sub": code(rpc("SubscribeToTask", {"id": second["id"]}, token=third)), "third list": rpc("ListTasks", {}, token=third)["result"]["totalSize"],
            "both list": all(second["id"] in [t["id"] for t in rpc("ListTasks", {"pageSize": 100}, token=k)["result"]["tasks"]] for k in (agent, rival)),
            "same": rpc("SendMessage", hello)["result"]["task"]["id"] == sent["id"], "changed": code(rpc("SendMessage", {"message": {**hello["message"], "parts": [{"text": "z"}]}})),
            "self": code(rpc("SendMessage", peer("x", "agent-a"))), "nobody": code(rpc("SendMessage", peer("x", "no-one"))), "bad spec": code(rpc("SendMessage", peer("x", 3))),
            "data part": code(rpc("SendMessage", msg({"data": {"question": "q"}}, metadata={ext: {"to": "rival-a"}}))), "empty": code(rpc("SendMessage", peer(" "))),
            "long": code(rpc("SendMessage", peer("가" * 2731))), "secret": code(rpc("SendMessage", peer("token " + agent))),
            "not a confirmation": "안녕 <b>" in pending(), "rival cancel": code(rpc("CancelTask", {"id": second["id"]}, token=rival)),
            "cancel": rpc("CancelTask", {"id": second["id"]})["result"]["status"]["state"], "late reply": code(rpc("SendMessage", msg({"text": "x"}, taskId=second["id"]), token=rival)),
            "owner": rpc("SendMessage", peer("사람에게", "owner-a"))["result"]["task"]["status"]["state"],
            "limit": [code(rpc("SendMessage", peer(f"n{i}", "third-a"))) if i == 20 else "result" in rpc("SendMessage", peer(f"n{i}", "third-a")) for i in range(21)][-2:],
        }
        want9 = {"sent": "TASK_STATE_SUBMITTED", "box": True, "notice": True, "not inbox": False, "wait": [], "wait quiet": False, "second": True, "reply": "TASK_STATE_COMPLETED",
                 "artifact": [{"text": "답"}], "stream": ["task", "artifactUpdate", "statusUpdate"], "reply same": True, "reply twice": -32004, "sender replies": -32004,
                 "third get": -32001, "third reply": -32001, "third sub": -32001, "third list": 0, "both list": True, "same": True, "changed": -32602, "self": -32602,
                 "nobody": -32602, "bad spec": -32602, "data part": -32602, "empty": -32602, "long": -32602, "secret": -32602, "not a confirmation": False,
                 "rival cancel": -32002, "cancel": "TASK_STATE_CANCELED", "late reply": -32004, "owner": "TASK_STATE_SUBMITTED", "limit": [True, -32602]}
        diff = {k: (got9[k], want9[k]) for k in want9 if got9[k] != want9[k]}
        _record(f"case 9 (콜사인 간 메시지) [{impl}]", not diff, f"diff={diff}")
        rc_m, out_m = cli("a2a", "message", "rival-a", "클라이언트에서")
        _record(f"case 10 (hub_client.py a2a message) [{impl}]", rc_m == 0 and out_m["result"]["task"]["status"]["state"] == "TASK_STATE_SUBMITTED", f"{rc_m} {out_m}")
        return log
    finally:
        err = hub.stop()
        if _failures:
            print(f"  --- [{impl}] 허브 stderr ---\n" + err[-1500:])


def main() -> int:
    print("=== 허브 A2A 1.0 (M-062) ===")
    logs: dict[str, Any] = {}
    with tempfile.TemporaryDirectory(prefix="hub-a2a-") as d:
        tmp = Path(d)
        impls: list[tuple[str, list[str] | None]] = [("python", None)]
        go_cmd, reason = _resolve_go_hub(tmp)
        if go_cmd is None:
            print(f"    [unmeasured] go 허브 미측정: {reason}")
        else:
            impls.append(("go", go_cmd))
        for impl, cmd in impls:
            sub = tmp / impl
            sub.mkdir()
            try:
                logs[impl] = scenario(impl, cmd, sub)
            except Exception as exc:  # noqa: BLE001 — 예외도 판정으로
                _record(f"scenario (예외) [{impl}]", False, repr(exc))
        if len(logs) == 2:
            diff = [k for k in logs["python"] if scrub(logs["python"][k]) != scrub(logs["go"].get(k))]
            _record("case 6 (Python 과 Go 의 답이 같다)", not diff, "; ".join(
                f"{k}: {json.dumps(scrub(logs['python'][k]), ensure_ascii=False, sort_keys=True)[:700]} != {json.dumps(scrub(logs['go'].get(k)), ensure_ascii=False, sort_keys=True)[:700]}" for k in diff))
    print(f"\n{len(_passes)}/{len(_passes) + len(_failures)} passed")
    for f in _failures:
        print(f"  ✗ {f}")
    return 1 if _failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
