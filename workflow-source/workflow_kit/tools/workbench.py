#!/usr/bin/env python3
"""`workbench` — 브라우저에서 계획과 진척을 읽고 결정에 답하는 서버 (`core/plan_workbench_spec.md` §2 · §3).

- 서버가 쓰는 워크플로우 상태는 받은편지함 하나다. 그 밖에는 checkout 루트의 ``.workbench/server.json`` 과
  그 디렉터리의 ``.gitignore`` 뿐이다.
- 모델은 서버를 조작하지 않는다 — 사람이 띄우고 URL 을 연다.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import signal
import ssl
import sys
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
    parser.add_argument("--status", action="store_true", help="실행 기록을 JSON 으로 내고 끝난다")
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
            "public_url": record.get("public_url"), "started_at": record.get("started_at")}


def running_public_url(workspace: Path) -> str | None:
    """살아 있는 서버의 ``public_url`` — ``session-start`` 가 보고에 싣는다 (스펙 §3 · §8.2)."""
    status = status_of(workspace)
    url = status.get("public_url")
    return url if status["running"] and isinstance(url, str) else None


def write_record(workspace: Path, *, port: int, public_url: str) -> Path:
    directory = ensure_record_dir(workspace)
    path = directory / RECORD_FILENAME
    payload = {"pid": os.getpid(), "port": port, "public_url": public_url,
               "started_at": dt.datetime.now().astimezone().isoformat(timespec="seconds")}
    temp = directory / f".{RECORD_FILENAME}.{os.getpid()}"
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temp, path)
    return path


def remove_record(workspace: Path) -> None:
    record = read_record(workspace)
    if record is not None and record.get("pid") == os.getpid():
        (record_dir(workspace) / RECORD_FILENAME).unlink(missing_ok=True)


def sweep_temp_files(branch_dir: Path) -> list[str]:
    """받은편지함의 죽은 pid 임시 파일(``.tmp-<pid>-*``)을 지운다 (스펙 §6 끝) — 형식은 ``plan_responses`` 가 안다."""
    return plan_responses.sweep_dead_temp_files(branch_dir, alive=pid_alive)


# --------------------------------------------------------------------------- 시작 판정 (§2)


def validate_start(args: argparse.Namespace, workspace: Path) -> tuple[tuple[auth.Token, ...], str]:
    """시작을 거절할 이유가 있으면 :class:`StartRefused`. 아니면 (토큰, public_url)."""
    try:
        tokens = auth.load_tokens(args.token)
    except auth.TokenError as exc:
        raise StartRefused(str(exc)) from None
    if not 0 <= args.port <= 65535:
        raise StartRefused(f"포트가 범위 밖이다: {args.port}")
    public_url = server.normalize_public_url(args.public_url or f"http://{DEFAULT_BIND}:{args.port}/")
    scheme = urlsplit(public_url).scheme.lower()
    if scheme not in ("http", "https") or not urlsplit(public_url).netloc:
        raise StartRefused(f"public_url 은 http(s)://호스트/ 꼴이다: {public_url}")
    tls = bool(args.tls_cert or args.tls_key)
    if tls and not (args.tls_cert and args.tls_key):
        raise StartRefused("TLS 는 --tls-cert 와 --tls-key 를 같이 준다")
    if tls and scheme == "http":
        raise StartRefused("TLS 를 켰는데 public_url 이 http 다")
    if not server.is_loopback(args.bind) and not tls and not args.allow_plain_http:
        raise StartRefused(f"--bind {args.bind} 는 loopback 이 아니다 — TLS 또는 --allow-plain-http 가 필요하다")
    live = status_of(workspace)
    if live["running"]:
        raise StartRefused(f"이 checkout 에 살아 있는 서버가 있다: {live.get('public_url')}")
    return tokens, public_url


def startup_warnings(bind: str) -> list[str]:
    """시작 때 표준 오류에 낼 경고 — loopback 이 아닌 bind 면 한 줄 (스펙 §2)."""
    if server.is_loopback(bind):
        return []
    return [f"workbench: 경고 — loopback 이 아닌 주소 {bind} 에 bind 했다"]


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
    try:
        tokens, public_url = validate_start(args, workspace)
    except StartRefused as exc:
        print(f"workbench: {exc}", file=sys.stderr)
        return 2
    locate = server.where_for(profile)
    app = server.App(public_url=public_url, tokens=tokens, locate=locate,
                     trusted_proxies=frozenset(args.trusted_proxy))
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
        public_url = app.public_url = f"http://{DEFAULT_BIND}:{port}/"
    write_record(workspace, port=port, public_url=public_url)
    sweep_temp_files(locate().branch_dir)
    print(public_url, flush=True)
    for note in startup_warnings(args.bind):
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
