#!/usr/bin/env python3
"""진행 기록 상기 (`core/plan_workbench_spec.md` §4.6, TASK-2026-11-17-claude-remote-sync-check-234c32-003).

1. 판정 — in_progress 이고 Progress 가 ACTIVE_WINDOW 안인 task 가 STALE_AFTER 넘게 그대로면 hook JSON 하나,
   새로우면 · 물려받은 낡은 task 뿐이면 · 끝난(done) · 계획(planned) task 뿐이면 · 시각 없는 Progress 면 출력 없음
2. 부를 때마다 `.workbench/progress.checked` 와 자기 무시 `.gitignore` 를 쓴다 — 출력이 있든 없든
3. hooks.json 의 PostToolUse 명령을 실제 셸로 — 낡으면 같은 JSON; 표식이 STALE_AFTER 안이면 Python 을 띄우지 않는다;
   워크플로우 프로젝트(ai-workflow/memory)가 아니면 아무것도 쓰지 않는다
4. 이 기능을 모르는 kit 뿐이면 표식만 써서 STALE_AFTER 동안 다시 탐침하지 않는다 (도구마다 Python 탐침 방지)
5. 정본 §1 · 플러그인 rules 가 진행 기록 원칙을 싣는다 · 렌더러 출력 = 커밋된 hooks.json
"""

from __future__ import annotations

#: backlog-update · 셸 hook subprocess 를 여러 번 돈다.
CHECK_TIMEOUT_S = 240

#: 이 검사의 입력 표면 (spec `core/test_impact_tiering_spec.md` §2).
WATCHES = (
    "workflow-source/pyproject.toml",
    "workflow-source/workflow_kit/*",
    "workflow-source/core/global_workflow_standard.md",
    "workflow-source/tests/_workbench_fixture.py",
    "plugin/hooks/hooks.json",
    "plugin/adapters/claude-code/hooks.json",
    "plugin/adapters/claude-code/rules.md",
)

import datetime as dt
import json
import os
import subprocess
import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _workbench_fixture as fx  # noqa: E402

from workflow_kit import plugin_payload  # noqa: E402
from workflow_kit.common.standard_rules import load_standard_rules  # noqa: E402
from workflow_kit.tools import progress_nudge as pn  # noqa: E402

FAILURES: list[str] = []
REPO_ROOT = fx.SOURCE_ROOT.parent
HOOK_FILES = ("plugin/hooks/hooks.json", "plugin/adapters/claude-code/hooks.json")
PRINCIPLE_KEY = "backlog-update --progress-note"


def _record(name: str, problems: list[str]) -> None:
    if problems:
        FAILURES.append(name)
        print(f"  FAIL  {name}")
        for problem in problems[:12]:
            print(f"        - {problem}")
    else:
        print(f"  PASS  {name}")


def _stamp(at: dt.datetime) -> str:
    return at.strftime(pn.STAMP_FORMAT)


def _task(ws: Path, *, status: str, progress: str, name: str = "작업 중인 task") -> str:
    """backlog-update 로 만든다 — 손으로 적은 시각(`YYYY-MM-DD HH:MM`)은 도구가 그대로 둔다 (main-009)."""
    out = fx.backlog(ws, "--mode", "create", "--status", status, "--task-name", name, "--task-brief", "b",
                     "--done-criteria", "[C1] 끝난다", "--progress-note", progress)
    return str(out["task_id"])


def _hook_json(text: str) -> str | None:
    text = text.strip()
    if not text:
        return None
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return f"(JSON 아님) {text[:120]}"
    return str((data.get("hookSpecificOutput") or {}).get("additionalContext"))


def _run(ws: Path, now: dt.datetime) -> str | None:
    from io import StringIO
    from contextlib import redirect_stdout

    buffer = StringIO()
    # 브랜치는 fixture 의 것 — 없으면 이 저장소의 git 브랜치로 풀려 다른 디렉터리를 본다 (셸 경로는 fx.env() 로 받는다)
    saved = os.environ.get("CODEX_WORKFLOW_BRANCH")
    os.environ["CODEX_WORKFLOW_BRANCH"] = fx.BRANCH
    try:
        with redirect_stdout(buffer):
            pn.run_hook(fx.profile(ws), "PostToolUse", now=now)
    finally:
        if saved is None:
            os.environ.pop("CODEX_WORKFLOW_BRANCH", None)
        else:
            os.environ["CODEX_WORKFLOW_BRANCH"] = saved
    return _hook_json(buffer.getvalue())


def case_verdict() -> list[str]:
    problems: list[str] = []
    now = dt.datetime.now().replace(second=0, microsecond=0)
    with fx.temp_workspace("progress-nudge-1-") as td:
        ws = fx.make_workspace(td)
        if _run(ws, now) is not None:
            problems.append("task 가 없는데 상기했다")
        old = _task(ws, status="in_progress", progress=f"`{_stamp(now - dt.timedelta(hours=13))}` 물려받은 task")
        _task(ws, status="planned", progress=f"`{_stamp(now - dt.timedelta(minutes=40))}` 계획만 한 task", name="계획")
        bare = _task(ws, status="in_progress", progress="시각 없는 진행 기록", name="시각 없음")
        # 도구는 시각을 붙인다 — 시각 없는 Progress 는 1.25.0 이전에 쓰인 task 파일의 모양이라 그 줄만 옛 모양으로 돌린다
        bare_path = fx.branch_dir(ws) / "backlog" / "tasks" / f"{bare}.md"
        bare_path.write_text("\n".join("- Progress: 시각 없는 진행 기록" if line.startswith("- Progress:") else line
                                       for line in bare_path.read_text(encoding="utf-8").splitlines()) + "\n",
                             encoding="utf-8")
        if (message := _run(ws, now)) is not None:
            problems.append(f"물려받은 낡은 · planned · 시각 없는 task 뿐인데 상기했다: {message[:100]}")
        active = _task(ws, status="in_progress", progress=f"`{_stamp(now - dt.timedelta(minutes=5))}` 구현 중", name="작업")
        if (message := _run(ws, now)) is not None:
            problems.append(f"5분 전 기록인데 상기했다: {message[:100]}")
        message = _run(ws, now + dt.timedelta(minutes=16))  # 21분째 그대로
        if message is None or active not in message or "21분" not in message or "--progress-note" not in message:
            problems.append(f"21분째 그대로인데 상기가 없거나 문구가 다르다: {message!r}")
        if message and old in message:
            problems.append("물려받은 낡은 task 를 상기 대상에 넣었다")
        fx.backlog(ws, "--mode", "update", "--task-id", active, "--task-name", "작업", "--progress-note",
                   f"`{_stamp(now + dt.timedelta(minutes=15))}` 검사 중")
        if (message := _run(ws, now + dt.timedelta(minutes=16))) is not None:
            problems.append(f"진행 기록을 갱신했는데 상기했다: {message[:100]}")
    return problems


def case_marker() -> list[str]:
    problems: list[str] = []
    now = dt.datetime.now().replace(second=0, microsecond=0)
    with fx.temp_workspace("progress-nudge-2-") as td:
        ws = fx.make_workspace(td)
        _run(ws, now)
        checked = ws / ".workbench" / pn.CHECKED
        ignore = ws / ".workbench" / ".gitignore"
        if not checked.is_file():
            problems.append("출력이 없어도 확인 표식을 써야 한다")
        if not ignore.is_file() or ignore.read_text(encoding="utf-8") != "*\n":
            problems.append(".workbench/.gitignore 가 자기 무시(*) 가 아니다")
    return problems


def _hook_command(rel: str) -> str:
    data = json.loads((REPO_ROOT / rel).read_text(encoding="utf-8"))
    commands = [h.get("command", "") for entry in data["hooks"].get("PostToolUse", []) for h in entry.get("hooks", [])]
    return next((c for c in commands if f"{pn.COMMAND} --hook" in c), "")


def _bash(command: str, ws: Path, path_prefix: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    env = {**fx.env(), "CLAUDE_PROJECT_DIR": str(ws), "PATH": f"{path_prefix}{os.pathsep}{os.environ.get('PATH', '')}"}
    return subprocess.run(["bash", "-c", command], capture_output=True, text=True, cwd=str(cwd or ws), env=env,
                          timeout=120)


def case_shell() -> list[str]:
    problems: list[str] = []
    command = _hook_command("plugin/hooks/hooks.json")
    if not command:
        return ["plugin/hooks/hooks.json 의 PostToolUse 에 progress-nudge 명령이 없다"]
    real_bin = str(Path(sys.executable).parent)
    now = dt.datetime.now().replace(second=0, microsecond=0)
    with fx.temp_workspace("progress-nudge-3-") as td:
        ws = fx.make_workspace(td)
        task_id = _task(ws, status="in_progress", progress=f"`{_stamp(now - dt.timedelta(minutes=30))}` 구현 중")
        proc = _bash(command, ws, real_bin)
        message = _hook_json(proc.stdout)
        if proc.returncode != 0 or message is None or task_id not in message:
            problems.append(f"낡은 진행 기록에 셸 hook 이 상기하지 않았다: rc {proc.returncode} {proc.stdout[:160]!r} {proc.stderr[-200:]!r}")
        checked = ws / ".workbench" / pn.CHECKED
        before = checked.stat().st_mtime_ns if checked.exists() else None
        fake_bin = ws / "fakebin"
        fake_bin.mkdir()
        marker = ws / "python-ran"
        for name in ("python3", "python"):  # 표식이 새로우면 이것조차 불리면 안 된다
            script = fake_bin / name
            script.write_text(f"#!/bin/sh\ntouch {marker}\nexit 1\n", encoding="utf-8")
            script.chmod(0o755)
        again = _bash(command, ws, str(fake_bin))
        if again.stdout.strip() or marker.exists():
            problems.append(f"표식이 {pn.STALE_AFTER} 안인데 Python 을 띄웠거나 출력했다: {again.stdout[:120]!r}")
        if before is None or checked.stat().st_mtime_ns != before:
            problems.append("표식이 새로울 때 표식을 다시 썼다")
    with fx.temp_workspace("progress-nudge-3b-") as td:
        plain = Path(td)
        proc = _bash(command, plain, real_bin)
        if proc.stdout.strip() or (plain / ".workbench").exists():
            problems.append(f"워크플로우 프로젝트가 아닌데 출력했거나 .workbench 를 만들었다: {proc.stdout[:120]!r}")
    return problems


def case_old_kit() -> list[str]:
    problems: list[str] = []
    command = _hook_command("plugin/hooks/hooks.json")
    now = dt.datetime.now().replace(second=0, microsecond=0)
    with fx.temp_workspace("progress-nudge-4-") as td:
        ws = fx.make_workspace(td)
        _task(ws, status="in_progress", progress=f"`{_stamp(now - dt.timedelta(minutes=30))}` 구현 중")
        fake_bin = ws / "oldkit"
        fake_bin.mkdir()
        runs = ws / "python-runs"
        for name in ("python3", "python"):
            script = fake_bin / name
            # 옛 kit 의 모양: progress_nudge 를 모른다.
            script.write_text(f"#!/bin/sh\necho x >> {runs}\nexit 1\n", encoding="utf-8")
            script.chmod(0o755)
        first = _bash(command, ws, str(fake_bin))
        count = runs.read_text().count("x") if runs.exists() else 0
        if first.stdout.strip():
            problems.append(f"옛 kit 뿐인데 무엇인가 출력했다: {first.stdout[:120]!r}")
        if not (ws / ".workbench" / pn.CHECKED).is_file():
            problems.append("옛 kit 뿐일 때 표식을 쓰지 않았다 — 도구마다 Python 탐침을 다시 한다")
        if (ws / ".workbench" / ".gitignore").read_text(encoding="utf-8") != "*\n" if (ws / ".workbench" / ".gitignore").exists() else True:
            problems.append("옛 kit 경로가 만든 .workbench 에 자기 무시 .gitignore 가 없다")
        _bash(command, ws, str(fake_bin))
        if (runs.read_text().count("x") if runs.exists() else 0) != count:
            problems.append("표식을 쓴 뒤에도 다시 Python 탐침을 했다")
    return problems


def case_declared() -> list[str]:
    problems: list[str] = []
    rules = load_standard_rules(fx.SOURCE_ROOT)
    if not any(PRINCIPLE_KEY in p for p in rules.principles):
        problems.append(f"정본 §1 에 진행 기록 원칙({PRINCIPLE_KEY})이 없다")
    rules_md = (REPO_ROOT / "plugin" / "adapters" / "claude-code" / "rules.md").read_text(encoding="utf-8")
    if PRINCIPLE_KEY not in rules_md:
        problems.append("플러그인 rules.md 에 진행 기록 원칙이 없다")
    rendered = json.loads(plugin_payload.render_claude_code_hooks(rules))
    for rel in HOOK_FILES:
        committed = json.loads((REPO_ROOT / rel).read_text(encoding="utf-8"))
        if committed.get("hooks", {}).get("PostToolUse") != rendered["hooks"]["PostToolUse"]:
            problems.append(f"{rel} 의 PostToolUse 가 렌더러 출력과 다르다 — plugin_payload --apply 로 다시 만든다")
    return problems


CASES = (
    ("1 판정 — 작업 중 task 가 15분 넘게 그대로일 때만 상기", case_verdict),
    ("2 부를 때마다 확인 표식 · 자기 무시 .gitignore", case_marker),
    ("3 hooks.json 명령을 실제 셸로 · 표식이 새로우면 Python 안 띄움 · 비 워크플로우 무동작", case_shell),
    ("4 옛 kit 뿐이면 표식만 — 다시 탐침하지 않는다", case_old_kit),
    ("5 정본 원칙 · 플러그인 rules · hooks.json = 렌더러", case_declared),
)


def main() -> int:
    print("check_progress_nudge — 진행 기록 상기 (plan_workbench_spec §4.6)")
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
