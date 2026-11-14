#!/usr/bin/env python3
"""워크벤치 — 진척 · 계획 화면과 `api/state` (`core/plan_workbench_spec.md` §4.4 · §7 · §11).

1. 선언 ≠ 파생이면 둘 다 보인다 — 화면과 `api/state` 가 같은 값
2. 잎 0 은 "미측정" (0% 가 아니다), `api/state` 는 `leaves_done: null`; 생성물에 없는 목록도 "미측정"
3. 절대 경로 · 호스트 이름 · 사용자 홈 · 환경변수 값 · 토큰 이름 목록이 어느 응답에도 없다 (`api/state` · 오류 화면 포함)
4. 이스케이프 — task 파일의 `<script>` 가 글자로 보인다
5. 읽기 전용 — 화면 · `api/state` · 제출을 돌린 뒤 `git status` 가 같고 받은편지함 밖의 파일이 그대로다
6. 계획 화면 — 계산한 결정 상태 · 칸이 다르면 "task 파일의 칸은" · 열린 결정 · 미반영 응답 건수 · 주장 없는 task 는 폼 없음
7. 정적 자원이 wheel 에 실린다 — 디스크의 `static/` 파일 = 서버의 고정 목록 = `package-data` 선언이 덮는 것
"""

from __future__ import annotations

#: 이 검사의 입력 표면 (spec `core/test_impact_tiering_spec.md` §2).
WATCHES = (
    "workflow-source/pyproject.toml",
    "workflow-source/workflow_kit/*",
    "workflow-source/tests/_workbench_fixture.py",
)

import fnmatch
import json
import os
import socket
import subprocess
import sys
import traceback
import tomllib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _workbench_fixture as fx  # noqa: E402
from workflow_kit.common import plan_claims as pc  # noqa: E402
from workflow_kit.common import plan_responses as pr  # noqa: E402
from workflow_kit.common import plan_tasks  # noqa: E402
from workflow_kit.workbench import server  # noqa: E402

FAILURES: list[str] = []
SOURCE_ROOT = fx.SOURCE_ROOT


def _record(name: str, problems: list[str]) -> None:
    if problems:
        FAILURES.append(name)
        print(f"  FAIL  {name}")
        for problem in problems[:12]:
            print(f"        - {problem}")
    else:
        print(f"  PASS  {name}")


def _roadmap(ws: Path, milestones: list[dict[str, object]], issues: list[dict[str, str]] | None = None) -> None:
    path = ws / "ai-workflow" / "memory" / "active" / "roadmap" / "roadmap_state.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"schema_version": 1, "generated_at": "2026-11-14", "milestones": milestones,
                                "issues": issues or []}, ensure_ascii=False), encoding="utf-8")


def _state(ws: Path, backlog: dict[str, object]) -> None:
    path = fx.branch_dir(ws) / "state.json"
    path.write_text(json.dumps({"schema_version": 1, "generated_at": "2026-11-14T10:00:00", "backlog": backlog},
                               ensure_ascii=False), encoding="utf-8")


def _milestone(mid: str, declared: str, derived: str, done: int, total: int) -> dict[str, object]:
    return {"id": mid, "title": f"{mid} 제목", "declared_status": declared, "derived_status": derived,
            "done_leaves": done, "total_leaves": total, "deliverables_missing": [], "wbs": []}


def _session(port: int) -> fx.Browser:
    browser = fx.Browser(port)
    browser.login(fx.APPROVER)
    return browser


def case_declared_vs_derived() -> list[str]:
    problems: list[str] = []
    with fx.temp_workspace("wb-views-1-") as td:
        ws = fx.make_workspace(td)
        _roadmap(ws, [_milestone("M-001", "in_progress", "done", 3, 4), _milestone("M-002", "done", "done", 2, 2)])
        with fx.running(ws) as srv:
            browser = _session(srv.port)
            page = browser.get("/").text
            api = json.loads(browser.get("/api/state").text)
        if "선언 in_progress · 파생 done" not in page:
            problems.append("선언 ≠ 파생인 마일스톤이 둘 다 보이지 않는다")
        if "선언 done" in page:
            problems.append("선언 = 파생인 마일스톤도 둘로 나눠 그렸다")
        if "완료 잎 3 / 전체 4" not in page or 'value="3" max="4"' not in page:
            problems.append("진척이 센 값 · 그 두 수의 막대로 그려지지 않았다")
        m1 = next((m for m in api.get("milestones", []) if m["id"] == "M-001"), {})
        if (m1.get("declared"), m1.get("derived"), m1.get("leaves_done"), m1.get("leaves_total")) != (
                "in_progress", "done", 3, 4):
            problems.append(f"api/state 의 마일스톤 값이 화면과 다르다: {m1}")
    return problems


def case_unmeasured() -> list[str]:
    problems: list[str] = []
    with fx.temp_workspace("wb-views-2-") as td:
        ws = fx.make_workspace(td)
        _roadmap(ws, [_milestone("M-003", "planned", "planned", 0, 0)])
        _state(ws, {"in_progress_items": ["TASK-2026-11-14-workbench-001 — 하는 중"], "done_items": []})
        with fx.running(ws) as srv:
            browser = _session(srv.port)
            page = browser.get("/").text
            api = json.loads(browser.get("/api/state").text)
        row = page[page.find("M-003"):][:400]
        if "미측정" not in row or "0%" in row or "<progress" in row:
            problems.append(f"잎 0 이 미측정으로 그려지지 않았다: {row[:200]}")
        m3 = next((m for m in api.get("milestones", []) if m["id"] == "M-003"), {})
        if m3.get("leaves_done") is not None or m3.get("leaves_total") != 0:
            problems.append(f"api/state 잎 0 의 leaves_done 이 null 이 아니다: {m3}")
        tasks = api.get("tasks", {})
        if tasks.get("planned") is not None or tasks.get("blocked") is not None:
            problems.append(f"생성물에 없는 목록을 빈 목록으로 지어냈다: {tasks}")
        if tasks.get("in_progress") != [{"id": "TASK-2026-11-14-workbench-001", "title": "하는 중"}]:
            problems.append(f"state.json 의 진행 중 목록이 그대로가 아니다: {tasks.get('in_progress')}")
        if page.count("미측정") < 3:
            problems.append("생성물에 없는 목록(차단 · 계획)이 화면에서 미측정이 아니다")
        if api.get("generated_at") != {"roadmap": "2026-11-14", "state": "2026-11-14T10:00:00"}:
            problems.append(f"생성물의 generated_at 이 그대로 실리지 않았다: {api.get('generated_at')}")
    return problems


def case_no_host_facts() -> list[str]:
    problems: list[str] = []
    with fx.temp_workspace("wb-views-3-") as td:
        ws = fx.make_workspace(td)
        task_id = fx.create_task(ws)
        _roadmap(ws, [_milestone("M-001", "in_progress", "done", 1, 2)],
                 issues=[{"code": "wbs_parse", "detail": "읽지 못했다", "where": str(ws / "M-001.md")},
                         {"code": "index_orphan", "detail": "어느 마일스톤에도 없다", "where": str(ws / "index.md")}])
        _state(ws, {"in_progress_items": [f"{task_id} — x"]})
        (pr.ensure_inbox(fx.branch_dir(ws)) / "stray.md").write_text("x", encoding="utf-8")
        forbidden = {
            "작업 공간 절대 경로": str(ws), "실경로": str(ws.resolve()), "사용자 홈": str(Path.home()),
            "호스트 이름": socket.gethostname(), "토큰 이름(viewer)": fx.VIEWER.name,
            "PATH 값": os.environ.get("PATH", "")[:40],
        }
        with fx.running(ws) as srv:
            browser = _session(srv.port)
            replies = {
                "/": browser.get("/"), "/api/state": browser.get("/api/state"), f"/task/{task_id}": browser.get(f"/task/{task_id}"),
                "/login": fx.request(srv.port, "GET", "/login"), "/nope": browser.get("/nope"),
                "/task/없는": browser.get("/task/TASK-2026-01-01-workbench-999"),
                "409": fx.submit(browser, f"/task/{task_id}", overrides={"plan_digest": "0" * 64})[0],
                "403": browser.post(f"/task/{task_id}/respond", {"csrf": "x"}, origin="http://other"),
            }
        for path, reply in replies.items():
            blob = reply.text + json.dumps(reply.headers, ensure_ascii=False)
            for label, value in forbidden.items():
                if value and value in blob:
                    problems.append(f"{path} 에 {label} 가 있다")
        for code in ("wbs_parse", "index_orphan"):
            if code not in replies["/"].text or code not in replies["/api/state"].text:
                problems.append(f"roadmap issue {code} 가 화면 · api 에 없다 (경로를 빼다가 issue 를 버렸다)")
    return problems


def case_escape() -> list[str]:
    problems: list[str] = []
    with fx.temp_workspace("wb-views-4-") as td:
        ws = fx.make_workspace(td)
        evil = "<script>alert(1)</script>"
        task_id = fx.create_task(
            ws, f"D1 [C1] {evil} 막는가? | default: block | options: block = <b>거부</b>; warn = 경고",
            name=f"제목 {evil}", claims=(f"C1 주장 {evil} 이다",), criteria=(f"[C1] 기준 {evil}",))
        _state(ws, {"in_progress_items": [f"{task_id} — {evil}"]})
        with fx.running(ws) as srv:
            browser = _session(srv.port)
            pages = {"/": browser.get("/").text, "task": browser.get(f"/task/{task_id}").text}
        for label, text in pages.items():
            if evil in text or "<b>거부</b>" in text:
                problems.append(f"{label}: task 파일의 마크업이 이스케이프 없이 들어갔다")
            if "&lt;script&gt;alert(1)&lt;/script&gt;" not in text:
                problems.append(f"{label}: 이스케이프된 글자가 보이지 않는다")
    return problems


def case_read_only() -> list[str]:
    problems: list[str] = []
    with fx.temp_workspace("wb-views-5-") as td:
        ws = fx.make_workspace(td)
        task_id = fx.create_task(ws)
        _roadmap(ws, [_milestone("M-001", "done", "done", 1, 1)])
        _state(ws, {"in_progress_items": []})
        git = ["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid", "-c", "commit.gpgsign=false"]
        subprocess.run([*git, "init", "-q", "-b", "main"], cwd=ws, check=True)
        subprocess.run([*git, "add", "-A"], cwd=ws, check=True)
        subprocess.run([*git, "commit", "-q", "-m", "fixture"], cwd=ws, check=True)
        status = lambda: subprocess.run(["git", "status", "--porcelain", "--ignored=no"], cwd=ws,  # noqa: E731
                                        capture_output=True, encoding="utf-8", check=True).stdout
        before_git = status()
        before_tree = fx.tree_snapshot(ws, skip=(".git/",))
        with fx.running(ws) as srv:
            browser = _session(srv.port)
            for path in ("/", "/api/state", f"/task/{task_id}", "/static/workbench.css", "/healthz", "/nope"):
                browser.get(path)
            reply, _ = fx.submit(browser, f"/task/{task_id}")
            if reply.status != 303:
                problems.append(f"제출이 통하지 않았다: {reply.status}")
        if status() != before_git:
            problems.append(f"git status 가 바뀌었다:\n{status()}")
        after_tree = fx.tree_snapshot(ws, skip=(".git/",))
        inbox_prefix = pr.inbox_dir(fx.branch_dir(ws)).relative_to(ws).as_posix() + "/"
        changed = sorted(k for k in set(before_tree) | set(after_tree)
                         if before_tree.get(k) != after_tree.get(k) and not k.startswith(inbox_prefix))
        if changed:
            problems.append(f"받은편지함 밖의 파일이 바뀌었다: {changed}")
        if not any(k.startswith(inbox_prefix) and k.endswith(".md") for k in after_tree):
            problems.append("제출한 응답이 받은편지함에 없다 (이 case 가 쓰기를 재지 못했다)")
    return problems


def case_plan_page() -> list[str]:
    problems: list[str] = []
    with fx.temp_workspace("wb-views-6-") as td:
        ws = fx.make_workspace(td)
        task_id = fx.create_task(ws)
        claims_only = fx.backlog(ws, "--mode", "create", "--status", "planned", "--task-name", "결정 없는 task",
                                 "--task-brief", "b", "--done-criteria", "[C1] 잰다",
                                 "--plan-claim", "C1 결정 없이 주장만 있다")["task_id"]
        plain = fx.backlog(ws, "--mode", "create", "--status", "planned", "--task-name", "주장 없는 task",
                           "--task-brief", "그대로 보인다", "--done-criteria", "끝난다")["task_id"]
        branch = fx.branch_dir(ws)
        task = plan_tasks.read_task_plan(branch / "backlog" / "tasks" / f"{task_id}.md")
        assert task is not None
        # 보관의 자격 있는 응답 — D1 을 warn 으로 (칸은 proposed 그대로).
        archive = pr.responses_dir(branch)
        archive.mkdir(parents=True)
        (archive / f"{task_id}-1.md").write_text(pr.render_response(
            task_id=task_id, plan=task.plan, responder="carol", received_at="2026-11-14T09:00:00.000000+09:00",
            values={"D1": "warn"}, opened={"D1": True}), encoding="utf-8")
        pr.publish(branch, task_id, pr.render_response(
            task_id=task_id, plan=task.plan, responder="dave", received_at="2026-11-14T09:00:01.000000+09:00").encode())
        with fx.running(ws) as srv:
            browser = _session(srv.port)
            page = browser.get(f"/task/{task_id}").text
            plain_page = browser.get(f"/task/{plain}").text
            claims_page = browser.get(f"/task/{claims_only}").text
        if fx.respond_form(claims_page) is not None or "결정 없이 주장만 있다" not in claims_page:
            problems.append("결정 없는 task 에 응답 폼이 있다 (답할 결정이 없다)")
        computed = plan_tasks.computed_states(task).states
        if computed.get("D1") != f"{pc.STATE_CHANGED}:warn":
            problems.append(f"fixture 가 성립하지 않았다 — 계산값 {computed}")
        if "changed:warn" not in page or "task 파일의 칸은 proposed" not in page:
            problems.append("계산한 상태와 칸의 값이 둘 다 보이지 않는다")
        if "열린 결정 1건" not in page or "미반영 응답 1건" not in page:
            problems.append("머리의 열린 결정 · 미반영 응답 건수가 계산값이 아니다")
        if 'value="block" checked' not in page or "(추천)" not in page:
            problems.append("기본값에 추천 · checked 가 없다")
        if fx.respond_form(plain_page) is not None or "그대로 보인다" not in plain_page:
            problems.append("주장 없는 task 가 필드를 그대로 보이지 않거나 폼이 있다")
    return problems


def case_static_in_wheel() -> list[str]:
    problems: list[str] = []
    static = SOURCE_ROOT / "workflow_kit" / "workbench" / "static"
    on_disk = sorted(p.name for p in static.iterdir() if p.is_file())
    if on_disk != sorted(server.STATIC_FILES):
        problems.append(f"디스크의 static/ {on_disk} 와 서버의 고정 목록 {sorted(server.STATIC_FILES)} 이 다르다")
    data = tomllib.loads((SOURCE_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    setuptools = data.get("tool", {}).get("setuptools", {})
    if "workflow_kit.workbench" not in setuptools.get("packages", []):
        problems.append("pyproject packages 에 workflow_kit.workbench 가 없다")
    globs = setuptools.get("package-data", {}).get("workflow_kit.workbench", [])
    for name in on_disk:
        if not any(fnmatch.fnmatch(f"static/{name}", pattern) for pattern in globs):
            problems.append(f"package-data 가 static/{name} 을 덮지 않는다 — wheel 에 안 실린다")
    from workflow_kit.tools import check_packaging
    missing = sorted(set(f"workbench/static/{n}" for n in on_disk) - set(check_packaging.REQUIRED_DATA))
    if missing:
        problems.append(f"발행 때 wheel 실측(check_packaging)이 재지 않는 자원: {missing}")
    return problems


CASES = (
    ("1 선언 ≠ 파생이면 둘 다 — 화면과 api/state 가 같은 값", case_declared_vs_derived),
    ("2 잎 0 · 생성물에 없는 목록은 미측정", case_unmeasured),
    ("3 절대 경로 · 호스트 이름 · 홈 · 토큰 이름이 어느 응답에도 없다", case_no_host_facts),
    ("4 이스케이프 — task 파일의 마크업은 글자다", case_escape),
    ("5 읽기 전용 — git status · 받은편지함 밖 파일 그대로", case_read_only),
    ("6 계획 화면 — 계산값 · 칸 · 건수 · 주장 없는 task", case_plan_page),
    ("7 정적 자원이 wheel 에 실린다 (선언 = 디스크 = 서버 목록)", case_static_in_wheel),
)


def main() -> int:
    print("check_workbench_views — 워크벤치 화면 · api/state (plan_workbench_spec §4.4 · §7)")
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
