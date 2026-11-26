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
DIFF = ["⋯ 같은 줄", "  앞4", "  앞5", "- 옛 줄", "+ 새 줄 <script>1</script>", "  가운데", "- 지울 줄", "  뒤0", "  뒤1", "⋯ 같은 줄", "  뒤4", "  뒤5",
        "+ 끝U+202E문U+2028단U+0000값U+200BU+3164U+00A0U+E0041", "  "]

_fails: list[str] = []
_count = 0

# 화면 함수 → (해시 경로, 있어야 할 글). {pid} 등은 실행 때 채운다.
SCREENS: dict[str, tuple[str, str]] = {
    "viewProjects": ("", "screens-demo"), "viewHarnesses": ("harnesses", "하네스"), "viewProject": ("p/{pid}", "결정 있는 task"),
    "viewOrchestration": ("p/{pid}/orch", "본문이 보인다"), "viewConfirmations": ("p/{pid}/confirmations", "확인 부탁"),
    "viewIdeas": ("p/{pid}/ideas", "적어 둔 생각"), "viewRoadmap": ("p/{pid}/roadmap", "열린 마일스톤"), "viewCallsign": ("p/{pid}/c/bot-a", "bot-a"), "viewGuide": ("p/{pid}/guide", "지침"),
    "viewWiki": ("p/{pid}/w", "위키 한 장"), "viewKnowledge": ("p/{pid}/k/{ref}", "위키 한 장"), "viewDcrs": ("p/{pid}/dcr", "결정 하나"),
    "viewWikiPage": ("p/{pid}/wp/topics%2Fone.md", "위키 한 장"), "viewTask": ("p/{pid}/t/{tid}", "답이 반영된다"), "viewEvents": ("p/{pid}/events", "register"),
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
                        b"document.body.dataset.text=d.innerText},4000)</script>")
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
    must("hub_wiki_ingest", {"pages": [{"path": "topics/one.md", "body": "---\ntitle: 위키 한 장\n---\n\n# 위키 한 장\n\n본문\n", "expected_version": 0}], "summary": "한 장"}, owner)
    dcr = must("hub_dcr_create", {"title": "결정 하나", "rationale": "이유", "proposal": "제안", "target_refs": []}, bot)
    assert dcr
    miles = [("M-001", "끝난 마일스톤", 1), ("M-003", "예정 마일스톤", 2), ("M-002", "열린 마일스톤", 3), ("M-004", "병렬 마일스톤", 4)]

    def roadmap(version: int, first: str) -> None:
        status = {"M-001": first, "M-002": "in_progress", "M-003": "planned", "M-004": "in_progress"}
        must("hub_roadmap_put", {"path": "index.md", "expected_version": version, "body": "# Roadmap — s\n\n## Milestones\n\n" + "".join(
            f"- **{i}** [implementation] {t} — status: {status[i]}\n  - path: [`./{i}-x.md`](./{i}-x.md)\n" for i, t, _ in miles)}, owner)
        for i, t, n in miles:
            must("hub_roadmap_put", {"path": f"{i}-x.md", "expected_version": version, "body": f"---\nid: {i}\ntitle: {t}\nsdlc_phase: implementation\nstatus: {status[i]}\n"
                                     f"order: {n}\nparallel_allowed: [M-001, M-002, M-003, M-004]\ndeliverables: []\n---\n\n# {i}\n\n## WBS\n\n- **WBS-{n}.1** 작업 {n}\n"}, owner)

    roadmap(0, "in_progress")
    must("hub_idea_add", {"body": "적어 둔 생각"}, bot)
    t1 = must("hub_task_create", {"title": "끝난 일", "wbs": "M-001/WBS-1.1", "fields": {"done_criteria": ["끝"]}}, owner)["task"]
    must("hub_task_claim", {"id": t1["id"]}, owner)
    t1 = must("hub_task_get", {"id": t1["id"]}, owner)["task"]
    must("hub_task_close", {"id": t1["id"], "expected_version": t1["version"], "validation_result": "확인"}, owner)
    roadmap(1, "done")  # done 선언은 task 가 끝난 뒤 (그 전에는 WBS 게이트가 task 를 막는다)
    must("hub_approval_request", {"session": sw, "title": "확인 부탁", "question": "할까요?"}, bot)
    must("hub_project_doc_put", {"name": "purpose", "body": DOC_OLD, "expected_version": 0}, owner)
    must("hub_project_doc_put", {"name": "profile", "body": "옛 프로필\n", "expected_version": 0}, owner)
    must("hub_approval_request", {"session": sw, "title": "문서", "question": "쓸까요?", "action": {
        "type": "project_doc_put", "name": "purpose", "body": DOC_NEW, "expected_version": 1}}, bot)
    must("hub_approval_request", {"session": sw, "title": "제\u202e목", "question": "질\u200b문", "details": "설\u2066명", "action": {
        "type": "project_doc_put", "name": "profile", "body": "새 프로필\n", "expected_version": 1}}, bot)
    must("hub_project_doc_put", {"name": "profile", "body": "그 사이 바뀜\n", "expected_version": 1}, owner)  # 요청을 낡게 한다
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
        for n, body in (("a", {"title": "알림 제목", "text": "본문이 보인다\u200b"}), ("b", "문자열 본문\u2066")):
            c.execute("INSERT INTO inbox_message (project_id,id,to_kind,to_id,from_callsign,from_session,from_orchestrator,kind,body_json,ref_task,state,"
                      "delivered_via,delivered_at,created_at) VALUES (?,?,'session',?,'owner-a',?,1,'note',?,?,'unacknowledged','piggyback',?,?)",
                      (pid, f"MSG-20261122-{n * 12}", sw, so, json.dumps(body, ensure_ascii=False), tid, "2026-11-22T00:00:00+00:00", "2026-11-22T00:00:00+00:00"))
    with sqlite3.connect(db) as c:  # 객체가 아닌 본문의 approval 이 확인 요청 화면을 막지 않는다
        for n, raw in (("d", '"글"'), ("e", "[1]")):
            c.execute("INSERT INTO inbox_message (project_id,id,to_kind,to_id,from_callsign,from_session,from_orchestrator,kind,body_json,state,created_at) "
                      "VALUES (?,?,'callsign','owner-a','bot-a','',0,'approval',?,'queued',?)", (pid, f"MSG-20261121-{n * 12}", raw, "2026-11-21T00:00:00+00:00"))
    found = must("hub_knowledge_search", {"query": "위키"}, owner)
    ref = next((str(x.get("ref")) for x in found.get("results") or found.get("hits") or []), "")
    from urllib.parse import quote
    return {"owner": owner, "bot": bot, "pid": pid, "tid": tid, "ref": quote(ref, safe=""), "cookie": head.get("set-cookie", "").split(";", 1)[0], "host": host}


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
        rm = doms["viewRoadmap"]
        fold = rm.find('data-keep="rm-done"')
        at = [rm.find(f"<h2>{t} 마일스톤") for t in ("열린", "병렬", "예정", "끝난")]
        _record(f"[{impl}] 로드맵 — 현재 · 진행 중 · 예정 · 완료 순", at[0] > 0 and at == sorted(at), f"{at}")
        kept = draw(exe, tmp, port, f"p/{env['pid']}/roadmap", "@rm-done", 14000)
        folds = re.findall(r'<details[^>]*data-keep="rm-done"[^>]*>', kept)
        _record(f"[{impl}] 자동 갱신이 펼친 접기를 닫지 않는다", len(folds) == 1 and " open" in folds[0] and 'data-renders="1"' in kept, f"{folds}")
        _record(f"[{impl}] 로드맵 — 열린 것 먼저 · 완료는 접기", 0 < rm.find("<h2>열린 마일스톤") < fold < rm.find("<h2>끝난 마일스톤"), f"접기 {fold}")
        orch = doms["viewOrchestration"]
        _record(f"[{impl}] 오케스트레이션 — 메시지 본문", all(x in orch for x in ("알림 제목", "본문이 보인다", "문자열 본문")))
        _record(f"[{impl}] 오케스트레이션 — 지시문 · 메시지의 보이지 않는 문자", [orch.count(f">{u}</mark>") for u in ("U+202E", "U+FFFC", "U+200B", "U+2066")] == [2, 2, 1, 1])
        _record(f"[{impl}] 오케스트레이션 — 정리 안내문", "세션이 끝났으면 같은 콜사인" in orch and "hub_inbox_ack(decision=seen)" in orch and "읽음으로 정리" in orch)
        guide = doms["viewGuide"]
        _record(f"[{impl}] 지침 제안 — 보이지 않는 문자", guide.count(">U+202E</mark>") == 1 and guide.count(">U+200B</mark>") == 1
                and re.search(r'<pre class="diff exact">[^<]*\+새 규<mark', guide) is not None)
        exact = {v: re.findall(r'data-exact="([^"]*)"', doms[v])[:1] for v in ("viewConfirmations", "viewOrchestration", "viewGuide")}
        _record(f"[{impl}] 승인 글은 저장된 순서 · 공백 그대로", all(x == ["bidi-override/pre-wrap"] for x in exact.values()), f"{exact}")
        conf = doms["viewConfirmations"]
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
        acts = ["승인", "거절", "세션 인계 (transfer)", "전체 정지 (halt)", "정지 풀기 (resume)", "거두기", "lease 해제", "오케스트레이터 지정", "중계 초대 코드 발급"]
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
