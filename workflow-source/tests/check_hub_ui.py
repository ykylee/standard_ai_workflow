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


def main() -> int:
    print("check_hub_ui")
    with tempfile.TemporaryDirectory(prefix="hub-ui-") as d:
        tmp = Path(d)
        case_1_2_off(tmp)
        case_3_web_on(tmp)
        case_4_5_6(tmp)
    print(f"PASS {len(_passes)} · FAIL {len(_failures)}")
    for f in _failures:
        print(f"  FAIL {f}")
    return 1 if _failures else 0


if __name__ == "__main__":
    sys.exit(main())
