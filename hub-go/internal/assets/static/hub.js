// 허브 화면 (hub_spec §4.6 · §4.7 · hub_orchestration_spec §10).
// 사람은 허브 계정 세션 쿠키로 로그인한다. 에이전트 콜사인 토큰 입력도 하위 호환으로 남긴다.
// 모든 링크 · API 호출은 상대 경로 (R13.4). DOM 은 textContent 로만 만든다 (서버 문자열을 HTML 로 해석하지 않는다).
"use strict";

(function () {
  const app = document.getElementById("app");
  const crumbs = document.getElementById("crumbs");
  const adminLink = document.getElementById("admin-link");
  const whoEl = document.getElementById("who");
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
  const chip = (text, cls) => el("span", { class: "chip " + (cls || text) }, text);
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
  function markDirty() { dirty = true; }

  app.addEventListener("input", markDirty);
  app.addEventListener("change", markDirty);

  function render(...nodes) {
    const flash = pendingFlash;
    pendingFlash = null;
    hideRefreshNotice();
    app.replaceChildren(...(flash ? [alertBox(flash.kind, flash.text)] : []), ...nodes.filter((node) => node !== null && node !== undefined));
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
      whoEl.textContent = `${principal.callsign} (${principal.callsign_kind}${principal.callsign_kind === "human" && !principal.human_approved ? " · 승인 전" : ""} · ${principal.role})`;
    } else {
      whoEl.textContent = `공용 ${principal.kind} 토큰 — 읽기 전용`;
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
      ["confirmations", "확인 요청", `${base}/confirmations`],
      ["roadmap", "로드맵", `${base}/roadmap`],
      ["events", "이력", `${base}/events`],
      ["guide", "지침", `${base}/guide`],
      ["wiki", "지식", `${base}/w`],
      ["dcr", "결정", `${base}/dcr`],
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
    } }, el("label", {}, "토큰 넣기", input), el("button", { type: "submit" }, "이 브라우저에 두기"), msg);
  }

  function accountPanel(account, onDone) {
    const status = el("div");
    if (account) {
      const linkToken = el("input", { required: true, autocomplete: "off", placeholder: "다른 프로젝트의 승인된 사람 콜사인 토큰" });
      return el("section", { class: "card" }, el("h2", {}, "허브 계정"),
        el("p", {}, `${account.display_name} (${account.username})로 로그인됨`),
        el("form", { class: "row", onsubmit: async (ev) => { ev.preventDefault(); const r = await api("account/link", { method: "POST", token: linkToken.value.trim(), forceToken: true, body: {} }); if (r.status !== 200) status.replaceChildren(alertBox("bad", errorText(r))); else { linkToken.value = ""; status.replaceChildren(alertBox("ok", `콜사인을 연결했다: ${r.data.linked.callsign}`)); onDone(); } } }, linkToken, el("button", { type: "submit" }, "콜사인 연결")), status,
        el("button", { class: "ghost", onclick: async () => { const r = await api("account/logout", { method: "POST", body: {} }); if (r.status === 200) { signedInAccount = false; location.hash = "#/"; onDone(); } else status.replaceChildren(alertBox("bad", errorText(r))); } }, "로그아웃"));
    }
    const loginUser = el("input", { required: true, autocomplete: "username", placeholder: "계정 이름" });
    const loginPass = el("input", { required: true, type: "password", autocomplete: "current-password", placeholder: "비밀번호" });
    const enrollToken = el("input", { required: true, autocomplete: "off", placeholder: "기존 승인된 사람 콜사인 토큰" });
    const enrollUser = el("input", { required: true, autocomplete: "username", placeholder: "계정 이름" });
    const enrollName = el("input", { required: true, autocomplete: "name", placeholder: "표시 이름" });
    const enrollPass = el("input", { required: true, type: "password", autocomplete: "new-password", minlength: "12", placeholder: "비밀번호 (12자 이상)" });
    return el("section", { class: "card" }, el("h2", {}, "허브 계정 로그인"),
      el("p", { class: "muted" }, "계정은 이 브라우저에 토큰을 저장하지 않는다. 처음에는 승인된 사람 콜사인 토큰으로 1회 등록한다."),
      el("form", { class: "row", onsubmit: async (ev) => { ev.preventDefault(); const r = await api("account/login", { method: "POST", body: { username: loginUser.value, password: loginPass.value } }); if (r.status !== 200) status.replaceChildren(alertBox("bad", errorText(r))); else { signedInAccount = true; dirty = false; onDone(); } } }, loginUser, loginPass, el("button", { type: "submit" }, "로그인")),
      el("details", {}, el("summary", {}, "계정 최초 등록"),
        el("form", { class: "row", onsubmit: async (ev) => { ev.preventDefault(); const r = await api("account/enroll", { method: "POST", token: enrollToken.value.trim(), body: { username: enrollUser.value, display_name: enrollName.value, password: enrollPass.value } }); if (r.status !== 200) status.replaceChildren(alertBox("bad", errorText(r))); else { signedInAccount = true; enrollToken.value = ""; dirty = false; onDone(); } } }, enrollToken, enrollUser, enrollName, enrollPass, el("button", { type: "submit" }, "계정 등록"))), status);
  }

  function registerForm(pid, onDone) {
    const name = el("input", { type: "text", placeholder: "콜사인 (예: yk-desk)", autocomplete: "off", "aria-label": "콜사인" });
    const kind = el("select", { "aria-label": "종류" }, el("option", { value: "human" }, "human (사람)"), el("option", { value: "agent" }, "agent"));
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
          msg.replaceChildren(alertBox("warn", `등록했지만 브라우저 저장소에 둘 수 없다 — 토큰을 지금 옮겨 둔다: ${r.data.token}`));
          return;
        }
        pendingFlash = { kind: "ok", text: `${r.data.callsign} 로 등록했다 — 토큰은 이 브라우저에만 있고 다시 나오지 않는다.${r.data.human_pending ? " human 은 소유자 승인 전까지 결정에 답할 수 없다." : ""}` };
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
      el("div", { class: "row" }, ...["in_progress", "blocked", "planned", "done"].map((s) => chip(`${s} ${p.task_counts[s] || 0}`, s))),
      storedToken(p.id) ? el("div", { class: "muted" }, "이 브라우저에 콜사인 토큰 있음") : null));
    render(
      accountPanel(projectList.status === 200 && projectList.data.principal?.kind === "account" ? projectList.data.account : null, () => route()),
      el("section", { class: "card" }, el("h1", {}, "프로젝트"),
        cards.length ? el("div", { class: "grid" }, cards)
          : el("p", { class: "muted" }, projectList.status === 401
            ? "토큰 없는 화면 읽기가 꺼져 있다 (허브 기본). 콜사인 토큰을 넣으면 그 프로젝트가 보인다."
            : "등록된 프로젝트가 없다.")),
      el("section", { class: "card admin-entry" }, el("div", {}, el("h2", {}, "허브 전체 관리"),
        el("p", { class: "muted" }, "하네스 등록 제보를 검토하고 사람 담당자 명부를 관리합니다. 관리자 토큰이 필요합니다.")),
        el("a", { class: "admin-entry-button", href: "#/harnesses" }, principal?.kind === "admin" ? "관리 화면 열기" : "관리자 로그인")),
      errors.length ? el("section", { class: "card" }, errors.map((e) => alertBox("bad", e))) : null,
      el("section", { class: "card" }, el("h2", {}, "이 브라우저에 콜사인 토큰 넣기"), tokenForm(() => route())));
  }

  async function viewHarnesses() {
    setCrumbs([{ text: "프로젝트", href: "#/" }, { text: "하네스 등록 검토" }]);
    const token = storedAdminToken();
    if (!token) {
      const input = el("input", { type: "password", autocomplete: "off", placeholder: "hub admin 토큰", "aria-label": "hub admin 토큰" });
      const message = el("div");
      setWho(null); adminLink.textContent = "관리자 로그인";
      render(el("section", { class: "card" }, el("h1", {}, "허브 관리자 로그인"),
        el("p", {}, "허브 관리자 토큰으로 하네스 제보를 검토하고 사람 담당자 명부를 관리한다."),
        el("h2", {}, "관리자 토큰 발급"),
        el("p", { class: "muted" }, "토큰은 허브 서버에서 한 번 발급한다. Python 또는 Go 허브 터미널에서 실행한다."),
        el("pre", {}, "Python: python -m workflow_kit hub admin --db <DB 경로> token issue --role admin --name <이름>\nGo: workflow-hub admin --db <DB 경로> token issue --role admin --name <이름>"),
        el("p", { class: "muted" }, "로그인하면 토큰은 이 브라우저에 저장된다. 공유 기기에서는 사용 후 관리자 토큰을 지운다."),
        el("form", { class: "row", onsubmit: async (ev) => {
          ev.preventDefault();
          const submitted = input.value.trim();
          const r = await api("session", { token: submitted });
          if (r.status !== 200 || r.data.principal.kind !== "admin") {
            const reason = r.status === 200 ? "이 토큰은 허브 관리자 권한이 아니다. web 또는 콜사인 토큰 대신 admin 토큰을 입력한다."
              : r.status === 401 || r.status === 403 ? "토큰을 확인할 수 없다. 허브 관리자 토큰을 다시 확인한다." : errorText(r);
            message.replaceChildren(alertBox("bad", reason)); return;
          }
          if (!storeAdminToken(submitted)) { message.replaceChildren(alertBox("bad", "브라우저 저장소에 토큰을 보관할 수 없다. 브라우저 저장소 설정을 확인한다.")); return; }
          input.value = ""; dirty = false; route();
        } }, el("label", {}, "관리자 토큰", input), el("button", { type: "submit" }, "관리자 모드로 로그인"), message)));
      return;
    }
    const [session, reportsRes, peopleRes, registryRes] = await Promise.all([
      api("session", { token }), api("harness-reports?status=pending", { token }),
      api("harness-people", { token }), api("harness-registry", { token })]);
    if (session.status !== 200 || session.data.principal.kind !== "admin") {
      const invalid = session.status === 401 || session.status === 403 || session.status === 200;
      if (invalid) { try { localStorage.removeItem(`hub:${hubHost}:admin-token`); } catch (e) { /* 저장소 없음 */ } }
      render(el("section", { class: "card" }, alertBox("bad", invalid ? "관리자 토큰이 유효하지 않다. 새 토큰으로 로그인한다." : `관리자 세션을 확인할 수 없다. 토큰은 보존했다. ${errorText(session)}`),
        el("button", { onclick: () => { route(); } }, invalid ? "다시 로그인" : "다시 확인")));
      return;
    }
    setWho(session.data.principal);
    adminLink.textContent = "관리 화면";
    if ([reportsRes, peopleRes, registryRes].some((r) => r.status !== 200)) {
      render(el("section", { class: "card" }, alertBox("bad", errorText([reportsRes, peopleRes, registryRes].find((r) => r.status !== 200))))); return;
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
          : alertBox("warn", "자동 셋업 승인에 필요한 정보가 부족하다. mcp_transports에 streamable-http, config_formats에 mcp-http-json-v1, 두 후보 경로 목록을 포함해 다시 제보해야 한다."),
        el("label", {}, "검토 메모", note),
        el("div", { class: "row" }, el("button", { disabled: !people.length, onclick: () => decide("approve") }, "담당자를 지정하고 등록 승인"),
          el("button", { class: "danger", onclick: () => decide("reject") }, "거절")), result);
    });
    render(el("section", { class: "card" }, el("h1", {}, "하네스 제보 검토"),
      el("nav", { class: "nav-links" }, el("a", { href: "#/" }, "프로젝트"), el("a", { class: "on", href: "#/harnesses" }, "하네스 검토")),
      el("p", {}, "승인은 사람 명부에 등록된 담당자를 한 명 이상 지정해야 한다."), addPerson,
      el("button", { class: "ghost", onclick: () => { try { localStorage.removeItem(`hub:${hubHost}:admin-token`); } catch (e) { /* 저장소 없음 */ } route(); } }, "관리자 토큰 지우기")),
      cards.length ? cards : el("section", { class: "card" }, el("p", { class: "muted" }, "대기 중인 제보가 없다.")));
  }

  // --- 화면: 프로젝트 · KPI · task 목록 --------------------------------------------------

  const STATUSES = ["", "in_progress", "blocked", "planned", "done"];

  function kpiCard(label, value, sub, tone) {
    return el("div", { class: "kpi " + (tone || "") },
      el("div", { class: "kpi-label" }, label),
      el("div", { class: "kpi-value" }, String(value)),
      sub ? el("div", { class: "kpi-sub" }, sub) : null);
  }

  async function viewProject(pid, status, query) {
    query = query || new URLSearchParams();
    const token = storedToken(pid);
    const pr = await api(`projects/${encodeURIComponent(pid)}`, { token });
    if (pr.status !== 200) {
      setCrumbs([{ text: "프로젝트", href: "#/" }, { text: pid }]);
      render(el("section", { class: "card" }, alertBox("bad", errorText(pr)),
        token ? forgetButton(pid, route) : null, el("h2", {}, "토큰 넣기"), tokenForm(() => route())));
      return;
    }
    const { project, principal, summary } = pr.data;
    setWho(principal);
    setCrumbs([{ text: "프로젝트", href: "#/" }, { text: project.display_name }]);
    const pageLimit = Number(query.get("limit") || 25);
    const pageOffset = Number(query.get("offset") || 0);
    const listQuery = new URLSearchParams({ limit: String(pageLimit), offset: String(pageOffset) });
    if (status) listQuery.set("status", status);
    for (const key of ["roadmap", "milestone", "wbs", "category_level_1", "category_level_2", "category_level_3"]) {
      if (query.get(key)) listQuery.set(key, query.get(key));
    }
    const [tr, cr] = await Promise.all([
      api(`projects/${encodeURIComponent(pid)}/tasks?${listQuery}`, { token }),
      api(`projects/${encodeURIComponent(pid)}/callsigns`, { token })]);
    const base = `#/p/${encodeURIComponent(pid)}`;
    const sum = summary || {};
    const sc = sum.session_counts || {};
    const activeSessions = (sc.idle || 0) + (sc.working || 0) + (sc.waiting || 0);
    const unknownSessions = sum.unknown_sessions || 0;
    const orch = sum.orchestrator;
    const tc = project.task_counts || {};

    const attention = [];
    if (orch && orch.halted) {
      attention.push(alertBox("bad", "오케스트레이션이 정지(halted)돼 있다. ", el("a", { href: `${base}/orch` }, "오케스트레이션 판으로")));
    }
    if ((sum.pending_approvals || 0) > 0) {
      attention.push(alertBox("warn", `승인 대기 중인 중계 요청 ${sum.pending_approvals}건 — `, el("a", { href: `${base}/orch` }, "여기서 승인·거절")));
    }
    if ((sum.unacknowledged || 0) > 0) {
      attention.push(alertBox("warn", `10분 이상 미확인 메시지 ${sum.unacknowledged}건 — `, el("a", { href: `${base}/orch` }, "오케스트레이션 판 확인")));
    }

    const kpis = el("section", { class: "kpis", "aria-label": "프로젝트 요약" },
      kpiCard("진행 · 막힘 task", `${tc.in_progress || 0} / ${tc.blocked || 0}`, `전체 ${Object.values(tc).reduce((a, b) => a + b, 0)}건`, (tc.blocked || 0) > 0 ? "warn" : "info"),
      kpiCard("열린 결정 task", sum.open_decision_tasks || 0, "사람 응답 필요", (sum.open_decision_tasks || 0) > 0 ? "warn" : "ok"),
      kpiCard("승인 대기 요청", sum.pending_approvals || 0, "세션 띄우기 · 멈춤", (sum.pending_approvals || 0) > 0 ? "warn" : "ok"),
      kpiCard("활성 · unknown 세션", `${activeSessions} / ${unknownSessions}`, `전체 ${sum.sessions_total || 0} (ended ${sc.ended || 0})`, unknownSessions > 0 ? "bad" : "info"),
      kpiCard("오케스트레이터", orch ? `${orch.callsign}${orch.halted ? " (정지)" : ""}` : "미지정",
        orch ? `배정 열림 ${sum.open_assignments || 0}건` : "hub_orch_declare 로 지정", orch && orch.halted ? "bad" : orch ? "ok" : ""));

    const statusFilters = el("nav", { class: "filters", "aria-label": "상태" }, STATUSES.map((s) => {
      const next = new URLSearchParams(query);
      next.set("limit", String(pageLimit)); next.set("offset", "0");
      next.delete("status");
      const suffix = next.toString() ? `?${next}` : "";
      return el("a", { href: `${s ? `${base}/s/${encodeURIComponent(s)}` : base}${suffix}`, class: s === (status || "") ? "on" : "" }, s || "전체");
    }));
    const rows = tr.status === 200 ? tr.data.tasks.map((t) => el("tr", {},
      el("td", { class: "mono nowrap" }, el("a", { href: `${base}/t/${encodeURIComponent(t.id)}`, title: t.id }, t.id)),
      el("td", { class: "title" }, t.title),
      el("td", { class: "muted" }, t.fields?.category ? [t.fields.category.level_1, t.fields.category.level_2, t.fields.category.level_3].join(" / ") : "—"),
      el("td", {}, chip(t.status)),
      el("td", {}, t.assignee || "—"),
      el("td", { class: "muted progress" }, t.progress_note ? el("div", { class: "clamp-2", title: t.progress_note }, t.progress_note) : ""),
      el("td", { class: "muted nowrap" }, when(t.updated_at)))) : [];
    const facets = tr.data?.facets || {};
    const filterOptions = (key, label, values) => el("label", {}, label,
      el("select", { name: key, "aria-label": label },
        el("option", { value: "" }, "전체"),
        (values || []).map((value) => el("option", { value, selected: query.get(key) === value },
          key === "roadmap" ? (value === "linked" ? "연결됨" : "미지정") : value))));
    const listFilters = el("form", { class: "task-filters", onsubmit: (ev) => {
      ev.preventDefault();
      const next = new URLSearchParams();
      for (const key of ["roadmap", "milestone", "wbs", "category_level_1", "category_level_2", "category_level_3"]) {
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
      filterOptions("category_level_1", "카테고리 1", facets.category_level_1),
      filterOptions("category_level_2", "카테고리 2", facets.category_level_2),
      filterOptions("category_level_3", "카테고리 3", facets.category_level_3),
      el("button", { type: "submit" }, "분류 적용"));
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
      el("div", { class: "row" }, el("span", { class: "mono muted" }, t.id), chip(t.status), chip(t.priority, "planned")),
      el("h3", {}, t.title),
      el("p", { class: "muted" }, t.wbs || "로드맵 미지정", " · ", t.fields?.category ? [t.fields.category.level_1, t.fields.category.level_2, t.fields.category.level_3].filter(Boolean).join(" / ") : "카테고리 없음"),
      t.progress_note ? el("p", {}, t.progress_note) : null,
      el("div", { class: "muted" }, `맡은 이 ${t.assignee || "—"} · `, when(t.updated_at)))) : [];
    const listView = viewMode === "card"
      ? cards.length ? el("div", { class: "grid task-cards" }, cards) : el("p", { class: "muted" }, "조건에 맞는 task 가 없다.")
      : rows.length ? el("div", { class: "table-wrap" }, el("table", { class: "tasks" },
          el("colgroup", {}, ["c-id", "c-title", "c-category", "c-status", "c-who", "c-doing", "c-when"].map((c) => el("col", { class: c }))),
          el("thead", {}, el("tr", {}, ["ID", "제목", "카테고리", "상태", "맡은 이", "지금 하는 일", "고친 때"].map((h) => el("th", {}, h)))),
          el("tbody", {}, rows))) : el("p", { class: "muted" }, "조건에 맞는 task 가 없다.");
    const pagination = tr.status === 200 ? el("div", { class: "row pagination" },
      el("span", { class: "muted" }, `${total}개 · ${page}/${pageCount}페이지`),
      el("a", { class: page <= 1 ? "disabled" : "", href: pageQuery(Math.max(0, pageOffset - pageLimit)) }, "이전"),
      el("a", { class: page >= pageCount ? "disabled" : "", href: pageQuery(Math.min((pageCount - 1) * pageLimit, pageOffset + pageLimit)) }, "다음")) : null;
    render(
      el("section", { class: "card" },
        el("h1", {}, project.display_name),
        el("div", { class: "row muted" }, el("span", { class: "mono" }, project.id), `소유자 ${project.owner_callsign}`),
        projectNav(pid, "tasks"),
        principal.auth_mode === "account"
          ? accountPanel(principal.account, route)
          : principal.kind === "callsign"
          ? el("div", { class: "row" }, forgetButton(pid, route))
          : el("div", {}, el("h2", {}, "이 브라우저의 콜사인"), registerForm(pid, route), tokenForm(() => route()))),
      ...attention,
      kpis,
      callsignSection(pid, principal, cr),
      el("section", { class: "card" }, el("h2", {}, "task"), statusFilters, listFilters,
        el("div", { class: "row view-switch" }, el("span", {}, "보기"),
          el("a", { class: viewMode === "table" ? "on" : "", href: pageQuery(pageOffset, "table") }, "표"),
          el("a", { class: viewMode === "card" ? "on" : "", href: pageQuery(pageOffset, "card") }, "카드")),
        tr.status !== 200 ? alertBox("bad", errorText(tr))
          : listView, pagination));
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
      if (canManage) {
        if (orch) {
          controls.push(el("button", {
            type: "button", class: orch.halted ? "" : "danger",
            onclick: async () => {
              const res = await api(`projects/${encodeURIComponent(pid)}/orchestration/halt`, {
                method: "POST", token: storedToken(pid), body: { on: !orch.halted } });
              if (res.status !== 200) { msg.replaceChildren(alertBox("bad", errorText(res))); return; }
              dirty = false;
              pendingFlash = { kind: "ok", text: res.data.halted ? "오케스트레이션을 정지(halt)했다." : "오케스트레이션 정지를 풀었다." };
              route();
            },
          }, orch.halted ? "정지 풀기 (resume)" : "전체 정지 (halt)"));
        }
        const sel = el("select", { "aria-label": "오케스트레이터 대상 세션" },
          activeSessions.length
            ? activeSessions.map((s) => el("option", { value: s.id }, `${s.id} · ${s.callsign} (${s.harness}/${s.status})`))
            : el("option", { value: "" }, "활성 세션 없음"));
        controls.push(sel,
          el("button", {
            type: "button", class: "ghost", disabled: !activeSessions.length || undefined,
            onclick: () => postLease({ action: orch ? "transfer" : "declare", session: sel.value },
              orch ? `${sel.value} 로 오케스트레이터를 인계했다.` : `${sel.value} 를 오케스트레이터로 지정했다.`),
          }, orch ? "세션 인계 (transfer)" : "오케스트레이터 지정"));
        if (orch) {
          controls.push(el("button", { type: "button", class: "ghost", onclick: () => postLease({ action: "release" }, "오케스트레이터 lease 를 해제했다.") }, "lease 해제"));
        }
      }
      return el("section", { class: "card" },
        el("div", { class: "row" }, el("h1", {}, "오케스트레이션"),
          orch && orch.halted ? chip("정지 (halted)", "halted") : null),
        projectNav(pid, "orch"),
        orch ? el("div", { class: "row" }, "오케스트레이터 ", el("strong", {}, orch.callsign),
          el("span", { class: "mono muted" }, orch.session), "만료 ", when(orch.expires_at))
          : el("p", { class: "muted" }, "지정된 오케스트레이터가 없다."),
        controls.length ? el("div", { class: "row" }, controls) : el("p", { class: "muted" }, "정지 · lease 지정 · 승인은 이 프로젝트의 승인된 owner 콜사인 토큰으로만 한다."),
        msg);
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
          `호스트 ${req.host_id}`, `· 요청 ${req.requested_by} · `, when(req.created_at)),
        el("div", {}, detailText),
        req.decided_by ? el("div", { class: "muted" }, `결정 ${req.decided_by} · `, when(req.decided_at)) : null,
        req.result && Object.keys(req.result).length ? el("div", { class: "mono muted" }, JSON.stringify(req.result)) : null,
        req.state === "pending_approval" && canManage ? el("div", { class: "row" }, note, decideBtn("approve", "승인"), decideBtn("reject", "거절", "ghost")) : null,
        msg);
    };

    const approvalsSection = el("section", { class: "card" },
      el("h2", {}, `세션 승인 대기 (${pendingReqs.length})`),
      pendingReqs.length ? pendingReqs.map(reqCard) : el("p", { class: "muted" }, "승인 대기 중인 요청이 없다."),
      otherReqs.length ? el("details", {}, el("summary", {}, `이전 요청 기록 (${otherReqs.length})`),
        el("div", {}, otherReqs.map(reqCard))) : null);

    const sessCountsRow = el("div", { class: "row" },
      ...["working", "waiting", "idle", "ended"].map((st) => chip(`${st} ${sc[st] || 0}`, st)),
      chip(`unknown ${d.unknown_sessions || 0}`, (d.unknown_sessions || 0) > 0 ? "unknown" : "planned"));

    const sessRows = d.sessions.map((s) => el("tr", {},
      el("td", { class: "mono nowrap" }, s.id, s.orchestrator ? " " : null, s.orchestrator ? chip("오케스트레이터", "approved") : null),
      el("td", {}, el("a", { href: `${base}/c/${encodeURIComponent(s.callsign)}` }, s.callsign)),
      el("td", {}, s.harness || "—", s.kind === "worker" ? " (worker)" : ""),
      el("td", {}, chip(s.status, s.status)),
      el("td", { class: "mono muted" }, (s.delivery || []).join(", ") || "—"),
      el("td", {}, String(s.open_assignments || 0)),
      el("td", { class: "mono muted" }, s.host_id || "로컬/직접"),
      el("td", { class: "muted nowrap" }, when(s.last_signal_at))));

    const sessionsSection = el("section", { class: "card" },
      el("h2", {}, `세션 (${d.sessions.length})`), sessCountsRow,
      d.sessions.length ? el("div", { class: "table-wrap" }, el("table", {},
        el("thead", {}, el("tr", {}, ["세션", "콜사인", "하네스", "상태", "전달", "열린 배정", "호스트", "마지막 신호"].map((h) => el("th", {}, h)))),
        el("tbody", {}, sessRows))) : el("p", { class: "muted" }, "등록된 세션이 없다."));

    const unackSection = d.unacknowledged.length ? el("section", { class: "card" },
      el("h2", {}, `미확인 메시지 unacknowledged (${d.unacknowledged.length})`),
      d.unacknowledged.map((m) => alertBox("warn",
        `${m.id} → ${m.to_kind}:${m.to_id} (${m.kind}${m.ref_task ? ` · ${m.ref_task}` : ""}) · 경로 ${m.delivered_via || "—"}`))) : null;

    const assignRows = d.assignments.map((a) => el("tr", {},
      el("td", { class: "mono nowrap" }, el("a", { href: `${base}/t/${encodeURIComponent(a.task_id)}` }, a.task_id)),
      el("td", {}, a.task_title || "—", a.progress_note ? el("div", { class: "muted clamp-2" }, a.progress_note) : null),
      el("td", {}, chip(a.state, a.state), a.message_state === "unacknowledged" ? el("span", {}, " ", chip("unack", "unack")) : null),
      el("td", {}, a.callsign, el("div", { class: "mono muted" }, a.session_id)),
      el("td", { class: "muted" }, a.delivered_via || "—", a.delivery_count ? ` (${a.delivery_count}회)` : ""),
      el("td", { class: "muted" }, a.return_reason || (a.report && a.report.summary) || when(a.offered_at) || "—")));

    const assignSection = el("section", { class: "card" },
      el("h2", {}, `배정 현황 (${d.assignments.length})`),
      d.assignments.length ? el("div", { class: "table-wrap" }, el("table", {},
        el("thead", {}, el("tr", {}, ["task", "제목 · 진척", "상태", "대상", "전달", "사유 · 보고"].map((h) => el("th", {}, h)))),
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
            alertBox("ok", `1회용 초대 코드(이 화면에서만 보임 · 만료 ${res.data.expires_at}): ${res.data.invite}`),
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
          el("thead", {}, el("tr", {}, ["호스트", "이름", "하네스", "허용 digest", "마지막 폴링", ""].map((h) => el("th", {}, h)))),
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
    const cards = requests.map((req) => {
      const note = el("textarea", { rows: "2", placeholder: "결정 메모 (선택)" });
      const decide = (decision) => async () => {
        const r = await api(`projects/${encodeURIComponent(pid)}/confirmations/${encodeURIComponent(req.id)}`, {
          method: "POST", token, body: { decision, note: note.value.trim() },
        });
        if (r.status !== 200) { pendingFlash = { kind: "bad", text: errorText(r) }; return route(); }
        pendingFlash = { kind: "ok", text: `요청 ${req.id} ${decision === "approve" ? "승인" : "거절"} — A2A로 결과를 보냈다.` };
        dirty = false;
        route();
      };
      return el("section", { class: "card" },
        el("div", { class: "row" }, el("h2", {}, req.title), chip("승인 대기", "blocked")),
        el("div", { class: "muted" }, `${req.requested_by} · ${req.created_at}`),
        el("p", {}, req.question), req.details ? el("pre", { class: "wrap" }, req.details) : null,
        el("div", { class: "row" }, note,
          el("button", { type: "button", onclick: decide("approve") }, "승인"),
          el("button", { class: "danger", type: "button", onclick: decide("reject") }, "거절")));
    });
    render(el("section", { class: "card" }, el("h1", {}, "에이전트 확인 요청"),
      el("p", { class: "muted" }, "요청에 답하면 승인 또는 거절 결과가 요청한 콜사인의 A2A 받은편지함으로 전달됩니다. 승인은 요청 내용을 승인하는 결정이며, 작업은 에이전트가 결과를 확인한 뒤 진행합니다."),
      projectNav(pid, "confirmations")),
      ...(cards.length ? cards : [el("section", { class: "card muted" }, "대기 중인 에이전트 확인 요청이 없습니다.")]));
  }

  // --- 화면: 로드맵 (M-053 WBS-53.1) -----------------------------------------------------

  function renderWbsNode(base, node) {
    return el("li", { class: "wbs-node" },
      el("div", { class: "row" }, el("span", { class: "mono" }, node.id), chip(node.derived_status), el("span", {}, node.title),
        node.total_leaves ? el("span", { class: "muted" }, `(${node.done_leaves}/${node.total_leaves})`) : null),
      node.linked_task_ids && node.linked_task_ids.length
        ? el("div", { class: "row" }, node.linked_task_ids.map((tid) => el("a", { class: "mono", href: `${base}/t/${encodeURIComponent(tid)}` }, tid)))
        : null,
      node.children && node.children.length
        ? el("ul", { class: "wbs-list" }, node.children.map((ch) => renderWbsNode(base, ch))) : null);
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
    const msCards = st.milestones.map((m) => el("section", { class: "card" },
      el("div", { class: "row" }, el("strong", { class: "mono" }, m.id), chip(m.sdlc_phase, "planned"),
        chip(`선언 ${m.declared_status}`, m.declared_status), chip(`파생 ${m.derived_status}`, m.derived_status),
        m.id === st.current_milestone_id ? chip("현재 마일스톤", "in_progress") : null),
      el("h2", {}, m.title),
      el("div", { class: "meter" },
        el("div", { class: "muted" }, `WBS leaf ${m.done_leaves} / ${m.total_leaves} (${Math.round((m.progress || 0) * 100)}%)`),
        el("progress", { value: m.progress || 0, max: 1 })),
      m.wbs && m.wbs.length ? el("ul", { class: "wbs-list" }, m.wbs.map((w) => renderWbsNode(base, w))) : null));
    render(
      el("section", { class: "card" }, el("h1", {}, "로드맵"), projectNav(pid, "roadmap"),
        el("div", { class: "row muted" }, `마일스톤 ${st.milestones.length}개`,
          st.current_milestone_id ? ` · 현재 ${st.current_milestone_id}` : "",
          st.exempt_tasks ? ` · exempt ${st.exempt_tasks.length}건` : "")),
      st.issues && st.issues.length ? el("section", { class: "card" }, el("h2", {}, `로드맵 경고 (${st.issues.length})`),
        el("ul", {}, st.issues.map((i) => el("li", {}, el("span", { class: "mono" }, i.code), ` — ${i.detail}`)))) : null,
      msCards);
  }

  // --- 콜사인 표 · 콜사인 화면 (WBS-37.2) ------------------------------------------------

  const canApprove = (principal) => principal.kind === "callsign" && principal.role === "owner"
    && principal.callsign_kind === "human" && principal.human_approved;

  function guideChip(c, current) {
    if (c.guide_state === "current") return chip("지침 최신", "done");
    if (c.guide_state === "stale") return el("span", { class: "chip blocked", title: `받은 판 ${c.guide_version_seen} · 허브 ${current}` }, `옛 지침 ${c.guide_version_seen}`);
    return chip("지침 받은 적 없음", "planned");
  }

  function kindText(c) {
    if (c.kind !== "human") return "agent";
    return c.human_approved ? "human" : "human · 승인 전";
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
      el("a", { class: "mono", href: `${base}/t/${encodeURIComponent(t.id)}` }, t.id), " ", chip(t.status), " ",
      t.progress_note ? el("span", {}, t.progress_note) : el("span", { class: "muted" }, t.title))));
  }

  function callsignSection(pid, principal, cr) {
    if (cr.status !== 200) return el("section", { class: "card" }, el("h2", {}, "콜사인"), alertBox("bad", errorText(cr)));
    const base = `#/p/${encodeURIComponent(pid)}`;
    const { callsigns, guide_current: current } = cr.data;
    const rows = callsigns.map((c) => el("tr", { class: c.archived ? "archived" : "" },
      el("td", {}, el("a", { href: `${base}/c/${encodeURIComponent(c.id)}` }, c.id), c.archived ? " " : null, c.archived ? chip("보관", "planned") : null),
      el("td", {}, kindText(c), ` · ${c.role}`, c.kind === "human" && !c.human_approved && !c.archived && canApprove(principal) ? approveButton(pid, c) : null),
      el("td", {}, nowDoing(c, base)),
      el("td", { class: "muted nowrap" }, when(c.last_seen_at) || "활동 없음"),
      el("td", {}, guideChip(c, current)),
      el("td", { class: "muted mono" }, c.client_version_seen || "—")));
    return el("section", { class: "card" }, el("h2", {}, "콜사인 — 지금 누가 무엇을"),
      el("p", { class: "muted" }, "허브 지침 판 ", el("span", { class: "mono" }, current)),
      el("div", { class: "table-wrap" }, el("table", {}, el("thead", {}, el("tr", {}, ["콜사인", "종류", "지금 하는 일", "마지막 활동", "지침", "클라이언트"].map((h) => el("th", {}, h)))),
        el("tbody", {}, rows))));
  }

  const HANDOFF = [["baseline", "현재 기준선"], ["focus", "주 작업 축"], ["in_progress", "진행 중"], ["blocked", "막힘"],
    ["recent_done", "최근 완료"], ["next", "다음 시작 포인트"], ["risks", "남은 위험"]];

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
    }) : [el("p", { class: "muted" }, "아직 올린 handoff 가 없다.")];
    render(
      el("section", { class: "card" },
        el("h1", {}, c.id),
        el("div", { class: "row" }, kindText(c), `· ${c.role}`, c.label ? `· ${c.label}` : null, c.host ? `· ${c.host}` : null,
          c.archived ? chip("보관 (읽기 전용)", "planned") : null,
          c.kind === "human" && !c.human_approved && !c.archived && canApprove(principal) ? approveButton(pid, c) : null),
        el("div", { class: "row muted" }, "마지막 활동 ", when(c.last_seen_at) || "없음", "·", guideChip(c, current), "·",
          `클라이언트 ${c.client_version_seen || "—"}`, "·", c.setup_complete ? "셋업 끝" : "셋업 미완"),
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
        `${prop.proposed_by} · `, when(prop.proposed_at), ` · 기준 v${prop.base_version}`,
        prop.applied_version ? ` → v${prop.applied_version}` : null,
        prop.decided_by && prop.decided_by !== prop.proposed_by ? ` · 결정 ${prop.decided_by}` : null),
      prop.note ? el("div", {}, prop.note) : null,
      prop.stale ? alertBox("warn", "기준 판이 지금 판이 아니다 — 승인할 수 없다. 새 판 위에서 다시 제안해야 한다.") : null,
      el("details", { open: open || undefined }, el("summary", {}, "바뀐 줄"), el("pre", { class: "diff" }, prop.diff || "(차이 없음)")),
      open && canDecide ? el("div", { class: "row" },
        el("button", { type: "button", onclick: decide(true), disabled: prop.stale || undefined }, "승인"),
        el("button", { type: "button", class: "ghost", onclick: decide(false) }, "거절")) : null);
  }

  async function viewGuide(pid) {
    const { token } = await projectHead(pid, "지침");
    const r = await api(`projects/${encodeURIComponent(pid)}/guide`, { token });
    if (r.status !== 200) { render(el("section", { class: "card" }, alertBox("bad", errorText(r)))); return; }
    const g = r.data;
    const open = g.proposals.filter((x) => x.status === "open");
    let editor = el("p", { class: "muted" }, "고치려면 이 프로젝트의 콜사인 토큰이 이 브라우저에 있어야 한다.");
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
        el("p", { class: "muted" }, g.can_decide ? "승인된 사람 콜사인 — 고치면 바로 판이 오르고, 열린 제안을 승인 · 거절한다."
          : "에이전트 · 승인 전 사람 콜사인의 변경은 제안으로 남는다 (D11)."),
        el("details", {}, el("summary", {}, "지금 본문"), el("pre", {}, g.body || "(비었다 — 표준 규칙만 렌더된다)")),
        el("h2", {}, "고치기"), editor),
      el("section", { class: "card" }, el("h2", {}, "제안"),
        g.proposals.length ? g.proposals.map((x) => proposalCard(pid, x, g.can_decide)) : el("p", { class: "muted" }, "제안이 없다.")),
      el("section", { class: "card" }, el("h2", {}, "판 이력"),
        g.history.length ? el("div", { class: "table-wrap" }, el("table", {}, el("thead", {}, el("tr", {}, ["판", "누가", "언제", "크기"].map((h) => el("th", {}, h)))),
          el("tbody", {}, g.history.map((h) => el("tr", {}, el("td", { class: "mono" }, `v${h.version}`), el("td", {}, h.updated_by),
            el("td", { class: "muted nowrap" }, when(h.updated_at)), el("td", { class: "muted" }, `${h.size}자`))))))
          : el("p", { class: "muted" }, "아직 판이 없다 (v0 — 표준 규칙만).")));
  }

  const pageHref = (base, path) => `${base}/wp/${encodeURIComponent(path)}`;

  async function viewWiki(pid, query) {
    const { token, base } = await projectHead(pid, "위키");
    const q = (query || "").trim();
    const r = await api(`projects/${encodeURIComponent(pid)}/wiki${q ? `?q=${encodeURIComponent(q)}` : ""}`, { token });
    const input = el("input", { type: "search", placeholder: "낱말 (모두 들어간 페이지)", "aria-label": "위키 검색" });
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
      el("div", { class: "row" }, (r.data.generated || []).map((g) => el("a", { href: pageHref(base, g) }, g)), el("span", { class: "muted" }, "(생성물)")),
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

  async function viewDcrs(pid, id) {
    const { token, base } = await projectHead(pid, "결정 변경 기록");
    const r = await api(`projects/${encodeURIComponent(pid)}/dcr${id ? `/${encodeURIComponent(id)}` : ""}`, { token });
    const body = r.status !== 200 ? alertBox("bad", errorText(r)) : id
      ? el("div", {}, el("p", { class: "muted" }, `${r.data.status} · v${r.data.version} · ${r.data.author}`),
        el("h2", {}, "근거"), el("pre", { class: "wiki" }, r.data.rationale), el("h2", {}, "제안"), el("pre", { class: "wiki" }, r.data.proposal_md),
        el("h2", {}, "감사 기록"), el("ul", {}, r.data.timeline.map((e) => el("li", {}, `${e.at} · ${e.actor} · ${e.op}`))),
        r.data.adr_path ? el("p", { class: "mono" }, `ADR: ${r.data.adr_path}`) : null)
      : r.data.dcrs.length ? el("ul", { class: "hits" }, r.data.dcrs.map((d) => el("li", {}, el("a", { href: `${base}/dcr/${encodeURIComponent(d.id)}` }, d.title), ` · ${d.status} · ${d.author}`)))
        : el("p", { class: "muted" }, "등록된 DCR이 없다.");
    render(el("section", { class: "card" }, el("h1", {}, id ? `DCR ${id}` : "결정 변경 기록"), projectNav(pid, "dcr"), body));
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
      el("div", { class: "row" }, el("h1", { class: "mono" }, pg.path), pg.generated ? chip("생성물", "planned") : chip(`v${pg.version}`, "planned")),
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
            type: "radio", name: `dec_${d.id}`, value: v, checked: v === d.default || undefined,
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
            el("label", { class: "muted" }, openedBox, "기본값/선택지를 확인했다 (선택 변경 시 자동 체크)")));
        det.addEventListener("toggle", () => { if (det.open) { openedBox.checked = true; dirty = true; } });
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
          : el("div", { class: "claim-body muted" }, "이 주장에 걸린 결정 없음"));
    });
    if (orphanDecisions.length) {
      treeNodes.push(el("details", { class: "claim", open: true },
        el("summary", {}, "연결 주장이 없는 결정"),
        el("div", { class: "claim-body" }, orphanDecisions.map(decisionBlock))));
    }

    let statusNotice;
    if (!openIds.size) statusNotice = el("p", { class: "muted" }, "열린 결정이 없다.");
    else if (plan.has_errors) statusNotice = alertBox("warn", "계획이 오류 규칙을 어긴 상태라 응답을 받을 수 없다 — 작업 세션이 계획을 고친다.");
    else if (!principal.can_answer) statusNotice = alertBox("warn", principal.kind === "callsign"
      ? "결정에는 승인된 human 콜사인만 답한다 — 이 콜사인은 아니다."
      : "결정에 답하려면 이 프로젝트의 승인된 human 콜사인 토큰이 이 브라우저에 있어야 한다.");

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
      el("td", { class: "mono muted" }, String(e.seq)),
      el("td", { class: "muted nowrap" }, when(e.at)),
      el("td", {}, e.callsign || "—"),
      withTarget ? el("td", { class: "mono" }, `${e.target_kind} ${e.target_id}`) : null,
      el("td", {}, e.op),
      el("td", { class: "muted" }, e.via),
      el("td", {}, (e.before !== null || e.after !== null)
        ? el("details", {}, el("summary", {}, "값"), el("pre", {}, JSON.stringify({ before: e.before, after: e.after }, null, 1)))
        : "")));
  }
  const eventHead = (withTarget) => el("thead", {}, el("tr", {},
    ["#", "시각", "콜사인", withTarget ? "대상" : null, "무엇", "경로", ""].filter((h) => h !== null).map((h) => el("th", {}, h))));

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
        el("div", { class: "row" }, el("span", { class: "mono muted" }, task.id), chip(task.status), chip(task.priority, "planned"),
          `맡은 이 ${task.assignee || "—"}`, task.wbs ? el("span", { class: "mono" }, task.wbs) : null, `v${task.version}`),
        task.progress_note ? el("p", {}, el("strong", {}, "지금 하는 일 "), task.progress_note, el("span", { class: "muted" }, ` (${task.progress_at || ""})`)) : null,
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

  async function viewEvents(pid) {
    const token = storedToken(pid);
    const [pr, r] = await Promise.all([
      api(`projects/${encodeURIComponent(pid)}`, { token }),
      api(`projects/${encodeURIComponent(pid)}/events?limit=500`, { token })]);
    const base = `#/p/${encodeURIComponent(pid)}`;
    setCrumbs([{ text: "프로젝트", href: "#/" }, { text: pr.status === 200 ? pr.data.project.display_name : pid, href: base }, { text: "이력" }]);
    if (r.status !== 200) { render(el("section", { class: "card" }, alertBox("bad", errorText(r)))); return; }
    setWho(pr.status === 200 ? pr.data.principal : null);
    render(el("section", { class: "card" }, el("h1", {}, "이력"), projectNav(pid, "events"),
      el("div", { class: "table-wrap" }, el("table", {}, eventHead(true), el("tbody", {}, eventRows(r.data.events, true))))));
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
      render(el("section", { class: "card" }, alertBox("bad", "허브에 닿지 않는다: " + e)));
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
