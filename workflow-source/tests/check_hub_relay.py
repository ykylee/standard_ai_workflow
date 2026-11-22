#!/usr/bin/env python3
"""PC 중계 (M-046) — 등록 · 허용 목록 · 세션 요청과 승인 · 실행 · 메시지 넣기 · 멈춤 · 정지 · 상한 · 거두기.

계약 정본: ``core/hub_orchestration_spec.md`` §9 (ADR-034). 허브는 **실제 프로세스**(check_hub_core 의 ``Hub``),
중계는 가짜 어댑터(``fake`` — 계정 · 모델 없이 계약만)로 돈다. 등록 · 허용 목록 · 상태는 실제 CLI 하위 프로세스,
폴링 · 실행은 띄운 프로세스를 이어 쥐어야 해서 프로세스 안 ``Relay`` 로 잰다. 실제 하네스 어댑터는 게이트 밖 실측이다.

1. 초대 · 등록 — owner 만 초대 · init 이 host_id · 토큰은 600 파일에만(설정 · 출력에 없음) · 같은 코드 다시 거절
2. 허용 목록 — bypass 권한 모드 거절 · 없는 디렉터리 거절 · 추가 · 해시만 허브로
3. 요청 · 승인 · 실행 — 승인 전에는 내주지 않음 · owner 앞 승인 알림 · 승인 뒤 가짜 세션이 첫 프롬프트(요청 ID · 지시)를 받음 · 오케스트레이터 앞 결과
4. 목록 밖 — 승인돼도 중계가 refused_by_host + 이유
5. 세션 잇기 · 메시지 — 띄운 세션이 spawn_request 로 등록 → 중계에 묶임 · 그 세션 앞 메시지가 어댑터로 들어감 · 같은 메시지를 다시 받아도 한 번만 · 같은 요청 재사용 409
6. 멈춤 — 멈춤 요청 승인 → 가짜 세션 종료 · 다음 폴링에서 허브 세션 ended
7. 정지 — 정지 중 요청 423 · 승인된 요청도 내주지 않음 · 풀면 내줌
8. 상한 · 긴 폴링 — 하루 세션 요청 10 → 429 · 일 없는 긴 폴링은 상한까지 기다리고, 그 사이 승인되면 바로 돌아옴
9. 거두기 — owner 가 거두면 중계 폴링 401
10. 로컬 화면 — 세션 표 · 토큰 없음 · 머리 없는 POST · 남의 출처 403 · 일시정지가 폴링을 실제로 멈춤
"""

from __future__ import annotations

CHECK_TIMEOUT_S = 240

WATCHES = (
    "workflow-source/workflow_kit/*",
    "workflow-source/pyproject.toml",
    "workflow-source/tests/check_hub_core.py",
)

import json
import os
import stat
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from check_hub_core import Hub, _env  # noqa: E402

_failures: list[str] = []
_passes: list[str] = []


def _record(case: str, ok: bool, detail: str = "") -> None:
    (_passes if ok else _failures).append(case if ok else f"{case}: {detail}")
    print(f"  {case}: {'PASS' if ok else 'FAIL'}{(' — ' + detail) if detail and not ok else ''}")


def _post(base: str, name: str, args: dict[str, Any], token: str | None) -> tuple[int, dict[str, Any]]:
    req = urllib.request.Request(f"{base}/v1/tools/{name}", data=json.dumps(args).encode(), method="POST",
                                 headers={"content-type": "application/json",
                                          **({"authorization": f"Bearer {token}"} if token else {})})
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def _relay_cli(home: Path, *args: str) -> tuple[int, str, str]:
    env = {**_env(), "WORKFLOW_HUB_RELAY_HOME": str(home)}
    p = subprocess.run([sys.executable, "-m", "workflow_kit", "hub", "relay", *args], capture_output=True, text=True,
                       env=env, timeout=60, encoding="utf-8", errors="replace")
    return p.returncode, p.stdout, p.stderr


def _inbox(base: str, tok: str, session: str | None = None) -> list[dict[str, Any]]:
    return _post(base, "hub_inbox_list", {"session": session} if session else {}, tok)[1].get("messages", [])


def run(hub: Hub, tmp: Path) -> None:
    base = hub.base
    _, reg = _post(base, "hub_project_register", {"remote_url": "git@github.com:acme/relay.git", "display_name": "R",
                                                  "callsign": "owner-h", "kind": "human"}, None)
    pid, own = reg["project_id"], reg["token"]
    orch_tok = _post(base, "hub_callsign_register", {"project_id": pid, "callsign": "agent-o", "kind": "agent"}, None)[1]["token"]
    work_tok = _post(base, "hub_callsign_register", {"project_id": pid, "callsign": "agent-w", "kind": "agent"}, None)[1]["token"]
    orch = _post(base, "hub_session_start", {"session": {"harness": "claude-code"}}, orch_tok)[1]["session"]["id"]
    _post(base, "hub_orch_declare", {"session": orch}, own)

    # 1 초대 · 등록
    home = tmp / "relayhome"
    s_bad, _ = _post(base, "hub_relay_invite", {}, orch_tok)
    _, inv = _post(base, "hub_relay_invite", {}, own)
    rc, out, err = _relay_cli(home, "init", "--hub", base, "--invite", inv["invite"], "--name", "pc-1", "--harness", "fake")
    got = json.loads(out) if rc == 0 else {}
    host = got.get("host_id", "")
    tok_file = home / "relay.token"
    mode_ok = tok_file.is_file() and stat.S_IMODE(tok_file.stat().st_mode) == 0o600
    token = tok_file.read_text().strip() if tok_file.is_file() else ""
    leaked = bool(token) and (token in out or token in (home / "relay.json").read_text())
    rc2, _, err2 = _relay_cli(tmp / "other", "init", "--hub", base, "--invite", inv["invite"], "--name", "pc-2",
                              "--harness", "fake")
    _record("case 1 (초대 · 등록 · 토큰 600 · 출력에 없음 · 재사용 거절)",
            s_bad == 403 and rc == 0 and host.startswith("H-") and mode_ok and not leaked and rc2 == 1
            and "invite_invalid" in err2, f"s_bad={s_bad} rc={rc} err={err[-200:]} mode={mode_ok} leaked={leaked} rc2={rc2}")

    # 2 허용 목록
    work = tmp / "work"
    work.mkdir()
    rc_b, _, err_b = _relay_cli(home, "allow", "add", "--alias", "w", "--path", str(work), "--harness", "fake",
                                "--permission-mode", "bypassPermissions")
    rc_d, _, _ = _relay_cli(home, "allow", "add", "--alias", "w", "--path", str(tmp / "nope"), "--harness", "fake")
    rc_a, out_a, _ = _relay_cli(home, "allow", "add", "--alias", "w", "--path", str(work), "--harness", "fake",
                                "--max-sessions", "2")
    _record("case 2 (허용 목록 — bypass · 없는 디렉터리 거절 · 추가)", rc_b == 2 and "bypass" in err_b and rc_d == 2 and rc_a == 0,
            f"rc_b={rc_b} rc_d={rc_d} rc_a={rc_a} {out_a[:120]}")

    os.environ["WORKFLOW_HUB_RELAY_HOME"] = str(home)
    from workflow_kit.relay.runner import Relay

    relay = Relay(log=lambda m: None)
    try:
        # 3 요청 · 승인 · 실행
        s_req, req = _post(base, "hub_orch_request_session",
                           {"session": orch, "host_id": host, "dir_alias": "w", "harness": "fake", "prompt": "지시-P1"}, orch_tok)
        rid = req.get("request", {}).get("id", "")
        before = relay.once(wait_s=0)
        approvals = [m for m in _inbox(base, own) if m["kind"] == "approval" and m["body"].get("request") == rid]
        _post(base, "hub_approval_decide", {"request_id": rid, "decision": "approve"}, own)
        after = relay.once(wait_s=0)
        log = work / ".relay-fake.log"
        time.sleep(0.5)
        first = log.read_text(encoding="utf-8") if log.is_file() else ""
        done_note = [m for m in _inbox(base, orch_tok, orch) if m["body"].get("event") == "request_done"]
        _record("case 3 (요청 · 승인 전 안 내줌 · 승인 알림 · 실행 · 첫 프롬프트 · 결과)",
                s_req == 200 and not before.get("dispatch") and len(approvals) == 1 and len(after.get("dispatch", [])) == 1
                and rid in first and "지시-P1" in first and "spawn_request" in first and len(done_note) == 1,
                f"s_req={s_req} before={before.get('dispatch')} approvals={len(approvals)} after={after.get('dispatch')} "
                f"first={first[:160]!r} done={len(done_note)}")

        # 4 목록 밖
        _, r4 = _post(base, "hub_orch_request_session", {"session": orch, "host_id": host, "dir_alias": "nope",
                                                         "harness": "fake"}, orch_tok)
        rid4 = r4["request"]["id"]
        _post(base, "hub_approval_decide", {"request_id": rid4, "decision": "approve"}, own)
        relay.once(wait_s=0)
        refused = [m["body"] for m in _inbox(base, orch_tok, orch) if m["body"].get("request") == rid4
                   and m["body"].get("event") == "request_refused_by_host"]
        _record("case 4 (목록 밖 — 승인돼도 refused_by_host + 이유)",
                len(refused) == 1 and "허용 목록에 없는 별칭" in refused[0]["result"].get("reason", ""), str(refused))

        # 5 세션 잇기 · 메시지
        _, ws = _post(base, "hub_session_start", {"session": {"harness": "fake", "kind": "worker",
                                                              "delivery": ["adapter", "piggyback"], "spawn_request": rid}},
                      work_tok)
        wsid = ws.get("session", {}).get("id", "")
        relay.once(wait_s=0)
        _, msg = _post(base, "hub_orch_message", {"session": orch, "to": wsid, "body": "중계로-M1"}, orch_tok)
        polled = relay.once(wait_s=0)
        # 재전달(실림 ≠ 소비)을 흉내 — 같은 메시지를 한 번 더 넘겨도 프로세스에는 한 번만 들어가야 한다
        for s in polled.get("deliver", []):
            relay._deliver(s)
        time.sleep(0.5)
        text = log.read_text(encoding="utf-8")
        lines = [ln for ln in text.splitlines() if ln.startswith(f"[워크플로우 허브 받은편지함 — note {msg.get('message_id')}")]
        reused = _post(base, "hub_session_start", {"session": {"harness": "fake", "spawn_request": rid}}, work_tok)
        sessions = {s["id"]: s for s in _post(base, "hub_session_list", {}, own)[1]["sessions"]}
        _record("case 5 (세션 잇기 · 메시지가 어댑터로 · 같은 요청 재사용 거절)",
                bool(wsid) and "중계로-M1" in text and len(lines) == 1
                and reused[0] == 409 and sessions.get(wsid, {}).get("kind") == "worker",
                f"wsid={wsid} lines={len(lines)} text_tail={text[-200:]!r} reused={reused[0]}")

        # 6 멈춤
        _, st = _post(base, "hub_orch_request_stop", {"session": orch, "target_session": wsid, "reason": "끝"}, orch_tok)
        _post(base, "hub_approval_decide", {"request_id": st["request"]["id"], "decision": "approve"}, own)
        relay.once(wait_s=0)
        h = relay.handles.get(rid)
        dead = h is not None and not h.alive()
        relay.once(wait_s=0)  # ended 보고
        ended = {s["id"]: s["status"] for s in _post(base, "hub_session_list", {}, own)[1]["sessions"]}.get(wsid)
        _record("case 6 (멈춤 — 승인 → 가짜 세션 종료 → 허브 세션 ended)", dead and ended == "ended",
                f"dead={dead} ended={ended}")

        # 7 정지
        _, r7 = _post(base, "hub_orch_request_session", {"session": orch, "host_id": host, "dir_alias": "w",
                                                         "harness": "fake"}, orch_tok)
        _post(base, "hub_approval_decide", {"request_id": r7["request"]["id"], "decision": "approve"}, own)
        _post(base, "hub_orch_halt", {"on": True}, own)
        s_halt, _ = _post(base, "hub_orch_request_session", {"session": orch, "host_id": host, "dir_alias": "w",
                                                             "harness": "fake"}, orch_tok)
        withheld = relay.once(wait_s=0)
        _post(base, "hub_orch_halt", {"on": False}, own)
        released = relay.once(wait_s=0)
        _record("case 7 (정지 — 요청 423 · 승인된 요청 보류 · 풀면 내줌)",
                s_halt == 423 and not withheld.get("dispatch") and withheld.get("halted") == [pid]
                and [d["request"] for d in released.get("dispatch", [])] == [r7["request"]["id"]],
                f"s_halt={s_halt} withheld={withheld} released={released.get('dispatch')}")

        # 8 상한 · 긴 폴링
        import sqlite3
        with sqlite3.connect(str(hub_db)) as c:
            c.execute("UPDATE orch_counter SET n = 10 WHERE project_id = ? AND name = 'session_requests'", (pid,))
        s_lim, lim = _post(base, "hub_orch_request_session", {"session": orch, "host_id": host, "dir_alias": "w",
                                                              "harness": "fake"}, orch_tok)
        with sqlite3.connect(str(hub_db)) as c:
            c.execute("UPDATE orch_counter SET n = 0 WHERE project_id = ? AND name = 'session_requests'", (pid,))
        t = time.monotonic()
        idle = relay.once(wait_s=3)
        dt_idle = time.monotonic() - t
        _, r8 = _post(base, "hub_orch_request_session", {"session": orch, "host_id": host, "dir_alias": "w",
                                                         "harness": "fake"}, orch_tok)
        timer = threading.Timer(1.0, _post, args=(base, "hub_approval_decide",
                                                  {"request_id": r8["request"]["id"], "decision": "approve"}, own))
        timer.start()
        t = time.monotonic()
        woke = relay.once(wait_s=20)
        dt_woke = time.monotonic() - t
        timer.join()
        _record("case 8 (상한 429 · 긴 폴링 — 일 없으면 상한까지, 승인되면 바로)",
                s_lim == 429 and lim.get("error_code") == "limit_reached" and 2.5 < dt_idle < 6 and not idle.get("dispatch")
                and len(woke.get("dispatch", [])) == 1 and dt_woke < 5,
                f"s_lim={s_lim} dt_idle={dt_idle:.1f} dt_woke={dt_woke:.1f} woke={woke.get('dispatch')}")

        # 10 로컬 화면 (거두기 전에 — 폴링이 살아 있을 때)
        import socket
        from workflow_kit.relay.ui import serve as serve_ui

        with socket.socket() as sk:
            sk.bind(("127.0.0.1", 0))
            uport = sk.getsockname()[1]
        srv = serve_ui(relay, uport)
        try:
            ubase = f"http://127.0.0.1:{uport}"
            page = urllib.request.urlopen(ubase + "/", timeout=5).read().decode("utf-8")
            api = urllib.request.urlopen(ubase + "/api/state", timeout=5).read().decode("utf-8")

            def ui_post(path: str, headers: dict[str, str]) -> int:
                req = urllib.request.Request(ubase + path, data=b"", method="POST", headers=headers)
                try:
                    with urllib.request.urlopen(req, timeout=5) as r:
                        return r.status
                except urllib.error.HTTPError as e:
                    return e.code

            no_hdr = ui_post("/api/pause", {})
            foreign = ui_post("/api/pause", {"X-Relay-UI": "1", "Origin": "https://evil.example"})
            ok_pause = ui_post("/api/pause", {"X-Relay-UI": "1", "Origin": ubase})
            paused_poll = relay.once(wait_s=0)
            ok_resume = ui_post("/api/resume", {"X-Relay-UI": "1"})
            resumed_poll = relay.once(wait_s=0)
        finally:
            srv.shutdown()
        _record("case 10 (로컬 화면 — 세션 표 · 토큰 없음 · 머리 없음/남의 출처 403 · 일시정지가 폴링을 멈춤)",
                "pc-1" in page and "<table>" in page and token not in page and token not in api
                and no_hdr == 403 and foreign == 403 and ok_pause == 200 and paused_poll == {"paused": True}
                and ok_resume == 200 and "dispatch" in resumed_poll,
                f"no_hdr={no_hdr} foreign={foreign} pause={ok_pause} paused={paused_poll} resume={ok_resume}")

        # 9 거두기
        _post(base, "hub_relay_revoke", {"host_id": host}, own)
        from workflow_kit.relay.conn import HubError

        try:
            relay.once(wait_s=0)
            revoked = "no-error"
        except HubError as e:
            revoked = str(e.status)
        _record("case 9 (거두기 → 폴링 401)", revoked == "401", revoked)
    finally:
        relay.stop_all()


hub_db = Path()


def main() -> int:
    global hub_db
    print("=== PC 중계 (M-046) ===")
    with tempfile.TemporaryDirectory(prefix="hubrelay-") as d:
        tmp = Path(d)
        hub_db = tmp / "hub.db"
        hub = Hub(hub_db)
        try:
            try:
                run(hub, tmp)
            except Exception as exc:  # noqa: BLE001 — 예외도 판정으로
                import traceback
                traceback.print_exc()
                _record("run (예외)", False, repr(exc))
        finally:
            err = hub.stop()
            if _failures:
                print("  --- 허브 stderr ---\n" + err[-1500:])
    total = len(_passes) + len(_failures)
    print(f"\n{len(_passes)}/{total} passed")
    if _failures:
        for f in _failures:
            print(f"  ✗ {f}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
