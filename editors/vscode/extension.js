// @ts-check
// 워크플로우 허브 PC 중계 — VS Code 확장 **껍데기** (core/hub_orchestration_spec.md §10, 요구 R22.3 · O8 · DO12).
// 하는 일은 셋뿐이다: ① 중계 로컬 화면을 webview 의 iframe 으로 띄운다 ② 상태 표시줄에 중계 상태(활성 세션 수 · 일시정지)를 보인다
// ③ VS Code 테마 종류를 iframe 주소의 ?theme= 로 넘긴다.
// 화면 로직(HTML 생성 · 판정)은 중계(Python) 한 벌이다 — 여기서 그리지 않는다. PURPOSE 의 non-Python 예외는 이 범위뿐이다.
"use strict";

const vscode = require("vscode");
const http = require("http");

const HOST = "127.0.0.1";

/** @returns {number} */
function relayPort() {
  return Number(vscode.workspace.getConfiguration("workflowHub").get("relayPort", 8771));
}

/** 중계 상태를 읽는다 — 실패하면 null (중계가 꺼져 있음). @param {number} port */
function readState(port) {
  return new Promise((resolve) => {
    const req = http.get({ host: HOST, port, path: "/api/state", timeout: 3000 }, (res) => {
      let body = "";
      res.setEncoding("utf8");
      res.on("data", (c) => (body += c));
      res.on("end", () => {
        try {
          resolve(res.statusCode === 200 ? JSON.parse(body) : null);
        } catch {
          resolve(null);
        }
      });
    });
    req.on("timeout", () => req.destroy());
    req.on("error", () => resolve(null));
  });
}

/** 상태 표시줄 문구 — 숫자 두 개만 옮긴다 (판정은 중계 몫). @param {any} s */
function statusText(s) {
  if (!s) return { text: "$(debug-disconnect) 중계 꺼짐", tooltip: "중계가 돌지 않는다 — hub relay serve --ui-port" };
  // 활성 세션만 센다 — 끝난 세션은 자리를 차지하지 않는다 (중계가 active_sessions 를 낸다; 옛 중계면 ended 를 뺀다).
  const n = typeof s.active_sessions === "number" ? s.active_sessions
    : Array.isArray(s.sessions) ? s.sessions.filter((x) => x && x.status !== "ended").length : 0;
  return {
    text: `${s.paused ? "$(debug-pause)" : "$(radio-tower)"} 중계 ${n}/${s.max_sessions ?? "?"}${s.paused ? " · 일시정지" : ""}`,
    tooltip: `${s.name ?? ""} · ${s.host_id ?? ""} — 클릭하면 중계 화면`,
  };
}

/** VS Code 테마 종류 → 중계 화면 테마 이름. iframe(다른 출처)은 --vscode-* 변수를 못 읽고, webview 안의
 * prefers-color-scheme 도 VS Code 테마를 따르지 않는다(1.148 실측: 어두운 테마에서 false) — 그래서 확장이 넘긴다.
 * @param {number | undefined} kind */
function themeName(kind) {
  return { 1: "light", 2: "dark", 3: "hc-dark", 4: "hc-light" }[kind ?? 0] || "";
}

/** webview 본문 — 중계 화면을 그대로 담는 iframe 하나. @param {number} port @param {string} [theme] */
function webviewHtml(port, theme) {
  const src = `http://localhost:${port}/${theme ? `?theme=${encodeURIComponent(theme)}` : ""}`;
  return `<!doctype html><html><head><meta charset="utf-8">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; frame-src http://localhost:${port}/ http://127.0.0.1:${port}/; style-src 'unsafe-inline';">
<style>html,body,iframe{margin:0;padding:0;border:0;width:100%;height:100%}</style></head>
<body><iframe src="${src}" title="PC 중계"></iframe></body></html>`;
}

/** @param {vscode.ExtensionContext} context */
function activate(context) {
  const item = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 50);
  item.command = "workflowHub.openRelay";
  context.subscriptions.push(item);

  const refresh = async () => {
    const t = statusText(await readState(relayPort()));
    item.text = t.text;
    item.tooltip = t.tooltip;
    item.show();
  };

  /** @type {Set<vscode.WebviewPanel>} */
  const panels = new Set();
  const currentTheme = () => themeName(vscode.window.activeColorTheme && vscode.window.activeColorTheme.kind);
  if (vscode.window.onDidChangeActiveColorTheme) {
    context.subscriptions.push(vscode.window.onDidChangeActiveColorTheme(() => {
      for (const p of panels) p.webview.html = webviewHtml(relayPort(), currentTheme());
    }));
  }

  context.subscriptions.push(
    vscode.commands.registerCommand("workflowHub.openRelay", () => {
      const port = relayPort();
      const panel = vscode.window.createWebviewPanel("workflowHubRelay", "PC 중계", vscode.ViewColumn.Active, {
        // 껍데기 문서 자신은 CSP(default-src 'none', script-src 없음)로 스크립트를 못 돌린다. enableScripts 는 webview 의
        // sandbox 에 allow-scripts 를 주는 것이라, 꺼 두면 그 안에 담긴 중계 화면(다른 출처 iframe)의 일시정지 버튼 JS 까지
        // 죽는다 — 실제 VS Code 1.147 실측 (TASK-2026-11-22-main-016).
        enableScripts: true,
        portMapping: [{ webviewPort: port, extensionHostPort: port }],
      });
      panel.webview.html = webviewHtml(port, currentTheme());
      panels.add(panel);
      if (panel.onDidDispose) panel.onDidDispose(() => panels.delete(panel));
      return panel;
    })
  );

  const seconds = Math.max(5, Number(vscode.workspace.getConfiguration("workflowHub").get("statusIntervalSeconds", 15)));
  const timer = setInterval(refresh, seconds * 1000);
  context.subscriptions.push({ dispose: () => clearInterval(timer) });
  return refresh();
}

function deactivate() {}

module.exports = { activate, deactivate, statusText, webviewHtml, themeName };
