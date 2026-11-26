#!/usr/bin/env python3
"""워크벤치 결정 폼을 실제 브라우저로 누른다 — 보지 않은 결정에 추천값이 나가지 않는다 (TASK-2026-11-26-claude-plex-009).

HTTP 검사(``check_workbench_write``)는 서버가 고르지 않은 결정을 422 로 받는지를 잰다. 이 검사는 화면 쪽이다:
라디오가 미리 골라져 있으면 사람이 펼쳐 보지 않은 결정까지 한 번의 '응답 보내기' 로 나간다 — 그 기본값은 HTML 만
읽어서는 확인할 수 없고(``checked`` 는 속성 하나), 보내기 단추를 끄는 것은 스크립트다. Chrome headless ``--dump-dom``.
브라우저가 없으면 **미측정**이라고 알린다 — 통과로 세지 않는다.

1. 처음 연 계획 화면 — 고른 라디오 0 · '응답 보내기' 꺼짐 · 'N건 중 0건' 표시 · '정본은 허브' 안내와 허브 링크
2. 결정 하나만 '추천 받아들이기' — 1건 골랐다 · 여전히 꺼짐 (나머지를 보지 않았다)
3. 나머지도 고르면 켜지고, 보내면 POST 하나 · 받은편지함 응답 하나 · 두 결정 모두 ``opened: yes``
4. 칩 · 꼬리표 글자 대비 ≥ 4.5 — 밝은 테마는 렌더된 색으로, 어두운 테마는 CSS 토큰 쌍으로
"""

from __future__ import annotations

CHECK_TIMEOUT_S = 180

WATCHES = (
    "workflow-source/workflow_kit/*",
    "workflow-source/pyproject.toml",
    "workflow-source/tests/_workbench_fixture.py",
)

import json
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import traceback
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _workbench_fixture as fx  # noqa: E402

FAILURES: list[str] = []
CSS = fx.SOURCE_ROOT / "workflow_kit" / "workbench" / "static" / "workbench.css"
HUB = "https://hub.example.test/workflow"
PROJECT = "P-20261121-fcfdccb1"


def _record(case: str, problems: list[str]) -> None:
    print(f"  {'PASS' if not problems else 'FAIL'}  {case}")
    for p in problems:
        print(f"        - {p}")
    if problems:
        FAILURES.append(case)


def browser() -> str | None:
    return next((p for n in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser") if (p := shutil.which(n))), None)


def _lum(rgb: str) -> float:
    hexes = rgb.lstrip("#")
    vals = [int(hexes[i:i + 2], 16) / 255 for i in (0, 2, 4)] if rgb.startswith("#") else \
        [int(x) / 255 for x in re.findall(r"\d+", rgb)[:3]]
    lin = [v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in vals]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def contrast(a: str, b: str) -> float:
    la, lb = sorted((_lum(a), _lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


PROBE = r"""<!doctype html><meta charset=utf-8><iframe id=f width=900 height=1600 src="%(path)s"></iframe><script>
const z=t=>new Promise(r=>setTimeout(r,t));
(async()=>{await z(2000);const d=f.contentDocument,out={};const form=d.querySelector('form.respond');
const st=()=>({checked:[...form.querySelectorAll('input[type=radio]:checked')].map(r=>r.name+'='+r.value),
  disabled:d.getElementById('respond-submit').disabled,count:d.getElementById('pick-count').textContent});
out.first=st();const note=d.querySelector('.hub-note');out.note=note?[note.textContent,(note.querySelector('a')||{}).href||null]:null;
out.chips=[...d.querySelectorAll('.chip,.badge')].filter(e=>e.getClientRects().length).map(e=>{const c=getComputedStyle(e);return [e.textContent.trim().slice(0,20),c.color,c.backgroundColor]});
const dec=[...d.querySelectorAll('details.decision.open')];out.decisions=dec.map(x=>x.dataset.decision);
dec[0].open=true;await z(100);dec[0].querySelector('button[data-pick]').click();await z(100);out.one=st();
for(const x of dec.slice(1)){x.open=true;await z(100);x.querySelector('button[data-pick]').click();await z(100);}
out.all=st();out.opened=[...form.querySelectorAll('input[name^=opened_]')].map(i=>i.name+'='+i.value);
d.getElementById('respond-submit').click();await z(2500);
out.posts=await (await fetch('/__posts')).json();
document.body.dataset.out=JSON.stringify(out);})().catch(e=>{document.body.dataset.out=JSON.stringify({error:String(e)})});
</script>"""


def _proxy(upstream: int, ctl: dict[str, Any]) -> ThreadingHTTPServer:
    class P(BaseHTTPRequestHandler):
        def log_message(self, *_a: Any) -> None:
            return

        def _reply(self, code: int, body: bytes, headers: list[tuple[str, str]]) -> None:
            self.send_response(code)
            for k, v in headers:
                if k.lower() not in ("content-length", "transfer-encoding", "connection"):
                    self.send_header(k, v)
            self.send_header("content-length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _go(self) -> None:
            if self.path == "/__probe":
                return self._reply(200, ctl["probe"].encode(), [("content-type", "text/html; charset=utf-8")])
            if self.path == "/__posts":
                return self._reply(200, json.dumps(ctl["posts"]).encode(), [("content-type", "application/json")])
            size = int(self.headers.get("content-length") or 0)
            data = self.rfile.read(size) if size else None
            if self.command == "POST":
                ctl["posts"].append(self.path)
            hdrs = {k: v for k, v in self.headers.items() if k.lower() not in ("connection", "content-length", "accept-encoding")}
            req = urllib.request.Request(f"http://127.0.0.1:{upstream}{self.path}", method=self.command, headers=hdrs, data=data)

            class NoRedirect(urllib.request.HTTPRedirectHandler):
                def redirect_request(self, *_a: Any, **_k: Any) -> None:
                    return None

            opener = urllib.request.build_opener(NoRedirect)
            try:
                with opener.open(req, timeout=20) as r:
                    code, body, headers = r.status, r.read(), list(r.headers.items())
            except urllib.error.HTTPError as e:
                code, body, headers = e.code, e.read(), list(e.headers.items())
            # 감싼 쪽(같은 출처 iframe)에서 재려면 프레임 금지만 걷는다 — 나머지 CSP(script-src 'self' 등)는 그대로 둔다.
            kept: list[tuple[str, str]] = []
            for k, v in headers:
                if k.lower() == "x-frame-options":
                    continue
                if k.lower() == "content-security-policy":
                    v = "; ".join(d for d in v.split(";") if not d.strip().startswith("frame-ancestors"))
                kept.append((k, v))
            self._reply(code, body, kept)

        do_GET = do_POST = _go

    srv = ThreadingHTTPServer(("127.0.0.1", 0), P)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def _dark_tokens() -> dict[str, str]:
    css = CSS.read_text(encoding="utf-8")
    block = css.split("@media (prefers-color-scheme: dark)", 1)[1].split("}", 2)[0]
    return dict(re.findall(r"--([\w-]+):\s*(#[0-9a-fA-F]{6})", block))


def main() -> int:
    print("=== 워크벤치 결정 폼 (실브라우저) ===")
    exe = browser()
    # 4 (어두운 테마) — 토큰 쌍. 칩은 .76rem 작은 글자라 4.5 기준.
    dark = _dark_tokens()
    pairs = [("ok", "ok-soft"), ("info", "info-soft"), ("warn", "warn-soft"), ("bad", "bad-soft"), ("muted", "neutral-soft"),
             ("muted", "surface"), ("accent-fg", "accent")]
    low = [f"{a}/{b} {contrast(dark[a], dark[b]):.2f}" for a, b in pairs if contrast(dark[a], dark[b]) < 4.5]
    _record("case 4b (어두운 테마 칩 · 꼬리표 · 주 단추 토큰 쌍 대비 ≥ 4.5)", low)
    if exe is None:
        print("  SKIP: Chrome 없음 — case 1~3 · 4a 미측정 (통과 아님)")
        return 1 if FAILURES else 0

    with fx.temp_workspace("wb-dec-") as td:
        ws = fx.make_workspace(td)
        marker = ws / "ai-workflow" / "HUB_MIGRATED.json"
        marker.write_text(json.dumps({"format": "workflow-hub-migrated/1", "hub": HUB, "project_id": PROJECT}), encoding="utf-8")
        (ws / ".git").mkdir()  # 표식 탐색은 git 뿌리에서 멈춘다 — 이 저장소 밖으로 올라가지 않게
        task_id = fx.create_task(ws)
        ctl: dict[str, Any] = {"posts": [], "probe": PROBE % {"path": f"/task/{task_id}"}}
        with fx.running(ws, open_name="tester") as srv:
            proxy = _proxy(srv.port, ctl)
            try:
                # Chrome 은 프로필 안에 유닉스 소켓을 만든다 — 러너의 긴 임시 경로 아래 깊이 두면 경로 한도(~107자)를 넘어 죽는다
                prof = Path(tempfile.mkdtemp(prefix="c", dir=tempfile.gettempdir()))
                r = subprocess.run([exe, "--headless=new", "--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage", "--no-first-run",
                                    "--password-store=basic", "--disable-background-networking", "--no-proxy-server",
                                    "--window-size=1200,1800", f"--user-data-dir={prof}", "--virtual-time-budget=30000",
                                    "--dump-dom", f"http://127.0.0.1:{proxy.server_address[1]}/__probe"],
                                   capture_output=True, encoding="utf-8", errors="replace", timeout=90)
            finally:
                proxy.shutdown()
                shutil.rmtree(prof, ignore_errors=True)
        m = re.search(r'data-out="([^"]*)"', r.stdout)
        out: dict[str, Any] = json.loads(m.group(1).replace("&quot;", '"').replace("&amp;", "&")) if m else \
            {"error": f"결과 없음 rc={r.returncode} err={r.stderr[-300:]!r}"}
        if "error" in out:
            _record("측정", [str(out["error"])])
            return 1
        inbox = fx.inbox_snapshot(ws)
        bodies = [p.read_text(encoding="utf-8") for p in fx.pr.inbox_dir(fx.branch_dir(ws)).iterdir()
                  if p.is_file() and p.name in inbox]

    first, one, every = out["first"], out["one"], out["all"]
    total = len(out["decisions"])
    p1 = []
    if first["checked"]:
        p1.append(f"처음부터 골라진 라디오: {first['checked']}")
    if not first["disabled"]:
        p1.append("고르기 전에 '응답 보내기' 가 켜져 있다")
    if f"{total}건 중 0건" not in first["count"]:
        p1.append(f"고른 수 표시: {first['count']!r}")
    if not out["note"] or "정본은 허브" not in out["note"][0] or out["note"][1] != f"{HUB}/ui/#/p/{PROJECT}":
        p1.append(f"허브 안내 · 링크: {out['note']}")
    _record(f"case 1 (처음 — 고른 라디오 0 · 보내기 꺼짐 · {total}건 중 0건 · 정본은 허브 안내)", p1)
    _record("case 2 (하나만 추천 받아들이기 — 1건 · 여전히 꺼짐)",
            [] if total >= 2 and len(one["checked"]) == 1 and one["disabled"] and f"{total}건 중 1건" in one["count"]
            else [f"decisions={out['decisions']} one={one}"])
    opened_ok = all(f"opened: yes" in line for b in bodies for line in b.splitlines() if re.match(r"- D\d+ \[", line))
    _record("case 3 (다 고르면 켜짐 · POST 하나 · 응답 하나 · 모두 opened: yes)",
            [] if len(every["checked"]) == total and not every["disabled"] and out["posts"] == [f"/task/{task_id}/respond"]
            and len(bodies) == 1 and opened_ok
            else [f"all={every} posts={out['posts']} inbox={len(bodies)} opened={out['opened']} body={bodies[:1]}"])
    lowl = [f"{t!r} {contrast(c, b):.2f}" for t, c, b in out["chips"] if "rgba(0, 0, 0, 0)" not in b and contrast(c, b) < 4.5]
    _record(f"case 4a (밝은 테마 칩 · 꼬리표 {len(out['chips'])}개 렌더 대비 ≥ 4.5)", lowl if out["chips"] else ["칩 0개 — 미측정"])

    total_cases = 5
    print(f"\n{total_cases - len(FAILURES)}/{total_cases} PASS")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:  # noqa: BLE001
        traceback.print_exc()
        sys.exit(1)
