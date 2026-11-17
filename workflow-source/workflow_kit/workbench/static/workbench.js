// 워크벤치 화면 스크립트 — 인라인 없이 이 파일 하나 (CSP script-src 'self').
// 1) 결정의 <details> 가 처음 열릴 때 그 opened_<D> 를 yes 로 바꾼다 (워크벤치 스펙 §6).
// 2) 자동 새로고침 (스펙 §4.5): body[data-refresh] 초마다 같은 주소를 다시 받아 main 의 data-version 이
//    바뀌었을 때만 main 을 갈아 끼운다. 답을 쓰는 중이면 갈아 끼우지 않고 알림만 낸다.
(function () {
  var dirty = false;

  function bindDecisions(root) {
    root.querySelectorAll("details[data-decision]").forEach(function (el) {
      if (el.getAttribute("data-bound")) { return; }
      el.setAttribute("data-bound", "1");
      el.addEventListener("toggle", function () {
        if (!el.open) { return; }
        var input = document.getElementById("opened_" + el.getAttribute("data-decision"));
        if (input) { input.value = "yes"; dirty = true; }
      });
    });
  }

  function bindForm(root) {
    var form = root.querySelector("form.respond");
    if (!form || form.getAttribute("data-bound")) { return; }
    form.setAttribute("data-bound", "1");
    form.addEventListener("input", function () { dirty = true; });
    form.addEventListener("change", function () { dirty = true; });
  }

  // todo 폼(스펙 §13.1) — 글을 쓰는 중이거나 '고치기' 를 펼쳐 둔 동안은 화면을 갈아 끼우지 않는다.
  function bindTodo(root) {
    root.querySelectorAll("form.todo-add, form.todo-edit").forEach(function (form) {
      if (form.getAttribute("data-bound")) { return; }
      form.setAttribute("data-bound", "1");
      form.addEventListener("input", function () { dirty = true; });
    });
    root.querySelectorAll("details.todo-more").forEach(function (el) {
      if (el.getAttribute("data-bound")) { return; }
      el.setAttribute("data-bound", "1");
      el.addEventListener("toggle", function () { if (el.open) { dirty = true; } });
    });
  }

  function notify() {
    if (document.querySelector(".refresh-notice")) { return; }
    var box = document.createElement("div");
    box.className = "alert warn refresh-notice";
    box.appendChild(document.createTextNode("내용이 바뀌었다 — 쓰던 글은 그대로 두었다. "));
    var button = document.createElement("button");
    button.type = "button";
    button.className = "ghost";
    button.textContent = "새로고침";
    button.addEventListener("click", function () { location.reload(); });
    box.appendChild(button);
    var main = document.querySelector("main");
    main.parentNode.insertBefore(box, main);
  }

  // 3) 쓰기 폼(응답 · todo · 로그인 · 로그아웃)을 fetch POST 로 보낸다 (TASK-2026-11-17-claude-remote-sync-check-234c32-004).
  //    iOS Chrome(CriOS 156 · iPadOS 27)은 이 화면의 폼 제출 페이지 이동을 서버에 보내지 않고 조용히 버렸다 — submit 은
  //    일어나는데 접속이 0 이었고, 같은 화면의 fetch POST 는 닿았다(실측). 스크립트가 없으면 폼이 원래대로 간다.
  function notice(text) {
    var box = document.querySelector(".submit-notice");
    if (!box) {
      box = document.createElement("div");
      box.className = "alert warn submit-notice";
      var main = document.querySelector("main");
      main.parentNode.insertBefore(box, main);
    }
    box.textContent = text;
  }

  function sendForm(form) {
    var buttons = form.querySelectorAll("button[type=submit]");
    var body = new URLSearchParams(new FormData(form)).toString();
    dirty = true; // 보내는 동안 자동 새로고침이 화면을 갈아 끼우지 않는다
    buttons.forEach(function (b) { b.disabled = true; });
    // 주소는 action 속성에서 — todo 폼의 <input name="action"> 이 폼 요소의 action 프로퍼티를 가린다 (실측: POST /task/[object HTMLInputElement])
    var target = new URL(form.getAttribute("action") || "", location.href).href;
    fetch(target, {
      method: "POST", body: body, credentials: "same-origin", redirect: "follow", cache: "no-store",
      headers: { "Content-Type": "application/x-www-form-urlencoded" }
    }).then(function (resp) {
      if (resp.redirected) { location.assign(resp.url); return null; }
      return resp.text().then(function (text) {
        buttons.forEach(function (b) { b.disabled = false; });
        var page = (resp.headers.get("Content-Type") || "").indexOf("text/html") === 0
          ? new DOMParser().parseFromString(text, "text/html") : null;
        var next = page && page.querySelector("main");
        var main = document.querySelector("main");
        if (next && main) {
          // 서버의 오류 화면(403 · 409 …)을 이 자리에 — dirty 는 켠 채라 자동 새로고침이 덮지 않는다
          main.innerHTML = next.innerHTML;
          main.removeAttribute("data-version");
          if (page.title) { document.title = page.title; }
          window.scrollTo(0, 0);
        } else {
          notice(resp.status + " — " + text.trim());
        }
      });
    }).catch(function () {
      buttons.forEach(function (b) { b.disabled = false; });
      notice("보내지 못했다 — 서버에 닿지 않는다. 쓴 내용은 그대로 두었다.");
    });
  }

  document.addEventListener("submit", function (event) {
    var form = event.target;
    if (event.defaultPrevented || !form || (form.getAttribute("method") || "").toLowerCase() !== "post") { return; }
    if (!window.fetch || !window.FormData || !window.URLSearchParams) { return; }
    event.preventDefault();
    sendForm(form);
  });

  document.addEventListener("DOMContentLoaded", function () {
    bindDecisions(document);
    bindForm(document);
    bindTodo(document);
    var seconds = parseInt(document.body.getAttribute("data-refresh") || "0", 10);
    if (!(seconds > 0)) { return; }
    var busy = false;
    setInterval(function () {
      if (busy || document.hidden) { return; }
      busy = true;
      fetch(location.href, { cache: "no-store", credentials: "same-origin", redirect: "manual" })
        .then(function (resp) { return resp.ok ? resp.text() : null; })
        .then(function (text) {
          if (!text) { return; }
          var next = new DOMParser().parseFromString(text, "text/html").querySelector("main");
          var main = document.querySelector("main");
          if (!next || !main || next.getAttribute("data-version") === main.getAttribute("data-version")) { return; }
          if (dirty) { notify(); return; }
          main.innerHTML = next.innerHTML;
          main.setAttribute("data-version", next.getAttribute("data-version"));
          bindDecisions(main);
          bindForm(main);
          bindTodo(main);
        })
        .catch(function () { /* 서버가 잠시 없으면 다음 차례에 다시 본다 */ })
        .then(function () { busy = false; });
    }, seconds * 1000);
  });
})();
