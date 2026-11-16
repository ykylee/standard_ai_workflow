#!/usr/bin/env python3
"""워크벤치 todo 화면 · 편집 · 작업 세션 알림 (`core/plan_workbench_spec.md` §13.1, TASK-2026-11-16-main-017).

1. 화면 — 진척 화면의 '할 일'(항목 · 끝냄 단추 · 고치기 · 추가 폼) · 계획 카드와 보드의 `todo n/m` · 계획 화면의
   체크리스트 · `api/state` 의 todo · viewer 는 읽기만(폼 없음) · 이스케이프
2. 왕복 — 진척 · 계획 화면의 폼을 그대로 제출해 추가 · 끝냄 · 되돌림 · 고침 · 삭제가 todo.md 에 들고, 돌아가는 곳이 그 화면이다
3. 거절 — 세션 없음 401 · viewer 403 · 다른 Origin 403 · CSRF 403 · 본문 초과 413 · back 경로 · 끝 줄바꿈 400 · 빈 글 422 ·
   없는 id 404 · 없는 task 404 · 모르는 동작 422 · 락 시간 초과 503 — 전부 todo.md 무변경 · 기록 없음
4. hook — 브라우저 변경 뒤 `plan-import --hook` 출력에 누가 · 무엇을 · 글이 실리고, 다시 부르면 조용하다;
   작업 세션의 `todo` CLI 변경은 알리지 않는다
5. 새로고침 · 넘침 — todo.md 가 바뀌면 data-version 이 바뀐다 · 긴 글은 clamp + title · todo CSS 의 넘침 방지 규칙 ·
   스크립트가 todo 폼을 쓰는 중으로 센다
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
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _workbench_fixture as fx  # noqa: E402

from workflow_kit.common import todo_list  # noqa: E402

FAILURES: list[str] = []
STATIC = fx.SOURCE_ROOT / "workflow_kit" / "workbench" / "static"
VERSION_RE = re.compile(r'<main data-version="([0-9a-f]{16})">')


def _record(name: str, problems: list[str]) -> None:
    if problems:
        FAILURES.append(name)
        print(f"  FAIL  {name}")
        for problem in problems[:12]:
            print(f"        - {problem}")
    else:
        print(f"  PASS  {name}")


class _Forms(HTMLParser):
    """todo 폼 전부 — class · action · hidden 값."""

    def __init__(self) -> None:
        super().__init__()
        self.forms: list[dict[str, Any]] = []
        self._current: dict[str, Any] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = {k: v or "" for k, v in attrs}
        if tag == "form" and a.get("class", "").startswith("todo-"):
            self._current = {"class": a["class"], "action": a.get("action", ""), "fields": {}}
            self.forms.append(self._current)
        elif self._current is not None and tag == "input" and a.get("type") == "hidden":
            self._current["fields"][a.get("name", "")] = a.get("value", "")

    def handle_endtag(self, tag: str) -> None:
        if tag == "form":
            self._current = None


def _forms(html_text: str) -> list[dict[str, Any]]:
    parser = _Forms()
    parser.feed(html_text)
    return parser.forms


def _form(html_text: str, cls: str, item_id: str | None = None) -> dict[str, Any]:
    for form in _forms(html_text):
        if form["class"] == cls and (item_id is None or form["fields"].get("id") == item_id):
            return form
    raise AssertionError(f"폼이 없다: {cls} {item_id or ''}")


def _submit(browser: fx.Browser, page_path: str, cls: str, item_id: str | None = None,
            text: str | None = None) -> tuple[fx.Reply, str]:
    form = _form(browser.get(page_path).text, cls, item_id)
    fields = dict(form["fields"])
    if text is not None:
        fields["text"] = text
    action = fx.resolve(page_path, form["action"])
    return browser.post(action, fields), action


def _events(ws: Path) -> Path:
    return ws / ".workbench" / "todo-events.jsonl"


def _event_lines(ws: Path) -> list[str]:
    path = _events(ws)
    return path.read_text(encoding="utf-8").splitlines() if path.is_file() else []


def case_screen() -> list[str]:
    problems: list[str] = []
    with fx.temp_workspace("wb-todo-1-") as td:
        ws = fx.make_workspace(td)
        task_id = fx.create_task(ws)
        fx.backlog(ws, "--mode", "update", "--task-id", task_id, "--task-name", "x", "--status", "in_progress")
        bd = fx.branch_dir(ws)
        b = todo_list.add(bd, todo_list.BRANCH_SCOPE, "<script>alert(1)</script> 브랜치 일")
        todo_list.add(bd, task_id, "체크 하나")
        done = todo_list.add(bd, task_id, "체크 둘")
        todo_list.set_done(bd, done.id, True)
        with fx.running(ws, tokens=(), open_name="owner") as srv:
            browser = fx.Browser(srv.port)
            root = browser.get("/").text
            plan = browser.get(f"/task/{task_id}").text
            state = json.loads(browser.get("/api/state").text)
        if "<h2>할 일</h2>" not in root or f'data-todo="{b.id}"' not in root:
            problems.append("진척 화면에 브랜치 할 일이 없다")
        if "<script>alert(1)</script>" in root or "&lt;script&gt;alert(1)&lt;/script&gt;" not in root:
            problems.append("todo 글이 이스케이프되지 않았다")
        classes = sorted({f["class"] for f in _forms(root)})
        if classes != ["todo-add", "todo-edit", "todo-remove", "todo-toggle"]:
            problems.append(f"진척 화면 todo 폼이 모자라다: {classes}")
        if root.count("todo 1/2") < 2:
            problems.append("계획 카드 · 보드에 todo 1/2 가 둘 다 보이지 않는다")
        if "<h2>체크리스트</h2>" not in plan or "체크 하나" not in plan or "체크 둘" not in plan:
            problems.append("계획 화면에 그 task 체크리스트가 없다")
        if "브랜치 일" in plan:
            problems.append("계획 화면에 브랜치 할 일이 섞였다")
        add = _form(plan, "todo-add")["fields"]
        if add.get("scope") != task_id or add.get("back") != f"task/{task_id}":
            problems.append(f"계획 화면 추가 폼의 범위 · 돌아갈 곳이 틀리다: {add}")
        todo = state.get("todo") or {}
        if [i["id"] for i in todo.get("branch") or []] != [b.id] or todo.get("counts", {}).get(task_id) != [1, 2]:
            problems.append(f"api/state 의 todo 가 틀리다: {todo}")
        with fx.running(ws) as srv:
            viewer = fx.Browser(srv.port)
            viewer.login(fx.VIEWER)
            vroot, vplan = viewer.get("/").text, viewer.get(f"/task/{task_id}").text
        if _forms(vroot) or _forms(vplan):
            problems.append("viewer 화면에 todo 폼이 있다")
        if f'data-todo="{b.id}"' not in vroot or "체크 둘" not in vplan:
            problems.append("viewer 가 todo 를 읽지 못한다")
    return problems


def case_roundtrip() -> list[str]:
    problems: list[str] = []
    with fx.temp_workspace("wb-todo-2-") as td:
        ws = fx.make_workspace(td)
        task_id = fx.create_task(ws)
        bd = fx.branch_dir(ws)
        with fx.running(ws, tokens=(), open_name="owner") as srv:
            browser = fx.Browser(srv.port)
            for page_path, scope in (("/", todo_list.BRANCH_SCOPE), (f"/task/{task_id}", task_id)):
                reply, action = _submit(browser, page_path, "todo-add", text="  새 일  ")
                back = fx.resolve(action, reply.header("Location") or "")
                if reply.status != 303 or back != page_path:
                    problems.append(f"{page_path} 추가: {reply.status} → {back}")
                items = todo_list.read(bd).items(scope)
                if [i.text for i in items] != ["새 일"]:
                    problems.append(f"{page_path} 추가가 {scope} 에 들지 않았다: {items}")
                    continue
                item_id = items[0].id
                for cls, text, check in (("todo-toggle", None, lambda i: i.done),
                                         ("todo-toggle", None, lambda i: not i.done),
                                         ("todo-edit", "고친 일", lambda i: i.text == "고친 일")):
                    reply, _ = _submit(browser, page_path, cls, item_id, text)
                    item = todo_list.read(bd).find(item_id)
                    if reply.status != 303 or item is None or not check(item):
                        problems.append(f"{page_path} {cls}: {reply.status} {item}")
                reply, _ = _submit(browser, page_path, "todo-remove", item_id)
                if reply.status != 303 or todo_list.read(bd).find(item_id) is not None:
                    problems.append(f"{page_path} 삭제: {reply.status}")
    return problems


def case_reject() -> list[str]:
    problems: list[str] = []
    with fx.temp_workspace("wb-todo-3-") as td:
        ws = fx.make_workspace(td)
        task_id = fx.create_task(ws)
        bd = fx.branch_dir(ws)
        item = todo_list.add(bd, todo_list.BRANCH_SCOPE, "남는 일")
        with fx.running(ws) as srv:
            approver = fx.Browser(srv.port)
            approver.login(fx.APPROVER)
            base = dict(_form(approver.get("/").text, "todo-add")["fields"])
            viewer = fx.Browser(srv.port)
            viewer.login(fx.VIEWER)
            before = todo_list.todo_path(bd).read_bytes()
            attempts: list[tuple[str, fx.Reply, int]] = [
                ("세션 없음", fx.Browser(srv.port).post("/todo", {**base, "text": "x"}), 401),
                ("viewer", viewer.post("/todo", {**base, "csrf": fx.csrf_of(viewer.get("/").text), "text": "x"}), 403),
                ("다른 Origin", approver.post("/todo", {**base, "text": "x"}, origin="http://evil.example"), 403),
                ("CSRF", approver.post("/todo", {**base, "csrf": "0" * 40, "text": "x"}), 403),
                ("본문 초과", approver.post("/todo", {**base, "text": "가" * 3000}), 413),
                ("back 경로", approver.post("/todo", {**base, "text": "x", "back": "//evil.example/"}), 400),
                ("back 끝 줄바꿈", approver.post("/todo", {**base, "text": "x", "back": f"task/{task_id}\n"}), 400),
                ("빈 글", approver.post("/todo", {**base, "text": "   "}), 422),
                ("없는 id", approver.post("/todo", {**base, "action": "done", "id": "abcdef"}), 404),
                ("없는 task", approver.post("/todo", {**base, "scope": "TASK-2026-01-01-none-001", "text": "x"}), 404),
                ("모르는 동작", approver.post("/todo", {**base, "action": "wipe", "text": "x"}), 422),
            ]
            # 락을 쥔 채 요청 — 기다림 상한을 넘기면 503 이고 쓰지 않는다 (같은 프로세스의 다른 열기는 flock 에 막힌다).
            saved_timeout = todo_list.LOCK_TIMEOUT_S
            todo_list.LOCK_TIMEOUT_S = 0.3
            try:
                with todo_list._locked(bd):
                    attempts.append(("락 시간 초과", approver.post("/todo", {**base, "text": "x"}), 503))
            finally:
                todo_list.LOCK_TIMEOUT_S = saved_timeout
        for label, reply, status in attempts:
            if reply.status != status:
                problems.append(f"{label}: {reply.status} (기대 {status})")
        if todo_list.todo_path(bd).read_bytes() != before:
            problems.append("거절된 요청이 todo.md 를 바꿨다")
        if _event_lines(ws):
            problems.append(f"거절된 요청이 기록을 남겼다: {_event_lines(ws)}")
        del item, task_id
    return problems


def _hook(ws: Path) -> str:
    proc = fx.cli(ws, ["-m", "workflow_kit", "plan-import", "--project-profile-path", str(fx.profile(ws)),
                       "--hook", "UserPromptSubmit"])
    if proc.returncode != 0:
        raise AssertionError(f"hook rc {proc.returncode}: {proc.stderr[-200:]}")
    return proc.stdout


def case_hook() -> list[str]:
    problems: list[str] = []
    with fx.temp_workspace("wb-todo-4-") as td:
        ws = fx.make_workspace(td)
        task_id = fx.create_task(ws)
        with fx.running(ws, tokens=(), open_name="owner") as srv:
            browser = fx.Browser(srv.port)
            _submit(browser, "/", "todo-add", text="소유자가 더한 일")
            _submit(browser, f"/task/{task_id}", "todo-add", text="체크 항목")
            item = todo_list.read(fx.branch_dir(ws)).items(task_id)[0]
            _submit(browser, f"/task/{task_id}", "todo-toggle", item.id)
        out = _hook(ws)
        try:
            context = json.loads(out)["hookSpecificOutput"]["additionalContext"]
        except (json.JSONDecodeError, KeyError, TypeError):
            return [f"hook 출력이 hook JSON 이 아니다: {out[-200:]!r}"]
        for needle in ("소유자가 todo 를 바꿨다", "owner · 추가 · 브랜치 할 일: 소유자가 더한 일",
                       f"owner · 추가 · {task_id} 체크리스트: 체크 항목", f"owner · 끝냄 · {task_id} 체크리스트: 체크 항목"):
            if needle not in context:
                problems.append(f"hook 알림에 없다: {needle}")
        if _hook(ws).strip():
            problems.append("이미 알린 변경을 다시 실었다")
        cli = fx.cli(ws, ["-m", "workflow_kit", "todo", "--project-profile-path", str(fx.profile(ws)), "--add", "작업 세션 일"])
        if cli.returncode != 0:
            problems.append(f"todo CLI 실패: {cli.stderr[-160:]}")
        if _event_lines(ws):
            problems.append("작업 세션의 CLI 변경이 소유자 변경 기록에 들었다")
    return problems


def case_refresh_and_overflow() -> list[str]:
    problems: list[str] = []
    with fx.temp_workspace("wb-todo-5-") as td:
        ws = fx.make_workspace(td)
        fx.create_task(ws)
        bd = fx.branch_dir(ws)
        with fx.running(ws, tokens=(), open_name="owner") as srv:
            srv.app.refresh_seconds = 5
            browser = fx.Browser(srv.port)
            first = VERSION_RE.search(browser.get("/").text)
            todo_list.add(bd, todo_list.BRANCH_SCOPE, "가" * 300)
            text = browser.get("/").text
            second = VERSION_RE.search(text)
        if not first or not second or first.group(1) == second.group(1):
            problems.append("todo.md 가 바뀌었는데 data-version 이 그대로다")
        if not re.search(r'<span class="todo-text clamp-3" title="가{300}">', text):
            problems.append("긴 todo 글에 clamp · title 이 없다")
        if 'style="' in text:
            problems.append("인라인 style 이 있다")
    css = (STATIC / "workbench.css").read_text(encoding="utf-8")
    for rule in (r"\.todo-text \{[^}]*min-width: 0[^}]*overflow-wrap: anywhere",
                 r"\.todo-item \{[^}]*flex-wrap: wrap[^}]*min-width: 0",
                 r"\.todo-edit input, \.todo-add input \{[^}]*min-width: 0"):
        if not re.search(rule, css):
            problems.append(f"todo CSS 넘침 방지 규칙이 없다: {rule[:40]}")
    if css.rindex(".clamp-3 {") < css.index(".todo-text {"):
        problems.append("clamp 규칙이 todo 규칙보다 앞에 있다 — display 가 덮인다")
    js = (STATIC / "workbench.js").read_text(encoding="utf-8")
    if 'querySelectorAll("form.todo-add, form.todo-edit")' not in js or "bindTodo(main)" not in js:
        problems.append("스크립트가 todo 폼을 쓰는 중으로 세지 않는다 — 새로고침이 쓰던 글을 지운다")
    return problems


CASES = (
    ("1 화면 — 할 일 · todo n/m · 체크리스트 · api/state · viewer 읽기만", case_screen),
    ("2 왕복 — 폼 제출이 todo.md 에 · 그 화면으로 돌아감", case_roundtrip),
    ("3 거절 — 401 · 403 · 413 · 400 · 422 · 404 · 503, 무변경 · 기록 없음", case_reject),
    ("4 hook — 소유자 변경 알림 · 한 번만 · CLI 변경은 안 알림", case_hook),
    ("5 새로고침 지문 · 넘침 방지 · 쓰는 중", case_refresh_and_overflow),
)


def main() -> int:
    print("check_workbench_todo — 워크벤치 todo (plan_workbench_spec §13.1)")
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
