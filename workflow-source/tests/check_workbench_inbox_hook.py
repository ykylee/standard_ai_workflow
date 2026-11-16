#!/usr/bin/env python3
"""워크벤치 응답 도착 신호 + 작업 세션 hook 자동 반영 (`core/plan_workbench_spec.md` §6.1, TASK-2026-11-16-main-014).

1. 서버는 응답을 받으면 `.workbench/inbox.stamp` 를 갱신하고 task 파일은 쓰지 않는다; 계획 화면은 그 응답을 '반영 대기' 로 보인다
2. `plan-import --hook PostToolUse` — stamp 가 새로우면 응답을 보관으로 옮기고 결정 상태를 바꾸며 stdout 은 hook JSON 하나
   (hookEventName · additionalContext 에 task · 결정 변화); seen 이 stamp 시각이 된다; 계획 화면은 '반영됨'
3. 할 것이 없으면 조용하다 — 두 번째 호출 · stamp 없음 · seen 이 stamp 와 같은 표식: 출력 없음 · rc 0 · 받은편지함 그대로;
   같은 초(mtime 같음)에 온 두 번째 응답도 표식이 달라 반영한다 (1초 단위 파일시스템 — verifier 재현)
4. 자격 없는 응답(제출 뒤 계획이 바뀜)은 받은편지함에 남기고 사유를 알린다
5. 플러그인 hooks.json 의 PostToolUse · UserPromptSubmit 명령을 실제 셸로 — 같은 결과; stamp 가 없으면 Python 을 띄우지 않는다;
   cwd 가 프로젝트 밖이어도 $CLAUDE_PROJECT_DIR 로 반영한다; 기능을 아는 kit 이 없으면 한 번 알리고 다시 띄우지 않는다
"""

from __future__ import annotations

#: 서버 · plan-import · 셸 hook subprocess 를 여러 번 돈다.
CHECK_TIMEOUT_S = 240

#: 이 검사의 입력 표면 (spec `core/test_impact_tiering_spec.md` §2).
WATCHES = (
    "workflow-source/pyproject.toml",
    "workflow-source/workflow_kit/*",
    "workflow-source/tests/_workbench_fixture.py",
    "plugin/hooks/hooks.json",
    "plugin/adapters/claude-code/hooks.json",
)

import hashlib
import json
import os
import subprocess
import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _workbench_fixture as fx  # noqa: E402
from workflow_kit.common import plan_claims as pc  # noqa: E402
from workflow_kit.common import plan_responses as pr  # noqa: E402
from workflow_kit.common import plan_tasks  # noqa: E402

FAILURES: list[str] = []
REPO_ROOT = Path(__file__).resolve().parents[2]


def _record(name: str, problems: list[str]) -> None:
    if problems:
        FAILURES.append(name)
        print(f"  FAIL  {name}")
        for problem in problems[:12]:
            print(f"        - {problem}")
    else:
        print(f"  PASS  {name}")


def _task_path(ws: Path, task_id: str) -> Path:
    return fx.branch_dir(ws) / "backlog" / "tasks" / f"{task_id}.md"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _submit(ws: Path, task_id: str, *, warn: bool = True) -> tuple[int, str]:
    """워크벤치(개방 모드)로 응답 하나를 보낸다 — (상태, 제출 뒤 계획 화면)."""
    with fx.running(ws, tokens=(), open_name="owner") as srv:
        browser = fx.Browser(srv.port)
        reply, _ = fx.submit(browser, f"/task/{task_id}", overrides={"value_D1": "warn"} if warn else None)
        page = browser.get(f"/task/{task_id}").text
    return reply.status, page


def _hook(ws: Path, event: str = "PostToolUse") -> subprocess.CompletedProcess[str]:
    return fx.cli(ws, ["-m", "workflow_kit", "plan-import", "--hook", event])


def _stamp(ws: Path) -> Path:
    return ws / ".workbench" / "inbox.stamp"


def _seen(ws: Path) -> Path:
    return ws / ".workbench" / "inbox.seen"


def case_server_signal() -> list[str]:
    problems: list[str] = []
    with fx.temp_workspace("wb-hook-1-") as td:
        ws = fx.make_workspace(td)
        task_id = fx.create_task(ws)
        before = _sha(_task_path(ws, task_id))
        status, page = _submit(ws, task_id)
        if status != 303 or not _stamp(ws).is_file():
            problems.append(f"제출({status}) 뒤 inbox.stamp 가 없다")
        if _sha(_task_path(ws, task_id)) != before:
            problems.append("서버가 task 파일을 썼다 — ADR-032 결정 15")
        if "반영 대기" not in page or "owner" not in page:
            problems.append("계획 화면이 보낸 응답을 '반영 대기' 로 보이지 않는다")
    return problems


def case_hook_applies() -> list[str]:
    problems: list[str] = []
    with fx.temp_workspace("wb-hook-2-") as td:
        ws = fx.make_workspace(td)
        task_id = fx.create_task(ws)
        _submit(ws, task_id)
        proc = _hook(ws)
        try:
            out = json.loads(proc.stdout)
        except json.JSONDecodeError:
            return [f"stdout 이 JSON 하나가 아니다: {proc.stdout[:200]!r} {proc.stderr[-200:]}"]
        hso = out.get("hookSpecificOutput") or {}
        ctx = str(hso.get("additionalContext") or "")
        if hso.get("hookEventName") != "PostToolUse" or task_id not in ctx or "D1" not in ctx or "changed:warn" not in ctx:
            problems.append(f"hook JSON 이 결정 변화를 알리지 않는다: {out}")
        if fx.inbox_snapshot(ws) or len(pr.archive_files(fx.branch_dir(ws), task_id)) != 1:
            problems.append("응답이 보관으로 옮겨지지 않았다")
        task = plan_tasks.read_task_plan(_task_path(ws, task_id))
        if task is None or plan_tasks.computed_states(task).states.get("D1") != f"{pc.STATE_CHANGED}:warn":
            problems.append("결정 상태가 응답을 반영하지 않았다")
        if not _seen(ws).is_file() or _seen(ws).read_bytes() != _stamp(ws).read_bytes():
            problems.append("seen 이 처리한 stamp 표식이 아니다")
        with fx.running(ws, tokens=(), open_name="owner") as srv:
            page = fx.request(srv.port, "GET", f"/task/{task_id}").text
        if "반영됨" not in page or "반영 대기" in page:
            problems.append("반영 뒤 계획 화면이 '반영됨' 이 아니다")
    return problems


def case_quiet() -> list[str]:
    problems: list[str] = []
    with fx.temp_workspace("wb-hook-3-") as td:
        ws = fx.make_workspace(td)
        task_id = fx.create_task(ws)
        none = _hook(ws)
        if none.returncode != 0 or none.stdout.strip():
            problems.append(f"stamp 가 없는데 출력했다: rc {none.returncode} {none.stdout[:120]!r}")
        _submit(ws, task_id)
        _hook(ws)
        again = _hook(ws)
        if again.returncode != 0 or again.stdout.strip():
            problems.append(f"두 번째 호출이 조용하지 않다: {again.stdout[:120]!r}")
        # 받은편지함에 응답이 있어도 seen 이 stamp 와 같은 표식이면 hook 은 보지 않는다 (session-start 가 보고한다).
        _submit(ws, task_id, warn=False)
        _seen(ws).write_bytes(_stamp(ws).read_bytes())
        stale = _hook(ws)
        if stale.stdout.strip() or not fx.inbox_snapshot(ws):
            problems.append("seen 이 stamp 와 같은데 hook 이 반영했다")
        # 같은 초 — mtime 이 같아도 표식이 다르면 새 응답이다.
        _seen(ws).write_bytes(b"older-token\n")
        stamp_ns = _stamp(ws).stat().st_mtime_ns
        os.utime(_seen(ws), ns=(stamp_ns, stamp_ns))
        same_second = _hook(ws)
        if not same_second.stdout.strip() or fx.inbox_snapshot(ws):
            problems.append("mtime 이 같은 두 번째 응답을 놓쳤다 — 1초 단위 파일시스템에서 응답이 묻힌다")
    return problems


def case_ineligible() -> list[str]:
    problems: list[str] = []
    with fx.temp_workspace("wb-hook-4-") as td:
        ws = fx.make_workspace(td)
        task_id = fx.create_task(ws)
        _submit(ws, task_id)
        # 제출 뒤 계획이 바뀌면 응답의 지문이 맞지 않는다 — 자격 없음.
        fx.backlog(ws, "--mode", "update", "--task-id", task_id, "--task-name", "x",
                   "--plan-decision", "D3 [C1] 하나 더? | default: x | options: x = 엑스; y = 와이")
        proc = _hook(ws)
        ctx = str(((json.loads(proc.stdout or "{}") or {}).get("hookSpecificOutput") or {}).get("additionalContext") or "")
        if "자격 없는" not in ctx or task_id not in ctx:
            problems.append(f"자격 없는 응답의 사유를 알리지 않았다: {proc.stdout[:300]!r}")
        if not fx.inbox_snapshot(ws):
            problems.append("자격 없는 응답을 받은편지함에서 옮겼다")
    return problems


def _hook_command(rel: str, event: str) -> str:
    data = json.loads((REPO_ROOT / rel).read_text(encoding="utf-8"))
    commands = [h.get("command", "") for entry in data["hooks"].get(event, []) for h in entry.get("hooks", [])]
    return next((c for c in commands if "plan-import --hook" in c), "")


def case_shell_hook() -> list[str]:
    problems: list[str] = []
    for rel in ("plugin/hooks/hooks.json", "plugin/adapters/claude-code/hooks.json"):
        for event in ("PostToolUse", "UserPromptSubmit"):
            if f"plan-import --hook {event}" not in _hook_command(rel, event):
                problems.append(f"{rel}: {event} 에 plan-import --hook 명령이 없다")
    command = _hook_command("plugin/hooks/hooks.json", "UserPromptSubmit")
    with fx.temp_workspace("wb-hook-5-") as td:
        ws = fx.make_workspace(td)
        task_id = fx.create_task(ws)
        fake_bin = ws / "fakebin"
        fake_bin.mkdir()
        marker = ws / "python-ran"
        for name in ("python3", "python"):  # stamp 가 없으면 이것조차 불리면 안 된다
            script = fake_bin / name
            script.write_text(f"#!/bin/sh\ntouch {marker}\nexit 1\n", encoding="utf-8")
            script.chmod(0o755)
        env = {**fx.env(), "CLAUDE_PROJECT_DIR": str(ws), "PATH": f"{fake_bin}{os.pathsep}{os.environ.get('PATH', '')}"}
        quiet = subprocess.run(["bash", "-c", command], capture_output=True, text=True, cwd=str(ws), env=env, timeout=60)
        if quiet.stdout.strip() or quiet.returncode != 0 or marker.exists():
            problems.append(f"stamp 가 없는데 hook 이 Python 을 띄웠거나 출력했다 (ran={marker.exists()})")
        _submit(ws, task_id)
        real_bin = Path(sys.executable).parent
        env["PATH"] = f"{real_bin}{os.pathsep}{os.environ.get('PATH', '')}"
        proc = subprocess.run(["bash", "-c", command], capture_output=True, text=True, cwd=str(ws), env=env, timeout=120)
        try:
            hso = json.loads(proc.stdout).get("hookSpecificOutput") or {}
        except json.JSONDecodeError:
            return problems + [f"셸 hook 출력이 JSON 이 아니다: {proc.stdout[:200]!r} rc {proc.returncode}"]
        if hso.get("hookEventName") != "UserPromptSubmit" or "changed:warn" not in str(hso.get("additionalContext")):
            problems.append(f"셸 hook 이 반영 결과를 알리지 않았다: {hso}")
    # 셸 경로의 같은 초 — seen 의 mtime 이 stamp 와 같아도 표식이 다르면 셸 hook 이 거르지 않는다.
    with fx.temp_workspace("wb-hook-5e-") as td:
        ws = fx.make_workspace(td)
        task_id = fx.create_task(ws)
        _submit(ws, task_id)
        _seen(ws).write_bytes(b"older-token\n")
        stamp_ns = _stamp(ws).stat().st_mtime_ns
        os.utime(_seen(ws), ns=(stamp_ns, stamp_ns))
        env = {**fx.env(), "CLAUDE_PROJECT_DIR": str(ws),
               "PATH": f"{Path(sys.executable).parent}{os.pathsep}{os.environ.get('PATH', '')}"}
        proc = subprocess.run(["bash", "-c", command], capture_output=True, text=True, cwd=str(ws), env=env, timeout=120)
        if "changed:warn" not in proc.stdout or fx.inbox_snapshot(ws):
            problems.append("셸 hook 이 mtime 이 같은 새 응답을 걸렀다 — 1초 단위 파일시스템에서 응답이 묻힌다")
    # cwd 가 프로젝트 밖 — $CLAUDE_PROJECT_DIR 로 같은 checkout 을 본다.
    with fx.temp_workspace("wb-hook-5b-") as td, fx.temp_workspace("wb-hook-5c-") as outside:
        ws = fx.make_workspace(td)
        task_id = fx.create_task(ws)
        _submit(ws, task_id)
        env = {**fx.env(), "CLAUDE_PROJECT_DIR": str(ws),
               "PATH": f"{Path(sys.executable).parent}{os.pathsep}{os.environ.get('PATH', '')}"}
        proc = subprocess.run(["bash", "-c", command], capture_output=True, text=True, cwd=outside, env=env, timeout=120)
        if "changed:warn" not in proc.stdout or fx.inbox_snapshot(ws):
            problems.append(f"cwd 가 프로젝트 밖일 때 반영하지 않았다: {proc.stdout[:160]!r}")
    # 기능을 아는 kit 이 없음(옛 kit 만) — 한 번 알리고 seen 을 맞춰 다시 띄우지 않는다.
    with fx.temp_workspace("wb-hook-5d-") as td:
        ws = fx.make_workspace(td)
        task_id = fx.create_task(ws)
        _submit(ws, task_id)
        fake_bin = ws / "oldkit"
        fake_bin.mkdir()
        runs = ws / "python-runs"
        for name in ("python3", "python"):
            script = fake_bin / name
            # 옛 kit 의 모양: `import workflow_kit` 은 되고 새 모듈(inbox_signal)과 --hook 은 모른다.
            script.write_text("#!/bin/sh\n"
                              f"echo x >> {runs}\n"
                              'case "$*" in *inbox_signal*) exit 1;; *"import workflow_kit"*) exit 0;; esac\n'
                              "exit 2\n", encoding="utf-8")
            script.chmod(0o755)
        env = {**fx.env(), "CLAUDE_PROJECT_DIR": str(ws), "PATH": f"{fake_bin}{os.pathsep}/usr/bin{os.pathsep}/bin"}
        first = subprocess.run(["bash", "-c", command], capture_output=True, text=True, cwd=str(ws), env=env, timeout=60)
        try:
            notice = str((json.loads(first.stdout).get("hookSpecificOutput") or {}).get("additionalContext"))
        except json.JSONDecodeError:
            notice = ""
        if "plan-import" not in notice or "--apply" not in notice:
            problems.append(f"옛 kit 뿐인데 직접 반영하라고 알리지 않았다: {first.stdout[:160]!r}")
        before = runs.read_text().count("x") if runs.exists() else 0
        second = subprocess.run(["bash", "-c", command], capture_output=True, text=True, cwd=str(ws), env=env, timeout=60)
        after = runs.read_text().count("x") if runs.exists() else 0
        if second.stdout.strip() or after != before:
            problems.append("옛 kit 뿐인 호스트에서 hook 이 도구마다 다시 알리거나 Python 을 띄운다")
    return problems


CASES = (
    ("1 서버는 stamp 만 — task 파일 그대로 · 화면 '반영 대기'", case_server_signal),
    ("2 hook 이 반영하고 JSON 으로 알린다 · 화면 '반영됨'", case_hook_applies),
    ("3 할 것이 없으면 조용하다", case_quiet),
    ("4 자격 없는 응답은 남기고 사유를 알린다", case_ineligible),
    ("5 hooks.json 명령을 실제 셸로 · 신호 없으면 Python 안 띄움", case_shell_hook),
)


def main() -> int:
    print("check_workbench_inbox_hook — 응답 도착 신호 · hook 자동 반영 (plan_workbench_spec §6.1)")
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
