// 허브 화면 (hub_spec §4.6 · §4.7). 로그인 없음 — 콜사인 토큰을 이 브라우저 저장소에 두고 Bearer 로 싣는다.
// 모든 링크 · API 호출은 상대 경로 (R13.4). DOM 은 textContent 로만 만든다 (서버 문자열을 HTML 로 해석하지 않는다).
"use strict";

(function () {
  const app = document.getElementById("app");
  const crumbs = document.getElementById("crumbs");
  const whoEl = document.getElementById("who");
  let hubHost = location.host;
  // 다음 화면 머리에 한 번 싣는 안내 — 화면을 다시 그려도 사라지지 않게 (등록 토큰 경고 등).
  let pendingFlash = null;

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

  async function api(path, opts) {
    opts = opts || {};
    const headers = { "accept": "application/json" };
    if (opts.token) headers["authorization"] = "Bearer " + opts.token;
    if (opts.body !== undefined) headers["content-type"] = "application/json";
    const res = await fetch("../api/" + path, {
      method: opts.method || "GET", headers, credentials: "omit",
      body: opts.body !== undefined ? JSON.stringify(opts.body) : undefined,
    });
    let data = null;
    try { data = await res.json(); } catch (e) { data = { error_code: "bad_response", message: "응답이 JSON 이 아니다" }; }
    return { status: res.status, data };
  }

  // --- DOM -----------------------------------------------------------------------

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
  // 허브 시각(UTC ISO) → 이 브라우저 시간대의 'YYYY-MM-DD HH:MM'. 원문은 title 로 남긴다.
  function when(iso) {
    if (!iso) return null;
    const d = new Date(iso);
    if (isNaN(d)) return el("span", {}, iso);
    const z = (n) => String(n).padStart(2, "0");
    return el("time", { datetime: iso, title: iso },
      `${d.getFullYear()}-${z(d.getMonth() + 1)}-${z(d.getDate())} ${z(d.getHours())}:${z(d.getMinutes())}`);
  }
  const chip = (text, cls) => el("span", { class: "chip " + (cls || text) }, text);
  const alertBox = (kind, text) => el("div", { class: "alert " + kind, role: kind === "bad" ? "alert" : "status" }, text);
  function render(...nodes) {
    const flash = pendingFlash;
    pendingFlash = null;
    app.replaceChildren(...(flash ? [alertBox(flash.kind, flash.text)] : []), ...nodes);
  }
  function setCrumbs(items) {
    // replaceChildren 은 null 을 글자 "null" 로 넣는다 — 빈 칸은 걸러 낸다.
    crumbs.replaceChildren(...items.flatMap((it, i) => [i ? el("span", {}, "›") : null,
      it.href ? el("a", { href: it.href }, it.text) : el("span", {}, it.text)]).filter(Boolean));
  }
  function setWho(principal) {
    if (!principal) { whoEl.textContent = ""; return; }
    if (principal.kind === "callsign") {
      whoEl.textContent = `${principal.callsign} (${principal.callsign_kind}${principal.callsign_kind === "human" && !principal.human_approved ? " · 승인 전" : ""} · ${principal.role})`;
    } else {
      whoEl.textContent = `공용 ${principal.kind} 토큰 — 읽기 전용`;
    }
  }
  function errorText(r) {
    const d = r.data || {};
    let msg = `${r.status} ${d.error_code || ""} — ${d.message || ""}`;
    if (r.status === 401) msg += " · 이 브라우저의 토큰을 지운 뒤 다시 등록하거나 토큰을 넣는다.";
    return msg;
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
      onDone(r.data.principal.project_id);
    } }, el("label", {}, "토큰 넣기", input), el("button", { type: "submit" }, "이 브라우저에 두기"), msg);
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
        if (!saved) {
          // 저장소가 없으면 화면을 다시 그리지 않는다 — 토큰을 옮겨 적을 때까지 남겨 둔다.
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
      onDone();
    } }, "이 브라우저에서 콜사인 지우기");
  }

  // --- 화면: 프로젝트 목록 -------------------------------------------------------------

  async function viewProjects() {
    setCrumbs([{ text: "프로젝트" }]);
    const seen = new Map();
    let principal = null;
    const errors = [];
    const anon = await api("projects");
    if (anon.status === 200) { principal = anon.data.principal; anon.data.projects.forEach((p) => seen.set(p.id, p)); }
    for (const pid of storedProjects()) {
      const r = await api("projects", { token: storedToken(pid) });
      if (r.status === 200) r.data.projects.forEach((p) => seen.set(p.id, p));
      else errors.push(`${pid}: ${errorText(r)}`);
    }
    setWho(principal);
    const cards = [...seen.values()].map((p) => el("a", { class: "card", href: `#/p/${encodeURIComponent(p.id)}` },
      el("h2", {}, p.display_name),
      el("div", { class: "mono muted" }, p.id),
      el("div", { class: "row" }, ...["in_progress", "blocked", "planned", "done"].map((s) => chip(`${s} ${p.task_counts[s] || 0}`, s))),
      storedToken(p.id) ? el("div", { class: "muted" }, "이 브라우저에 콜사인 토큰 있음") : null));
    render(
      el("section", { class: "card" }, el("h1", {}, "프로젝트"),
        cards.length ? el("div", { class: "grid" }, cards)
          : el("p", { class: "muted" }, anon.status === 401
            ? "토큰 없는 화면 읽기가 꺼져 있다 (허브 기본). 콜사인 토큰을 넣으면 그 프로젝트가 보인다."
            : "등록된 프로젝트가 없다.")),
      errors.length ? el("section", { class: "card" }, errors.map((e) => alertBox("bad", e))) : null,
      el("section", { class: "card" }, el("h2", {}, "이 브라우저에 콜사인 토큰 넣기"), tokenForm(() => route())));
  }

  // --- 화면: 프로젝트 · task 목록 ------------------------------------------------------

  const STATUSES = ["", "in_progress", "blocked", "planned", "done"];

  async function viewProject(pid, status) {
    const token = storedToken(pid);
    const pr = await api(`projects/${encodeURIComponent(pid)}`, { token });
    if (pr.status !== 200) {
      setCrumbs([{ text: "프로젝트", href: "#/" }, { text: pid }]);
      render(el("section", { class: "card" }, alertBox("bad", errorText(pr)),
        token ? forgetButton(pid, route) : null, el("h2", {}, "토큰 넣기"), tokenForm(() => route())));
      return;
    }
    const { project, principal } = pr.data;
    setWho(principal);
    setCrumbs([{ text: "프로젝트", href: "#/" }, { text: project.display_name }]);
    const q = status ? `?status=${encodeURIComponent(status)}` : "";
    const [tr, cr] = await Promise.all([
      api(`projects/${encodeURIComponent(pid)}/tasks${q}`, { token }),
      api(`projects/${encodeURIComponent(pid)}/callsigns`, { token })]);
    const base = `#/p/${encodeURIComponent(pid)}`;
    const filters = el("nav", { class: "filters", "aria-label": "상태" }, STATUSES.map((s) =>
      el("a", { href: s ? `${base}/s/${s}` : base, class: s === (status || "") ? "on" : "" }, s || "전체")));
    const rows = tr.status === 200 ? tr.data.tasks.slice().reverse().map((t) => el("tr", {},
      el("td", { class: "mono" }, el("a", { href: `${base}/t/${encodeURIComponent(t.id)}` }, t.id)),
      el("td", {}, t.title),
      el("td", {}, chip(t.status)),
      el("td", {}, t.assignee || "—"),
      el("td", { class: "muted" }, t.progress_note ? `${t.progress_note}` : ""),
      el("td", { class: "muted nowrap" }, when(t.updated_at)))) : [];
    render(
      el("section", { class: "card" },
        el("h1", {}, project.display_name),
        el("div", { class: "row muted" }, el("span", { class: "mono" }, project.id), `소유자 ${project.owner_callsign}`,
          el("a", { href: `${base}/events` }, "이력")),
        principal.kind === "callsign"
          ? el("div", { class: "row" }, forgetButton(pid, route))
          : el("div", {}, el("h2", {}, "이 브라우저의 콜사인"), registerForm(pid, route), tokenForm(() => route()))),
      callsignSection(pid, principal, cr),
      el("section", { class: "card" }, el("h2", {}, "task"), filters,
        tr.status !== 200 ? alertBox("bad", errorText(tr))
          : rows.length ? el("table", {}, el("thead", {}, el("tr", {}, ["ID", "제목", "상태", "맡은 이", "지금 하는 일", "고친 때"].map((h) => el("th", {}, h)))), el("tbody", {}, rows))
          : el("p", { class: "muted" }, "task 가 없다.")));
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
      el("table", {}, el("thead", {}, el("tr", {}, ["콜사인", "종류", "지금 하는 일", "마지막 활동", "지침", "클라이언트"].map((h) => el("th", {}, h)))),
        el("tbody", {}, rows)));
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

  // --- 화면: task 상세 · 결정 답 ------------------------------------------------------

  function decisionState(d, open) {
    if (open) return chip("열림", "open");
    return chip(d.state, d.state.startsWith("answered") || d.state.startsWith("changed") ? "answered" : "planned");
  }

  function answerForm(pid, tid, plan, onDone) {
    const openIds = new Set(plan.open_decisions);
    const inputs = {};
    const blocks = plan.decisions.filter((d) => openIds.has(d.id)).map((d) => {
      const select = el("select", { "aria-label": `${d.id} 값` }, d.options.map(([v, label]) =>
        el("option", { value: v, selected: v === d.default }, `${v} — ${label}`)));
      const opened = el("input", { type: "checkbox", "aria-label": `${d.id} 열어 봄` });
      inputs[d.id] = { select, opened };
      return el("div", { class: "decision" }, el("strong", {}, `${d.id} [${d.claim_id}] ${d.question}`),
        el("div", { class: "row" }, select, el("label", {}, opened, "기본값을 열어 보고 골랐다")));
    });
    const comment = el("textarea", { placeholder: "주석 (선택)", "aria-label": "주석" });
    const msg = el("div");
    const button = el("button", { type: "submit" }, "응답 보내기");
    return el("form", { onsubmit: async (ev) => {
      ev.preventDefault();
      button.disabled = true;
      const values = {}, opened = {};
      for (const [id, inp] of Object.entries(inputs)) { values[id] = inp.select.value; opened[id] = inp.opened.checked; }
      const r = await api(`projects/${encodeURIComponent(pid)}/tasks/${encodeURIComponent(tid)}/responses`, {
        method: "POST", token: storedToken(pid),
        body: { plan_digest: plan.digest, values, opened, comments: comment.value.trim() ? { "-": comment.value } : {} } });
      button.disabled = false;
      if (r.status !== 200) { msg.replaceChildren(alertBox("bad", errorText(r))); return; }
      onDone(r.data.duplicate ? "같은 응답이 이미 있다 — 한 번만 반영된다." : "응답을 반영했다.");
    } }, blocks, comment, el("div", { class: "row" }, button), msg);
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
    const open = new Set(plan.open_decisions);
    const f = task.fields || {};
    const list = (xs) => (xs && xs.length ? el("ul", {}, xs.map((x) => el("li", {}, x))) : el("span", { class: "muted" }, "—"));
    let answer;
    if (!plan.open_decisions.length) answer = el("p", { class: "muted" }, "열린 결정이 없다.");
    else if (plan.has_errors) answer = alertBox("warn", "계획이 오류 규칙을 어긴 상태라 응답을 받을 수 없다 — 작업 세션이 계획을 고친다.");
    else if (principal.can_answer) answer = answerForm(pid, tid, plan, (m) => viewTask(pid, tid, m));
    else answer = alertBox("warn", principal.kind === "callsign"
      ? "결정에는 승인된 human 콜사인만 답한다 — 이 콜사인은 아니다."
      : "결정에 답하려면 이 프로젝트의 승인된 human 콜사인 토큰이 이 브라우저에 있어야 한다.");
    render(
      flash ? alertBox("ok", flash) : null,
      el("section", { class: "card" },
        el("h1", {}, task.title),
        el("div", { class: "row" }, el("span", { class: "mono muted" }, task.id), chip(task.status), chip(task.priority, "planned"),
          `맡은 이 ${task.assignee || "—"}`, task.wbs ? el("span", { class: "mono" }, task.wbs) : null, `v${task.version}`),
        task.progress_note ? el("p", {}, el("strong", {}, "지금 하는 일 "), task.progress_note, el("span", { class: "muted" }, ` (${task.progress_at || ""})`)) : null,
        task.description ? el("p", {}, task.description) : null,
        el("h2", {}, "완료 기준"), list(f.done_criteria),
        f.result ? el("div", {}, el("h2", {}, "결과"), el("p", {}, f.result)) : null,
        f.validation_result ? el("div", {}, el("h2", {}, "검증 결과"), el("p", {}, f.validation_result)) : null,
        task.commits && task.commits.length ? el("div", {}, el("h2", {}, "커밋"), list(task.commits.map((c) => `${c.sha} ${c.branch || ""} (${c.added_by})`))) : null),
      el("section", { class: "card" },
        el("h2", {}, "계획 · 결정"),
        plan.lint.filter((i) => i.severity === "error").map((i) => alertBox("bad", `${i.rule} ${i.ref} ${i.message}`)),
        plan.claims.length ? el("ul", {}, plan.claims.map((c) => el("li", {}, el("strong", {}, c.id + " "), c.text))) : null,
        plan.decisions.map((d) => el("div", { class: "decision" },
          el("div", { class: "row" }, el("strong", {}, `${d.id} [${d.claim_id}]`), decisionState(d, open.has(d.id))),
          el("div", {}, d.question),
          el("div", { class: "muted" }, `기본값 ${d.default} · 선택지 ${d.options.map((o) => o[0]).join(" · ")}`))),
        el("p", { class: "muted" }, `반영된 응답 ${plan.responses}건 · 계획 지문 `, el("span", { class: "mono" }, plan.digest.slice(0, 12))),
        answer,
        el("details", {}, el("summary", {}, "계획 원문"), el("pre", {}, task.plan_md || "(없음)"))),
      el("section", { class: "card" }, el("h2", {}, "이력"),
        events.length ? el("table", {}, eventHead(false), el("tbody", {}, eventRows(events, false))) : el("p", { class: "muted" }, "없음")));
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
    render(el("section", { class: "card" }, el("h1", {}, "이력"),
      el("table", {}, eventHead(true), el("tbody", {}, eventRows(r.data.events, true)))));
  }

  // --- 길 ------------------------------------------------------------------------

  async function route() {
    const parts = location.hash.replace(/^#\/?/, "").split("/").map(decodeURIComponent);
    try {
      if (parts[0] === "p" && parts[1]) {
        if (parts[2] === "t" && parts[3]) return await viewTask(parts[1], parts[3]);
        if (parts[2] === "events") return await viewEvents(parts[1]);
        if (parts[2] === "c" && parts[3]) return await viewCallsign(parts[1], parts[3]);
        return await viewProject(parts[1], parts[2] === "s" ? parts[3] : "");
      }
      return await viewProjects();
    } catch (e) {
      render(el("section", { class: "card" }, alertBox("bad", "허브에 닿지 않는다: " + e)));
    }
  }

  window.addEventListener("hashchange", route);
  fetch("../healthz", { credentials: "omit" }).then((r) => r.json()).then((h) => {
    try { if (h.public_url) hubHost = new URL(h.public_url).host; } catch (e) { /* 그대로 */ }
  }).catch(() => {}).finally(route);
})();
