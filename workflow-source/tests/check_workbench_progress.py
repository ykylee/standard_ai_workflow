#!/usr/bin/env python3
"""작업 중 진행 기록 — 워크벤치의 '지금 하는 일' (`core/plan_workbench_spec.md` §7.1, TASK-2026-11-16-main-009).

1. `backlog-update --mode update --progress-note` 는 시각(`YYYY-MM-DD HH:MM`)을 앞에 붙여 Progress 한 줄을 바꾼다;
   이미 백틱 시각으로 시작한 노트는 그대로다
2. 워크벤치 — `api/state` 의 `plans[].progress` · `tasks.in_progress[].progress` 가 task 파일 값과 같고,
   진척 화면의 계획 카드 · 작업 보드에 '지금' 과 글이 보인다; 노트가 바뀌면 화면 지문(`data-version`)이 바뀐다
3. 단계마다 기록하라는 규칙이 backlog-update 스킬(SKILL.md)과 이 저장소 CLAUDE.md 에 있다
"""

from __future__ import annotations

#: 이 검사의 입력 표면 (spec `core/test_impact_tiering_spec.md` §2).
WATCHES = (
    "workflow-source/pyproject.toml",
    "workflow-source/workflow_kit/*",
    "workflow-source/tests/_workbench_fixture.py",
    "plugin/skills/backlog-update/SKILL.md",
    "CLAUDE.md",
)

import json
import re
import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _workbench_fixture as fx  # noqa: E402

FAILURES: list[str] = []
REPO_ROOT = Path(__file__).resolve().parents[2]
STAMPED = re.compile(r"^- Progress: `\d{4}-\d{2}-\d{2} \d{2}:\d{2}` (.*)$", re.M)


def _record(name: str, problems: list[str]) -> None:
    if problems:
        FAILURES.append(name)
        print(f"  FAIL  {name}")
        for problem in problems[:12]:
            print(f"        - {problem}")
    else:
        print(f"  PASS  {name}")


def _task_text(ws: Path, task_id: str) -> str:
    return (fx.branch_dir(ws) / "backlog" / "tasks" / f"{task_id}.md").read_text(encoding="utf-8")


def _note(ws: Path, task_id: str, note: str) -> None:
    fx.backlog(ws, "--mode", "update", "--task-id", task_id, "--task-name", "x", "--progress-note", note)


def case_stamp() -> list[str]:
    problems: list[str] = []
    with fx.temp_workspace("wb-progress-1-") as td:
        ws = fx.make_workspace(td)
        task_id = fx.create_task(ws)
        _note(ws, task_id, "검사를 돌리는 중")
        match = STAMPED.search(_task_text(ws, task_id))
        if not match or match.group(1) != "검사를 돌리는 중":
            problems.append(f"진행 노트에 시각이 붙지 않았거나 글이 바뀌었다: {match.group(0) if match else None}")
        _note(ws, task_id, "`check_x.py` 를 돌리는 중")
        match = STAMPED.search(_task_text(ws, task_id))
        if not match or match.group(1) != "`check_x.py` 를 돌리는 중":
            problems.append("백틱으로 시작하지만 시각이 아닌 노트에 시각을 붙이지 않았다")
        _note(ws, task_id, "`2026-01-02 03:04` 손으로 시각을 적었다")
        if "- Progress: `2026-01-02 03:04` 손으로 시각을 적었다" not in _task_text(ws, task_id):
            problems.append("이미 시각으로 시작한 노트에 시각을 또 붙였다")
    return problems


def case_workbench_shows() -> list[str]:
    problems: list[str] = []
    with fx.temp_workspace("wb-progress-2-") as td:
        ws = fx.make_workspace(td)
        task_id = fx.create_task(ws)
        fx.backlog(ws, "--mode", "update", "--task-id", task_id, "--task-name", "x", "--status", "in_progress")
        _note(ws, task_id, "verifier 를 기다리는 중")
        (fx.branch_dir(ws) / "state.json").write_text(json.dumps(
            {"schema_version": 1, "generated_at": "2026-11-16T00:00:00",
             "backlog": {"in_progress_items": [f"{task_id} — 응답을 받는 task"]}}, ensure_ascii=False), encoding="utf-8")
        with fx.running(ws, tokens=(), open_name="owner") as srv:
            api = json.loads(fx.request(srv.port, "GET", "/api/state").text)
            page = fx.request(srv.port, "GET", "/").text
            plan = next((p for p in api["plans"] if p["task"] == task_id), {})
            board = next((i for i in api["tasks"]["in_progress"] or [] if i["id"] == task_id), {})
            for label, entry in (("plans", plan), ("tasks.in_progress", board)):
                progress = entry.get("progress") or {}
                if progress.get("text") != "verifier 를 기다리는 중" or not re.match(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}$",
                                                                                str(progress.get("at"))):
                    problems.append(f"api/state {label} 의 progress 가 task 파일과 다르다: {progress}")
            if page.count("verifier 를 기다리는 중") < 2 or "<b>지금</b>" not in page:
                problems.append("계획 카드 · 작업 보드에 '지금 하는 일' 이 보이지 않는다")
            # 진행 노트는 task 파일의 글이다 — 마크업은 글자로 (스펙 §1-3).
            _note(ws, task_id, "<script>alert(1)</script> & <img src=x onerror=1>")
            escaped = fx.request(srv.port, "GET", "/").text
            if "<script>alert(1)" in escaped or "<img src=x" in escaped or "&lt;script&gt;alert(1)" not in escaped:
                problems.append("진행 노트의 마크업이 이스케이프되지 않았다")
            # 차단 항목에도 '지금' 이 붙는다.
            (fx.branch_dir(ws) / "state.json").write_text(json.dumps(
                {"schema_version": 1, "generated_at": "2026-11-16T00:00:00",
                 "backlog": {"in_progress_items": [], "blocked_items": [f"{task_id} — 막힌 task"]}}, ensure_ascii=False),
                encoding="utf-8")
            blocked = json.loads(fx.request(srv.port, "GET", "/api/state").text)["tasks"]["blocked"] or []
            if not blocked or "alert(1)" not in str((blocked[0].get("progress") or {}).get("text")):
                problems.append(f"차단 항목에 '지금 하는 일' 이 붙지 않았다: {blocked}")
            page = fx.request(srv.port, "GET", "/").text
            before = re.search(r'data-version="([0-9a-f]+)"', page)
            _note(ws, task_id, "커밋하는 중")
            after = re.search(r'data-version="([0-9a-f]+)"', fx.request(srv.port, "GET", "/").text)
            if not before or not after or before.group(1) == after.group(1):
                problems.append("진행 노트가 바뀌었는데 화면 지문이 그대로다 — 자동 새로고침이 일어나지 않는다")
    return problems


def case_rules() -> list[str]:
    problems: list[str] = []
    skill = (REPO_ROOT / "plugin" / "skills" / "backlog-update" / "SKILL.md").read_text(encoding="utf-8")
    if "Record progress as you work" not in skill or "--progress-note" not in skill:
        problems.append("backlog-update 스킬에 단계마다 진행을 기록하라는 규칙이 없다")
    claude = (REPO_ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    if not re.search(r"작업 중: .*--progress-note", claude):
        problems.append("CLAUDE.md 에 작업 중 진행 기록 규칙이 없다")
    return problems


CASES = (
    ("1 progress-note 에 시각 · 손으로 적은 시각은 그대로", case_stamp),
    ("2 워크벤치 '지금 하는 일' — api · 계획 카드 · 작업 보드 · 지문", case_workbench_shows),
    ("3 단계마다 기록 규칙 — 스킬 · CLAUDE.md", case_rules),
)


def main() -> int:
    print("check_workbench_progress — 작업 중 진행 기록 (plan_workbench_spec §7.1)")
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
