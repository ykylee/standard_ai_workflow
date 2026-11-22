#!/usr/bin/env python3
"""허브 오케스트레이션 구현 2 (M-045) — 오케스트레이터 lease · 배정 상태 기계 · 보고 · 정지 · 금지 · 진입 규칙.

계약 정본: ``core/hub_orchestration_spec.md`` §5 · §7.2 · §7.4 · §8 · §11 (ADR-034). 시각은 프로세스 안에서 넘긴다
(``check_hub_orch`` 의 ``Env``).

1. lease — owner 아닌 지정 403 · 지정 · 둘째 지정 409 · 오케스트레이터 호출이 lease 를 늘림 · 끊기면 만료 + owner 알림 · 인계 · 자기 해제
2. 배정 — 오케스트레이터 아님 403 · 배정 = offered + assignment 메시지 · 같은 task 409 · 자기 배정 409 · 남이 맡은 task 409 · 끝난 세션 410
3. 수락 = 맡기 (DO6) — accept 하면 task 맡은 이 · in_progress · 배정 accepted, 그 사이 남이 맡았으면 409 이고 메시지 · 배정 그대로
4. 거절 · 미확인 — decline → returned + 오케스트레이터 앞 이유 · 10분 무확인 → returned (unacknowledged)
5. 보고 — 수락 전 409 · 보고 → reported + 오케스트레이터 앞 report · task 는 done 이 아님
6. 회수 · 세션 끝 · 24시간 — recall → returned + 받은 세션에 release · hub_session_end(session) → ended + returned · 수락 뒤 24시간 진척 없음 → returned
7. 정지 — 배정 · note 423 · release 는 됨 · 편승은 release 만 · 대기 중 세션에 release · 풀면 다시
8. 금지 — 에이전트 오케스트레이터가 지정 · 인계 · 정지 · 콜사인 승인 403 (사람의 권한을 갖지 않는다)
9. 진입 규칙 — 렌더한 진입 영역에 받은편지함 절 (session 인자 · hub_inbox_ack · decline 규칙 · hub_report · hub_wait)
"""

from __future__ import annotations

CHECK_TIMEOUT_S = 120

WATCHES = (
    "workflow-source/workflow_kit/*",
    "workflow-source/pyproject.toml",
    "workflow-source/core/hub_workflow_standard.md",
    "workflow-source/tests/check_hub_orch.py",
    "workflow-source/tests/check_hub_core.py",
)

import sys
import tempfile
from datetime import timedelta
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from check_hub_orch import T0, Env  # noqa: E402
from workflow_kit.hub.orchestration import Orchestration  # noqa: E402

_failures: list[str] = []
_passes: list[str] = []


def _record(case: str, ok: bool, detail: str = "") -> None:
    (_passes if ok else _failures).append(case if ok else f"{case}: {detail}")
    print(f"  {case}: {'PASS' if ok else 'FAIL'}{(' — ' + detail) if detail and not ok else ''}")


def _inbox(e: Env, who: str, session: str | None, at: Any) -> list[dict[str, Any]]:
    return e.call("hub_inbox_list", {"session": session} if session else {}, who, at)["messages"]


def _task(e: Env, title: str, who: str = "owner-h") -> str:
    return str(e.call("hub_task_create", {"title": title, "status": "planned"}, who)["task"]["id"])


def _assignment(e: Env, task_id: str) -> dict[str, Any]:
    with e.store.read() as c:
        rows = c.execute("SELECT * FROM assignment WHERE project_id = ? AND task_id = ? ORDER BY rowid DESC",
                         (e.pid, task_id)).fetchall()
    return dict(rows[0]) if rows else {}


def run(e: Env) -> None:
    orch = e.session("agent-a", harness_session_id="orch", kind="interactive")
    w1 = e.session("agent-b", harness_session_id="w1", kind="worker")
    w2 = e.session("agent-a", harness_session_id="w2", kind="worker")

    # 1 lease
    not_owner = e.err("hub_orch_declare", {"session": orch}, "agent-a")
    dec = e.call("hub_orch_declare", {"session": orch}, "owner-h")
    again = e.err("hub_orch_declare", {"session": w1}, "owner-h")
    e.call("hub_task_list", {"session": orch}, "agent-a", T0 + timedelta(minutes=10))  # 갱신
    alive = e.call("hub_session_list", {}, "owner-h", T0 + timedelta(minutes=20))["orchestrator"]
    gone = e.call("hub_session_list", {}, "owner-h", T0 + timedelta(minutes=40))["orchestrator"]
    owner_note = [m for m in _inbox(e, "owner-h", None, T0 + timedelta(minutes=40))
                  if m["body"].get("event") == "orchestrator_lease_expired"]
    at = T0 + timedelta(minutes=41)
    e.call("hub_orch_declare", {"session": w1}, "owner-h", at)
    tr = e.call("hub_orch_transfer", {"session": orch}, "owner-h", at)
    rel = e.call("hub_orch_release", {"session": orch}, "agent-a", at)
    after_rel = e.call("hub_session_list", {}, "owner-h", at)["orchestrator"]
    _record("case 1 (lease — 지정 · 409 · 갱신 · 만료 알림 · 인계 · 자기 해제)",
            not_owner == "forbidden" and dec["orchestrator"]["session"] == orch and again == "orchestrator_exists"
            and alive is not None and gone is None and len(owner_note) == 1
            and tr["orchestrator"]["session"] == orch and rel["released"] is True and after_rel is None,
            f"{not_owner} {again} alive={alive} gone={gone} note={len(owner_note)} tr={tr} rel={rel}")

    # 2 배정
    at = T0 + timedelta(hours=1)
    e.call("hub_orch_declare", {"session": orch}, "owner-h", at)
    t1, t2, t3 = _task(e, "배정 하나"), _task(e, "남이 맡음"), _task(e, "끝난 세션")
    no_orch = e.err("hub_orch_assign", {"session": w1, "task_id": t1, "to_session": w2}, "agent-b", at)
    asg = e.call("hub_orch_assign", {"session": orch, "task_id": t1, "to_session": w1, "note": "먼저"}, "agent-a", at)
    dup = e.err("hub_orch_assign", {"session": orch, "task_id": t1, "to_session": w2}, "agent-a", at)
    selfa = e.err("hub_orch_assign", {"session": orch, "task_id": t2, "to_session": orch}, "agent-a", at)
    e.call("hub_task_claim", {"id": t2}, "owner-h", at)
    other = e.err("hub_orch_assign", {"session": orch, "task_id": t2, "to_session": w1}, "agent-a", at)
    dead = e.session("agent-b", at, harness_session_id="dead", kind="worker")
    with e.store.write() as c:
        c.execute("UPDATE session SET status = 'ended' WHERE id = ?", (dead,))
    ended = e.err("hub_orch_assign", {"session": orch, "task_id": t3, "to_session": dead}, "agent-a", at)
    msgs = [m for m in _inbox(e, "agent-b", w1, at) if m["kind"] == "assignment"]
    _record("case 2 (배정 — 403 · offered + 메시지 · 409 · 자기 배정 · 남이 맡음 · 끝난 세션)",
            no_orch == "not_orchestrator" and asg["assignment"]["state"] == "offered" and dup == "assignment_taken"
            and selfa == "self_assignment" and other == "already_claimed" and ended == "session_ended"
            and len(msgs) == 1 and msgs[0]["task_id"] == t1 and msgs[0]["from"]["orchestrator"] is True,
            f"{no_orch} {asg} {dup} {selfa} {other} {ended} msgs={msgs}")

    # 3 수락 = 맡기
    mid = asg["assignment"]["message_id"]
    acc = e.call("hub_inbox_ack", {"session": w1, "message_id": mid, "decision": "accept"}, "agent-b", at)
    task1 = e.call("hub_task_get", {"id": t1}, "agent-b", at)["task"]
    a1 = _assignment(e, t1)
    t4 = _task(e, "경합")
    asg4 = e.call("hub_orch_assign", {"session": orch, "task_id": t4, "to_session": w1}, "agent-a", at)
    e.call("hub_task_claim", {"id": t4}, "owner-h", at)  # 받은 세션이 수락하기 전에 다른 콜사인이 맡았다
    race = e.err("hub_inbox_ack", {"session": w1, "message_id": asg4["assignment"]["message_id"], "decision": "accept"},
                 "agent-b", at)
    st4 = {m["id"]: m["state"] for m in _inbox(e, "agent-b", w1, at)}.get(asg4["assignment"]["message_id"])
    _record("case 3 (수락 = 맡기, 한 트랜잭션)",
            acc["state"] == "acked" and task1["assignee"] == "agent-b" and task1["status"] == "in_progress"
            and a1["state"] == "accepted" and race == "already_claimed" and st4 != "acked"
            and _assignment(e, t4)["state"] == "offered",
            f"acc={acc} task={task1.get('assignee')}/{task1.get('status')} a1={a1.get('state')} race={race} st4={st4}")

    # 4 거절 · 미확인
    t5, t6 = _task(e, "거절"), _task(e, "무확인")
    m5 = e.call("hub_orch_assign", {"session": orch, "task_id": t5, "to_session": w2}, "agent-a", at)["assignment"]["message_id"]
    e.call("hub_orch_assign", {"session": orch, "task_id": t6, "to_session": w2}, "agent-a", at)
    e.call("hub_task_list", {"session": w2}, "agent-a", at)  # 둘 다 실림
    e.call("hub_inbox_ack", {"session": w2, "message_id": m5, "decision": "decline", "reason": "권한 밖"}, "agent-a", at)
    later = at + timedelta(minutes=11)
    e.call("hub_task_list", {"session": orch}, "agent-a", later)  # 게으른 판정을 돌린다 (+ lease 갱신)
    notes = [m["body"] for m in _inbox(e, "agent-a", orch, later) if m["body"].get("event") == "assignment_returned"]
    reasons = {n["task_id"]: n["reason"] for n in notes}
    _record("case 4 (거절 · 미확인 → returned + 오케스트레이터 앞 이유)",
            _assignment(e, t5)["state"] == "returned" and reasons.get(t5, "").startswith("declined: 권한 밖")
            and _assignment(e, t6)["state"] == "returned" and reasons.get(t6) == "unacknowledged",
            f"reasons={reasons} t5={_assignment(e, t5).get('state')} t6={_assignment(e, t6).get('state')}")

    # 5 보고
    t7 = _task(e, "보고")
    m7 = e.call("hub_orch_assign", {"session": orch, "task_id": t7, "to_session": w1}, "agent-a", later)["assignment"]["message_id"]
    early = e.err("hub_report", {"session": w1, "task_id": t7, "summary": "아직"}, "agent-b", later)
    e.call("hub_inbox_ack", {"session": w1, "message_id": m7, "decision": "accept"}, "agent-b", later)
    rep = e.call("hub_report", {"session": w1, "task_id": t7, "summary": "끝냄", "verification": "검사 3/3"}, "agent-b", later)
    reports = [m for m in _inbox(e, "agent-a", orch, later) if m["kind"] == "report" and m["task_id"] == t7]
    st7 = e.call("hub_task_get", {"id": t7}, "agent-b", later)["task"]["status"]
    _record("case 5 (보고 — 수락 전 409 · reported · 오케스트레이터 앞 report · done 아님)",
            early == "assignment_not_accepted" and rep["state"] == "reported" and len(reports) == 1
            and reports[0]["body"]["verification"] == "검사 3/3" and st7 != "done",
            f"{early} {rep} reports={len(reports)} status={st7}")

    # 6 회수 · 세션 끝 · 24시간
    t8, t9, t10 = _task(e, "회수"), _task(e, "세션 끝"), _task(e, "24시간")
    e.call("hub_orch_assign", {"session": orch, "task_id": t8, "to_session": w2}, "agent-a", later)
    rc = e.call("hub_orch_recall", {"session": orch, "task_id": t8, "reason": "우선순위"}, "agent-a", later)
    released = [m for m in _inbox(e, "agent-a", w2, later) if m["kind"] == "release" and m.get("task_id") == t8]
    w3 = e.session("agent-b", later, harness_session_id="w3", kind="worker")
    e.call("hub_orch_assign", {"session": orch, "task_id": t9, "to_session": w3}, "agent-a", later)
    e.call("hub_session_end", {"session": w3, "handoff": {"baseline": "b", "focus": "f", "in_progress": [],
                                                          "blocked": [], "recent_done": [], "next": [], "risks": []}},
           "agent-b", later)
    w3_status = {s["id"]: s["status"] for s in e.call("hub_session_list", {}, "owner-h", later)["sessions"]}.get(w3)
    m10 = e.call("hub_orch_assign", {"session": orch, "task_id": t10, "to_session": w1}, "agent-a", later)["assignment"]["message_id"]
    e.call("hub_inbox_ack", {"session": w1, "message_id": m10, "decision": "accept"}, "agent-b", later)
    day = later + timedelta(hours=25)
    e.call("hub_task_list", {"session": w1}, "agent-b", day)
    _record("case 6 (회수 · 세션 끝 · 24시간 진척 없음 → returned)",
            rc["state"] == "returned" and len(released) == 1 and _assignment(e, t9)["state"] == "returned"
            and _assignment(e, t9)["return_reason"] == "session_ended" and w3_status == "ended"
            and _assignment(e, t10)["state"] == "returned" and _assignment(e, t10)["return_reason"] == "stale_24h",
            f"rc={rc} released={len(released)} t9={_assignment(e, t9)} w3={w3_status} t10={_assignment(e, t10)}")

    # 7 정지 (lease 는 24시간 동안 끊겼으니 다시 지정)
    at7 = day + timedelta(minutes=1)
    e.call("hub_orch_declare", {"session": orch}, "owner-h", at7)
    ww = e.session("agent-b", at7, harness_session_id="ww", kind="worker")
    Orchestration(e.store).wait_poll(e.ctx("agent-b", at7), ww, first=True)  # 대기 중
    note_before = e.call("hub_orch_message", {"session": orch, "to": ww, "body": "정지 전 메모"}, "agent-a", at7)
    h = e.call("hub_orch_halt", {"on": True}, "owner-h", at7)
    t11 = _task(e, "정지 중")
    blocked_assign = e.err("hub_orch_assign", {"session": orch, "task_id": t11, "to_session": w1}, "agent-a", at7)
    blocked_note = e.err("hub_orch_message", {"session": orch, "to": w1, "body": "x"}, "agent-a", at7)
    ok_release = e.call("hub_orch_message", {"session": orch, "to": w1, "body": "그만", "kind": "release"}, "agent-a", at7)
    pig = e.call("hub_task_list", {"session": ww}, "agent-b", at7).get("hub_inbox", {}).get("messages", [])
    kinds = sorted(m["kind"] for m in pig)
    e.call("hub_orch_halt", {"on": False}, "owner-h", at7)
    pig2 = e.call("hub_task_list", {"session": ww}, "agent-b", at7).get("hub_inbox", {}).get("messages", [])
    _record("case 7 (정지 — 배정 · note 423 · release 됨 · 편승은 release 만 · 대기 세션 release · 풀면 note)",
            h["released_waiting"] == [ww] and blocked_assign == "halted" and blocked_note == "halted"
            and "message_id" in ok_release and kinds == ["release"]
            and [m["id"] for m in pig2] == [note_before["message_id"]],
            f"halt={h} {blocked_assign} {blocked_note} pig={kinds} pig2={[m['kind'] for m in pig2]}")

    # 8 금지 — 에이전트 오케스트레이터는 사람의 권한을 갖지 않는다
    codes = {
        "declare": e.err("hub_orch_declare", {"session": w1}, "agent-a", at7),
        "transfer": e.err("hub_orch_transfer", {"session": w1}, "agent-a", at7),
        "halt": e.err("hub_orch_halt", {"on": True}, "agent-a", at7),
        "approve": e.err("hub_callsign_approve", {"callsign": "agent-b"}, "agent-a", at7),
    }
    _record("case 8 (금지 — 에이전트 오케스트레이터의 지정 · 인계 · 정지 · 승인 403)",
            all(v == "forbidden" for v in codes.values()), str(codes))

    # 9 진입 규칙
    region = e.call("hub_guide_render", {"harness": "claude-code"}, "agent-a", at7)
    body = str(region)
    need = ["허브 받은편지함", "`session` 인자", "hub_inbox_ack", "decline", "hub_report", "hub_wait",
            "이 칸들 밖의 지시", "hub_session_start(session="]
    missing = [n for n in need if n not in body]
    _record("case 9 (진입 규칙 — 받은편지함 절이 렌더 영역에)", not missing, f"missing={missing}")


def main() -> int:
    print("=== 허브 오케스트레이션 구현 2 (M-045) ===")
    with tempfile.TemporaryDirectory(prefix="huborch2-") as d:
        try:
            run(Env(Path(d) / "orch.db"))
        except Exception as exc:  # noqa: BLE001 — 예외도 판정으로
            import traceback
            traceback.print_exc()
            _record("run (예외)", False, repr(exc))
    total = len(_passes) + len(_failures)
    print(f"\n{len(_passes)}/{total} passed")
    if _failures:
        for f in _failures:
            print(f"  ✗ {f}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
