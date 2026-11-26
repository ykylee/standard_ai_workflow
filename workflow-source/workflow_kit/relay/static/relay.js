// PC 중계 로컬 화면 — 정본은 이 파일 하나 (Go 는 hub-go/internal/relay/static/ 에 바이트 그대로 내장, check_go_assets_sync).
// <head> 에서 동기로 실행된다: 테마를 첫 그리기 전에 정하고, 나머지는 DOMContentLoaded 뒤에.
// confirm() 을 쓰지 않는다 — VS Code webview 의 iframe sandbox 에 allow-modals 가 없어 즉시 false 가 된다
// (실제 VS Code 1.148 실측, TASK-2026-11-26-claude-plex-010). 위험한 동작은 같은 자리 두 번 누름으로 확인한다.
(function () {
  "use strict";
  var THEMES = { light: 1, dark: 1, "hc-light": 1, "hc-dark": 1 };
  try {
    var t = new URLSearchParams(location.search).get("theme");
    if (t && THEMES[t]) document.documentElement.dataset.theme = t;
  } catch (e) { /* 테마는 선택 사항 — 없으면 prefers-color-scheme */ }

  var STATUS_KO = { busy: "일하는 중", idle: "대기", ended: "끝남", unknown: "확인 안 됨" };
  var POLL_MS = 3000;
  var ARM_MS = 6000;
  var HEADERS = { "X-Relay-UI": "1" };

  function $(id) { return document.getElementById(id); }
  function mk(tag, text, cls) {
    var el = document.createElement(tag);
    if (cls) el.className = cls;
    if (text !== undefined && text !== null) el.textContent = String(text);
    return el;
  }
  function hhmmss(d) {
    function p2(n) { return (n < 10 ? "0" : "") + n; }
    return p2(d.getHours()) + ":" + p2(d.getMinutes()) + ":" + p2(d.getSeconds());
  }

  function init() {
    var toggleBtn = $("toggle-btn");
    var msgEl = $("r-msg");      // 일시정지 · 재개 결과 — 그 단추가 있는 머리 카드 안
    var sessMsgEl = $("sess-msg"); // 종료 안내 · 결과 — 누른 종료 단추가 있는 세션 표 바로 아래 (재채점 P2)
    var connEl = $("r-conn");
    var last = null;          // 마지막으로 받은 상태
    var lastOk = null;        // 마지막 성공 시각
    var fails = 0;            // 연속 실패 수
    var armed = null;         // { req, until } — 종료 두 번 누름 대기
    var rowsSig = "";

    function say(text, kind, where) {
      var box = where || msgEl;
      box.className = "alert" + (kind ? " " + kind : "");
      box.textContent = text || "";
    }
    function saySess(text, kind) { say(text, kind, sessMsgEl); }

    // 실패는 코드만 보이지 않는다 — 무엇이 막혔는지와 다음에 할 일을 앞에, 코드는 괄호 안 보조로 (재채점 P2).
    function failText(label, r, stop) {
      var why;
      if (!r.status) why = "중계에 닿지 않는다. 중계(hub relay serve)가 돌고 있는지 확인하고 다시 누른다.";
      else if (r.status === 403) why = "이 화면에서 보낸 요청으로 확인되지 않아 막혔다. 이 창을 새로고침한 뒤 다시 누른다.";
      else if (r.status === 404 && stop) why = "이 세션은 이미 끝났다. 목록이 곧 갱신된다 — 할 일은 없다.";
      else if (r.status >= 500) why = "중계가 처리하다 실패했다" + (r.message ? " (" + r.message + ")" : "") + ". 아래 로그를 보고 다시 누른다.";
      else why = (r.message ? r.message + ". " : "") + "다시 누르고, 계속되면 아래 로그를 본다.";
      return label + " 실패 — " + why + (r.status ? " (HTTP " + r.status + ")" : "");
    }

    function renderConn() {
      var fresh = $("r-fresh");
      fresh.textContent = lastOk ? "마지막 확인 " + hhmmss(lastOk) : "";
      if (fails >= 2) {
        var ago = lastOk ? Math.round((Date.now() - lastOk.getTime()) / 1000) + "초 전" : "한 번도 못 받음";
        var text = "중계에 닿지 않는다 — 마지막 확인 " + (lastOk ? hhmmss(lastOk) + " (" + ago + ")" : ago) +
          ". 아래 내용은 그때 값이다. 중계(hub relay serve)가 돌고 있는지 확인한다.";
        if (connEl.textContent !== text) connEl.textContent = text;
        var st = $("r-status");
        st.className = "chip stale";
        st.textContent = "확인 안 됨";
        toggleBtn.disabled = true;
      } else if (connEl.textContent) {
        connEl.textContent = "";
      }
    }

    function sessionRow(x, active) {
      var tr = mk("tr");
      tr.append(mk("td", x.alias || "—", "c-alias"));
      var stTd = mk("td", null, "c-status");
      var status = String(x.status || "unknown");
      stTd.appendChild(mk("span", STATUS_KO[status] || status, "chip " + status));
      tr.appendChild(stTd);
      var cells = [["c-harness", "하네스", x.harness], ["c-id", "요청", x.request], ["c-pid", "pid", x.pid],
        ["c-session", "허브 세션", x.session || "—"]];
      for (var i = 0; i < cells.length; i++) {
        var td = mk("td", cells[i][2], cells[i][0]);
        td.dataset.label = cells[i][1];
        tr.appendChild(td);
      }
      var act = mk("td", null, "c-act");
      if (active) {
        var isArmed = armed && armed.req === x.request && armed.until > Date.now();
        var b = mk("button", isArmed ? "정말 종료" : "종료", "danger stop-btn" + (isArmed ? " armed" : ""));
        b.type = "button";
        b.dataset.req = x.request;
        b.dataset.step = isArmed ? "confirm" : "arm";
        b.setAttribute("aria-label", (isArmed ? "정말 종료 — " : "종료 — ") + (x.alias || x.request) + " " + x.request);
        act.appendChild(b);
        if (isArmed) {
          var c = mk("button", "취소", "ghost cancel-btn");
          c.type = "button";
          act.appendChild(c);
        }
      }
      tr.appendChild(act);
      return tr;
    }

    function renderSessions(s) {
      var sessions = Array.isArray(s.sessions) ? s.sessions : [];
      var active = sessions.filter(function (x) { return x.status !== "ended"; });
      var ended = sessions.filter(function (x) { return x.status === "ended"; });
      var n = typeof s.active_sessions === "number" ? s.active_sessions : active.length;
      $("sess-title").textContent = "띄운 세션 " + n + " / " + s.max_sessions;
      var sig = JSON.stringify([sessions, armed && armed.until > Date.now() ? armed.req : null]);
      if (sig === rowsSig) return;
      var focusedReq = document.activeElement && document.activeElement.dataset ? document.activeElement.dataset.req : null;
      var focusedCancel = document.activeElement && document.activeElement.classList &&
        document.activeElement.classList.contains("cancel-btn");
      rowsSig = sig;
      var tb = $("sess-body");
      tb.replaceChildren();
      if (!active.length) {
        var td = mk("td", "지금 도는 세션 없음", "empty");
        td.colSpan = 7;
        var tr = mk("tr");
        tr.appendChild(td);
        tb.appendChild(tr);
      } else {
        for (var i = 0; i < active.length; i++) tb.appendChild(sessionRow(active[i], true));
      }
      var eb = $("ended-body");
      eb.replaceChildren();
      for (var j = 0; j < ended.length; j++) eb.appendChild(sessionRow(ended[j], false));
      $("ended-box").hidden = !ended.length;
      $("ended-title").textContent = "끝난 세션 " + ended.length;
      if (focusedReq) {
        var again = tb.querySelector(focusedCancel ? ".cancel-btn" : '.stop-btn[data-req="' + CSS.escape(focusedReq) + '"]');
        if (again) again.focus();
      }
    }

    function renderState(s) {
      last = s;
      $("r-name").textContent = s.name || "—";
      var meta = $("r-meta");
      meta.replaceChildren();
      var parts = [["host", s.host_id], ["프로젝트", s.project_id], ["허브", s.hub],
        ["하네스", (s.harnesses || []).join(", ") || "—"]];
      for (var i = 0; i < parts.length; i++) {
        if (i) meta.append(" · ");
        meta.append(mk("span", parts[i][0] + " " + (parts[i][1] == null ? "—" : parts[i][1])));
      }
      var st = $("r-status");
      st.className = "chip " + (s.paused ? "paused" : "running");
      st.textContent = s.paused ? "일시정지" : "돌고 있음";
      toggleBtn.hidden = false;
      toggleBtn.disabled = false;
      toggleBtn.dataset.action = s.paused ? "resume" : "pause";
      toggleBtn.textContent = s.paused ? "재개" : "일시정지";
      toggleBtn.className = s.paused ? "" : "ghost";
      var links = $("hub-links");
      var hl = s.hub_links || {};
      if (!links.childElementCount && hl.orch) {
        var a1 = mk("a", "중앙 허브 오케스트레이션", "link-btn");
        a1.href = hl.orch; a1.target = "_blank"; a1.rel = "noopener";
        var a2 = mk("a", "프로젝트 화면", "link-btn");
        a2.href = hl.project; a2.target = "_blank"; a2.rel = "noopener";
        links.append(a1, a2);
      }
      renderSessions(s);
      var ul = $("allow-list");
      ul.replaceChildren();
      var allow = s.allow || [];
      if (!allow.length) ul.appendChild(mk("li", "없음"));
      for (var k = 0; k < allow.length; k++) {
        var a = allow[k];
        var li = mk("li");
        li.append(mk("code", a.alias), " ", mk("span", a.path || "", "path"), mk("br"),
          mk("span", (a.harnesses || []).join(", ") + " · " + (a.permission_modes || []).join(", ") +
            " · 세션 " + (a.active_sessions || 0) + " / " + a.max_sessions, "mute"));
        ul.appendChild(li);
      }
      var lp = s.last_poll || {};
      $("poll-line").textContent = "승인은 중앙 허브 화면에서 owner 가 한다 · 마지막 폴링: 내줌 " +
        (lp.dispatch || 0) + " · 전달 " + (lp.deliver || 0);
      var logEl = $("log-box");
      var nextLog = (s.log || []).join("\n") || "—";
      var sel = window.getSelection ? String(window.getSelection()) : "";
      if (!sel && logEl.textContent !== nextLog) {
        var atBottom = logEl.scrollTop + logEl.clientHeight >= logEl.scrollHeight - 8;
        logEl.textContent = nextLog;
        if (atBottom) logEl.scrollTop = logEl.scrollHeight;
      }
    }

    function refresh() {
      return fetch("/api/state", { cache: "no-store" }).then(function (r) {
        if (!r.ok) throw new Error("HTTP " + r.status);
        return r.json();
      }).then(function (s) {
        fails = 0;
        lastOk = new Date();
        renderState(s);
        renderConn();
      }).catch(function () {
        fails += 1;
        renderConn();
      });
    }

    function post(path) {
      return fetch(path, { method: "POST", headers: HEADERS }).then(function (r) {
        return r.json().then(function (b) { return b; }, function () { return {}; }).then(function (b) {
          return { ok: r.ok, status: r.status, message: b && typeof b.message === "string" ? b.message : "" };
        });
      }, function () { return { ok: false, status: 0, message: "" }; });
    }

    toggleBtn.addEventListener("click", function () {
      var action = toggleBtn.dataset.action;
      var label = action === "pause" ? "일시정지" : "재개";
      toggleBtn.disabled = true;
      post("/api/" + action).then(function (r) {
        say(r.ok ? label + "했다." : failText(label, r, false), r.ok ? "ok" : "bad");
        return refresh();
      }).then(function () { if (fails < 2) toggleBtn.disabled = false; });
    });

    $("sess-body").addEventListener("click", function (ev) {
      var t = ev.target;
      if (!t || !t.closest) return;
      if (t.closest(".cancel-btn")) {
        armed = null;
        rowsSig = "";
        saySess("");
        if (last) renderSessions(last);
        return;
      }
      var btn = t.closest(".stop-btn");
      if (!btn) return;
      var reqId = btn.dataset.req;
      if (btn.dataset.step !== "confirm") {
        armed = { req: reqId, until: Date.now() + ARM_MS };
        rowsSig = "";
        saySess(reqId + " 세션을 이 PC 에서 강제 종료하려면 '정말 종료' 를 한 번 더 누른다 (" + ARM_MS / 1000 + "초).", "info");
        if (last) renderSessions(last);
        var again = $("sess-body").querySelector('.stop-btn[data-req="' + CSS.escape(reqId) + '"]');
        if (again) again.focus();
        setTimeout(function () {
          if (armed && armed.req === reqId && armed.until <= Date.now()) {
            armed = null; rowsSig = ""; saySess("");
            if (last) renderSessions(last);
          }
        }, ARM_MS + 50);
        return;
      }
      armed = null;
      rowsSig = "";
      btn.disabled = true;
      post("/api/sessions/" + encodeURIComponent(reqId) + "/stop").then(function (r) {
        saySess(r.ok ? reqId + " 세션을 로컬에서 종료했다." : failText(reqId + " 종료", r, true), r.ok ? "ok" : "bad");
        return refresh();
      });
    });

    refresh();
    setInterval(refresh, POLL_MS);
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
