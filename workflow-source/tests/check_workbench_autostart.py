#!/usr/bin/env python3
"""워크벤치 자동 기동 — session-start 가 띄우고 SessionEnd hook 이 내린다 (`core/plan_workbench_spec.md` §3.1).

1. `--autostart on <시작 인자>` 가 `.workbench/autostart.json` 에 인자를 쓴다 — 잘못된 인자는 rc 2 로 쓰지 않는다,
   `off` 가 지운다, `--status` 가 `autostart` 를 보인다
2. 설정이 있으면 `session-start` 가 띄운다 — summary `워크벤치 시작: <url>`, 기록 `autostarted`, healthz 응답;
   다음 `session-start` 는 새로 띄우지 않고 `워크벤치 실행 중:`; `--stop --autostarted-only` 가 내리고 기록을 지운다
3. 시작 실패(포트 사용 중)는 `warnings` 한 줄이고 `session-start` 는 status ok · summary 줄 없음
4. 끄는 표식 — 검사 표식이 이 작업 공간을 가리키거나 `WORKFLOW_KIT_NO_WORKBENCH_AUTOSTART` 가 있으면 띄우지 않는다
5. 내리기의 안전 — `--autostarted-only` 는 손으로 띄운 서버를 두고, 기록의 pid 가 워크벤치로 답하지 않으면 죽이지 않는다;
   플래그 없는 `--stop` 은 손으로 띄운 서버도 내린다
6. Claude Code 플러그인 hooks 의 SessionEnd 에 `workbench --stop --autostarted-only`
7. 시작 대기 시간 초과 — 기록을 쓰기 전의 자식은 내려서 고아를 남기지 않는다
"""

from __future__ import annotations

#: 서버 subprocess 와 session-start subprocess 를 여러 번 돈다.
CHECK_TIMEOUT_S = 240

#: 이 검사의 입력 표면 (spec `core/test_impact_tiering_spec.md` §2).
WATCHES = (
    "workflow-source/pyproject.toml",
    "workflow-source/workflow_kit/*",
    "workflow-source/tests/_workbench_fixture.py",
    "plugin/hooks/hooks.json",
    "plugin/adapters/claude-code/hooks.json",
)

import json
import os
import signal
import socket
import subprocess
import sys
import threading
import time
import traceback
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _workbench_fixture as fx  # noqa: E402
from workflow_kit.tools import workbench as wb_cli  # noqa: E402

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


def _env(**extra: str) -> dict[str, str]:
    env = fx.env()
    # 러너가 건 검사 표식은 살아 있는 저장소를 가리킨다 — 임시 작업 공간의 자동 기동은 막지 않는다.
    env.pop(wb_cli.AUTOSTART_OFF_ENV, None)
    env[wb_cli.CHECK_MARK_ENV] = str(REPO_ROOT)
    env.update(extra)
    return env


def _wb(ws: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "workflow_kit", "workbench", "--project-profile-path", str(fx.profile(ws)), *args],
        capture_output=True, encoding="utf-8", errors="replace", check=False, env=_env(), cwd=str(ws), timeout=60)


def _session_start(ws: Path, **extra: str) -> dict:
    handoff = fx.branch_dir(ws) / "session_handoff.md"
    if not handoff.is_file():
        handoff.write_text("# Session Handoff\n", encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, "-m", "workflow_kit", "session-start", "--project-profile-path", str(fx.profile(ws))],
        capture_output=True, encoding="utf-8", errors="replace", check=False, env=_env(**extra), cwd=str(ws),
        timeout=120)
    try:
        out: dict = json.loads(proc.stdout)
        return out
    except json.JSONDecodeError:
        return {"_raw": proc.stdout[-300:], "_err": proc.stderr[-300:]}


def _record_of(ws: Path) -> dict:
    return wb_cli.read_record(ws) or {}


def _kill_recorded(ws: Path) -> None:
    pid = _record_of(ws).get("pid")
    if isinstance(pid, int) and wb_cli.pid_alive(pid) and pid != os.getpid():
        try:
            os.kill(pid, signal.SIGTERM)
        except OSError:
            pass
        deadline = time.monotonic() + 10
        while wb_cli.pid_alive(pid) and time.monotonic() < deadline:
            time.sleep(0.1)


def _workbench_lines(out: dict) -> list[str]:
    return [line for line in out.get("summary") or [] if "워크벤치" in line]


def case_config() -> list[str]:
    problems: list[str] = []
    with fx.temp_workspace("wb-auto-1-") as td:
        ws = fx.make_workspace(td)
        path = ws / ".workbench" / "autostart.json"
        proc = _wb(ws, "--autostart", "on", "--open", "owner", "--token", "approver:a=env:X")
        if proc.returncode != 2 or path.exists():
            problems.append(f"잘못된 인자: rc {proc.returncode} · 파일 {path.exists()}")
        proc = _wb(ws, "--autostart", "on", "--open", "owner", "--bind", "0.0.0.0", "--port", "8799")
        if proc.returncode != 0 or not path.is_file():
            return problems + [f"--autostart on: rc {proc.returncode} {proc.stderr[-200:]}"]
        argv = json.loads(path.read_text(encoding="utf-8")).get("argv")
        if argv != ["--bind", "0.0.0.0", "--port", "8799", "--open", "owner"]:
            problems.append(f"저장된 인자가 다르다: {argv}")
        if (ws / ".workbench" / ".gitignore").read_bytes() != b"*\n":
            problems.append(".workbench/ 가 자기 무시 디렉터리가 아니다")
        status = json.loads(_wb(ws, "--status").stdout)
        if status.get("autostart") is not True or status.get("running") is not False:
            problems.append(f"--status 가 autostart 를 보이지 않는다: {status}")
        proc = _wb(ws, "--autostart", "off")
        if proc.returncode != 0 or path.exists():
            problems.append(f"--autostart off: rc {proc.returncode} · 파일이 남았다 {path.exists()}")
    return problems


def case_session_start_starts() -> list[str]:
    problems: list[str] = []
    with fx.temp_workspace("wb-auto-2-") as td:
        ws = fx.make_workspace(td)
        try:
            if _wb(ws, "--autostart", "on", "--open", "owner", "--port", "0").returncode != 0:
                return ["--autostart on 이 실패했다"]
            out = _session_start(ws)
            lines = _workbench_lines(out)
            record = _record_of(ws)
            url = record.get("public_url")
            if out.get("status") not in ("ok", "warning") or lines != [f"워크벤치 시작: {url}"]:
                return problems + [f"session-start 가 띄우지 않았다: {lines} {out.get('warnings')} {str(out)[:200]}"]
            if record.get("autostarted") is not True or not wb_cli.pid_alive(record.get("pid")):
                problems.append(f"실행 기록에 autostarted 가 없거나 pid 가 죽었다: {record}")
            health = fx.request(int(record["port"]), "GET", "/healthz")
            if health.status != 200:
                problems.append(f"자동 기동 서버의 healthz 가 {health.status} 다")
            pid = record.get("pid")
            # session-start 의 앞선 판정과 별개로 진입점 자신도 살아 있는 서버 위에 띄우지 않는다.
            with mock.patch.dict(os.environ, _env(), clear=True):
                direct = wb_cli.autostart_if_configured(fx.profile(ws).resolve())
            if direct != (None, None):
                problems.append(f"살아 있는 서버가 있는데 autostart_if_configured 가 다시 띄우려 했다: {direct}")
            again = _workbench_lines(_session_start(ws))
            if again != [f"워크벤치 실행 중: {url}"] or _record_of(ws).get("pid") != pid:
                problems.append(f"두 번째 session-start 가 새로 띄웠거나 실행 중 줄이 없다: {again}")
            stop = json.loads(_wb(ws, "--stop", "--autostarted-only").stdout)
            if stop.get("stopped") is not True or wb_cli.pid_alive(pid) or _record_of(ws):
                problems.append(f"--stop --autostarted-only 가 자동 기동 서버를 내리지 않았다: {stop}")
        finally:
            _kill_recorded(ws)
    return problems


def case_start_failure() -> list[str]:
    problems: list[str] = []
    with fx.temp_workspace("wb-auto-3-") as td:
        ws = fx.make_workspace(td)
        busy = socket.socket()
        busy.bind(("127.0.0.1", 0))
        busy.listen(1)
        try:
            port = str(busy.getsockname()[1])
            if _wb(ws, "--autostart", "on", "--open", "owner", "--port", port).returncode != 0:
                return ["--autostart on 이 실패했다"]
            out = _session_start(ws)
            notes = [w for w in out.get("warnings") or [] if "워크벤치 자동 기동 실패" in w]
            if out.get("status") not in ("ok", "warning") or len(notes) != 1 or _workbench_lines(out):
                problems.append(f"시작 실패가 경고 한 줄이 아니다: status {out.get('status')} {notes} "
                                f"{_workbench_lines(out)} {str(out)[:200]}")
            if "bind" not in (notes[0] if notes else ""):
                problems.append(f"실패 사유에 서버의 이유(bind)가 없다: {notes}")
        finally:
            busy.close()
            _kill_recorded(ws)
    return problems


def case_suppressed() -> list[str]:
    problems: list[str] = []
    with fx.temp_workspace("wb-auto-4-") as td:
        ws = fx.make_workspace(td)
        try:
            if _wb(ws, "--autostart", "on", "--open", "owner", "--port", "0").returncode != 0:
                return ["--autostart on 이 실패했다"]
            for label, extra in (("검사 표식", {wb_cli.CHECK_MARK_ENV: str(ws)}),
                                 ("끄는 env", {wb_cli.AUTOSTART_OFF_ENV: "1"})):
                out = _session_start(ws, **extra)
                if _workbench_lines(out) or _record_of(ws):
                    problems.append(f"{label}: 띄웠다 {_workbench_lines(out)}")
        finally:
            _kill_recorded(ws)
    return problems


def _manual_server(ws: Path) -> subprocess.Popen[str]:
    proc = subprocess.Popen(
        [sys.executable, "-m", "workflow_kit", "workbench", "--project-profile-path", str(fx.profile(ws)),
         "--open", "owner", "--port", "0"],
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, encoding="utf-8", env=_env(), cwd=str(ws))
    assert proc.stdout is not None
    proc.stdout.readline()
    proc.stdout.close()
    # 이 검사가 부모다 — 거두지 않으면 SIGTERM 뒤에도 좀비로 '살아 있다'. 실물의 부모(셸)처럼 곧바로 거둔다.
    threading.Thread(target=proc.wait, daemon=True).start()
    return proc


def case_stop_safety() -> list[str]:
    problems: list[str] = []
    with fx.temp_workspace("wb-auto-5-") as td:
        ws = fx.make_workspace(td)
        manual = _manual_server(ws)
        try:
            stop = json.loads(_wb(ws, "--stop", "--autostarted-only").stdout)
            if stop.get("stopped") is not False or manual.poll() is not None:
                problems.append(f"--autostarted-only 가 손으로 띄운 서버를 내렸다: {stop}")
            stop = json.loads(_wb(ws, "--stop").stdout)
            try:
                manual.wait(timeout=15)
            except subprocess.TimeoutExpired:
                pass
            if stop.get("stopped") is not True or manual.poll() is None:
                problems.append(f"플래그 없는 --stop 이 손으로 띄운 서버를 내리지 않았다: {stop}")
        finally:
            if manual.poll() is None:
                manual.kill()
                manual.wait()
        # 기록의 pid 가 다른 프로세스 — 워크벤치로 답하지 않으면 죽이지 않는다.
        stranger = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
        threading.Thread(target=stranger.wait, daemon=True).start()
        try:
            with socket.socket() as sock:
                sock.bind(("127.0.0.1", 0))
                free = sock.getsockname()[1]
            wb_cli.ensure_record_dir(ws)
            (ws / ".workbench" / "server.json").write_text(json.dumps(
                {"pid": stranger.pid, "port": free, "public_url": f"http://127.0.0.1:{free}/", "started_at": "x",
                 "autostarted": True, "bind": "127.0.0.1"}), encoding="utf-8")
            stop = json.loads(_wb(ws, "--stop", "--autostarted-only").stdout)
            time.sleep(0.3)
            if stop.get("stopped") is not False or stranger.poll() is not None:
                problems.append(f"워크벤치가 아닌 pid 를 죽였다: {stop}")
        finally:
            stranger.kill()
            stranger.wait()
    return problems


def case_hook() -> list[str]:
    problems: list[str] = []
    for rel in ("plugin/hooks/hooks.json", "plugin/adapters/claude-code/hooks.json"):
        data = json.loads((REPO_ROOT / rel).read_text(encoding="utf-8"))
        commands = [hook.get("command", "") for entry in data["hooks"].get("SessionEnd", [])
                    for hook in entry.get("hooks", [])]
        if not any("workbench --stop --autostarted-only" in command for command in commands):
            problems.append(f"{rel}: SessionEnd 에 워크벤치 내리기가 없다")
    return problems


def case_timeout_reaps_child() -> list[str]:
    problems: list[str] = []
    with fx.temp_workspace("wb-auto-7-") as td:
        ws = fx.make_workspace(td)
        try:
            with mock.patch.dict(os.environ, _env(), clear=True), mock.patch.object(wb_cli, "DETACH_WAIT_S", 0.01):
                url, problem = wb_cli.start_detached(fx.profile(ws).resolve(), ["--open", "owner", "--port", "0"])
            if url is not None or not problem or "내렸다" not in problem:
                problems.append(f"시간 초과가 실패로 보고되지 않았다: {url} {problem}")
            time.sleep(1.5)  # 자식이 살아 있었다면 이 사이에 기록을 쓴다
            pid = _record_of(ws).get("pid")
            if isinstance(pid, int) and wb_cli.pid_alive(pid):
                problems.append(f"시간 초과 뒤에도 자식 서버가 살아 기록을 썼다: pid {pid}")
        finally:
            _kill_recorded(ws)
    return problems


CASES = (
    ("1 --autostart on/off · 인자 검증 · --status", case_config),
    ("2 session-start 가 띄우고 다시 띄우지 않는다 · --stop --autostarted-only", case_session_start_starts),
    ("3 시작 실패는 경고 한 줄", case_start_failure),
    ("4 검사 표식 · 끄는 env 면 띄우지 않는다", case_suppressed),
    ("5 내리기의 안전 — 손으로 띄운 서버 · 남의 pid", case_stop_safety),
    ("6 SessionEnd hook", case_hook),
    ("7 시간 초과는 자식을 거둔다", case_timeout_reaps_child),
)


def main() -> int:
    print("check_workbench_autostart — 워크벤치 자동 기동 (plan_workbench_spec §3.1)")
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
