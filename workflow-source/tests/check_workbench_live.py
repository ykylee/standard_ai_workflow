#!/usr/bin/env python3
"""워크벤치 진척의 실시간 값 (`core/plan_workbench_spec.md` §7.1, TASK-2026-11-16-main-008).

1. 프로필을 아는 서버는 `state.json` 이 낡아도 원천에서 계산한 값을 낸다 — 방금 진행 중으로 바꾼 task 가 목록에 있고 낡은 항목은 없다,
   `api/state.source == "live"`, 화면에 "실시간"; 요청 전후 작업 공간 파일이 그대로다(저장소에 쓰지 않는다)
2. 원천 지문 — 원천이 그대로면 생성기를 다시 부르지 않고(호출 횟수), 원천이 바뀌면 다시 부른다; 같은 원천의 화면 지문이 같다
3. 프로필을 모르는 위치는 생성물을 읽는다 — `source == "generated"`, 낡은 항목 그대로, 화면에 생성 시각
4. CLI 서버가 쓰는 위치(`server.where_for`)는 프로필을 싣는다 — 실제 서버 경로가 실시간이다
5. 브랜치 전환 — 파일이 그대로여도 브랜치가 바뀌면 다시 계산하고 그 브랜치의 값을 낸다 (캐시 키에 브랜치)
6. 실시간 계산 실패는 조용하지 않다 — `api/state.live_error` · 화면 경고, 값은 생성물
7. roadmap 도 실시간 — 마일스톤은 `build_roadmap_state` 의 값이고 디스크의 낡은 `roadmap_state.json` 이 아니다;
   roadmap 원천이 없으면 낡은 생성물을 실시간으로 보이지 않는다
8. 지문에 마일스톤 산출물 — 산출물 파일이 생기면 다시 계산한다
9. 실패 사유에 절대 경로가 없다 — 작업 공간 경로는 상대로, 그 밖의 절대 경로(사용자 홈 등)는 가린다 (`api/state` · 화면)
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
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _workbench_fixture as fx  # noqa: E402
from workflow_kit.workbench import server, state_view  # noqa: E402

FAILURES: list[str] = []
STALE = "TASK-2026-01-01-workbench-099"


def _record(name: str, problems: list[str]) -> None:
    if problems:
        FAILURES.append(name)
        print(f"  FAIL  {name}")
        for problem in problems[:12]:
            print(f"        - {problem}")
    else:
        print(f"  PASS  {name}")


def _stale_state(ws: Path) -> None:
    (fx.branch_dir(ws) / "state.json").write_text(json.dumps(
        {"schema_version": 1, "generated_at": "2026-01-01T00:00:00",
         "backlog": {"in_progress_items": [f"{STALE} — 낡은 항목"], "planned_items": [], "blocked_items": [],
                     "done_items": []}}, ensure_ascii=False), encoding="utf-8")


@contextmanager
def _live_server(ws: Path, *, with_profile: bool = True) -> Iterator[fx.Running]:
    def locate() -> state_view.Where:
        return state_view.Where(workspace_root=ws, branch=fx.BRANCH, branch_dir=fx.branch_dir(ws),
                                profile_path=fx.profile(ws).resolve() if with_profile else None)
    logs: list[str] = []
    app = server.App(public_url="http://127.0.0.1:0/", tokens=(), locate=locate, open_name="owner", log=logs.append)
    httpd = server.make_server(app, "127.0.0.1", 0)
    port = httpd.server_address[1]
    app.public_url = f"http://127.0.0.1:{port}/"
    server.serve_in_thread(httpd)
    state_view._LIVE_CACHE.clear()
    # 생성기의 브랜치 해석이 fixture 브랜치를 보게 한다 (backlog-update 와 같은 env).
    with mock.patch.dict("os.environ", {"CODEX_WORKFLOW_BRANCH": fx.BRANCH}):
        try:
            yield fx.Running(app=app, httpd=httpd, port=port, logs=logs)
        finally:
            httpd.shutdown()
            httpd.server_close()


def _api(port: int) -> dict[str, Any]:
    return json.loads(fx.request(port, "GET", "/api/state").text)


def case_live_values() -> list[str]:
    problems: list[str] = []
    with fx.temp_workspace("wb-live-1-") as td:
        ws = fx.make_workspace(td)
        task_id = fx.create_task(ws)
        # state.json 생성기는 진행 중 · 차단 · 완료 목록을 낸다(계획 목록은 없다 — 화면에서 미측정).
        fx.backlog(ws, "--mode", "update", "--task-id", task_id, "--task-name", "x", "--status", "in_progress")
        _stale_state(ws)
        before = fx.tree_snapshot(ws, skip=(".workbench/",))
        with _live_server(ws) as srv:
            api = _api(srv.port)
            page = fx.request(srv.port, "GET", "/").text
        after = fx.tree_snapshot(ws, skip=(".workbench/",))
        if api.get("source") != "live":
            problems.append(f"프로필을 아는데 source 가 {api.get('source')!r} 다")
        listed = [item["id"] for item in (api["tasks"].get("in_progress") or [])]
        if task_id not in listed:
            problems.append(f"방금 진행 중으로 바꾼 task 가 실시간 진행 중 목록에 없다: {listed}")
        if STALE in json.dumps(api, ensure_ascii=False):
            problems.append("낡은 state.json 의 항목이 실시간 값에 섞였다")
        if "실시간" not in page:
            problems.append("화면에 실시간 표시가 없다")
        if before != after:
            changed = sorted(k for k in set(before) | set(after) if before.get(k) != after.get(k))
            problems.append(f"실시간 계산이 작업 공간에 썼다: {changed[:6]}")
    return problems


def case_fingerprint() -> list[str]:
    problems: list[str] = []
    with fx.temp_workspace("wb-live-2-") as td:
        ws = fx.make_workspace(td)
        task_id = fx.create_task(ws)
        with _live_server(ws) as srv:
            start = state_view.LIVE_COMPUTE_COUNT
            first = fx.request(srv.port, "GET", "/").text
            second = fx.request(srv.port, "GET", "/").text
            _api(srv.port)
            if state_view.LIVE_COMPUTE_COUNT - start != 1:
                problems.append(f"원천이 그대로인데 생성기를 {state_view.LIVE_COMPUTE_COUNT - start}번 불렀다 (기대 1)")
            versions = [re.search(r'data-version="([0-9a-f]+)"', t) for t in (first, second)]
            if None in versions or versions[0].group(1) != versions[1].group(1):  # type: ignore[union-attr]
                problems.append("같은 원천인데 화면 지문이 다르다 — 자동 새로고침이 매번 갈아 끼운다")
            fx.backlog(ws, "--mode", "update", "--task-id", task_id, "--task-name", "x", "--status", "blocked")
            api = _api(srv.port)
            if state_view.LIVE_COMPUTE_COUNT - start != 2:
                problems.append("원천이 바뀌었는데 다시 계산하지 않았다")
            if task_id not in [item["id"] for item in (api["tasks"].get("blocked") or [])]:
                problems.append(f"상태를 blocked 로 바꾼 task 가 차단 목록에 없다: {api['tasks']}")
    return problems


def case_generated_fallback() -> list[str]:
    problems: list[str] = []
    with fx.temp_workspace("wb-live-3-") as td:
        ws = fx.make_workspace(td)
        fx.create_task(ws)
        _stale_state(ws)
        with _live_server(ws, with_profile=False) as srv:
            api = _api(srv.port)
            page = fx.request(srv.port, "GET", "/").text
        if api.get("source") != "generated":
            problems.append(f"프로필을 모르는데 source 가 {api.get('source')!r} 다")
        if [item["id"] for item in api["tasks"]["in_progress"] or []] != [STALE]:
            problems.append(f"생성물의 목록을 그대로 읽지 않았다: {api['tasks']['in_progress']}")
        if "state 생성 2026-01-01T00:00:00" not in page or "실시간" in page:
            problems.append("생성물을 읽은 화면에 생성 시각이 없거나 실시간으로 표시했다")
    return problems


def case_where_for() -> list[str]:
    problems: list[str] = []
    with fx.temp_workspace("wb-live-4-") as td:
        ws = fx.make_workspace(td)
        with mock.patch.dict("os.environ", {"CODEX_WORKFLOW_BRANCH": fx.BRANCH}):
            where = server.where_for(fx.profile(ws).resolve())()
        if where.profile_path is None:
            problems.append("server.where_for 가 프로필을 싣지 않는다 — CLI 서버가 생성물만 읽는다")
    return problems


class _FakeRoadmap:
    def __init__(self, mid: str) -> None:
        self.mid = mid

    def model_dump(self, mode: str = "json") -> dict[str, Any]:
        return {"generated_at": "live", "issues": [], "milestones": [
            {"id": self.mid, "title": "실시간 마일스톤", "declared_status": "in_progress", "derived_status": "in_progress",
             "done_leaves": 1, "total_leaves": 2, "deliverables_missing": [], "wbs": []}]}


def _stale_roadmap(ws: Path, mid: str) -> None:
    path = ws / "ai-workflow" / "memory" / "active" / "roadmap" / "roadmap_state.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"schema_version": 1, "generated_at": "2026-01-01", "issues": [], "milestones": [
        {"id": mid, "title": "낡은 마일스톤", "declared_status": "done", "derived_status": "done", "done_leaves": 1,
         "total_leaves": 1, "deliverables_missing": [], "wbs": []}]}), encoding="utf-8")


def case_branch_switch() -> list[str]:
    problems: list[str] = []
    with fx.temp_workspace("wb-live-5-") as td:
        ws = fx.make_workspace(td)
        task_id = fx.create_task(ws)
        fx.backlog(ws, "--mode", "update", "--task-id", task_id, "--task-name", "x", "--status", "in_progress")
        other = ws / "ai-workflow" / "memory" / "active" / "other"
        (other / "backlog" / "tasks").mkdir(parents=True)
        locate = server.where_for(fx.profile(ws).resolve())
        logs: list[str] = []
        app = server.App(public_url="http://127.0.0.1:0/", tokens=(), locate=locate, open_name="owner", log=logs.append)
        httpd = server.make_server(app, "127.0.0.1", 0)
        port = httpd.server_address[1]
        server.serve_in_thread(httpd)
        state_view._LIVE_CACHE.clear()
        try:
            with mock.patch.dict("os.environ", {"CODEX_WORKFLOW_BRANCH": fx.BRANCH}):
                first = _api(port)
            start = state_view.LIVE_COMPUTE_COUNT
            with mock.patch.dict("os.environ", {"CODEX_WORKFLOW_BRANCH": "other"}):
                second = _api(port)
        finally:
            httpd.shutdown()
            httpd.server_close()
        if task_id not in [i["id"] for i in first["tasks"]["in_progress"] or []]:
            problems.append(f"fixture 가 성립하지 않았다 — 첫 브랜치에 진행 중 task 가 없다: {first['tasks']}")
        if second.get("branch") != "other" or state_view.LIVE_COMPUTE_COUNT - start != 1:
            problems.append(f"브랜치가 바뀌었는데 다시 계산하지 않았다 (branch {second.get('branch')}, "
                            f"재계산 {state_view.LIVE_COMPUTE_COUNT - start})")
        if task_id in json.dumps(second["tasks"], ensure_ascii=False):
            problems.append("다른 브랜치의 진척을 실시간 값으로 보였다")
    return problems


def case_failure_reported() -> list[str]:
    problems: list[str] = []
    with fx.temp_workspace("wb-live-6-") as td:
        ws = fx.make_workspace(td)
        fx.create_task(ws)
        _stale_state(ws)
        with _live_server(ws) as srv, mock.patch("workflow_kit.common.state.cache.refresh_workflow_state_cache",
                                                 side_effect=RuntimeError("boom")):
            api = _api(srv.port)
            page = fx.request(srv.port, "GET", "/").text
        if api.get("source") != "generated" or "boom" not in str(api.get("live_error")):
            problems.append(f"실패가 api 에 없다: source {api.get('source')} · live_error {api.get('live_error')}")
        if "실시간 계산 실패" not in page or "boom" not in page:
            problems.append("실시간 계산 실패가 화면에 보이지 않는다")
    return problems


def case_roadmap_live() -> list[str]:
    problems: list[str] = []
    with fx.temp_workspace("wb-live-7-") as td:
        ws = fx.make_workspace(td)
        fx.create_task(ws)
        _stale_roadmap(ws, "M-066")
        target = "workflow_kit.common.state.roadmap.build_roadmap_state"
        with _live_server(ws) as srv:
            with mock.patch(target, return_value=_FakeRoadmap("M-077")):
                ids = [m["id"] for m in _api(srv.port)["milestones"]]
            if ids != ["M-077"]:
                problems.append(f"마일스톤이 실시간 roadmap 이 아니다: {ids}")
            state_view._LIVE_CACHE.clear()
            with mock.patch(target, return_value=None):
                api = _api(srv.port)
            if api.get("source") != "live" or api["milestones"]:
                problems.append(f"roadmap 원천이 없는데 낡은 생성물을 실시간으로 보였다: {[m['id'] for m in api['milestones']]}")
    return problems


def case_deliverable_fingerprint() -> list[str]:
    problems: list[str] = []
    with fx.temp_workspace("wb-live-8-") as td:
        ws = fx.make_workspace(td)
        fx.create_task(ws)
        deliverable = ws / "docs" / "design.md"
        with _live_server(ws) as srv, mock.patch.object(state_view, "_deliverable_paths", return_value=(deliverable,)):
            start = state_view.LIVE_COMPUTE_COUNT
            _api(srv.port)
            _api(srv.port)
            if state_view.LIVE_COMPUTE_COUNT - start != 1:
                problems.append(f"산출물이 그대로인데 {state_view.LIVE_COMPUTE_COUNT - start}번 계산했다 (기대 1)")
            deliverable.write_text("x", encoding="utf-8")
            _api(srv.port)
            if state_view.LIVE_COMPUTE_COUNT - start != 2:
                problems.append("마일스톤 산출물이 생겼는데 다시 계산하지 않았다 — deliverables_missing 이 낡는다")
    return problems


def case_error_has_no_paths() -> list[str]:
    problems: list[str] = []
    with fx.temp_workspace("wb-live-9-") as td:
        ws = fx.make_workspace(td)
        fx.create_task(ws)
        handoff = fx.branch_dir(ws) / "session_handoff.md"
        boom = PermissionError(13, "Permission denied", str(handoff))
        boom2 = RuntimeError("cannot read /home/someone/.config/x.toml or C:\\Users\\someone\\y.json")
        for exc in (boom, boom2):
            with _live_server(ws) as srv, mock.patch("workflow_kit.common.state.cache.refresh_workflow_state_cache",
                                                     side_effect=exc):
                api_text = fx.request(srv.port, "GET", "/api/state").text
                page = fx.request(srv.port, "GET", "/").text
            error = json.loads(api_text).get("live_error") or ""
            if not error:
                problems.append(f"{type(exc).__name__}: 실패 사유가 없다")
            if exc is boom and handoff.relative_to(ws).as_posix() not in error:
                problems.append(f"작업 공간 경로를 상대 경로로 남기지 않았다(무엇이 실패했는지 잃었다): {error}")
            for label, text in (("api/state", api_text), ("화면", page)):
                for needle in (str(ws), str(ws.resolve()), "/home/someone", "C:\\Users", "C:\\\\Users"):
                    if needle in text:
                        problems.append(f"{type(exc).__name__}: {label} 에 절대 경로 {needle!r} 가 있다")
    return problems


CASES = (
    ("1 프로필을 알면 원천에서 실시간 계산 · 저장소에 쓰지 않는다", case_live_values),
    ("2 원천 지문 — 같으면 다시 계산하지 않고 바뀌면 다시", case_fingerprint),
    ("3 프로필을 모르면 생성물", case_generated_fallback),
    ("4 CLI 서버의 위치는 프로필을 싣는다", case_where_for),
    ("5 브랜치 전환은 다시 계산한다", case_branch_switch),
    ("6 실시간 계산 실패는 보인다", case_failure_reported),
    ("7 roadmap 도 실시간 · 낡은 생성물 안 보임", case_roadmap_live),
    ("8 지문에 마일스톤 산출물", case_deliverable_fingerprint),
    ("9 실패 사유에 절대 경로 없음", case_error_has_no_paths),
)


def main() -> int:
    print("check_workbench_live — 워크벤치 진척의 실시간 값 (plan_workbench_spec §7.1)")
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
