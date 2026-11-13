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
13. dry-run 도 같은 판정을 낸다 — 오류 규칙 · 열린 결정의 거부가 `--apply` 없이도 rc 1 이다
14. 문구 — 경고와 거부의 문장이 스펙 §4 와 글자까지 같다
15. 사유는 명시한 `--progress-note` 만이다 — `--task-brief` 로는 열린 결정을 걷지 못한다
16. `plan-status` · 우회 검출 · `open_decisions` 의 범위 — 계산값으로 판정하고, 진행 중 · 차단 · 계획만 세고, done 만 우회로 본다
17. L5 는 git 저장소에서 실제 HEAD 를 읽는다
18. 겹친 사유 — 검증 결과 없는 done 과 열린 결정이 겹치면 거부가 이기고 강등 사유도 싣는다
19. 받은편지함 — 결정이 있는 task 에 미반영 응답이 있으면 → `done` 거부 (`pending_plan_responses`), 겹친 사유의 순서,
    결정이 없는 task 는 무관, `backlog-update` · `session-start` · `plan-status` 의 미반영 보고, 지문을 바꾸는 쓰기의 경고
20. 보관 응답으로 판정한다 — `kept` · `changed` 는 닫히고 `unopened` · `disputed` 는 거부되며, 지문이 바뀌면 옛 응답은 세지 않는다
"""
from __future__ import annotations

#: CLI 를 60 회 남짓 subprocess 로 띄운다 — 병렬 부하에서 기본 상한을 넘을 수 있다.
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
from workflow_kit.common import plan_responses as pr  # noqa: E402
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


def _run(ws: Path, *extra: str, apply: bool = True) -> tuple[int, dict]:
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--project-profile-path", str(ws / "docs" / "PROJECT_PROFILE.md"),
         "--target-date", "2026-11-13", *(("--apply",) if apply else ()), *extra],
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


def _update(ws: Path, task_id: str, *extra: str, apply: bool = True) -> tuple[int, dict]:
    return _run(ws, "--mode", "update", "--task-id", task_id, "--task-name", "주장 있는 task", *extra, apply=apply)


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
        # L9 — 묶음이 나뉜 파일에 주장을 쓰려 하면 거부된다.
        path = _tasks(ws) / f"{task_id}.md"
        split = _text(ws, task_id).replace("- Files that change:", f"- Files that change:\n- {CLAIMS}: C4 떨어진 주장", 1)
        path.write_text(split, encoding="utf-8")
        before = _snapshot(ws)
        rc, out = _update(ws, task_id, "--plan-claim", "C5 하나 더")
        if rc != 1 or out.get("error_code") != "plan_lint_error" or "L9" not in out.get("error", ""):
            problems.append(f"나뉜 묶음(L9)이 쓰기를 막지 않았다: rc={rc} {out.get('error_code')} {out.get('error')}")
        if _snapshot(ws) != before:
            problems.append("거부인데 파일이 바뀌었다")
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
        rc, out = _run(ws, "--mode", "create", "--status", "planned", "--task-name", "상태를 적어 넣음", "--task-brief", "b",
                       "--done-criteria", "[C1] 기준", "--plan-claim", "C1 하나를 한다",
                       "--plan-decision", DECISION_ARG + " | state: answered:warn")
        if rc != 0 or not _warned(out, "--plan-decision D1: 줄에 적힌 상태를 버렸다"):
            problems.append(f"상태를 버린 것을 알리지 않았다: rc={rc} {out.get('warnings')}")
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
        rc, out = _run(ws, "--mode", "create", "--status", "planned", "--task-name", "파일 셋 (create)", "--task-brief", "b",
                       "--plan-file", "a.py", "--plan-file", "b.py", "--plan-file", "c.py")
        if rc != 0 or not _warned(out, "Claims 가 없다 — 바뀌는 파일 3개 (R2.3)"):
            problems.append(f"create 의 Claims 권고가 없다: rc={rc} {out.get('warnings')}")
        rc, out = _run(ws, "--mode", "create", "--status", "planned", "--task-name", "파일 둘", "--task-brief", "b",
                       "--plan-file", "a.py", "--plan-file", "b.py", "--plan-file", "ai-workflow/memory/x.md")
        if _warned(out, "Claims 가 없다"):
            problems.append(f"메타 경로를 빼면 둘인데 권고가 났다: {out.get('warnings')}")
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
        state_path = ws / "ai-workflow" / "memory" / "active" / BRANCH / "state.json"
        if "open_decisions" in json.loads(state_path.read_text(encoding="utf-8")):
            problems.append("done task 의 열린 결정을 state.json open_decisions 에 셌다 (진행 중 · 차단 · 계획만 센다)")
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


def case_13_dry_run_gives_the_same_verdict() -> None:
    problems: list[str] = []
    with tempfile.TemporaryDirectory() as td:
        ws = _workspace(td)
        task_id = _with_decision(ws)
        before = _snapshot(ws)
        rc, out = _update(ws, task_id, "--plan-claim", "C2 같은 ID 를 또 쓴다", apply=False)
        if rc != 1 or out.get("error_code") != "plan_lint_error":
            problems.append(f"dry-run 이 오류 규칙을 거부하지 않았다: rc={rc} {out.get('error_code')}")
        rc, out = _update(ws, task_id, "--status", "done", "--validation-result", "v", apply=False)
        if rc != 1 or out.get("error_code") != "open_decisions":
            problems.append(f"dry-run 이 열린 결정의 done 을 거부하지 않았다: rc={rc} {out.get('error_code')}")
        rc, out = _run(ws, "--mode", "create", "--status", "done", "--validation-result", "v", "--task-name", "닫힌 채 생성",
                       "--task-brief", "b", "--plan-claim", "C1 하나를 한다", "--plan-decision", DECISION_ARG, apply=False)
        if rc != 1 or out.get("error_code") != "open_decisions":
            problems.append(f"열린 결정이 있는 task 를 done 으로 create 할 수 있다: rc={rc} {out.get('error_code')}")
        if _snapshot(ws) != before:
            problems.append("dry-run 이 파일을 바꿨다")
    _record("case 13 (dry-run 도 같은 판정)", problems)


def case_14_messages_match_the_spec() -> None:
    problems: list[str] = []
    with tempfile.TemporaryDirectory() as td:
        ws = _workspace(td)
        task_id = _with_decision(ws)
        _, out = _update(ws, task_id, "--status", "in_progress")
        warn = "열린 결정 1건 (D1 proposed) — 묻지 않았거나, 열리지 않았거나, 답이 갈렸다. 기본값은 동의가 아니다."
        if warn not in out.get("warnings", []):
            problems.append(f"in_progress 경고 문구: {out.get('warnings')}")
        _, out = _update(ws, task_id, "--status", "done", "--validation-result", "v")
        refusal = ("done 거부: 열린 결정 1건 (D1). --decision-state D1=answered:<value> 로 답을 기록하거나, "
                   "--replace-field plan_decisions 로 결정을 걷고 사유를 Progress 에 남긴다.")
        if out.get("error") != refusal:
            problems.append(f"done 거부 문구: {out.get('error')!r}")
        # 전이가 아닌 update 는 린트 경고를 되풀이하지 않는다.
        _update(ws, task_id, "--replace-field", "done_criteria", "--done-criteria", "인용 없는 기준")
        _, out = _update(ws, task_id, "--status", "in_progress")
        if any(w.startswith("L7") for w in out.get("warnings", [])):
            problems.append(f"같은 상태를 다시 줬는데 린트 경고가 되풀이됐다: {out.get('warnings')}")
        _, out = _update(ws, task_id, "--progress-note", "메모")
        if any(w.startswith("L7") for w in out.get("warnings", [])):
            problems.append(f"진행 메모에 린트 경고가 붙었다: {out.get('warnings')}")
    _record("case 14 (경고 · 거부 문구가 스펙과 같다, 되풀이하지 않는다)", problems)


def case_15_brief_is_not_a_removal_note() -> None:
    problems: list[str] = []
    with tempfile.TemporaryDirectory() as td:
        ws = _workspace(td)
        task_id = _with_decision(ws)
        before = _snapshot(ws)
        rc, out = _update(ws, task_id, "--replace-field", "plan_decisions", "--task-brief", "brief 로 채운 진행 줄")
        if rc != 1 or out.get("error_code") != "decision_removal_needs_note":
            problems.append(f"--task-brief 로 열린 결정이 걷혔다: rc={rc} {out.get('error_code')}")
        rc, out = _update(ws, task_id, "--replace-field", "plan_decisions", "--progress-note", "   ",
                          "--status", "done", "--validation-result", "v")
        if rc != 1 or out.get("error_code") != "decision_removal_needs_note":
            problems.append(f"공백뿐인 사유로 열린 결정이 걷히고 닫혔다: rc={rc} {out.get('error_code')}")
        if _snapshot(ws) != before:
            problems.append("거부인데 파일이 바뀌었다")
        # git 밖에서는 위치를 확인하지 못한다 — 그 사실을 warnings 로 남긴다 (통과로 세지 않는다).
        rc, out = _update(ws, task_id, "--plan-claim", "C1.1 둘을 한다", "--plan-claim", "C1.1.1 @ a.py:1 · f()")
        if rc != 0 or not _warned(out, "git 밖이라 위치 1건을 확인하지 못했다"):
            problems.append(f"git 밖의 L5 건너뜀을 알리지 않았다: rc={rc} {out.get('warnings')}")
        # 같은 ID 로 task 를 다시 만드는 create 가 열린 결정을 덮어쓰고 닫지 못한다.
        before = _snapshot(ws)
        rc, out = _run(ws, "--mode", "create", "--task-id", task_id, "--status", "done", "--validation-result", "v",
                       "--task-name", "덮어쓰기", "--task-brief", "b")
        if rc != 1 or out.get("error_code") != "decision_removal_needs_note":
            problems.append(f"create 로 열린 결정이 있는 task 를 덮어쓰고 닫았다: rc={rc} {out.get('error_code')}")
        if _snapshot(ws) != before:
            problems.append("거부인데 파일이 바뀌었다")
        rc, out = _update(ws, task_id, "--replace-field", "plan_decisions", "--progress-note", "\u200b\ufeff",
                          "--status", "done", "--validation-result", "v")
        if rc != 1 or out.get("error_code") != "decision_removal_needs_note":
            problems.append(f"폭 없는 문자뿐인 사유로 닫혔다: rc={rc} {out.get('error_code')}")
        # 눈에 보이는 글자 · 숫자가 없으면 사유가 아니다 — 빈칸으로 찍히는 채움 문자, 기호뿐인 값.
        for note in ("\u3164", "\u115f", "\u1160", "\uffa0", "\U00013441", "\U00013442", "\u3164 \u200b", "-", ".", "—"):
            rc, out = _update(ws, task_id, "--replace-field", "plan_decisions", "--progress-note", note,
                              "--status", "done", "--validation-result", "v")
            if rc != 1 or out.get("error_code") != "decision_removal_needs_note":
                problems.append(f"보이지 않는 사유 {note!r} 로 닫혔다: rc={rc} {out.get('error_code')}")
        # 다시 만드는 create 는 닫지 않을 때도 사유가 필요하다 — planned 로 덮어쓴 뒤 닫는 두 단계 길.
        rc, out = _run(ws, "--mode", "create", "--task-id", task_id, "--status", "planned",
                       "--task-name", "덮어쓰기", "--task-brief", "b")
        if rc != 1 or out.get("error_code") != "decision_removal_needs_note":
            problems.append(f"create(planned) 로 열린 결정을 사유 없이 덮어썼다: rc={rc} {out.get('error_code')}")
        if _snapshot(ws) != before:
            problems.append("거부인데 파일이 바뀌었다 (사유 판정)")
        # 숫자 한 글자 · 글자 한 글자는 사유다 (흔적이지 방벽이 아니다).
        for note in ("1", "가"):
            with tempfile.TemporaryDirectory() as td2:
                ws2 = _workspace(td2)
                tid2 = _with_decision(ws2)
                rc, out = _update(ws2, tid2, "--replace-field", "plan_decisions", "--progress-note", note)
                if rc != 0 or _decision_lines(ws2, tid2):
                    problems.append(f"글자 · 숫자가 있는 사유 {note!r} 가 거부됐다: rc={rc} {out.get('error_code')}")
    # 열린 결정 둘 중 하나만 걷어도 사유가 필요하다 — 남은 것이 있다고 통과하지 않는다.
    with tempfile.TemporaryDirectory() as td:
        ws = _workspace(td)
        second = DECISION_ARG.replace("D1 [C1]", "D2 [C2]", 1)
        task_id = _create(ws, "--plan-claim", "C1 열린 결정이 남으면 닫히지 않는다",
                          "--plan-claim", "C2 옛 task 는 그대로 읽힌다",
                          "--plan-decision", DECISION_ARG, "--plan-decision", second)
        before = _snapshot(ws)
        rc, out = _update(ws, task_id, "--replace-field", "plan_decisions", "--plan-decision", DECISION_ARG)
        if rc != 1 or out.get("error_code") != "decision_removal_needs_note" or "D2" not in str(out.get("error")):
            problems.append(f"열린 결정 일부를 사유 없이 걷었다: rc={rc} {out.get('error_code')} {out.get('error')}")
        if _snapshot(ws) != before:
            problems.append("거부인데 파일이 바뀌었다 (일부 제거)")
    # 다시 만드는 create 도 create 다 — 주장 없이 파일 셋이면 R2.3 권고가 나온다.
    with tempfile.TemporaryDirectory() as td:
        ws = _workspace(td)
        files = ("--plan-file", "a.py", "--plan-file", "b.py", "--plan-file", "c.py")
        task_id = _create(ws, *files)
        rc, out = _run(ws, "--mode", "create", "--task-id", task_id, "--status", "planned",
                       "--task-name", "다시", "--task-brief", "b", *files)
        if rc != 0 or not _warned(out, "(R2.3)"):
            problems.append(f"다시 만드는 create 에서 R2.3 권고가 사라졌다: rc={rc} {out.get('warnings')}")
    _record("case 15 (사유는 명시한 --progress-note 만 · git 밖의 L5 보고 · create 덮어쓰기)", problems)


def case_16_computed_values_and_scopes() -> None:
    problems: list[str] = []
    with tempfile.TemporaryDirectory() as td:
        ws = _workspace(td)
        base = ws / "ai-workflow" / "memory" / "active" / BRANCH
        state_path = base / "state.json"
        planned = _with_decision(ws)
        state = json.loads(state_path.read_text(encoding="utf-8"))
        if state.get("open_decisions") != {planned: 1}:
            problems.append(f"planned task 의 열린 결정을 세지 않았다: {state.get('open_decisions')}")
        two = _create(ws, "--plan-claim", "C1 하나를 한다", "--plan-claim", "C2 둘을 한다", "--plan-claim", "C3 재지 않는다",
                      "--plan-decision", DECISION_ARG,
                      "--plan-decision", "D2 [C2] 둘째 질문 | default: a | options: a = 가; b = 나", name="결정 둘")
        state = json.loads(state_path.read_text(encoding="utf-8"))
        if state.get("open_decisions", {}).get(two) != 2:
            problems.append(f"열린 결정의 수: {state.get('open_decisions')}")
        _, out = _tool(ws, "workflow_kit.tools.plan_status", "--task", two)
        flags = [(c["id"], c["unmeasured"]) for c in json.loads(out).get("claims", [])]
        if flags != [("C1", False), ("C2", False), ("C3", True)]:
            problems.append(f"plan-status 의 재지 않는 주장 표시: {flags}")
        _update(ws, two, "--decision-state", "D1=answered:warn", "--decision-state", "D2=answered:a")
        state = json.loads(state_path.read_text(encoding="utf-8"))
        if state.get("open_decisions") != {planned: 1}:
            problems.append(f"둘 다 답한 뒤의 open_decisions: {state.get('open_decisions')}")
        # 손으로 kept 로 고친 칸 — plan-status 는 계산값을 내고 칸도 함께 보인다.
        path = _tasks(ws) / f"{planned}.md"
        path.write_text(_text(ws, planned).replace("state: proposed", "state: kept"), encoding="utf-8")
        rc, out = _tool(ws, "workflow_kit.tools.plan_status", "--task", planned)
        data = json.loads(out) if rc == 0 else {}
        decision = (data.get("decisions") or [{}])[0]
        if (decision.get("state"), decision.get("column_state"), decision.get("open")) != ("proposed", "kept", True):
            problems.append(f"plan-status 가 칸으로 판정했다: {decision}")
        expected_digest = pc.plan_digest(pc.parse_plan(_text(ws, planned).splitlines()))
        if data.get("plan_digest") != expected_digest:
            problems.append(f"plan-status 의 지문: {data.get('plan_digest')}")
        _, md = _tool(ws, "workflow_kit.tools.plan_status", "--task", planned, "--format", "md")
        if "- 열린 결정: D1 (proposed)" not in md:
            problems.append(f"md 의 열린 결정 상태가 계산값이 아니다: {md[-80:]!r}")
        # open_decisions 는 칸 기준이다 (생성기의 입력은 task 파일뿐) — 칸이 kept 면 세지 않는다.
        _tool(ws, "workflow_kit.tools.refresh_state", "--project-profile-path", str(ws / "docs" / "PROJECT_PROFILE.md"))
        if "open_decisions" in json.loads(state_path.read_text(encoding="utf-8")):
            problems.append("open_decisions 가 칸이 아니라 계산값으로 셌다 (스펙 §11 은 칸 기준)")
        if data.get("open_decisions") != ["D1"] or data.get("status") != "warning" or \
                not any("상태 칸이 계산값과 다르다: D1" in w for w in data.get("warnings", [])):
            problems.append(f"칸 불일치를 알리지 않았다: {data.get('status')} {data.get('warnings')} {data.get('open_decisions')}")
        # 같은 손 편집 + frontmatter done — 칸은 닫혀 보이지만 우회다.
        path.write_text(_text(ws, planned).replace("status: planned", "status: done", 1), encoding="utf-8")
        handoff = base / "session_handoff.md"
        if not handoff.is_file():
            handoff.write_text("# Session Handoff\n", encoding="utf-8")
        profile = str(ws / "docs" / "PROJECT_PROFILE.md")
        _, out = _tool(ws, "workflow_kit.tools.refresh_state", "--project-profile-path", profile)
        warnings = json.loads(out).get("warnings", [])
        if f"done 인데 열린 결정이 있다: {planned} (D1)" not in warnings:
            problems.append(f"칸이 kept 인 done task 의 우회를 못 봤다: {warnings}")
        state = json.loads(state_path.read_text(encoding="utf-8"))
        if "open_decisions" in state:
            problems.append(f"done task 를 open_decisions 에 셌다: {state['open_decisions']}")
        _, out = _tool(ws, "workflow_kit.tools.refresh_state", "--project-profile-path", profile, "--check")
        if f"done 인데 열린 결정이 있다: {planned} (D1)" not in json.loads(out).get("warnings", []):
            problems.append("--check 가 우회를 싣지 않았다")
        # 진행 중인 task 의 열린 결정은 우회가 아니다.
        active = _with_decision(ws)
        _update(ws, active, "--status", "in_progress")
        _, out = _tool(ws, "workflow_kit.tools.refresh_state", "--project-profile-path", profile)
        warnings = json.loads(out).get("warnings", [])
        if any(active in w for w in warnings):
            problems.append(f"진행 중 task 를 우회로 보고했다: {warnings}")
        state = json.loads(state_path.read_text(encoding="utf-8"))
        if state.get("open_decisions") != {active: 1}:
            problems.append(f"open_decisions 범위: {state.get('open_decisions')}")
        _update(ws, active, "--status", "blocked")
        state = json.loads(state_path.read_text(encoding="utf-8"))
        if state.get("open_decisions") != {active: 1}:
            problems.append(f"blocked task 의 열린 결정을 세지 않았다: {state.get('open_decisions')}")
        # 인용 없는 주장이 있으면 plan-status 의 lint 에 실린다.
        loose = _create(ws, "--plan-claim", "C1 하나를 한다", "--plan-claim", "C2 둘을 한다",
                        "--plan-claim", "C3 재지 않는 주장이다", name="재지 않는 주장")
        _, out = _tool(ws, "workflow_kit.tools.plan_status", "--task", loose)
        if not any(item.startswith("L7 C3") for item in json.loads(out).get("lint", [])):
            problems.append(f"plan-status 의 lint 가 비었다: {json.loads(out).get('lint')}")
    _record("case 16 (계산값으로 판정 · open_decisions 와 우회의 범위)", problems)


def case_17_l5_reads_head() -> None:
    problems: list[str] = []
    with tempfile.TemporaryDirectory() as td:
        ws = _workspace(td)
        (ws / "src").mkdir()
        (ws / "src" / "a.py").write_text("one\ntwo\nthree\n", encoding="utf-8")
        git_env = dict(os.environ, GIT_CONFIG_NOSYSTEM="1", GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t",
                       GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")
        for command in (["git", "init", "-q", "-b", BRANCH], ["git", "add", "-A"], ["git", "commit", "-q", "-m", "base"]):
            subprocess.run(command, cwd=str(ws), env=git_env, check=True, capture_output=True)
        rc, out = _run(ws, "--mode", "create", "--status", "planned", "--task-name", "위치", "--task-brief", "b",
                       "--done-criteria", "[C1] 기준",
                       "--plan-claim", "C1 하나를 한다", "--plan-claim", "C1.1 둘을 한다",
                       "--plan-claim", "C1.1.1 @ src/a.py:2-3 · f()", "--plan-claim", "C1.1.2 @ src/a.py:3-9 · g()",
                       "--plan-claim", "C1.1.3 @ src/none.py:1 · h()", "--plan-claim", "C1.1.4 @ new: src/b.py · k()")
        l5 = sorted(w for w in out.get("warnings", []) if w.startswith("L5"))
        if rc != 0 or len(l5) != 2 or "C1.1.2" not in l5[0] or "3줄" not in l5[0] or "C1.1.3" not in l5[1]:
            problems.append(f"L5 가 HEAD 를 읽지 않았다: rc={rc} {l5} {[w for w in out.get('warnings', []) if 'L5' in w]}")
    _record("case 17 (L5 — git 저장소에서 HEAD 의 줄 수를 읽는다)", problems)


def case_18_overlapping_reasons() -> None:
    problems: list[str] = []
    with tempfile.TemporaryDirectory() as td:
        ws = _workspace(td)
        task_id = _with_decision(ws)
        before = _snapshot(ws)
        rc, out = _update(ws, task_id, "--status", "done")   # 검증 결과 없음 → 강등 대상이기도 하다
        if rc != 1 or out.get("error_code") != "open_decisions":
            problems.append(f"강등과 겹치면 거부가 이겨야 한다: rc={rc} {out.get('error_code')} {out.get('status')}")
        if not any("검증 결과" in w for w in out.get("warnings", [])):
            problems.append(f"강등 사유를 함께 싣지 않았다: {out.get('warnings')}")
        if _snapshot(ws) != before:
            problems.append("거부인데 파일이 바뀌었다")
    _record("case 18 (겹친 사유 — 거부가 이기고 강등 사유도 싣는다)", problems)


AT = "2026-11-13T21:04:11.{:06d}+09:00"


def _branch_dir(ws: Path) -> Path:
    return ws / "ai-workflow" / "memory" / "active" / BRANCH


def _respond(ws: Path, task_id: str, responder: str, micro: int, *, value: str | None = None,
             opened: bool = False, archive: bool = False) -> Path:
    """응답 한 건을 받은편지함에 놓는다. ``archive`` 면 보관에 직접 놓는다 (plan-import 가 옮긴 모양)."""
    plan = pc.parse_plan(_text(ws, task_id).splitlines())
    data = pr.render_response(
        task_id=task_id, plan=plan, responder=responder, received_at=AT.format(micro),
        values={"D1": value} if value else None, opened={"D1": opened}).encode("utf-8")
    path = pr.publish(_branch_dir(ws), task_id, data)
    if archive:
        path = pr.move_exclusive(path, _branch_dir(ws), task_id)
    return path


def _plan_status(ws: Path, task_id: str) -> dict:
    _, out = _tool(ws, "workflow_kit.tools.plan_status", "--task", task_id,
                   "--project-profile-path", str(ws / "docs" / "PROJECT_PROFILE.md"))
    return json.loads(out)


def case_19_inbox_gate_and_reports() -> None:
    problems: list[str] = []
    with tempfile.TemporaryDirectory() as td:
        ws = _workspace(td)
        task_id = _with_decision(ws)
        _update(ws, task_id, "--decision-state", "D1=answered:warn")   # 열린 결정은 없다 — 받은편지함만 남긴다
        _respond(ws, task_id, "kim", 1, value="warn")
        _respond(ws, task_id, "lee", 2)
        before = _snapshot(ws)
        for apply in (True, False):
            rc, out = _update(ws, task_id, "--status", "done", "--validation-result", "v", apply=apply)
            refusal = "done 거부: 계획 응답 2건 미반영 — plan-import 로 반영하거나 --discard 로 거둔다."
            if rc != 1 or out.get("error_code") != "pending_plan_responses" or out.get("error") != refusal:
                problems.append(f"apply={apply}: 미반영 응답이 있는데 rc={rc} {out.get('error_code')} {out.get('error')!r}")
            if _snapshot(ws) != before:
                problems.append(f"apply={apply}: 거부인데 파일이 바뀌었다")
        # 다른 전이 · 진행 메모는 막지 않고 건수를 알린다 (내용은 싣지 않는다).
        rc, out = _update(ws, task_id, "--status", "in_progress")
        note = f"계획 응답 2건 미반영 ({task_id}) — plan-import 로 확인"
        if rc != 0 or note not in out.get("warnings", []):
            problems.append(f"backlog-update 가 미반영 건수를 알리지 않았다: rc={rc} {out.get('warnings')}")
        if any("kim" in w or "lee" in w for w in out.get("warnings", [])):
            problems.append("미반영 경고에 응답의 내용이 실렸다")
        for status in ("blocked", "planned"):
            rc, out = _update(ws, task_id, "--status", status)
            if rc != 0:
                problems.append(f"→ {status} 가 받은편지함 때문에 막혔다: {out.get('error_code')}")
        # 겹친 사유 — pending_plan_responses > open_decisions, 나머지는 warnings 에.
        _update(ws, task_id, "--decision-state", "D1=proposed")
        rc, out = _update(ws, task_id, "--status", "done", "--validation-result", "v")
        if rc != 1 or out.get("error_code") != "pending_plan_responses" or not _warned(out, "열린 결정 1건 (D1)"):
            problems.append(f"미반영 + 열린 결정: {out.get('error_code')} {out.get('warnings')}")
        # plan_lint_error > pending_plan_responses.
        healthy = _text(ws, task_id)
        path = _tasks(ws) / f"{task_id}.md"
        path.write_text(healthy.replace("- Claims: C2 ", "- Claims: C1 ", 1), encoding="utf-8")
        rc, out = _update(ws, task_id, "--status", "done", "--validation-result", "v")
        if rc != 1 or out.get("error_code") != "plan_lint_error" or not _warned(out, "계획 응답 2건 미반영"):
            problems.append(f"오류 규칙 + 미반영: {out.get('error_code')} {out.get('warnings')}")
        path.write_text(healthy, encoding="utf-8")
        # plan-status — 건수 · 파일별 자격 · 알 수 없는 파일.
        (pr.inbox_dir(_branch_dir(ws)) / "memo.md").write_text("x", encoding="utf-8")
        bad = pr.inbox_dir(_branch_dir(ws)) / f"{task_id}-5.md"
        bad.write_text("x", encoding="utf-8")
        status = _plan_status(ws, task_id)
        stages = sorted((r["stage"] is None, r["stage"]) for r in status.get("inbox", []))
        if status.get("pending_responses") != 3 or stages != [(False, 1), (True, None), (True, None)]:
            problems.append(f"plan-status 의 받은편지함: {status.get('pending_responses')} {status.get('inbox')}")
        if status.get("unknown_inbox_files") != ["memo.md"]:
            problems.append(f"plan-status 의 알 수 없는 파일: {status.get('unknown_inbox_files')}")
        bad.unlink()
        # session-start 도 건수를 알린다.
        handoff = _branch_dir(ws) / "session_handoff.md"
        if not handoff.is_file():
            handoff.write_text("# Session Handoff\n", encoding="utf-8")
        _, raw = _tool(ws, "workflow_kit.tools.session_start",
                       "--project-profile-path", str(ws / "docs" / "PROJECT_PROFILE.md"))
        if note not in json.loads(raw).get("warnings", []):
            problems.append(f"session-start 가 미반영 건수를 알리지 않았다: {json.loads(raw).get('warnings')}")
        # 지문을 바꾸는 쓰기는 받은편지함의 응답이 옛 계획에 대한 것이 됐음을 알린다. 거두지는 않는다.
        rc, out = _update(ws, task_id, "--plan-claim", "C3 새 주장을 더한다")
        if rc != 0 or "받은편지함 2건이 옛 계획에 대한 것이다 — plan-import --discard" not in out.get("warnings", []):
            problems.append(f"지문을 바꾸는 쓰기의 경고: rc={rc} {out.get('warnings')}")
        if len(pr.inbox_files(_branch_dir(ws), task_id)) != 2:
            problems.append("지문을 바꾸는 쓰기가 받은편지함을 건드렸다")
        rc, out = _update(ws, task_id, "--progress-note", "메모")
        if _warned(out, "옛 계획에 대한 것이다"):
            problems.append("지문을 바꾸지 않는 쓰기가 옛 계획 경고를 냈다")
        # 받은편지함을 비우면 닫힌다.
        for name in [p.name for p in pr.inbox_files(_branch_dir(ws), task_id)]:
            pr.move_exclusive(pr.inbox_dir(_branch_dir(ws)) / name, _branch_dir(ws), task_id, rejected=True)
        _update(ws, task_id, "--decision-state", "D1=answered:warn")
        rc, out = _update(ws, task_id, "--status", "done", "--validation-result", "v")
        if rc != 0 or _status(ws, task_id) != "done" or _warned(out, "미반영"):
            problems.append(f"받은편지함을 비웠는데 닫히지 않았다: rc={rc} {out.get('error_code')} {out.get('warnings')}")

    # 결정이 없는 task 는 받은편지함 행의 영향을 받지 않는다. 다른 task 의 받은편지함도 막지 않는다.
    with tempfile.TemporaryDirectory() as td:
        ws = _workspace(td)
        with_decision = _with_decision(ws)
        plain = _create(ws, "--plan-claim", "C1 열린 결정이 남으면 닫히지 않는다",
                        "--plan-claim", "C2 옛 task 는 그대로 읽힌다", name="주장만 있는 task")
        _respond(ws, with_decision, "kim", 1, value="warn")
        (pr.inbox_dir(_branch_dir(ws)) / f"{plain}-1.md").write_text("x", encoding="utf-8")
        rc, out = _run(ws, "--mode", "update", "--task-id", plain, "--task-name", "주장만 있는 task",
                       "--status", "done", "--validation-result", "v")
        if rc != 0 or _status(ws, plain) != "done":
            problems.append(f"결정이 없는 task 가 받은편지함 때문에 막혔다: rc={rc} {out.get('error_code')}")
        if not _warned(out, "계획 응답 2건 미반영"):
            problems.append(f"브랜치의 미반영 건수를 알리지 않았다: {out.get('warnings')}")
    _record("case 19 (받은편지함 — done 거부 · 사유의 순서 · 미반영 보고 · 옛 계획 경고)", problems)


def case_20_archived_responses_decide() -> None:
    problems: list[str] = []
    #: (보관한 응답들, 계산 상태, → done 이 통하는가)
    rows: list[tuple[str, list[tuple[str, int, str | None, bool]], str, bool]] = [
        ("기본값을 열어 봤다", [("kim", 1, None, True)], "kept", True),
        ("값을 바꿨다", [("kim", 1, "warn", False)], "changed:warn", True),
        ("열지 않았다", [("kim", 1, None, False)], "unopened", False),
        ("둘이 갈렸다", [("kim", 1, "warn", False), ("lee", 2, None, True)], "disputed", False),
        ("둘이 같다", [("kim", 1, "warn", False), ("lee", 2, "warn", True)], "changed:warn", True),
        ("말을 바꿨다", [("kim", 1, "warn", False), ("kim", 2, None, True)], "kept", True),
    ]
    for label, responses, state, closes in rows:
        with tempfile.TemporaryDirectory() as td:
            ws = _workspace(td)
            task_id = _with_decision(ws)
            for responder, micro, value, opened in responses:
                _respond(ws, task_id, responder, micro, value=value, opened=opened, archive=True)
            status = _plan_status(ws, task_id)
            got = {d["id"]: d["state"] for d in status.get("decisions", [])}
            if got != {"D1": state} or status.get("open_decisions") != ([] if closes else ["D1"]):
                problems.append(f"{label}: plan-status {got} 열린 {status.get('open_decisions')} (기대 {state})")
            rc, out = _update(ws, task_id, "--status", "in_progress")
            column = pc.parse_plan(_text(ws, task_id).splitlines()).decisions[0].state
            if rc != 0 or column != state:
                problems.append(f"{label}: 쓰기가 칸을 계산값으로 적지 않았다: {column}")
            if closes == _warned(out, f"열린 결정 1건 (D1 {state})"):
                problems.append(f"{label}: → in_progress 경고가 계산 상태와 맞지 않는다: {out.get('warnings')}")
            before = _snapshot(ws)
            rc, out = _update(ws, task_id, "--status", "done", "--validation-result", "v")
            if closes and (rc != 0 or _status(ws, task_id) != "done"):
                problems.append(f"{label}: 닫혀야 하는데 rc={rc} {out.get('error_code')}")
            if not closes and (rc != 1 or out.get("error_code") != "open_decisions" or _snapshot(ws) != before):
                problems.append(f"{label}: 거부돼야 하는데 rc={rc} {out.get('error_code')}")
    # 지문이 바뀌면 보관된 응답은 세지 않는다 — 닫히던 task 가 다시 열린다. 우회 검출도 보관 응답으로 계산한다.
    with tempfile.TemporaryDirectory() as td:
        ws = _workspace(td)
        task_id = _with_decision(ws)
        _respond(ws, task_id, "kim", 1, value="warn", archive=True)
        rc, _ = _update(ws, task_id, "--status", "done", "--validation-result", "v")
        handoff = _branch_dir(ws) / "session_handoff.md"
        if not handoff.is_file():
            handoff.write_text("# Session Handoff\n", encoding="utf-8")
        _, raw = _tool(ws, "workflow_kit.tools.refresh_state",
                       "--project-profile-path", str(ws / "docs" / "PROJECT_PROFILE.md"))
        if rc != 0 or any("done 인데 열린 결정" in w for w in json.loads(raw).get("warnings", [])):
            problems.append("보관 응답으로 닫힌 task 를 우회로 보고했다 — 우회 검출이 응답을 읽지 않는다")
        path = _tasks(ws) / f"{task_id}.md"
        path.write_text(_text(ws, task_id).replace("막는가?", "정말 막는가?", 1), encoding="utf-8")   # 손으로 질문을 바꿨다
        _, raw = _tool(ws, "workflow_kit.tools.refresh_state",
                       "--project-profile-path", str(ws / "docs" / "PROJECT_PROFILE.md"))
        if f"done 인데 열린 결정이 있다: {task_id} (D1)" not in json.loads(raw).get("warnings", []):
            problems.append(f"지문이 바뀐 뒤에도 옛 응답을 셌다: {json.loads(raw).get('warnings')}")
        status = _plan_status(ws, task_id)
        if status["decisions"][0]["state"] != "proposed" or status["decisions"][0]["column_state"] != "changed:warn":
            problems.append(f"plan-status 가 옛 응답을 셌다: {status['decisions'][0]}")
        # 사유 없이 걷을 수 없는 "열린 결정" 도 보관 응답으로 계산한다 — kept 인 결정은 사유 없이 걷힌다.
    with tempfile.TemporaryDirectory() as td:
        ws = _workspace(td)
        task_id = _with_decision(ws)
        _respond(ws, task_id, "kim", 1, opened=True, archive=True)
        rc, out = _update(ws, task_id, "--replace-field", "plan_decisions")
        if rc != 0:
            problems.append(f"kept 인 결정을 걷는 데 사유를 요구했다: {out.get('error_code')}")
    _record(f"case 20 (보관 응답으로 판정 — {len(rows)} 행의 상태 · 닫힘, 지문이 바뀌면 세지 않는다)", problems)


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
    case_13_dry_run_gives_the_same_verdict,
    case_14_messages_match_the_spec,
    case_15_brief_is_not_a_removal_note,
    case_16_computed_values_and_scopes,
    case_17_l5_reads_head,
    case_18_overlapping_reasons,
    case_19_inbox_gate_and_reports,
    case_20_archived_responses_decide,
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
