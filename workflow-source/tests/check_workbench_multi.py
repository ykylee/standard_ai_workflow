#!/usr/bin/env python3
"""한 호스트에 워크벤치 여러 개 (`core/plan_workbench_spec.md` §3.2, TASK-2026-11-17-claude-remote-sync-check-234c32-005).

1. 포트 — checkout 경로 해시로 범위 안 한 포트, 같은 checkout 은 같은 포트, 후보는 범위를 한 바퀴
2. 저장소 이름 · 브랜치 — 일반 checkout · worktree(.git 파일)에서 저장소 이름과 HEAD 브랜치를 파일만 읽어 낸다
3. 두 checkout 이 `--port` 없이 뜬다 — 한쪽의 해시 포트를 다른 프로세스가 쥐고 있으면 다음 빈 포트로, 서로 다른 포트 ·
   실행 기록 · `--status` 가 실제 URL. 명시한 `--port` 가 차 있으면 넘어가지 않고 rc 2
4. 화면 머리와 `<title>` 에 저장소 이름 · 브랜치 이름
5. 호스트 공용 목록 — 뜬 서버가 등록되고 `--list` 가 저장소 · 브랜치 · URL 을 보이고, 죽은 pid 기록은 지우고,
   `--stop` 이 자기 기록을 지운다. 목록 위치는 임시 디렉터리(`WORKFLOW_KIT_WORKBENCH_REGISTRY`)
"""

from __future__ import annotations

#: 서버 subprocess 를 여러 번 띄운다.
CHECK_TIMEOUT_S = 240

#: 이 검사의 입력 표면 (spec `core/test_impact_tiering_spec.md` §2).
WATCHES = (
    "workflow-source/pyproject.toml",
    "workflow-source/workflow_kit/*",
    "workflow-source/tests/_workbench_fixture.py",
)

import json
import re
import socket
import subprocess
import sys
import tempfile
import threading
import traceback
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _workbench_fixture as fx  # noqa: E402

from workflow_kit.workbench import registry  # noqa: E402

FAILURES: list[str] = []


def _record(name: str, problems: list[str]) -> None:
    if problems:
        FAILURES.append(name)
        print(f"  FAIL  {name}")
        for problem in problems[:12]:
            print(f"        - {problem}")
    else:
        print(f"  PASS  {name}")


def case_ports() -> list[str]:
    problems: list[str] = []
    with tempfile.TemporaryDirectory(prefix="wb-multi-1a-") as a, tempfile.TemporaryDirectory(prefix="wb-multi-1b-") as b:
        pa, pb = registry.preferred_port(Path(a)), registry.preferred_port(Path(b))
        for port in (pa, pb):
            if not registry.PORT_BASE <= port < registry.PORT_BASE + registry.PORT_SPAN:
                problems.append(f"해시 포트가 범위 밖이다: {port}")
        if registry.preferred_port(Path(a)) != pa:
            problems.append("같은 checkout 의 포트가 부를 때마다 다르다")
        candidates = registry.candidate_ports(Path(a))
        if candidates[0] != pa or sorted(candidates) != list(range(registry.PORT_BASE, registry.PORT_BASE + registry.PORT_SPAN)):
            problems.append("후보가 해시 포트에서 시작해 범위를 한 바퀴 돌지 않는다")
    return problems


def case_names() -> list[str]:
    problems: list[str] = []
    with tempfile.TemporaryDirectory(prefix="wb-multi-2-") as td:
        root = Path(td)
        main = root / "myrepo"
        (main / ".git" / "worktrees" / "feat-x").mkdir(parents=True)
        (main / ".git" / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
        (main / ".git" / "worktrees" / "feat-x" / "HEAD").write_text("ref: refs/heads/feat/x\n", encoding="utf-8")
        wt = root / "myrepo-feat-x"
        wt.mkdir()
        (wt / ".git").write_text(f"gitdir: {main / '.git' / 'worktrees' / 'feat-x'}\n", encoding="utf-8")
        plain = root / "plain"
        plain.mkdir()
        for path, repo, branch in ((main, "myrepo", "main"), (wt, "myrepo", "feat/x"), (plain, "plain", None)):
            if registry.repo_name(path) != repo:
                problems.append(f"{path.name}: 저장소 이름 {registry.repo_name(path)!r} (기대 {repo!r})")
            if registry.head_branch(path) != branch:
                problems.append(f"{path.name}: 브랜치 {registry.head_branch(path)!r} (기대 {branch!r})")
        (main / ".git" / "HEAD").write_text("0123456789abcdef0123456789abcdef01234567\n", encoding="utf-8")
        if registry.head_branch(main) is not None:
            problems.append("분리 HEAD 를 브랜치로 읽었다")
    return problems


def _env(reg: Path) -> dict[str, str]:
    env = fx.env()
    env[registry.REGISTRY_ENV] = str(reg)
    return env


def _wb(ws: Path, reg: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, "-m", "workflow_kit", "workbench", "--project-profile-path", str(fx.profile(ws)),
                           *args], capture_output=True, encoding="utf-8", errors="replace", check=False, env=_env(reg),
                          cwd=str(ws), timeout=60)


def _start(ws: Path, reg: Path, *args: str) -> tuple[subprocess.Popen[str], str]:
    proc = subprocess.Popen([sys.executable, "-m", "workflow_kit", "workbench", "--project-profile-path", str(fx.profile(ws)),
                             "--open", "owner", *args], stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding="utf-8",
                            env=_env(reg), cwd=str(ws))
    assert proc.stdout is not None
    return proc, proc.stdout.readline().strip()


def _stop(proc: subprocess.Popen[str]) -> None:
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()


def _port(url: str) -> int | None:
    match = re.match(r"http://127\.0\.0\.1:(\d+)/$", url)
    return int(match.group(1)) if match else None


def case_two_checkouts() -> list[str]:
    problems: list[str] = []
    with fx.temp_workspace("wb-multi-3a-") as a, fx.temp_workspace("wb-multi-3b-") as b, \
            tempfile.TemporaryDirectory(prefix="wb-multi-reg-") as reg_dir:
        ws_a, ws_b, reg = fx.make_workspace(a), fx.make_workspace(b), Path(reg_dir)
        blocker = socket.socket()
        blocked: int | None = None
        for port in registry.candidate_ports(ws_a):  # a 의 해시 포트(차 있으면 그다음)를 다른 프로세스가 쥔다
            try:
                blocker.bind(("127.0.0.1", port))
                blocked = port
                break
            except OSError:
                continue
        blocker.listen(1)
        procs: list[subprocess.Popen[str]] = []
        try:
            proc_a, url_a = _start(ws_a, reg)
            procs.append(proc_a)
            proc_b, url_b = _start(ws_b, reg)
            procs.append(proc_b)
            port_a, port_b = _port(url_a), _port(url_b)
            if port_a is None or port_b is None:
                return [f"--port 없이 뜨지 않았다: a={url_a!r} b={url_b!r} {proc_a.poll()} {proc_b.poll()}"]
            span = range(registry.PORT_BASE, registry.PORT_BASE + registry.PORT_SPAN)
            if port_a not in span or port_b not in span or port_a == port_b:
                problems.append(f"포트가 범위 밖이거나 같다: a={port_a} b={port_b}")
            if port_a == blocked:
                problems.append(f"다른 프로세스가 쥔 포트 {blocked} 를 a 가 받았다")
            for ws, url in ((ws_a, url_a), (ws_b, url_b)):
                record = json.loads((ws / ".workbench" / "server.json").read_text(encoding="utf-8"))
                status = json.loads(_wb(ws, reg, "--status").stdout)
                if record.get("public_url") != url or status.get("public_url") != url or not status.get("running"):
                    problems.append(f"실행 기록 · --status 가 실제 URL 이 아니다: {record.get('public_url')} {status}")
            # 서버가 없는 세 번째 checkout 으로 — 서버가 떠 있는 checkout 은 '살아 있는 서버' 로 따로 rc 2 다
            with fx.temp_workspace("wb-multi-3c-") as c:
                ws_c = fx.make_workspace(c)
                fixed = subprocess.Popen(
                    [sys.executable, "-m", "workflow_kit", "workbench", "--project-profile-path", str(fx.profile(ws_c)),
                     "--open", "owner", "--port", str(blocked)], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    encoding="utf-8", env=_env(reg), cwd=str(ws_c))
                try:
                    rc = fixed.wait(timeout=20)
                except subprocess.TimeoutExpired:
                    rc = None
                    _stop(fixed)
                err = fixed.stderr.read() if fixed.stderr else ""
                if rc != 2 or f":{blocked} 에 bind 하지 못했다" not in err:
                    problems.append(f"명시한 --port {blocked} 가 차 있는데 rc {rc} {err[-120:]!r} (넘어가면 안 된다)")
        finally:
            for proc in procs:
                _stop(proc)
            blocker.close()
    return problems


def case_header() -> list[str]:
    problems: list[str] = []
    with fx.temp_workspace("wb-multi-4-") as td, tempfile.TemporaryDirectory(prefix="wb-multi-reg-") as reg_dir:
        ws = fx.make_workspace(td)
        proc, url = _start(ws, Path(reg_dir))
        try:
            html = urllib.request.urlopen(url, timeout=10).read().decode("utf-8")  # noqa: S310 — 로컬 검사 서버
        finally:
            _stop(proc)
        repo = registry.repo_name(ws)
        title = re.search(r"<title>(.*?)</title>", html)
        if not title or repo not in title.group(1) or fx.BRANCH not in title.group(1):
            problems.append(f"<title> 에 저장소 · 브랜치가 없다: {title.group(1) if title else None!r}")
        header = html.split("</header>")[0]
        if f"저장소 {repo}" not in header or f"브랜치 {fx.BRANCH}" not in header:
            problems.append("화면 머리에 저장소 · 브랜치가 없다")
    return problems


def case_list() -> list[str]:
    problems: list[str] = []
    with fx.temp_workspace("wb-multi-5a-") as a, fx.temp_workspace("wb-multi-5b-") as b, \
            tempfile.TemporaryDirectory(prefix="wb-multi-reg-") as reg_dir:
        ws_a, ws_b, reg = fx.make_workspace(a), fx.make_workspace(b), Path(reg_dir)
        dead = subprocess.Popen([sys.executable, "-c", "pass"])
        dead.wait()
        (reg / "dead.json").write_text(json.dumps({"pid": dead.pid, "port": 1, "public_url": "http://x/"}), encoding="utf-8")
        proc_a, url_a = _start(ws_a, reg)
        proc_b, url_b = _start(ws_b, reg)
        try:
            listed = _wb(ws_a, reg, "--list")
            try:
                entries = json.loads(listed.stdout)["workbenches"]
            except (json.JSONDecodeError, KeyError, TypeError):
                return [f"--list 출력이 JSON 목록이 아니다: rc {listed.returncode} {listed.stdout[:200]!r} {listed.stderr[-200:]!r}"]
            urls = sorted(e.get("public_url") for e in entries)
            if urls != sorted([url_a, url_b]):
                problems.append(f"--list 가 두 서버만 보이지 않는다: {urls}")
            for entry in entries:
                if not entry.get("repo") or "branch" not in entry or not entry.get("workspace"):
                    problems.append(f"목록 항목에 저장소 · 브랜치 · 작업 공간이 없다: {entry}")
            if (reg / "dead.json").exists():
                problems.append("죽은 pid 의 기록을 지우지 않았다")
            # 검사가 띄운 자식은 검사가 거둔다 — 거두지 않으면 좀비가 살아 있는 pid 로 보여 --stop 이 끝을 못 본다
            reaper = threading.Thread(target=proc_a.wait, daemon=True)
            reaper.start()
            stopped = json.loads(_wb(ws_a, reg, "--stop").stdout)
            reaper.join(timeout=15)
            remaining = json.loads(_wb(ws_b, reg, "--list").stdout)["workbenches"]
            if not stopped.get("stopped") or [e.get("public_url") for e in remaining] != [url_b]:
                problems.append(f"--stop 뒤 목록에 내린 서버가 남았다: {stopped} {remaining}")
        finally:
            _stop(proc_a)
            _stop(proc_b)
    return problems


CASES = (
    ("1 포트 — 경로 해시 · 같은 checkout 같은 포트 · 범위 한 바퀴", case_ports),
    ("2 저장소 이름 · 브랜치 — 일반 · worktree · 분리 HEAD", case_names),
    ("3 두 checkout 이 --port 없이 — 차 있으면 다음 포트 · 기록 · --status · 명시 포트는 넘어가지 않음", case_two_checkouts),
    ("4 화면 머리 · <title> 에 저장소 · 브랜치", case_header),
    ("5 호스트 공용 목록 — 등록 · --list · 죽은 기록 청소 · --stop 이 지움", case_list),
)


def main() -> int:
    print("check_workbench_multi — 한 호스트에 워크벤치 여러 개 (plan_workbench_spec §3.2)")
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
