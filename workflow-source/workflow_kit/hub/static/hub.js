// 허브 화면 (hub_spec §4.6 · §4.7 · hub_orchestration_spec §10).
// 사람은 허브 계정 세션 쿠키로 로그인한다. 에이전트 콜사인 토큰 입력도 하위 호환으로 남긴다.
// 모든 링크 · API 호출은 상대 경로 (R13.4). DOM 은 textContent 로만 만든다 (서버 문자열을 HTML 로 해석하지 않는다).
"use strict";

(function () {
  const app = document.getElementById("app");
  const crumbs = document.getElementById("crumbs");
  const adminLink = document.getElementById("admin-link");
  const whoEl = document.getElementById("who");
  const live = document.getElementById("live");
  let hubHost = location.host;
  let pendingFlash = null;
  let dirty = false;
  let signedInAccount = false;
  let noticeNode = null;

  // --- 저장소 · 요청 --------------------------------------------------------------

  const keyOf = (pid) => `hub:${hubHost}:${pid}:token`;
  function storedToken(pid) {
    try { return localStorage.getItem(keyOf(pid)); } catch (e) { return null; }
  }
  function storeToken(pid, token) {
    try { localStorage.setItem(keyOf(pid), token); return true; } catch (e) { return false; }
  }
  function forgetToken(pid) {
    try { localStorage.removeItem(keyOf(pid)); } catch (e) { /* 저장소 없음 */ }
  }
  function storedProjects() {
    const out = [];
    try {
      const prefix = `hub:${hubHost}:`;
      for (let i = 0; i < localStorage.length; i++) {
        const k = localStorage.key(i);
        if (k && k.startsWith(prefix) && k.endsWith(":token")) out.push(k.slice(prefix.length, -":token".length));
      }
    } catch (e) { /* 저장소 없음 */ }
    return out;
  }
  function storedAdminToken() {
    try { return localStorage.getItem(`hub:${hubHost}:admin-token`) || ""; } catch (e) { return ""; }
  }
  function storeAdminToken(token) {
    try { localStorage.setItem(`hub:${hubHost}:admin-token`, token); return true; } catch (e) { return false; }
  }

  async function api(path, opts) {
    opts = opts || {};
    const headers = { "accept": "application/json" };
    if (opts.token && (!signedInAccount || opts.forceToken)) headers["authorization"] = "Bearer " + opts.token;
    if (opts.body !== undefined) headers["content-type"] = "application/json";
    const res = await fetch("../api/" + path, {
      method: opts.method || "GET", headers, credentials: "same-origin", cache: "no-store",
      body: opts.body !== undefined ? JSON.stringify(opts.body) : undefined,
    });
    let data = null;
    try { data = await res.json(); } catch (e) { data = { error_code: "bad_response", message: "응답이 JSON 이 아니다" }; }
    return { status: res.status, data };
  }

  // --- DOM · 편집 보호 자동 갱신 ----------------------------------------------------

  function el(tag, attrs, ...children) {
    const node = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs || {})) {
      if (v === undefined || v === null || v === false) continue;
      if (k === "class") node.className = v;
      else if (k === "text") node.textContent = v;
      else if (k.startsWith("on")) node.addEventListener(k.slice(2), v);
      else node.setAttribute(k, v === true ? "" : String(v));
    }
    for (const c of children.flat()) {
      if (c === undefined || c === null || c === false) continue;
      node.append(c instanceof Node ? c : document.createTextNode(String(c)));
    }
    return node;
  }
  function when(iso) {
    if (!iso) return null;
    const d = new Date(iso);
    if (isNaN(d)) return el("span", {}, iso);
    const z = (n) => String(n).padStart(2, "0");
    return el("time", { datetime: iso, title: iso },
      `${d.getFullYear()}-${z(d.getMonth() + 1)}-${z(d.getDate())} ${z(d.getHours())}:${z(d.getMinutes())}`);
  }
  // 상태 낱말 — 화면은 한국어 하나로 말하고, 원래 값은 title 에 남긴다 (PRODUCT.md 원칙 2).
  const STATUS_LABEL = {
    planned: "예정", in_progress: "진행 중", blocked: "막힘", done: "끝남", idle: "대기", working: "일하는 중", waiting: "기다림",
    ended: "끝남", open: "열림", pending: "대기", pending_approval: "승인 대기", approved: "승인됨", rejected: "거절됨", declined: "거절함",
    returned: "돌려받음", offered: "제안됨", accepted: "수락함", dispatched: "보냄", reported: "보고됨", answered: "답함", proposed: "제안됨",
    unknown: "신호 끊김", failed: "실패", halted: "정지", refused_by_host: "PC 가 거절", unack: "미확인", unacknowledged: "미확인",
    queued: "대기", delivered: "전달됨", acked: "읽음", high: "높음", medium: "보통", low: "낮음",
    note: "알림", spawn: "세션 띄우기", stop: "멈춤", assignment: "배정", approval: "승인 요청",
  };
  const statusLabel = (s) => STATUS_LABEL[s] || s;
  const PHASE_LABEL = { concept: "구상", requirements: "요구 사항", design: "설계", implementation: "구현", release: "발행", operations: "운영", operation: "운영" };
  const VIA_LABEL = { http: "API", ui: "화면", mcp: "MCP", relay: "PC 중계", cli: "명령줄", a2a: "A2A", piggyback: "다른 응답에 덧붙여", wait: "대기 중 받음", push: "바로 보냄" };
  const OP_LABEL = { create: "만듦", update: "고침", claim: "맡음", release: "놓음", close: "닫음", progress: "진행 기록", link_commit: "커밋 연결",
    register: "등록", approve: "승인", reject: "거절", declare: "지정", transfer: "넘김", delete: "지움", archive: "보관", respond: "응답" };
  const viaLabel = (v) => VIA_LABEL[v] || v;
  const chip = (text, cls) => STATUS_LABEL[text]
    ? el("span", { class: "chip " + (cls || text), title: text }, STATUS_LABEL[text])
    : el("span", { class: "chip " + (cls || text) }, text);
  const alertBox = (kind, text, ...extra) => el("div", { class: "alert " + kind, role: kind === "bad" ? "alert" : "status" }, text, ...extra);

  function hideRefreshNotice() {
    if (noticeNode) { noticeNode.remove(); noticeNode = null; }
  }
  function showRefreshNotice() {
    if (noticeNode) return;
    const btn = el("button", { type: "button", class: "ghost", onclick: () => { dirty = false; hideRefreshNotice(); route(); } }, "지금 새로고침");
    noticeNode = el("div", { class: "alert warn refresh-notice", role: "status" },
      "쓰거나 펼쳐 둔 내용이 있어 자동 새로고침을 잠시 멈췄다 — 최신 상태를 보려면 새로고침을 누른다.", btn);
    document.body.insertBefore(noticeNode, app);
  }
  let renderedHash = null;
  function markDirty() { dirty = true; }

  app.addEventListener("input", markDirty);
  app.addEventListener("change", markDirty);

  function render(...nodes) {
    // 요청이 오가는 동안 쓰기 시작했으면 같은 화면을 다시 그리지 않는다 — 적던 글을 지우지 않게.
    if (dirty && renderedHash === location.hash) { showRefreshNotice(); return; }
    renderedHash = location.hash;
    const flash = pendingFlash;
    pendingFlash = null;
    // 동작 결과는 늘 있는 live 영역으로도 읽힌다 — 새로 그린 알림 상자는 보조기술이 놓칠 수 있다.
    if (live) live.textContent = flash ? flash.text : "";
    hideRefreshNotice();
    // 배열을 그대로 넘기면 '[object HTMLElement]' 글자가 된다 — 펼쳐서 넣는다. 자동 갱신은 펼쳐 둔 접기를 닫지 않는다.
    const open = new Set([...app.querySelectorAll("details[data-keep][open]")].map((d) => d.dataset.keep));
    app.replaceChildren(...(flash ? [alertBox(flash.kind, flash.text)] : []),
      ...nodes.flat(Infinity).filter((node) => node !== null && node !== undefined && node !== false));
    app.querySelectorAll("details[data-keep]").forEach((d) => { if (open.has(d.dataset.keep)) d.open = true; });
  }
  function setCrumbs(items) {
    crumbs.replaceChildren(...items.flatMap((it, i) => [i ? el("span", {}, "›") : null,
      it.href ? el("a", { href: it.href }, it.text) : el("span", {}, it.text)]).filter(Boolean));
  }
  function setWho(principal) {
    if (!principal) { whoEl.textContent = ""; return; }
    if (principal.kind === "admin") { whoEl.textContent = `허브 관리자 ${principal.name || ""}`; return; }
    if (principal.kind === "account") { whoEl.textContent = `허브 계정 ${principal.name || ""}`; return; }
    if (principal.auth_mode === "account") { whoEl.textContent = `허브 계정 ${principal.account?.display_name || principal.name || ""}`; return; }
    if (principal.kind === "callsign") {
      whoEl.textContent = `${principal.callsign} (${principal.callsign_kind === "human" ? "사람" : "에이전트"}${principal.callsign_kind === "human" && !principal.human_approved ? " · 승인 전" : ""} · ${{ owner: "소유자", editor: "편집자", viewer: "읽기 전용" }[principal.role] || principal.role})`;
    } else {
      whoEl.textContent = `공용 읽기 전용 토큰`;
    }
  }
  function errorText(r) {
    const d = r.data || {};
    let msg = `${r.status} ${d.error_code || ""} — ${d.message || ""}`;
    if (r.status === 401) msg += " · 허브 계정으로 로그인하거나 유효한 콜사인 토큰을 확인한다.";
    return msg;
  }

  function projectNav(pid, active) {
    const base = `#/p/${encodeURIComponent(pid)}`;
    const tabs = [
      ["tasks", "개요 · task", base],
      ["orch", "오케스트레이션", `${base}/orch`],
      ["ideas", "아이디어", `${base}/ideas`],
      ["confirmations", "확인 요청", `${base}/confirmations`],
      ["roadmap", "로드맵", `${base}/roadmap`],
      ["events", "이력", `${base}/events`],
      ["guide", "지침", `${base}/guide`],
      ["wiki", "지식", `${base}/w`],
      ["dcr", "결정 변경", `${base}/dcr`],
    ];
    return el("nav", { class: "nav-links", "aria-label": "프로젝트 판" },
      tabs.map(([id, label, href]) => el("a", { href, class: active === id ? "on" : "" }, label)));
  }

  // --- 토큰 넣기 · 등록 · 지우기 ------------------------------------------------------

  function tokenForm(onDone) {
    const input = el("input", { type: "text", placeholder: "wfh_…", autocomplete: "off", "aria-label": "콜사인 토큰" });
    const msg = el("div");
    return el("form", { class: "row", onsubmit: async (ev) => {
      ev.preventDefault();
      const token = input.value.trim();
      if (!token) return;
      const r = await api("session", { token });
      if (r.status !== 200 || r.data.principal.kind !== "callsign") { msg.replaceChildren(alertBox("bad", errorText(r))); return; }
      storeToken(r.data.principal.project_id, token);
      input.value = "";
      dirty = false;
      onDone(r.data.principal.project_id);
    } }, el("label", {}, "토큰 넣기", input), el("button", { type: "submit" }, "이 브라우저에 저장"), msg);
  }

  function accountPanel(account, onDone) {
    const status = el("div");
    if (account) {
      const linkToken = el("input", { type: "password", required: true, autocomplete: "off", placeholder: "wfh_…" });
      const joinProject = el("input", { type: "text", required: true, autocomplete: "off", placeholder: "P-… 또는 github.com/…" });
      const joinCallsign = el("input", { type: "text", required: true, autocomplete: "off", placeholder: "예: yk-desk" });
      return el("section", { class: "card" }, el("h2", {}, "허브 계정"),
        el("p", {}, `${account.display_name} (${account.username})로 로그인됨`),
        el("form", { class: "row", onsubmit: async (ev) => { ev.preventDefault(); const r = await api("account/join", { method: "POST", body: { project: joinProject.value.trim(), callsign: joinCallsign.value.trim() } }); if (r.status !== 200) { status.replaceChildren(alertBox("bad", errorText(r))); return; } pendingFlash = { kind: "ok", text: `${r.data.joined.callsign}로 참여를 요청했다 — 프로젝트 소유자가 승인하면 결정에 답할 수 있다.` }; dirty = false; onDone(); } }, el("label", { class: "field" }, "프로젝트 ID 또는 git 주소", joinProject), el("label", { class: "field" }, "쓸 콜사인", joinCallsign), el("button", { type: "submit" }, "프로젝트 참여 요청")),
        el("form", { class: "row", onsubmit: async (ev) => { ev.preventDefault(); const r = await api("account/link", { method: "POST", token: linkToken.value.trim(), forceToken: true, body: {} }); if (r.status !== 200) status.replaceChildren(alertBox("bad", errorText(r))); else { linkToken.value = ""; status.replaceChildren(alertBox("ok", `콜사인을 연결했다: ${r.data.linked.callsign}`)); onDone(); } } }, el("label", { class: "field" }, "다른 프로젝트의 승인된 사람 콜사인 토큰", linkToken), el("button", { type: "submit" }, "콜사인 연결")), status,
        el("button", { class: "ghost", onclick: async () => { const r = await api("account/logout", { method: "POST", body: {} }); if (r.status === 200) { signedInAccount = false; location.hash = "#/"; onDone(); } else status.replaceChildren(alertBox("bad", errorText(r))); } }, "로그아웃"));
    }
    const loginUser = el("input", { type: "text", required: true, autocomplete: "username" });
    const loginPass = el("input", { required: true, type: "password", autocomplete: "current-password" });
    const enrollToken = el("input", { type: "password", autocomplete: "off", placeholder: "wfh_…" });
    const enrollUser = el("input", { type: "text", required: true, autocomplete: "username" });
    const enrollName = el("input", { type: "text", required: true, autocomplete: "name" });
    const enrollPass = el("input", { required: true, type: "password", autocomplete: "new-password", minlength: "8" });
    return el("section", { class: "card" }, el("h2", {}, "허브 계정 로그인"),
      el("p", { class: "muted" }, "처음이면 토큰 없이 바로 가입한다. 가입 뒤 프로젝트에 참여하면 소유자가 승인한다. 이미 사람 콜사인 토큰이 있으면 함께 넣어 바로 연결한다."),
      el("form", { class: "row", onsubmit: async (ev) => { ev.preventDefault(); const r = await api("account/login", { method: "POST", body: { username: loginUser.value, password: loginPass.value } }); if (r.status !== 200) status.replaceChildren(alertBox("bad", errorText(r))); else { signedInAccount = true; dirty = false; onDone(); } } }, el("label", { class: "field" }, "계정 이름", loginUser), el("label", { class: "field" }, "비밀번호", loginPass), el("button", { type: "submit" }, "로그인")),
      el("details", {}, el("summary", {}, "새 계정 만들기"),
        el("form", { class: "row", onsubmit: async (ev) => { ev.preventDefault(); const r = await api("account/enroll", { method: "POST", token: enrollToken.value.trim() || undefined, body: { username: enrollUser.value, display_name: enrollName.value, password: enrollPass.value } }); if (r.status !== 200) status.replaceChildren(alertBox("bad", errorText(r))); else { signedInAccount = true; enrollToken.value = ""; dirty = false; onDone(); } } }, el("label", { class: "field" }, "계정 이름", enrollUser), el("label", { class: "field" }, "표시 이름", enrollName),
          el("label", { class: "field" }, "비밀번호 (8자 이상)", enrollPass), el("label", { class: "field" }, "사람 콜사인 토큰 (선택 — 넣으면 바로 연결)", enrollToken), el("button", { type: "submit" }, "가입"))), status);
  }

  function registerForm(pid, onDone) {
    const name = el("input", { type: "text", placeholder: "콜사인 (예: yk-desk)", autocomplete: "off", "aria-label": "콜사인" });
    const kind = el("select", { "aria-label": "종류" }, el("option", { value: "human" }, "사람"), el("option", { value: "agent" }, "에이전트"));
    const label = el("input", { type: "text", placeholder: "설명 (선택)", autocomplete: "off", "aria-label": "설명" });
    const msg = el("div");
    return el("div", {},
      el("form", { class: "row", onsubmit: async (ev) => {
        ev.preventDefault();
        const r = await api(`projects/${encodeURIComponent(pid)}/callsigns`, {
          method: "POST", token: storedToken(pid), body: { callsign: name.value.trim(), kind: kind.value, label: label.value } });
        if (r.status !== 200) { msg.replaceChildren(alertBox("bad", errorText(r))); return; }
        const saved = storeToken(pid, r.data.token);
        dirty = false;
        if (!saved) {
          msg.replaceChildren(alertBox("warn", `등록했지만 이 브라우저에 토큰을 저장하지 못했다. 다시 볼 수 없으니 지금 복사해 둔다: ${r.data.token}`));
          return;
        }
        pendingFlash = { kind: "ok", text: `${r.data.callsign} 로 등록했다 — 토큰은 이 브라우저에만 있고 다시 나오지 않는다.${r.data.human_pending ? " 사람 콜사인은 소유자가 승인하기 전까지 결정에 답할 수 없다." : ""}` };
        onDone();
      } }, name, kind, label, el("button", { type: "submit" }, "콜사인 등록")), msg);
  }

  function forgetButton(pid, onDone) {
    return el("button", { class: "ghost", type: "button", onclick: () => {
      if (!confirm("이 브라우저에서 콜사인 토큰을 지운다. 토큰은 허브가 다시 내주지 않는다 — 다시 쓰려면 새 콜사인을 등록한다. 지울까?")) return;
      forgetToken(pid);
      dirty = false;
      onDone();
    } }, "이 브라우저에서 콜사인 지우기");
  }

  // --- 화면: 프로젝트 목록 -------------------------------------------------------------

  async function viewProjects() {
    setCrumbs([{ text: "프로젝트" }]);
    const seen = new Map();
    let principal = null;
    const errors = [];
    const adminToken = storedAdminToken();
    if (adminToken) {
      const session = await api("session", { token: adminToken });
      if (session.status === 200 && session.data.principal.kind === "admin") principal = session.data.principal;
      else if (session.status === 401 || session.status === 403 || session.status === 200) {
        try { localStorage.removeItem(`hub:${hubHost}:admin-token`); } catch (e) { /* 저장소 없음 */ }
      } else errors.push(`관리자 세션 확인: ${errorText(session)}`);
    }
    const projectList = await api("projects", { token: principal?.kind === "admin" ? adminToken : undefined });
    if (projectList.status === 200) { principal = principal || projectList.data.principal; projectList.data.projects.forEach((p) => seen.set(p.id, p)); }
    if (!signedInAccount) for (const pid of storedProjects()) {
      const r = await api("projects", { token: storedToken(pid) });
      if (r.status === 200) r.data.projects.forEach((p) => seen.set(p.id, p));
      else errors.push(`${pid}: ${errorText(r)}`);
    }
    setWho(principal);
    adminLink.textContent = principal?.kind === "admin" ? "관리 화면" : "관리자 모드";
    const cards = [...seen.values()].map((p) => el("a", { class: "card", href: `#/p/${encodeURIComponent(p.id)}` },
      el("h2", {}, p.display_name),
      el("div", { class: "mono muted" }, p.id),
      el("div", { class: "row" }, ...["in_progress", "blocked", "planned", "done"].map((s) => chip(`${statusLabel(s)} ${p.task_counts[s] || 0}`, s))),
      storedToken(p.id) ? el("div", { class: "muted" }, "이 브라우저에 콜사인 토큰 있음") : null));
    render(
      accountPanel(projectList.status === 200 && projectList.data.account ? projectList.data.account : null, () => route()),
      el("section", { class: "card" }, el("h1", {}, "프로젝트"),
        cards.length ? el("div", { class: "grid" }, cards)
          : el("p", { class: "muted" }, projectList.status === 401
            ? "로그인하지 않으면 프로젝트가 보이지 않는다 (허브 기본 설정). 허브 계정으로 로그인하거나 콜사인 토큰을 넣는다."
            : "등록된 프로젝트가 없다.")),
      el("section", { class: "card admin-entry" }, el("div", {}, el("h2", {}, "허브 전체 관리"),
        el("p", { class: "muted" }, "하네스 등록 제보를 검토하고 사람 담당자 명부와 계정 관리자 권한을 관리한다. 관리자 토큰이나 관리자 계정이 필요하다.")),
        el("a", { class: "admin-entry-button", href: "#/harnesses" }, principal?.kind === "admin" ? "관리 화면 열기" : "관리자 로그인")),
      errors.length ? el("section", { class: "card" }, errors.map((e) => alertBox("bad", e))) : null,
      el("section", { class: "card" }, el("h2", {}, "이 브라우저에 콜사인 토큰 넣기"), tokenForm(() => route())));
  }

  async function viewHarnesses() {
    setCrumbs([{ text: "프로젝트", href: "#/" }, { text: "하네스 등록 검토" }]);
    const token = storedAdminToken();
    // 관리자 권한이 있는 계정으로 로그인했으면 토큰 없이 쿠키 세션으로 연다 (admin 토큰과 같은 권한).
    const accountSession = token ? null : await api("session");
    const viaAccount = accountSession?.status === 200 && accountSession.data.principal.kind === "admin";
    if (!token && !viaAccount) {
      const input = el("input", { type: "password", autocomplete: "off", placeholder: "관리자 토큰", "aria-label": "관리자 토큰" });
      const message = el("div");
      setWho(null); adminLink.textContent = "관리자 로그인";
      render(el("section", { class: "card" }, el("h1", {}, "허브 관리자 로그인"),
        el("p", {}, "허브 관리자 토큰으로 하네스 제보를 검토하고 사람 담당자 명부를 관리한다. 관리자 권한을 받은 허브 계정으로 로그인했다면 토큰 없이 열린다."),
        el("h2", {}, "관리자 토큰 발급"),
        el("p", { class: "muted" }, "토큰은 허브 서버에서 한 번 발급한다. Python 또는 Go 허브 터미널에서 실행한다."),
        el("pre", {}, "Python: python -m workflow_kit hub admin --db <DB 경로> token issue --role admin --name <이름>\nGo: workflow-hub admin --db <DB 경로> token issue --role admin --name <이름>"),
        el("p", { class: "muted" }, "로그인하면 토큰은 이 브라우저에 저장된다. 공유 기기에서는 사용 후 관리자 토큰을 지운다."),
        el("form", { class: "row", onsubmit: async (ev) => {
          ev.preventDefault();
          const submitted = input.value.trim();
          const r = await api("session", { token: submitted });
          if (r.status !== 200 || r.data.principal.kind !== "admin") {
            const reason = r.status === 200 ? "이 토큰에는 허브 관리자 권한이 없다. 콜사인 토큰이나 공용 읽기 토큰이 아니라 관리자 토큰을 넣는다."
              : r.status === 401 || r.status === 403 ? "토큰을 확인할 수 없다. 허브 관리자 토큰을 다시 확인한다." : errorText(r);
            message.replaceChildren(alertBox("bad", reason)); return;
          }
          if (!storeAdminToken(submitted)) { message.replaceChildren(alertBox("bad", "브라우저 저장소에 토큰을 보관할 수 없다. 브라우저 저장소 설정을 확인한다.")); return; }
          input.value = ""; dirty = false; route();
        } }, el("label", {}, "관리자 토큰", input), el("button", { type: "submit" }, "관리자 모드로 로그인"), message)));
      return;
    }
    const [session, reportsRes, peopleRes, registryRes, accountsRes] = await Promise.all([
      api("session", { token }), api("harness-reports?status=pending", { token }),
      api("harness-people", { token }), api("harness-registry", { token }), api("accounts", { token })]);
    if (session.status !== 200 || session.data.principal.kind !== "admin") {
      const invalid = session.status === 401 || session.status === 403 || session.status === 200;
      if (invalid) { try { localStorage.removeItem(`hub:${hubHost}:admin-token`); } catch (e) { /* 저장소 없음 */ } }
      render(el("section", { class: "card" }, alertBox("bad", invalid ? "관리자 토큰이 유효하지 않다. 새 토큰으로 로그인한다." : `관리자 세션을 확인할 수 없다. 토큰은 보존했다. ${errorText(session)}`),
        el("button", { onclick: () => { route(); } }, invalid ? "다시 로그인" : "다시 확인")));
      return;
    }
    setWho(session.data.principal);
    adminLink.textContent = "관리 화면";
    if ([reportsRes, peopleRes, registryRes, accountsRes].some((r) => r.status !== 200)) {
      render(el("section", { class: "card" }, alertBox("bad", errorText([reportsRes, peopleRes, registryRes, accountsRes].find((r) => r.status !== 200))))); return;
    }
    const people = peopleRes.data.people || [];
    const registry = new Map((registryRes.data.harnesses || []).map((h) => [h.harness_id, h]));
    const displayName = el("input", { type: "text", maxlength: "100", placeholder: "사람 담당자 이름", "aria-label": "사람 담당자 이름" });
    const addMessage = el("div");
    const addPerson = el("form", { class: "row", onsubmit: async (ev) => {
      ev.preventDefault();
      const r = await api("harness-people", { method: "POST", token, body: { display_name: displayName.value.trim() } });
      if (r.status !== 200) { addMessage.replaceChildren(alertBox("bad", errorText(r))); return; }
      displayName.value = ""; dirty = false; route();
    } }, el("label", {}, "사람 명부에 등록", displayName), el("button", { type: "submit" }, "사람 추가"), addMessage);
    const cards = (reportsRes.data.reports || []).map((report) => {
      const existing = registry.get(report.harness_id);
      const selectedIds = new Set((existing?.owners || []).map((p) => p.id));
      const ownerSelect = el("select", { multiple: true, size: String(Math.min(6, Math.max(2, people.length))), "aria-label": "하네스 담당자 여러 명 선택" },
        people.map((p) => el("option", { value: p.id, selected: selectedIds.has(p.id) }, `${p.display_name} · ${p.id}`)));
      const setup = report.report || {};
      const entryCandidates = setup.entry_file_candidates || [];
      const configCandidates = setup.mcp_config_candidates || [];
      const supportsProfile = (setup.config_formats || []).includes("mcp-http-json-v1")
        && (setup.mcp_transports || []).includes("streamable-http") && entryCandidates.length > 0 && configCandidates.length > 0;
      const entryFile = el("select", { "aria-label": "셋업 진입 파일" },
        entryCandidates.map((path) => el("option", { value: path }, path)));
      const configPath = el("select", { "aria-label": "MCP JSON 설정 파일" },
        configCandidates.map((path) => el("option", { value: path }, path)));
      const setupConfirmed = el("input", { type: "checkbox", "aria-label": "셋업 프로필을 검토하고 활성화" });
      const note = el("textarea", { maxlength: "1000", placeholder: "검토 메모 (선택)", "aria-label": "검토 메모" });
      const result = el("div");
      const decide = async (decision) => {
        const owner_ids = decision === "approve" ? [...ownerSelect.selectedOptions].map((o) => o.value) : [];
        if (decision === "approve" && (!supportsProfile || !setupConfirmed.checked)) {
          result.replaceChildren(alertBox("bad", "승인하려면 mcp-http-json-v1 호환 정보와 경로를 확인한 뒤 셋업 프로필 활성화를 체크한다.")); return;
        }
        const r = await api(`harness-reports/${encodeURIComponent(report.id)}/decision`, {
          method: "POST", token, body: { decision, note: note.value.trim(), owner_ids,
            setup_profile: decision === "approve" ? { kind: "mcp-http-json-v1", entry_file: entryFile.value, mcp_config_path: configPath.value } : undefined } });
        if (r.status !== 200) { result.replaceChildren(alertBox("bad", errorText(r))); return; }
        dirty = false; route();
      };
      const data = report.report || {};
      return el("article", { class: "card" }, el("h2", {}, `${data.display_name || report.harness_id} · ${report.harness_id}`),
        el("p", { class: "muted" }, `제보 ${report.id} · 프로젝트 ${report.project_id} · ${report.submitted_by} · ${when(report.submitted_at)}`),
        el("pre", {}, JSON.stringify(data, null, 2)),
        el("label", {}, "사람 담당자 (복수 선택, 최초 등록에 1명 이상 필수)", ownerSelect),
        !people.length ? alertBox("warn", "먼저 사람 명부에 담당자를 등록해야 승인할 수 있다.") : null,
        el("h3", {}, "셋업 지원 프로필 · mcp-http-json-v1"),
        supportsProfile ? el("div", { class: "row" },
          el("label", {}, "진입 파일", entryFile), el("label", {}, "MCP JSON 경로", configPath),
          el("label", {}, setupConfirmed, "이 경로와 Streamable HTTP JSON 호환을 확인하고 셋업 지원 활성화"))
          : alertBox("warn", "자동 셋업을 승인할 정보가 모자란다 — 제보한 쪽이 다시 보내야 한다. (필요: mcp_transports 에 streamable-http, config_formats 에 mcp-http-json-v1, 후보 경로 목록 두 개)"),
        el("label", {}, "검토 메모", note),
        el("div", { class: "row" }, el("button", { disabled: !people.length, onclick: () => decide("approve") }, "담당자를 지정하고 등록 승인"),
          el("button", { class: "danger", onclick: () => decide("reject") }, "거절")), result);
    });
    render(el("section", { class: "card" }, el("h1", {}, "하네스 제보 검토"),
      el("nav", { class: "nav-links" }, el("a", { href: "#/" }, "프로젝트"), el("a", { class: "on", href: "#/harnesses" }, "하네스 검토")),
      el("p", {}, "승인은 사람 명부에 등록된 담당자를 한 명 이상 지정해야 한다."), addPerson,
      token ? el("button", { class: "ghost", onclick: () => { try { localStorage.removeItem(`hub:${hubHost}:admin-token`); } catch (e) { /* 저장소 없음 */ } route(); } }, "관리자 토큰 지우기") : null),
      cards.length ? cards : el("section", { class: "card" }, el("p", { class: "muted" }, "대기 중인 제보가 없다.")),
      accountAdmins(accountsRes.data.accounts || [], token),
      await callsignCleanup(token));
  }

  // 계정 관리자 권한 — 관리자(토큰 또는 관리자 계정)가 주고 거둔다. 거두면 그 계정의 다음 요청부터 일반 계정이다.
  function accountAdmins(accounts, token) {
    const message = el("div");
    const toggle = async (a) => {
      const verb = a.is_admin ? "거둔다" : "준다";
      if (!window.confirm(`${a.display_name} (${a.username}) 계정에 허브 관리자 권한을 ${verb}.`)) return;
      const r = await api(`accounts/${encodeURIComponent(a.username)}/admin`, { method: "POST", token, body: { admin: !a.is_admin } });
      if (r.status !== 200) { message.replaceChildren(alertBox("bad", errorText(r))); return; }
      dirty = false; route();
    };
    return el("section", { class: "card" }, el("h2", {}, "계정 관리자 권한"),
      el("p", { class: "muted" }, "관리자 계정은 로그인만으로 이 관리 화면을 admin 토큰과 같은 권한으로 연다. 첫 관리자는 서버에서 `hub admin account admin --username <계정> --grant` 로 정한다."),
      message,
      accounts.length ? el("table", {}, el("thead", {}, el("tr", {}, ...["계정", "표시 이름", "관리자", "가입", ""].map((h) => el("th", {}, h)))),
        el("tbody", {}, accounts.map((a) => el("tr", { class: a.active ? "" : "archived" },
          el("td", { class: "mono" }, a.username), el("td", {}, a.display_name), el("td", {}, a.is_admin ? "관리자" : "—"),
          el("td", {}, when(a.created_at)),
          el("td", {}, a.active ? el("button", { class: a.is_admin ? "danger" : "", "data-account-admin": a.username, onclick: () => toggle(a) },
            a.is_admin ? "관리자 거두기" : "관리자 주기") : null)))))
        : el("p", { class: "muted" }, "가입한 계정이 없다."));
  }

  // 관리자 콜사인 정리 — 활동이 없는 것만 지워진다 (허브가 판정한다). 활동이 있으면 사유를 보인다.
  async function callsignCleanup(token) {
    const list = await api("projects", { token });
    if (list.status !== 200) return el("section", { class: "card" }, el("h2", {}, "콜사인 정리"), alertBox("bad", errorText(list)));
    const blocks = await Promise.all(list.data.projects.map(async (p) => {
      const r = await api(`projects/${encodeURIComponent(p.id)}/callsigns`, { token });
      if (r.status !== 200) return el("div", {}, el("h3", {}, p.display_name), alertBox("bad", errorText(r)));
      const message = el("div");
      const remove = async (id) => {
        if (window.prompt(`콜사인을 지운다. 되돌릴 수 없다. 확인하려면 ${id} 를 입력한다.`) !== id) return;
        const d = await api(`projects/${encodeURIComponent(p.id)}/callsigns/${encodeURIComponent(id)}/delete`, { method: "POST", token, body: { confirm: id } });
        if (d.status !== 200) { message.replaceChildren(alertBox("bad", errorText(d))); return; }
        route();
      };
      return el("div", {}, el("h3", {}, `${p.display_name} · ${p.id}`), message,
        el("table", {}, el("thead", {}, el("tr", {}, ...["콜사인", "종류", "등록", "마지막 활동", "셋업", ""].map((h) => el("th", {}, h)))),
          el("tbody", {}, r.data.callsigns.map((c) => el("tr", { class: c.archived ? "archived" : "" },
            el("td", {}, c.id, c.archived ? el("span", { class: "muted" }, " (보관)") : null), el("td", {}, `${c.kind} · ${c.role}`),
            el("td", {}, when(c.created_at)), el("td", {}, c.last_seen_at ? when(c.last_seen_at) : "—"),
            el("td", {}, c.setup_complete ? "완료" : "미완료"),
            el("td", {}, c.role === "owner" ? null : el("button", { class: "danger", "data-delete-callsign": c.id, onclick: () => remove(c.id) }, "삭제")))))));
    }));
    return el("section", { class: "card" }, el("h2", {}, "콜사인 정리"),
      el("p", { class: "muted" }, "등록·셋업 외 활동이 없는 콜사인만 지운다. 활동 기록이 있는 콜사인은 지울 수 없다 — 허브가 거절한다."), blocks);
  }

  // --- 화면: 프로젝트 · KPI · task 목록 --------------------------------------------------

  const STATUSES = ["", "all", "blocked", "in_progress", "planned", "done"];

  async function viewProject(pid, status, query) {
    query = query || new URLSearchParams();
    const token = storedToken(pid);
    const pr = await api(`projects/${encodeURIComponent(pid)}`, { token });
    if (pr.status !== 200) {
      setCrumbs([{ text: "프로젝트", href: "#/" }, { text: pid }]);
      // 공유받은 링크로 처음 온 사람이 길을 잃지 않게 — 로그인이 먼저, 토큰은 접어 둔다.
      render(pr.status === 401 && !signedInAccount ? accountPanel(null, () => route()) : null,
        el("section", { class: "card" }, alertBox(pr.status === 401 ? "info" : "bad",
          pr.status === 401 ? "이 프로젝트를 보려면 로그인한다." : errorText(pr)),
        token ? forgetButton(pid, route) : null,
        el("details", { class: "account" }, el("summary", {}, "콜사인 토큰으로 열기"), tokenForm(() => route()))));
      return;
    }
    const { project, principal, summary } = pr.data;
    setWho(principal);
    setCrumbs([{ text: "프로젝트", href: "#/" }, { text: project.display_name }]);
    const pageLimit = Number(query.get("limit") || 25);
    const pageOffset = Number(query.get("offset") || 0);
    const listQuery = new URLSearchParams({ limit: String(pageLimit), offset: String(pageOffset) });
    const FACETS = ["roadmap", "milestone", "wbs", "category_level_1", "category_level_2", "category_level_3"];
    for (const key of FACETS) {
      if (query.get(key)) listQuery.set(key, query.get(key));
    }
    // 기본 탭 '지금' = 막힘 + 진행 중 (진척을 보러 온 사람이 먼저 봐야 할 task). '전체' 는 s/all.
    const nowMode = !status;
    if (status && status !== "all") listQuery.set("status", status);
    const nowQuery = (st) => { const q = new URLSearchParams(listQuery); q.set("status", st); q.set("limit", "100"); q.set("offset", "0"); return q; };
    const root = `projects/${encodeURIComponent(pid)}`;
    // 사람이 결정할 일은 화면마다 따로 있다 — 각 화면의 API 를 그대로 읽어 센다 (못 읽은 것은 '확인 못 함', 0 으로 세지 않는다).
    const [tr0, trBlocked, cr, conf, dcr, guide, rm] = await Promise.all([
      api(`${root}/tasks?${nowMode ? nowQuery("in_progress") : listQuery}`, { token }),
      nowMode ? api(`${root}/tasks?${nowQuery("blocked")}`, { token }) : Promise.resolve(null), api(`${root}/callsigns`, { token }),
      api(`${root}/confirmations`, { token }), api(`${root}/dcr`, { token }),
      api(`${root}/guide`, { token }), api(`${root}/roadmap`, { token })]);
    const tr = nowMode && tr0.status === 200 && trBlocked && trBlocked.status === 200
      ? { status: 200, data: { ...tr0.data, tasks: [...trBlocked.data.tasks, ...tr0.data.tasks], total: (trBlocked.data.total || 0) + (tr0.data.total || 0) } }
      : nowMode && trBlocked && trBlocked.status !== 200 ? trBlocked : tr0;
    const base = `#/p/${encodeURIComponent(pid)}`;
    const sum = summary || {};
    const sc = sum.session_counts || {};
    const activeSessions = (sc.idle || 0) + (sc.working || 0) + (sc.waiting || 0);
    const unknownSessions = sum.unknown_sessions || 0;
    const orch = sum.orchestrator;
    const tc = project.task_counts || {};
    const totalTasks = Object.values(tc).reduce((a, b) => a + b, 0);

    const counted = (r, pick) => r.status === 200 ? pick(r.data) : null;
    const decisions = [
      ["확인 요청", counted(conf, (d) => (d.requests || []).length), `${base}/confirmations`, "에이전트가 승인을 기다린다"],
      ["중계 승인", sum.pending_approvals || 0, `${base}/orch`, "세션 띄우기 · 멈춤"],
      ["열린 결정 task", sum.open_decision_tasks || 0, (sum.open_decision_task_ids || []).length
        ? `${base}/t/${encodeURIComponent(sum.open_decision_task_ids[0])}` : base,
        (sum.open_decision_task_ids || []).length > 1 ? `첫 task 부터 — 모두 ${sum.open_decision_task_ids.length}건` : "그 task 에서 답한다"],
      ["결정 변경(DCR)", counted(dcr, (d) => (d.dcrs || []).filter((x) => x.status === "open").length), `${base}/dcr`, "승인 · 거절"],
      ["지침 제안", counted(guide, (d) => (d.proposals || []).filter((x) => x.status === "open").length), `${base}/guide`, "새 판으로 올릴지"],
      ["막힌 task", tc.blocked || 0, `${base}/s/blocked`, "풀 사람이 필요하다"],
    ];
    const need = decisions.filter(([, n]) => n);
    const unread = decisions.filter(([, n]) => n === null);
    const decideRow = el("section", { "aria-labelledby": "decide-h" },
      el("div", { class: "decide-head" }, el("h2", { id: "decide-h" }, "사람이 결정할 일"),
        el("span", { class: "muted" }, need.length ? `${need.reduce((a, [, n]) => a + n, 0)}건` : "지금 없음",
          unread.length ? ` · 확인 못 함: ${unread.map(([l]) => l).join(", ")} (이 계정에 권한이 없다)` : "",
          // 확인 요청 · 중계 승인을 알린 메시지도 섞여 있다 — 결정 수에 더하지 않는다 (같은 일을 두 번 세지 않는다).
          (sum.unacknowledged || 0) > 0 ? [" · ", el("a", { href: `${base}/orch` }, `읽지 않은 에이전트 메시지 ${sum.unacknowledged}건`)] : null)),
      need.length
        ? el("div", { class: "decide" }, need.map(([label, n, href, what]) =>
          el("a", { class: "need", href, "data-decide": label }, el("span", { class: "n" }, String(n)), el("span", {}, label), el("span", { class: "what" }, what))))
        : el("div", { class: "decide-clear" }, "모든 결정이 처리됐다. 새 요청이 오면 여기에 먼저 보인다."));

    const attention = [];
    if (orch && orch.halted) {
      attention.push(alertBox("bad", "오케스트레이션이 정지돼 있다 — 에이전트에게 새 일을 나누지 않는다. ", el("a", { href: `${base}/orch` }, "오케스트레이션에서 풀기")));
    }
    if (unknownSessions > 0) {
      attention.push(alertBox("bad", `신호가 끊긴 세션 ${unknownSessions}개 — `, el("a", { href: `${base}/orch` }, "오케스트레이션에서 확인")));
    }
    if ((sum.ideas_unread || 0) > 0) {
      attention.push(alertBox("info", `아이디어에 새 회신 ${sum.ideas_unread}건 — `, el("a", { href: `${base}/ideas`, "data-ideas-unread": String(sum.ideas_unread) }, "아이디어 보기")));
    }

    const st = rm.status === 200 ? rm.data.roadmap_state : null;
    let progress;
    if (!st || !(st.milestones || []).length) {
      progress = el("section", { class: "card", "aria-labelledby": "rail-h" }, el("h2", { id: "rail-h" }, "진척"),
        el("p", { class: "muted" }, rm.status === 200 ? "로드맵이 아직 없다 — 마일스톤을 등록하면 여기에 진척 띠가 생긴다. " : `로드맵을 읽지 못했다 (${rm.status}). `,
          el("a", { href: `${base}/roadmap` }, "로드맵 화면")));
    } else {
      const ms = st.milestones;
      const isDone = (m) => m.derived_status === "done" && m.declared_status === "done";
      const cur = ms.find((m) => m.id === st.current_milestone_id) || ms.find((m) => !isDone(m));
      const tenth = (p) => Math.max(0, Math.min(100, Math.round((p || 0) * 10) * 10));
      const rail = el("div", { class: "rail", role: "list", "aria-label": "마일스톤 진척" }, ms.map((m) => {
        const pct = isDone(m) ? 100 : tenth(m.progress);
        const label = `${m.id} ${m.title} — ${isDone(m) ? "끝남" : `세부 작업 ${m.done_leaves || 0}/${m.total_leaves || 0} 끝남`}`;
        return el("a", { role: "listitem", href: `${base}/roadmap`, title: label, "aria-label": label,
          class: `w-${Math.max(1, Math.min(8, m.total_leaves || 1))}${isDone(m) ? "" : " open"}${cur && m.id === cur.id ? " current" : ""}` },
          el("span", { class: "bar" }, el("span", { class: `fill pct-${pct}` })), el("span", { class: "lbl" }, m.title || m.id), el("span", { class: "lbl-id" }, m.id));
      }));
      const doneCount = ms.filter(isDone).length;
      progress = el("section", { class: "card", "aria-labelledby": "rail-h" },
        el("div", { class: "decide-head" }, el("h2", { id: "rail-h" }, "진척"), el("a", { href: `${base}/roadmap` }, "로드맵 전체")),
        el("div", { class: "rail-wrap" }, rail,
          el("div", { class: "rail-legend" },
            cur ? el("span", {}, "지금 ", el("b", {}, `${cur.id} ${cur.title}`), ` · 세부 작업 ${cur.done_leaves || 0}/${cur.total_leaves || 0} 끝남`) : el("span", {}, "모든 마일스톤이 끝났다"),
            el("span", {}, `마일스톤 ${ms.length}개 중 ${doneCount}개 끝남`),
            el("span", {}, `task 진행 중 ${tc.in_progress || 0} · 막힘 ${tc.blocked || 0} · 끝남 ${tc.done || 0} / 전체 ${totalTasks}`))));
    }

    const statusFilters = el("nav", { class: "filters", "aria-label": "상태로 거르기" }, STATUSES.map((s) => {
      const next = new URLSearchParams(query);
      next.set("limit", String(pageLimit)); next.set("offset", "0");
      next.delete("status");
      const suffix = next.toString() ? `?${next}` : "";
      const on = s === (status || "");
      return el("a", { href: `${s ? `${base}/s/${encodeURIComponent(s)}` : base}${suffix}`, class: on ? "on" : "",
        "aria-current": on ? "true" : null }, s === "" ? `지금 (막힘 · 진행 중 ${(tc.blocked || 0) + (tc.in_progress || 0)})` : s === "all" ? `전체 ${totalTasks}` : `${statusLabel(s)} ${tc[s] || 0}`);
    }));
    const category = (t) => t.fields?.category ? [t.fields.category.level_1, t.fields.category.level_2, t.fields.category.level_3].filter(Boolean).join(" / ") : "";
    const rows = tr.status === 200 ? tr.data.tasks.map((t) => el("tr", {},
      el("td", { class: "t-title" }, el("a", { href: `${base}/t/${encodeURIComponent(t.id)}` }, t.title || t.id),
        el("span", { class: "t-id" }, t.id), category(t) ? el("span", { class: "t-cat" }, category(t)) : null),
      el("td", { class: "t-status" }, chip(t.status)),
      el("td", { class: "t-more", "data-label": "맡은 이" }, t.assignee || "—"),
      el("td", { class: "t-more" }, t.progress_note ? el("div", { class: "clamp-2", title: t.progress_note }, t.progress_note) : ""),
      el("td", { class: "t-more nowrap" }, when(t.updated_at)))) : [];
    const facets = tr.data?.facets || {};
    const filterOptions = (key, label, values) => el("label", {}, label,
      el("select", { name: key, "aria-label": label },
        el("option", { value: "" }, "전체"),
        (values || []).map((value) => el("option", { value, selected: query.get(key) === value },
          key === "roadmap" ? (value === "linked" ? "연결됨" : "미지정") : value))));
    const listFilters = el("details", { class: "facets", "data-keep": "facets", open: FACETS.some((k) => query.get(k)) },
      el("summary", {}, "분류로 거르기"),
      el("form", { class: "task-filters", onsubmit: (ev) => {
        ev.preventDefault();
        const next = new URLSearchParams();
        for (const key of FACETS) {
          const value = ev.currentTarget.elements.namedItem(key)?.value || "";
          if (value) next.set(key, value);
        }
        next.set("limit", String(pageLimit));
        next.set("view", query.get("view") || "table");
        location.hash = `${base}${status ? `/s/${encodeURIComponent(status)}` : ""}?${next}`;
      } },
        filterOptions("roadmap", "로드맵 연결", ["linked", "unlinked"]),
        filterOptions("milestone", "마일스톤", facets.milestones),
        filterOptions("wbs", "WBS", facets.wbs),
        filterOptions("category_level_1", "분류 1", facets.category_level_1),
        filterOptions("category_level_2", "분류 2", facets.category_level_2),
        filterOptions("category_level_3", "분류 3", facets.category_level_3),
        el("button", { type: "submit" }, "분류 적용")));
    const viewMode = query.get("view") === "card" ? "card" : "table";
    const pageQuery = (offset, view = viewMode) => {
      const next = new URLSearchParams(query);
      next.set("limit", String(pageLimit)); next.set("offset", String(offset)); next.set("view", view);
      if (status) next.set("status", status); else next.delete("status");
      return `${base}${status ? `/s/${encodeURIComponent(status)}` : ""}?${next}`;
    };
    const total = tr.data?.total || 0;
    const page = Math.floor(pageOffset / pageLimit) + 1;
    const pageCount = Math.max(1, Math.ceil(total / pageLimit));
    const cards = tr.status === 200 ? tr.data.tasks.map((t) => el("a", { class: "card task-card", href: `${base}/t/${encodeURIComponent(t.id)}` },
      el("div", { class: "row" }, chip(t.status), chip(t.priority, "planned"), el("span", { class: "mono muted" }, t.id)),
      el("h3", {}, t.title),
      el("p", { class: "muted" }, t.wbs || "로드맵 미지정", " · ", category(t) || "분류 없음"),
      t.progress_note ? el("p", {}, t.progress_note) : null,
      el("div", { class: "muted" }, `맡은 이 ${t.assignee || "—"} · `, when(t.updated_at)))) : [];
    const listView = viewMode === "card"
      ? cards.length ? el("div", { class: "grid task-cards" }, cards) : el("p", { class: "muted" }, nowMode ? "지금 막히거나 진행 중인 task 가 없다 — '전체' 탭에서 모두 본다." : "조건에 맞는 task 가 없다.")
      : rows.length ? el("div", { class: "table-wrap" }, el("table", { class: "tasks stack" },
          el("colgroup", {}, ["c-title", "c-status", "c-who", "c-doing", "c-when"].map((c) => el("col", { class: c }))),
          el("thead", {}, el("tr", {}, ["task", "상태", "맡은 이", "지금 하는 일", "고친 때"].map((h) => el("th", { scope: "col" }, h)))),
          el("tbody", {}, rows))) : el("p", { class: "muted" }, nowMode ? "지금 막히거나 진행 중인 task 가 없다 — '전체' 탭에서 모두 본다." : "조건에 맞는 task 가 없다.");
    const pagination = nowMode ? null : tr.status === 200 ? el("div", { class: "row pagination" },
      el("span", { class: "muted" }, `${total}개 · ${page}/${pageCount}페이지`),
      el("a", { class: page <= 1 ? "disabled" : "", "aria-disabled": page <= 1 ? "true" : null, href: pageQuery(Math.max(0, pageOffset - pageLimit)) }, "이전"),
      el("a", { class: page >= pageCount ? "disabled" : "", "aria-disabled": page >= pageCount ? "true" : null, href: pageQuery(Math.min((pageCount - 1) * pageLimit, pageOffset + pageLimit)) }, "다음")) : null;
    const who = principal.auth_mode === "account"
      ? el("details", { class: "account", "data-keep": "account" }, el("summary", {}, "내 계정 · 프로젝트 참여 · 콜사인 연결"), accountPanel(principal.account, route))
      : principal.kind === "callsign"
      ? el("div", { class: "row" }, forgetButton(pid, route))
      : el("details", { class: "account", "data-keep": "account", open: true }, el("summary", {}, "이 브라우저의 콜사인"), registerForm(pid, route), tokenForm(() => route()));
    render(
      el("section", { class: "card project-head" },
        el("h1", {}, project.display_name),
        el("div", { class: "meta" }, el("span", { class: "mono" }, project.id), el("span", {}, `소유자 ${project.owner_callsign}`)),
        projectNav(pid, "tasks"), who),
      ...attention,
      decideRow,
      progress,
      el("section", { class: "card", "aria-labelledby": "tasks-h" },
        el("div", { class: "decide-head" }, el("h2", { id: "tasks-h" }, "task"),
          el("div", { class: "row view-switch" }, el("span", { class: "muted" }, "보기"),
            el("a", { class: viewMode === "table" ? "on" : "", href: pageQuery(pageOffset, "table") }, "표"),
            el("a", { class: viewMode === "card" ? "on" : "", href: pageQuery(pageOffset, "card") }, "카드"))),
        el("div", { class: "task-tools" }, statusFilters), listFilters,
        tr.status !== 200 ? alertBox("bad", errorText(tr))
          : listView, pagination),
      callsignSection(pid, principal, cr));
  }

  const MSG_FIELD = { request_type: "종류", request_id: "요청", dir_alias: "별칭", harness: "하네스", permission_mode: "권한", prompt: "지시",
    host_id: "PC", host: "PC", request: "요청", session: "세션", reason: "사유", task_id: "task", decide_with: "결정 방법", kind: "종류", target: "대상", to_session: "받는 세션" };
  // 알려진 값은 한국어로, 원래 값은 괄호 안에 남긴다 (이력의 '만듦 (create)' 과 같은 방식).
  const MSG_VALUE = { spawn: "세션 띄우기", stop: "멈춤", default: "기본", acceptEdits: "편집 자동 허용", plan: "계획만 세움", bypassPermissions: "권한 확인 건너뜀",
    hub_approval_decide: "허브에서 승인", agent_confirmation: "에이전트 확인 요청", session_request: "세션 요청" };
  const msgValue = (v) => typeof v === "string" && MSG_VALUE[v] ? `${MSG_VALUE[v]} (${v})` : v;
  function messageBody(body) {
    if (typeof body === "string") return el("div", { class: "exact" }, reveal(body));
    if (Array.isArray(body)) return el("pre", { class: "wrap exact" }, reveal(JSON.stringify(body)));
    const b = body || {};
    const text = ["title", "text", "question", "summary", "message", "note"].map((k) => b[k]).filter((v) => typeof v === "string" && v);
    const state = typeof b.state === "string" ? b.state : typeof b.decision === "string" ? b.decision : "";
    // 글 칸이 없는 본문은 이름표 붙은 칸으로 — 값은 그대로(보이지 않는 문자 드러냄), 모르는 이름은 원문 이름으로.
    const rest = Object.entries(b).filter(([k]) => !["state", "decision"].includes(k));
    const field = ([k, v]) => el("div", { class: "kv" }, el("span", { class: "muted", title: k }, MSG_FIELD[k] || k),
      el("span", { class: "exact" }, reveal(typeof v === "string" ? msgValue(v) : JSON.stringify(v))));
    return el("div", {}, state ? chip(state, "planned") : null, text.map((v) => el("div", { class: "exact" }, reveal(v))),
      !text.length && rest.length ? el("div", { class: "kvs" }, rest.map(field)) : null);
  }

  // --- 화면: 오케스트레이션 (M-053 WBS-53.1) -----------------------------------------------

  async function viewOrchestration(pid) {
    const { token, base, pr } = await projectHead(pid, "오케스트레이션");
    if (pr.status !== 200) { render(el("section", { class: "card" }, alertBox("bad", errorText(pr)))); return; }
    const r = await api(`projects/${encodeURIComponent(pid)}/orchestration`, { token });
    if (r.status !== 200) { render(el("section", { class: "card" }, alertBox("bad", errorText(r)))); return; }
    const d = r.data;
    const canManage = d.principal && d.principal.can_manage;
    const orch = d.orchestrator;
    const sc = d.session_counts || {};
    const activeSessions = d.sessions.filter((s) => s.status !== "ended");
    const pendingReqs = d.requests.filter((x) => x.state === "pending_approval");
    const otherReqs = d.requests.filter((x) => x.state !== "pending_approval");

    const leaseCard = (() => {
      const msg = el("div");
      const postLease = async (payload, okText) => {
        const res = await api(`projects/${encodeURIComponent(pid)}/orchestration/lease`, {
          method: "POST", token: storedToken(pid), body: payload });
        if (res.status !== 200) { msg.replaceChildren(alertBox("bad", errorText(res))); return; }
        dirty = false;
        pendingFlash = { kind: "ok", text: okText };
        route();
      };
      const controls = [];
      let haltRow = null;
      if (canManage) {
        if (orch) {
          haltRow = el("div", { class: "row halt-row" }, el("span", { class: "muted" }, orch.halted
            ? "정지 중 — 에이전트에게 새 일을 나누지 않는다."
            : "모든 에이전트의 새 배정을 멈춘다. 돌고 있는 세션은 끝나지 않는다."), el("button", {
            type: "button", class: orch.halted ? "" : "danger",
            onclick: async () => {
              const res = await api(`projects/${encodeURIComponent(pid)}/orchestration/halt`, {
                method: "POST", token: storedToken(pid), body: { on: !orch.halted } });
              if (res.status !== 200) { msg.replaceChildren(alertBox("bad", errorText(res))); return; }
              dirty = false;
              pendingFlash = { kind: "ok", text: res.data.halted ? "오케스트레이션을 정지했다." : "오케스트레이션 정지를 풀었다." };
              route();
            },
          }, orch.halted ? "정지 풀기" : "전체 정지"));
        }
        const sel = el("select", { "aria-label": "오케스트레이터 대상 세션" },
          activeSessions.length
            ? activeSessions.map((s) => el("option", { value: s.id }, `${s.id} · ${s.callsign} (${s.harness}/${s.status})`))
            : el("option", { value: "" }, "활성 세션 없음"));
        controls.push(sel,
          el("button", {
            type: "button", class: "ghost", disabled: !activeSessions.length || undefined,
            onclick: () => postLease({ action: orch ? "transfer" : "declare", session: sel.value },
              orch ? `${sel.value} 로 오케스트레이터를 넘겼다.` : `${sel.value} 를 오케스트레이터로 지정했다.`),
          }, orch ? "이 세션에 넘기기" : "오케스트레이터 지정"));
        if (orch) {
          controls.push(el("button", { type: "button", class: "ghost", onclick: () => postLease({ action: "release" }, "오케스트레이터를 내려놓았다 — 지금은 맡은 세션이 없다.") }, "오케스트레이터 내려놓기"));
        }
      }
      return el("section", { class: "card" },
        el("div", { class: "row" }, el("h1", {}, "오케스트레이션"),
          orch && orch.halted ? chip("정지", "halted") : null),
        projectNav(pid, "orch"),
        orch ? el("div", { class: "row" }, "오케스트레이터 ", el("strong", {}, orch.callsign),
          el("span", { class: "mono muted" }, orch.session), "만료 ", when(orch.expires_at))
          : el("p", { class: "muted" }, "지정된 오케스트레이터가 없다."),
        controls.length ? el("div", { class: "row" }, el("span", { class: "muted" }, "오케스트레이터 세션"), controls) : el("p", { class: "muted" }, "정지 · 오케스트레이터 지정 · 승인은 이 프로젝트의 소유자가 한다 — 허브 계정으로 로그인하거나 승인된 소유자 콜사인 토큰을 쓴다."),
        haltRow, msg);
    })();

    const reqCard = (req) => {
      const target = req.target || {};
      const detailText = req.kind === "stop"
        ? `대상 세션 ${target.session || "—"}${target.reason ? ` · 사유: ${target.reason}` : ""}`
        : `별칭 ${target.dir_alias || "—"} · 하네스 ${target.harness || "—"} · 권한 ${target.permission_mode || "default"}${target.prompt ? ` · 지시: ${target.prompt}` : ""}`;
      const note = el("input", { type: "text", placeholder: "결정 메모 (선택)", "aria-label": `${req.id} 메모` });
      const msg = el("div");
      const decideBtn = (decision, label, cls) => el("button", {
        type: "button", class: cls || "",
        onclick: async () => {
          const res = await api(`projects/${encodeURIComponent(pid)}/orchestration/approvals/${encodeURIComponent(req.id)}`, {
            method: "POST", token: storedToken(pid), body: { decision, note: note.value } });
          if (res.status !== 200) { msg.replaceChildren(alertBox("bad", errorText(res))); return; }
          dirty = false;
          pendingFlash = { kind: "ok", text: `${req.id} 를 ${decision === "approve" ? "승인" : "거절"}했다.` };
          route();
        },
      }, label);
      return el("div", { class: "decision" },
        el("div", { class: "row" }, el("strong", { class: "mono" }, req.id), chip(req.kind, "planned"), chip(req.state, req.state),
          `PC ${req.host_id}`, `· 요청 ${req.requested_by} · `, when(req.created_at)),
        el("div", { class: "exact" }, reveal(detailText)),
        req.decided_by ? el("div", { class: "muted" }, `결정 ${req.decided_by} · `, when(req.decided_at)) : null,
        req.result && Object.keys(req.result).length ? el("div", { class: "mono muted" }, JSON.stringify(req.result)) : null,
        req.state === "pending_approval" && canManage ? el("div", { class: "row" }, note, decideBtn("approve", "승인"), decideBtn("reject", "거절", "danger")) : null,
        msg);
    };

    const approvalsSection = el("section", { class: "card" },
      el("h2", {}, `세션 승인 대기 (${pendingReqs.length})`),
      pendingReqs.length ? pendingReqs.map(reqCard) : el("p", { class: "muted" }, "승인 대기 중인 요청이 없다."),
      otherReqs.length ? el("details", { "data-keep": "orch-old" }, el("summary", {}, `이전 요청 기록 (${otherReqs.length})`),
        el("div", {}, otherReqs.map(reqCard))) : null);

    const sessCountsRow = el("div", { class: "row" },
      ...["working", "waiting", "idle", "ended"].map((st) => chip(`${statusLabel(st)} ${sc[st] || 0}`, st)),
      chip(`${statusLabel("unknown")} ${d.unknown_sessions || 0}`, (d.unknown_sessions || 0) > 0 ? "unknown" : "planned"));

    const sessRows = d.sessions.map((s) => el("tr", {},
      el("td", {}, el("a", { href: `${base}/c/${encodeURIComponent(s.callsign)}` }, s.callsign), s.orchestrator ? " " : null, s.orchestrator ? chip("오케스트레이터", "approved") : null,
        el("span", { class: "t-id" }, s.id)),
      el("td", {}, s.harness || "—", s.kind === "worker" ? " (자동 작업 세션)" : ""),
      el("td", {}, chip(s.status, s.status)),
      el("td", { class: "muted" }, (s.delivery || []).map(viaLabel).join(", ") || "—"),
      el("td", {}, String(s.open_assignments || 0)),
      el("td", { class: "mono muted" }, s.host_id || "로컬/직접"),
      el("td", { class: "muted nowrap" }, when(s.last_signal_at))));

    const sessionsSection = el("section", { class: "card" },
      el("h2", {}, `세션 (${d.sessions.length})`), sessCountsRow,
      d.sessions.length ? el("div", { class: "table-wrap" }, el("table", {},
        el("thead", {}, el("tr", {}, ["콜사인 · 세션", "하네스", "상태", "전달", "열린 배정", "호스트", "마지막 신호"].map((h) => el("th", { scope: "col" }, h)))),
        el("tbody", {}, sessRows))) : el("p", { class: "muted" }, "등록된 세션이 없다."));

    const unackSection = d.unacknowledged.length ? el("section", { class: "card" },
      el("h2", {}, `미확인 메시지 (${d.unacknowledged.length})`),
      el("p", { class: "muted" }, "10분 넘게 읽지 않은 메시지다. 받은 세션이 읽음으로 표시하면(세션이 끝났으면 같은 콜사인의 새 세션이) 사라진다. 소유자는 '읽음으로 정리' 로 지울 수 있고, 배정 · 승인 상태는 바뀌지 않는다."),
      d.unacknowledged.map((m) => el("div", { class: "decision" },
        el("div", { class: "row" }, chip(m.kind, "planned"), el("span", {}, `받는 이 ${m.to_kind === "session" ? "세션" : "콜사인"} ${m.to_id}`),
          m.ref_task ? el("a", { href: `${base}/t/${encodeURIComponent(m.ref_task)}`, title: m.ref_task }, "관련 task") : null,
          el("span", { class: "muted" }, `${viaLabel(m.delivered_via) || "—"} · `, when(m.created_at)), el("span", { class: "mono muted" }, m.id)),
        messageBody(m.body),
        m.kind === "approval" && m.body && m.body.request_type === "agent_confirmation"
          ? el("a", { href: `${base}/confirmations` }, "확인 요청에서 결정")
          : canManage ? el("button", { type: "button", class: "ghost", onclick: async () => {
            const res = await api(`projects/${encodeURIComponent(pid)}/orchestration/messages/${encodeURIComponent(m.id)}/close`, {
              method: "POST", token: storedToken(pid), body: {} });
            pendingFlash = res.status === 200 ? { kind: "ok", text: `${m.id} 를 정리했다.` } : { kind: "bad", text: errorText(res) };
            dirty = false;
            route();
          } }, "읽음으로 정리") : null))) : null;

    const assignRows = d.assignments.map((a) => el("tr", {},
      el("td", { class: "t-title" }, el("a", { href: `${base}/t/${encodeURIComponent(a.task_id)}` }, a.task_title || a.task_id), el("span", { class: "t-id" }, a.task_id),
        a.progress_note ? el("div", { class: "muted clamp-2" }, a.progress_note) : null),
      el("td", {}, chip(a.state, a.state), a.message_state === "unacknowledged" ? el("span", {}, " ", chip("unack", "unack")) : null),
      el("td", {}, a.callsign, el("div", { class: "mono muted" }, a.session_id)),
      el("td", { class: "muted" }, viaLabel(a.delivered_via) || "—", a.delivery_count ? ` (${a.delivery_count}회)` : ""),
      el("td", { class: "muted" }, a.return_reason || (a.report && a.report.summary) || when(a.offered_at) || "—")));

    const assignSection = el("section", { class: "card" },
      el("h2", {}, `배정 현황 (${d.assignments.length})`),
      d.assignments.length ? el("div", { class: "table-wrap" }, el("table", {},
        el("thead", {}, el("tr", {}, ["task · 진척", "상태", "대상", "전달", "사유 · 보고"].map((h) => el("th", { scope: "col" }, h)))),
        el("tbody", {}, assignRows))) : el("p", { class: "muted" }, "배정 기록이 없다."));

    const hostsSection = (() => {
      const inviteBox = el("div");
      const hostMsg = el("div");
      const inviteBtn = canManage ? el("button", {
        type: "button",
        onclick: async () => {
          const res = await api(`projects/${encodeURIComponent(pid)}/orchestration/relays/invite`, {
            method: "POST", token: storedToken(pid), body: {} });
          if (res.status !== 200) { inviteBox.replaceChildren(alertBox("bad", errorText(res))); return; }
          dirty = true;
          inviteBox.replaceChildren(
            alertBox("ok", `1회용 초대 코드(이 화면에서만 보임 · 만료 ${res.data.expires_at ? when(res.data.expires_at).textContent : "—"}): ${res.data.invite}`),
            el("pre", {}, res.data.command));
        },
      }, "중계 초대 코드 발급") : null;
      const hostRows = d.hosts.map((h) => el("tr", {},
        el("td", { class: "mono" }, h.host_id),
        el("td", {}, h.name),
        el("td", {}, (h.harnesses || []).join(", ") || "—"),
        el("td", { class: "mono muted" }, h.allow_digest ? h.allow_digest.slice(0, 18) : "—"),
        el("td", { class: "muted nowrap" }, when(h.last_seen_at)),
        el("td", {}, canManage ? el("button", {
          type: "button", class: "ghost danger",
          onclick: async () => {
            if (!confirm(`${h.name} (${h.host_id}) 중계 토큰을 거둔다. 계속할까?`)) return;
            const res = await api(`projects/${encodeURIComponent(pid)}/orchestration/relays/${encodeURIComponent(h.host_id)}/revoke`, {
              method: "POST", token: storedToken(pid), body: {} });
            if (res.status !== 200) { hostMsg.replaceChildren(alertBox("bad", errorText(res))); return; }
            dirty = false;
            pendingFlash = { kind: "ok", text: `중계 ${h.host_id} 토큰을 거뒀다.` };
            route();
          },
        }, "거두기") : "—")));
      return el("section", { class: "card" },
        el("div", { class: "row" }, el("h2", {}, `PC 중계 호스트 (${d.hosts.length})`), inviteBtn),
        inviteBox, hostMsg,
        d.hosts.length ? el("div", { class: "table-wrap" }, el("table", {},
          el("thead", {}, el("tr", {}, ["호스트", "이름", "하네스", "허용 목록 지문", "마지막 연결", ""].map((h) => el("th", {}, h)))),
          el("tbody", {}, hostRows))) : el("p", { class: "muted" }, "등록된 PC 중계가 없다."));
    })();

    render(leaseCard, unackSection, approvalsSection, sessionsSection, assignSection, hostsSection);
  }

  async function viewConfirmations(pid) {
    const token = storedToken(pid);
    const [project, result] = await Promise.all([
      api(`projects/${encodeURIComponent(pid)}`, { token }),
      api(`projects/${encodeURIComponent(pid)}/confirmations`, { token }),
    ]);
    const base = `#/p/${encodeURIComponent(pid)}`;
    setCrumbs([{ text: "프로젝트", href: "#/" },
      { text: project.status === 200 ? project.data.project.display_name : pid, href: base },
      { text: "에이전트 확인 요청" }]);
    setWho(project.status === 200 ? project.data.principal : null);
    if (result.status !== 200) {
      render(el("section", { class: "card" }, el("h1", {}, "에이전트 확인 요청"), projectNav(pid, "confirmations"),
        alertBox("bad", errorText(result))));
      return;
    }
    const requests = result.data.requests || [];
    const actingAccount = project.status === 200 && project.data.principal?.auth_mode === "account";
    const cards = requests.map((req) => {
      const note = el("textarea", { rows: "2", placeholder: "결정 메모 (선택)" });
      const decide = (decision) => async () => {
        const r = await api(`projects/${encodeURIComponent(pid)}/confirmations/${encodeURIComponent(req.id)}`, {
          method: "POST", token, body: { decision, note: note.value.trim() },
        });
        if (r.status !== 200) { pendingFlash = { kind: "bad", text: errorText(r) }; return route(); }
        pendingFlash = { kind: "ok", text: `요청 ${req.id} ${decision === "approve" ? "승인" : "거절"} — 허브 받은편지함으로 결과를 보냈다.` };
        dirty = false;
        route();
      };
      return el("section", { class: "card" },
        el("div", { class: "row" }, el("h2", { class: "exact" }, reveal(req.title)), staleDoc(req) ? chip("낡은 요청", "unack") : chip("승인 대기", "blocked")),
        el("div", { class: "muted" }, `${req.requested_by} · `, when(req.created_at)),
        req.action ? el("section", { class: "card", "data-action": req.action.type },
          el("h3", {}, "승인하면 실행되는 일"),
          ...(req.action.type === "project_doc_put" ? docPutCard(req) : req.action.type === "knowledge_source_register" ? [
          el("p", {}, "지식 원본 등록 · ", el("span", { class: "mono" }, reveal(req.action.summary.source_id)), " · 저장소 ", el("span", { class: "mono" }, reveal(req.action.summary.repo_key))),
          el("p", { class: "muted" }, `승인하면 요청한 콜사인 ${req.requested_by} 만 24시간 안에 한 번 실행할 수 있다. 아래 경로의 문서 ${req.action.summary.paths}개만 스냅샷으로 받는다.`),
          el("ul", { "data-source-paths": String(req.action.summary.paths) }, req.action.summary.allowlist.map((x) => el("li", { class: "mono exact" }, reveal(x))))] : [
          el("p", {}, `${{ migrate_import: "1.x 기록 들여오기", migrate_marker: "'허브로 옮김' 표식" }[req.action.type] || req.action.type} · ${req.action.summary.migration_id}`),
          el("p", { class: "muted" }, `승인하면 요청한 콜사인 ${req.requested_by} 만 24시간 안에 한 번 실행할 수 있다. 브랜치 `, reveal(req.action.summary.branch), ` · ${String(req.action.summary.head).slice(0, 8)} · 미커밋 파일 ${req.action.summary.uncommitted}개`),
          req.action.summary.files ? el("ul", {}, Object.entries(req.action.summary.files).map(([k, n]) => el("li", {}, `${k}: ${n}개 파일`))) : null,
          req.action.summary.marker ? el("p", {}, `표식 동작: ${req.action.summary.marker}`) : null]),
          actingAccount ? null : alertBox("warn", "이 승인은 허브 계정 로그인이 필요하다. 홈에서 계정으로 로그인한 뒤 승인한다.")) : null,
        el("p", { class: "muted" }, "요청한 에이전트의 설명"), el("p", { class: "exact" }, reveal(req.question)), req.details ? el("pre", { class: "wrap exact" }, reveal(req.details)) : null,
        el("div", { class: "row" }, note,
          el("button", { type: "button", disabled: (Boolean(req.action) && !actingAccount) || staleDoc(req), onclick: decide("approve") }, "승인"),
          el("button", { class: "danger", type: "button", onclick: decide("reject") }, "거절")));
    });
    render(el("section", { class: "card" }, el("h1", {}, "에이전트 확인 요청"),
      el("p", { class: "muted" }, "승인하거나 거절하면 결과가 요청한 에이전트의 받은편지함으로 간다. 에이전트는 결과를 확인한 뒤에 일을 이어 간다."),
      projectNav(pid, "confirmations")),
      ...(cards.length ? cards : [el("section", { class: "card muted" }, "기다리는 확인 요청이 없다.")]));
  }

  // --- 화면: 아이디어 박스 — 사람이 적고 에이전트가 회신한다 -------------------------------------

  const IDEA_STATUS = { new: ["검토 대기", "planned"], reviewing: ["검토 중", "in_progress"], replied: ["회신 도착", "open"],
    adopted: ["task 로 만듦", "done"], kept: ["보관", "ended"], closed: ["닫음", "ended"] };
  const IDEA_VERDICT = { do: "추천", conditional: "조건부", hold: "보류", exists: "이미 있음", question: "질문" };
  const ideaChip = (status) => chip(...(IDEA_STATUS[status] || [status, "unknown"]));

  async function viewIdeas(pid, id) {
    const token = storedToken(pid);
    const root = `projects/${encodeURIComponent(pid)}`;
    const base = `#/p/${encodeURIComponent(pid)}`;
    const [project, result] = await Promise.all([api(root, { token }), api(`${root}/ideas${id ? `/${encodeURIComponent(id)}` : ""}`, { token })]);
    const principal = project.status === 200 ? project.data.principal : null;
    setCrumbs([{ text: "프로젝트", href: "#/" }, { text: project.status === 200 ? project.data.project.display_name : pid, href: base },
      id ? { text: "아이디어", href: `${base}/ideas` } : { text: "아이디어" }, ...(id ? [{ text: id }] : [])]);
    setWho(principal);
    const head = (title, ...rest) => el("section", { class: "card" }, el("h1", {}, title), projectNav(pid, "ideas"), ...rest);
    if (result.status !== 200) { render(head("아이디어", alertBox("bad", errorText(result)))); return; }
    const canWrite = principal?.auth_mode === "account" && principal.callsign_kind === "human" && principal.human_approved;
    const readOnly = canWrite ? null : alertBox("warn", "적고 처리하려면 허브 계정으로 로그인한 승인된 사람이어야 한다.");
    render(...(id ? ideaDetail(`${principal?.callsign}/${pid}/${id}`, root, base, result.data.idea, canWrite, readOnly, head, result.data.similar) : ideaList(root, base, result.data, canWrite, readOnly, head)));
  }

  function ideaList(root, base, data, canWrite, readOnly, head) {
    const text = el("textarea", { rows: "4", placeholder: "떠오른 생각을 대충 적는다", "aria-label": "아이디어" });
    const msg = el("div");
    const send = el("button", { type: "submit" }, "적어 두기");
    let key = "", sent = "";
    const form = el("form", { onsubmit: async (ev) => {
      ev.preventDefault();
      if (!text.value.trim()) { msg.replaceChildren(alertBox("bad", "내용을 적는다.")); return; }
      if (!key || sent !== text.value) { key = `web-${Date.now()}-${Math.random().toString(36).slice(2)}`; sent = text.value; }  // 같은 글의 재시도는 한 번만 적힌다
      send.disabled = true;
      text.readOnly = true;  // 성공하면 다시 그릴 때까지 잠근다 — 그 사이 쓴 글이 두 번 적히지 않게
      const unlock = () => { send.disabled = false; text.readOnly = false; };
      let similar = [];
      try {
        const r = await api(`${root}/ideas`, { method: "POST", body: { body: text.value, request_id: key } });
        if (r.status !== 200) { unlock(); msg.replaceChildren(alertBox("bad", errorText(r))); return; }  // 적던 글은 그대로 둔다
        similar = r.data.similar || [];
      } catch (e) { unlock(); msg.replaceChildren(alertBox("bad", "허브에 연결할 수 없다 — 적은 글은 그대로 있다. 다시 눌러 본다.")); return; }
      pendingFlash = { kind: "ok", text: "적어 두었다 — 다음에 에이전트 세션이 열릴 때 검토해 회신한다."
        + (similar.length ? ` 비슷한 아이디어: ${similar.map((x) => x.id).join(" · ")}` : "") };
      dirty = false;
      route();
    } }, text, el("div", { class: "row" }, send), msg);
    const groups = [["회신 도착", ["replied"]], ["검토 대기", ["new", "reviewing"]], ["처리됨", ["adopted", "kept", "closed"]]];
    const item = (i) => el("li", {}, el("a", { href: `${base}/ideas/${encodeURIComponent(i.id)}`, class: "exact" }, reveal(i.excerpt)), el("div", { class: "muted" },
      i.unread ? chip(`새 회신 ${i.unread}`, "unack") : null, ideaChip(i.status), i.verdict ? ` ${IDEA_VERDICT[i.verdict]} · ` : " ", i.id, ` · ${i.author}${i.added_via === "agent" ? " (에이전트가 적음)" : ""} · `, when(i.updated_at),
      i.claimed_by ? ` · ${i.claimed_by}` : "", i.task_id ? el("a", { href: `${base}/t/${encodeURIComponent(i.task_id)}` }, ` ${i.task_id}`) : null));
    return [head("아이디어", el("p", { class: "muted" }, "대충 적어 두면 에이전트가 검토해 회신한다. 회신은 다음 에이전트 세션이 열릴 때 나온다."),
      data.unread_total ? alertBox("info", `아직 안 본 회신 ${data.unread_total}건`) : null, readOnly, canWrite ? form : null),
      ...groups.map(([label, states]) => {
        const rows = data.ideas.filter((i) => states.includes(i.status));
        const list = rows.length ? el("ul", { class: "hits" }, rows.map(item)) : el("p", { class: "muted" }, "없음");
        return el("section", { class: "card" }, label === "처리됨" ? el("details", { "data-keep": "ideas-done" }, el("summary", {}, `${label} ${rows.length}`), list)
          : [el("h2", {}, `${label} ${rows.length}`), list]);
      }),
      data.total > data.ideas.length ? el("p", { class: "muted" }, `전체 ${data.total}건 가운데 ${data.ideas.length}건만 보인다.`) : null];
  }

  // 허브 WBS 게이트의 거절을 이 화면의 칸 이름으로 말한다 (게이트 문구는 CLI 옵션으로 설명한다)
  function ideaGateText(r) {
    const warn = r.data?.error_code === "gate_denied" ? (r.data.detail?.warnings || []) : [];
    if (warn.includes("exempt_reason_required")) return "로드맵 밖 일이면 'WBS 면제 사유' 칸을 채운다.";
    if (warn.includes("wbs_required")) return "이 프로젝트는 로드맵이 있어 WBS 가 필요하다 — 'WBS' 칸에 M-NNN/WBS-N.N 을 적거나, 로드맵 밖이면 'WBS 면제 사유' 를 적는다.";
    if (warn.includes("wbs_ref_format")) return "'WBS' 칸은 M-NNN/WBS-N.N 꼴이다 (예: M-007/WBS-7.2).";
    return "";
  }

  const ideaDrafts = new Map();  // 아이디어마다 적던 글 — 다른 처리를 눌러 다시 그려도 남는다
  function ideaDetail(key, root, base, idea, canWrite, readOnly, head, similar) {
    similar = similar || [];
    const msg = el("div");
    const typed = ideaDrafts.get(key) || {};
    ideaDrafts.set(key, typed);
    const reply = [...idea.entries].reverse().find((e) => e.kind === "reply" && e.draft);
    const draft = reply?.draft || {};
    const linkTask = [...idea.entries].reverse().find((e) => e.kind === "reply" && e.task_id)?.task_id || "";
    const act = (body, done, sent) => async (ev) => {
      const fields = [...app.querySelectorAll("textarea, input")], button = ev.currentTarget;
      const lock = (on) => { button.disabled = on; fields.forEach((f) => { f.readOnly = on; }); };
      lock(true);
      let r;
      try { r = await api(`${root}/ideas/${encodeURIComponent(idea.id)}`, { method: "POST", body: { expected_version: idea.version, ...body() } }); }
      catch (e) { lock(false); msg.replaceChildren(alertBox("bad", "허브에 연결할 수 없다 — 적던 글은 그대로 있다.")); return; }
      if (r.status !== 200) { lock(false); msg.replaceChildren(alertBox("bad", ideaGateText(r) || errorText(r) + (r.data?.error_code === "version_conflict" ? " · 새로고침해 바뀐 내용을 본 뒤 다시 한다 (적던 글은 남는다)." : ""))); return; }
      (sent || []).forEach((name) => delete typed[name]);
      pendingFlash = { kind: "ok", text: done(r.data) };
      dirty = false;
      route();
    };
    const part = (label, value) => value ? [el("div", { class: "muted" }, label), el("div", { class: "exact" }, reveal(value))] : [];
    const entry = (e) => el("section", { class: "card", "data-idea-entry": e.kind },
      el("div", { class: "row" }, el("strong", {}, { idea: "아이디어", ask: "더 묻기", reply: "회신" }[e.kind]), e.kind === "reply" ? chip(IDEA_VERDICT[e.verdict] || e.verdict, "answered") : null,
        el("span", { class: "muted" }, `${e.author} · `, when(e.at))),
      ...(e.kind !== "reply" ? [el("div", { class: "exact" }, reveal(e.body))] : [
        ...part("이렇게 이해했다", e.understood), ...part("이유", e.reason), ...part("예상 범위", e.scope), ...part("다음 한 걸음", e.next),
        e.refs.length ? [el("div", { class: "muted" }, "근거"), el("ul", {}, e.refs.map((x) => el("li", { class: "exact" }, reveal(x))))] : null,
        e.task_id ? [el("div", { class: "muted" }, "이미 맡은 task"), el("a", { href: `${base}/t/${encodeURIComponent(e.task_id)}`, "data-reply-task": e.task_id }, e.task_id)] : null,
        (e.related_ideas || []).length ? [el("div", { class: "muted" }, "비슷한 아이디어"), el("div", { class: "row" }, e.related_ideas.map((x) => el("a", { href: `${base}/ideas/${encodeURIComponent(x)}` }, x)))] : null,
        ...part("확인하지 않은 것", e.unverified)]));
    const out = [head(idea.id, el("div", { class: "row" }, ideaChip(idea.status), idea.claimed_by ? el("span", { class: "muted" }, `${idea.claimed_by} 검토 중`) : null,
      idea.added_via === "agent" ? chip("에이전트가 적음", "unack") : null, idea.task_id ? el("a", { href: `${base}/t/${encodeURIComponent(idea.task_id)}` }, idea.task_id) : null),
      idea.added_via === "agent" && !idea.asked_by_human ? el("p", { class: "muted" }, "에이전트가 대신 적은 아이디어다. 사람이 '더 묻기' 를 보내야 다음 세션의 검토 대기에 오른다.") : null, readOnly),
      ...idea.entries.map(entry),
      similar.length ? el("section", { class: "card", "data-similar": String(similar.length) }, el("h2", {}, "비슷한 아이디어"),
        el("ul", { class: "hits" }, similar.map((x) => el("li", {}, el("a", { href: `${base}/ideas/${encodeURIComponent(x.id)}`, class: "exact" }, reveal(x.excerpt)),
          el("div", { class: "muted" }, ideaChip(x.status), ` ${x.id} · 겹침 ${x.score}%`))))) : null];
    // 사람이 열어 본 회신은 읽음으로 — 판(version)을 바꾸지 않아 적던 처리와 부딪치지 않는다
    if (canWrite && idea.unread) api(`${root}/ideas/${encodeURIComponent(idea.id)}`, { method: "POST", body: { action: "seen" } }).catch(() => {});
    if (!canWrite || idea.status === "adopted") return out;
    const ask = el("textarea", { rows: "3", placeholder: "덧붙이거나 더 물을 것", "aria-label": "더 묻기" });
    const title = el("input", { type: "text", "aria-label": "task 제목" }), wbs = el("input", { type: "text", "aria-label": "WBS", placeholder: "M-007/WBS-7.2" });
    const exempt = el("input", { type: "text", "aria-label": "WBS 면제 사유" }), done = el("textarea", { rows: "4", "aria-label": "완료 기준" });
    const form = { title: draft.title || "", wbs: draft.wbs || "", exempt: draft.wbs_exempt_reason || "", done: (draft.done_criteria || []).join("\n"), ...typed.form };
    const boxes = { title, wbs, exempt, done }, hiddenNote = el("div");
    const check = () => {  // 초안이 아니라 등록될 칸의 값을 센다
      const all = Object.values(boxes).map((f) => f.value).join("\n"), n = hiddenCount(all);
      hiddenNote.replaceChildren(...(n ? [alertBox("warn", `등록할 내용에 보이지 않는 문자 ${n}개 — 아래처럼 들어 있다.`), el("pre", { class: "wrap exact" }, reveal(all))] : []));
    };
    Object.entries(boxes).forEach(([name, f]) => {
      f.value = form[name];
      f.addEventListener("input", () => { typed.form = Object.fromEntries(Object.entries(boxes).map(([k, b]) => [k, b.value])); typed.base ??= reply?.seq ?? 0; check(); });
    });
    check();
    ask.value = typed.ask || "";
    ask.addEventListener("input", () => { typed.ask = ask.value; });
    const newer = typed.form && typed.base !== (reply?.seq ?? 0);
    const lines = () => done.value.split("\n").map((s) => s.trim()).filter(Boolean);
    const adopt = act(() => ({ action: "adopt", title: title.value.trim(), wbs: wbs.value.trim() || (exempt.value.trim() ? "exempt" : ""),
      ...(exempt.value.trim() ? { wbs_exempt_reason: exempt.value.trim() } : {}), done_criteria: lines() }), (d) => `${d.task.id} 로 만들었다.`);
    return [...out, el("section", { class: "card" }, el("h2", {}, "처리"), msg, ask,
      el("div", { class: "row" }, el("button", { type: "button", onclick: act(() => ({ action: "ask", body: ask.value }), () => "보냈다 — 다시 검토 대기다.", ["ask"]) }, "더 묻기"),
        el("button", { type: "button", class: "ghost", onclick: act(() => ({ action: "keep" }), () => "보관했다.") }, "보관"),
        el("button", { type: "button", class: "ghost", onclick: act(() => ({ action: "close" }), () => "닫았다.") }, "닫기"))),
    linkTask ? el("section", { class: "card", "data-link-task": linkTask }, el("h2", {}, "이미 있는 task 로 처리"),
      el("p", { class: "muted" }, `회신에 따르면 이 일은 이미 ${linkTask} 에서 하고 있다. 이 task 에 연결하면 새 task 를 만들지 않는다.`),
      el("button", { type: "button", onclick: act(() => ({ action: "link", task_id: linkTask }), () => `${linkTask} 에 연결했다.`) }, "이 task 로 처리")) : null,
    el("section", { class: "card" }, el("h2", {}, "task 로 만들기"),
      el("p", { class: "muted" }, draft.title ? `회신이 채운 초안이다. 고쳐서 등록한다. 원문은 task 설명에 그대로 들어간다.` : "원문은 task 설명에 그대로 들어간다."),
      newer ? alertBox("warn", "그 사이 새 회신의 초안이 왔다. 아래는 전에 고치던 내용이다.", el("button", { type: "button", class: "ghost", onclick: () => { delete typed.form; delete typed.base; dirty = false; route(); } }, "새 초안으로 바꾸기")) : null,
      hiddenNote,
      el("div", { class: "task-filters" }, el("label", {}, "제목", title), el("label", {}, "WBS", wbs), el("label", {}, "WBS 면제 사유 (WBS 가 없을 때)", exempt)),
      el("label", { class: "idea-done" }, "완료 기준 (한 줄에 하나)", done),
      el("div", { class: "row" }, el("button", { type: "button", onclick: (ev) => {
        // 로드맵 밖(exempt)은 사유가 있어야 허브 WBS 게이트를 지난다 — 보내기 전에 그 칸을 가리킨다
        if (wbs.value.trim() === "exempt" && !exempt.value.trim()) {
          msg.replaceChildren(alertBox("bad", "로드맵 밖 일이면 'WBS 면제 사유' 칸을 채운다 — 아직 보내지 않았다."));
          exempt.focus();
          return undefined;
        }
        return adopt(ev);
      } }, "task 로 등록")))];
  }

  // 보이지 않거나 글자 순서를 뒤집는 문자를 드러낸다 — 사람이 본 글과 쓰일 글이 같아야 한다.
  const HIDDEN_CHARS = /(?![\n\t ])[\p{C}\p{Z}\p{Default_Ignorable_Code_Point}\u2800\u2D7F\uFFFC\u{1107F}\u{13441}\u{13442}\u{16FE4}\u{1D159}]/gu;
  function reveal(text) {
    const s = String(text ?? ""), out = [];
    let at = 0;
    for (const m of s.matchAll(HIDDEN_CHARS)) {
      out.push(s.slice(at, m.index), el("mark", { class: "hidden-char" }, `U+${m[0].codePointAt(0).toString(16).toUpperCase().padStart(4, "0")}`));
      at = m.index + m[0].length;
    }
    return [...out, s.slice(at)];
  }
  const hiddenCount = (text) => (String(text ?? "").match(HIDDEN_CHARS) || []).length;

  // 승인할 문서 본문 — 허브가 보관한 요청 본문과 요청 때 판의 줄 단위 차이. 자르지 않는다.
  function lineDiff(before, after) {
    const a = before ? before.split("\n") : [], b = after ? after.split("\n") : [];
    let s = 0, t = 0;
    while (s < a.length && s < b.length && a[s] === b[s]) s += 1;
    while (t < a.length - s && t < b.length - s && a[a.length - 1 - t] === b[b.length - 1 - t]) t += 1;
    const x = a.slice(s, a.length - t), y = b.slice(s, b.length - t), out = a.slice(0, s).map((l) => [" ", l]);
    if (x.length * y.length > 4e6) {
      x.forEach((l) => out.push(["-", l])); y.forEach((l) => out.push(["+", l]));
    } else {
      const w = y.length + 1, m = new Uint32Array((x.length + 1) * w);
      for (let i = x.length - 1; i >= 0; i -= 1) for (let j = y.length - 1; j >= 0; j -= 1) {
        m[i * w + j] = x[i] === y[j] ? m[(i + 1) * w + j + 1] + 1 : Math.max(m[(i + 1) * w + j], m[i * w + j + 1]);
      }
      let i = 0, j = 0;
      while (i < x.length || j < y.length) {
        if (i < x.length && j < y.length && x[i] === y[j]) { out.push([" ", x[i]]); i += 1; j += 1; }
        else if (i < x.length && (j >= y.length || m[(i + 1) * w + j] >= m[i * w + j + 1])) { out.push(["-", x[i]]); i += 1; }
        else { out.push(["+", y[j]]); j += 1; }
      }
    }
    return out.concat(a.slice(a.length - t).map((l) => [" ", l]));
  }

  const staleDoc = (req) => req.action?.type === "project_doc_put" && req.action.current_version !== req.action.summary.version;

  function docPutCard(req) {
    const d = req.action.summary;
    const rows = lineDiff(d.base, d.proposed);
    const near = new Set();
    rows.forEach(([mark], i) => { if (mark !== " ") for (let k = i - 2; k <= i + 2; k += 1) near.add(k); });
    const body = [];
    rows.forEach(([mark, text], i) => {
      if (near.has(i)) body.push(el("span", { class: mark === "+" ? "diff-add" : mark === "-" ? "diff-del" : "" }, `${mark} `, reveal(text), "\n"));
      else if (near.has(i - 1) || i === 0) body.push(el("span", { class: "muted" }, "⋯ 바뀌지 않은 줄\n"));
    });
    const changed = rows.filter(([mark]) => mark !== " ");
    return [
      el("p", {}, `프로젝트 문서 쓰기 · ${d.name} · ${d.version}판 → ${d.version + 1}판`),
      el("p", { class: "muted" }, `승인하면 요청한 콜사인 ${req.requested_by} 만 24시간 안에 아래 본문 그대로 한 번 쓸 수 있다. 그 사이 문서가 바뀌면 쓸 수 없다. sha256 ${d.sha256.slice(0, 12)}`),
      el("p", {}, `추가 ${changed.filter(([mark]) => mark === "+").length}줄 · 삭제 ${changed.filter(([mark]) => mark === "-").length}줄`),
      staleDoc(req) ? alertBox("warn", `낡은 요청 — 문서가 지금 ${req.action.current_version}판이라 승인해도 쓸 수 없다. 거절하고 다시 요청받는다.`) : null,
      hiddenCount(d.proposed) ? alertBox("warn", `새 본문에 보이지 않는 문자 ${hiddenCount(d.proposed)}개 — U+… 로 표시했다.`) : null,
      changed.length ? el("pre", { class: "wrap exact", "data-doc-diff": d.name }, body) : el("p", { class: "muted" }, "줄 차이가 없다."),
      el("details", { "data-keep": `doc-${req.id}` }, el("summary", {}, "새 본문 전체"), el("pre", { class: "wrap exact" }, reveal(d.proposed))),
    ];
  }

  // --- 화면: 로드맵 (M-053 WBS-53.1) -----------------------------------------------------

  function renderWbsNode(base, node, titles) {
    titles = titles || new Map();
    return el("li", { class: "wbs-node" },
      el("div", { class: "row" }, chip(node.derived_status), el("span", {}, node.title), el("span", { class: "mono muted" }, node.id),
        node.total_leaves ? el("span", { class: "muted" }, `${node.done_leaves}/${node.total_leaves} 끝남`) : null),
      node.linked_task_ids && node.linked_task_ids.length
        ? el("ul", { class: "wbs-tasks" }, node.linked_task_ids.map((tid) => {
          const t = titles.get(tid);
          return el("li", {}, t ? chip(t.status) : null, " ", el("a", { href: `${base}/t/${encodeURIComponent(tid)}`, title: tid }, t ? t.title : tid));
        }))
        : null,
      node.children && node.children.length
        ? el("ul", { class: "wbs-list" }, node.children.map((ch) => renderWbsNode(base, ch, titles))) : null);
  }

  // 로드맵에 묶인 task 의 제목 · 상태 — 목록 API 를 100건씩 읽는다 (ID 만 보이면 무엇인지 다시 찾아야 한다).
  async function linkedTaskTitles(pid, token) {
    const out = new Map();
    for (let offset = 0; offset < 1000; offset += 100) {
      const r = await api(`projects/${encodeURIComponent(pid)}/tasks?roadmap=linked&limit=100&offset=${offset}`, { token });
      if (r.status !== 200) break;
      for (const t of r.data.tasks) out.set(t.id, t);
      if (offset + 100 >= (r.data.total || 0)) break;
    }
    return out;
  }

  async function viewRoadmap(pid) {
    const { token, base, pr } = await projectHead(pid, "로드맵");
    if (pr.status !== 200) { render(el("section", { class: "card" }, alertBox("bad", errorText(pr)))); return; }
    const r = await api(`projects/${encodeURIComponent(pid)}/roadmap`, { token });
    if (r.status !== 200) { render(el("section", { class: "card" }, alertBox("bad", errorText(r)))); return; }
    const st = r.data.roadmap_state;
    if (!st) {
      render(el("section", { class: "card" }, el("h1", {}, "로드맵"), projectNav(pid, "roadmap"),
        el("p", { class: "muted" }, r.data.reason || "로드맵이 없다.")));
      return;
    }
    const titles = await linkedTaskTitles(pid, token);
    // 상태는 하나로 보인다 — 로드맵에 적힌 상태(선언)와 task 로 계산한 상태(파생)가 다르면 그때만 알린다.
    const card = (m) => el("section", { class: "card" },
      el("div", { class: "row" }, chip(m.derived_status), m.id === st.current_milestone_id ? chip("현재 마일스톤", "in_progress") : null,
        el("span", { class: "mono muted" }, m.id), el("span", { class: "muted", title: m.sdlc_phase }, PHASE_LABEL[m.sdlc_phase] || m.sdlc_phase)),
      el("h2", {}, m.title),
      m.declared_status !== m.derived_status ? alertBox("warn", `로드맵 문서에는 '${statusLabel(m.declared_status)}' 로 적혀 있지만 task 로 계산하면 '${statusLabel(m.derived_status)}' 이다 — 로드맵 문서나 task 상태를 맞춘다.`) : null,
      el("div", { class: "meter" },
        el("div", { class: "muted" }, `세부 작업 ${m.done_leaves} / ${m.total_leaves} 끝남 (${Math.round((m.progress || 0) * 100)}%)`),
        el("progress", { value: m.progress || 0, max: 1, "aria-label": `${m.id} 진척` })),
      m.wbs && m.wbs.length ? el("ul", { class: "wbs-list" }, m.wbs.map((w) => renderWbsNode(base, w, titles))) : null);
    const isDone = (m) => m.derived_status === "done" && m.declared_status === "done";
    const open = st.milestones.filter((m) => !isDone(m));
    // 현재 → 진행 중(선언이나 파생) → 나머지 (같은 무리 안은 로드맵 순서 그대로)
    const rank = (m) => m.id === st.current_milestone_id ? 0 : [m.declared_status, m.derived_status].includes("in_progress") ? 1 : 2;
    open.sort((a, b) => rank(a) - rank(b));
    const done = st.milestones.filter(isDone).reverse();
    render(
      el("section", { class: "card" }, el("h1", {}, "로드맵"), projectNav(pid, "roadmap"),
        el("div", { class: "row muted" }, `마일스톤 ${st.milestones.length}개 (열림 ${open.length} · 완료 ${done.length})`,
          st.current_milestone_id ? ` · 현재 ${st.current_milestone_id}` : "",
          st.exempt_tasks ? ` · 로드맵 밖(면제) task ${st.exempt_tasks.length}건` : "")),
      st.issues && st.issues.length ? el("section", { class: "card" }, el("h2", {}, `로드맵 경고 (${st.issues.length})`),
        el("ul", {}, st.issues.map((i) => el("li", { title: i.code }, i.detail || i.code)))) : null,
      open.map(card),
      done.length ? el("details", { class: "card", "data-keep": "rm-done" }, el("summary", {}, `완료한 마일스톤 (${done.length})`), done.map(card)) : null);
  }

  // --- 콜사인 표 · 콜사인 화면 (WBS-37.2) ------------------------------------------------

  const canApprove = (principal) => principal.kind === "callsign" && principal.role === "owner"
    && principal.callsign_kind === "human" && principal.human_approved;

  function guideChip(c, current) {
    if (c.guide_state === "current") return chip("지침 최신", "done");
    if (c.guide_state === "stale") return el("span", { class: "chip blocked", title: `받은 판 ${c.guide_version_seen} · 허브 ${current}` }, `옛 지침 ${c.guide_version_seen}`);
    return chip("지침 받은 적 없음", "planned");
  }

  const ROLE_LABEL = { owner: "소유자", editor: "편집자", viewer: "읽기 전용" };
  function kindText(c) {
    if (c.kind !== "human") return "에이전트";
    return c.human_approved ? "사람" : "사람 · 승인 전";
  }

  function approveButton(pid, c) {
    return el("button", { type: "button", class: "ghost", onclick: async () => {
      const r = await api(`projects/${encodeURIComponent(pid)}/callsigns/${encodeURIComponent(c.id)}/approve`, {
        method: "POST", token: storedToken(pid), body: {} });
      dirty = false;
      pendingFlash = r.status === 200 ? { kind: "ok", text: `${c.id} 를 승인했다 — 이제 결정에 답할 수 있다.` }
        : { kind: "bad", text: errorText(r) };
      route();
    } }, "승인");
  }

  function nowDoing(c, base) {
    if (!c.open_tasks.length) return el("span", { class: "muted" }, "맡은 열린 task 없음");
    return el("ul", { class: "doing" }, c.open_tasks.map((t) => el("li", {},
      chip(t.status), " ", el("a", { href: `${base}/t/${encodeURIComponent(t.id)}`, title: t.id }, t.title || t.id),
      t.progress_note ? el("div", { class: "muted clamp-2" }, t.progress_note) : null)));
  }

  function callsignSection(pid, principal, cr) {
    if (cr.status !== 200) return el("section", { class: "card" }, el("h2", {}, "콜사인"), alertBox("bad", errorText(cr)));
    const base = `#/p/${encodeURIComponent(pid)}`;
    const { callsigns, guide_current: current } = cr.data;
    const rows = callsigns.map((c) => el("tr", { class: c.archived ? "archived" : "" },
      el("td", { class: "t-title nowrap" }, el("a", { href: `${base}/c/${encodeURIComponent(c.id)}` }, c.id), c.archived ? " " : null, c.archived ? chip("보관", "planned") : null,
        el("span", { class: "t-cat" }, kindText(c), ` · ${ROLE_LABEL[c.role] || c.role}`),
        c.kind === "human" && !c.human_approved && !c.archived && canApprove(principal) ? approveButton(pid, c) : null),
      el("td", { class: "t-status" }, guideChip(c, current)),
      el("td", { class: "t-more" }, nowDoing(c, base)),
      el("td", { class: "t-more nowrap", "data-label": "마지막 활동" }, when(c.last_seen_at) || "활동 없음"),
      el("td", { class: "t-more mono", "data-label": "클라이언트" }, c.client_version_seen || "—")));
    return el("section", { class: "card" }, el("h2", {}, "콜사인 — 지금 누가 무엇을"),
      el("p", { class: "muted" }, "허브 지침 판 ", el("span", { class: "mono" }, current)),
      el("div", { class: "table-wrap" }, el("table", { class: "stack callsigns" }, el("thead", {}, el("tr", {}, ["콜사인", "지침", "지금 하는 일", "마지막 활동", "클라이언트"].map((h) => el("th", { scope: "col" }, h)))),
        el("tbody", {}, rows))));
  }

  const HANDOFF = [["baseline", "현재 기준선"], ["focus", "주요 작업"], ["in_progress", "진행 중"], ["blocked", "막힘"],
    ["recent_done", "최근 완료"], ["next", "다음에 시작할 곳"], ["risks", "남은 위험"]];

  async function viewCallsign(pid, cs) {
    const token = storedToken(pid);
    const [pr, r] = await Promise.all([
      api(`projects/${encodeURIComponent(pid)}`, { token }),
      api(`projects/${encodeURIComponent(pid)}/callsigns/${encodeURIComponent(cs)}`, { token })]);
    const base = `#/p/${encodeURIComponent(pid)}`;
    setCrumbs([{ text: "프로젝트", href: "#/" }, { text: pr.status === 200 ? pr.data.project.display_name : pid, href: base }, { text: cs }]);
    if (r.status !== 200 || pr.status !== 200) { render(el("section", { class: "card" }, alertBox("bad", errorText(r.status !== 200 ? r : pr)))); return; }
    const principal = pr.data.principal;
    setWho(principal);
    const { callsign: c, handoff: h, guide_current: current } = r.data;
    const sections = h.handoff;
    const body = sections ? HANDOFF.map(([key, title]) => {
      const v = sections[key];
      const empty = Array.isArray(v) ? !v.length : !v;
      return el("div", { class: "handoff-part" }, el("h2", {}, title),
        empty ? el("p", { class: "muted" }, "—")
          : Array.isArray(v) ? el("ul", {}, v.map((x) => el("li", {}, x))) : el("p", {}, v));
    }) : [el("p", { class: "muted" }, "아직 올린 인계 기록이 없다.")];
    render(
      el("section", { class: "card" },
        el("h1", {}, c.id),
        el("div", { class: "row" }, kindText(c), `· ${c.role}`, c.label ? `· ${c.label}` : null, c.host ? `· ${c.host}` : null,
          c.archived ? chip("보관 (읽기 전용)", "planned") : null,
          c.kind === "human" && !c.human_approved && !c.archived && canApprove(principal) ? approveButton(pid, c) : null),
        el("div", { class: "row muted" }, "마지막 활동 ", when(c.last_seen_at) || "없음", "·", guideChip(c, current), "·",
          `클라이언트 ${c.client_version_seen || "—"}`, "·", c.setup_complete ? "셋업 완료" : "셋업 미완료"),
        el("h2", {}, "지금 하는 일"), nowDoing(c, base)),
      el("section", { class: "card" }, el("h2", {}, "handoff"),
        sections ? el("p", { class: "muted" }, `v${h.version} · `, when(h.updated_at)) : null, body));
  }

  // --- 지침 · 위키 (WBS-37.3) -------------------------------------------------------

  async function projectHead(pid, label) {
    const token = storedToken(pid);
    const pr = await api(`projects/${encodeURIComponent(pid)}`, { token });
    const base = `#/p/${encodeURIComponent(pid)}`;
    setCrumbs([{ text: "프로젝트", href: "#/" }, { text: pr.status === 200 ? pr.data.project.display_name : pid, href: base }, { text: label }]);
    setWho(pr.status === 200 ? pr.data.principal : null);
    return { token, base, pr };
  }

  function proposalCard(pid, prop, canDecide) {
    const decide = (approve) => async () => {
      const r = await api(`projects/${encodeURIComponent(pid)}/guide/proposals/${encodeURIComponent(prop.id)}`, {
        method: "POST", token: storedToken(pid), body: { approve } });
      dirty = false;
      pendingFlash = r.status === 200
        ? { kind: "ok", text: approve ? `${prop.id} 를 승인했다 — 지침 판 ${r.data.guide_version}` : `${prop.id} 를 거절했다.` }
        : { kind: "bad", text: errorText(r) };
      route();
    };
    const open = prop.status === "open";
    return el("div", { class: "decision" },
      el("div", { class: "row" }, el("strong", { class: "mono" }, prop.id),
        chip(open ? "열림" : prop.status === "approved" ? "승인" : "거절", open ? "open" : prop.status === "approved" ? "answered" : "planned"),
        `${prop.proposed_by} · `, when(prop.proposed_at), ` · 기준 ${prop.base_version}판`,
        prop.applied_version ? ` → v${prop.applied_version}` : null,
        prop.decided_by && prop.decided_by !== prop.proposed_by ? ` · 결정 ${prop.decided_by}` : null),
      prop.note ? el("div", { class: "exact" }, reveal(prop.note)) : null,
      prop.stale ? alertBox("warn", "기준 판이 지금 판이 아니다 — 승인할 수 없다. 새 판 위에서 다시 제안해야 한다.") : null,
      el("details", { open: open || undefined }, el("summary", {}, "바뀐 줄"), el("pre", { class: "diff exact" }, prop.diff ? reveal(prop.diff) : "(차이 없음)")),
      open && canDecide ? el("div", { class: "row" },
        el("button", { type: "button", onclick: decide(true), disabled: prop.stale || undefined }, "승인"),
        el("button", { type: "button", class: "danger", onclick: decide(false) }, "거절")) : null);
  }

  async function viewGuide(pid) {
    const { token } = await projectHead(pid, "지침");
    const r = await api(`projects/${encodeURIComponent(pid)}/guide`, { token });
    if (r.status !== 200) { render(el("section", { class: "card" }, alertBox("bad", errorText(r)))); return; }
    const g = r.data;
    const open = g.proposals.filter((x) => x.status === "open");
    let editor = el("p", { class: "muted" }, "고치려면 허브 계정으로 로그인하거나 이 프로젝트의 콜사인 토큰을 넣는다.");
    if (g.can_propose) {
      const text = el("textarea", { class: "guide-edit", "aria-label": "지침 본문" });
      text.value = g.body;
      const note = el("input", { type: "text", placeholder: "무엇을 왜 바꾸나 (한 줄)", "aria-label": "변경 메모" });
      const msg = el("div");
      editor = el("form", { onsubmit: async (ev) => {
        ev.preventDefault();
        const res = await api(`projects/${encodeURIComponent(pid)}/guide`, {
          method: "POST", token: storedToken(pid), body: { base_version: g.version, body: text.value, note: note.value } });
        if (res.status !== 200) { msg.replaceChildren(alertBox("bad", errorText(res))); return; }
        dirty = false;
        pendingFlash = res.data.applied_version
          ? { kind: "ok", text: `지침 판을 ${res.data.guide_version} 로 올렸다.` }
          : { kind: "ok", text: `제안 ${res.data.proposal_id} 를 올렸다 — 승인된 사람 콜사인이 승인하면 판이 오른다.` };
        route();
      } }, text, el("div", { class: "row" }, note,
        el("button", { type: "submit" }, g.can_decide ? "판 올리기" : "제안 올리기")), msg);
    }
    render(
      el("section", { class: "card" }, el("h1", {}, "프로젝트 지침"), projectNav(pid, "guide"),
        el("div", { class: "row muted" }, "지금 판 ", el("span", { class: "mono" }, g.guide_version), `· 열린 제안 ${open.length}`),
        el("p", { class: "muted" }, g.can_decide ? "승인된 사람 콜사인이라 고치면 바로 새 판이 되고, 열린 제안을 승인하거나 거절할 수 있다."
          : "에이전트나 아직 승인받지 않은 사람 콜사인이 고치면 제안으로 남는다."),
        el("details", {}, el("summary", {}, "지금 본문"), el("pre", {}, g.body || "(비어 있다 — 표준 규칙만 적용된다)")),
        el("h2", {}, "고치기"), editor),
      el("section", { class: "card" }, el("h2", {}, "제안"),
        g.proposals.length ? g.proposals.map((x) => proposalCard(pid, x, g.can_decide)) : el("p", { class: "muted" }, "제안이 없다.")),
      el("section", { class: "card" }, el("h2", {}, "판 이력"),
        g.history.length ? el("div", { class: "table-wrap" }, el("table", {}, el("thead", {}, el("tr", {}, ["판", "누가", "언제", "크기"].map((h) => el("th", {}, h)))),
          el("tbody", {}, g.history.map((h) => el("tr", {}, el("td", { class: "mono" }, `v${h.version}`), el("td", {}, h.updated_by),
            el("td", { class: "muted nowrap" }, when(h.updated_at)), el("td", { class: "muted" }, `${h.size}자`))))))
          : el("p", { class: "muted" }, "아직 올린 판이 없다 — 표준 규칙만 적용된다.")));
  }

  const pageHref = (base, path) => `${base}/wp/${encodeURIComponent(path)}`;

  async function viewWiki(pid, query) {
    const { token, base } = await projectHead(pid, "지식");
    const q = (query || "").trim();
    const r = await api(`projects/${encodeURIComponent(pid)}/wiki${q ? `?q=${encodeURIComponent(q)}` : ""}`, { token });
    const input = el("input", { type: "search", placeholder: "검색어 (모두 들어간 문서를 찾는다)", "aria-label": "위키 검색" });
    input.value = q;
    const search = el("form", { class: "row", role: "search", onsubmit: (ev) => {
      ev.preventDefault();
      dirty = false;
      location.hash = input.value.trim() ? `${base}/w/q/${encodeURIComponent(input.value.trim())}` : `${base}/w`;
    } }, input, el("button", { type: "submit" }, "검색"), q ? el("a", { href: `${base}/w` }, "전체 목록") : null);
    let body;
    if (r.status !== 200) body = alertBox("bad", errorText(r));
    else if (q) body = r.data.hits.length ? el("ul", { class: "hits" }, r.data.hits.map((h) => el("li", {},
      el("a", { href: h.kind === "wiki" ? pageHref(base, h.path) : `${base}/k/${encodeURIComponent(h.ref)}` }, h.title), " ", el("span", { class: "mono muted" }, h.path || h.canonical_ref || ""),
      h.snippet || h.excerpt ? el("div", { class: "muted" }, h.snippet || h.excerpt) : null))) : el("p", { class: "muted" }, "맞는 문서가 없다.");
    else body = el("div", {},
      el("div", { class: "row" }, (r.data.generated || []).map((g) => el("a", { href: pageHref(base, g) }, g)), el("span", { class: "muted" }, "(자동 생성)")),
      r.data.pages.length ? el("div", { class: "table-wrap" }, el("table", {}, el("thead", {}, el("tr", {}, ["페이지", "경로", "판", "고친 이", "고친 때"].map((h) => el("th", {}, h)))),
        el("tbody", {}, r.data.pages.map((pg) => el("tr", {}, el("td", {}, el("a", { href: pageHref(base, pg.path) }, pg.title)),
          el("td", { class: "mono muted" }, pg.path), el("td", { class: "mono" }, `v${pg.version}`), el("td", {}, pg.updated_by || "—"),
          el("td", { class: "muted nowrap" }, when(pg.updated_at)))))))
        : el("p", { class: "muted" }, "위키 페이지가 없다."));
    render(el("section", { class: "card" }, el("h1", {}, "프로젝트 지식"), projectNav(pid, "wiki"), search,
      r.status === 200 && q ? el("p", { class: "muted" }, `${r.data.total}건`) : null, body));
  }

  async function viewKnowledge(pid, ref) {
    const { token } = await projectHead(pid, "문서");
    const r = await api(`projects/${encodeURIComponent(pid)}/knowledge/ref?ref=${encodeURIComponent(ref)}`, { token });
    let body = "";
    if (r.status === 200) {
      body = typeof r.data.body === "string" ? r.data.body
        : r.data.proposal_md ? `## Context\n\n${r.data.rationale || ""}\n\n## Proposal\n\n${r.data.proposal_md}`
          : JSON.stringify(r.data.body ?? r.data, null, 2);
    }
    render(el("section", { class: "card" }, el("h1", {}, r.status === 200 ? r.data.title || r.data.path || r.data.id : "문서"), projectNav(pid, "wiki"),
      r.status === 200 ? el("div", {}, el("p", { class: "muted mono" }, `${r.data.authority || "hub"} · ${r.data.ref} · ${r.data.status || `v${r.data.revision}`}`),
        el("pre", { class: "wiki" }, body)) : alertBox("bad", errorText(r))));
  }

  const DCR_STATUS = { open: ["열림", "open"], accepted: ["승인됨", "approved"], rejected: ["거절됨", "planned"] };
  const dcrChip = (st) => { const [t, c] = DCR_STATUS[st] || [st, "planned"]; return el("span", { class: "chip " + c, title: st }, t); };

  async function viewDcrs(pid, id) {
    const { token, base, pr } = await projectHead(pid, "결정 변경 기록");
    const r = await api(`projects/${encodeURIComponent(pid)}/dcr${id ? `/${encodeURIComponent(id)}` : ""}`, { token });
    const principal = pr.status === 200 ? pr.data.principal : null;
    const canDecide = Boolean(principal && principal.can_manage);  // 소유자 — 요약 API 가 계산한다 (계정 로그인 포함)
    let body;
    if (r.status !== 200) body = alertBox("bad", errorText(r));
    else if (id) {
      const d = r.data;
      let decideBox = null;
      if (d.status === "open" && canDecide) {
        const why = el("textarea", { rows: "3", required: true, "aria-label": "판단 근거", "aria-describedby": "dcr-why-hint" });
        const msg = el("div");
        const decide = (decision) => async () => {
          // 오류는 자동 새로고침이 지우지 않게 한다 (dirty — 읽기 전에 사라지면 왜 막혔는지 모른다).
          if (!why.value.trim()) { dirty = true; msg.replaceChildren(alertBox("bad", "판단 근거를 적어야 결정할 수 있다 — 근거는 ADR 과 감사 기록에 남는다.")); why.focus(); return; }
          const res = await api(`projects/${encodeURIComponent(pid)}/dcr/${encodeURIComponent(d.id)}/decision`, {
            method: "POST", token, body: { decision, rationale: why.value.trim(), expected_version: d.version } });
          if (res.status !== 200) {
            dirty = true;
            const code = res.data?.error_code;
            msg.replaceChildren(alertBox("bad", code === "stale_decision_base"
              ? "이 DCR 이 가리키는 문서가 그 사이 바뀌었다 — 승인할 수 없다. 제안한 쪽이 새 판 위에서 다시 올려야 한다."
              : code === "version_conflict" ? "다른 사람이 먼저 이 DCR 을 바꿨다 — 새로고침해서 지금 상태를 본다." : errorText(res)));
            return;
          }
          dirty = false;
          pendingFlash = { kind: "ok", text: decision === "approve"
            ? `${d.id} 를 승인했다${res.data?.adr_path ? ` — ADR ${res.data.adr_path}` : ""}.` : `${d.id} 를 거절했다.` };
          route();
        };
        decideBox = el("section", { class: "decide-box", "aria-labelledby": "dcr-decide-h" },
          el("h2", { id: "dcr-decide-h" }, "결정"),
          el("label", { class: "field" }, "판단 근거 (필수)", why),
          el("p", { class: "muted", id: "dcr-why-hint" }, "승인하면 결정 기록(ADR)이 허브 위키 decisions/ 에 바로 남고, 거절해도 근거가 감사 기록에 남는다."),
          el("div", { class: "row" }, el("button", { type: "button", onclick: decide("approve") }, "승인"),
            el("button", { type: "button", class: "danger", onclick: decide("reject") }, "거절")), msg);
      } else if (d.status === "open") {
        decideBox = el("p", { class: "muted" }, "승인 · 거절은 이 프로젝트의 소유자가 한다 — 허브 계정으로 로그인한 승인된 소유자에게 단추가 보인다.");
      }
      body = el("div", {},
        el("div", { class: "row" }, dcrChip(d.status), el("span", { class: "muted" }, `제안 ${d.author} · ${d.version}판`), el("span", { class: "mono muted" }, d.id)),
        el("h2", {}, "근거"), el("pre", { class: "wiki" }, d.rationale), el("h2", {}, "제안"), el("pre", { class: "wiki" }, d.proposal_md),
        decideBox,
        el("h2", {}, "감사 기록"), el("ul", {}, d.timeline.map((e) => el("li", {}, when(e.at), ` · ${e.actor} · ${OP_LABEL[e.op] ? `${OP_LABEL[e.op]} (${e.op})` : e.op}`))),
        d.adr_path ? el("p", {}, "확정된 ADR ", el("span", { class: "mono" }, d.adr_path)) : null);
    } else {
      const order = { open: 0, accepted: 1, rejected: 2 };
      const list = r.data.dcrs.slice().sort((x, y) => (order[x.status] ?? 3) - (order[y.status] ?? 3));
      body = list.length ? el("ul", { class: "hits" }, list.map((d) => el("li", {}, dcrChip(d.status), " ",
        el("a", { href: `${base}/dcr/${encodeURIComponent(d.id)}` }, d.title), el("span", { class: "muted" }, ` · 제안 ${d.author}`),
        d.status === "open" && canDecide ? el("span", { class: "muted" }, " · 결정 대기") : null)))
        : el("p", { class: "muted" }, "등록된 결정 변경 기록(DCR)이 없다.");
    }
    render(el("section", { class: "card" }, el("h1", {}, id ? (r.status === 200 ? r.data.title : `DCR ${id}`) : "결정 변경 기록"), projectNav(pid, "dcr"), body));
  }

  function wikiLinks(path, text) {
    const dir = path.includes("/") ? path.slice(0, path.lastIndexOf("/") + 1) : "";
    const out = new Map();
    for (const m of text.matchAll(/\[([^\]]*)\]\(([^)\s]+?\.md)(#[^)]*)?\)/g)) {
      const href = m[2];
      if (/^[a-z][a-z0-9+.-]*:/i.test(href) || href.startsWith("/")) continue;
      const parts = [];
      for (const seg of (dir + href).split("/")) {
        if (seg === "..") { if (!parts.length) { parts.length = 0; parts.push(null); break; } parts.pop(); }
        else if (seg && seg !== ".") parts.push(seg);
      }
      if (parts.includes(null)) continue;
      out.set(parts.join("/"), m[1] || parts.join("/"));
    }
    for (const m of text.matchAll(/\[\[([^\]|#]+?)(?:[|#][^\]]*)?\]\]/g)) {
      const target = m[1].trim().replace(/\.md$/, "") + ".md";
      if (!target.startsWith("/") && !target.split("/").includes("..") && !out.has(target)) out.set(target, m[1].trim());
    }
    return [...out.entries()];
  }

  async function viewWikiPage(pid, path) {
    const { token, base } = await projectHead(pid, path);
    const r = await api(`projects/${encodeURIComponent(pid)}/wiki/page?path=${encodeURIComponent(path)}`, { token });
    if (r.status !== 200) { render(el("section", { class: "card" }, alertBox("bad", errorText(r)), el("a", { href: `${base}/w` }, "위키 목록"))); return; }
    const pg = r.data;
    const links = wikiLinks(path, pg.body);
    render(el("section", { class: "card" },
      el("div", { class: "row" }, el("h1", { class: "mono" }, pg.path), pg.generated ? chip("자동 생성", "planned") : chip(`${pg.version}판`, "planned")),
      pg.generated ? null : el("div", { class: "row muted" }, `${pg.updated_by || "—"} · `, when(pg.updated_at),
        pg.source && pg.source.sha ? el("span", { class: "mono" }, ` · 출처 ${pg.source.repo_key || ""}@${pg.source.sha.slice(0, 12)}`) : null),
      el("pre", { class: "wiki" }, pg.body),
      links.length ? el("div", {}, el("h2", {}, "이 페이지가 가리키는 위키 페이지"),
        el("ul", {}, links.map(([target, label]) => el("li", {}, el("a", { href: pageHref(base, target) }, label), " ",
          el("span", { class: "mono muted" }, target))))) : null,
      el("a", { href: `${base}/w` }, "← 위키 목록")));
  }

  // --- 화면: task 상세 · 주장 트리 · 라디오 결정 UX (M-053 WBS-53.1) --------------------------

  function decisionState(d, open) {
    if (open) return chip("열림", "open");
    return chip(d.state, d.state.startsWith("answered") || d.state.startsWith("changed") ? "answered" : "planned");
  }

  function renderPlanSection(pid, tid, plan, principal, planMd, onDone) {
    const openIds = new Set(plan.open_decisions);
    const interactive = openIds.size > 0 && !plan.has_errors && principal.can_answer;
    const inputs = {};

    function decisionBlock(d) {
      const isOpen = openIds.has(d.id);
      if (interactive && isOpen) {
        const openedBox = el("input", { type: "checkbox", "aria-label": `${d.id} 열어 보고 확인함` });
        const radios = d.options.map(([v, label]) => {
          const inp = el("input", {
            // 미리 고르지 않는다 — 사람이 고르거나 '기본값으로 답한다' 를 체크해야 답이 된다 (보지 않은 결정에 답이 나가지 않게).
            type: "radio", name: `dec_${d.id}`, value: v,
            onchange: () => { openedBox.checked = true; dirty = true; },
          });
          return el("label", { class: "option" }, inp, el("span", { class: "opt-value" }, v),
            el("span", {}, label), v === d.default ? chip("기본값", "planned") : null);
        });
        inputs[d.id] = { radios, openedBox, defaultVal: d.default };
        const det = el("details", { class: "decision open", "data-decision": d.id, open: true },
          el("summary", {}, el("span", { class: "row" }, el("strong", {}, `${d.id} [${d.claim_id}]`), decisionState(d, true), d.question)),
          el("div", { class: "claim-body" },
            el("div", { class: "options" }, radios),
            el("label", { class: "muted" }, openedBox, `선택지를 확인했다 — 고르지 않으면 기본값(${d.default})으로 답한다`)));
        openedBox.addEventListener("change", () => { dirty = true; });
        return det;
      }
      return el("div", { class: "decision" + (isOpen ? " open" : "") },
        el("div", { class: "row" }, el("strong", {}, `${d.id} [${d.claim_id}]`), decisionState(d, isOpen)),
        el("div", {}, d.question),
        el("div", { class: "muted" }, `기본값 ${d.default} · 선택지 ${d.options.map((o) => `${o[0]} (${o[1]})`).join(" · ")}`));
    }

    const byClaim = new Map();
    const orphanDecisions = [];
    const claimIds = new Set(plan.claims.map((c) => c.id));
    for (const d of plan.decisions) {
      if (claimIds.has(d.claim_id)) {
        if (!byClaim.has(d.claim_id)) byClaim.set(d.claim_id, []);
        byClaim.get(d.claim_id).push(d);
      } else {
        orphanDecisions.push(d);
      }
    }

    const treeNodes = plan.claims.map((c) => {
      const ds = byClaim.get(c.id) || [];
      return el("details", { class: "claim", open: true },
        el("summary", {}, `${c.id} — ${c.text}`),
        ds.length ? el("div", { class: "claim-body" }, ds.map(decisionBlock))
          : el("div", { class: "claim-body muted" }, "이 주장에 연결된 결정 없음"));
    });
    if (orphanDecisions.length) {
      treeNodes.push(el("details", { class: "claim", open: true },
        el("summary", {}, "연결된 주장이 없는 결정"),
        el("div", { class: "claim-body" }, orphanDecisions.map(decisionBlock))));
    }

    let statusNotice;
    if (!openIds.size) statusNotice = el("p", { class: "muted" }, "열린 결정이 없다.");
    else if (plan.has_errors) statusNotice = alertBox("warn", "계획에 오류가 있어 지금은 답할 수 없다 — 작업 중인 에이전트가 계획을 고치면 답할 수 있다.");
    else if (!principal.can_answer) statusNotice = alertBox("warn", principal.kind === "callsign"
      ? "결정에는 승인된 사람 콜사인만 답할 수 있다 — 이 콜사인은 아니다."
      : "결정에 답하려면 허브 계정으로 로그인하거나, 이 프로젝트의 승인된 사람 콜사인 토큰을 이 브라우저에 넣는다.");

    const treeEl = treeNodes.length ? el("div", { class: "tree" }, treeNodes) : null;
    const planRaw = el("details", {}, el("summary", {}, "계획 원문"), el("pre", {}, planMd || "(없음)"));

    if (!interactive) {
      return el("section", { class: "card" },
        el("h2", {}, "계획 · 결정"),
        plan.lint.filter((i) => i.severity === "error").map((i) => alertBox("bad", `${i.rule} ${i.ref} ${i.message}`)),
        treeEl,
        el("p", { class: "muted" }, `반영된 응답 ${plan.responses}건 · 계획 지문 `, el("span", { class: "mono" }, plan.digest.slice(0, 12))),
        statusNotice, planRaw);
    }

    const comment = el("textarea", { placeholder: "주석 (선택)", "aria-label": "주석" });
    const msg = el("div");
    const button = el("button", { type: "submit" }, "응답 보내기");
    return el("section", { class: "card" },
      el("h2", {}, "계획 · 결정"),
      plan.lint.filter((i) => i.severity === "error").map((i) => alertBox("bad", `${i.rule} ${i.ref} ${i.message}`)),
      el("form", { onsubmit: async (ev) => {
        ev.preventDefault();
        button.disabled = true;
        const values = {}, opened = {};
        const untouched = Object.entries(inputs).filter(([, inp]) => !inp.radios.some((r) => r.checked) && !inp.openedBox.checked).map(([id]) => id);
        if (untouched.length) {
          button.disabled = false;
          dirty = true;
          msg.replaceChildren(alertBox("bad", `아직 답하지 않은 결정이 있다: ${untouched.join(", ")} — 선택지를 고르거나 '선택지를 확인했다' 를 체크한다.`));
          return;
        }
        for (const [id, inp] of Object.entries(inputs)) {
          const picked = inp.radios.find((r) => r.checked);
          values[id] = picked ? picked.value : inp.defaultVal;
          opened[id] = inp.openedBox.checked;
        }
        const r = await api(`projects/${encodeURIComponent(pid)}/tasks/${encodeURIComponent(tid)}/responses`, {
          method: "POST", token: storedToken(pid),
          body: { plan_digest: plan.digest, values, opened, comments: comment.value.trim() ? { "-": comment.value } : {} } });
        button.disabled = false;
        if (r.status !== 200) { msg.replaceChildren(alertBox("bad", errorText(r))); return; }
        dirty = false;
        onDone(r.data.duplicate ? "같은 응답이 이미 있다 — 한 번만 반영된다." : "응답을 반영했다.");
      } },
        treeEl,
        el("p", { class: "muted" }, `반영된 응답 ${plan.responses}건 · 계획 지문 `, el("span", { class: "mono" }, plan.digest.slice(0, 12))),
        comment,
        el("div", { class: "submitbar" }, el("span", { class: "muted" }, "응답자 ", principal.callsign || "—"), button),
        msg),
      planRaw);
  }

  function eventRows(events, withTarget) {
    return events.slice().reverse().map((e) => el("tr", {},
      el("td", { class: "t-title" }, el("span", { title: e.op }, OP_LABEL[e.op] ? `${OP_LABEL[e.op]} (${e.op})` : e.op), withTarget ? el("span", { class: "t-id" }, `${e.target_kind} ${e.target_id}`) : null),
      el("td", { class: "t-status nowrap muted" }, when(e.at)),
      el("td", { class: "t-more", "data-label": "누가" }, e.callsign || "—"),
      el("td", { class: "t-more muted", "data-label": `#${e.seq} ·`, title: e.via }, viaLabel(e.via)),
      el("td", { class: "t-more" }, (e.before !== null || e.after !== null)
        ? el("details", {}, el("summary", {}, "바뀐 값"), el("pre", {}, JSON.stringify({ before: e.before, after: e.after }, null, 1)))
        : "")));
  }
  const eventHead = (withTarget) => el("thead", {}, el("tr", {},
    [withTarget ? "무엇 · 대상" : "무엇", "시각", "누가", "어디서", ""].map((h) => el("th", { scope: "col" }, h))));

  async function viewTask(pid, tid, flash) {
    const token = storedToken(pid);
    const [pr, r] = await Promise.all([
      api(`projects/${encodeURIComponent(pid)}`, { token }),
      api(`projects/${encodeURIComponent(pid)}/tasks/${encodeURIComponent(tid)}`, { token })]);
    const base = `#/p/${encodeURIComponent(pid)}`;
    setCrumbs([{ text: "프로젝트", href: "#/" }, { text: pr.status === 200 ? pr.data.project.display_name : pid, href: base }, { text: tid }]);
    if (r.status !== 200 || pr.status !== 200) { render(el("section", { class: "card" }, alertBox("bad", errorText(r.status !== 200 ? r : pr)))); return; }
    const principal = pr.data.principal;
    setWho(principal);
    const { task, plan, events } = r.data;
    const f = task.fields || {};
    const list = (xs) => (xs && xs.length ? el("ul", {}, xs.map((x) => el("li", {}, x))) : el("span", { class: "muted" }, "—"));
    render(
      flash ? alertBox("ok", flash) : null,
      el("section", { class: "card" },
        el("h1", {}, task.title),
        el("div", { class: "row" }, chip(task.status), chip(task.priority, "planned"), el("span", { class: "muted" }, `맡은 이 ${task.assignee || "—"}`),
          task.wbs ? el("span", { class: "mono muted" }, task.wbs) : null, el("span", { class: "mono muted" }, `${task.id} · v${task.version}`)),
        task.progress_note ? el("p", {}, el("strong", {}, "지금 하는 일 "), task.progress_note, task.progress_at ? el("span", { class: "muted" }, " · ", when(task.progress_at)) : null) : null,
        task.description ? el("p", {}, task.description) : null,
        f.category ? el("p", { class: "muted" }, "분류 ", [f.category.level_1, f.category.level_2, f.category.level_3].join(" / ")) : null,
        f.tests?.length ? el("div", {}, el("h2", {}, "테스트 · 최근 실행"), el("ul", {}, f.tests.map((test) => {
          const run = test.runs?.at(-1);
          return el("li", {}, `${test.name}${test.required ? " (필수)" : " (선택)"}: ${run?.status || "미실행"}${run?.summary ? ` — ${run.summary}` : ""}`);
        }))) : null,
        el("h2", {}, "완료 기준"), list(f.done_criteria),
        f.result ? el("div", {}, el("h2", {}, "결과"), el("p", {}, f.result)) : null,
        f.validation_result ? el("div", {}, el("h2", {}, "검증 결과"), el("p", {}, f.validation_result)) : null,
        task.commits && task.commits.length ? el("div", {}, el("h2", {}, "커밋"), list(task.commits.map((c) => `${c.sha} ${c.branch || ""} (${c.added_by})`))) : null),
      renderPlanSection(pid, tid, plan, principal, task.plan_md, (m) => viewTask(pid, tid, m)),
      el("section", { class: "card" }, el("h2", {}, "이력"),
        events.length ? el("div", { class: "table-wrap" }, el("table", {}, eventHead(false), el("tbody", {}, eventRows(events, false))))
          : el("p", { class: "muted" }, "없음")));
  }

  // --- 화면: 프로젝트 이력 ----------------------------------------------------------

  let eventsShown = 50;
  async function viewEvents(pid) {
    const token = storedToken(pid);
    const [pr, r] = await Promise.all([
      api(`projects/${encodeURIComponent(pid)}`, { token }),
      api(`projects/${encodeURIComponent(pid)}/events?limit=500`, { token })]);
    const base = `#/p/${encodeURIComponent(pid)}`;
    setCrumbs([{ text: "프로젝트", href: "#/" }, { text: pr.status === 200 ? pr.data.project.display_name : pid, href: base }, { text: "이력" }]);
    if (r.status !== 200) { render(el("section", { class: "card" }, alertBox("bad", errorText(r)))); return; }
    setWho(pr.status === 200 ? pr.data.principal : null);
    // 최근 것부터 50건씩 — 한 화면에 수백 줄을 쌓지 않는다.
    const all = r.data.events;
    const shown = all.slice(Math.max(0, all.length - eventsShown));
    const more = all.length - shown.length;
    render(el("section", { class: "card" }, el("h1", {}, "이력"), projectNav(pid, "events"),
      el("p", { class: "muted" }, `최근 ${shown.length}건 / 불러온 ${all.length}건 — 최신이 위`),
      el("div", { class: "table-wrap" }, el("table", { class: "stack events" }, eventHead(true), el("tbody", {}, eventRows(shown, true)))),
      more ? el("div", { class: "row pagination" }, el("button", { type: "button", class: "ghost", onclick: () => { eventsShown += 50; route({ preserveScroll: true }); } },
        `50건 더 보기 (남은 ${more}건)`)) : null));
  }

  // --- 길 · 자동 갱신 루프 ---------------------------------------------------------

  async function route(opts) {
    const keepScroll = opts && opts.preserveScroll;
    const sx = keepScroll ? window.scrollX : 0;
    const sy = keepScroll ? window.scrollY : 0;
    if (!keepScroll) dirty = false;
    const session = await api("session");
    signedInAccount = session.status === 200 && session.data.principal?.kind === "account";
    const hashUrl = new URL(location.hash.slice(1) || "/", location.href);
    const parts = hashUrl.pathname.replace(/^\/?/, "").replace(/\/$/, "").split("/").map(decodeURIComponent);
    try {
      if (parts[0] === "harnesses") {
        await viewHarnesses();
      } else if (parts[0] === "p" && parts[1]) {
        if (parts[2] === "t" && parts[3]) await viewTask(parts[1], parts[3]);
        else if (parts[2] === "orch") await viewOrchestration(parts[1]);
        else if (parts[2] === "confirmations") await viewConfirmations(parts[1]);
        else if (parts[2] === "ideas") await viewIdeas(parts[1], parts[3] || "");
        else if (parts[2] === "roadmap") await viewRoadmap(parts[1]);
        else if (parts[2] === "events") await viewEvents(parts[1]);
        else if (parts[2] === "c" && parts[3]) await viewCallsign(parts[1], parts[3]);
        else if (parts[2] === "guide") await viewGuide(parts[1]);
        else if (parts[2] === "w") await viewWiki(parts[1], parts[3] === "q" ? parts[4] : "");
        else if (parts[2] === "k" && parts[3]) await viewKnowledge(parts[1], parts[3]);
        else if (parts[2] === "dcr") await viewDcrs(parts[1], parts[3] || "");
        else if (parts[2] === "wp" && parts[3]) await viewWikiPage(parts[1], parts[3]);
        else await viewProject(parts[1], parts[2] === "s" ? parts[3] : "", hashUrl.searchParams);
      } else {
        await viewProjects();
      }
      if (keepScroll) window.scrollTo(sx, sy);
    } catch (e) {
      render(el("section", { class: "card" }, alertBox("bad", "허브에 연결할 수 없다: " + e)));
    }
  }

  window.addEventListener("hashchange", () => route());
  setInterval(() => {
    if (document.visibilityState === "hidden") return;
    if (dirty) { showRefreshNotice(); return; }
    route({ preserveScroll: true });
  }, 10000);

  fetch("../healthz", { credentials: "omit" }).then((r) => r.json()).then((h) => {
    try { if (h.public_url) hubHost = new URL(h.public_url).host; } catch (e) { /* 그대로 */ }
  }).catch(() => {}).finally(() => route());
})();
