#!/usr/bin/env python3
"""host serve registry CLI — federation §7.4 의 *쓰기* 쪽 (v1.1.2+, TASK-022).

TASK-016 이 `pull_remote_registry()` 로 *읽기* 를 닫았지만 상대편이 없었다. 읽을
곳을 아무도 서빙하지 않으니 `known_hosts` 의 endpoint 는 `file://` (sshfs mount
가정) 로만 쓸 수 있었고, `http://` 는 문서상의 형식일 뿐이었다. 본 CLI 가 그
`http://` 를 실제로 만든다.

## 안전 기본값

- **bind 는 `127.0.0.1`.** registry 에는 워크스페이스 절대 경로와 브랜치 이름이
  들어 있다. 파일은 0o600 인데 HTTP 는 0.0.0.0 이면 그 보호가 무의미하다.
  외부로 열려면 `--bind` 를 명시해야 하고, 그때 경고를 낸다.
- **read-only.** GET / HEAD 만. 쓰기 메서드는 405.
- **경로 2개만.** `/registry.json` + `/healthz`. 파일 시스템을 탐색하지 않는다.
- **토큰은 환경변수 이름으로 받는다** (`--token-env`). `--token=SECRET` 을 지원하지
  않는 이유는 `ps` 와 shell history 에 그대로 남기 때문이다.

## 사용법

```bash
# loopback 에 띄운다 (기본)
python3 workflow-source/tools/host_serve_registry.py --port 8765

# LAN 에 열고 토큰 요구
export WK_REGISTRY_TOKEN=$(python3 -c 'import secrets;print(secrets.token_urlsafe(32))')
python3 workflow-source/tools/host_serve_registry.py \
    --bind 0.0.0.0 --port 8765 --token-env WK_REGISTRY_TOKEN

# 설정만 확인하고 뜨지 않는다
python3 workflow-source/tools/host_serve_registry.py --check --json
```

상대 호스트에서는:

```bash
python3 workflow-source/tools/workspace_registry.py add-known-host \
    --host-id <이 호스트> --endpoint http://<host>:8765/registry.json
python3 workflow-source/tools/host_pull_registry.py pull --host <이 호스트>
```

Cross-ref: `core/multi_workspace_orchestration.md` §7.4 (TASK-016 / TASK-022).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from workflow_kit.common import registry_server as S  # noqa: E402
from workflow_kit.common import workspace_registry as R  # noqa: E402


def _print_json(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))


def _describe(args: argparse.Namespace, registry_path: Path) -> dict[str, Any]:
    import os

    token_present = bool(os.environ.get(args.token_env, "")) if args.token_env else False
    return {
        "bind": args.bind,
        "port": args.port,
        "loopback": S.is_loopback(args.bind),
        "registry_path": str(registry_path),
        "registry_exists": registry_path.is_file(),
        "token_env": args.token_env or None,
        "token_present": token_present,
        "routes": [S.REGISTRY_ROUTE, S.HEALTH_ROUTE],
        "endpoint_hint": f"http://<this-host>:{args.port}{S.REGISTRY_ROUTE}",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="host_serve_registry",
        description="Serve this host's workspace registry over HTTP (read-only).",
    )
    parser.add_argument(
        "--bind",
        default=S.DEFAULT_BIND,
        help=f"bind address (default: {S.DEFAULT_BIND} — loopback only)",
    )
    parser.add_argument(
        "--port", type=int, default=S.DEFAULT_PORT, help=f"port (default: {S.DEFAULT_PORT})"
    )
    parser.add_argument(
        "--registry-path",
        default=None,
        help="registry file to serve (default: workspace_registry.registry_path())",
    )
    parser.add_argument(
        "--token-env",
        default="",
        metavar="NAME",
        help="require `Authorization: Bearer <value>`; NAME is the ENV VAR NAME holding the value",
    )
    parser.add_argument("--quiet", action="store_true", help="suppress access log")
    parser.add_argument(
        "--check",
        action="store_true",
        help="print resolved configuration and exit without binding",
    )
    parser.add_argument(
        "--print-systemd-unit",
        action="store_true",
        dest="print_systemd_unit",
        help="상시 가동용 systemd user unit 을 stdout 에 출력하고 종료한다 "
             "(~/.config/systemd/user/ 에 저장 후 `systemctl --user enable --now`). "
             "토큰은 EnvironmentFile (%%h/.config/workflow_kit/registry_server.env) 로 공급",
    )
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args(argv)

    registry_path = (
        Path(args.registry_path).expanduser() if args.registry_path else R.registry_path()
    )

    info = _describe(args, registry_path)

    if args.print_systemd_unit:
        # 상시 가동의 **실행 가능한 경로** (TASK-2026-08-12-main-001). 절차를 산문으로만
        # 두면 호스트마다 손으로 unit 을 짜게 되고, 그 사본이 낡는다 (§11 과 같은 원리).
        # 토큰 검사는 하지 않는다 — unit 은 EnvironmentFile 에서 실행 시점에 읽는다.
        exec_parts = [
            sys.executable,
            str(Path(__file__).resolve()),
            "--bind", str(args.bind),
            "--port", str(args.port),
            "--quiet",
        ]
        if args.token_env:
            exec_parts += ["--token-env", args.token_env]
        if args.registry_path:
            exec_parts += ["--registry-path", str(registry_path)]
        env_file_line = (
            "EnvironmentFile=%h/.config/workflow_kit/registry_server.env\n"
            if args.token_env
            else ""
        )
        unit = (
            "[Unit]\n"
            "Description=Standard AI Workflow registry server (read-only federation serving)\n"
            "After=network.target\n"
            "\n"
            "[Service]\n"
            "Type=simple\n"
            f"{env_file_line}"
            f"ExecStart={' '.join(exec_parts)}\n"
            "Restart=on-failure\n"
            "RestartSec=5\n"
            "\n"
            "[Install]\n"
            "WantedBy=default.target\n"
        )
        print(unit, end="")
        print(
            "# 설치: 위 내용을 ~/.config/systemd/user/wk-registry.service 로 저장 후\n"
            "#   systemctl --user daemon-reload && systemctl --user enable --now wk-registry\n"
            + ("#   (토큰: ~/.config/workflow_kit/registry_server.env 에 "
               f"`{args.token_env}=<값>` 을 0o600 으로 저장)\n" if args.token_env else ""),
            file=sys.stderr,
        )
        return 0

    if args.token_env and not info["token_present"]:
        print(
            f"ERROR: --token-env {args.token_env} 가 지정됐지만 그 환경변수가 비어 있습니다. "
            f"토큰 없이 뜨면 인증이 사실상 꺼진 채로 열립니다.",
            file=sys.stderr,
        )
        return 2

    if not info["loopback"]:
        # 거부하지는 않는다 — LAN federation 은 정당한 사용이다. 다만 무엇을 여는지
        # 는 반드시 보이게 한다.
        print(
            f"WARNING: {args.bind} 는 loopback 이 아닙니다. registry 에는 워크스페이스 "
            f"절대 경로와 브랜치 이름이 들어 있습니다."
            + ("" if args.token_env else " --token-env 없이 여는 중입니다."),
            file=sys.stderr,
        )

    if args.check:
        if args.json:
            _print_json({"ok": True, **info})
        else:
            for key, value in info.items():
                print(f"{key}: {value}")
        return 0

    try:
        httpd = S.serve_registry(
            registry_path=registry_path,
            bind=args.bind,
            port=args.port,
            token_env=args.token_env,
            quiet=args.quiet,
        )
    except OSError as e:
        print(f"ERROR: bind {args.bind}:{args.port} 실패 — {type(e).__name__}: {e}", file=sys.stderr)
        return 2

    if args.json:
        _print_json({"ok": True, "serving": True, **info})
    else:
        print(f"serving {registry_path} on http://{args.bind}:{args.port}{S.REGISTRY_ROUTE}")
        print("Ctrl-C to stop.")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped.", file=sys.stderr)
    finally:
        httpd.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
