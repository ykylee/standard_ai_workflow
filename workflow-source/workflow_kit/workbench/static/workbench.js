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

  function notify() {
    if (document.querySelector(".refresh-notice")) { return; }
    var box = document.createElement("div");
    box.className = "alert warn refresh-notice";
    box.appendChild(document.createTextNode("내용이 바뀌었다 — 쓰던 답은 그대로 두었다. "));
    var button = document.createElement("button");
    button.type = "button";
    button.className = "ghost";
    button.textContent = "새로고침";
    button.addEventListener("click", function () { location.reload(); });
    box.appendChild(button);
    var main = document.querySelector("main");
    main.parentNode.insertBefore(box, main);
  }

  document.addEventListener("DOMContentLoaded", function () {
    bindDecisions(document);
    bindForm(document);
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
        })
        .catch(function () { /* 서버가 잠시 없으면 다음 차례에 다시 본다 */ })
        .then(function () { busy = false; });
    }, seconds * 1000);
  });
})();
