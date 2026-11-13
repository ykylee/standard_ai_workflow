#!/usr/bin/env python3
"""주장 트리 계획 — `backlog-update` 의 린트 거부 · 전이 게이트 · 칸 고쳐 쓰기 (ADR-031, `core/claim_plan_spec.md` §3 · §4 · §8.6).

CLI 를 subprocess 로 끝까지 돌린다. 거부는 **파일을 하나도 바꾸지 않아야** 하므로 매번 전후를 비교한다.

1. 오류 규칙이면 `--apply` 가 쓰지 않는다 (rc 1 · `plan_lint_error`), 경고 규칙은 쓰고 `warnings` 에 규칙 번호를 싣는다
2. 열린 결정이 있으면 → `in_progress` 는 경고하며 통과하고 → `done` 은 거부된다 (rc 1 · `open_decisions` · 무변경)
3. `--decision-state D=answered:<v>` 뒤에는 → `done` 이 통과한다
4. `--decision-state` 는 `answered:<v>` 와 `proposed` 만 받는다 — `kept` · 선택지 밖의 값 · 모르는 결정은 거부
5. 손으로 `kept` 로 고친 칸은 계산값(`proposed`)으로 판정된다 — `done` 거부 · 무변경 · 불일치 경고, 다음 쓰기가 칸을 고친다
6. 오류 규칙을 어긴 task: 진행 메모는 통과하되 칸을 건드리지 않고, → `done` 은 열린 결정이 없어도 거부된다
7. 사유 없이 열린 결정을 걷는 교체는 거부, 사유가 있으면 걷힌다
8. `--plan-decision` 에 적힌 상태는 버려지고 새 결정은 `proposed` 다; 같은 결정을 다시 넣어도 겹치지 않는다
9. 결정이 없는 task 는 게이트와 무관하다 — 주장만 있어도 → `done` 이 통과한다
10. 4필드 Plan 절이 있는 옛 task 에 주장을 쓰면 절의 맨 앞에 들어간다
11. `plan-status` 는 계산값을 내고 아무것도 쓰지 않는다; `state.json` 의 `open_decisions` 는 열린 결정이 있을 때만 나온다
12. `done` 인데 열린 결정이 있는 task 를 `refresh-state` 와 `session-start` 가 warning 으로 싣는다 (옛 kit 의 우회)
"""
from __future__ import annotations

#: CLI 를 30 회 남짓 subprocess 로 띄운다 — 병렬 부하에서 기본 상한을 넘을 수 있다.
CHECK_TIMEOUT_S = 150

WATCHES = (
    "workflow-source/pyproject.toml",
    "workflow-source/workflow_kit/*",
    "workflow-source/skills/backlog-update/*",
)

import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SOURCE_ROOT))

from workflow_kit.common import plan_claims as pc  # noqa: E402
from workflow_kit.common.project_docs import task_label  # noqa: E402

BRANCH = "plan-gate"
SCRIPT = SOURCE_ROOT / "skills" / "backlog-update" / "scripts" / "run_backlog_update.py"
DECISIONS = task_label(pc.DECISIONS_KEY)
CLAIMS = task_label(pc.CLAIMS_KEY)
DECISION_ARG = "D1 [C1] 막는가? | default: block | options: block = 거부한다; warn = 경고만 낸다"

FAILURES: list[str] = []


def _record(name: str, problems: list[str]) -> None:
    if problems:
        FAILURES.append(name)
        print(f"  FAIL  {name}")
        for problem in problems:
            print(f"        - {problem}")
    else:
        print(f"  PASS  {name}")


def _env() -> dict[str, str]:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(SOURCE_ROOT)
    env["CODEX_WORKFLOW_BRANCH"] = BRANCH
    env["PYTHONIOENCODING"] = "utf-8"
    return env


def _workspace(td: str) -> Path:
    ws = Path(td)
    (ws / "docs").mkdir(parents=True)
    (ws / "docs" / "PROJECT_PROFILE.md").write_text("# Profile\n", encoding="utf-8")
    base = ws / "ai-workflow" / "memory" / "active" / BRANCH
    (base / "backlog" / "tasks").mkdir(parents=True)
    (base / "sessions").mkdir(parents=True)
    return ws


def _tasks(ws: Path) -> Path:
    return ws / "ai-workflow" / "memory" / "active" / BRANCH / "backlog" / "tasks"


def _snapshot(ws: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted((ws / "ai-workflow").rglob("*")):
        if path.is_file() and "telemetry" not in path.parts:
            digest.update(path.relative_to(ws).as_posix().encode())
            digest.update(path.read_bytes())
    return digest.hexdigest()


def _run(ws: Path, *extra: str) -> tuple[int, dict]:
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--project-profile-path", str(ws / "docs" / "PROJECT_PROFILE.md"),
         "--target-date", "2026-11-13", "--apply", *extra],
        capture_output=True, encoding="utf-8", errors="replace", check=False, env=_env(), cwd=str(ws),
    )
    try:
        return proc.returncode, json.loads(proc.stdout)
    except json.JSONDecodeError:
        raise AssertionError(f"JSON 이 아니다 (rc={proc.returncode}): {proc.stdout[-400:]} {proc.stderr[-800:]}") from None


def _tool(ws: Path, module: str, *args: str) -> tuple[int, str]:
    proc = subprocess.run(
        [sys.executable, "-m", module, *args],
        capture_output=True, encoding="utf-8", errors="replace", check=False, env=_env(), cwd=str(ws),
    )
    return proc.returncode, proc.stdout


def _create(ws: Path, *extra: str, name: str = "주장 있는 task") -> str:
    # 상태를 명시한다 — 빈 workspace 의 첫 create 는 daily backlog 를 만드는 연산이라 기본이 in_progress 다.
    rc, out = _run(ws, "--mode", "create", "--status", "planned", "--task-name", name, "--task-brief", "b",
                   "--done-criteria", "[C1] 닫히지 않는다", "--done-criteria", "[C2] 그대로다", *extra)
    if rc != 0:
        raise AssertionError(f"create 실패: {out}")
    return str(out["task_id"])


def _with_decision(ws: Path) -> str:
    return _create(ws, "--plan-claim", "C1 열린 결정이 남으면 닫히지 않는다",
                   "--plan-claim", "C2 옛 task 는 그대로 읽힌다", "--plan-decision", DECISION_ARG)


def _update(ws: Path, task_id: str, *extra: str) -> tuple[int, dict]:
    return _run(ws, "--mode", "update", "--task-id", task_id, "--task-name", "주장 있는 task", *extra)


def _text(ws: Path, task_id: str) -> str:
    return (_tasks(ws) / f"{task_id}.md").read_text(encoding="utf-8")


def _decision_lines(ws: Path, task_id: str) -> list[str]:
    return [line for line in _text(ws, task_id).splitlines() if line.startswith(f"- {DECISIONS}:")]


def _status(ws: Path, task_id: str) -> str:
    return next(line.split(":", 1)[1].strip() for line in _text(ws, task_id).splitlines() if line.startswith("status:"))


def _warned(out: dict, needle: str) -> bool:
    return any(needle in w for w in out.get("warnings", []))


def case_1_lint_error_blocks_write_warning_does_not() -> None:
    problems: list[str] = []
    with tempfile.TemporaryDirectory() as td:
        ws = _workspace(td)
        task_id = _with_decision(ws)
        before = _snapshot(ws)
        rc, out = _update(ws, task_id, "--plan-claim", "C2 같은 ID 를 또 쓴다")
        if rc != 1 or out.get("error_code") != "plan_lint_error" or "L2" not in out.get("error", ""):
            problems.append(f"L2 위반이 거부되지 않았다: rc={rc} {out.get('error_code')} {out.get('error')}")
        if _snapshot(ws) != before:
            problems.append("거부인데 파일이 바뀌었다")
        rc, out = _update(ws, task_id, "--plan-claim", "C3 " + "가" * 90)
        if rc != 0 or not _warned(out, "L3 C3"):
            problems.append(f"L3 경고가 쓰기를 막았거나 warnings 에 없다: rc={rc} {out.get('warnings')}")
        if f"- {CLAIMS}: C3 " not in _text(ws, task_id):
            problems.append("경고 규칙인데 쓰지 않았다")
    _record("case 1 (오류 규칙은 쓰지 않고, 경고 규칙은 쓴다)", problems)


def case_2_open_decision_gates_transitions() -> None:
    problems: list[str] = []
    with tempfile.TemporaryDirectory() as td:
        ws = _workspace(td)
        task_id = _with_decision(ws)
        rc, out = _update(ws, task_id, "--status", "in_progress")
        if rc != 0 or not _warned(out, "열린 결정 1건 (D1 proposed)") or _status(ws, task_id) != "in_progress":
            problems.append(f"→ in_progress: rc={rc} status={_status(ws, task_id)} {out.get('warnings')}")
        before = _snapshot(ws)
        rc, out = _update(ws, task_id, "--status", "done", "--validation-result", "v")
        if rc != 1 or out.get("error_code") != "open_decisions" or "D1" not in out.get("error", ""):
            problems.append(f"→ done 이 거부되지 않았다: rc={rc} {out.get('error_code')} {out.get('error')}")
        if _snapshot(ws) != before or _status(ws, task_id) != "in_progress":
            problems.append("거부인데 파일이 바뀌었다")
        rc, out = _update(ws, task_id, "--status", "blocked")
        if rc != 0 or _status(ws, task_id) != "blocked":
            problems.append(f"→ blocked 는 영향이 없어야 한다: rc={rc}")
    _record("case 2 (열린 결정 — in_progress 는 경고, done 은 거부 · 무변경)", problems)


def case_3_answered_then_done() -> None:
    problems: list[str] = []
    with tempfile.TemporaryDirectory() as td:
        ws = _workspace(td)
        task_id = _with_decision(ws)
        rc, _ = _update(ws, task_id, "--decision-state", "D1=answered:warn")
        if rc != 0 or not _decision_lines(ws, task_id)[0].endswith("| state: answered:warn"):
            problems.append(f"answered 가 적히지 않았다: {_decision_lines(ws, task_id)}")
        rc, out = _update(ws, task_id, "--status", "done", "--validation-result", "v")
        if rc != 0 or _status(ws, task_id) != "done":
            problems.append(f"답한 뒤의 done 이 통과하지 않았다: rc={rc} {out.get('error')}")
        rc, _ = _update(ws, task_id, "--decision-state", "D1=proposed")
        if rc != 0 or not _decision_lines(ws, task_id)[0].endswith("| state: proposed"):
            problems.append(f"answered 를 걷지 못했다: {_decision_lines(ws, task_id)}")
    _record("case 3 (answered 뒤에는 done 이 통과한다)", problems)


def case_4_decision_state_is_restricted() -> None:
    problems: list[str] = []
    with tempfile.TemporaryDirectory() as td:
        ws = _workspace(td)
        task_id = _with_decision(ws)
        before = _snapshot(ws)
        for value in ("D1=kept", "D1=changed:warn", "D1=unopened", "D1=disputed", "D1=answered:nope",
                      "D9=answered:warn", "D1"):
            rc, out = _update(ws, task_id, "--decision-state", value)
            if rc != 1 or out.get("error_code") != "decision_state_rejected":
                problems.append(f"`{value}` 가 거부되지 않았다: rc={rc} {out.get('error_code')}")
        if _snapshot(ws) != before:
            problems.append("거부인데 파일이 바뀌었다")
    _record("case 4 (--decision-state 는 answered:<v> 와 proposed 만)", problems)


def case_5_hand_edited_column_is_not_trusted() -> None:
    problems: list[str] = []
    with tempfile.TemporaryDirectory() as td:
        ws = _workspace(td)
        task_id = _with_decision(ws)
        path = _tasks(ws) / f"{task_id}.md"
        path.write_text(_text(ws, task_id).replace("state: proposed", "state: kept"), encoding="utf-8")
        before = _snapshot(ws)
        rc, out = _update(ws, task_id, "--status", "done", "--validation-result", "v")
        if rc != 1 or out.get("error_code") != "open_decisions":
            problems.append(f"손으로 고친 kept 로 done 이 통과했다: rc={rc} {out.get('error_code')}")
        if not _warned(out, "뒷받침 없는 상태를 되돌렸다: D1 kept → proposed"):
            problems.append(f"칸 불일치 경고가 없다: {out.get('warnings')}")
        if _snapshot(ws) != before:
            problems.append("거부인데 파일이 바뀌었다")
        rc, out = _update(ws, task_id, "--status", "in_progress")
        if rc != 0 or not _decision_lines(ws, task_id)[0].endswith("| state: proposed"):
            problems.append(f"통과한 쓰기가 칸을 고치지 않았다: {_decision_lines(ws, task_id)}")
    _record("case 5 (손 편집 칸 — 계산값으로 판정, 다음 쓰기가 고친다)", problems)


def case_6_error_state_file() -> None:
    problems: list[str] = []
    with tempfile.TemporaryDirectory() as td:
        ws = _workspace(td)
        task_id = _with_decision(ws)
        _update(ws, task_id, "--decision-state", "D1=answered:warn")
        path = _tasks(ws) / f"{task_id}.md"
        broken = _text(ws, task_id).replace(f"- {CLAIMS}: C2 ", f"- {CLAIMS}: C1 ")
        path.write_text(broken, encoding="utf-8")
        rc, out = _update(ws, task_id, "--progress-note", "메모")
        if rc != 0 or not _warned(out, "오류 규칙을 어긴 상태다"):
            problems.append(f"오류 상태 파일의 진행 메모: rc={rc} {out.get('warnings')}")
        if _decision_lines(ws, task_id) != [l for l in broken.splitlines() if l.startswith(f"- {DECISIONS}:")]:
            problems.append("오류 상태인데 결정 줄을 다시 적었다")
        before = _snapshot(ws)
        rc, out = _update(ws, task_id, "--status", "done", "--validation-result", "v")
        if rc != 1 or out.get("error_code") != "plan_lint_error":
            problems.append(f"모든 결정이 answered 인 오류 파일이 닫혔다: rc={rc} {out.get('error_code')}")
        if _snapshot(ws) != before:
            problems.append("거부인데 파일이 바뀌었다")
        rc, _ = _update(ws, task_id, "--status", "blocked")
        if rc != 0:
            problems.append("오류 상태 파일의 → blocked 는 통과해야 한다")
    _record("case 6 (오류 상태 task — 메모는 통과 · 칸 무변경, done 은 거부)", problems)


def case_7_removing_open_decisions_needs_a_note() -> None:
    problems: list[str] = []
    with tempfile.TemporaryDirectory() as td:
        ws = _workspace(td)
        task_id = _with_decision(ws)
        before = _snapshot(ws)
        rc, out = _update(ws, task_id, "--replace-field", "plan_decisions")
        if rc != 1 or out.get("error_code") != "decision_removal_needs_note":
            problems.append(f"사유 없는 제거가 통과했다: rc={rc} {out.get('error_code')}")
        if _snapshot(ws) != before:
            problems.append("거부인데 파일이 바뀌었다")
        rc, _ = _update(ws, task_id, "--replace-field", "plan_decisions", "--progress-note", "소유자와 대화로 확인 — 결정 불필요")
        if rc != 0 or _decision_lines(ws, task_id):
            problems.append(f"사유가 있는데 걷히지 않았다: rc={rc} {_decision_lines(ws, task_id)}")
    _record("case 7 (열린 결정을 걷으려면 사유가 있어야 한다)", problems)


def case_8_new_decisions_start_proposed() -> None:
    problems: list[str] = []
    with tempfile.TemporaryDirectory() as td:
        ws = _workspace(td)
        task_id = _create(ws, "--plan-claim", "C1 하나를 한다", "--plan-claim", "C2 둘을 한다",
                          "--plan-decision", DECISION_ARG.replace("default:", "기본:").replace("options:", "선택:") + " | 상태: kept")
        lines = _decision_lines(ws, task_id)
        if lines != [f"- {DECISIONS}: {DECISION_ARG} | state: proposed"]:
            problems.append(f"새 결정이 proposed · 정본 표기가 아니다: {lines}")
        _update(ws, task_id, "--decision-state", "D1=answered:warn")
        rc, out = _update(ws, task_id, "--plan-decision", DECISION_ARG)
        after = _decision_lines(ws, task_id)
        if rc != 0 or len(after) != 1 or not after[0].endswith("| state: answered:warn"):
            problems.append(f"같은 결정을 다시 넣자 겹치거나 답이 사라졌다: rc={rc} {after}")
    _record("case 8 (새 결정은 proposed, 같은 결정은 겹치지 않는다)", problems)


def case_9_tasks_without_decisions_are_unaffected() -> None:
    problems: list[str] = []
    with tempfile.TemporaryDirectory() as td:
        ws = _workspace(td)
        plain = _create(ws, name="주장 없는 task")
        rc, out = _update(ws, plain, "--status", "done", "--validation-result", "v")
        if rc != 0 or _status(ws, plain) != "done":
            problems.append(f"주장 없는 task 의 done: rc={rc} {out.get('error')}")
        if any(m in _text(ws, plain) for m in (f"- {CLAIMS}", f"- {DECISIONS}")):
            problems.append("주장 없는 task 에 주장 · 결정 줄이 생겼다")
        claims_only = _create(ws, "--plan-claim", "C1 하나를 한다", "--plan-claim", "C2 둘을 한다", name="주장만")
        rc, out = _update(ws, claims_only, "--status", "done", "--validation-result", "v")
        if rc != 0 or _status(ws, claims_only) != "done":
            problems.append(f"결정 없는 task 의 done 이 막혔다: rc={rc} {out.get('error')}")
        many = _create(ws, "--plan-file", "a.py", "--plan-file", "b.py", "--plan-file", "c.py",
                       "--plan-file", "ai-workflow/memory/x.md", name="파일 셋")
        rc, out = _update(ws, many, "--status", "in_progress")
        if not _warned(out, "Claims 가 없다 — 바뀌는 파일 3개 (R2.3)"):
            problems.append(f"Claims 권고가 없다: {out.get('warnings')}")
    _record("case 9 (결정 없는 task 는 게이트와 무관, Claims 권고)", problems)


LEGACY = """---
id: {task_id}
status: in_progress
created_at: 2026-10-01
source_anchor: generic-{anchor}
source_path: backlog/2026-10-01.md
kind: generic
---

# {task_id} — 옛 task

## 📝 Description

- Status: in_progress
- Description: 옛 본문
- Completion criteria: 옛 기준

## 🧭 Plan

- Files that change: a.py
- Order of work: 1. x
- Plan risks:
- Proof: p

## 🛠️ Implementation / Content

- Progress: 옛 진행

## ✅ Outcome

- Result:
"""


def case_10_claims_go_first_in_existing_plan_section() -> None:
    problems: list[str] = []
    with tempfile.TemporaryDirectory() as td:
        ws = _workspace(td)
        task_id = "TASK-2026-10-01-plan-gate-001"
        (_tasks(ws) / f"{task_id}.md").write_text(
            LEGACY.format(task_id=task_id, anchor=task_id.lower()), encoding="utf-8")
        rc, out = _run(ws, "--mode", "update", "--task-id", task_id, "--task-name", "옛 task",
                       "--plan-claim", "C1 하나를 한다", "--plan-decision", DECISION_ARG)
        text = _text(ws, task_id)
        plan = [l for l in text.split("## 🧭 Plan", 1)[1].split("\n## ", 1)[0].splitlines() if l.startswith("- ")]
        if rc != 0 or [l.split(":", 1)[0] for l in plan[:3]] != [f"- {CLAIMS}", f"- {DECISIONS}", "- Files that change"]:
            problems.append(f"주장 · 결정이 절의 맨 앞에 없다: rc={rc} {plan} {out.get('warnings')}")
        if _warned(out, "찾지 못해 반영하지 못했다"):
            problems.append("라벨 줄이 없어 값이 버려졌다")
        if "옛 본문" not in text or "- Order of work: 1. x" not in text:
            problems.append("기존 내용이 사라졌다")
    _record("case 10 (4필드 Plan 절에 주장 · 결정이 맨 앞으로 들어간다)", problems)


def case_11_plan_status_and_state_json() -> None:
    problems: list[str] = []
    with tempfile.TemporaryDirectory() as td:
        ws = _workspace(td)
        plain = _create(ws, name="주장 없는 task")
        state_path = ws / "ai-workflow" / "memory" / "active" / BRANCH / "state.json"
        if state_path.is_file() and "open_decisions" in json.loads(state_path.read_text(encoding="utf-8")):
            problems.append("열린 결정이 없는데 state.json 에 open_decisions 가 있다")
        task_id = _with_decision(ws)
        _update(ws, task_id, "--status", "in_progress")
        state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.is_file() else {}
        if state.get("open_decisions") != {task_id: 1}:
            problems.append(f"state.json open_decisions: {state.get('open_decisions')}")
        before = _snapshot(ws)
        rc, out = _tool(ws, "workflow_kit.tools.plan_status", "--task", task_id)
        data = json.loads(out) if rc == 0 else {}
        if rc != 0 or data.get("open_decisions") != ["D1"] or [c["id"] for c in data.get("claims", [])] != ["C1", "C2"]:
            problems.append(f"plan-status json: rc={rc} {out[:200]}")
        if data and (data["claims"][0]["criteria"], data["claims"][1]["criteria"]) != ([1], [2]):
            problems.append(f"인용 묶음: {data['claims']}")
        rc, md = _tool(ws, "workflow_kit.tools.plan_status", "--task", task_id, "--format", "md")
        if rc != 0 or not md.startswith("### 주장별") or "- 열린 결정: D1 (proposed)" not in md:
            problems.append(f"plan-status md: rc={rc} {md[:200]}")
        rc, md = _tool(ws, "workflow_kit.tools.plan_status", "--task", plain, "--format", "md")
        if rc != 0 or md.strip():
            problems.append(f"주장 없는 task 는 절을 내지 않아야 한다: rc={rc} {md!r}")
        rc, _ = _tool(ws, "workflow_kit.tools.plan_status", "--task", task_id, "--tas", task_id)
        if rc == 0:
            problems.append("모르는(축약된) 인자를 받아들였다")
        if _snapshot(ws) != before:
            problems.append("plan-status 가 파일을 바꿨다")
        _update(ws, task_id, "--decision-state", "D1=answered:block")
        state = json.loads(state_path.read_text(encoding="utf-8"))
        if "open_decisions" in state:
            problems.append(f"결정을 닫았는데 open_decisions 가 남았다: {state['open_decisions']}")
    _record("case 11 (plan-status 는 읽기 전용, open_decisions 는 있을 때만)", problems)


def case_12_bypass_is_reported() -> None:
    problems: list[str] = []
    with tempfile.TemporaryDirectory() as td:
        ws = _workspace(td)
        task_id = _with_decision(ws)
        path = _tasks(ws) / f"{task_id}.md"
        # 게이트를 모르는 kit 이 닫은 모양 — frontmatter 만 done 이다.
        path.write_text(_text(ws, task_id).replace("status: planned", "status: done", 1), encoding="utf-8")
        handoff = ws / "ai-workflow" / "memory" / "active" / BRANCH / "session_handoff.md"
        if not handoff.is_file():
            handoff.write_text("# Session Handoff\n", encoding="utf-8")
        rc, out = _tool(ws, "workflow_kit.tools.refresh_state",
                        "--project-profile-path", str(ws / "docs" / "PROJECT_PROFILE.md"))
        try:
            warnings = json.loads(out).get("warnings", [])
        except json.JSONDecodeError:
            warnings = []
        expected = f"done 인데 열린 결정이 있다: {task_id} (D1)"
        if expected not in warnings:
            problems.append(f"우회가 보고되지 않았다: rc={rc} {warnings} {out[:200]}")
        rc, out = _tool(ws, "workflow_kit.tools.session_start",
                        "--project-profile-path", str(ws / "docs" / "PROJECT_PROFILE.md"))
        try:
            session_warnings = json.loads(out).get("warnings", [])
        except json.JSONDecodeError:
            session_warnings = []
        if expected not in session_warnings:
            problems.append(f"session-start 가 우회를 보고하지 않았다: rc={rc} {session_warnings} {out[:200]}")
        if any("결정 상태 판정 실패" in w for w in session_warnings):
            problems.append(f"session-start 의 결정 상태 판정이 예외로 떨어졌다: {session_warnings}")
        if "status: done" not in _text(ws, task_id):
            problems.append("읽기 전용 판정이 task 를 고쳤다")
    _record("case 12 (done 인데 열린 결정 — refresh-state · session-start warning)", problems)


CASES = [
    case_1_lint_error_blocks_write_warning_does_not,
    case_2_open_decision_gates_transitions,
    case_3_answered_then_done,
    case_4_decision_state_is_restricted,
    case_5_hand_edited_column_is_not_trusted,
    case_6_error_state_file,
    case_7_removing_open_decisions_needs_a_note,
    case_8_new_decisions_start_proposed,
    case_9_tasks_without_decisions_are_unaffected,
    case_10_claims_go_first_in_existing_plan_section,
    case_11_plan_status_and_state_json,
    case_12_bypass_is_reported,
]


def main() -> int:
    print("=== 주장 트리 계획 — backlog-update 게이트 (ADR-031) ===")
    for fn in CASES:
        try:
            fn()
        except Exception as exc:  # noqa: BLE001
            FAILURES.append(fn.__name__)
            print(f"  FAIL  {fn.__name__} — 예외 {type(exc).__name__}: {exc}")
    if FAILURES:
        print(f"\n{len(FAILURES)} fail: {FAILURES}")
        return 1
    print(f"\n{len(CASES)}/{len(CASES)} PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
