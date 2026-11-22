#!/usr/bin/env python3
"""PC 중계 (M-046 · M-052 WBS-52.3) — 등록 · 허용 목록 · 세션 요청과 승인 · 실행 · 메시지 넣기 · 멈춤 · 정지 · 상한 · 거두기.

계약 정본: ``core/hub_orchestration_spec.md`` §9 (ADR-034) · ``core/hub_go_spec.md`` §6.
허브는 **실제 프로세스**(check_hub_core 의 ``Hub``), 중계는 **실제 중계 프로세스**(``serve --ui-port`` +
``WORKFLOW_HUB_RELAY_MANUAL=1`` 수동 폴링 HTTP 제어) 와 가짜 어댑터(``fake`` — 계정 · 모델 없이 계약만)로 돈다.
구현 스위치 ``WORKFLOW_RELAY_IMPL`` (``python`` | ``go`` | ``both``, 기본 ``both`` — Go 가 있으면 둘 다 잰다).
실제 하네스 어댑터는 게이트 밖 실측이다.

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
11. Codex 쓰기 루트 — workspace-write 면 작업 디렉터리 + git dir (worktree 는 common dir 도) · plan 은 정책 없음 ·
    git 밖은 작업 디렉터리만 · ``turn/start`` 에 ``sandboxPolicy`` 로 실림 (TASK-2026-11-22-main-014 — 실제 Codex 커밋은 게이트 밖 실측)
"""

from __future__ import annotations

CHECK_TIMEOUT_S = 240

WATCHES = (
    "workflow-source/workflow_kit/*",
    "workflow-source/pyproject.toml",
    "workflow-source/tests/check_hub_core.py",
    "hub-go/*",
)

import json
import os
import re
import shutil
import socket
import sqlite3
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
HUB_GO = REPO_ROOT / "hub-go"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from check_hub_core import Hub, _env  # noqa: E402

_failures: list[str] = []
_passes: list[str] = []
_skips: list[str] = []


def _record(case: str, ok: bool, detail: str = "") -> None:
    (_passes if ok else _failures).append(case if ok else f"{case}: {detail}")
    print(f"  {case}: {'PASS' if ok else 'FAIL'}{(' — ' + detail) if detail and not ok else ''}")


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def _post(base: str, name: str, args: dict[str, Any], token: str | None) -> tuple[int, dict[str, Any]]:
    req = urllib.request.Request(f"{base}/v1/tools/{name}", data=json.dumps(args).encode(), method="POST",
                                 headers={"content-type": "application/json",
                                          **({"authorization": f"Bearer {token}"} if token else {})})
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def _ui_post(uport: int, path: str, body: dict[str, Any] | None = None,
             headers: dict[str, str] | None = None) -> tuple[int, dict[str, Any]]:
    hdrs = {"X-Relay-UI": "1"} if headers is None else dict(headers)
    data = b"" if body is None else json.dumps(body).encode("utf-8")
    if body is not None:
        hdrs.setdefault("content-type", "application/json")
    req = urllib.request.Request(f"http://127.0.0.1:{uport}{path}", data=data, method="POST", headers=hdrs)
    try:
        with urllib.request.urlopen(req, timeout=45) as r:
            return r.status, json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        try:
            return e.code, json.loads(raw)
        except ValueError:
            return e.code, {"error_code": "http_error", "raw": raw}


def _ui_get(uport: int, path: str) -> tuple[int, str]:
    with urllib.request.urlopen(f"http://127.0.0.1:{uport}{path}", timeout=10) as r:
        return r.status, r.read().decode("utf-8")


def _relay_cli(cmd_prefix: list[str], home: Path, *args: str) -> tuple[int, str, str]:
    env = {**_env(), "WORKFLOW_HUB_RELAY_HOME": str(home)}
    p = subprocess.run([*cmd_prefix, *args], capture_output=True, text=True,
                       env=env, timeout=60, encoding="utf-8", errors="replace")
    return p.returncode, p.stdout, p.stderr


def _inbox(base: str, tok: str, session: str | None = None) -> list[dict[str, Any]]:
    return _post(base, "hub_inbox_list", {"session": session} if session else {}, tok)[1].get("messages", [])


def _declared_go_version() -> str | None:
    mod = HUB_GO / "go.mod"
    if not mod.is_file():
        return None
    for raw in mod.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line.startswith("go "):
            return line.split(None, 1)[1].strip()
    return None


def _resolve_go_relay(tmp: Path) -> tuple[list[str] | None, str]:
    explicit = os.environ.get("WORKFLOW_HUB_BIN", "").strip()
    if explicit:
        bin_path = Path(explicit)
        if bin_path.is_file():
            return [str(bin_path), "relay"], ""
        return None, f"WORKFLOW_HUB_BIN 파일이 없다: {explicit}"

    go_exe = shutil.which("go")
    if not go_exe:
        return None, "go 실행 파일이 PATH 에 없다"
    declared = _declared_go_version()
    if not declared:
        return None, "hub-go/go.mod 에서 go 판을 읽지 못했다"
    env = {**os.environ, "GOTOOLCHAIN": "local", "CGO_ENABLED": "0"}
    vproc = subprocess.run([go_exe, "version"], capture_output=True, text=True, env=env, timeout=30,
                           encoding="utf-8", errors="replace")
    m = re.search(r"\bgo(\d+\.\d+(?:\.\d+)?)\b", vproc.stdout)
    actual = m.group(1) if m else ""
    if actual != declared:
        return None, f"go 판 불일치: 호스트 {actual} != go.mod {declared}"
    out_bin = tmp / ("workflow-hub.exe" if os.name == "nt" else "workflow-hub")
    bproc = subprocess.run([go_exe, "build", "-trimpath", "-o", str(out_bin), "./cmd/workflow-hub"],
                           cwd=str(HUB_GO), env=env, capture_output=True, text=True, timeout=120,
                           encoding="utf-8", errors="replace")
    if bproc.returncode != 0 or not out_bin.is_file():
        return None, f"go build 실패: {(bproc.stdout + bproc.stderr).strip()[:200]}"
    return [str(out_bin), "relay"], ""


class RelayProc:
    def __init__(self, cmd_prefix: list[str], home: Path, uport: int) -> None:
        self.uport = uport
        env = {**_env(), "WORKFLOW_HUB_RELAY_HOME": str(home), "WORKFLOW_HUB_RELAY_MANUAL": "1"}
        self.proc = subprocess.Popen(
            [*cmd_prefix, "serve", "--ui-port", str(uport)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, encoding="utf-8", errors="replace",
        )
        deadline = time.time() + 15
        while time.time() < deadline:
            try:
                st, _ = _ui_get(uport, "/api/state")
                if st == 200:
                    return
            except OSError:
                if self.proc.poll() is not None:
                    break
                time.sleep(0.1)
        err = self.stop()
        raise RuntimeError(f"중계가 뜨지 않았다 (uport={uport}): {err[-500:]}")

    def stop(self) -> str:
        if self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(10)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                self.proc.wait(5)
        return self.proc.stderr.read() if self.proc.stderr else ""


def run(impl: str, cmd_prefix: list[str], hub: Hub, hub_db: Path, tmp: Path) -> None:
    base = hub.base
    tag = f"[{impl}] "
    _, reg = _post(base, "hub_project_register", {"remote_url": f"git@github.com:acme/relay-{impl}.git",
                                                  "display_name": f"R-{impl}", "callsign": "owner-h", "kind": "human"}, None)
    pid, own = reg["project_id"], reg["token"]
    orch_tok = _post(base, "hub_callsign_register", {"project_id": pid, "callsign": "agent-o", "kind": "agent"}, None)[1]["token"]
    work_tok = _post(base, "hub_callsign_register", {"project_id": pid, "callsign": "agent-w", "kind": "agent"}, None)[1]["token"]
    orch = _post(base, "hub_session_start", {"session": {"harness": "claude-code"}}, orch_tok)[1]["session"]["id"]
    _post(base, "hub_orch_declare", {"session": orch}, own)

    # 1 초대 · 등록
    home = tmp / "relayhome"
    s_bad, _ = _post(base, "hub_relay_invite", {}, orch_tok)
    _, inv = _post(base, "hub_relay_invite", {}, own)
    rc, out, err = _relay_cli(cmd_prefix, home, "init", "--hub", base, "--invite", inv["invite"], "--name", "pc-1", "--harness", "fake")
    got = json.loads(out) if rc == 0 else {}
    host = got.get("host_id", "")
    tok_file = home / "relay.token"
    mode_ok = tok_file.is_file() and stat.S_IMODE(tok_file.stat().st_mode) == 0o600
    token = tok_file.read_text(encoding="utf-8").strip() if tok_file.is_file() else ""
    leaked = bool(token) and (token in out or token in (home / "relay.json").read_text(encoding="utf-8"))
    rc2, _, err2 = _relay_cli(cmd_prefix, tmp / "other", "init", "--hub", base, "--invite", inv["invite"], "--name", "pc-2",
                              "--harness", "fake")
    _record(f"{tag}case 1 (초대 · 등록 · 토큰 600 · 출력에 없음 · 재사용 거절)",
            s_bad == 403 and rc == 0 and host.startswith("H-") and mode_ok and not leaked and rc2 == 1
            and "invite_invalid" in err2, f"s_bad={s_bad} rc={rc} err={err[-200:]} mode={mode_ok} leaked={leaked} rc2={rc2}")

    # 2 허용 목록
    work = tmp / "work"
    work.mkdir()
    rc_b, _, err_b = _relay_cli(cmd_prefix, home, "allow", "add", "--alias", "w", "--path", str(work), "--harness", "fake",
                                "--permission-mode", "bypassPermissions")
    rc_d, _, _ = _relay_cli(cmd_prefix, home, "allow", "add", "--alias", "w", "--path", str(tmp / "nope"), "--harness", "fake")
    rc_a, out_a, _ = _relay_cli(cmd_prefix, home, "allow", "add", "--alias", "w", "--path", str(work), "--harness", "fake",
                                "--max-sessions", "2")
    _record(f"{tag}case 2 (허용 목록 — bypass · 없는 디렉터리 거절 · 추가)", rc_b == 2 and "bypass" in err_b and rc_d == 2 and rc_a == 0,
            f"rc_b={rc_b} rc_d={rc_d} rc_a={rc_a} {out_a[:120]}")

    uport = _free_port()
    relay_proc = RelayProc(cmd_prefix, home, uport)
    try:
        # 3 요청 · 승인 · 실행
        s_req, req = _post(base, "hub_orch_request_session",
                           {"session": orch, "host_id": host, "dir_alias": "w", "harness": "fake", "prompt": "지시-P1"}, orch_tok)
        rid = req.get("request", {}).get("id", "")
        _, before = _ui_post(uport, "/api/poll", {"wait_s": 0})
        approvals = [m for m in _inbox(base, own) if m["kind"] == "approval" and m["body"].get("request") == rid]
        _post(base, "hub_approval_decide", {"request_id": rid, "decision": "approve"}, own)
        _, after = _ui_post(uport, "/api/poll", {"wait_s": 0})
        log = work / ".relay-fake.log"
        deadline = time.time() + 3.0
        first = ""
        while time.time() < deadline:
            if log.is_file():
                first = log.read_text(encoding="utf-8")
                if rid in first and "지시-P1" in first:
                    break
            time.sleep(0.05)
        done_note = [m for m in _inbox(base, orch_tok, orch) if m["body"].get("event") == "request_done"]
        _record(f"{tag}case 3 (요청 · 승인 전 안 내줌 · 승인 알림 · 실행 · 첫 프롬프트 · 결과)",
                s_req == 200 and not before.get("dispatch") and len(approvals) == 1 and len(after.get("dispatch", [])) == 1
                and rid in first and "지시-P1" in first and "spawn_request" in first and len(done_note) == 1,
                f"s_req={s_req} before={before.get('dispatch')} approvals={len(approvals)} after={after.get('dispatch')} "
                f"first={first[:160]!r} done={len(done_note)}")

        # 4 목록 밖
        _, r4 = _post(base, "hub_orch_request_session", {"session": orch, "host_id": host, "dir_alias": "nope",
                                                         "harness": "fake"}, orch_tok)
        rid4 = r4["request"]["id"]
        _post(base, "hub_approval_decide", {"request_id": rid4, "decision": "approve"}, own)
        _ui_post(uport, "/api/poll", {"wait_s": 0})
        refused = [m["body"] for m in _inbox(base, orch_tok, orch) if m["body"].get("request") == rid4
                   and m["body"].get("event") == "request_refused_by_host"]
        _record(f"{tag}case 4 (목록 밖 — 승인돼도 refused_by_host + 이유)",
                len(refused) == 1 and "허용 목록에 없는 별칭" in refused[0]["result"].get("reason", ""), str(refused))

        # 5 세션 잇기 · 메시지
        _, ws = _post(base, "hub_session_start", {"session": {"harness": "fake", "kind": "worker",
                                                              "delivery": ["adapter", "piggyback"], "spawn_request": rid}},
                      work_tok)
        wsid = ws.get("session", {}).get("id", "")
        _ui_post(uport, "/api/poll", {"wait_s": 0})
        _, msg = _post(base, "hub_orch_message", {"session": orch, "to": wsid, "body": "중계로-M1"}, orch_tok)
        _, polled = _ui_post(uport, "/api/poll", {"wait_s": 0})
        # 재전달(실림 ≠ 소비)을 흉내 — 같은 메시지를 한 번 더 넘겨도 프로세스에는 한 번만 들어가야 한다
        for s in polled.get("deliver", []):
            _ui_post(uport, "/api/deliver", s)
        deadline = time.time() + 3.0
        text = ""
        while time.time() < deadline:
            if log.is_file():
                text = log.read_text(encoding="utf-8")
                if "중계로-M1" in text:
                    break
            time.sleep(0.05)
        time.sleep(0.15)
        text = log.read_text(encoding="utf-8") if log.is_file() else ""
        lines = [ln for ln in text.splitlines() if ln.startswith(f"[워크플로우 허브 받은편지함 — note {msg.get('message_id')}")]
        reused = _post(base, "hub_session_start", {"session": {"harness": "fake", "spawn_request": rid}}, work_tok)
        sessions = {s["id"]: s for s in _post(base, "hub_session_list", {}, own)[1]["sessions"]}
        _record(f"{tag}case 5 (세션 잇기 · 메시지가 어댑터로 · 같은 요청 재사용 거절)",
                bool(wsid) and "중계로-M1" in text and len(lines) == 1
                and reused[0] == 409 and sessions.get(wsid, {}).get("kind") == "worker",
                f"wsid={wsid} lines={len(lines)} text_tail={text[-200:]!r} reused={reused[0]}")

        # 6 멈춤
        _, st = _post(base, "hub_orch_request_stop", {"session": orch, "target_session": wsid, "reason": "끝"}, orch_tok)
        _post(base, "hub_approval_decide", {"request_id": st["request"]["id"], "decision": "approve"}, own)
        _ui_post(uport, "/api/poll", {"wait_s": 0})
        _, api_raw = _ui_get(uport, "/api/state")
        api_doc = json.loads(api_raw)
        sess_entry = next((x for x in api_doc.get("sessions", []) if x.get("request") == rid), None)
        dead = sess_entry is not None and sess_entry.get("status") == "ended"
        _ui_post(uport, "/api/poll", {"wait_s": 0})  # ended 보고
        ended = {s["id"]: s["status"] for s in _post(base, "hub_session_list", {}, own)[1]["sessions"]}.get(wsid)
        _record(f"{tag}case 6 (멈춤 — 승인 → 가짜 세션 종료 → 허브 세션 ended)", dead and ended == "ended",
                f"dead={dead} sess_entry={sess_entry} ended={ended}")

        # 7 정지
        _, r7 = _post(base, "hub_orch_request_session", {"session": orch, "host_id": host, "dir_alias": "w",
                                                         "harness": "fake"}, orch_tok)
        _post(base, "hub_approval_decide", {"request_id": r7["request"]["id"], "decision": "approve"}, own)
        _post(base, "hub_orch_halt", {"on": True}, own)
        s_halt, _ = _post(base, "hub_orch_request_session", {"session": orch, "host_id": host, "dir_alias": "w",
                                                             "harness": "fake"}, orch_tok)
        _, withheld = _ui_post(uport, "/api/poll", {"wait_s": 0})
        _post(base, "hub_orch_halt", {"on": False}, own)
        _, released = _ui_post(uport, "/api/poll", {"wait_s": 0})
        _record(f"{tag}case 7 (정지 — 요청 423 · 승인된 요청 보류 · 풀면 내줌)",
                s_halt == 423 and not withheld.get("dispatch") and withheld.get("halted") == [pid]
                and [d["request"] for d in released.get("dispatch", [])] == [r7["request"]["id"]],
                f"s_halt={s_halt} withheld={withheld} released={released.get('dispatch')}")

        # 8 상한 · 긴 폴링
        with sqlite3.connect(str(hub_db)) as c:
            c.execute("UPDATE orch_counter SET n = 10 WHERE project_id = ? AND name = 'session_requests'", (pid,))
        s_lim, lim = _post(base, "hub_orch_request_session", {"session": orch, "host_id": host, "dir_alias": "w",
                                                              "harness": "fake"}, orch_tok)
        with sqlite3.connect(str(hub_db)) as c:
            c.execute("UPDATE orch_counter SET n = 0 WHERE project_id = ? AND name = 'session_requests'", (pid,))
        t = time.monotonic()
        _, idle = _ui_post(uport, "/api/poll", {"wait_s": 3})
        dt_idle = time.monotonic() - t
        _, r8 = _post(base, "hub_orch_request_session", {"session": orch, "host_id": host, "dir_alias": "w",
                                                         "harness": "fake"}, orch_tok)
        timer = threading.Timer(1.0, _post, args=(base, "hub_approval_decide",
                                                  {"request_id": r8["request"]["id"], "decision": "approve"}, own))
        timer.start()
        t = time.monotonic()
        _, woke = _ui_post(uport, "/api/poll", {"wait_s": 20})
        dt_woke = time.monotonic() - t
        timer.join()
        _record(f"{tag}case 8 (상한 429 · 긴 폴링 — 일 없으면 상한까지, 승인되면 바로)",
                s_lim == 429 and lim.get("error_code") == "limit_reached" and 2.5 < dt_idle < 6 and not idle.get("dispatch")
                and len(woke.get("dispatch", [])) == 1 and dt_woke < 5,
                f"s_lim={s_lim} dt_idle={dt_idle:.1f} dt_woke={dt_woke:.1f} woke={woke.get('dispatch')}")

        # 10 로컬 화면 (거두기 전에 — 폴링이 살아 있을 때)
        ubase = f"http://127.0.0.1:{uport}"
        _, page = _ui_get(uport, "/")
        _, api = _ui_get(uport, "/api/state")
        api_state = json.loads(api)
        allow0 = (api_state.get("allow") or [{}])[0]
        before_active = int(allow0.get("active_sessions", -1))
        no_hdr = _ui_post(uport, "/api/pause", headers={})[0]
        foreign = _ui_post(uport, "/api/pause", headers={"X-Relay-UI": "1", "Origin": "https://evil.example"})[0]
        ok_pause = _ui_post(uport, "/api/pause", headers={"X-Relay-UI": "1", "Origin": ubase})[0]
        _, paused_poll = _ui_post(uport, "/api/poll", {"wait_s": 0})
        ok_resume = _ui_post(uport, "/api/resume", headers={"X-Relay-UI": "1"})[0]
        _, resumed_poll = _ui_post(uport, "/api/poll", {"wait_s": 0})
        r7_req = r7["request"]["id"]
        stop_miss = _ui_post(uport, "/api/sessions/SR-9999/stop", headers={"X-Relay-UI": "1", "Origin": ubase})[0]
        stop_nohdr = _ui_post(uport, f"/api/sessions/{r7_req}/stop", headers={})[0]
        stop_ok, stop_doc = _ui_post(uport, f"/api/sessions/{r7_req}/stop", headers={"X-Relay-UI": "1", "Origin": ubase})
        _, api_after_raw = _ui_get(uport, "/api/state")
        api_after = json.loads(api_after_raw)
        r7_entry = next((x for x in api_after.get("sessions", []) if x.get("request") == r7_req), {})
        allow0_after = (api_after.get("allow") or [{}])[0]
        hub_orch_link = f"{base}/ui/#/p/{pid}/orch"
        _record(f"{tag}case 10 (로컬 화면 — 무깜빡임 fetch · 로컬 path/사용률 · 허브 딥링크 · 개별 종료 · 출처 403)",
                "pc-1" in page and "<table>" in page and 'http-equiv="refresh"' not in page
                and 'fetch("/api/state"' in page and hub_orch_link in page
                and Path(str(allow0.get("path", ""))).resolve() == work.resolve() and before_active >= 1
                and token not in page and token not in api
                and no_hdr == 403 and foreign == 403 and ok_pause == 200 and paused_poll == {"paused": True}
                and ok_resume == 200 and "dispatch" in resumed_poll
                and stop_miss == 404 and stop_nohdr == 403 and stop_ok == 200 and stop_doc.get("stopped") == r7_req
                and r7_entry.get("status") == "ended" and allow0_after.get("active_sessions") == before_active - 1,
                f"no_hdr={no_hdr} foreign={foreign} pause={ok_pause} stop={stop_miss}/{stop_nohdr}/{stop_ok} "
                f"allow0={allow0} allow0_after={allow0_after} r7={r7_entry}")

        # 9 거두기
        _post(base, "hub_relay_revoke", {"host_id": host}, own)
        rev_status, _ = _ui_post(uport, "/api/poll", {"wait_s": 0})
        _record(f"{tag}case 9 (거두기 → 폴링 401)", rev_status == 401, str(rev_status))
    finally:
        relay_proc.stop()


def run_codex_roots(impl: str, cmd_prefix: list[str], tmp: Path) -> None:
    tag = f"[{impl}] "
    home = tmp / "relayhome"
    repo = tmp / "cx-repo"
    repo.mkdir()
    git = ["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid"]
    subprocess.run([*git, "-C", str(repo), "init", "-q"], check=True)
    subprocess.run([*git, "-C", str(repo), "commit", "-q", "--allow-empty", "-m", "init"], check=True)
    wt = tmp / "cx-wt"
    subprocess.run([*git, "-C", str(repo), "worktree", "add", "-q", "-b", "wt", str(wt)], check=True)
    plain = tmp / "cx-plain"
    plain.mkdir()
    real = lambda p: str(Path(p).resolve())  # noqa: E731

    def cli_policy(sandbox: str, cwd: Path) -> dict[str, Any] | None:
        rc, out, err = _relay_cli(cmd_prefix, home, "__sandbox-policy", "--sandbox", sandbox, "--cwd", str(cwd))
        if rc != 0:
            raise RuntimeError(f"__sandbox-policy 실패(rc={rc}): {err}")
        doc = json.loads(out)
        val: dict[str, Any] | None = doc.get("policy")
        return val

    pol = cli_policy("workspace-write", repo) or {}
    roots = [real(r) for r in pol.get("writableRoots", [])]
    wt_roots = [real(r) for r in (cli_policy("workspace-write", wt) or {}).get("writableRoots", [])]
    plain_roots = [real(r) for r in ((cli_policy("workspace-write", plain) or {}).get("writableRoots") or [])]
    plan = cli_policy("read-only", repo)

    ok = (pol.get("type") == "workspaceWrite" and roots == [real(repo), real(repo / ".git")]
          and real(wt) in wt_roots and real(repo / ".git") in wt_roots and real(repo / ".git" / "worktrees" / "cx-wt") in wt_roots
          and plain_roots == [real(plain)] and plan is None)
    sent_turn: Any = None
    if impl == "python":
        from workflow_kit.relay.adapters import codex as cx
        from workflow_kit.relay.adapters.base import Handle

        sent: dict[str, Any] = {}
        ad = cx.CodexAdapter()
        ad._request = lambda h, m, params, timeout=60.0: sent.setdefault(m, params) and None  # type: ignore[method-assign]
        h = Handle("codex", None, repo, extra={"turn": None, "sandbox_policy": pol})  # type: ignore[arg-type]
        h.harness_session_id = "t1"
        ad.deliver(h, "hi")
        sent_turn = sent.get("turn/start")
        ok = ok and (sent_turn or {}).get("sandboxPolicy") == pol
    _record(f"{tag}case 11 (Codex 쓰기 루트 — git dir · worktree common dir · plan 없음 · turn/start 에 실림)", ok,
            f"roots={roots} wt={wt_roots} plain={plain_roots} plan={plan} sent={sent_turn}")


def _run_impl(impl: str, cmd_prefix: list[str], tmp: Path) -> None:
    sub = tmp / impl
    sub.mkdir(parents=True, exist_ok=True)
    hub_db = sub / "hub.db"
    hub = Hub(hub_db)
    try:
        try:
            run(impl, cmd_prefix, hub, hub_db, sub)
        except Exception as exc:  # noqa: BLE001 — 예외도 판정으로
            import traceback
            traceback.print_exc()
            _record(f"[{impl}] run (예외)", False, repr(exc))
        try:
            run_codex_roots(impl, cmd_prefix, sub)
        except Exception as exc:  # noqa: BLE001
            import traceback
            traceback.print_exc()
            _record(f"[{impl}] run_codex_roots (예외)", False, repr(exc))
    finally:
        err = hub.stop()
        if _failures:
            print(f"  --- [{impl}] 허브 stderr ---\n" + err[-1500:])


def main() -> int:
    print("=== PC 중계 (M-046 · M-052) ===")
    mode = os.environ.get("WORKFLOW_RELAY_IMPL", "both").strip().lower() or "both"
    if mode not in ("python", "go", "both"):
        print(f"  ✗ 알 수 없는 WORKFLOW_RELAY_IMPL={mode!r} (python · go · both 만 허용)")
        return 2

    py_cmd = [sys.executable, "-m", "workflow_kit", "hub", "relay"]
    with tempfile.TemporaryDirectory(prefix="hubrelay-") as d:
        tmp = Path(d)
        if mode in ("python", "both"):
            _run_impl("python", py_cmd, tmp)
        if mode in ("go", "both"):
            go_cmd, reason = _resolve_go_relay(tmp)
            if go_cmd is None:
                _skips.append(f"go ({reason})")
                print(f"    [unmeasured] go 중계 미측정: {reason}")
            else:
                _run_impl("go", go_cmd, tmp)

    total = len(_passes) + len(_failures)
    print(f"\n{len(_passes)}/{total} passed" + (f" · 미측정 {len(_skips)}" if _skips else ""))
    if _failures:
        for f in _failures:
            print(f"  ✗ {f}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
