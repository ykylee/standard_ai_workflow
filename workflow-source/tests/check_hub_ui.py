#!/usr/bin/env python3
"""허브 화면 (M-037 WBS-37.1) — 인증 · 화면 머리 · 읽기 범위 · 결정 답 권한.

정본: ``core/hub_spec.md`` §4.6 · §4.7 (요구 R13.2 · R13.2a · R13.4 · R4.6 · R5.8 · R5.10, 소유자 2026-11-21
'결정 답은 승인된 human 만'). 실제 허브 프로세스를 띄워 HTTP 로 잰다. 실브라우저 왕복은 게이트가 아니라
task Proof 의 CDP 실측이다 (워크벤치 선례 — 게이트는 브라우저를 띄우지 않는다).

1. 공용 토큰 꺼짐 — 토큰 없는 /api 읽기 · 등록 401, 정적 화면은 200 + CSP(script-src 'self') · Referrer-Policy
2. 상대 경로 — HTML · JS 의 링크 · 스크립트 · fetch 가 '/' 로 시작하지 않고, /ui 리다이렉트도 상대
3. 공용 토큰 켜짐 — 읽기 200 · 결정 답 403 · 등록 200(토큰 1회, 해시만 저장) · 같은 이름 409 · 거두면 401 ·
   없는 이름으로 serve 거절
4. 읽기 범위 — 콜사인 토큰은 자기 프로젝트만 (목록 1개 · 남의 프로젝트 403), task 상세에 계획 · 결정 상태 · 이력
5. 결정 답 권한 — agent · 승인 전 human 403 (화면 · MCP 둘 다), 남의 이름 responder 403, 승인은 소유자만,
   승인된 human 의 화면 답 → 반영 · 이력에 콜사인 이름 · 경로 ui
6. 위조 방지 — application/json 아닌 POST 415 · 쓰기 0, 낡은 계획 지문 409, 선택지 밖 값 400
7. 콜사인 표 (WBS-37.2) — 맡은 열린 task 와 진행 한 줄 · 마지막 활동 · 클라이언트 판(X-Hub-Client) · 거둔 콜사인은 보관,
   콜사인 화면의 handoff 는 다른 콜사인도 읽고(G3) 남의 프로젝트는 403
8. 받은 지침 판 (R7.8) — 진입 파일을 다시 렌더하고 세션 시작에서 그 판을 재면 '최신', 지침 새 판 뒤 '옛 지침',
   진입 파일 판이 섞이면 기록을 바꾸지 않는다
9. 화면 승인 — agent · 승인 전 human 403, 소유자 200 → 그 human 의 can_answer true
10. 지침 제안 (WBS-37.3 · R7.7 · D11) — agent · 승인 전 human 의 변경은 판 불변 · 제안 1, 승인된 human 의 변경은 판 +1,
    사람 승인 → 판 +1 · 거절 → 판 불변, agent 의 승인 403 · web 쓰기 403, 화면 · MCP 같은 함수
11. 지침 판 지키기 — 낡은 base 의 제안 · 승인 409, 렌더 예산을 넘는 본문은 판을 올리기 전 422 (admin guide set 도)
12. 위키 읽기 — 목록 · 검색 · 페이지 · 생성물 index.md 를 web 공용 토큰 · 콜사인 토큰으로, 남의 프로젝트 403
"""

from __future__ import annotations

CHECK_TIMEOUT_S = 240

WATCHES = (
    "workflow-source/workflow_kit/*",
    "workflow-source/pyproject.toml",
    "workflow-source/tests/check_hub_core.py",
)

import json
import re
import sqlite3
import subprocess
import sys
import tempfile
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
from workflow_kit.common import plan_claims, plan_responses  # noqa: E402

STATIC = SOURCE_ROOT / "workflow_kit" / "hub" / "static"

_failures: list[str] = []
_passes: list[str] = []

PLAN = (
    "- Claims: C1 화면에서 결정에 답한다\n"
    "- Decisions: D1 [C1] 어느 저장소? | default: sqlite | options: sqlite = 파일 하나; pg = 서버 | state: proposed\n"
)


def _record(case: str, ok: bool, detail: str = "") -> None:
    (_passes if ok else _failures).append(case if ok else f"{case}: {detail}")
    print(f"  {case}: {'PASS' if ok else 'FAIL'}{(' — ' + detail) if detail and not ok else ''}")


def _req(base: str, path: str, *, token: str | None = None, method: str = "GET", body: Any = None,
         ctype: str = "application/json", raw: bytes | None = None, follow: bool = True) -> tuple[int, Any, Any]:
    headers = {}
    if token:
        headers["authorization"] = f"Bearer {token}"
    data = raw
    if body is not None:
        data = json.dumps(body).encode("utf-8")
    if data is not None:
        headers["content-type"] = ctype

    class _NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *a: Any, **k: Any) -> None:
            return None

    opener = urllib.request.build_opener() if follow else urllib.request.build_opener(_NoRedirect)
    req = urllib.request.Request(base + path, data=data, method=method, headers=headers)
    try:
        with opener.open(req, timeout=20) as r:
            text = r.read().decode("utf-8")
            return r.status, (json.loads(text) if "json" in (r.headers.get("content-type") or "") else text), r.headers
    except urllib.error.HTTPError as e:
        text = e.read().decode("utf-8")
        try:
            return e.code, json.loads(text), e.headers
        except json.JSONDecodeError:
            return e.code, text, e.headers


def _admin(db: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, "-m", "workflow_kit", "hub", "admin", "--db", str(db), *args],
                          capture_output=True, encoding="utf-8", env=_env(), timeout=60)


def _project(hub: Hub, name: str, callsign: str = "owner-a") -> tuple[str, str]:
    st, reg, _ = hub.call("hub_project_register", {"remote_url": f"git@github.com:acme/{name}.git", "display_name": name,
                                                     "callsign": callsign, "kind": "human"})
    assert st == 200, reg
    return reg["project_id"], reg["token"]


def _task(hub: Hub, tok: str) -> str:
    st, out, _ = hub.call("hub_task_create", {"title": "결정 있는 task", "plan_md": PLAN,
                                                "fields": {"done_criteria": ["[C1] 답이 반영된다"]}}, tok)
    assert st == 200, out
    return str(out["task"]["id"])


def _event_count(db: Path) -> int:
    with sqlite3.connect(db) as conn:
        return int(conn.execute("SELECT COUNT(*) FROM event").fetchone()[0])


def case_1_2_off(tmp: Path) -> None:
    db = tmp / "off.db"
    hub = Hub(db)
    try:
        pid, _tok = _project(hub, "off")
        s1, _, _ = _req(hub.base, "/api/projects")
        s2, _, _ = _req(hub.base, f"/api/projects/{pid}/tasks")
        s3, _, _ = _req(hub.base, f"/api/projects/{pid}/callsigns", method="POST",
                        body={"callsign": "web-x", "kind": "human"})
        s4, html, h4 = _req(hub.base, "/ui/")
        s5, js, h5 = _req(hub.base, "/ui/hub.js")
        s6, _, h6 = _req(hub.base, "/ui", follow=False)
        csp = h4.get("content-security-policy") or ""
        ok1 = (s1 == s2 == s3 == 401 and s4 == 200 and s5 == 200 and "script-src 'self'" in csp
               and "unsafe-inline" not in csp and "frame-ancestors 'none'" in csp
               and h4.get("referrer-policy") == "same-origin" and "script-src 'self'" in (h5.get("content-security-policy") or ""))
        _record("case 1 (공용 토큰 꺼짐 — 토큰 없는 읽기 · 등록 401, 화면 머리 CSP)", ok1,
                f"{s1} {s2} {s3} {s4} {s5} csp={csp!r}")

        # 2 상대 경로 — 화면이 내리는 HTML · JS 의 주소가 '/' 로 시작하지 않는다 (R13.4).
        src_html = (STATIC / "index.html").read_text(encoding="utf-8")
        src_js = (STATIC / "hub.js").read_text(encoding="utf-8")
        abs_attr = re.findall(r'(?:href|src|action)="(/[^"]*)"', html + src_html)
        abs_fetch = re.findall(r'fetch\(\s*["\'`](/[^"\'`]*)', js + src_js)
        inline = re.findall(r"<script(?![^>]*\bsrc=)[^>]*>", html) + re.findall(r'\son[a-z]+="', html)
        loc = h6.get("location") or ""
        ok2 = (not abs_attr and not abs_fetch and not inline and "../api/" in js and s6 == 307 and loc == "ui/")
        _record("case 2 (상대 경로 — 링크 · 스크립트 · fetch · 리다이렉트, 인라인 스크립트 없음)", ok2,
                f"abs_attr={abs_attr} abs_fetch={abs_fetch} inline={inline} redirect={s6} {loc!r}")
    finally:
        hub.stop()


def case_3_web_on(tmp: Path) -> None:
    db = tmp / "on.db"
    # 없는 이름으로는 뜨지 않는다.
    Hub(db).stop()
    bad = subprocess.run([sys.executable, "-m", "workflow_kit", "hub", "serve", "--db", str(db), "--port", "1",
                          "--web-token-name", "nope"], capture_output=True, encoding="utf-8", env=_env(), timeout=60)
    issued = _admin(db, "token", "issue", "--role", "web", "--name", "screen")
    hub = Hub(db, extra=("--web-token-name", "screen"))
    try:
        pid, tok = _project(hub, "on")
        tid = _task(hub, tok)
        s1, projects, _ = _req(hub.base, "/api/projects")
        s2, tasks, _ = _req(hub.base, f"/api/projects/{pid}/tasks")
        s3, detail, _ = _req(hub.base, f"/api/projects/{pid}/tasks/{tid}")
        digest = detail.get("plan", {}).get("digest") if isinstance(detail, dict) else None
        s4, deny, _ = _req(hub.base, f"/api/projects/{pid}/tasks/{tid}/responses", method="POST",
                           body={"plan_digest": digest, "values": {"D1": "pg"}})
        s5, reg, _ = _req(hub.base, f"/api/projects/{pid}/callsigns", method="POST",
                          body={"callsign": "yk-web", "kind": "human", "label": "브라우저"})
        s6, dup, _ = _req(hub.base, f"/api/projects/{pid}/callsigns", method="POST",
                          body={"callsign": "yk-web", "kind": "human"})
        token = reg.get("token", "") if isinstance(reg, dict) else ""
        raw_db = db.read_bytes()
        s7, me, _ = _req(hub.base, "/api/session", token=token)
        _admin(db, "token", "revoke", "--name", "screen")
        s8, _, _ = _req(hub.base, "/api/projects")
        ok = (bad.returncode == 2 and issued.returncode == 0
              and s1 == 200 and [p["id"] for p in projects["projects"]] == [pid] and projects["principal"]["kind"] == "web"
              and s2 == 200 and len(tasks["tasks"]) == 1 and s3 == 200
              and s4 == 403 and deny.get("error_code") == "forbidden"
              and s5 == 200 and token.startswith("wfh_") and token.encode() not in raw_db and reg.get("human_pending") is True
              and s6 == 409 and dup.get("error_code") == "callsign_taken"
              and s7 == 200 and me["principal"]["callsign"] == "yk-web" and s8 == 401)
        _record("case 3 (공용 토큰 켜짐 — 읽기 200 · 답 403 · 등록 1회 토큰 · 409 · 거두면 401 · 없는 이름 거절)", ok,
                f"bad={bad.returncode} {s1} {s2} {s3} {s4}/{deny} {s5} {s6} {s7} {s8}")
    finally:
        hub.stop()


def case_4_5_6(tmp: Path) -> None:
    db = tmp / "scope.db"
    hub = Hub(db)
    try:
        pid, owner = _project(hub, "alpha")
        pid_b, owner_b = _project(hub, "beta", "owner-b")
        tid = _task(hub, owner)
        _, agent_reg, _ = hub.call("hub_callsign_register", {"project_id": pid, "callsign": "bot-a", "kind": "agent"})
        _, human_reg, _ = hub.call("hub_callsign_register", {"project_id": pid, "callsign": "yk-b", "kind": "human"})
        agent, human = agent_reg["token"], human_reg["token"]

        # 4 읽기 범위
        s1, mine, _ = _req(hub.base, "/api/projects", token=owner)
        s2, other, _ = _req(hub.base, f"/api/projects/{pid_b}/tasks", token=owner)
        s3, detail, _ = _req(hub.base, f"/api/projects/{pid}/tasks/{tid}", token=agent)
        s4, evs, _ = _req(hub.base, f"/api/projects/{pid}/events", token=owner_b)
        plan = detail["plan"]
        ok4 = (s1 == 200 and [p["id"] for p in mine["projects"]] == [pid] and s2 == 403 and s4 == 403
               and s3 == 200 and plan["open_decisions"] == ["D1"] and plan["decisions"][0]["options"][1][0] == "pg"
               and any(e["op"] == "create" for e in detail["events"]) and detail["task"]["plan_md"] == PLAN)
        _record("case 4 (읽기 범위 — 콜사인 토큰은 자기 프로젝트만, 상세에 계획 · 결정 · 이력)", ok4,
                f"{s1} {s2} {s3} {s4} open={plan.get('open_decisions')}")

        # 5 결정 답 권한
        path = f"/api/projects/{pid}/tasks/{tid}/responses"
        form = {"plan_digest": plan["digest"], "values": {"D1": "pg"}, "opened": {"D1": True}}
        a1, _, _ = _req(hub.base, path, token=agent, method="POST", body=form)
        a2, _, _ = _req(hub.base, path, token=human, method="POST", body=form)
        parsed_plan = plan_claims.parse_plan(PLAN.splitlines() + ["- Completion criteria: [C1] 답이 반영된다"])

        def body(responder: str) -> str:
            return plan_responses.render_response(task_id=tid, plan=parsed_plan, responder=responder,
                                                  received_at="2026-11-21T09:00:00+09:00", values={"D1": "pg"})

        m1, _, _ = hub.call("hub_plan_respond", {"task_id": tid, "body": body("bot-a")}, agent)
        m2, forged, _ = hub.call("hub_plan_respond", {"task_id": tid, "body": body("yk-b")}, owner)
        p1, _, _ = hub.call("hub_callsign_approve", {"callsign": "yk-b"}, agent)
        p2, appr, _ = hub.call("hub_callsign_approve", {"callsign": "yk-b"}, owner)
        b1, me, _ = _req(hub.base, f"/api/projects/{pid}", token=human)
        a3, done, _ = _req(hub.base, path, token=human, method="POST", body=form)
        _, after, _ = _req(hub.base, f"/api/projects/{pid}/tasks/{tid}", token=owner)
        resp_events = [e for e in after["events"] if e["op"] == "plan_response"]
        ok5 = (a1 == a2 == m1 == m2 == p1 == 403 and forged.get("detail", {}).get("field") == "responder"
               and p2 == 200 and appr.get("changed") is True and b1 == 200 and me["principal"]["can_answer"] is True
               and a3 == 200 and done.get("accepted") is True and after["plan"]["open_decisions"] == []
               and len(resp_events) == 1 and resp_events[0]["callsign"] == "yk-b" and resp_events[0]["via"] == "ui"
               and resp_events[0]["after"]["responder"] == "yk-b")
        _record("case 5 (결정 답 — 승인된 human 만 · responder = 그 콜사인 · 승인은 소유자 · 이력에 이름)", ok5,
                f"agent={a1} pending={a2} mcp_agent={m1} forged={m2} approve_by_agent={p1} approve={p2} "
                f"answer={a3}/{done} events={resp_events}")

        # 6 위조 방지 · 입력
        tid2 = _task(hub, owner)
        _, d2, _ = _req(hub.base, f"/api/projects/{pid}/tasks/{tid2}", token=owner)
        before = _event_count(db)
        f1, _, _ = _req(hub.base, f"/api/projects/{pid}/tasks/{tid2}/responses", token=owner, method="POST",
                        raw=json.dumps({"plan_digest": d2["plan"]["digest"], "values": {"D1": "pg"}}).encode(),
                        ctype="text/plain")
        f2, _, _ = _req(hub.base, f"/api/projects/{pid}/callsigns", method="POST",
                        raw=b'{"callsign":"csrf-x","kind":"agent","a":"=1"}', ctype="text/plain")
        written = _event_count(db) - before
        f3, stale, _ = _req(hub.base, f"/api/projects/{pid}/tasks/{tid2}/responses", token=owner, method="POST",
                            body={"plan_digest": "0" * 64, "values": {"D1": "pg"}})
        f4, badv, _ = _req(hub.base, f"/api/projects/{pid}/tasks/{tid2}/responses", token=owner, method="POST",
                           body={"plan_digest": d2["plan"]["digest"], "values": {"D1": "mysql"}})
        ok6 = (f1 == 415 and f2 in (401, 415) and written == 0 and f3 == 409 and stale.get("error_code") == "version_conflict"
               and f4 == 400 and badv.get("detail", {}).get("field") == "values.D1")
        _record("case 6 (위조 방지 — text/plain POST 415 · 쓰기 0, 낡은 지문 409, 선택지 밖 400)", ok6,
                f"{f1} {f2} written={written} {f3} {f4}/{badv}")
    finally:
        hub.stop()


def _tool(base: str, name: str, args: dict[str, Any], token: str, client: str | None = None) -> tuple[int, Any]:
    headers = {"content-type": "application/json", "authorization": f"Bearer {token}"}
    if client:
        headers["x-hub-client"] = client
    req = urllib.request.Request(f"{base}/v1/tools/{name}", data=json.dumps(args).encode(), method="POST", headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status, json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode("utf-8"))


def case_7_8_9(tmp: Path) -> None:
    db = tmp / "board.db"
    hub = Hub(db)
    try:
        pid, owner = _project(hub, "board")
        _, owner_b = _project(hub, "other", "owner-b")
        regs = {cs: hub.call("hub_callsign_register", {"project_id": pid, "callsign": cs, "kind": kind})[1]["token"]
                for cs, kind in (("bot-a", "agent"), ("yk-c", "human"), ("old-d", "agent"))}
        bot = regs["bot-a"]
        tid = _task(hub, owner)
        hub.call("hub_task_claim", {"id": tid}, bot)
        hub.call("hub_task_progress", {"id": tid, "note": "화면 표를 만든다"}, bot)
        c1, _ = _tool(hub.base, "hub_handoff_put", {"handoff": {"baseline": "기준선 X", "in_progress": [tid],
                                                                 "next": ["다음은 Y"]}}, bot, client="hub-client/9.9")
        rv = _admin(db, "callsign", "revoke", "--project", pid, "--callsign", "old-d")
        s1, board, _ = _req(hub.base, f"/api/projects/{pid}/callsigns", token=regs["yk-c"])
        rows = {c["id"]: c for c in board.get("callsigns", [])} if isinstance(board, dict) else {}
        b = rows.get("bot-a", {})
        s2, one, _ = _req(hub.base, f"/api/projects/{pid}/callsigns/bot-a", token=regs["yk-c"])
        s3, _, _ = _req(hub.base, f"/api/projects/{pid}/callsigns/bot-a", token=owner_b)
        s4, _, _ = _req(hub.base, f"/api/projects/{pid}/callsigns", token=owner_b)
        s5, nobody, _ = _req(hub.base, f"/api/projects/{pid}/callsigns/nobody", token=owner)
        ok7 = (c1 == 200 and rv.returncode == 0 and s1 == 200 and set(rows) == {"owner-a", "bot-a", "yk-c", "old-d"}
               and [t["id"] for t in b.get("open_tasks", [])] == [tid] and b["open_tasks"][0]["progress_note"].endswith("화면 표를 만든다")
               and b.get("last_seen_at") and b.get("client_version_seen") == "hub-client/9.9"
               and rows["old-d"]["archived"] is True and rows["yk-c"]["human_approved"] is False
               and all(r["guide_state"] == "never" for r in rows.values())
               and s2 == 200 and one["handoff"]["handoff"]["baseline"] == "기준선 X" and one["handoff"]["version"] == 1
               and one["callsign"]["handoff_updated_at"] and s3 == 403 and s4 == 403 and s5 == 404)
        _record("case 7 (콜사인 표 — 지금 하는 일 · 마지막 활동 · 클라이언트 판 · 보관 · handoff 읽기)", ok7,
                f"{c1} rv={rv.returncode} {s1} bot={b} {s2} {s3} {s4} {s5}")

        # 8 받은 지침 판 — 렌더 → 세션 시작 2단계에서 판을 잰다.
        def entry_head(content: str) -> str:
            return "".join(line + "\n" for line in content.splitlines()[:40])

        def start_with(heads: dict[str, str]) -> tuple[int, Any]:
            return _tool(hub.base, "hub_session_start", {"repo_results": {f"entry_head:{p}": {"rc": 0, "output": o}
                                                                          for p, o in heads.items()}}, bot)

        g1, cl = _tool(hub.base, "hub_guide_render", {"harness": "claude-code"}, bot)
        g2, cx = _tool(hub.base, "hub_guide_render", {"harness": "codex"}, bot)
        st1, out1 = start_with({cl["path"]: entry_head(cl["step"]["content"]), cx["path"]: entry_head(cx["step"]["content"])})
        _, after1, _ = _req(hub.base, f"/api/projects/{pid}/callsigns", token=owner)
        r1 = {c["id"]: c for c in after1["callsigns"]}["bot-a"]
        guide = tmp / "guide.md"
        guide.write_text("# 새 지침\n", encoding="utf-8")
        gs = _admin(db, "guide", "set", "--project", pid, "--file", str(guide))
        _, after2, _ = _req(hub.base, f"/api/projects/{pid}/callsigns", token=owner)
        r2 = {c["id"]: c for c in after2["callsigns"]}["bot-a"]
        # 섞인 판: 두 진입 파일 중 하나만 새 판 — 어느 쪽이 먼저 읽혀도 기록이 바뀌면 안 되므로 양쪽 순서를 다 잰다.
        g3, cx2 = _tool(hub.base, "hub_guide_render", {"harness": "codex"}, bot)
        st2, _ = start_with({cl["path"]: entry_head(cl["step"]["content"]), cx["path"]: entry_head(cx2["step"]["content"])})
        _, mid, _ = _req(hub.base, f"/api/projects/{pid}/callsigns", token=owner)
        r_mid = {c["id"]: c for c in mid["callsigns"]}["bot-a"]
        g4, cl2 = _tool(hub.base, "hub_guide_render", {"harness": "claude-code"}, bot)
        st3, _ = start_with({cl["path"]: entry_head(cl2["step"]["content"]), cx["path"]: entry_head(cx["step"]["content"])})
        _, after3, _ = _req(hub.base, f"/api/projects/{pid}/callsigns", token=owner)
        r3 = {c["id"]: c for c in after3["callsigns"]}["bot-a"]
        ok8 = (g1 == g2 == g3 == g4 == 200 and st1 == 200 and st3 == 200 and r_mid["guide_version_seen"] == r1["guide_version_seen"] and out1["hub"]["guide"]["changed"] is False
               and r1["guide_state"] == "current" and r1["guide_version_seen"] == after1["guide_current"]
               and gs.returncode == 0 and r2["guide_state"] == "stale" and after2["guide_current"] != after1["guide_current"]
               and st2 == 200 and r3["guide_state"] == "stale" and r3["guide_version_seen"] == r1["guide_version_seen"])
        _record("case 8 (받은 지침 판 — 렌더 · 세션 시작 뒤 최신, 새 판 뒤 옛 지침, 섞이면 기록 불변)", ok8,
                f"{g1} {g2} {g3} {st1} r1={r1.get('guide_state')}/{r1.get('guide_version_seen')} cur={after1.get('guide_current')} "
                f"gs={gs.returncode} r2={r2.get('guide_state')} {st2} r3={r3.get('guide_state')}/{r3.get('guide_version_seen')}")

        # 9 화면 승인
        path = f"/api/projects/{pid}/callsigns/yk-c/approve"
        a1, _, _ = _req(hub.base, path, token=bot, method="POST", body={})
        a2, _, _ = _req(hub.base, path, token=regs["yk-c"], method="POST", body={})
        a3, _, _ = _req(hub.base, path, token=owner_b, method="POST", body={})
        a4, ok_appr, _ = _req(hub.base, path, token=owner, method="POST", body={})
        _, me, _ = _req(hub.base, f"/api/projects/{pid}", token=regs["yk-c"])
        ok9 = (a1 == a2 == a3 == 403 and a4 == 200 and ok_appr.get("changed") is True and me["principal"]["can_answer"] is True)
        _record("case 9 (화면 승인 — 소유자만, 승인 뒤 결정에 답할 수 있다)", ok9, f"{a1} {a2} {a3} {a4} {me.get('principal')}")
    finally:
        hub.stop()


def case_10_11_12(tmp: Path) -> None:
    db = tmp / "guide.db"
    Hub(db).stop()
    _admin(db, "token", "issue", "--role", "web", "--name", "screen")
    hub = Hub(db, extra=("--web-token-name", "screen"))
    try:
        pid, owner = _project(hub, "guide")
        _, owner_b = _project(hub, "guide-b", "owner-b")
        regs = {cs: hub.call("hub_callsign_register", {"project_id": pid, "callsign": cs, "kind": kind})[1]["token"]
                for cs, kind in (("bot-a", "agent"), ("yk-p", "human"))}
        bot, pending = regs["bot-a"], regs["yk-p"]
        gpath = f"/api/projects/{pid}/guide"

        def version() -> int:
            return int(_req(hub.base, gpath)[1]["version"])

        # 10 제안 · 승인
        e1, d1 = _tool(hub.base, "hub_guide_propose", {"base_version": 0, "body": "# 지침 A\n", "note": "봇 제안"}, bot)
        e2, d2, _ = _req(hub.base, gpath, token=pending, method="POST", body={"base_version": 0, "body": "# 지침 B\n"})
        v_after_props = version()
        e3, _, _ = _req(hub.base, f"{gpath}/proposals/{d1.get('proposal_id')}", token=bot, method="POST", body={"approve": True})
        e4, _, _ = _req(hub.base, f"{gpath}/proposals/{d1.get('proposal_id')}", method="POST", body={"approve": True})
        e5, ap, _ = _req(hub.base, f"{gpath}/proposals/{d1.get('proposal_id')}", token=owner, method="POST", body={"approve": True})
        v1 = version()
        e6, dup, _ = _req(hub.base, f"{gpath}/proposals/{d1.get('proposal_id')}", token=owner, method="POST", body={"approve": False})
        e7, direct = _tool(hub.base, "hub_guide_propose", {"base_version": 1, "body": "# 지침 C\n"}, owner)
        v2 = version()
        e8, d8 = _tool(hub.base, "hub_guide_propose", {"base_version": 2, "body": "# 지침 D\n"}, bot)
        e9, rej = _tool(hub.base, "hub_guide_decide", {"proposal_id": d8.get("proposal_id"), "approve": False}, owner)
        s_view, view, _ = _req(hub.base, gpath)
        statuses = {x["id"]: x["status"] for x in view.get("proposals", [])}
        _, ev, _ = _req(hub.base, f"/api/projects/{pid}/events?target_kind=guide", token=owner)
        ok10 = (e1 == 200 and d1.get("status") == "open" and e2 == 200 and d2.get("status") == "open" and v_after_props == 0
                and e3 == 403 and e4 == 403 and e5 == 200 and ap.get("applied_version") == 1 and v1 == 1
                and e6 == 409 and dup.get("error_code") == "already_decided"
                and e7 == 200 and direct.get("status") == "approved" and direct.get("applied_version") == 2 and v2 == 2
                and e8 == 200 and e9 == 200 and rej.get("status") == "rejected" and version() == 2
                and s_view == 200 and view["body"] == "# 지침 C\n" and statuses.get(d2.get("proposal_id")) == "open"
                and view["can_decide"] is False and "+# 지침 A" in next((x["diff"] for x in view.get("proposals", []) if x["id"] == d1.get("proposal_id")), "")
                and [e["callsign"] for e in ev["events"] if e["op"] == "set"] == ["owner-a", "owner-a"])
        _record("case 10 (지침 제안 — agent · 승인 전 human 은 제안, 사람만 판을 올린다, 승인 · 거절 · web 403)", ok10,
                f"{e1}/{d1} {e2}/{d2.get('status')} v={v_after_props} {e3} {e4} {e5} v1={v1} {e6} {e7}/{direct} v2={v2} {e8} {e9}")

        # 11 판 지키기 — 지금 판은 2, yk-p 의 제안(기준 0)은 낡았다.
        f1, stale_p = _tool(hub.base, "hub_guide_propose", {"base_version": 1, "body": "# 낡은\n"}, bot)
        f2, stale_d, _ = _req(hub.base, f"{gpath}/proposals/{d2.get('proposal_id')}", token=owner, method="POST", body={"approve": True})
        big = "# 큰 지침\n" + ("가나다라마바사 " * 1200)
        f3, budget = _tool(hub.base, "hub_guide_propose", {"base_version": 2, "body": big}, owner)
        f3b, budget_b = _tool(hub.base, "hub_guide_propose", {"base_version": 2, "body": big}, bot)
        (tmp / "big.md").write_text(big, encoding="utf-8")
        f4 = _admin(db, "guide", "set", "--project", pid, "--file", str(tmp / "big.md"))
        _, still, _ = _req(hub.base, gpath)
        stale_flag = next((x["stale"] for x in still.get("proposals", []) if x["id"] == d2.get("proposal_id")), None)
        ok11 = (f1 == 409 and stale_p.get("error_code") == "version_conflict" and f2 == 409
                and f3 == 422 and budget.get("error_code") == "entry_budget_exceeded" and f3b == 422
                and f4.returncode != 0 and "entry_budget_exceeded" in f4.stdout and still["version"] == 2 and stale_flag is True
                and len([x for x in still["proposals"] if x["body_md"] == big]) == 0)
        _record("case 11 (지침 판 지키기 — 낡은 base 409, 예산 초과 422 · admin 도 거절, 판 불변)", ok11,
                f"{f1} {f2}/{stale_d} {f3}/{budget.get('error_code')} {f3b} admin={f4.returncode}:{f4.stdout[:120]} v={still['version']}")

        # 12 위키 읽기
        hub.call("hub_wiki_ingest", {"summary": "첫 페이지", "pages": [
            {"path": "concepts/hub.md", "body": "---\ntitle: 허브\n---\n# 허브\n\n[화면](../decisions/ui.md) 을 본다.\n", "expected_version": 0},
            {"path": "decisions/ui.md", "body": "# 화면 결정\n\n허브 화면은 상대 경로.\n", "expected_version": 0}]}, owner)
        w1, lst, _ = _req(hub.base, f"/api/projects/{pid}/wiki")
        w2, hits, _ = _req(hub.base, f"/api/projects/{pid}/wiki?q=%EC%83%81%EB%8C%80", token=bot)
        w3, page, _ = _req(hub.base, f"/api/projects/{pid}/wiki/page?path=concepts/hub.md", token=pending)
        w4, idx, _ = _req(hub.base, f"/api/projects/{pid}/wiki/page?path=index.md")
        w5, _, _ = _req(hub.base, f"/api/projects/{pid}/wiki", token=owner_b)
        w6, _, _ = _req(hub.base, f"/api/projects/{pid}/wiki/page?path=../etc.md", token=owner)
        w7, _, _ = _req(hub.base, f"/api/projects/{pid}/wiki/page?path=nope.md", token=owner)
        ok12 = (w1 == 200 and sorted(x["path"] for x in lst["pages"]) == ["concepts/hub.md", "decisions/ui.md"]
                and "index.md" in lst["generated"] and w2 == 200 and [h["path"] for h in hits["hits"]] == ["decisions/ui.md"]
                and w3 == 200 and "../decisions/ui.md" in page["body"] and w4 == 200 and idx.get("generated") is True
                and "[[concepts/hub]]" in idx["body"] and w5 == 403 and w6 == 400 and w7 == 404)
        _record("case 12 (위키 읽기 — 목록 · 검색 · 페이지 · index.md, 남의 프로젝트 403)", ok12,
                f"{w1} {w2}/{hits} {w3} {w4} {w5} {w6} {w7}")
    finally:
        hub.stop()


def main() -> int:
    print("check_hub_ui")
    with tempfile.TemporaryDirectory(prefix="hub-ui-") as d:
        tmp = Path(d)
        case_1_2_off(tmp)
        case_3_web_on(tmp)
        case_4_5_6(tmp)
        case_7_8_9(tmp)
        case_10_11_12(tmp)
    print(f"PASS {len(_passes)} · FAIL {len(_failures)}")
    for f in _failures:
        print(f"  FAIL {f}")
    return 1 if _failures else 0


if __name__ == "__main__":
    sys.exit(main())
