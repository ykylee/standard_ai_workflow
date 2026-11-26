#!/usr/bin/env python3
"""허브 화면을 실제 브라우저로 그린다 — 전 화면 (TASK-2026-11-25-claude-plex-001).

API 응답만 재면 화면이 깨져도 green 이다: 로드맵 화면은 M-053 부터 카드 대신 ``[object HTMLElement]`` 만 보였다.
Chrome headless 의 ``--dump-dom`` 으로 그린다 (Python 허브 · Go 허브 둘 다). 계정 쿠키는 앞에 둔 프록시가 싣는다.
브라우저가 없으면 **미측정**이라고 알린다 — 통과로 세지 않는다.

1. 화면 목록 — hub.js 의 ``view*`` 함수가 하나도 빠짐없이 아래 표에 있다
2. 전 화면 — ``[object `` · JS 오류 · '불러오는 중' · 오류 알림이 없고 그 화면의 내용이 있다
3. 로드맵 — 열린 마일스톤이 먼저, 완료는 접기 안
5. 확인 요청 — 문서 차이가 줄마다 맞고, 보이지 않는 문자를 드러내고, 낡은 요청의 승인 단추를 끈다 · 미확인 메시지 정리
4. 오케스트레이션 — 미확인 메시지 본문(객체 · 문자열), 계정 로그인 소유자의 승인 · 정지 · 거두기 · lease · 초대 버튼이 실제로 동작
"""

from __future__ import annotations

CHECK_TIMEOUT_S = 300

WATCHES = (
    "workflow-source/workflow_kit/*",
    "hub-go/*",
    "workflow-source/pyproject.toml",
    "workflow-source/tests/check_hub_core.py",
    "workflow-source/tests/check_hub_ui.py",
)

import html
import json
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import threading
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_hub_ui as ui  # noqa: E402
from check_hub_core import Hub, _resolve_go_hub  # noqa: E402

DOC_OLD = "\n".join(["머리", *(f"앞{i}" for i in range(6)), "옛 줄", "가운데", "지울 줄", *(f"뒤{i}" for i in range(6)), ""])
DOC_NEW = "\n".join(["머리", *(f"앞{i}" for i in range(6)), "새 줄 <script>1</script>", "가운데", *(f"뒤{i}" for i in range(6)),
                     "끝\u202e문\u2028단\u0000값\u200b\u3164\u00a0\U000e0041", ""])
# 화면이 보여야 할 차이 — 줄 앞 표시까지 그대로. 앞뒤 두 줄만, 나머지는 접는다.
DIFF = ["⋯ 바뀌지 않은 줄", "  앞4", "  앞5", "- 옛 줄", "+ 새 줄 <script>1</script>", "  가운데", "- 지울 줄", "  뒤0", "  뒤1", "⋯ 바뀌지 않은 줄", "  뒤4", "  뒤5",
        "+ 끝U+202E문U+2028단U+0000값U+200BU+3164U+00A0U+E0041", "  "]

_fails: list[str] = []
_count = 0

# 화면 함수 → (해시 경로, 있어야 할 글). {pid} 등은 실행 때 채운다.
SCREENS: dict[str, tuple[str, str]] = {
    "viewProjects": ("", "screens-demo"), "viewHarnesses": ("harnesses", "하네스"), "viewProject": ("p/{pid}", "허브 화면 재정비"),
    "viewOrchestration": ("p/{pid}/orch", "배정한 task 를 확인해 주세요"), "viewConfirmations": ("p/{pid}/confirmations", "배포 전 확인"),
    "viewIdeas": ("p/{pid}/ideas", "이력 화면에서 검색할 수 있으면 좋겠다"), "viewRoadmap": ("p/{pid}/roadmap", "허브 화면 재정비"), "viewCallsign": ("p/{pid}/c/bot-a", "bot-a"), "viewGuide": ("p/{pid}/guide", "지침"),
    "viewWiki": ("p/{pid}/w", "온보딩 안내"), "viewKnowledge": ("p/{pid}/k/{ref}", "온보딩 안내"), "viewDcrs": ("p/{pid}/dcr", "ADR 확정을 승인 즉시로 바꾸기"),
    "viewWikiPage": ("p/{pid}/wp/topics%2Fone.md", "온보딩 안내"), "viewTask": ("p/{pid}/t/{tid}", "답이 반영된다"), "viewEvents": ("p/{pid}/events", "register"),
}
PROBE = """<script>
window.addEventListener('error',e=>document.documentElement.dataset.err=(document.documentElement.dataset.err||'')+e.message+';');
window.addEventListener('unhandledrejection',e=>document.documentElement.dataset.err=(document.documentElement.dataset.err||'')+String(e.reason)+';');
window.confirm=()=>true;
setInterval(()=>{const x=[...document.querySelectorAll('.exact')].map(e=>getComputedStyle(e).unicodeBidi+'/'+getComputedStyle(e).whiteSpace);
if(x.length)document.documentElement.dataset.exact=[...new Set(x)].join(',');},400);
(async()=>{const acts=new URL(location.href).searchParams.get('acts');if(!acts)return;const z=t=>new Promise(r=>setTimeout(r,t));await z(1500);const log=[];
for(const a of acts.split('|')){if(a[0]==='@'){const d=document.querySelector('[data-keep="'+a.slice(1)+'"]');d.open=true;d.dataset.old='1';await z(10500);
if(!document.querySelector('[data-old]'))document.documentElement.dataset.renders='1';continue;}
if(a[0]==='!'){const [l,v]=a.slice(1).split('=');const g=window.fetch;window.fetch=async(...x)=>{const r=await g(...x);const f=document.querySelector('[aria-label="'+l+'"]');
if(f&&!f.value){f.value=v;f.dispatchEvent(new Event('input',{bubbles:true}));}await z(300);return r;};await z(11500);continue;}
if(a[0]==='~'){const [l,v]=a.slice(1).split('=');const f=document.querySelector('[aria-label="'+l+'"]');f.value=v;f.dispatchEvent(new Event('input',{bubbles:true}));continue;}const b=[...document.querySelectorAll('button')].find(x=>x.textContent===a&&!x.disabled);log.push(a+(b?'':':없음'));if(b){b.click();await z(900);}}
const tt=document.querySelector('[aria-label="task 제목"]');if(tt)document.documentElement.dataset.title=tt.value;
const kept=document.querySelector('textarea[aria-label="아이디어"]');if(kept&&kept.value)document.documentElement.dataset.kept=kept.value.length;
document.documentElement.dataset.acts=log.join('|');})();
</script>"""


def _record(case: str, ok: bool, detail: str = "") -> None:
    global _count
    _count += 1
    if not ok:
        _fails.append(f"{case}: {detail}")
    print(f"  {'PASS' if ok else 'FAIL'}: {case}{(' — ' + detail) if detail and not ok else ''}")


def browser() -> str | None:
    return next((p for n in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser") if (p := shutil.which(n))), None)


def proxy(hub: Hub, cookie: str) -> ThreadingHTTPServer:
    class H(BaseHTTPRequestHandler):
        def _go(self) -> None:
            if self.path.startswith("/narrow?"):  # 휴대폰 폭 — Chrome 창은 500px 아래로 줄지 않는다
                page = (b"<!doctype html><iframe width=360 height=800 src='/ui/" + urllib.parse.unquote(self.path[8:]).encode() + b"'></iframe><script>setTimeout(()=>{const d="
                        b"document.querySelector('iframe').contentDocument.documentElement;document.body.dataset.w=d.scrollWidth+'/'+d.clientWidth;"
                        b"document.body.dataset.text=d.innerText;"
                        # 표 안쪽 가로 넘침 — 페이지 폭은 그대로여도 표가 옆으로 밀리면 휴대폰에서 못 읽는다
                        b"document.body.dataset.tw=Math.max(0,...[...d.querySelectorAll('.table-wrap')].map(e=>e.scrollWidth-e.clientWidth));"
                        # 탭이 보이는 폭 밖으로 밀려 숨었는지 (가로 스크롤 안에 숨은 탭도 센다)
                        b"const nv=[...d.querySelectorAll('.nav-links a')];document.body.dataset.nav=nv.length+'/'+nv.filter(a=>{const r=a.getBoundingClientRect();"
                        b"const p=a.parentElement.getBoundingClientRect();return r.right>Math.min(p.right,d.clientWidth)+1||r.width===0}).length},4000)</script>")
                self.send_response(200)
                self.send_header("content-type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(page)
                return
            size = int(self.headers.get("content-length") or 0)
            headers = {k: v for k, v in self.headers.items() if k.lower() in ("accept", "content-type", "authorization", "sec-fetch-site")}
            headers["cookie"] = cookie
            headers["origin"] = hub.base
            req = urllib.request.Request(hub.base + self.path, method=self.command, headers=headers, data=self.rfile.read(size) if size else None)
            try:
                with urllib.request.urlopen(req, timeout=20) as r:
                    status, body, ctype = r.status, r.read(), r.headers.get("content-type") or ""
            except urllib.error.HTTPError as e:
                status, body, ctype = e.code, e.read(), e.headers.get("content-type") or ""
            if "text/html" in ctype:
                body = body.replace(b"<head>", b"<head>" + PROBE.encode(), 1)
            self.send_response(status)
            self.send_header("content-type", ctype)
            self.send_header("content-length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        do_GET = do_POST = _go

        def log_message(self, *a: Any) -> None:
            return

    srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def draw(exe: str, tmp: Path, port: int, route: str, acts: str = "", budget: int = 9500, narrow: bool = False) -> str:
    from urllib.parse import quote

    url = f"http://127.0.0.1:{port}/ui/{'?acts=' + quote(acts) if acts else ''}#/{route}"
    if narrow:
        url = f"http://127.0.0.1:{port}/narrow?{quote('#/' + route)}"
    with tempfile.TemporaryDirectory(prefix="chrome-", dir=tmp, ignore_cleanup_errors=True) as prof:
        r = subprocess.run([exe, "--headless=new", "--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage", "--no-first-run",
                            "--password-store=basic", "--disable-background-networking", "--no-proxy-server",  # 키링(D-Bus) 25초 대기를 피한다
                            f"--user-data-dir={prof}", f"--virtual-time-budget={budget}", "--dump-dom", url],
                           capture_output=True, encoding="utf-8", errors="replace", timeout=90)
    return r.stdout


def problems(dom: str, want: str) -> list[str]:
    text = html.unescape(re.sub(r"<(script|style)\b.*?</\1>", "", dom, flags=re.S))
    out = [f"'{bad}'" for bad in ("[object ", "불러오는 중", "허브에 닿지 않는다", "undefined") if bad in text]
    err = re.search(r'<html[^>]*data-err="([^"]*)"', dom)
    if err:
        out.append(f"JS 오류 {err[1][:120]}")
    if re.search(r'class="[^"]*\bbad\b', dom):
        out.append("오류 알림")
    if want not in text:
        out.append(f"내용 없음 '{want}'")
    return out


def seed(hub: Hub, db: Path, impl: str) -> dict[str, str]:
    pid, owner = ui._project(hub, "screens-demo")
    bot = hub.call("hub_callsign_register", {"project_id": pid, "callsign": "bot-a", "kind": "agent"})[1]["token"]
    _, _, head = ui._req(hub.base, "/api/account/enroll", method="POST", token=owner,
                         body={"username": f"scr-{impl}", "display_name": "Owner", "password": "long-test-password-123"})

    def must(name: str, args: dict[str, Any], tok: str) -> dict[str, Any]:
        st, out, _ = hub.call(name, args, tok)
        assert st == 200, (name, out)
        return out

    tid = ui._task(hub, owner)
    so = must("hub_session_start", {"session": {"harness": "claude-code"}}, owner)["session"]["id"]
    sw = must("hub_session_start", {"session": {"harness": "codex", "kind": "worker"}}, bot)["session"]["id"]
    must("hub_wiki_ingest", {"pages": [{"path": "topics/one.md", "body": "---\ntitle: 온보딩 안내\n---\n\n# 온보딩 안내\n\n본문\n", "expected_version": 0}], "summary": "한 장"}, owner)
    dcr = must("hub_dcr_create", {"title": "ADR 확정을 승인 즉시로 바꾸기", "rationale": "이유", "proposal": "제안", "target_refs": []}, bot)
    assert dcr
    miles = [("M-001", "계정 · 권한", 1), ("M-003", "워크벤치 정리", 2), ("M-002", "허브 화면 재정비", 3), ("M-004", "Go 허브 이전", 4)]

    wbs = {1: "계정 관리자 권한", 2: "워크벤치 결정 응답 정리", 3: "개요 화면 진척 띠", 4: "Go 허브 화면 API 맞추기"}

    def roadmap(version: int, first: str) -> None:
        status = {"M-001": first, "M-002": "in_progress", "M-003": "planned", "M-004": "in_progress"}
        must("hub_roadmap_put", {"path": "index.md", "expected_version": version, "body": "# Roadmap — s\n\n## Milestones\n\n" + "".join(
            f"- **{i}** [implementation] {t} — status: {status[i]}\n  - path: [`./{i}-x.md`](./{i}-x.md)\n" for i, t, _ in miles)}, owner)
        for i, t, n in miles:
            must("hub_roadmap_put", {"path": f"{i}-x.md", "expected_version": version, "body": f"---\nid: {i}\ntitle: {t}\nsdlc_phase: implementation\nstatus: {status[i]}\n"
                                     f"order: {n}\nparallel_allowed: [M-001, M-002, M-003, M-004]\ndeliverables: []\n---\n\n# {i}\n\n## WBS\n\n- **WBS-{n}.1** {wbs[n]}\n"}, owner)

    roadmap(0, "in_progress")
    must("hub_idea_add", {"body": "이력 화면에서 검색할 수 있으면 좋겠다"}, bot)
    t1 = must("hub_task_create", {"title": "계정 관리자 권한 추가", "wbs": "M-001/WBS-1.1", "fields": {"done_criteria": ["끝"]}}, owner)["task"]
    must("hub_task_claim", {"id": t1["id"]}, owner)
    t1 = must("hub_task_get", {"id": t1["id"]}, owner)["task"]
    must("hub_task_close", {"id": t1["id"], "expected_version": t1["version"], "validation_result": "확인"}, owner)
    roadmap(1, "done")  # done 선언은 task 가 끝난 뒤 (그 전에는 WBS 게이트가 task 를 막는다)
    must("hub_approval_request", {"session": sw, "title": "배포 전 확인", "question": "3.9.0 을 홈랩 허브에 배포해도 될까요?"}, bot)
    must("hub_project_doc_put", {"name": "purpose", "body": DOC_OLD, "expected_version": 0}, owner)
    must("hub_project_doc_put", {"name": "profile", "body": "옛 프로필\n", "expected_version": 0}, owner)
    must("hub_approval_request", {"session": sw, "title": "목적 문서 고치기", "question": "프로젝트 목적 문서를 이 내용으로 바꿀까요?", "action": {
        "type": "project_doc_put", "name": "purpose", "body": DOC_NEW, "expected_version": 1}}, bot)
    must("hub_approval_request", {"session": sw, "title": "제\u202e목", "question": "질\u200b문", "details": "설\u2066명", "action": {
        "type": "project_doc_put", "name": "profile", "body": "새 프로필\n", "expected_version": 1}}, bot)
    must("hub_project_doc_put", {"name": "profile", "body": "그 사이 바뀜\n", "expected_version": 1}, owner)  # 요청을 낡게 한다
    must("hub_approval_request", {"session": sw, "title": "원본 등록", "question": "온보딩 문서를 등록할까요?", "action": {
        "type": "knowledge_source_register", "source_id": "onboard-docs", "repo_key": "github.com/acme/screens-demo",
        "allowlist": ["docs/a.md", "docs/b.md"]}}, bot)
    must("hub_guide_propose", {"base_version": must("hub_guide_get", {}, bot)["version"], "body": "# 지침\n\n새 규\u202e칙\n", "note": "메\u200b모"}, bot)
    st, _, _ = ui._req(hub.base, f"/api/projects/{pid}/orchestration/lease", token=owner, method="POST", body={"action": "declare", "session": so})
    assert st == 200
    _, inv, _ = ui._req(hub.base, f"/api/projects/{pid}/orchestration/relays/invite", token=owner, method="POST", body={})
    reg = urllib.request.Request(hub.base + "/v1/relay/register", method="POST", headers={"content-type": "application/json"},
                                 data=json.dumps({"invite": inv["invite"], "name": "pc", "harnesses": ["fake"]}).encode())
    with urllib.request.urlopen(reg, timeout=20) as r:
        host = json.loads(r.read())["host_id"]
    for alias in ("w1", "w2"):
        must("hub_orch_request_session", {"session": so, "host_id": host, "dir_alias": alias, "harness": "fake", "prompt": "지\u202e시  두칸\ufffc"}, owner)
    must("hub_orch_assign", {"session": so, "task_id": tid, "to_session": sw}, owner)
    with sqlite3.connect(db) as c:
        for n, body in (("a", {"title": "새 배정 알림", "text": "배정한 task 를 확인해 주세요\u200b"}), ("b", "문자열 본문\u2066")):
            c.execute("INSERT INTO inbox_message (project_id,id,to_kind,to_id,from_callsign,from_session,from_orchestrator,kind,body_json,ref_task,state,"
                      "delivered_via,delivered_at,created_at) VALUES (?,?,'session',?,'owner-a',?,1,'note',?,?,'unacknowledged','piggyback',?,?)",
                      (pid, f"MSG-20261122-{n * 12}", sw, so, json.dumps(body, ensure_ascii=False), tid, "2026-11-22T00:00:00+00:00", "2026-11-22T00:00:00+00:00"))
    with sqlite3.connect(db) as c:  # 객체가 아닌 본문의 approval 이 확인 요청 화면을 막지 않는다
        for n, raw in (("d", '"글"'), ("e", "[1]")):
            c.execute("INSERT INTO inbox_message (project_id,id,to_kind,to_id,from_callsign,from_session,from_orchestrator,kind,body_json,state,created_at) "
                      "VALUES (?,?,'callsign','owner-a','bot-a','',0,'approval',?,'queued',?)", (pid, f"MSG-20261121-{n * 12}", raw, "2026-11-21T00:00:00+00:00"))
    found = must("hub_knowledge_search", {"query": "온보딩"}, owner)
    ref = next((str(x.get("ref")) for x in found.get("results") or found.get("hits") or []), "")
    from urllib.parse import quote
    return {"owner": owner, "bot": bot, "pid": pid, "tid": tid, "ref": quote(ref, safe=""), "cookie": head.get("set-cookie", "").split(";", 1)[0], "host": host}


APPROVE_TILES = {"확인 요청", "중계 승인", "결정 변경(DCR)", "지침 제안"}
REVIEW_TILES = {"열린 결정 task", "막힌 task"}
RAW_STATUS = {"in_progress", "planned", "blocked", "done", "working", "idle", "waiting", "ended", "unknown"}


def overview_cases(impl: str, exe: str, tmp: Path, port: int, hub: Hub, env: dict[str, str], doms: dict[str, str]) -> None:
    """개요 재정비(TASK-2026-11-26-claude-plex-008) — 사람이 결정할 일 · 진척 띠 · 한국어 상태 · 좁은 폭 표."""
    ov = html.unescape(doms["viewProject"])
    pid = env["pid"]
    want = len(ui._req(hub.base, f"/api/projects/{pid}/confirmations", token=env["owner"])[1]["requests"])
    summary = ui._req(hub.base, f"/api/projects/{pid}", token=env["owner"])[1]["summary"]
    tiles = {m[2]: (m[1], int(m[3])) for m in re.finditer(r'<a class="(?:need|look)" href="([^"]*)" data-decide="([^"]*)"><span class="n">(\d+)</span>', ov)}
    first = (summary.get("open_decision_task_ids") or [""])[0]
    ok = (tiles.get("확인 요청") == (f"#/p/{pid}/confirmations", want) and want > 0
          and tiles.get("열린 결정 task") == (f"#/p/{pid}/t/{first}", summary["open_decision_tasks"]) and first
          and tiles.get("결정 변경(DCR)", ("", 0))[0] == f"#/p/{pid}/dcr" and tiles.get("지침 제안", ("", 0))[0] == f"#/p/{pid}/guide"
          and ov.find('id="decide-h"') < ov.find('id="rail-h"') < ov.find('id="tasks-h"'))
    _record(f"[{impl}] 개요 — 사람이 결정할 일: 수는 각 화면 API 와 같고 그 화면으로 간다 · 결정 → 진척 → task 순", bool(ok), f"{tiles} want={want} first={first}")
    # 두 묶음 (TASK-2026-11-26-claude-plex-013) — 승인할 것(주황 need)이 먼저, 살펴볼 것(무채색 look)이 뒤, 묶음당 4칸 이하
    ia, ir, end = ov.find('data-group="approve"'), ov.find('data-group="review"'), ov.find('id="rail-h"')
    grouped = {k: re.findall(r'<a class="(need|look)[^"]*" href="[^"]*" data-decide="([^"]*)"', ov[a:b]) for k, a, b in (("approve", ia, ir), ("review", ir, end))}
    _record(f"[{impl}] 개요 — 결정 두 묶음: 승인할 것(실행 경계) 먼저 · 살펴볼 것 뒤, 묶음당 4칸 이하",
            0 < ia < ir < end and 0 < len(grouped["approve"]) <= 4 and 0 < len(grouped["review"]) <= 4
            and all(c == "need" and l in APPROVE_TILES for c, l in grouped["approve"])
            and all(c == "look" and l in REVIEW_TILES for c, l in grouped["review"]) and "승인할 것" in ov[ia:ir] and "살펴볼 것" in ov[ir:end],
            f"{grouped} at={ia},{ir},{end}")
    rail = re.search(r'<div class="rail"[^>]*>(.*?)</div>', ov, re.S)
    segs = re.findall(r'<a role="listitem"[^>]*class="([^"]*)"', rail[1]) if rail else []
    _record(f"[{impl}] 개요 — 진척 띠: 마일스톤마다 한 칸 · 현재 하나", len(segs) == 4 and sum("current" in c for c in segs) == 1, f"{segs}")
    raw = {v: sorted({t for t in re.findall(r'<span class="chip[^"]*"[^>]*>([^<]*)</span>', html.unescape(doms[v])) if t in RAW_STATUS})
           for v in ("viewProject", "viewRoadmap", "viewOrchestration", "viewTask")}
    _record(f"[{impl}] 상태는 한국어 낱말 — 원문 enum 꼬리표 없음", not any(raw.values()), f"{raw}")
    dom = draw(exe, tmp, port, f"p/{pid}", narrow=True, budget=12000)
    w = re.search(r'data-w="(\d+)/(\d+)"', dom)
    tw = re.search(r'data-tw="(-?\d+)"', dom)
    _record(f"[{impl}] 개요 360px — 페이지 · 표 안쪽 모두 가로 넘침 없음", bool(w and tw) and w[1] == w[2] and tw[1] == "0", f"w={w and w.groups()} tw={tw and tw[1]}")
    # 재채점 P2 · P3 (TASK-2026-11-26-claude-plex-012)
    orch = doms["viewOrchestration"]
    at_appr, at_msg = orch.find('id="approvals"'), orch.find("미확인 메시지")
    folded = re.search(r'<details class="card" data-keep="orch-unack"[^>]*>', orch)
    _record(f"[{impl}] 오케스트레이션 — 사람 승인이 메시지보다 위, 메시지는 접힘 · 중계 승인 타일이 그 자리로",
            0 < at_appr < at_msg and bool(folded) and " open" not in folded[0] and tiles.get("중계 승인", ("", 0))[0] == f"#/p/{pid}/orch?focus=approvals",
            f"approvals={at_appr} msg={at_msg} folded={folded and folded[0]} tile={tiles.get('중계 승인')}")
    st2, out2, _ = hub.call("hub_task_create", {"title": "배포 채널 정하기", "plan_md": ui.PLAN, "wbs": "exempt", "wbs_exempt_reason": "화면 검사",
                                               "fields": {"done_criteria": ["[C1] 답이 반영된다"]}}, env["owner"])
    assert st2 == 200, out2  # 열린 결정 task 가 둘이면 타일은 한 task 가 아니라 목록으로 간다
    many = ui._req(hub.base, f"/api/projects/{pid}", token=env["owner"])[1]["summary"]["open_decision_task_ids"]
    ov2 = html.unescape(draw(exe, tmp, port, f"p/{pid}"))
    tile2 = re.search(r'<a class="look" href="([^"]*)" data-decide="열린 결정 task">', ov2)
    lst = html.unescape(draw(exe, tmp, port, f"p/{pid}?decisions=open"))
    titles = [ui._req(hub.base, f"/api/projects/{pid}/tasks/{t}", token=env["owner"])[1]["task"]["title"] for t in many]
    _record(f"[{impl}] '열린 결정 task' 둘 이상 — 타일이 목록으로, 목록엔 그 task 만", len(many) == 2 and bool(tile2) and tile2[1] == f"#/p/{pid}?decisions=open"
            and all(t in lst for t in titles) and "답이 필요한 결정이 있는 task" in lst and lst.count('<td class="t-title">') == 2
            and ">필터 해제</a>" in lst and re.search(r'class="look on"[^>]*data-decide="열린 결정 task" aria-current="true"', lst) is not None, f"{many} tile={tile2 and tile2[1]}")
    ev = html.unescape(doms["viewEvents"])
    raw_ops = sorted({m for m in re.findall(r'<td class="t-title"><span title="([a-z_]+)">([^<]*)</span>', ev) if m[0] == m[1]})
    _record(f"[{impl}] 이력 — 동작명이 영어 원문만으로 나오지 않는다", not raw_ops and "<td class=\"t-title\">" in ev, f"{raw_ops}")
    nav = re.search(r'data-nav="(\d+)/(\d+)"', dom)
    _record(f"[{impl}] 360px 탭 — 9개 모두 보인다 (숨은 탭 0)", bool(nav) and nav[1] == "9" and nav[2] == "0", f"nav={nav and nav.groups()}")


def dcr_cases(impl: str, exe: str, tmp: Path, port: int, hub: Hub, env: dict[str, str], doms: dict[str, str]) -> None:
    """DCR 을 웹에서 승인 · 거절한다 (TASK-2026-11-26-claude-plex-011) — 근거 없으면 막고, 비소유자는 403."""
    pid = env["pid"]
    st, out, _ = hub.call("hub_dcr_create", {"title": "거절할 결정", "rationale": "이유", "proposal": "제안", "target_refs": []}, env["bot"])
    assert st == 200, out
    listed = {d["title"]: d["id"] for d in ui._req(hub.base, f"/api/projects/{pid}/dcr", token=env["owner"])[1]["dcrs"]}
    yes, no = listed["ADR 확정을 승인 즉시로 바꾸기"], listed["거절할 결정"]
    blank = draw(exe, tmp, port, f"p/{pid}/dcr/{yes}", "승인", 12000)  # 근거 없이 누르면 막힌다
    still = ui._req(hub.base, f"/api/projects/{pid}/dcr/{yes}", token=env["owner"])[1]["status"]
    _record(f"[{impl}] DCR — 근거 없이 승인하면 막는다", still == "open" and "판단 근거를 적어야" in html.unescape(blank), f"status={still}")
    # 결정 메모 칸은 화면마다 같은 모양 (TASK-2026-11-26-claude-plex-013) — 꼬리표 달린 여러 줄 칸 하나 + 승인 · 거절, 한 줄 입력 없음
    forms = {v: (len(re.findall(r'<div class="decide-form"><label class="field">[^<]*<textarea', d)), d.count(">거절</button>"),
                 len(re.findall(r'<input type="text"[^>]*메모', d)))
             for v, d in (("확인 요청", doms["viewConfirmations"]), ("중계 승인", doms["viewOrchestration"]), ("DCR", blank))}
    _record(f"[{impl}] 결정 메모 — 확인 요청 · 중계 승인 · DCR 이 같은 모양", all(f > 0 and f == r and t == 0 for f, r, t in forms.values()), f"{forms}")
    draw(exe, tmp, port, f"p/{pid}/dcr/{yes}", "~판단 근거=화면에서 승인한다|승인", 12000)
    draw(exe, tmp, port, f"p/{pid}/dcr/{no}", "~판단 근거=범위가 맞지 않는다|거절", 12000)
    got = {k: ui._req(hub.base, f"/api/projects/{pid}/dcr/{v}", token=env["owner"])[1] for k, v in (("yes", yes), ("no", no))}
    bot = ui._req(hub.base, f"/api/projects/{pid}/dcr/{no}/decision", method="POST", token=env["bot"],
                  body={"decision": "approve", "rationale": "r", "expected_version": got["no"]["version"]})[0]
    shown = html.unescape(draw(exe, tmp, port, f"p/{pid}/dcr/{yes}"))
    _record(f"[{impl}] DCR — 화면 단추로 승인(ADR 확정) · 거절, 비소유자 403, 끝난 DCR 엔 단추 없음",
            got["yes"]["status"] == "accepted" and bool(got["yes"].get("adr_path")) and got["no"]["status"] == "rejected" and bot == 403
            and ">승인</button>" not in shown and got["yes"]["adr_path"] in shown,
            f"yes={got['yes']['status']}/{got['yes'].get('adr_path')} no={got['no']['status']} bot={bot}")


def answer_cases(impl: str, exe: str, tmp: Path, port: int, hub: Hub, env: dict[str, str], doms: dict[str, str]) -> None:
    """보지 않은 결정에 답이 나가지 않는다 · 로그아웃 링크는 로그인으로 (TASK-2026-11-26-claude-plex-008 재채점 P1)."""
    pid, tid = env["pid"], env["tid"]
    task = doms["viewTask"]
    radios = re.findall(r'<input type="radio"[^>]*>', task)
    boxes = re.findall(r'<input type="checkbox"[^>]*열어 보고 확인함[^>]*>', task)
    before = ui._req(hub.base, f"/api/projects/{pid}/tasks/{tid}", token=env["owner"])[1]["plan"]["responses"]
    dom = html.unescape(draw(exe, tmp, port, f"p/{pid}/t/{tid}", "응답 보내기", 12000))
    after = ui._req(hub.base, f"/api/projects/{pid}/tasks/{tid}", token=env["owner"])[1]["plan"]["responses"]
    _record(f"[{impl}] 결정 — 미리 고르지 않고, 고르지 않은 채 보내면 막는다", bool(radios) and not any(" checked" in r for r in radios)
            and bool(boxes) and not any(" checked" in b for b in boxes) and "아직 답하지 않은 결정이 있다" in dom and after == before,
            f"radios={radios} boxes={boxes} responses {before}->{after}")
    direct = int(hub.base.rsplit(":", 1)[1].split("/")[0])
    out = html.unescape(draw(exe, tmp, direct, f"p/{pid}"))
    _record(f"[{impl}] 로그아웃으로 연 프로젝트 링크 — 로그인 양식이 먼저", "허브 계정 로그인" in out and "콜사인 토큰으로 열기" in out, out[-300:])


def measure(impl: str, cmd: list[str] | None, exe: str, tmp: Path) -> None:
    db = tmp / f"{impl}.db"
    hub = Hub(db, cmd_prefix=cmd)
    srv = None
    try:
        env = seed(hub, db, impl)
        srv = proxy(hub, env["cookie"])
        port = srv.server_address[1]
        doms: dict[str, str] = {}
        for view, (route, want) in SCREENS.items():
            doms[view] = draw(exe, tmp, port, route.format(**env))
            bad = problems(doms[view], want)
            _record(f"[{impl}] {view}", not bad, " · ".join(bad))
        overview_cases(impl, exe, tmp, port, hub, env, doms)
        dcr_cases(impl, exe, tmp, port, hub, env, doms)
        answer_cases(impl, exe, tmp, port, hub, env, doms)
        rm = doms["viewRoadmap"]
        fold = rm.find('data-keep="rm-done"')
        at = [rm.find(f"<h2>{t}") for t in ("허브 화면 재정비", "Go 허브 이전", "워크벤치 정리", "계정 · 권한")]
        _record(f"[{impl}] 로드맵 — 현재 · 진행 중 · 예정 · 완료 순", at[0] > 0 and at == sorted(at), f"{at}")
        kept = draw(exe, tmp, port, f"p/{env['pid']}/roadmap", "@rm-done", 14000)
        folds = re.findall(r'<details[^>]*data-keep="rm-done"[^>]*>', kept)
        _record(f"[{impl}] 자동 갱신이 펼친 접기를 닫지 않는다", len(folds) == 1 and " open" in folds[0] and 'data-renders="1"' in kept, f"{folds}")
        _record(f"[{impl}] 로드맵 — 열린 것 먼저 · 완료는 접기", 0 < rm.find("<h2>허브 화면 재정비") < fold < rm.find("<h2>계정 · 권한"), f"접기 {fold}")
        orch = doms["viewOrchestration"]
        _record(f"[{impl}] 오케스트레이션 — 메시지 본문", all(x in orch for x in ("새 배정 알림", "배정한 task 를 확인해 주세요", "문자열 본문")))
        _record(f"[{impl}] 오케스트레이션 — 지시문 · 메시지의 보이지 않는 문자", [orch.count(f">{u}</mark>") for u in ("U+202E", "U+FFFC", "U+200B", "U+2066")] == [2, 2, 1, 1])
        _record(f"[{impl}] 오케스트레이션 — 정리 안내문", "세션이 끝났으면 같은 콜사인" in orch and "읽음으로 표시" in orch and "hub_" not in re.sub(r"<[^>]+>", "", orch.split("<body", 1)[-1]) and "읽음으로 정리" in orch)
        guide = doms["viewGuide"]
        _record(f"[{impl}] 지침 제안 — 보이지 않는 문자", guide.count(">U+202E</mark>") == 1 and guide.count(">U+200B</mark>") == 1
                and re.search(r'<pre class="diff exact">[^<]*\+새 규<mark', guide) is not None)
        exact = {v: re.findall(r'data-exact="([^"]*)"', doms[v])[:1] for v in ("viewConfirmations", "viewOrchestration", "viewGuide")}
        _record(f"[{impl}] 승인 글은 저장된 순서 · 공백 그대로", all(x == ["bidi-override/pre-wrap"] for x in exact.values()), f"{exact}")
        conf = doms["viewConfirmations"]
        src = re.search(r'<section class="card" data-action="knowledge_source_register">.*?</section>', conf, re.S)
        _record(f"[{impl}] 확인 요청 — 지식 원본 등록 카드", bool(src) and "지식 원본 등록" in src[0] and 'data-source-paths="2"' in src[0]
                and "docs/a.md" in html.unescape(src[0]) and "onboard-docs" in html.unescape(src[0]), (src[0] if src else conf)[-400:])
        _record(f"[{impl}] 확인 요청 — 문서 차이", all(x in conf for x in (
            'class="diff-del">- 옛 줄', 'class="diff-add">+ 새 줄 &lt;script&gt;', "1판 → 2판", 'data-doc-diff="purpose"', "추가 2줄 · 삭제 2줄")))
        pre = re.search(r'<pre[^>]*data-doc-diff="purpose"[^>]*>(.*?)</pre>', conf, re.S)
        shown = html.unescape(re.sub(r"<[^>]+>", "", pre[1])).removesuffix("\n").split("\n") if pre else []
        _record(f"[{impl}] 확인 요청 — 차이가 줄마다 맞다", shown == DIFF, f"{shown}")
        raw = [f"U+{ord(ch):04X}" for ch in "\u202e\u2028\u0000\u200b\u3164\u00a0\U000e0041\u2066" if ch in html.unescape(conf)]
        marks = [conf.count(f">{u}</mark>") for u in ("U+202E", "U+2028", "U+0000", "U+200B", "U+3164", "U+00A0", "U+E0041", "U+2066")]
        _record(f"[{impl}] 확인 요청 — 보이지 않는 문자를 드러낸다 (본문 · 제목 · 질문 · 설명)",
                not raw and marks == [3, 2, 2, 3, 2, 2, 2, 1] and "보이지 않는 문자 7개" in conf, f"{raw} {marks}")
        cards = {t: c for c in re.findall(r'<section class="card">.*?(?=<section class="card"><div class="row"><h2|$)', conf, re.S)
                 for t in ("purpose", "profile") if f'data-doc-diff="{t}"' in c}
        approve = {t: re.search(r'<button type="button"([^>]*)>승인<', c) for t, c in cards.items()}
        _record(f"[{impl}] 확인 요청 — 낡은 요청은 알리고 승인 단추를 끈다", {t: bool(m and "disabled" in m[1]) for t, m in approve.items()} == {"purpose": False, "profile": True}
                and ["낡은 요청 — 문서가 지금 2판" in cards.get(t, "") for t in ("purpose", "profile")] == [False, True], f"{ {t: m and m[0] for t, m in approve.items()} }")
        odd = [ui._req(hub.base, f"/api/projects/{env['pid']}/confirmations/MSG-20261121-{n * 12}", method="POST", token=env["owner"], body={"decision": "approve"})[0] for n in "de"]
        _record(f"[{impl}] 확인 요청 — 객체가 아닌 본문은 404", odd == [404, 404], f"{odd}")
        close = f"/api/projects/{env['pid']}/orchestration/messages/{{}}/close"
        mid = f"MSG-20261122-{'a' * 12}"
        pending = next(r["id"] for r in ui._req(hub.base, f"/api/projects/{env['pid']}/confirmations", token=env["owner"])[1]["requests"])
        codes = [ui._req(hub.base, close.format(m), method="POST", token=t, body={})[0] for m, t in (
            (mid, env["bot"]), ("MSG-20261122-cccccccccccc", env["owner"]), (pending, env["owner"]))]
        _record(f"[{impl}] 미확인 정리 — 비소유자 403 · 없는 것 404 · 사람 확인 요청 403", codes == [403, 404, 403], f"{codes}")
        dom = draw(exe, tmp, port, f"p/{env['pid']}/orch", "읽음으로 정리")
        with sqlite3.connect(db) as c:
            left = c.execute("SELECT state, ack_by_session FROM inbox_message WHERE id LIKE 'MSG-20261122-%' ORDER BY state").fetchall()
        again = ui._req(hub.base, close.format(mid if "aaaa" not in dom else f"MSG-20261122-{'b' * 12}"), method="POST", token=env["owner"], body={})[0]
        _record(f"[{impl}] 미확인 정리 — 소유자 단추", sorted(left)[0] == ("acked", "web:owner-a") and [x[0] for x in left] == ["acked", "unacknowledged"] and again == 409, f"{left} {again}")
        acts = ["승인", "거절", "이 세션에 넘기기", "전체 정지", "정지 풀기", "거두기", "오케스트레이터 내려놓기", "오케스트레이터 지정", "중계 초대 코드 발급"]
        dom = draw(exe, tmp, port, f"p/{env['pid']}/orch", "|".join(acts), 16000)
        with sqlite3.connect(db) as c:
            state = (sorted(c.execute("SELECT state, decided_by FROM session_request").fetchall()), c.execute("SELECT revoked_at IS NOT NULL FROM relay_host").fetchone()[0],
                     c.execute("SELECT COUNT(*) FROM orchestrator_lease").fetchone()[0],
                     [r[0] for r in c.execute("SELECT op FROM event WHERE target_kind = 'orchestrator_lease' ORDER BY seq")])
        done = re.search(r'data-acts="([^"]*)"', dom)
        ok = bool(done) and html.unescape(done[1]) == "|".join(acts) and "1회용 초대 코드" in dom and state[0] == [("approved", "owner-a"), ("rejected", "owner-a")] and state[1:3] == (1, 1)
        ops = state[3]
        ok = ok and ops[0] == "declare" and ops[-1] == "declare" and "release" in ops and "transfer" in ops and len([o for o in ops if o not in ("declare", "release", "transfer")]) == 2
        _record(f"[{impl}] 오케스트레이션 — 계정 로그인 소유자 조작", ok, f"{done and done[1]} {state}")
        # 관리자 계정 — 쿠키 세션만으로 관리 화면이 열리고, 계정 권한 단추가 실브라우저에서 같은 출처 POST 로 동작한다
        with sqlite3.connect(db) as c:
            c.execute("UPDATE hub_account SET is_admin = 1")
            admins = c.execute("SELECT COUNT(*) FROM hub_account").fetchone()[0]
        dom = draw(exe, tmp, port, "harnesses")
        bad = problems(dom, "계정 관리자 권한") + (["로그인 양식이 떴다"] if "관리자 모드로 로그인" in dom else [])
        _record(f"[{impl}] 관리자 계정 — 토큰 없이 관리 화면 · 계정 권한 표", not bad, " · ".join(bad))
        dom = draw(exe, tmp, port, "harnesses", "관리자 거두기", 12000)
        with sqlite3.connect(db) as c:
            left = c.execute("SELECT COUNT(*) FROM hub_account WHERE is_admin = 1").fetchone()[0]
        done = re.search(r'data-acts="([^"]*)"', dom)
        _record(f"[{impl}] 관리자 계정 — 화면 단추로 권한 거두기", bool(done) and html.unescape(done[1]) == "관리자 거두기"
                and admins >= 1 and left == admins - 1, f"{done and done[1]} admins={admins} left={left}")
    finally:
        if srv:
            srv.shutdown()
            srv.server_close()
        hub.stop()


def main() -> int:
    print("check_hub_screens")
    route = ui.HUB_JS[ui.HUB_JS.index("async function route("):]  # 길에서 부르는 것이 정본 — 정의 방식(함수 · const)에 기대지 않는다
    views = set(re.findall(r"await (\w+)\((?:parts|\))", route)) | set(re.findall(r"(?:function\s+|const\s+)(view[A-Z]\w*)\s*(?:=\s*async\b|\()", ui.HUB_JS))
    _record("화면 목록이 hub.js 와 같다", views == set(SCREENS), f"{sorted(views ^ set(SCREENS))}")
    missed: list[str] = []
    exe = browser()
    if exe is None:
        print("    [unmeasured] 화면 미측정: Chrome · Chromium 이 없다")
        missed.append("브라우저")
    else:
        with tempfile.TemporaryDirectory(prefix="hub-screens-", ignore_cleanup_errors=True) as d:
            tmp = Path(d)
            measure("python", None, exe, tmp)
            go_cmd, reason = _resolve_go_hub(tmp)
            if go_cmd is None:
                print(f"    [unmeasured] go 허브 미측정: {reason}")
                missed.append("go 허브")
                if reason.startswith("go build"):  # 도구가 없는 것과 코드가 깨진 것은 다르다
                    _record("go 허브 빌드", False, reason[:200])
            else:
                measure("go", go_cmd, exe, tmp)
    note = f" · 미측정 {len(missed)} ({', '.join(missed)})" if missed else ""
    print(f"{_count - len(_fails)}/{_count} PASS{note}")
    return 1 if _fails else 0


if __name__ == "__main__":
    sys.exit(main())
