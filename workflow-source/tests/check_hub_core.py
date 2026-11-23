#!/usr/bin/env python3
"""허브 코어 (M-033) — 서버 · SQLite · 등록 · 콜사인 · task · 이력 · 원격 MCP 경계를 잰다.

계약 정본: ``core/hub_spec.md`` §2~§4 · 요구 ``docs/planning/workflow-hub-requirements-2026-11.md``.
서버 왕복은 **실제 프로세스 · 실제 포트**로 한다 (hub_spec §8 — 가짜 클라이언트가 머리를 대신 싣지 않게).

1. git 주소 정규화 표 — 같은 저장소의 세 표기 · 대소문자 규칙(DS8) · 거절 (R3.2)
2. 이관 — 새 DB 판 1 · 다시 열면 그대로 · 판이 더 새 DB 거절 · 판 2 적용 전 사본 · 실패한 판은 흔적 없음 (R1.3)
3. 온라인 백업 — 쓰는 중 백업한 사본이 열리고 무결하다 (R1.4)
4. healthz · 응답 머리 · loopback 밖 경고 (R1.6 · R13.3)
5. 등록 · 합류 — 토큰 1회 · DB 에 토큰 원문 없음 · 주소 변형으로 같은 프로젝트 · 409 · 이름 규칙 · 원격 아님 거절 (R3 · R4.1)
6. task — 토큰 없음 401 · 허브 토큰 403 · ID 형식(DS3) · 제목 상한 원인 · done 거절 · 모르는 인자 · 토큰 모양 거절 · 낡은 version 409 (R5)
7. 맡기 — 다른 콜사인 409 · 놓기 권한 (R5.3)
8. 이력 — 쓰기마다 한 줄 · 이전/새 값 · request_id 재전송은 다시 쓰지 않음 (R1.5 · R12.2)
9. MCP 경계 — 토큰 없으면 부트스트랩 묶음만 · 토큰 있으면 전체 · MCP 와 HTTP 가 같은 결과 · MCP 쓰기는 via=mcp (R2.3 · R2.7)
10. 거두기 — 토큰 401 · 맡던 열린 task 비움 (R4.7)
"""

from __future__ import annotations

CHECK_TIMEOUT_S = 240

# `python -m workflow_kit hub` 또는 `workflow-hub` 로 실제 프로세스를 띄운다.
# 구현 스위치 `WORKFLOW_HUB_IMPL` (`python` | `go` | `both`, 기본 `both` — Go 가 있으면 둘 다 잰다).
WATCHES = (
    "workflow-source/workflow_kit/*",
    "workflow-source/pyproject.toml",
    "hub-go/*",
)

import asyncio
import json
import os
import re
import shutil
import socket
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
HUB_GO = REPO_ROOT / "hub-go"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from workflow_kit.hub import db as hubdb  # noqa: E402
from workflow_kit.hub import gitkey  # noqa: E402
from workflow_kit.hub import tools as hubtools  # noqa: E402
from workflow_kit.hub.errors import HubError  # noqa: E402
from workflow_kit.hub.store import Ctx, Store  # noqa: E402

_failures: list[str] = []
_passes: list[str] = []
_skips: list[str] = []


def _record(case: str, ok: bool, detail: str = "") -> None:
    (_passes if ok else _failures).append(case if ok else f"{case}: {detail}")
    print(f"  {case}: {'PASS' if ok else 'FAIL'}{(' — ' + detail) if detail and not ok else ''}")


def _env() -> dict[str, str]:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(SOURCE_ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    return env


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _declared_go_version() -> str | None:
    mod = HUB_GO / "go.mod"
    if not mod.is_file():
        return None
    for raw in mod.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line.startswith("go "):
            return line.split(None, 1)[1].strip()
    return None


def _resolve_go_hub(tmp: Path) -> tuple[list[str] | None, str]:
    explicit = os.environ.get("WORKFLOW_HUB_BIN", "").strip()
    if explicit:
        bin_path = Path(explicit)
        if bin_path.is_file():
            return [str(bin_path)], ""
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
        err_snip = (bproc.stdout + bproc.stderr).strip()[:200]
        return None, f"go build 실패: {err_snip}"
    return [str(out_bin)], ""


class Hub:
    def __init__(self, db: Path, bind: str = "127.0.0.1", extra: tuple[str, ...] = (),
                 cmd_prefix: list[str] | None = None) -> None:
        self.port = _free_port()
        self.base = f"http://127.0.0.1:{self.port}"
        prefix = list(cmd_prefix) if cmd_prefix is not None else [sys.executable, "-m", "workflow_kit", "hub"]
        self.proc = subprocess.Popen(
            [*prefix, "serve", "--db", str(db), "--bind", bind, "--port", str(self.port), *extra],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=_env(), encoding="utf-8", errors="replace",
        )
        deadline = time.time() + 30
        while time.time() < deadline:
            try:
                urllib.request.urlopen(self.base + "/healthz", timeout=1).read()
                return
            except OSError:
                if self.proc.poll() is not None:
                    break
                time.sleep(0.2)
        err = self.stop()
        raise RuntimeError(f"허브가 뜨지 않았다: {err}")

    def stop(self) -> str:
        if self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(10)
            except subprocess.TimeoutExpired:
                self.proc.kill()
        return self.proc.stderr.read() if self.proc.stderr else ""

    def call(self, name: str, args: dict[str, Any] | None = None, token: str | None = None) -> tuple[int, dict[str, Any], Any]:
        req = urllib.request.Request(
            f"{self.base}/v1/tools/{name}", data=json.dumps(args or {}).encode("utf-8"), method="POST",
            headers={"content-type": "application/json", **({"authorization": f"Bearer {token}"} if token else {})},
        )
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                return r.status, json.loads(r.read().decode("utf-8")), r.headers
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read().decode("utf-8")), e.headers


def case_1_gitkey() -> None:
    same = ["git@github.com:Acme/Demo.git", "https://github.com/acme/demo", "ssh://git@github.com:22/Acme/Demo.git/",
            "https://user@GitHub.com/acme//demo.git"]
    keys = {gitkey.normalize(u) for u in same}
    ok1 = keys == {"github.com/acme/demo"}
    ok2 = gitkey.normalize("https://git.example.org/Team/Repo.git") == "git.example.org/Team/Repo"
    ok3 = gitkey.normalize("git@gitlab.com:Grp/Sub/Repo.git") == "gitlab.com/grp/sub/repo"
    bad = []
    for u in ["", "file:///srv/repo.git", "/srv/repo", "./repo", "C:\\work\\repo", "https://github.com/"]:
        try:
            gitkey.normalize(u)
            bad.append(u)
        except HubError as e:
            if e.code != "invalid_remote":
                bad.append(f"{u}:{e.code}")
    _record("case 1 (git 주소 정규화 · 거절)", ok1 and ok2 and ok3 and not bad,
            f"keys={keys} case={ok2} sub={ok3} 거절 안 됨={bad}")


def case_2_migration(tmp: Path) -> None:
    db = tmp / "m.db"
    c1 = hubdb.open_db(db, now=_now())
    c2 = hubdb.open_db(db, now=_now())
    conn = hubdb.connect(db)
    v = hubdb.schema_version(conn)
    conn.close()
    ok_fresh = v == hubdb.latest_version() and c1 == [] and c2 == []
    # 판이 더 새 DB
    newer = tmp / "newer.db"
    hubdb.open_db(newer, now=_now())
    conn = hubdb.connect(newer)
    conn.execute("UPDATE meta SET value = '99' WHERE key = 'schema_version'")
    conn.close()
    try:
        hubdb.open_db(newer, now=_now())
        ok_newer = False
    except HubError as e:
        ok_newer = e.code == "db_newer_than_hub"
    # 판 2 — 적용 전 사본 · 실패한 판은 흔적 없음
    saved = list(hubdb.MIGRATIONS)
    try:
        hubdb.MIGRATIONS.append("CREATE TABLE probe_ok (x INTEGER);")
        copies = hubdb.open_db(db, now=_now())
        conn = hubdb.connect(db)
        ok_v2 = (hubdb.schema_version(conn) == len(saved) + 1 and len(copies) == 1 and copies[0].exists()
                 and conn.execute("SELECT 1 FROM sqlite_master WHERE name = 'probe_ok'").fetchone() is not None)
        conn.close()
        hubdb.MIGRATIONS.append("CREATE TABLE probe_half (x INTEGER); THIS IS NOT SQL;")
        try:
            hubdb.open_db(db, now=_now())
            ok_atomic = False
        except sqlite3.Error:
            conn = hubdb.connect(db)
            ok_atomic = (hubdb.schema_version(conn) == len(saved) + 1
                         and conn.execute("SELECT 1 FROM sqlite_master WHERE name = 'probe_half'").fetchone() is None)
            conn.close()
    finally:
        hubdb.MIGRATIONS[:] = saved
    _record("case 2 (이관 · 사본 · 더 새 DB 거절 · 원자성)", ok_fresh and ok_newer and ok_v2 and ok_atomic,
            f"fresh={ok_fresh} newer={ok_newer} v2={ok_v2} atomic={ok_atomic}")


def case_3_backup(tmp: Path, impl: str, cmd_prefix: list[str]) -> None:
    sub = tmp / f"bk-{impl}"
    sub.mkdir(parents=True, exist_ok=True)
    db = sub / "b.db"
    hubdb.open_db(db, now=_now())
    store = Store(db)
    reg = store.register_project(Ctx(now=_now(), via="test"), "https://github.com/acme/bk", "bk", "agent-a", "agent")
    principal = store.authenticate(reg["token"])
    stop = threading.Event()
    errors: list[str] = []

    def writer() -> None:
        i = 0
        while not stop.is_set():
            try:
                store.task_create(Ctx(now=_now(), via="test", principal=principal), {"title": f"t{i}"})
            except Exception as exc:  # noqa: BLE001
                errors.append(repr(exc))
            i += 1

    t = threading.Thread(target=writer)
    t.start()
    time.sleep(0.3)
    out = sub / "b.copy.db"
    bk_ok = True
    if impl == "python":
        hubdb.backup(db, out)
    else:
        proc = subprocess.run([*cmd_prefix, "backup", "--db", str(db), "--out", str(out)],
                              capture_output=True, encoding="utf-8", env=_env(), timeout=60)
        bk_ok = proc.returncode == 0
        if not bk_ok:
            errors.append(f"backup rc={proc.returncode} err={(proc.stderr or proc.stdout)[:200]}")
    stop.set()
    t.join()
    conn = sqlite3.connect(str(out))
    integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
    rows = conn.execute("SELECT COUNT(*) FROM task").fetchone()[0]
    conn.close()
    _record(f"case 3 (쓰는 중 온라인 백업) [{impl}]", bk_ok and integrity == "ok" and rows > 0 and not errors,
            f"integrity={integrity} rows={rows} errors={errors[:2]}")


def _mcp_session(base: str, token: str | None, calls: list[tuple[str, dict[str, Any]]]) -> tuple[list[str], list[Any]]:
    from mcp import ClientSession
    from mcp.client.streamable_http import streamable_http_client

    # SDK 1.x/2.x 클라이언트 차이 (TASK-2026-11-22-main-022): 2.x 는 `streamablehttp_client(headers=)` 를 없애고
    # `streamable_http_client(http_client=)` 만 남겼다 — HTTP 클라이언트는 2.x 가 `httpx2`, 1.x 가 `httpx`.
    # 스트림도 1.x 는 (read, write, session_id), 2.x 는 (read, write) 라 앞의 둘만 쓴다.
    try:
        import httpx2 as _httpx  # type: ignore[import-not-found, unused-ignore]
    except ImportError:
        import httpx as _httpx

    async def go() -> tuple[list[str], list[Any]]:
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        async with _httpx.AsyncClient(headers=headers) as http, \
                streamable_http_client(base + "/mcp", http_client=http) as streams:
            r, w = streams[0], streams[1]
            async with ClientSession(r, w) as s:
                await s.initialize()
                names = sorted(t.name for t in (await s.list_tools()).tools)
                results = []
                for name, args in calls:
                    res = await s.call_tool(name, args)
                    # SDK 1.x/2.x 필드 이름 차이를 getattr 로 둘 다 읽는다 (check_mcp_lowlevel_sdk_compat)
                    is_error = getattr(res, "isError", None)
                    if is_error is None:
                        is_error = getattr(res, "is_error", None)
                    structured = getattr(res, "structuredContent", None)
                    if structured is None:
                        structured = getattr(res, "structured_content", None)
                    results.append((is_error, structured))
                return names, results

    return asyncio.run(go())


def case_4_to_10(tmp: Path, impl: str, cmd_prefix: list[str]) -> None:
    sub = tmp / f"core-{impl}"
    sub.mkdir(parents=True, exist_ok=True)
    db = sub / "e2e.db"
    hub = Hub(db, cmd_prefix=cmd_prefix)
    try:
        r = urllib.request.urlopen(hub.base + "/healthz", timeout=5)
        health = json.loads(r.read().decode("utf-8"))
        ok4 = (health.get("ok") is True and health.get("contract") == "hub/1" and health.get("db_version") == hubdb.latest_version()
               and r.headers.get("X-Hub-Contract") == "hub/1" and r.headers.get("X-Hub-Kit") and health.get("exposure") == "loopback")
        wild = Hub(sub / "wild.db", bind="0.0.0.0", cmd_prefix=cmd_prefix)
        warn = wild.stop()
        ok4b = "loopback 이 아닌" in warn and "누구나 프로젝트를 등록" in warn
        _record(f"case 4 (healthz · 머리 · loopback 밖 경고) [{impl}]", ok4 and ok4b, f"health={health} warn={warn[:120]!r}")

        # 5 등록 · 합류
        st, reg, _ = hub.call("hub_project_register", {"remote_url": "git@github.com:Acme/Demo.git", "display_name": "Demo",
                                                         "callsign": "claude-a", "kind": "human"})
        tok_a = reg.get("token", "")
        st2, look, _ = hub.call("hub_project_lookup", {"remote_url": "https://github.com/acme/demo"})
        st3, dup, _ = hub.call("hub_project_register", {"remote_url": "ssh://git@github.com/acme/demo", "display_name": "x",
                                                          "callsign": "other-x", "kind": "agent"})
        pid = reg.get("project_id")
        st4, join, _ = hub.call("hub_callsign_register", {"project_id": pid, "callsign": "codex-b", "kind": "human"})
        tok_b = join.get("token", "")
        st5, taken, _ = hub.call("hub_callsign_register", {"project_id": pid, "callsign": "codex-b", "kind": "agent"})
        st6, badname, _ = hub.call("hub_callsign_register", {"project_id": pid, "callsign": "Bad_Name", "kind": "agent"})
        st7, reserved, _ = hub.call("hub_callsign_register", {"project_id": pid, "callsign": "hub", "kind": "agent"})
        st8, local, _ = hub.call("hub_project_register", {"remote_url": "/srv/repo", "display_name": "x", "callsign": "aa-b", "kind": "agent"})
        raw = db.read_bytes() + (db.with_name(db.name + "-wal").read_bytes() if db.with_name(db.name + "-wal").exists() else b"")
        ok5 = (st == 200 and tok_a.startswith("wfh_") and reg.get("role") == "owner" and look.get("project_id") == pid
               and st3 == 409 and dup.get("error_code") == "project_exists"
               and st4 == 200 and join.get("role") == "editor" and join.get("human_pending") is True
               and st5 == 409 and taken.get("error_code") == "callsign_taken"
               and st6 == 400 and badname.get("error_code") == "invalid_field"
               and st7 == 400 and reserved.get("error_code") == "invalid_field"
               and st8 == 400 and local.get("error_code") == "invalid_remote"
               and tok_a.encode() not in raw and tok_b.encode() not in raw)
        _record(f"case 5 (등록 · 합류 · 토큰 원문 미저장) [{impl}]", ok5,
                f"{st} {st2} {st3}/{dup.get('error_code')} {st4} {st5} {st6} {st7} {st8} 원문저장={tok_a.encode() in raw}")

        # 6 task
        today = _now().strftime("%Y-%m-%d")
        s0, noauth, _ = hub.call("hub_task_create", {"title": "x"})
        adm = subprocess.run([*cmd_prefix, "admin", "--db", str(db), "token", "issue",
                              "--role", "admin", "--name", "ops"], capture_output=True, encoding="utf-8", env=_env(), timeout=60)
        adm_tok = json.loads(adm.stdout).get("token", "")
        s1, admin_try, _ = hub.call("hub_task_create", {"title": "x"}, adm_tok)
        s2, t1, _ = hub.call("hub_task_create", {"title": "첫 task", "plan_md": "- C1 주장"}, tok_a)
        s3, t2, _ = hub.call("hub_task_create", {"title": "둘째"}, tok_a)
        s4, long, _ = hub.call("hub_task_create", {"title": "가" * 201}, tok_a)
        s5, done, _ = hub.call("hub_task_create", {"title": "x", "status": "done"}, tok_a)
        s6, unk, _ = hub.call("hub_task_create", {"title": "x", "bogus": 1}, tok_a)
        s7, sec, _ = hub.call("hub_task_create", {"title": "x", "description": f"토큰 {tok_a}"}, tok_a)
        id1 = t1.get("task", {}).get("id")
        s8, upd, _ = hub.call("hub_task_update", {"id": id1, "expected_version": 1, "values": {"title": "고친 제목"}}, tok_a)
        s9, stale, _ = hub.call("hub_task_update", {"id": id1, "expected_version": 1, "values": {"title": "낡은"}}, tok_b)
        _, listing, _ = hub.call("hub_task_list", {}, tok_a)
        ok6 = (s0 == 401 and s1 == 403 and s2 == 200 and id1 == f"TASK-{today}-claude-a-001"
               and t2.get("task", {}).get("id") == f"TASK-{today}-claude-a-002"
               and s4 == 400 and long.get("error_code") == "invalid_field" and "200" in long.get("message", "")
               and s5 == 422 and done.get("error_code") == "gate_denied"
               and s6 == 400 and unk.get("error_code") == "unknown_field"
               and s7 == 400 and sec.get("error_code") == "secret_in_payload"
               and len(listing.get("tasks", [])) == 2
               and s8 == 200 and upd["task"]["version"] == 2
               and s9 == 409 and stale.get("error_code") == "version_conflict" and stale["detail"].get("current_version") == 2)
        _record(f"case 6 (task 생성 · 검증 · 409) [{impl}]", ok6,
                f"{s0} {s1} {s2} id={id1} {s4}/{long.get('message','')[:40]} {s5} {s6} {s7} tasks={len(listing.get('tasks', []))} {s8} {s9}")

        # 7 맡기
        c1, claim_a, _ = hub.call("hub_task_claim", {"id": id1}, tok_a)
        c2, clash, _ = hub.call("hub_task_claim", {"id": id1}, tok_b)
        c3, rel_b, _ = hub.call("hub_task_release", {"id": id1}, tok_b)
        c4, _, _ = hub.call("hub_task_release", {"id": id1}, tok_a)
        c5, claim_b, _ = hub.call("hub_task_claim", {"id": id1}, tok_b)
        ok7 = (c1 == 200 and c2 == 409 and clash.get("error_code") == "already_claimed" and c3 == 403
               and c4 == 200 and c5 == 200 and claim_b["task"]["assignee"] == "codex-b"
               # 맡는 순간 시작 — planned → in_progress, 놓아도 되돌리지 않는다 (소유자 2026-11-21)
               and claim_a["task"]["status"] == "in_progress" and claim_b["task"]["status"] == "in_progress")
        _record(f"case 7 (맡기 409 · 놓기 권한) [{impl}]", ok7, f"{c1} {c2} {c3} {c4} {c5}")

        # 8 이력 · request_id
        p1, prog, _ = hub.call("hub_task_progress", {"id": id1, "note": "구현 중", "request_id": "r-1"}, tok_b)
        _, ev_before, _ = hub.call("hub_events", {"target_kind": "task", "target_id": id1}, tok_a)
        p2, again, _ = hub.call("hub_task_progress", {"id": id1, "note": "구현 중", "request_id": "r-1"}, tok_b)
        _, ev_after, _ = hub.call("hub_events", {"target_kind": "task", "target_id": id1}, tok_a)
        ops = [e["op"] for e in ev_after.get("events", [])]
        upd_ev = next((e for e in ev_after.get("events", []) if e["op"] == "update"), {})
        ok8 = (p1 == 200 and p2 == 200 and again.get("replayed") is True
               and len(ev_before["events"]) == len(ev_after["events"])
               and ops == ["create", "update", "claim", "release", "claim", "progress"]
               and upd_ev.get("before", {}).get("title") == "첫 task" and upd_ev.get("after", {}).get("title") == "고친 제목"
               and upd_ev.get("callsign") == "claude-a" and upd_ev.get("via") == "http"
               and prog["task"]["progress_note"].endswith("구현 중"))
        _record(f"case 8 (이력 · request_id 멱등) [{impl}]", ok8, f"ops={ops} replayed={again.get('replayed')} upd={upd_ev}")

        # 9 MCP 경계
        boot = sorted(t.name for t in hubtools.visible_tools(False))
        full = sorted(hubtools.TOOLS)
        names_anon, res_anon = _mcp_session(hub.base, None, [("hub_task_list", {})])
        names_auth, res_auth = _mcp_session(hub.base, tok_a, [("hub_task_list", {}), ("hub_task_progress", {"id": id1, "note": "mcp 로"})])
        _, http_list, _ = hub.call("hub_task_list", {}, tok_a)
        mcp_list = res_auth[0][1]
        _, ev_mcp, _ = hub.call("hub_events", {"target_kind": "task", "target_id": id1}, tok_a)
        last = ev_mcp["events"][-1] if ev_mcp.get("events") else {}
        ok9 = (names_anon == boot and 0 < len(boot) < len(full) and all(hubtools.TOOLS[n].bundle == "bootstrap" for n in names_anon)
               and res_anon[0][0] is True
               and (res_anon[0][1] or {}).get("error_code") == "unauthorized"
               and names_auth == full
               and [t["id"] for t in mcp_list["tasks"]] == [t["id"] for t in http_list["tasks"]]
               and last.get("via") == "mcp" and last.get("op") == "progress" and last.get("callsign") == "claude-a")
        _record(f"case 9 (MCP 인증 경계 · HTTP 와 같은 결과) [{impl}]", ok9,
                f"anon={names_anon} auth={len(names_auth)}/{len(full)} anon_res={res_anon} last={last.get('via')}/{last.get('op')}")

        # 10 거두기
        rv = subprocess.run([*cmd_prefix, "admin", "--db", str(db), "callsign", "revoke",
                             "--project", pid, "--callsign", "codex-b"], capture_output=True, encoding="utf-8", env=_env(), timeout=60)
        out = json.loads(rv.stdout or "{}")
        r1, gone, _ = hub.call("hub_whoami", {}, tok_b)
        _, after, _ = hub.call("hub_task_get", {"id": id1}, tok_a)
        ok10 = (rv.returncode == 0 and out.get("released_tasks") == [id1] and r1 == 401
                and after["task"]["assignee"] is None)
        _record(f"case 10 (거두기 — 토큰 무효 · 맡던 task 비움) [{impl}]", ok10, f"rc={rv.returncode} out={out} whoami={r1}")
    finally:
        err = hub.stop()
        if _failures:
            print(f"  --- [{impl}] 허브 stderr ---\n" + err[-2000:])


def main() -> int:
    print("=== 허브 코어 (M-033 · M-055) ===")
    mode = os.environ.get("WORKFLOW_HUB_IMPL", "both").strip().lower() or "both"
    if mode not in ("python", "go", "both"):
        print(f"  ✗ 알 수 없는 WORKFLOW_HUB_IMPL={mode!r} (python · go · both 만 허용)")
        return 2

    py_cmd = [sys.executable, "-m", "workflow_kit", "hub"]
    with tempfile.TemporaryDirectory(prefix="hubcore-") as d:
        tmp = Path(d)
        case_1_gitkey()
        case_2_migration(tmp)
        if mode in ("python", "both"):
            case_3_backup(tmp, "python", py_cmd)
            case_4_to_10(tmp, "python", py_cmd)
        if mode in ("go", "both"):
            go_cmd, reason = _resolve_go_hub(tmp)
            if go_cmd is None:
                _skips.append(f"go ({reason})")
                print(f"    [unmeasured] go 허브 미측정: {reason}")
            else:
                case_3_backup(tmp, "go", go_cmd)
                case_4_to_10(tmp, "go", go_cmd)
    total = len(_passes) + len(_failures)
    print(f"\n{len(_passes)}/{total} passed" + (f" · 미측정 {len(_skips)}" if _skips else ""))
    if _failures:
        for f in _failures:
            print(f"  ✗ {f}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
