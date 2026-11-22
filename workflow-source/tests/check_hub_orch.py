#!/usr/bin/env python3
"""허브 오케스트레이션 구현 1 (M-044) — 세션 · 받은편지함 편승 · 대기 · 수신 확인을 잰다.

계약 정본: ``core/hub_orchestration_spec.md`` §3 · §4 · §5 · §6.1 · §6.2 · §7.1 (ADR-034).
시간 판정(60초 재전달 · 10분 미확인 · 15분 unknown)은 **프로세스 안에서 시각을 넘겨** 재고 (허브 함수는 시계를 읽지 않는다),
대기 도구의 async 경로 · MCP 경로는 **실제 허브 프로세스**로 잰다 (check_hub_core 의 ``Hub``).

1. 판 11 — 새 DB 판 11 · 판 10 DB 이관(이전 사본 · 2.0 행 그대로) · 열린 배정은 task 하나에 하나 (부분 유일 색인)
2. 세션 — 등록 · 같은 하네스 세션 ID 로 이어 붙임 · resume · 남의 세션 403 · 꼴 틀림 400 · 끝난 세션 410
3. 상태 5값 — idle · working(열린 배정) · waiting · unknown(신호 15분 초과, idle 로 안 셈) · ended
4. 편승 — 실을 것 없으면 칸 없음(2.0 응답과 같음) · 3건 · remaining · 8KB · 콜사인 주소는 session 없는 호출에도 · 세션 시작 첫 응답
5. 실림 ≠ 소비 — 60초 안 재전달 없음 · 60초 뒤 ack 안 된 것만 다시(redelivery 표시) · 10분 unacknowledged · 늦은 ack 409
6. 수신 확인 — 같은 결정 멱등 · 다른 결정 409 · 남의 메시지 403 · decline
7. 대기 권한 — interactive 는 wait_disabled · 에이전트의 allow_wait 켜기 403 · 승인 human 은 켬 · 연속 70회 wait_budget
8. 2.0 호환 — 2.0 도구의 필수 인자 그대로 · 선택 인자 session 만 더함 · 모르는 인자는 여전히 거절
9. 대기 async (실제 프로세스, HTTP) — 대기 중 투입 → 곧 응답 · 상한 빈 응답 · 동시 대기 45개(> 스레드 풀 40) 동안 다른 도구 즉시 응답
10. 대기 MCP 경로 (실제 프로세스) — MCP 로 부른 hub_wait 가 메시지를 받는다
"""

from __future__ import annotations

CHECK_TIMEOUT_S = 240

WATCHES = (
    "workflow-source/workflow_kit/*",
    "workflow-source/pyproject.toml",
    "workflow-source/tests/check_hub_core.py",
)

import json
import sqlite3
import sys
import tempfile
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from check_hub_core import Hub, _mcp_session  # noqa: E402
from workflow_kit.hub import db as hubdb  # noqa: E402
from workflow_kit.hub import tools as hubtools  # noqa: E402
from workflow_kit.hub.errors import HubError  # noqa: E402
from workflow_kit.hub.orchestration import WAIT_BUDGET, Orchestration  # noqa: E402
from workflow_kit.hub.store import Ctx, Store  # noqa: E402

_failures: list[str] = []
_passes: list[str] = []
T0 = datetime(2026, 11, 22, 3, 0, 0, tzinfo=timezone.utc)


def _record(case: str, ok: bool, detail: str = "") -> None:
    (_passes if ok else _failures).append(case if ok else f"{case}: {detail}")
    print(f"  {case}: {'PASS' if ok else 'FAIL'}{(' — ' + detail) if detail and not ok else ''}")


class Env:
    """프로세스 안 허브 — 시각을 넘겨 부른다."""

    def __init__(self, db: Path) -> None:
        hubdb.open_db(db, now=T0)
        self.store = Store(db)
        reg = self.call("hub_project_register", {"remote_url": "git@github.com:acme/orch.git", "display_name": "Orch",
                                                 "callsign": "owner-h", "kind": "human"}, None)
        self.pid = reg["project_id"]
        self.tok = {"owner-h": reg["token"]}
        for cs, kind in (("agent-a", "agent"), ("agent-b", "agent")):
            self.tok[cs] = self.call("hub_callsign_register", {"project_id": self.pid, "callsign": cs, "kind": kind},
                                     None)["token"]

    def ctx(self, who: str | None, at: datetime = T0) -> Ctx:
        principal = self.store.authenticate(self.tok[who]) if who else None
        return Ctx(now=at, via="http", principal=principal)

    def call(self, name: str, args: dict[str, Any], who: str | None, at: datetime = T0) -> dict[str, Any]:
        return hubtools.call(self.store, name, args, self.ctx(who, at))

    def err(self, name: str, args: dict[str, Any], who: str | None, at: datetime = T0) -> str:
        try:
            self.call(name, args, who, at)
        except HubError as e:
            return e.code
        return "no-error"

    def session(self, who: str, at: datetime = T0, **spec: Any) -> str:
        r = self.call("hub_session_start", {"session": {"harness": "claude-code", **spec}}, who, at)
        return str(r["session"]["id"])

    def send(self, to_kind: str, to_id: str, body: Any, at: datetime = T0, kind: str = "note") -> str:
        orch = Orchestration(self.store)
        with self.store.write() as conn:
            return orch.enqueue(conn, self.ctx("owner-h", at), self.pid, to_kind=to_kind, to_id=to_id, kind=kind,
                                body=body, from_callsign="owner-h", from_orchestrator=True)


def case_1(tmp: Path) -> None:
    fresh = tmp / "fresh.db"
    hubdb.open_db(fresh, now=T0)
    with hubdb.connect(fresh) as c:
        v = hubdb.schema_version(c)
        tables = {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    want = {"session", "inbox_message", "assignment", "orchestrator_lease", "session_request", "relay_host", "orch_counter"}
    old = tmp / "v10.db"
    for n in range(1, 11):
        hubdb._apply(old, n, T0)
    with hubdb.connect(old) as c:
        c.execute("INSERT INTO project (id, display_name, owner_callsign, created_at) VALUES ('P-1', 'x', 'o', 't')")
        before = [tuple(r) for r in c.execute("SELECT * FROM project")]
    copies = hubdb.open_db(old, now=T0)
    with hubdb.connect(old) as c:
        v_old = hubdb.schema_version(c)
        after = [tuple(r) for r in c.execute("SELECT * FROM project")]
        c.execute("INSERT INTO assignment (project_id, task_id, session_id, callsign, message_id, state, offered_at) "
                  "VALUES ('P-1', 'T1', 'S1', 'a', 'M1', 'returned', 't')")
        c.execute("INSERT INTO assignment (project_id, task_id, session_id, callsign, message_id, state, offered_at) "
                  "VALUES ('P-1', 'T1', 'S2', 'a', 'M2', 'offered', 't')")
        try:
            c.execute("INSERT INTO assignment (project_id, task_id, session_id, callsign, message_id, state, offered_at) "
                      "VALUES ('P-1', 'T1', 'S3', 'a', 'M3', 'accepted', 't')")
            dup_blocked = False
        except sqlite3.IntegrityError:
            dup_blocked = True
    ok = v == 11 and want <= tables and v_old == 11 and before == after and len(copies) == 1 \
        and copies[0].name.startswith("v10.db.pre-v11-") and dup_blocked
    _record("case 1 (판 11 · 이관 · 열린 배정 하나)", ok,
            f"v={v} missing={want - tables} v_old={v_old} same={before == after} copies={copies} dup_blocked={dup_blocked}")


def case_2_3(e: Env) -> None:
    s1 = e.session("agent-a", harness_session_id="h-1", kind="worker")
    s1b = e.session("agent-a", harness_session_id="h-1", kind="worker")
    s2 = e.session("agent-a")
    resumed = e.call("hub_session_start", {"session": {"harness": "claude-code", "resume": s2}}, "agent-a")["session"]
    not_yours = e.err("hub_task_list", {"session": s1}, "agent-b")
    bad = e.err("hub_task_list", {"session": "S-nope"}, "agent-a")
    with e.store.write() as c:
        c.execute("UPDATE session SET status = 'ended' WHERE id = ?", (s2,))
    ended = e.err("hub_task_list", {"session": s2}, "agent-a")
    _record("case 2 (세션 등록 · 이어 붙임 · resume · 403 · 400 · 410)",
            s1 == s1b and s2 != s1 and resumed["id"] == s2 and resumed["resumed"] is True
            and not_yours == "session_not_yours" and bad == "invalid_field" and ended == "session_ended",
            f"s1={s1} s1b={s1b} s2={s2} resumed={resumed.get('id')} {not_yours} {bad} {ended}")

    s3 = e.session("agent-b", kind="worker")
    st = {}
    st["idle"] = e.call("hub_session_list", {}, "agent-b")
    with e.store.write() as c:
        c.execute("INSERT INTO assignment (project_id, task_id, session_id, callsign, message_id, state, offered_at) "
                  "VALUES (?, 'T-x', ?, 'agent-b', 'M', 'accepted', ?)", (e.pid, s3, T0.isoformat()))
    working = e.call("hub_session_list", {"callsign": "agent-b"}, "agent-b")["sessions"][0]["status"]
    Orchestration(e.store).wait_poll(e.ctx("agent-b"), s3, first=True)
    waiting = e.call("hub_session_list", {"callsign": "agent-b"}, "agent-b")["sessions"][0]["status"]
    later = e.call("hub_session_list", {}, "agent-a", T0 + timedelta(minutes=16))
    by_id = {s["id"]: s["status"] for s in later["sessions"]}
    ok = (working == "working" and waiting == "waiting" and by_id.get(s1) == "unknown" and by_id.get(s2) == "ended"
          and later["unknown"] >= 1 and "idle" not in {by_id.get(s1)}
          and {s["status"] for s in st["idle"]["sessions"] if s["id"] == s1} == {"idle"})
    _record("case 3 (상태 5값 · unknown 은 idle 로 안 셈)", ok, f"working={working} waiting={waiting} later={by_id}")


def case_4_5_6(e: Env) -> None:
    s = e.session("agent-a", harness_session_id="pig", kind="worker")
    plain = e.call("hub_task_list", {}, "agent-a")
    with_sess = e.call("hub_task_list", {"session": s}, "agent-a")
    no_field = "hub_inbox" not in with_sess and plain == with_sess
    ids = [e.send("session", s, {"n": i}) for i in range(5)]
    r1 = e.call("hub_task_list", {"session": s}, "agent-a")
    r2 = e.call("hub_task_list", {"session": s}, "agent-a")
    r3 = e.call("hub_task_list", {"session": s}, "agent-a", T0 + timedelta(seconds=30))
    got1 = [m["id"] for m in r1.get("hub_inbox", {}).get("messages", [])]
    got2 = [m["id"] for m in r2.get("hub_inbox", {}).get("messages", [])]
    ok4a = got1 == ids[:3] and r1["hub_inbox"]["remaining"] == 2 and got2 == ids[3:] and "hub_inbox" not in r3
    # 5 — 실림 ≠ 소비. ids[0] 만 확인하고, 61초 뒤 나머지 넷이 다시 실린다.
    e.call("hub_inbox_ack", {"session": s, "message_id": ids[0], "decision": "accept"}, "agent-a",
           T0 + timedelta(seconds=40))
    at61 = T0 + timedelta(seconds=61)
    again = e.call("hub_task_list", {"session": s}, "agent-a", at61).get("hub_inbox", {})
    again_ids = [m["id"] for m in again.get("messages", [])]
    flagged = all(m.get("redelivery") for m in again.get("messages", []))
    at11 = T0 + timedelta(minutes=11)
    e.call("hub_task_list", {"session": s}, "agent-a", at11)
    states = {r["id"]: r["state"] for r in e.call("hub_inbox_list", {"session": s}, "agent-a", at11)["messages"]}
    late = e.err("hub_inbox_ack", {"session": s, "message_id": ids[1], "decision": "accept"}, "agent-a", at11)
    ok5 = (ids[0] not in again_ids and again_ids == ids[1:4] and flagged and states[ids[0]] == "acked"
           and all(states[i] == "unacknowledged" for i in ids[1:]) and late == "ack_too_late")
    _record("case 5 (실림 ≠ 소비 — 60초 재전달 · ack 된 것 제외 · 10분 unacknowledged · 늦은 ack)", ok5,
            f"again={again_ids} flagged={flagged} states={states} late={late}")

    big = [e.send("session", s, {"pad": "x" * 3500}, T0 + timedelta(minutes=30)) for _ in range(3)]
    rb = e.call("hub_task_list", {"session": s}, "agent-a", T0 + timedelta(minutes=30))
    ok4b = [m["id"] for m in rb["hub_inbox"]["messages"]] == big[:2]
    cs_msg = e.send("callsign", "agent-a", {"to": "callsign"}, T0 + timedelta(minutes=40))
    rc = e.call("hub_whoami", {}, "agent-a", T0 + timedelta(minutes=40))
    ok4c = [m["id"] for m in rc.get("hub_inbox", {}).get("messages", [])] == [cs_msg]
    pending = e.send("callsign", "agent-b", {"hello": 1}, T0 + timedelta(minutes=41))
    first = e.call("hub_session_start", {"session": {"harness": "codex", "kind": "worker"}}, "agent-b",
                   T0 + timedelta(minutes=41))
    ok4d = [m["id"] for m in first.get("hub_inbox", {}).get("messages", [])] == [pending]
    _record("case 4 (편승 — 칸 없음 · 3건 · remaining · 8KB · 콜사인 주소 · 세션 시작 첫 응답)",
            no_field and ok4a and ok4b and ok4c and ok4d,
            f"no_field={no_field} r1={got1} r2={got2} r3={'hub_inbox' in r3} big={ok4b} cs={ok4c} first={ok4d}")

    # 6 — 수신 확인
    at45 = T0 + timedelta(minutes=45)
    s_b = e.session("agent-b", at45, kind="worker")
    m = e.send("session", s, {"x": 1}, at45)
    other = e.send("session", s_b, {"y": 1}, at45)
    a1 = e.call("hub_inbox_ack", {"session": s, "message_id": m, "decision": "decline", "reason": "범위 밖"},
                "agent-a", at45)
    a2 = e.call("hub_inbox_ack", {"session": s, "message_id": m, "decision": "decline"}, "agent-a", at45)
    a3 = e.err("hub_inbox_ack", {"session": s, "message_id": m, "decision": "accept"}, "agent-a", at45)
    a4 = e.err("hub_inbox_ack", {"session": s, "message_id": other, "decision": "seen"}, "agent-a", at45)
    _record("case 6 (수신 확인 — 멱등 · 다른 결정 409 · 남의 메시지 403 · decline)",
            a1["state"] == "declined" and a2.get("unchanged") is True and a3 == "already_acked"
            and a4 == "message_not_yours", f"{a1} {a2} {a3} {a4}")


def case_7(e: Env) -> None:
    human = e.session("owner-h")
    agent_i = e.session("agent-a", harness_session_id="i-7")
    disabled = e.err("hub_wait", {"session": agent_i}, "agent-a")
    agent_on = e.err("hub_session_update", {"session": agent_i, "allow_wait": True}, "agent-a")
    human_on = e.call("hub_session_update", {"session": human, "allow_wait": True}, "owner-h")["session"]["allow_wait"]
    w = e.session("agent-a", harness_session_id="w-7", kind="worker")
    empty = e.call("hub_wait", {"session": w}, "agent-a")
    with e.store.write() as c:
        c.execute("UPDATE session SET idle_waits = ? WHERE id = ?", (WAIT_BUDGET, w))
    budget = e.err("hub_wait", {"session": w}, "agent-a")
    _record("case 7 (대기 권한 — wait_disabled · 에이전트 켜기 403 · human 켬 · 빈 응답 · wait_budget)",
            disabled == "wait_disabled" and agent_on == "forbidden" and human_on is True
            and empty.get("call_again") is True and budget == "wait_budget",
            f"{disabled} {agent_on} {human_on} {empty} {budget}")


def case_8(e: Env) -> None:
    spec = hubtools.TOOLS["hub_task_progress"]
    sch = spec.schema()
    bad = e.err("hub_task_list", {"nope": 1}, "agent-a")
    boot = hubtools.TOOLS["hub_project_lookup"].schema()
    ok = (sch["required"] == ["id", "note"] and "session" in sch["properties"] and bad == "unknown_field"
          and "session" not in boot["properties"])
    _record("case 8 (2.0 호환 — 필수 인자 그대로 · session 선택 인자 · 모르는 인자 거절 · bootstrap 묶음엔 없음)", ok,
            f"required={sch['required']} bad={bad} boot={sorted(boot['properties'])}")


def _post(hub: Hub, name: str, args: dict[str, Any], token: str, timeout: float = 70) -> tuple[int, dict[str, Any]]:
    import urllib.error
    import urllib.request
    req = urllib.request.Request(f"{hub.base}/v1/tools/{name}", data=json.dumps(args).encode(), method="POST",
                                 headers={"content-type": "application/json", "authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as ex:
        return ex.code, json.loads(ex.read())


def case_9_10(tmp: Path) -> None:
    db = tmp / "live.db"
    hub = Hub(db)
    try:
        _, reg = _post(hub, "hub_project_register", {"remote_url": "git@github.com:acme/live.git", "display_name": "L",
                                                     "callsign": "agent-w", "kind": "agent"}, "")[0:2]
        tok, pid = reg["token"], reg["project_id"]
        _, st = _post(hub, "hub_session_start", {"session": {"harness": "codex", "kind": "worker"}}, tok)
        sid = st["session"]["id"]
        store = Store(db)
        orch = Orchestration(store)

        def push(body: Any) -> None:
            now = datetime.now(timezone.utc)
            ctx = Ctx(now=now, via="http", principal=store.authenticate(tok))
            with store.write() as conn:
                orch.enqueue(conn, ctx, pid, to_kind="session", to_id=sid, kind="note", body=body,
                             from_callsign="agent-w")

        out: dict[str, Any] = {}

        def waiter() -> None:
            t = time.monotonic()
            out["r"] = _post(hub, "hub_wait", {"session": sid, "timeout_s": 30}, tok)
            out["dt"] = time.monotonic() - t

        th = threading.Thread(target=waiter)
        th.start()
        time.sleep(2.0)
        push({"wake": 1})
        th.join(40)
        code, body = out.get("r", (0, {}))
        woke = code == 200 and [m["body"] for m in body.get("work", [])] == [{"wake": 1}] and 1.5 < out.get("dt", 99) < 5
        t = time.monotonic()
        code2, empty = _post(hub, "hub_wait", {"session": sid, "timeout_s": 2}, tok)
        dt2 = time.monotonic() - t
        timed = code2 == 200 and empty.get("call_again") is True and 1.5 < dt2 < 5

        # 스레드 풀(40)보다 많은 대기 45개 동안 다른 도구가 바로 답하는가 — 대기가 스레드를 쥐면 여기서 멈춘다.
        sids = []
        for i in range(45):
            sids.append(_post(hub, "hub_session_start", {"session": {"harness": "codex", "kind": "worker",
                                                                     "harness_session_id": f"m{i}"}}, tok)[1]["session"]["id"])
        threads = [threading.Thread(target=_post, args=(hub, "hub_wait", {"session": x, "timeout_s": 6}, tok))
                   for x in sids]
        for x in threads:
            x.start()
        time.sleep(1.5)
        t = time.monotonic()
        code3, who = _post(hub, "hub_whoami", {}, tok, timeout=10)
        dt3 = time.monotonic() - t
        for x in threads:
            x.join(20)
        free = code3 == 200 and dt3 < 1.0
        _record("case 9 (대기 async — 투입 뒤 깸 · 상한 빈 응답 · 대기 45개 중 다른 도구 즉시)", woke and timed and free,
                f"woke={code} dt={out.get('dt')} body={str(body)[:160]} timed={code2} dt2={dt2:.1f} whoami={code3} dt3={dt3:.2f}")

        # 대기를 시작한 **뒤에** 넣는다 — 미리 넣어 두면 대기 루프가 없어도 통과한다.
        timer = threading.Timer(1.5, push, args=({"mcp": 1},))
        timer.start()
        _names, results = _mcp_session(hub.base, tok, [("hub_wait", {"session": sid, "timeout_s": 8})])
        timer.join()
        is_error, structured = results[0]
        ok10 = not is_error and [m["body"] for m in (structured or {}).get("work", [])] == [{"mcp": 1}]
        _record("case 10 (대기 MCP 경로)", ok10, f"error={is_error} structured={str(structured)[:200]}")
    finally:
        err = hub.stop()
        if _failures:
            print("  --- 허브 stderr ---\n" + err[-1500:])


def main() -> int:
    print("=== 허브 오케스트레이션 구현 1 (M-044) ===")
    with tempfile.TemporaryDirectory(prefix="huborch-") as d:
        tmp = Path(d)
        try:
            case_1(tmp)
        except Exception as exc:  # noqa: BLE001 — 예외도 판정으로 (판정 줄 없이 죽지 않게)
            _record("case 1 (예외)", False, repr(exc))
        e = Env(tmp / "orch.db")
        for name, fn in (("case 2·3", case_2_3), ("case 4·5·6", case_4_5_6), ("case 7", case_7), ("case 8", case_8)):
            try:
                fn(e)
            except Exception as exc:  # noqa: BLE001 — 예외도 판정으로
                _record(f"{name} (예외)", False, repr(exc))
        try:
            case_9_10(tmp)
        except Exception as exc:  # noqa: BLE001
            _record("case 9·10 (예외)", False, repr(exc))
    total = len(_passes) + len(_failures)
    print(f"\n{len(_passes)}/{total} passed")
    if _failures:
        for f in _failures:
            print(f"  ✗ {f}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
