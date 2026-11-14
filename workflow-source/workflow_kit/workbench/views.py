"""HTML 렌더 (워크벤치 스펙 §4.3 · §4.4 · §7.2).

글은 전부 :func:`esc` 를 거쳐 들어간다 — task 파일의 글도 데이터다 (스펙 §1-3). 인라인 스크립트 · 스타일은
없다 (CSP). 링크와 폼 action 은 전부 ``rel`` (현재 경로의 깊이로 만든 상대 접두) 위의 상대 경로다.
"""

from __future__ import annotations

import html
from collections.abc import Iterable, Sequence
from typing import Any

from workflow_kit.common import plan_claims
from workflow_kit.workbench.state_view import PlanView

UNMEASURED = "미측정"


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def relative_base(path: str) -> str:
    """현재 요청 경로에서 루트로 가는 상대 접두 — ``/`` → ``./``, ``/task/X`` → ``../`` (스펙 §4.3)."""
    depth = max(path.count("/") - 1, 0)
    return "../" * depth if depth else "./"


def page(*, title: str, rel: str, branch: str | None, body: str, script: bool = False,
         user: str | None = None, csrf: str | None = None) -> str:
    head = [
        "<!doctype html>", '<html lang="ko">', "<head>", '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        f"<title>{esc(title)}</title>", f'<link rel="stylesheet" href="{esc(rel)}static/workbench.css">',
    ]
    if script:
        head.append(f'<script src="{esc(rel)}static/workbench.js" defer></script>')
    head.extend(["</head>", "<body>", '<header class="top">', f'<a href="{esc(rel)}">워크벤치</a>'])
    if branch is not None:
        head.append(f'<span class="branch">브랜치 {esc(branch)}</span>')
    if user is not None and csrf is not None:
        head.append(
            f'<form method="post" action="{esc(rel)}logout" class="logout">'
            f'<input type="hidden" name="csrf" value="{esc(csrf)}">'
            f'<span>{esc(user)}</span> <button type="submit">로그아웃</button></form>')
    head.extend(["</header>", "<main>", body, "</main>", "</body>", "</html>"])
    return "\n".join(head) + "\n"


def login_page(*, rel: str, error: str | None = None) -> str:
    body = ["<h1>로그인</h1>"]
    if error:
        body.append(f'<p class="error">{esc(error)}</p>')
    body.append(
        f'<form method="post" action="{esc(rel)}login">'
        '<label>토큰 <input type="password" name="token" autocomplete="current-password" required></label> '
        '<button type="submit">로그인</button></form>')
    return page(title="워크벤치 로그인", rel=rel, branch=None, body="\n".join(body))


def message_page(*, rel: str, branch: str | None, title: str, message: str, back: str | None = None) -> str:
    body = [f"<h1>{esc(title)}</h1>", f'<p class="error">{esc(message)}</p>']
    if back is not None:
        body.append(f'<p><a href="{esc(back)}">돌아가기</a></p>')
    return page(title=title, rel=rel, branch=branch, body="\n".join(body))


def _progress(done: int | None, total: int) -> str:
    if not total or done is None:
        return f'<span class="unmeasured">{UNMEASURED}</span>'
    return (f'<span class="count">완료 잎 {esc(done)} / 전체 {esc(total)}</span> '
            f'<progress value="{esc(done)}" max="{esc(total)}"></progress>')


def _status(declared: Any, derived: Any) -> str:
    if declared == derived:
        return esc(declared if declared is not None else UNMEASURED)
    return f'선언 {esc(declared)} · 파생 {esc(derived)}'


def _task_list(items: Sequence[dict[str, str]] | None, rel: str, linked: set[str]) -> str:
    if items is None:
        return f'<p class="unmeasured">{UNMEASURED}</p>'
    if not items:
        return "<p>없음</p>"
    rows = []
    for item in items:
        label = esc(item["id"])
        if item["id"] in linked:
            label = f'<a href="{esc(rel)}task/{esc(item["id"])}">{label}</a>'
        rows.append(f"<li>{label} — {esc(item['title'])}</li>")
    return "<ul>" + "".join(rows) + "</ul>"


def progress_page(*, state: dict[str, Any], rel: str, user: str, csrf: str) -> str:
    body: list[str] = ["<h1>진척</h1>"]
    generated = state["generated_at"]
    body.append(
        f'<p class="generated">roadmap 생성 {esc(generated["roadmap"] or UNMEASURED)} · '
        f'state 생성 {esc(generated["state"] or UNMEASURED)}</p>')
    inbox = state["inbox"]
    if inbox["layout_problem"]:
        body.append(f'<p class="error">계획 응답 배치: {esc(inbox["layout_problem"])}</p>')
    if inbox["unknown"]:
        body.append(f'<p class="warn">받은편지함에 알 수 없는 항목 {len(inbox["unknown"])}건: '
                    + esc(", ".join(inbox["unknown"])) + "</p>")
    plans = state["plans"]
    linked = {entry["task"] for entry in plans}
    body.append("<h2>계획</h2>")
    if plans:
        rows = [
            f'<tr><td><a href="{esc(rel)}task/{esc(p["task"])}">{esc(p["task"])}</a></td>'
            f'<td>{esc(p["title"])}</td><td>{esc(p["status"])}</td>'
            f'<td>{esc(len(p["open_decisions"]))}</td><td>{esc(p["pending_responses"])}</td></tr>'
            for p in plans
        ]
        body.append('<table><thead><tr><th>task</th><th>제목</th><th>상태</th><th>열린 결정</th>'
                    '<th>미반영 응답</th></tr></thead><tbody>' + "".join(rows) + "</tbody></table>")
    else:
        body.append("<p>계획이 있는 진행 중 task 가 없다</p>")
    body.append("<h2>마일스톤</h2>")
    if state["milestones"]:
        rows = []
        for m in state["milestones"]:
            issues = "".join(f"<li>{esc(note)}</li>" for note in m["issues"])
            rows.append(
                f"<tr><td>{esc(m['id'])}</td><td>{esc(m['title'])}</td>"
                f"<td>{_status(m['declared'], m['derived'])}</td>"
                f"<td>{_progress(m['leaves_done'], m['leaves_total'])}</td>"
                f"<td>{'<ul>' + issues + '</ul>' if issues else ''}</td></tr>")
        body.append('<table><thead><tr><th>ID</th><th>제목</th><th>상태</th><th>진척</th><th>문제</th>'
                    '</tr></thead><tbody>' + "".join(rows) + "</tbody></table>")
    else:
        body.append(f'<p class="unmeasured">{UNMEASURED} — roadmap_state.json 이 없다</p>')
    if state["issues"]:
        body.append("<ul>" + "".join(f"<li>{esc(note)}</li>" for note in state["issues"]) + "</ul>")
    tasks = state["tasks"]
    for key, label in (("in_progress", "진행 중"), ("blocked", "차단"), ("planned", "계획"),
                       ("recent_done", "최근 완료")):
        body.append(f"<h2>{label}</h2>")
        body.append(_task_list(tasks[key], rel, linked))
    return page(title="워크벤치 — 진척", rel=rel, branch=state["branch"], body="\n".join(body),
                user=user, csrf=csrf)


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
        parts = [f'<details class="claim depth-{claim.depth}"><summary>{esc(claim.id)} {esc(claim.text)}</summary>']
        if claim.location is not None:
            loc = claim.location
            where = f"new: {loc.path}" if loc.new else f"{loc.path}:{loc.start}" + (f"-{loc.end}" if loc.end else "")
            parts.append(f'<p class="location">{esc(where)} · {esc(loc.symbol)}</p>')
        bundle = bundles.get(claim.id)
        if bundle is not None:
            if bundle.unmeasured:
                parts.append(f'<p class="unmeasured">완료 기준 없음 — {UNMEASURED}</p>')
            else:
                items = "".join(f"<li>{esc(view.task.criteria[n - 1])}</li>" for n in bundle.criteria)
                parts.append(f'<ul class="criteria">{items}</ul>')
        for decision_id in decisions_by_claim.get(claim.id, []):
            parts.append(f"<!--decision:{esc(decision_id)}-->")
        for child in by_parent.get(claim.id, []):
            parts.append(render(child))
        parts.append("</details>")
        return "".join(parts)

    for root in by_parent.get(None, []):
        yield render(root)


def _decision_block(view: PlanView, decision_id: str, *, can_answer: bool) -> str:
    dv = next(d for d in view.decisions if d.decision.id == decision_id)
    d = dv.decision
    parts = [f'<details class="decision" data-decision="{esc(d.id)}"><summary>{esc(d.id)} {esc(d.question)} — '
             f'<span class="state">{esc(dv.state)}</span></summary>']
    if d.state != dv.state:
        parts.append(f'<p class="warn">task 파일의 칸은 {esc(d.state)}</p>')
    if d.answered or not can_answer:
        chosen = d.state_value if d.answered else None
        items = "".join(
            f"<li>{esc(value)} — {esc(text)}" + (" (추천)" if value == d.default else "")
            + (" ← 답" if value == chosen else "") + "</li>"
            for value, text in d.options)
        parts.append(f"<ul>{items}</ul>")
    else:
        parts.append(f'<input type="hidden" name="opened_{esc(d.id)}" id="opened_{esc(d.id)}" value="no">')
        for value, text in d.options:
            checked = " checked" if value == d.default else ""
            parts.append(
                f'<label><input type="radio" name="value_{esc(d.id)}" value="{esc(value)}"{checked}> '
                f'{esc(value)} — {esc(text)}' + (" (추천)" if value == d.default else "") + "</label><br>")
        parts.append(f'<label>주석 <textarea name="comment_{esc(d.id)}" rows="2"></textarea></label>')
    parts.append("</details>")
    return "".join(parts)


def plan_page(*, view: PlanView, rel: str, branch: str, user: str, csrf: str, role: str,
              flash: str | None = None, error: str | None = None) -> str:
    task = view.task
    can_answer = role == "approver" and bool(view.decisions) and not view.has_errors
    open_count = sum(1 for d in view.decisions if d.open)
    body: list[str] = [f"<h1>{esc(task.task_id)}</h1>", f"<p>{esc(view.title)}</p>",
                       f'<p class="summary">상태 {esc(task.status)} · 열린 결정 {open_count}건 · 미반영 응답 {view.pending}건</p>']
    if view.layout_problem:
        body.append(f'<p class="error">계획 응답 배치: {esc(view.layout_problem)}</p>')
    if view.has_errors:
        body.append('<p class="error">task 파일의 주장 · 결정이 오류 규칙(L2 · L6 · L9)을 어겼다 — 응답을 받지 않는다</p>')
    if flash:
        body.append(f'<p class="flash">{esc(flash)}</p>')
    if error:
        body.append(f'<p class="error">{esc(error)}</p>')
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
        content = tree + "".join(loose)
        if view.verification:
            content += "<h2>검증</h2><ul>" + "".join(f"<li>{esc(v)}</li>" for v in view.verification) + "</ul>"
        if can_answer:
            content = (
                f'<form method="post" action="{esc(rel)}task/{esc(task.task_id)}/respond">'
                f'<input type="hidden" name="csrf" value="{esc(csrf)}">'
                f'<input type="hidden" name="plan_digest" value="{esc(view.digest)}">'
                + content
                + '<label>계획 전체 주석 <textarea name="comment_-" rows="3"></textarea></label>'
                '<p><button type="submit">응답 보내기</button></p></form>')
        body.append(content)
    else:
        rows = "".join(f"<li><b>{esc(label)}</b>: {esc(value)}</li>" for label, value in view.plain_fields)
        body.append(f"<ul>{rows}</ul>")
    if view.out_of_scope:
        body.append("<h2>Out of scope</h2><ul>" + "".join(f"<li>{esc(v)}</li>" for v in view.out_of_scope) + "</ul>")
    return page(title=f"워크벤치 — {task.task_id}", rel=rel, branch=branch, body="\n".join(body), script=can_answer,
                user=user, csrf=csrf)
