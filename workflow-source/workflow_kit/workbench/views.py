"""HTML 렌더 (워크벤치 스펙 §4.3 · §4.4 · §7.2).

글은 전부 :func:`esc` 를 거쳐 들어간다 — task 파일의 글도 데이터다 (스펙 §1-3). 인라인 스크립트 · 스타일은
없다 (CSP). 링크와 폼 action 은 전부 ``rel`` (현재 경로의 깊이로 만든 상대 접두) 위의 상대 경로다.
"""

from __future__ import annotations

import hashlib
import html
from collections.abc import Iterable, Sequence
from typing import Any

from workflow_kit.common import plan_claims
from workflow_kit.workbench.state_view import PlanView

UNMEASURED = "미측정"


def static_version(name: str) -> str:
    """정적 파일의 내용 지문 — 링크에 `?v=` 로 붙여 바뀐 CSS · JS 를 브라우저 캐시(max-age=3600)가 가리지 않게 한다
    (TASK-2026-11-16-main-013). 요청마다 읽는다 — 서버를 다시 띄우지 않고 파일만 바뀌어도 따라간다."""
    from importlib import resources

    try:
        data = resources.files("workflow_kit.workbench").joinpath("static").joinpath(name).read_bytes()
    except OSError:
        return "0"
    return hashlib.sha256(data).hexdigest()[:10]


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def relative_base(path: str) -> str:
    """현재 요청 경로에서 루트로 가는 상대 접두 — ``/`` → ``./``, ``/task/X`` → ``../`` (스펙 §4.3)."""
    depth = max(path.count("/") - 1, 0)
    return "../" * depth if depth else "./"


def _status_class(value: object) -> str:
    """상태 글자 → 배지 색 클래스. 모르는 값은 중립."""
    text = str(value or "").split(":", 1)[0]
    return {
        "done": "ok", "kept": "ok", "answered": "ok", "changed": "ok",
        "in_progress": "info", "active": "info",
        "blocked": "bad", "error": "bad",
        "planned": "muted", "proposed": "warn", "open": "warn",
    }.get(text, "muted")


def badge(value: object, *, kind: str | None = None) -> str:
    return f'<span class="badge {kind or _status_class(value)}">{esc(value)}</span>'


def page(*, title: str, rel: str, branch: str | None, body: str, script: bool = False,
         user: str | None = None, csrf: str | None = None, logout: bool = True, refresh: int = 0,
         repo: str | None = None) -> str:
    # 한 호스트에 워크벤치가 여럿이면 탭 제목으로 가른다 — `<저장소> · <브랜치> — <화면>` (스펙 §3.2)
    label = " · ".join(part for part in (repo, branch) if part)
    if label:
        title = f"{label} — {title}"
    head = [
        "<!doctype html>", '<html lang="ko">', "<head>", '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        f"<title>{esc(title)}</title>", f'<link rel="stylesheet" href="{esc(rel)}static/workbench.css?v={static_version("workbench.css")}">',
    ]
    if script or refresh:
        head.append(f'<script src="{esc(rel)}static/workbench.js?v={static_version("workbench.js")}" defer></script>')
    # 자동 새로고침 (스펙 §4.5) — 스크립트가 같은 주소를 다시 받아 main 의 지문이 바뀌었을 때만 갈아 끼운다.
    body_tag = f'<body data-refresh="{int(refresh)}">' if refresh > 0 else "<body>"
    # 지문은 세션마다 다른 CSRF 값을 빼고 잰다 — todo 폼이 main 안에 CSRF 를 싣는다 (TASK-2026-11-16-main-017).
    fingerprint = body.replace(csrf, "") if csrf else body
    version = hashlib.sha256(fingerprint.encode("utf-8")).hexdigest()[:16]
    head.extend(["</head>", body_tag, '<header class="top"><div class="bar">',
                 f'<a class="brand" href="{esc(rel)}"><span class="logo">◆</span> 워크벤치</a>'])
    if repo is not None:
        head.append(f'<span class="branch repo">저장소 {esc(repo)}</span>')
    if branch is not None:
        head.append(f'<span class="branch">브랜치 {esc(branch)}</span>')
    if user is not None and not logout:  # 개방 모드 — 로그인이 없으니 로그아웃도 없다 (스펙 §5.6)
        head.append(f'<span class="logout who">{esc(user)} · 인증 없음</span>')
    elif user is not None and csrf is not None:
        head.append(
            f'<form method="post" action="{esc(rel)}logout" class="logout">'
            f'<input type="hidden" name="csrf" value="{esc(csrf)}">'
            f'<span class="who">{esc(user)}</span> <button type="submit" class="ghost">로그아웃</button></form>')
    head.extend(["</div></header>", f'<main data-version="{version}">', body, "</main>", "</body>", "</html>"])
    return "\n".join(head) + "\n"


def login_page(*, rel: str, error: str | None = None) -> str:
    body = ['<section class="card narrow"><h1>로그인</h1>']
    if error:
        body.append(f'<p class="alert error">{esc(error)}</p>')
    body.append(
        f'<form method="post" action="{esc(rel)}login" class="stack">'
        '<label>토큰 <input type="password" name="token" autocomplete="current-password" required></label> '
        '<button type="submit">로그인</button></form></section>')
    return page(title="워크벤치 로그인", rel=rel, branch=None, body="\n".join(body))


def message_page(*, rel: str, branch: str | None, title: str, message: str, back: str | None = None,
                 repo: str | None = None) -> str:
    body = [f'<section class="card narrow"><h1>{esc(title)}</h1>', f'<p class="alert error">{esc(message)}</p>']
    if back is not None:
        body.append(f'<p><a href="{esc(back)}">돌아가기</a></p>')
    body.append("</section>")
    return page(title=title, rel=rel, branch=branch, body="\n".join(body), repo=repo)


def _progress(done: int | None, total: int) -> str:
    if not total or done is None:
        return f'<span class="unmeasured">{UNMEASURED}</span>'
    return (f'<div class="meter"><progress value="{esc(done)}" max="{esc(total)}"></progress>'
            f'<span class="count">완료 잎 {esc(done)} / 전체 {esc(total)}</span></div>')


def _status(declared: Any, derived: Any) -> str:
    if declared == derived:
        return badge(declared if declared is not None else UNMEASURED)
    return f'<span class="badge warn">선언 {esc(declared)} · 파생 {esc(derived)}</span>'


def _count(items: Sequence[Any] | None) -> str:
    return UNMEASURED if items is None else str(len(items))


def _now(progress: dict[str, Any] | None) -> str:
    """'지금 하는 일' 한 줄 — task 파일의 Progress (TASK-2026-11-16-main-009)."""
    if not progress or not progress.get("text"):
        return ""
    at = progress.get("at")
    stamp = f'<time>{esc(str(at)[5:])}</time> ' if at else ""
    return (f'<span class="now clamp-3" title="{esc(progress["text"])}"><b>지금</b> {stamp}'
            f'{esc(progress["text"])}</span>')


def _todo_chip(counts: dict[str, Any], task_id: str) -> str:
    pair = counts.get(task_id)
    if not pair:
        return ""
    done, total = pair
    kind = "ok" if done == total else "info"
    return f'<span class="chip {kind} todo-count">todo {esc(done)}/{esc(total)}</span>'


def _todo_form(rel: str, csrf: str, back: str, action: str, fields: dict[str, str], inner: str, cls: str) -> str:
    hidden = "".join(f'<input type="hidden" name="{esc(k)}" value="{esc(v)}">'
                     for k, v in {"csrf": csrf, "action": action, "back": back, **fields}.items())
    return f'<form method="post" action="{esc(rel)}todo" class="{cls}">{hidden}{inner}</form>'


def todo_block(*, items: Sequence[dict[str, Any]] | None, error: str | None, scope: str, rel: str, csrf: str,
               back: str, can_edit: bool, empty: str) -> str:
    """todo 목록 (스펙 §13.1) — 항목마다 끝냄 단추 · 글 · 고치기(글 · 삭제), 끝에 추가 폼. viewer 는 읽기만."""
    if items is None:
        return f'<p class="alert warn">todo 를 읽지 못했다: {esc(error or UNMEASURED)}</p>'
    done = sum(1 for item in items if item["done"])
    rows: list[str] = []
    for item in items:
        mark = "☑" if item["done"] else "☐"
        label = "끝냄 되돌리기" if item["done"] else "끝냄으로 표시"
        if can_edit:
            check = _todo_form(rel, csrf, back, "undo" if item["done"] else "done", {"id": item["id"]},
                               f'<button type="submit" class="check" title="{label}" aria-label="{label}">{mark}</button>',
                               "todo-toggle")
            more = ('<details class="todo-more"><summary>고치기</summary><div class="todo-more-body">'
                    + _todo_form(rel, csrf, back, "edit", {"id": item["id"]},
                                 f'<input type="text" name="text" value="{esc(item["text"])}" maxlength="300" required '
                                 'aria-label="고칠 글"><button type="submit">저장</button>', "todo-edit")
                    + _todo_form(rel, csrf, back, "remove", {"id": item["id"]},
                                 '<button type="submit" class="ghost danger">삭제</button>', "todo-remove")
                    + "</div></details>")
        else:
            check, more = f'<span class="check" aria-label="{label}">{mark}</span>', ""
        rows.append(f'<li class="todo-item{" done" if item["done"] else ""}" data-todo="{esc(item["id"])}">{check}'
                    f'<span class="todo-text clamp-3" title="{esc(item["text"])}">{esc(item["text"])}</span>{more}</li>')
    parts = [f'<p class="todo-summary">{done} / {len(items)} 끝냄</p>' if items else f'<p class="empty">{esc(empty)}</p>']
    if rows:
        parts.append('<ul class="todo-list">' + "".join(rows) + "</ul>")
    if can_edit:
        parts.append(_todo_form(rel, csrf, back, "add", {"scope": scope},
                                '<input type="text" name="text" maxlength="300" required placeholder="할 일 추가" '
                                'aria-label="새 할 일"><button type="submit">추가</button>', "todo-add"))
    return "".join(parts)


def _task_list(items: Sequence[dict[str, Any]] | None, rel: str, linked: set[str],
               counts: dict[str, Any] | None = None) -> str:
    if items is None:
        return f'<p class="unmeasured empty">{UNMEASURED}</p>'
    if not items:
        return '<p class="empty">없음</p>'
    rows = []
    for item in items:
        label = esc(item["id"])
        if item["id"] in linked:
            label = f'<a href="{esc(rel)}task/{esc(item["id"])}">{label}</a>'
        rows.append(f'<li class="item"><span class="tid">{label}</span>'
                    f'<span class="ttl clamp-3" title="{esc(item["title"])}">{esc(item["title"])}</span>'
                    f'{_now(item.get("progress"))}{_todo_chip(counts or {}, item["id"])}</li>')
    return '<ul class="items">' + "".join(rows) + "</ul>"


def _kpi(label: str, value: str, kind: str) -> str:
    cls = "unmeasured" if value == UNMEASURED else ""
    return f'<div class="kpi {kind}"><span class="kpi-label">{esc(label)}</span><span class="kpi-value {cls}">{esc(value)}</span></div>'


def progress_page(*, state: dict[str, Any], rel: str, user: str, csrf: str, logout: bool = True,
                  refresh: int = 0, role: str = "approver", repo: str | None = None) -> str:
    tasks = state["tasks"]
    plans = state["plans"]
    inbox = state["inbox"]
    open_total = sum(len(p["open_decisions"]) for p in plans)
    pending_total = sum(int(n) for n in (inbox.get("pending") or {}).values())
    body: list[str] = ['<div class="page-head"><h1>진척</h1>']
    generated = state["generated_at"]
    if state.get("source") == "live":
        # 지문(data-version)이 매 계산마다 바뀌지 않게 시각은 싣지 않는다 — 원천이 바뀔 때만 화면이 바뀐다.
        body.append('<p class="generated"><span class="chip ok">실시간</span> 원천(task · handoff · roadmap)에서 '
                    'refresh-state 와 같은 생성기로 계산</p></div>')
    else:
        body.append(
            f'<p class="generated">roadmap 생성 {esc(generated["roadmap"] or UNMEASURED)} · '
            f'state 생성 {esc(generated["state"] or UNMEASURED)}</p></div>')
    body.append('<section class="kpis">'
                + _kpi("진행 중", _count(tasks["in_progress"]), "info")
                + _kpi("차단", _count(tasks["blocked"]), "bad")
                + _kpi("계획", _count(tasks["planned"]), "muted")
                + _kpi("열린 결정", str(open_total), "warn" if open_total else "ok")
                + _kpi("미반영 응답", str(pending_total), "warn" if pending_total else "ok")
                + "</section>")
    if state.get("live_error"):
        body.append(f'<p class="alert warn">실시간 계산 실패 — 생성물을 보인다: {esc(state["live_error"])}</p>')
    if inbox["layout_problem"]:
        body.append(f'<p class="alert error">계획 응답 배치: {esc(inbox["layout_problem"])}</p>')
    if inbox["unknown"]:
        body.append(f'<p class="alert warn">받은편지함에 알 수 없는 항목 {len(inbox["unknown"])}건: '
                    + esc(", ".join(inbox["unknown"])) + "</p>")
    todo = state.get("todo") or {"branch": [], "counts": {}, "error": None}
    counts = todo.get("counts") or {}
    linked = {entry["task"] for entry in plans} | {scope for scope in counts if scope != "Branch"}
    body.append('<section class="section todo-section"><h2>할 일</h2><div class="card todo-card">'
                + todo_block(items=todo.get("branch"), error=todo.get("error"), scope="Branch", rel=rel, csrf=csrf,
                             back="", can_edit=role == "approver", empty="브랜치 할 일이 없다")
                + "</div></section>")
    body.append('<section class="section"><h2>계획</h2>')
    if plans:
        cards = []
        for p in plans:
            opened = len(p["open_decisions"])
            flags = []
            if opened:
                flags.append(f'<span class="chip warn">열린 결정 {opened}</span>')
            if p["pending_responses"]:
                flags.append(f'<span class="chip info">미반영 응답 {esc(p["pending_responses"])}</span>')
            chips = ("".join(flags) or '<span class="chip ok">결정 대기 없음</span>') + _todo_chip(counts, p["task"])
            attention = " attention" if opened else ""
            cards.append(
                f'<a class="card plan-card{attention}" href="{esc(rel)}task/{esc(p["task"])}">'
                f'<span class="card-top"><span class="tid">{esc(p["task"])}</span>{badge(p["status"])}</span>'
                f'<span class="card-title clamp-3" title="{esc(p["title"])}">{esc(p["title"])}</span>'
                f'{_now(p.get("progress"))}'
                f'<span class="chips">{chips}</span></a>')
        body.append('<div class="grid">' + "".join(cards) + "</div>")
    else:
        body.append('<p class="empty">계획이 있는 진행 중 task 가 없다</p>')
    body.append("</section>")
    columns = []
    for key, label, kind in (("in_progress", "진행 중", "info"), ("blocked", "차단", "bad"),
                             ("planned", "계획", "muted"), ("recent_done", "최근 완료", "ok")):
        columns.append(
            f'<div class="column {kind}"><h2><span>{label}</span><span class="n">{esc(_count(tasks[key]))}</span></h2>'
            + _task_list(tasks[key], rel, linked, counts) + "</div>")
    body.append('<section class="section"><h2>작업 보드</h2><div class="board">'
                + "".join(columns) + "</div></section>")
    body.append('<section class="section"><h2>마일스톤</h2>')
    if state["milestones"]:
        active: list[str] = []
        finished: list[str] = []
        for m in state["milestones"]:
            issues = "".join(f"<li>{esc(note)}</li>" for note in m["issues"])
            card = (
                f'<div class="card milestone"><div class="card-top"><span class="tid">{esc(m["id"])}</span>'
                f'{_status(m["declared"], m["derived"])}</div>'
                f'<div class="card-title clamp-3" title="{esc(m["title"])}">{esc(m["title"])}</div>'
                f'{_progress(m["leaves_done"], m["leaves_total"])}'
                + (f'<ul class="issues">{issues}</ul>' if issues else "") + "</div>")
            # 선언 · 파생이 둘 다 done 이고 문제가 없는 것만 접는다 — 어긋남 · 문제는 늘 펼쳐 보인다.
            settled = m["declared"] == "done" and m["derived"] == "done" and not m["issues"]
            (finished if settled else active).append(card)
        if active:
            body.append('<div class="grid">' + "".join(active) + "</div>")
        else:
            body.append('<p class="empty">진행 중인 마일스톤이 없다</p>')
        if finished:
            body.append(f'<details class="fold"><summary>완료된 마일스톤 {len(finished)}개</summary>'
                        '<div class="grid">' + "".join(finished) + "</div></details>")
    else:
        missing = "roadmap 원천이 없다" if state.get("source") == "live" else "roadmap_state.json 이 없다"
        body.append(f'<p class="unmeasured empty">{UNMEASURED} — {missing}</p>')
    if state["issues"]:
        body.append('<ul class="issues">' + "".join(f"<li>{esc(note)}</li>" for note in state["issues"]) + "</ul>")
    body.append("</section>")
    return page(title="워크벤치 — 진척", rel=rel, branch=state["branch"], body="\n".join(body), repo=repo,
                user=user, csrf=csrf, logout=logout, refresh=refresh)


def _claim_tree(view: PlanView) -> Iterable[str]:
    claims = [c for c in view.task.plan.claims if c.valid_id]
    by_parent: dict[str | None, list[plan_claims.Claim]] = {}
    for claim in claims:
        by_parent.setdefault(claim.parent_id, []).append(claim)
    bundles = {b.claim.id: b for b in view.bundles}
    decisions_by_claim: dict[str, list[str]] = {}
    for dv in view.decisions:
        decisions_by_claim.setdefault(dv.decision.claim_id, []).append(dv.decision.id)

    def render(claim: plan_claims.Claim) -> str:
        opened = " open" if claim.depth <= 1 else ""
        parts = [f'<details class="claim depth-{claim.depth}"{opened}><summary><span class="cid">{esc(claim.id)}</span> '
                 f'<span class="ctext">{esc(claim.text)}</span></summary><div class="claim-body">']
        if claim.location is not None:
            loc = claim.location
            where = f"new: {loc.path}" if loc.new else f"{loc.path}:{loc.start}" + (f"-{loc.end}" if loc.end else "")
            parts.append(f'<p class="location">{esc(where)} · {esc(loc.symbol)}</p>')
        bundle = bundles.get(claim.id)
        if bundle is not None:
            if bundle.unmeasured:
                parts.append(f'<p class="unmeasured">완료 기준 없음 — {UNMEASURED}</p>')
            else:
                # 검증 줄이 없으면 완료 기준은 "미측정" 이다 (§7.2) — 판정을 추론하지 않는다.
                mark = "" if view.verification else f' <span class="unmeasured">— 검증 줄 없음 · {UNMEASURED}</span>'
                items = "".join(f"<li>{esc(view.task.criteria[n - 1])}{mark}</li>" for n in bundle.criteria)
                parts.append(f'<ul class="criteria">{items}</ul>')
        for decision_id in decisions_by_claim.get(claim.id, []):
            parts.append(f"<!--decision:{esc(decision_id)}-->")
        for child in by_parent.get(claim.id, []):
            parts.append(render(child))
        parts.append("</div></details>")
        return "".join(parts)

    for root in by_parent.get(None, []):
        yield render(root)


def _decision_block(view: PlanView, decision_id: str, *, can_answer: bool) -> str:
    dv = next(d for d in view.decisions if d.decision.id == decision_id)
    d = dv.decision
    # 결정은 닫힌 채 그린다 — 펼침이 곧 '열어 봄'(opened) 기록이다 (스펙 §6, workbench.js).
    kind = "open" if dv.open else "closed"
    parts = [f'<details class="decision {kind}" data-decision="{esc(d.id)}"><summary>'
             f'<span class="did">{esc(d.id)}</span> <span class="question">{esc(d.question)}</span> — '
             f'<span class="state badge {_status_class(dv.state)}">{esc(dv.state)}</span></summary>'
             '<div class="decision-body">']
    if d.state != dv.state:
        parts.append(f'<p class="alert warn">task 파일의 칸은 {esc(d.state)}</p>')
    if d.answered or not can_answer:
        chosen = d.state_value if d.answered else None
        items = "".join(
            f'<li class="option{" chosen" if value == chosen else ""}"><span class="opt-value">{esc(value)}</span> — '
            f'<span class="opt-text">{esc(text)}</span>' + (' <span class="rec">(추천)</span>' if value == d.default else "")
            + (' <span class="answer">← 답</span>' if value == chosen else "") + "</li>"
            for value, text in d.options)
        parts.append(f'<ul class="options readonly">{items}</ul>')
    else:
        parts.append(f'<input type="hidden" name="opened_{esc(d.id)}" id="opened_{esc(d.id)}" value="no">')
        parts.append('<div class="options">')
        for value, text in d.options:
            checked = " checked" if value == d.default else ""
            parts.append(
                f'<label class="option"><input type="radio" name="value_{esc(d.id)}" value="{esc(value)}"{checked}> '
                f'<span class="opt-value">{esc(value)}</span> — <span class="opt-text">{esc(text)}</span>'
                + (' <span class="rec">(추천)</span>' if value == d.default else "") + "</label>")
        parts.append("</div>")
        parts.append(f'<label class="comment">주석 <textarea name="comment_{esc(d.id)}" rows="2"></textarea></label>')
    parts.append("</div></details>")
    return "".join(parts)


def plan_page(*, view: PlanView, rel: str, branch: str, user: str, csrf: str, role: str,
              flash: str | None = None, error: str | None = None, logout: bool = True, refresh: int = 0,
              repo: str | None = None) -> str:
    task = view.task
    can_answer = role == "approver" and bool(view.decisions) and not view.has_errors
    open_count = sum(1 for d in view.decisions if d.open)
    chips = [f'<span class="chip {_status_class(task.status)}">상태 {esc(task.status)}</span>',
             f'<span class="chip {"warn" if open_count else "ok"}">열린 결정 {open_count}건</span>',
             f'<span class="chip {"info" if view.pending else "ok"}">미반영 응답 {view.pending}건</span>']
    body: list[str] = [
        f'<p class="crumbs"><a href="{esc(rel)}">← 진척</a></p>',
        f'<section class="card head-card"><h1>{esc(task.task_id)}</h1><p class="lead">{esc(view.title)}</p>'
        f'<p class="summary chips">{"".join(chips)}</p></section>']
    if view.layout_problem:
        body.append(f'<p class="alert error">계획 응답 배치: {esc(view.layout_problem)}</p>')
    if view.responses:
        # 보낸 응답이 작업 세션에 반영됐는지 — hook 이 반영하면 자동 새로고침으로 '반영됨' 이 된다 (TASK-2026-11-16-main-014).
        items = "".join(
            f'<li class="resp"><span class="chip {"ok" if r["state"] == "반영됨" else "info"}">{esc(r["state"])}</span> '
            f'<span>{esc(r["responder"])}</span> <time>{esc(r["received_at"][:16].replace("T", " "))}</time></li>'
            for r in view.responses[:10])
        body.append(f'<section class="card responses"><h2>응답</h2><ul class="resp-list">{items}</ul></section>')
    if view.has_errors:
        body.append('<p class="alert error">task 파일의 주장 · 결정이 오류 규칙(L2 · L6 · L9)을 어겼다 — 응답을 받지 않는다</p>')
    if flash:
        body.append(f'<p class="alert flash">{esc(flash)}</p>')
    if error:
        body.append(f'<p class="alert error">{esc(error)}</p>')
    body.append('<section class="section todo-section"><h2>체크리스트</h2><div class="card todo-card">'
                + todo_block(items=view.todos, error=view.todo_error, scope=task.task_id, rel=rel, csrf=csrf,
                             back=f"task/{task.task_id}", can_edit=role == "approver", empty="체크리스트가 없다")
                + "</div></section>")
    if task.plan.claims:
        tree = "\n".join(_claim_tree(view))
        placed: set[str] = set()
        for dv in view.decisions:
            marker = f"<!--decision:{esc(dv.decision.id)}-->"
            if marker in tree:
                tree = tree.replace(marker, _decision_block(view, dv.decision.id, can_answer=can_answer))
                placed.add(dv.decision.id)
        loose = [_decision_block(view, dv.decision.id, can_answer=can_answer)
                 for dv in view.decisions if dv.decision.id not in placed]
        content = '<section class="section"><h2>주장 · 결정</h2><div class="tree">' + tree + "".join(loose) + "</div></section>"
        if view.verification:
            content += ('<section class="section"><h2>검증</h2><ul class="card list">'
                        + "".join(f"<li>{esc(v)}</li>" for v in view.verification) + "</ul></section>")
        if can_answer:
            content = (
                f'<form method="post" action="{esc(rel)}task/{esc(task.task_id)}/respond" class="respond">'
                f'<input type="hidden" name="csrf" value="{esc(csrf)}">'
                f'<input type="hidden" name="plan_digest" value="{esc(view.digest)}">'
                + content
                + '<section class="section"><label class="comment">계획 전체 주석 '
                '<textarea name="comment_-" rows="3"></textarea></label></section>'
                '<div class="submitbar"><span class="hint">펼쳐 본 결정만 &#39;열어 봄&#39; 으로 기록된다</span>'
                '<button type="submit">응답 보내기</button></div></form>')
        body.append(content)
    else:
        rows = "".join(f"<div><dt>{esc(label)}</dt><dd>{esc(value)}</dd></div>" for label, value in view.plain_fields)
        body.append(f'<section class="card"><dl class="fields">{rows}</dl></section>')
    if view.out_of_scope:
        body.append('<section class="section"><h2>Out of scope</h2><ul class="card list">'
                    + "".join(f"<li>{esc(v)}</li>" for v in view.out_of_scope) + "</ul></section>")
    return page(title=f"워크벤치 — {task.task_id}", rel=rel, branch=branch, body="\n".join(body), script=can_answer, repo=repo,
                user=user, csrf=csrf, logout=logout, refresh=refresh)
