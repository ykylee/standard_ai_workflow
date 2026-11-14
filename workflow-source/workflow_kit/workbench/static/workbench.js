// 결정의 <details> 가 처음 열릴 때 그 opened_<D> 를 yes 로 바꾸는 일 하나만 한다 (워크벤치 스펙 §6).
document.addEventListener("DOMContentLoaded", function () {
  document.querySelectorAll("details[data-decision]").forEach(function (el) {
    el.addEventListener("toggle", function () {
      if (!el.open) { return; }
      var input = document.getElementById("opened_" + el.getAttribute("data-decision"));
      if (input) { input.value = "yes"; }
    });
  });
});
