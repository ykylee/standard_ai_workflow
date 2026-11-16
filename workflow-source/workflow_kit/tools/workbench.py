#!/usr/bin/env python3
"""`workbench` — 브라우저에서 계획과 진척을 읽고 결정에 답하는 서버 (`core/plan_workbench_spec.md` §2 · §3).

- 서버가 쓰는 워크플로우 상태는 받은편지함 하나다. 그 밖에는 checkout 루트의 ``.workbench/server.json`` 과
  그 디렉터리의 ``.gitignore`` 뿐이다.
- 모델은 서버를 조작하지 않는다 — 사람이 띄우고 URL 을 연다. 소유자가 ``--autostart on`` 으로 켜 두면
  ``session-start`` 가 띄우고 플러그인 SessionEnd hook 이 ``--stop --autostarted-only`` 로 내린다 (스펙 §3.1).
"""

from __future__ import annotations

import argparse
import datetime as dt
import http.client
import json
import os
import signal
import socket
import ssl
import subprocess
import sys
import time
import warnings
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from workflow_kit.common import plan_responses
from workflow_kit.common.paths import discover_project_profile_path, project_workspace_root
from workflow_kit.common.stdio import force_utf8_stdio
from workflow_kit.workbench import auth, server

DEFAULT_BIND = "127.0.0.1"
DEFAULT_PORT = 8766
RECORD_DIRNAME = ".workbench"
RECORD_FILENAME = "server.json"
GITIGNORE_BODY = "*\n"
AUTOSTART_FILENAME = "autostart.json"
LOG_FILENAME = "server.log"
#: 있으면 ``session-start`` 가 띄우지 않는다. 검사 표식(``WORKFLOW_KIT_TELEMETRY_SKIP_ROOT``)이 이 작업 공간을
#: 가리킬 때도 — 러너 · 스모크가 살아 있는 저장소에서 session-start 를 부를 때 서버를 남기지 않게.
AUTOSTART_OFF_ENV = "WORKFLOW_KIT_NO_WORKBENCH_AUTOSTART"
CHECK_MARK_ENV = "WORKFLOW_KIT_TELEMETRY_SKIP_ROOT"
DETACH_WAIT_S = 15.0
STOP_WAIT_S = 10.0


class StartRefused(Exception):
    """시작 거절 — 메시지가 이유 한 줄이다 (rc 2)."""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m workflow_kit workbench",
        description="계획 · 진척 워크벤치 서버를 띄운다 (core/plan_workbench_spec.md).",
        allow_abbrev=False,
    )
    parser.add_argument("--bind", default=DEFAULT_BIND)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--public-url", default=None)
    parser.add_argument("--token", action="append", default=[],
                        help="<viewer|approver>:<name>=env:<VAR> 또는 =file:<경로> (반복)")
    parser.add_argument("--trusted-proxy", action="append", default=[])
    parser.add_argument("--tls-cert", default=None)
    parser.add_argument("--tls-key", default=None)
    parser.add_argument("--allow-plain-http", action="store_true")
    parser.add_argument("--open", default=None, metavar="NAME",
                        help="개방 모드 — 토큰 · 로그인 없이 누구나 NAME 이름으로 보고 답한다 (스펙 §5.6)")
    parser.add_argument("--status", action="store_true", help="실행 기록을 JSON 으로 내고 끝난다")
    parser.add_argument("--autostart", choices=("on", "off"), default=None,
                        help="on: 함께 준 시작 인자를 저장해 session-start 가 띄우게 한다 · off: 지운다 (스펙 §3.1)")
    parser.add_argument("--stop", action="store_true", help="이 checkout 의 서버를 내린다")
    parser.add_argument("--autostarted-only", action="store_true", help="--stop 을 자동 기동한 서버에만")
    parser.add_argument("--autostarted", action="store_true", help=argparse.SUPPRESS)  # 자동 기동한 자식의 표식
    parser.add_argument("--new-token", default=None, metavar="ROLE:NAME",
                        help="토큰을 0600 파일로 만든다 (값은 출력하지 않는다)")
    parser.add_argument("--out", default=None, help="--new-token 의 출력 파일")
    parser.add_argument("--project-profile-path", default=None, help="미지정 시 cwd 상위에서 자동 탐색")
    return parser


# --------------------------------------------------------------------------- 실행 기록 (§3)


def pid_alive(pid: object) -> bool:
    if not isinstance(pid, int) or pid <= 0:
        return False
    if pid == os.getpid():
        return True
    if os.name == "nt":  # os.kill(pid, 0) 은 Windows 에서 CTRL_C_EVENT 다 — 쓰지 않는다
        import ctypes

        kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
        handle = kernel32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
        if not handle:
            return False
        code = ctypes.c_ulong()
        kernel32.GetExitCodeProcess(handle, ctypes.byref(code))
        kernel32.CloseHandle(handle)
        return code.value == 259  # STILL_ACTIVE
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def record_dir(workspace: Path) -> Path:
    return workspace / RECORD_DIRNAME


def ensure_record_dir(workspace: Path) -> Path:
    """``.workbench/`` 와 자기 무시 ``.gitignore`` — 내용을 매번 바이트로 확인한다 (스펙 §3)."""
    directory = record_dir(workspace)
    directory.mkdir(exist_ok=True)
    ignore = directory / ".gitignore"
    try:
        current = ignore.read_bytes() if ignore.is_file() else None
    except OSError:
        current = None
    if current != GITIGNORE_BODY.encode("utf-8"):
        ignore.write_bytes(GITIGNORE_BODY.encode("utf-8"))
    return directory


def read_record(workspace: Path) -> dict[str, Any] | None:
    try:
        data = json.loads((record_dir(workspace) / RECORD_FILENAME).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def status_of(workspace: Path) -> dict[str, Any]:
    record = read_record(workspace) or {}
    running = pid_alive(record.get("pid"))
    return {"running": running, "pid": record.get("pid"), "port": record.get("port"),
            "public_url": record.get("public_url"), "started_at": record.get("started_at"),
            "autostarted": record.get("autostarted") is True, "autostart": read_autostart(workspace) is not None}


def running_public_url(workspace: Path) -> str | None:
    """살아 있는 서버의 ``public_url`` — ``session-start`` 가 보고에 싣는다 (스펙 §3 · §8.2)."""
    status = status_of(workspace)
    url = status.get("public_url")
    return url if status["running"] and isinstance(url, str) else None


def write_record(workspace: Path, *, port: int, public_url: str, autostarted_bind: str | None = None) -> Path:
    directory = ensure_record_dir(workspace)
    path = directory / RECORD_FILENAME
    payload: dict[str, Any] = {"pid": os.getpid(), "port": port, "public_url": public_url,
                               "started_at": dt.datetime.now().astimezone().isoformat(timespec="seconds")}
    if autostarted_bind is not None:  # 자동 기동분만 — SessionEnd hook 이 이것만 내린다
        payload.update({"autostarted": True, "bind": autostarted_bind})
    temp = directory / f".{RECORD_FILENAME}.{os.getpid()}"
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temp, path)
    return path


def remove_record(workspace: Path) -> None:
    record = read_record(workspace)
    if record is not None and record.get("pid") == os.getpid():
        (record_dir(workspace) / RECORD_FILENAME).unlink(missing_ok=True)


# --------------------------------------------------------------------------- 자동 기동 (§3.1)


def start_argv(args: argparse.Namespace) -> list[str]:
    """시작 인자를 다시 명령줄로 — 토큰은 값이 아니라 ``env:`` · ``file:`` 참조만 실린다."""
    out: list[str] = []
    if args.bind != DEFAULT_BIND:
        out += ["--bind", args.bind]
    if args.port != DEFAULT_PORT:
        out += ["--port", str(args.port)]
    for flag, value in (("--public-url", args.public_url), ("--tls-cert", args.tls_cert),
                        ("--tls-key", args.tls_key), ("--open", args.open)):
        if value is not None:
            out += [flag, value]
    for token in args.token:
        out += ["--token", token]
    for proxy in args.trusted_proxy:
        out += ["--trusted-proxy", proxy]
    if args.allow_plain_http:
        out.append("--allow-plain-http")
    return out


def read_autostart(workspace: Path) -> list[str] | None:
    try:
        data = json.loads((record_dir(workspace) / AUTOSTART_FILENAME).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError):
        return None
    argv = data.get("argv") if isinstance(data, dict) else None
    return argv if isinstance(argv, list) and all(isinstance(item, str) for item in argv) else None


def write_autostart(workspace: Path, argv: list[str]) -> Path:
    directory = ensure_record_dir(workspace)
    path = directory / AUTOSTART_FILENAME
    payload = {"argv": argv, "saved_at": dt.datetime.now().astimezone().isoformat(timespec="seconds")}
    temp = directory / f".{AUTOSTART_FILENAME}.{os.getpid()}"
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temp, path)
    return path


def autostart_suppressed(workspace: Path, environ: dict[str, str] | None = None) -> bool:
    env = os.environ if environ is None else environ
    if env.get(AUTOSTART_OFF_ENV):
        return True
    mark = env.get(CHECK_MARK_ENV)
    if not mark:
        return False
    try:
        return Path(mark).resolve() == workspace.resolve()
    except OSError:
        return True


def start_detached(profile: Path, argv: list[str]) -> tuple[str | None, str | None]:
    """서버를 이 프로세스와 떨어진 자식으로 띄우고 실행 기록을 기다린다 — (public_url, 실패 사유)."""
    workspace = project_workspace_root(profile)
    directory = ensure_record_dir(workspace)
    command = [sys.executable, "-m", "workflow_kit", "workbench", "--project-profile-path", str(profile),
               *argv, "--autostarted"]
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONPATH"] = os.pathsep.join(entry for entry in sys.path if entry)
    detach: dict[str, Any] = {}
    if os.name == "nt":
        detach["creationflags"] = (getattr(subprocess, "DETACHED_PROCESS", 0x8)
                                   | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0x200)
                                   | getattr(subprocess, "CREATE_NO_WINDOW", 0x8000000))
    else:
        detach["start_new_session"] = True  # 세션이 끝나도 SIGHUP 을 받지 않는다
    log = directory / LOG_FILENAME
    with open(log, "wb") as handle:
        proc = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=handle, stderr=handle,
                                cwd=str(workspace), env=env, close_fds=True, **detach)
    try:
        deadline = time.monotonic() + DETACH_WAIT_S
        while time.monotonic() < deadline:
            record = read_record(workspace) or {}
            url = record.get("public_url")
            if record.get("pid") == proc.pid and isinstance(url, str):
                return url, None
            code = proc.poll()
            if code is not None:
                try:
                    tail = [ln for ln in log.read_text(encoding="utf-8", errors="replace").splitlines() if ln.strip()]
                except OSError:
                    tail = []
                return None, f"서버가 시작하지 못했다 (rc {code}){' — ' + tail[-1] if tail else ''}"
            time.sleep(0.1)
        # 기록을 쓰지 않은 자식은 누구도 내릴 수 없는 고아가 된다 — 여기서 거둔다.
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
        return None, f"서버가 {DETACH_WAIT_S:.0f}초 안에 실행 기록을 쓰지 않았다 — 자식을 내렸다 ({log})"
    finally:
        # 자식은 일부러 떠나보낸다 — 살아 있는 Popen 을 놓을 때의 ResourceWarning 은 결함이 아니다.
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", ResourceWarning)
            del proc


def autostart_if_configured(profile: Path) -> tuple[str | None, str | None]:
    """``session-start`` 가 부른다 — 설정이 있고 살아 있는 서버가 없으면 띄운다 (스펙 §3.1)."""
    workspace = project_workspace_root(profile)
    argv = read_autostart(workspace)
    if argv is None or autostart_suppressed(workspace) or status_of(workspace)["running"]:
        return None, None
    url, problem = start_detached(profile, argv)
    return url, (f"워크벤치 자동 기동 실패 — {problem}" if problem else None)


def _answers_healthz(record: dict[str, Any]) -> bool:
    """기록의 포트가 워크벤치로 답하는가 — 죽은 서버의 pid 가 다른 프로세스에 재사용됐을 때 죽이지 않게."""
    port = record.get("port")
    if not isinstance(port, int):
        return False
    bind = record.get("bind")
    hosts = ["127.0.0.1"]
    if isinstance(bind, str) and bind not in ("", "0.0.0.0", "::") and not server.is_loopback(bind):
        hosts.insert(0, bind)
    https = str(record.get("public_url", "")).lower().startswith("https://")
    for host in hosts:
        conn: http.client.HTTPConnection
        if https:
            conn = http.client.HTTPSConnection(host, port, timeout=2, context=ssl._create_unverified_context())
        else:
            conn = http.client.HTTPConnection(host, port, timeout=2)
        try:
            conn.request("GET", "/healthz")
            resp = conn.getresponse()
            if resp.status == 200 and resp.read(16).strip() == b"ok":
                return True
        except (OSError, http.client.HTTPException):
            continue
        finally:
            conn.close()
    return False


def stop_server(workspace: Path, *, autostarted_only: bool = False) -> dict[str, Any]:
    record = read_record(workspace) or {}
    pid = record.get("pid")
    if not pid_alive(pid) or pid == os.getpid():
        return {"stopped": False, "reason": "실행 중인 서버가 없다"}
    assert isinstance(pid, int)
    if autostarted_only and record.get("autostarted") is not True:
        return {"stopped": False, "pid": pid, "reason": "손으로 띄운 서버다 — 두고 간다"}
    if not _answers_healthz(record):
        return {"stopped": False, "pid": pid, "reason": "기록의 pid 가 워크벤치로 답하지 않는다 — 건드리지 않는다"}
    os.kill(pid, signal.SIGTERM)  # Windows 는 TerminateProcess — 기록은 아래에서 지운다
    deadline = time.monotonic() + STOP_WAIT_S
    while pid_alive(pid) and time.monotonic() < deadline:
        time.sleep(0.1)
    if pid_alive(pid):
        return {"stopped": False, "pid": pid, "reason": f"{STOP_WAIT_S:.0f}초 안에 끝나지 않았다"}
    if (read_record(workspace) or {}).get("pid") == pid:
        (record_dir(workspace) / RECORD_FILENAME).unlink(missing_ok=True)
    return {"stopped": True, "pid": pid}


def sweep_temp_files(branch_dir: Path) -> list[str]:
    """받은편지함의 죽은 pid 임시 파일(``.tmp-<pid>-*``)을 지운다 (스펙 §6 끝) — 형식은 ``plan_responses`` 가 안다."""
    return plan_responses.sweep_dead_temp_files(branch_dir, alive=pid_alive)


# --------------------------------------------------------------------------- 시작 판정 (§2)


def lan_address() -> str:
    """기본 경로의 이 호스트 주소 — UDP ``connect`` 는 패킷을 보내지 않는다. 못 찾으면 loopback."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
            probe.connect(("192.0.2.1", 9))  # TEST-NET-1 (RFC 5737)
            address = str(probe.getsockname()[0])
    except OSError:
        return DEFAULT_BIND
    return address if address and not address.startswith("0.") else DEFAULT_BIND


def default_public_url(bind: str, port: int, *, open_mode: bool) -> str:
    """``--public-url`` 이 없을 때의 주소 — 개방 모드로 loopback 밖에 bind 하면 다른 기기가 열 수 있는 주소다."""
    host = DEFAULT_BIND
    if open_mode and not server.is_loopback(bind):
        host = lan_address() if bind in ("", "0.0.0.0", "::") else bind
    if ":" in host:
        host = f"[{host}]"
    return f"http://{host}:{port}/"


def validate_start(args: argparse.Namespace, workspace: Path, *,
                   check_live: bool = True) -> tuple[tuple[auth.Token, ...], str]:
    """시작을 거절할 이유가 있으면 :class:`StartRefused`. 아니면 (토큰, public_url)."""
    open_mode = args.open is not None
    if open_mode:
        if args.token:
            raise StartRefused("--open 과 --token 은 같이 줄 수 없다")
        if not auth.NAME_RE.match(args.open):
            raise StartRefused(f"--open 의 이름은 [A-Za-z0-9_-]{{1,32}} 이다: {args.open[:40]}")
        tokens: tuple[auth.Token, ...] = ()
    else:
        try:
            tokens = auth.load_tokens(args.token)
        except auth.TokenError as exc:
            raise StartRefused(str(exc)) from None
    if not 0 <= args.port <= 65535:
        raise StartRefused(f"포트가 범위 밖이다: {args.port}")
    public_url = server.normalize_public_url(
        args.public_url or default_public_url(args.bind, args.port, open_mode=open_mode))
    scheme = urlsplit(public_url).scheme.lower()
    if scheme not in ("http", "https") or not urlsplit(public_url).netloc:
        raise StartRefused(f"public_url 은 http(s)://호스트/ 꼴이다: {public_url}")
    tls = bool(args.tls_cert or args.tls_key)
    if tls and not (args.tls_cert and args.tls_key):
        raise StartRefused("TLS 는 --tls-cert 와 --tls-key 를 같이 준다")
    if tls and scheme == "http":
        raise StartRefused("TLS 를 켰는데 public_url 이 http 다")
    if not open_mode and not server.is_loopback(args.bind) and not tls and not args.allow_plain_http:
        raise StartRefused(f"--bind {args.bind} 는 loopback 이 아니다 — TLS 또는 --allow-plain-http 가 필요하다")
    live = status_of(workspace) if check_live else {"running": False}
    if live["running"]:
        raise StartRefused(f"이 checkout 에 살아 있는 서버가 있다: {live.get('public_url')}")
    return tokens, public_url


def startup_warnings(bind: str, *, open_name: str | None = None) -> list[str]:
    """시작 때 표준 오류에 낼 경고 — loopback 이 아닌 bind 이거나 개방 모드면 한 줄 (스펙 §2 · §5.6)."""
    where = "" if server.is_loopback(bind) else f" loopback 이 아닌 주소 {bind} 에"
    if open_name is not None:
        return [f"workbench: 경고 —{where} 인증 없이 열었다 — 접속할 수 있는 누구나 {open_name} 이름으로 결정에 답한다"]
    if not where:
        return []
    return [f"workbench: 경고 —{where} bind 했다"]


def _new_token(args: argparse.Namespace) -> int:
    try:
        role, name = auth.parse_role_name(args.new_token)
    except auth.TokenError as exc:
        print(f"workbench: {exc}", file=sys.stderr)
        return 2
    if not args.out:
        print("workbench: --new-token 은 --out <경로> 가 필요하다", file=sys.stderr)
        return 2
    out = Path(args.out).expanduser()
    try:
        auth.write_new_token(out)
    except FileExistsError:
        print(f"workbench: 파일이 이미 있다 — 덮지 않는다: {out}", file=sys.stderr)
        return 2
    print(json.dumps({"status": "ok", "role": role, "name": name, "path": str(out),
                      "token_arg": f"{role}:{name}=file:{out}"}, ensure_ascii=False))
    return 0


def _profile(args: argparse.Namespace) -> Path | None:
    if args.project_profile_path:
        return Path(args.project_profile_path).resolve()
    found = discover_project_profile_path()
    return found.resolve() if found else None


def main(argv: list[str] | None = None) -> int:
    force_utf8_stdio()
    args = build_parser().parse_args(argv)
    if args.new_token is not None:
        return _new_token(args)
    profile = _profile(args)
    if profile is None or not profile.is_file():
        print("workbench: PROJECT_PROFILE.md 를 찾지 못했다 — --project-profile-path 로 준다", file=sys.stderr)
        return 2
    workspace = project_workspace_root(profile)
    if args.status:
        print(json.dumps(status_of(workspace), ensure_ascii=False))
        return 0
    if args.autostart == "off":
        (record_dir(workspace) / AUTOSTART_FILENAME).unlink(missing_ok=True)
        print(json.dumps({"status": "ok", "autostart": "off"}, ensure_ascii=False))
        return 0
    if args.autostart == "on":
        try:
            validate_start(args, workspace, check_live=False)
        except StartRefused as exc:
            print(f"workbench: {exc}", file=sys.stderr)
            return 2
        argv = start_argv(args)
        path = write_autostart(workspace, argv)
        print(json.dumps({"status": "ok", "autostart": "on", "argv": argv, "path": str(path),
                          "note": "다음 session-start 가 띄운다"}, ensure_ascii=False))
        return 0
    if args.stop:
        print(json.dumps(stop_server(workspace, autostarted_only=args.autostarted_only), ensure_ascii=False))
        return 0
    try:
        tokens, public_url = validate_start(args, workspace)
    except StartRefused as exc:
        print(f"workbench: {exc}", file=sys.stderr)
        return 2
    locate = server.where_for(profile)
    app = server.App(public_url=public_url, tokens=tokens, locate=locate,
                     trusted_proxies=frozenset(args.trusted_proxy), open_name=args.open)
    try:
        httpd = server.make_server(app, args.bind, args.port)
    except OSError as exc:
        print(f"workbench: {args.bind}:{args.port} 에 bind 하지 못했다 — {exc.strerror or exc}", file=sys.stderr)
        return 2
    if args.tls_cert:
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        try:
            context.load_cert_chain(args.tls_cert, args.tls_key)
        except (OSError, ssl.SSLError) as exc:
            httpd.server_close()
            print(f"workbench: TLS 인증서를 읽지 못했다 — {exc}", file=sys.stderr)
            return 2
        httpd.socket = context.wrap_socket(httpd.socket, server_side=True)
    port = httpd.server_address[1]
    if args.public_url is None and port != args.port:  # --port 0 — 기본 public_url 은 실제 포트로
        public_url = app.public_url = default_public_url(args.bind, port, open_mode=args.open is not None)
    write_record(workspace, port=port, public_url=public_url,
                 autostarted_bind=args.bind if args.autostarted else None)
    sweep_temp_files(locate().branch_dir)
    print(public_url, flush=True)
    for note in startup_warnings(args.bind, open_name=args.open):
        print(note, file=sys.stderr, flush=True)

    def _stop(signum: int, frame: object) -> None:
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, _stop)
    try:
        httpd.serve_forever(poll_interval=0.2)
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
        remove_record(workspace)
    return 0


if __name__ == "__main__":
    sys.exit(main())
