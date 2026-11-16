#!/usr/bin/env python3
"""워크벤치 화면 구조 — 대시보드형 진척 · 카드형 계획 (`core/plan_workbench_spec.md` §4.4 · §7.2, TASK-2026-11-16-main-003).

1. 진척 화면의 요약 수치(진행 중 · 차단 · 계획 · 열린 결정 · 미반영 응답)가 `api/state` 에서 센 값과 같다 —
   생성물에 없는 목록은 "미측정"
2. 작업 보드 4열(진행 중 · 차단 · 계획 · 최근 완료) · 열 머리 건수, 계획 카드의 열린 결정 강조, 마일스톤 진척 막대;
   선언 · 파생이 둘 다 done 이고 문제 없는 마일스톤만 접히고 어긋난 것은 펼쳐 있다
3. 계획 화면 — 상태 칩 · 열린 결정은 `decision open` 클래스 · 선택지 카드(`label.option`) · 고정 제출 막대; 결정은 닫힌 채 그린다
   (펼침이 곧 '열어 봄' 기록이다)
4. CSP 위생 — 모든 화면에 `style=` 속성 · 인라인 스크립트 · 외부 URL 이 없다; CSS 에 어두운 모드 · 좁은 폭 규칙이 있고 외부 자원(`url(` · `@import`)이 없다
"""

from __future__ import annotations

#: 이 검사의 입력 표면 (spec `core/test_impact_tiering_spec.md` §2).
WATCHES = (
    "workflow-source/pyproject.toml",
    "workflow-source/workflow_kit/*",
    "workflow-source/tests/_workbench_fixture.py",
)

import json
import re
import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _workbench_fixture as fx  # noqa: E402
from workflow_kit.common import plan_responses as pr  # noqa: E402

FAILURES: list[str] = []
CSS = fx.SOURCE_ROOT / "workflow_kit" / "workbench" / "static" / "workbench.css"
KPI_RE = re.compile(r'<span class="kpi-label">([^<]+)</span><span class="kpi-value[^"]*">([^<]+)</span>')


def _record(name: str, problems: list[str]) -> None:
    if problems:
        FAILURES.append(name)
        print(f"  FAIL  {name}")
        for problem in problems[:12]:
            print(f"        - {problem}")
    else:
        print(f"  PASS  {name}")


def _roadmap(ws: Path, milestones: list[dict[str, object]]) -> None:
    path = ws / "ai-workflow" / "memory" / "active" / "roadmap" / "roadmap_state.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"schema_version": 1, "generated_at": "2026-11-14", "milestones": milestones,
                                "issues": []}, ensure_ascii=False), encoding="utf-8")


def _milestone(mid: str, declared: str, derived: str, done: int, total: int) -> dict[str, object]:
    return {"id": mid, "title": f"{mid} 제목", "declared_status": declared, "derived_status": derived,
            "done_leaves": done, "total_leaves": total, "deliverables_missing": [], "wbs": []}


def _state(ws: Path, backlog: dict[str, object]) -> None:
    (fx.branch_dir(ws) / "state.json").write_text(json.dumps(
        {"schema_version": 1, "generated_at": "2026-11-14T10:00:00", "backlog": backlog}, ensure_ascii=False),
        encoding="utf-8")


def _workspace(td: str) -> tuple[Path, str]:
    ws = fx.make_workspace(td)
    task_id = fx.create_task(ws)
    _roadmap(ws, [_milestone("M-001", "done", "done", 2, 2), _milestone("M-002", "in_progress", "in_progress", 1, 3),
                  _milestone("M-003", "in_progress", "done", 4, 4)])
    _state(ws, {"in_progress_items": [f"{task_id} — 응답을 받는 task", "TASK-2026-11-14-workbench-009 — 둘째"],
                "blocked_items": [], "done_items": ["TASK-2026-11-13-workbench-001 — 끝난 것"]})
    return ws, task_id


def _pages(ws: Path, task_id: str) -> dict[str, str]:
    with fx.running(ws, tokens=(), open_name="owner") as srv:
        browser = fx.Browser(srv.port)
        # 미반영 응답 1건 — 서버가 쓴 응답이어야 census 가 센다.
        fx.submit(browser, f"/task/{task_id}")
        return {"/": browser.get("/").text, "api": browser.get("/api/state").text,
                "task": browser.get(f"/task/{task_id}").text, "missing": browser.get("/task/TASK-2026-01-01-x-001").text,
                "login": fx.request(srv.port, "GET", "/login").text}


def case_kpis() -> list[str]:
    problems: list[str] = []
    with fx.temp_workspace("wb-design-1-") as td:
        ws, task_id = _workspace(td)
        pages = _pages(ws, task_id)
    api = json.loads(pages["api"])
    tasks = api["tasks"]
    expected = {
        "진행 중": str(len(tasks["in_progress"])),
        "차단": str(len(tasks["blocked"])),
        "계획": "미측정" if tasks["planned"] is None else str(len(tasks["planned"])),
        "열린 결정": str(sum(len(p["open_decisions"]) for p in api["plans"])),
        "미반영 응답": str(sum(api["inbox"]["pending"].values())),
    }
    shown = dict(KPI_RE.findall(pages["/"]))
    if shown != expected:
        problems.append(f"요약 수치가 api/state 와 다르다: 화면 {shown} · 기대 {expected}")
    if expected["열린 결정"] == "0" or expected["미반영 응답"] == "0" or expected["계획"] != "미측정":
        problems.append(f"fixture 가 성립하지 않았다 — 0 · 측정값만으로는 수치를 재지 못한다: {expected}")
    return problems


def case_board_and_milestones() -> list[str]:
    problems: list[str] = []
    with fx.temp_workspace("wb-design-2-") as td:
        ws, task_id = _workspace(td)
        page = _pages(ws, task_id)["/"]
    columns = re.findall(r'<div class="column (\w+)"><h2><span>([^<]+)</span><span class="n">([^<]+)</span>', page)
    if [(label, n) for _, label, n in columns] != [("진행 중", "2"), ("차단", "0"), ("계획", "미측정"), ("최근 완료", "1")]:
        problems.append(f"작업 보드 4열 · 건수가 다르다: {columns}")
    if f'class="card plan-card attention" href="./task/{task_id}"' not in page:
        problems.append("열린 결정이 있는 계획 카드가 강조되지 않았다")
    fold = page[page.find('<details class="fold">'):] if '<details class="fold">' in page else ""
    if not fold or "M-001" not in fold or "완료된 마일스톤 1개" not in fold:
        problems.append("선언 · 파생 모두 done 인 마일스톤이 접히지 않았다")
    for mid in ("M-002", "M-003"):
        if mid in fold or mid not in page:
            problems.append(f"{mid}(진행 중 또는 어긋남)이 접혔거나 없다")
    if '<div class="meter"><progress value="1" max="3"></progress>' not in page:
        problems.append("마일스톤 진척 막대가 없다")
    return problems


def case_plan_page() -> list[str]:
    problems: list[str] = []
    with fx.temp_workspace("wb-design-3-") as td:
        ws, task_id = _workspace(td)
        page = _pages(ws, task_id)["task"]
    for needle, label in (('<span class="chip warn">열린 결정 2건</span>', "열린 결정 칩"),
                          ('<span class="chip info">미반영 응답 1건</span>', "미반영 응답 칩"),
                          ('<div class="submitbar">', "고정 제출 막대"),
                          ('<p class="crumbs"><a href="../">', "진척으로 가는 상대 링크")):
        if needle not in page:
            problems.append(f"계획 화면에 {label} 이 없다")
    decisions = re.findall(r'<details([^>]*) class="decision (\w+)" data-decision="(D\d+)"', page)
    if sorted((d, kind) for _, kind, d in decisions) != [("D1", "open"), ("D2", "open")]:
        problems.append(f"열린 결정이 강조 클래스로 그려지지 않았다: {decisions}")
    if any(attrs.strip() for attrs, _, _ in decisions) or re.search(r'<details open class="decision', page):
        problems.append("결정을 펼친 채 그렸다 — 펼침이 곧 '열어 봄' 기록이다")
    options = page.count('<label class="option"><input type="radio"')
    if options != 4:
        problems.append(f"선택지 카드가 4개가 아니다: {options}")
    return problems


def case_csp_hygiene() -> list[str]:
    problems: list[str] = []
    with fx.temp_workspace("wb-design-4-") as td:
        ws, task_id = _workspace(td)
        (pr.ensure_inbox(fx.branch_dir(ws)) / "stray.md").write_text("x", encoding="utf-8")
        pages = _pages(ws, task_id)
    for name, html_text in pages.items():
        if name == "api":
            continue
        if re.search(r"\sstyle\s*=", html_text):
            problems.append(f"{name}: style= 속성이 있다 (CSP style-src 'self')")
        if re.search(r"<script(?![^>]*\ssrc=)", html_text):
            problems.append(f"{name}: 인라인 스크립트가 있다")
        if re.search(r'(?:href|src|action)="(?:https?:)?//', html_text):
            problems.append(f"{name}: 외부 · 절대 URL 이 있다")
    css = CSS.read_text(encoding="utf-8")
    if "prefers-color-scheme: dark" not in css or not re.search(r"@media \(max-width: \d+px\)", css):
        problems.append("CSS 에 어두운 모드 · 좁은 폭 규칙이 없다")
    if "url(" in css or "@import" in css:
        problems.append("CSS 가 외부 자원을 부른다")
    return problems


CASES = (
    ("1 요약 수치 = api/state", case_kpis),
    ("2 작업 보드 4열 · 계획 카드 강조 · 마일스톤 막대 · 완료분 접기", case_board_and_milestones),
    ("3 계획 화면 — 칩 · 열린 결정 강조 · 선택지 카드 · 제출 막대 · 결정은 닫힌 채", case_plan_page),
    ("4 CSP 위생 · 어두운 모드 · 좁은 폭", case_csp_hygiene),
)


def main() -> int:
    print("check_workbench_design — 워크벤치 화면 구조 (plan_workbench_spec §4.4 · §7.2)")
    for name, case in CASES:
        try:
            _record(name, case())
        except Exception:  # noqa: BLE001 — case 하나의 예외는 그 case 의 FAIL 이다
            _record(name, ["예외: " + traceback.format_exc().strip().splitlines()[-1]])
            traceback.print_exc()
    print(f"\n{len(CASES) - len(FAILURES)}/{len(CASES)} PASS")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
