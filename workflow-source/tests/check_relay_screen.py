#!/usr/bin/env python3
"""PC 중계 로컬 화면을 실제 브라우저로 그린다 (TASK-2026-11-26-claude-plex-010).

정본은 ``workflow_kit/relay/static/relay.{html,css,js}`` — Go 중계는 같은 바이트를 내장한다(``check_go_assets_sync``).
실제 ``relay/ui.serve`` 앞에 프록시를 두고, 같은 출처의 감싼 쪽(iframe 폭 고정)에서 화면을 재고 누른다. Chrome headless ``--dump-dom``.
브라우저가 없으면 **미측정**이라고 알린다 — 통과로 세지 않는다.

fixture 는 운영 상한을 채운다: 활성 세션 3(= ``MAX_SESSIONS``) · 끝난 세션 2 · 긴 별칭 · 실제 꼴 ID(``SR-NNNN`` · ``S-YYYYMMDD-xxxxxxxx``).

폭 3개(900 · 520 · 390 — VS Code 패널 · 좁은 패널 · 휴대폰) × 테마마다:
1. 페이지 가로 넘침 0 · 글자 단위로 꺾인 낱말 0 (표 칸 · 칩 · 단추 · 제목 · 메타)
2. 활성 세션만 센다(``3 / 3``) · 끝난 세션은 접힌 묶음 · 상태 칩은 한국어
3. 테마 — ``?theme=`` 가 ``<html data-theme>`` 로, 주 단추(accent 위 on-accent) 대비 ≥ 4.5
4. 종료 두 번 누름 — 첫 누름은 POST 없이 '정말 종료' 로 무장, 3초 갱신이 지나도 무장 유지, 둘째 누름에 POST 하나
5. 연결 끊김 — /api/state 가 실패하기 시작하면 2회부터 aria-live 경보 · 상태 '확인 안 됨' · 마지막 확인 시각
6. ``confirm(`` · ``alert(`` · ``prompt(`` 를 쓰지 않는다 (VS Code webview sandbox 에 allow-modals 가 없다 — 실측)
7. 종료 안내 · 결과는 누른 단추가 있는 세션 카드 안, 표 바로 아래에 뜬다 — 머리 카드 알림은 비어 있다 (재채점 P2)
8. 종료 실패는 코드만이 아니라 다음 행동을 말한다 — 500 은 로그 보고 다시, 404 는 이미 끝남 · 할 일 없음 (재채점 P2)
"""

from __future__ import annotations

CHECK_TIMEOUT_S = 240

WATCHES = (
    "workflow-source/workflow_kit/*",
    "workflow-source/pyproject.toml",
)

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
STATIC = SOURCE_ROOT / "workflow_kit" / "relay" / "static"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))


def browser() -> str | None:
    return next((p for n in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser") if (p := shutil.which(n))), None)


_fails: list[str] = []
_count = 0


def _record(case: str, ok: bool, detail: str = "") -> None:
    global _count
    _count += 1
    if not ok:
        _fails.append(f"{case}: {detail}")
    print(f"  {'PASS' if ok else 'FAIL'}: {case}{(' — ' + detail) if detail and not ok else ''}")


def _lum(rgb: str) -> float:
    vals = [int(x) / 255 for x in re.findall(r"\d+", rgb)[:3]]
    lin = [v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in vals]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def contrast(a: str, b: str) -> float:
    la, lb = sorted((_lum(a), _lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def fixture() -> dict[str, Any]:
    def sess(n: int, alias: str, harness: str, status: str, sid: str | None) -> dict[str, Any]:
        return {"request": f"SR-{n:04d}", "alias": alias, "harness": harness, "pid": 3_900_000 + n, "status": status,
                "session": sid, "harness_session_id": None}

    return {
        "hub": "https://hub.homelab.example:8770", "host_id": "H-20261126-9f3a2c1b", "project_id": "P-20261121-fcfdccb1",
        "name": "yklee-workstation-linux", "harnesses": ["claude-code", "codex"], "paused": False,
        "sessions": [sess(12, "frontend-monorepo", "claude-code", "busy", "S-20261126-41773183"),
                     sess(13, "결제-서비스", "codex", "idle", "S-20261126-5be0aa17"),
                     sess(14, "standard_ai_workflow", "claude-code", "busy", None),
                     sess(9, "frontend-monorepo", "claude-code", "ended", "S-20261125-0c1d2e3f"),
                     sess(10, "결제-서비스", "codex", "ended", None)],
        "max_sessions": 3, "active_sessions": 3,
        "allow": [{"alias": "frontend-monorepo", "path": "/home/yklee/work/clients/acme/frontend-monorepo-with-a-long-directory-name",
                   "harnesses": ["claude-code"], "permission_modes": ["default", "acceptEdits"], "max_sessions": 2, "active_sessions": 1},
                  {"alias": "결제-서비스", "path": "/home/yklee/work/결제-서비스", "harnesses": ["codex"], "permission_modes": ["default"],
                   "max_sessions": 1, "active_sessions": 1},
                  {"alias": "standard_ai_workflow", "path": "/home/yklee/repos/standard_ai_workflow", "harnesses": ["claude-code", "codex"],
                   "permission_modes": ["default"], "max_sessions": 3, "active_sessions": 1}],
        "last_poll": {"dispatch": 0, "deliver": 1, "halted": []},
        "log": [f"2026-11-26T10:{i:02d}:00 세션 SR-{i:04d} 상태 확인 — 하네스 claude-code 응답 정상 (긴 줄 {'가' * 40})" for i in range(30)],
        "hub_links": {"project": "https://hub.homelab.example:8770/ui/#/p/P-20261121-fcfdccb1",
                      "orch": "https://hub.homelab.example:8770/ui/#/p/P-20261121-fcfdccb1/orch"},
    }


PROBE = r"""<!doctype html><meta charset=utf-8><iframe id=f width=%(w)d height=1400 src="/?theme=%(theme)s"></iframe><script>
const z=t=>new Promise(r=>setTimeout(r,t));
(async()=>{await z(1500);const d=f.contentDocument,out={};
const de=d.documentElement;out.overflow=de.scrollWidth-de.clientWidth;out.theme=de.dataset.theme||null;
const broken=[];
for(const el of d.querySelectorAll('h1,h2,th,td,.chip,button,.meta span,summary,code,.link-btn,#poll-line,.fresh')){
  if(!el.getClientRects().length)continue;
  const tw=d.createTreeWalker(el,NodeFilter.SHOW_TEXT);let n;
  while((n=tw.nextNode())){if(n.parentElement.closest('pre,.path'))continue;const re=/\S+/g;let m;
    while((m=re.exec(n.data))){const r=d.createRange();r.setStart(n,m.index);r.setEnd(n,m.index+m[0].length);
      const tops=new Set([...r.getClientRects()].filter(x=>x.width>0).map(x=>Math.round(x.top)));if(tops.size>1)broken.push(m[0]);}}}
out.broken=[...new Set(broken)];
out.title=d.getElementById('sess-title').textContent;out.chips=[...d.querySelectorAll('#sess-body .chip')].map(x=>x.textContent);
out.ended=d.getElementById('ended-title').textContent;out.endedOpen=d.getElementById('ended-box').open;out.endedHidden=d.getElementById('ended-box').hidden;
const tb=d.getElementById('toggle-btn'),cs=getComputedStyle(tb);out.toggle=[tb.textContent,tb.className,cs.color,cs.backgroundColor];
const b=d.querySelector('#sess-body .stop-btn');b.click();await z(200);
out.armed=[...d.querySelectorAll('#sess-body tr:first-child .c-act button')].map(x=>x.textContent);out.posts1=await (await fetch('/__posts')).json();
await z(3600);out.armedAfterPoll=[...d.querySelectorAll('#sess-body tr:first-child .c-act button')].map(x=>x.textContent);
out.armedCount=d.querySelectorAll('#sess-body .stop-btn.armed').length;d.querySelector('#sess-body .stop-btn.armed').click();await z(900);out.posts2=await (await fetch('/__posts')).json();
out.msg=d.getElementById('sess-msg').textContent;out.topMsg=d.getElementById('r-msg').textContent;
const sm=d.getElementById('sess-msg'),tbl=d.getElementById('sess-body').closest('table');
out.near=[!!sm.closest('.card')&&sm.closest('.card')===tbl.closest('.card')&&sm.closest('.card')!==d.getElementById('r-msg').closest('.card'),Math.round(sm.getBoundingClientRect().top-tbl.getBoundingClientRect().bottom)];
const fail=async(code)=>{await fetch('/__stopfail?'+code);const x=d.querySelectorAll('#sess-body .stop-btn')[1];x.click();await z(200);
d.querySelector('#sess-body .stop-btn.armed').click();await z(900);return [d.getElementById('sess-msg').textContent,d.getElementById('sess-msg').className];};
out.fail500=await fail(500);out.fail404=await fail(404);await fetch('/__stopfail?0');
out.connBefore=d.getElementById('r-conn').textContent;
await fetch('/__fail');await z(3200);out.connAfter1=d.getElementById('r-conn').textContent;await z(3200);
const c=d.getElementById('r-conn');out.conn=[c.textContent,c.getAttribute('aria-live'),getComputedStyle(c).display];
out.status=d.getElementById('r-status').textContent;out.fresh=d.getElementById('r-fresh').textContent;
document.body.dataset.out=JSON.stringify(out);})().catch(e=>{document.body.dataset.out=JSON.stringify({error:String(e)})});
</script>"""


def main() -> int:
    print("=== PC 중계 화면 (실브라우저) ===")
    js = (STATIC / "relay.js").read_text(encoding="utf-8")
    code_only = re.sub(r"//[^\n]*", "", js)
    _record("case 6 (모달 대화상자 안 씀 — confirm · alert · prompt)",
            not re.search(r"\b(confirm|alert|prompt)\s*\(", code_only), "relay.js 에 모달 호출")

    exe = browser()
    if exe is None:
        print("  SKIP: Chrome 없음 — case 1~5 · 7 · 8 미측정 (통과 아님)")
        print(f"\n{_count - len(_fails)}/{_count} passed · 미측정 7")
        return 1 if _fails else 0

    with tempfile.TemporaryDirectory(prefix="relayscr-") as tmp:
        os.environ["WORKFLOW_HUB_RELAY_HOME"] = tmp
        from workflow_kit.relay import ui

        state = fixture()
        stops: list[str] = []
        ui.state = lambda _relay: state  # type: ignore[assignment]

        class _Stub:
            def stop(self, h: Any) -> None:
                stops.append(h.req)

        class _Adapters:
            @staticmethod
            def get(_name: str) -> _Stub:
                return _Stub()

        ui.adapters = _Adapters  # type: ignore[assignment]

        class _H:
            harness = "fake"

            def __init__(self, req: str) -> None:
                self.req = req

            def alive(self) -> bool:
                return True

        class _Relay:
            handles = {x["request"]: _H(x["request"]) for x in state["sessions"]}

            def log(self, _m: str) -> None:
                return

        with __import__("socket").socket() as s:
            s.bind(("127.0.0.1", 0))
            uport = int(s.getsockname()[1])
        usrv = ui.serve(_Relay(), uport)  # type: ignore[arg-type]
        ctl: dict[str, Any] = {"fail": False, "posts": [], "probe": "", "stopfail": 0}

        class P(BaseHTTPRequestHandler):
            def log_message(self, *_a: Any) -> None:
                return

            def _reply(self, code: int, body: bytes, ctype: str) -> None:
                self.send_response(code)
                self.send_header("content-type", ctype)
                self.send_header("content-length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def _go(self) -> None:
                if self.path == "/__probe":
                    return self._reply(200, ctl["probe"].encode(), "text/html; charset=utf-8")
                if self.path == "/__posts":
                    return self._reply(200, json.dumps(ctl["posts"]).encode(), "application/json")
                if self.path.startswith("/__stopfail?"):
                    ctl["stopfail"] = int(self.path.split("?", 1)[1])
                    return self._reply(200, b"{}", "application/json")
                if ctl["stopfail"] and self.command == "POST" and self.path.endswith("/stop"):
                    self.rfile.read(int(self.headers.get("content-length") or 0))
                    msg = {"error_code": "io_error", "message": "relay-state.json 을 쓰지 못했다"} if ctl["stopfail"] >= 500 else {"error_code": "not_found", "message": "실행 중인 세션이 없다"}
                    return self._reply(ctl["stopfail"], json.dumps(msg, ensure_ascii=False).encode(), "application/json")
                if self.path == "/__fail":
                    ctl["fail"] = True
                    return self._reply(200, b"{}", "application/json")
                if ctl["fail"] and self.path.startswith("/api/"):
                    return self._reply(502, b"{}", "application/json")
                size = int(self.headers.get("content-length") or 0)
                if self.command == "POST":
                    ctl["posts"].append(self.path)
                hdrs = {k: v for k, v in self.headers.items() if k.lower() in ("x-relay-ui", "content-type")}
                if self.headers.get("origin"):
                    hdrs["origin"] = f"http://127.0.0.1:{uport}"
                req = urllib.request.Request(f"http://127.0.0.1:{uport}{self.path}", method=self.command, headers=hdrs,
                                             data=self.rfile.read(size) if size else None)
                try:
                    with urllib.request.urlopen(req, timeout=10) as r:
                        code, body, ctype = r.status, r.read(), r.headers.get("content-type") or ""
                except urllib.error.HTTPError as e:
                    code, body, ctype = e.code, e.read(), e.headers.get("content-type") or ""
                self._reply(code, body, ctype)

            do_GET = do_POST = _go

        psrv = ThreadingHTTPServer(("127.0.0.1", 0), P)
        threading.Thread(target=psrv.serve_forever, daemon=True).start()
        base = f"http://127.0.0.1:{psrv.server_address[1]}"
        try:
            for width, theme, paused in ((900, "light", True), (520, "dark", False), (390, "dark", True)):
                tag = f"[{width}px · {theme}]"
                state["paused"] = paused
                ctl.update(fail=False, posts=[], stopfail=0, probe=PROBE % {"w": width, "theme": theme})
                stops.clear()
                prof = Path(tmp) / f"prof-{width}"
                r = subprocess.run([exe, "--headless=new", "--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage", "--no-first-run",
                                    "--password-store=basic", "--disable-background-networking", "--no-proxy-server",
                                    "--window-size=1200,1600", f"--user-data-dir={prof}", "--virtual-time-budget=46000",
                                    "--dump-dom", base + "/__probe"],
                                   capture_output=True, encoding="utf-8", errors="replace", timeout=90)
                m = re.search(r'data-out="([^"]*)"', r.stdout)
                if not m:
                    _record(f"{tag} 측정", False, f"결과 없음 rc={r.returncode} err={r.stderr[-300:]!r}")
                    continue
                out = json.loads(m.group(1).replace("&quot;", '"').replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">"))
                if "error" in out:
                    _record(f"{tag} 측정", False, out["error"])
                    continue
                _record(f"{tag} case 1 (가로 넘침 0 · 글자 단위 꺾임 0)", out["overflow"] <= 0 and not out["broken"],
                        f"overflow={out['overflow']} broken={out['broken'][:8]}")
                _record(f"{tag} case 2 (활성만 센다 · 끝난 세션 접힘 · 한국어 칩)",
                        out["title"] == "띄운 세션 3 / 3" and out["chips"] == ["일하는 중", "대기", "일하는 중"]
                        and out["ended"] == "끝난 세션 2" and out["endedOpen"] is False and out["endedHidden"] is False,
                        f"title={out['title']!r} chips={out['chips']} ended={out['ended']!r} open={out['endedOpen']}")
                fg, bg = out["toggle"][2], out["toggle"][3]
                primary = paused and out["toggle"][1] == ""
                ratio = contrast(fg, bg)
                _record(f"{tag} case 3 (테마 data-theme={theme} · 단추 대비 ≥ 4.5{' · 주 단추' if primary else ''})",
                        out["theme"] == theme and ratio >= 4.5 and (primary or not paused),
                        f"theme={out['theme']} toggle={out['toggle']} ratio={ratio:.2f}")
                _record(f"{tag} case 4 (종료 두 번 누름 — 무장은 POST 0 · 갱신 뒤 유지 · 둘째에 POST 1)",
                        out["armed"] == ["정말 종료", "취소"] and out["armedCount"] == 1 and out["posts1"] == [] and out["armedAfterPoll"] == ["정말 종료", "취소"]
                        and out["posts2"] == ["/api/sessions/SR-0012/stop"] and stops == ["SR-0012"] and "종료했다" in out["msg"],
                        f"armed={out['armed']} posts1={out['posts1']} after={out['armedAfterPoll']} posts2={out['posts2']} "
                        f"stops={stops} msg={out['msg']!r}")
                _record(f"{tag} case 7 (종료 안내 · 결과는 누른 단추의 카드 안 · 표 바로 아래, 머리 카드 알림 비어 있음)",
                        out["near"][0] is True and 0 <= out["near"][1] <= 40 and out["topMsg"] == "" and "종료했다" in out["msg"],
                        f"near={out['near']} top={out['topMsg']!r} msg={out['msg']!r}")
                f5, f4 = out["fail500"], out["fail404"]
                _record(f"{tag} case 8 (종료 실패는 다음 행동을 말한다 — 500 로그 보고 다시 · 404 이미 끝남, 코드는 괄호 보조)",
                        "bad" in f5[1] and "로그를 보고 다시 누른다" in f5[0] and "relay-state.json" in f5[0] and f5[0].endswith("(HTTP 500)")
                        and "이미 끝났다" in f4[0] and "할 일은 없다" in f4[0] and f4[0].endswith("(HTTP 404)")
                        and not re.fullmatch(r".*실패 — HTTP \d+", f5[0]), f"500={f5} 404={f4}")
                _record(f"{tag} case 5 (연결 끊김 — 1회는 조용 · 2회부터 aria-live 경보 · '확인 안 됨' · 마지막 확인)",
                        out["connBefore"] == "" and out["connAfter1"] == "" and "중계에 닿지 않는다" in out["conn"][0]
                        and out["conn"][1] == "assertive" and out["conn"][2] != "none" and out["status"] == "확인 안 됨"
                        and re.fullmatch(r"마지막 확인 \d\d:\d\d:\d\d", out["fresh"]) is not None,
                        f"before={out['connBefore']!r} after1={out['connAfter1']!r} conn={out['conn']} status={out['status']!r} "
                        f"fresh={out['fresh']!r}")
        finally:
            psrv.shutdown()
            usrv.shutdown()

    print(f"\n{_count - len(_fails)}/{_count} passed")
    if _fails:
        for f in _fails:
            print(f"  ✗ {f}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
