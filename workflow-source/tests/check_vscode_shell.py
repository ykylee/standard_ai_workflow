#!/usr/bin/env python3
"""VS Code 확장 껍데기 (M-047) — 이 호스트에 VS Code 가 없어 **stub ``vscode`` 모듈 위에서 Node 로** 활성화를 잰다.

계약 정본: ``core/hub_orchestration_spec.md`` §10 · 요구 R22.3 · O8 · DO12 (PURPOSE 예외 — 껍데기만).
실제 VS Code 로드는 게이트 밖 실측이다 (TASK-2026-11-22-main-016 — 내려받은 VS Code 1.147 · xvfb: 이 stub 판정이 놓친
결함 2건을 잡았다 — frame-ancestors 에 작업대 출처 누락 · 스크립트 꺼짐이 중계 화면 버튼을 죽임. 아래 3 · 6 이 그 실측값을 고정한다).

1. 매니페스트 — main 파일 · 명령 ``workflowHub.openRelay`` · 설정 ``relayPort``(8771) · ``engines.vscode``
2. 활성화 (stub, 중계 켜짐) — 상태 표시줄에 세션 수/상한 · 일시정지 · 클릭 명령
3. 명령 — webview 가 iframe 하나로 설정 포트의 중계 화면을 담고, ``portMapping`` 이 그 포트, ``enableScripts`` 켜짐(중계 화면 버튼) ·
   껍데기 문서 CSP 는 ``default-src 'none'`` 에 ``script-src`` 없음(껍데기 자신은 스크립트 0)
4. 중계 꺼짐 — 상태 표시줄 '꺼짐' (예외 없이)
5. 껍데기 — 확장에 화면 로직(표 · 목록 그리기) 없음 · wheel 패키지 목록에 ``editors`` 없음
6. 중계 화면 프레임 정책 — ``frame-ancestors`` 가 정확히 ``'self' vscode-webview: vscode-file://vscode-app`` · ``X-Frame-Options`` 없음 · 와일드카드 없음
"""

from __future__ import annotations

CHECK_TIMEOUT_S = 90

WATCHES = (
    "editors/vscode/*",
    "workflow-source/workflow_kit/*",
    "workflow-source/pyproject.toml",
)

import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
EXT = REPO_ROOT / "editors" / "vscode"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

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


STUB = r"""
const calls = { commands: {}, panels: [], items: [] };
const settings = JSON.parse(process.env.STUB_SETTINGS || "{}");
module.exports = {
  __calls: calls,
  StatusBarAlignment: { Left: 1, Right: 2 },
  ViewColumn: { Active: -1 },
  window: {
    createStatusBarItem: () => { const it = { text: "", tooltip: "", command: "", shown: false, show() { this.shown = true; } }; calls.items.push(it); return it; },
    createWebviewPanel: (id, title, col, opts) => { const p = { id, title, opts, webview: { html: "" } }; calls.panels.push(p); return p; },
  },
  commands: { registerCommand: (name, fn) => { calls.commands[name] = fn; return { dispose() {} }; } },
  workspace: { getConfiguration: () => ({ get: (k, d) => (k in settings ? settings[k] : d) }) },
};
"""

DRIVER = r"""
const path = require("path");
const vscode = require("vscode");
const ext = require(process.env.EXT_MAIN);
(async () => {
  const ctx = { subscriptions: [] };
  await ext.activate(ctx);
  const item = vscode.__calls.items[0] || {};
  const cmd = vscode.__calls.commands["workflowHub.openRelay"];
  const panel = cmd ? cmd() : null;
  for (const s of ctx.subscriptions) { if (s && s.dispose) s.dispose(); }
  console.log(JSON.stringify({ status: { text: item.text, command: item.command, shown: item.shown },
    commands: Object.keys(vscode.__calls.commands),
    panel: panel ? { opts: panel.opts, html: panel.webview.html } : null }));
})().catch((e) => { console.log(JSON.stringify({ error: String(e) })); process.exit(1); });
"""


def _run_node(tmp: Path, port: int) -> dict[str, Any]:
    mod = tmp / "node_modules" / "vscode"
    mod.mkdir(parents=True, exist_ok=True)
    (mod / "index.js").write_text(STUB, encoding="utf-8")
    (tmp / "driver.js").write_text(DRIVER, encoding="utf-8")
    env = {**os.environ, "EXT_MAIN": str(EXT / "extension.js"), "NODE_PATH": str(tmp / "node_modules"),
           "STUB_SETTINGS": json.dumps({"relayPort": port, "statusIntervalSeconds": 5})}
    p = subprocess.run(["node", str(tmp / "driver.js")], capture_output=True, text=True, env=env, timeout=30,
                       encoding="utf-8", errors="replace", cwd=str(tmp))
    try:
        out: dict[str, Any] = json.loads(p.stdout.strip().splitlines()[-1])
        return out
    except (ValueError, IndexError):
        return {"error": f"rc={p.returncode} out={p.stdout[-300:]} err={p.stderr[-300:]}"}


def main() -> int:
    print("=== VS Code 확장 껍데기 (M-047) ===")
    # 1 매니페스트
    pkg = json.loads((EXT / "package.json").read_text(encoding="utf-8"))
    cmds = [c["command"] for c in pkg.get("contributes", {}).get("commands", [])]
    props = pkg.get("contributes", {}).get("configuration", {}).get("properties", {})
    _record("case 1 (매니페스트 — main · 명령 · relayPort 8771 · engines)",
            (EXT / pkg.get("main", "x")).is_file() and cmds == ["workflowHub.openRelay"]
            and props.get("workflowHub.relayPort", {}).get("default") == 8771 and "vscode" in pkg.get("engines", {}),
            f"main={pkg.get('main')} cmds={cmds} props={list(props)}")

    if shutil.which("node") is None:
        _skips.append("case 2~4 (node 없음 — 미측정)")
        print("  case 2~4: SKIP — node 가 없다 (미측정, 통과 아님)")
    else:
        state = {"name": "pc-1", "host_id": "H-1", "paused": True, "max_sessions": 3,
                 "sessions": [{"request": "SR-0001"}, {"request": "SR-0002"}]}

        class H(BaseHTTPRequestHandler):
            def log_message(self, *_a: Any) -> None:
                return

            def do_GET(self) -> None:
                body = json.dumps(state).encode()
                self.send_response(200 if self.path == "/api/state" else 404)
                self.send_header("content-type", "application/json")
                self.end_headers()
                self.wfile.write(body)

        port = _free_port()
        srv = ThreadingHTTPServer(("127.0.0.1", port), H)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        with tempfile.TemporaryDirectory(prefix="vscshell-") as d:
            on = _run_node(Path(d), port)
        srv.shutdown()
        st = on.get("status") or {}
        _record("case 2 (활성화 — 상태 표시줄 세션 2/3 · 일시정지 · 클릭 명령)",
                "중계 2/3" in str(st.get("text")) and "일시정지" in str(st.get("text")) and st.get("shown") is True
                and st.get("command") == "workflowHub.openRelay", str(on)[:300])
        panel = on.get("panel") or {}
        html = str(panel.get("html", ""))
        opts = panel.get("opts") or {}
        shell_csp = (re.findall(r'http-equiv="Content-Security-Policy" content="([^"]+)"', html) or [""])[0]
        _record("case 3 (명령 — iframe 하나 · 설정 포트 · portMapping · enableScripts 켜짐 · 껍데기 CSP 스크립트 0)",
                html.count("<iframe") == 1 and re.findall(r'<iframe[^>]*\ssrc="([^"]+)"', html) == [f"http://localhost:{port}/"]
                and opts.get("portMapping") == [{"webviewPort": port, "extensionHostPort": port}]
                and opts.get("enableScripts") is True and "default-src 'none'" in shell_csp and "script-src" not in shell_csp,
                f"opts={opts} csp={shell_csp!r} html={html[:200]!r}")
        with tempfile.TemporaryDirectory(prefix="vscshell-") as d:
            off = _run_node(Path(d), _free_port())
        _record("case 4 (중계 꺼짐 — '꺼짐' · 예외 없음)", "error" not in off and "꺼짐" in str((off.get("status") or {}).get("text")),
                str(off)[:200])

    # 5 껍데기
    src = (EXT / "extension.js").read_text(encoding="utf-8")
    drawing = [m for m in ("<table", "<tr", "<li", ".map(", "innerHTML") if m in src]
    pyproject = (SOURCE_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    _record("case 5 (껍데기 — 화면 로직 없음 · wheel 밖)", not drawing and "editors" not in pyproject
            and not (SOURCE_ROOT / "workflow_kit" / "editors").exists(), f"drawing={drawing}")

    # 6 중계 화면 프레임 정책 (실제 relay/ui.py)
    with tempfile.TemporaryDirectory(prefix="vscshell-ui-") as d:
        os.environ["WORKFLOW_HUB_RELAY_HOME"] = d
        from workflow_kit.relay.ui import serve as serve_ui

        class FakeRelay:
            session_of: dict[str, str] = {}
            handles: dict[str, Any] = {}
            alias_of: dict[str, str] = {}
            last: dict[str, Any] = {}
            recent: list[str] = []

            def log(self, _m: str) -> None:
                return

        uport = _free_port()
        srv2 = serve_ui(FakeRelay(), uport)  # type: ignore[arg-type]
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{uport}/", timeout=5) as r:
                csp = r.headers.get("content-security-policy") or ""
                xfo = r.headers.get("x-frame-options")
        finally:
            srv2.shutdown()
    fa = next((d.split()[1:] for d in csp.split(";") if d.split()[:1] == ["frame-ancestors"]), None)
    _record("case 6 (중계 화면 프레임 — 자신 · VS Code webview · 데스크톱 작업대만 · XFO 없음 · 와일드카드 없음)",
            fa is not None and sorted(fa) == sorted(["'self'", "vscode-webview:", "vscode-file://vscode-app"])
            and xfo is None and "*" not in csp, f"csp={csp!r} xfo={xfo!r}")

    total = len(_passes) + len(_failures)
    print(f"\n{len(_passes)}/{total} passed" + (f" · 미측정 {len(_skips)}" if _skips else ""))
    if _failures:
        for f in _failures:
            print(f"  ✗ {f}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
