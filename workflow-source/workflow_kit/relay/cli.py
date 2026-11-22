"""``python -m workflow_kit hub relay …`` (스펙 §9.1)."""

from __future__ import annotations

import argparse
import json
import socket
import sys
from pathlib import Path
from typing import Any

from workflow_kit.relay import adapters, config
from workflow_kit.relay.conn import HubError, HubUnreachable, post


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="python -m workflow_kit hub relay", description="PC 중계 허브 (2.1)")
    sub = p.add_subparsers(dest="cmd", required=True)
    i = sub.add_parser("init", help="초대 코드로 이 PC 를 중앙 허브에 등록한다 (토큰은 600 파일에만)")
    i.add_argument("--hub", required=True)
    i.add_argument("--invite", required=True)
    i.add_argument("--name", default=socket.gethostname())
    i.add_argument("--harness", action="append", default=None, help=f"쓸 어댑터 (반복) — {' · '.join(adapters.ADAPTERS)}")
    a = sub.add_parser("allow", help="허용 목록 — 이 PC 에서 띄울 수 있는 디렉터리 · 하네스 · 권한 모드")
    asub = a.add_subparsers(dest="action", required=True)
    aa = asub.add_parser("add")
    aa.add_argument("--alias", required=True)
    aa.add_argument("--path", required=True)
    aa.add_argument("--project", default=None, help="기본: 등록한 프로젝트")
    aa.add_argument("--harness", action="append", required=True)
    aa.add_argument("--permission-mode", action="append", default=None)
    aa.add_argument("--max-sessions", type=int, default=1)
    ar = asub.add_parser("remove")
    ar.add_argument("--alias", required=True)
    asub.add_parser("list")
    s = sub.add_parser("serve", help="상주 — 중앙 폴링 · 세션 실행 · 메시지 넣기")
    s.add_argument("--once", action="store_true", help="폴링 한 번만 (검사 · 진단)")
    s.add_argument("--wait", type=int, default=25, help="긴 폴링 한 번 대기 초 (상한 25)")
    s.add_argument("--ui-port", type=int, default=None, help="로컬 화면 포트 (127.0.0.1 만) — 예: 8771. 주지 않으면 화면 없음")
    sub.add_parser("pause", help="이 PC 정지 — 폴링 · 실행을 멈춘다 (허브의 승인된 요청은 남는다)")
    sub.add_parser("resume")
    sub.add_parser("status")
    return p


def _out(obj: Any) -> None:
    print(json.dumps(obj, ensure_ascii=False, indent=2))


def main(argv: list[str] | None = None) -> int:
    raw = list(sys.argv[1:] if argv is None else argv)
    if raw and raw[0] == "__sandbox-policy":
        sp = argparse.ArgumentParser(prog="python -m workflow_kit hub relay __sandbox-policy")
        sp.add_argument("--sandbox", required=True)
        sp.add_argument("--cwd", required=True)
        sargs = sp.parse_args(raw[1:])
        from workflow_kit.relay.adapters import codex as cx

        _out({"policy": cx.sandbox_policy(sargs.sandbox, Path(sargs.cwd))})
        return 0
    args = _parser().parse_args(argv)
    if args.cmd == "init":
        harnesses = args.harness or ["claude-code", "codex"]
        bad = [h for h in harnesses if h not in adapters.ADAPTERS]
        if bad:
            print(f"relay: 모르는 어댑터 {bad}", file=sys.stderr)
            return 2
        try:
            got = post(args.hub, "/v1/relay/register", {"invite": args.invite, "name": args.name, "harnesses": harnesses})
        except HubError as e:
            print(f"relay: 등록 거절 — {e}", file=sys.stderr)
            return 1
        except HubUnreachable as e:
            print(f"relay: 허브에 닿지 않는다 — {e}", file=sys.stderr)
            return 2
        config.write_token(str(got["token"]))
        config.write_json("relay.json", {"hub": args.hub, "host_id": got["host_id"], "project_id": got["project_id"],
                                         "name": args.name, "harnesses": harnesses})
        _out({"status": "ok", "host_id": got["host_id"], "project_id": got["project_id"],
              "config": str(config.home()), "next": "hub relay allow add … → hub relay serve"})
        return 0
    if args.cmd == "allow":
        entries = config.load_allow()
        if args.action == "list":
            _out({"dir": entries, "digest": config.allow_digest(entries)})
            return 0
        if args.action == "remove":
            kept = [e for e in entries if e.get("alias") != args.alias]
            config.save_allow(kept)
            _out({"status": "ok", "removed": len(entries) - len(kept)})
            return 0
        entry = {"alias": args.alias, "path": args.path,
                 "project": args.project or config.read_json("relay.json", {}).get("project_id", ""),
                 "harnesses": args.harness, "permission_modes": args.permission_mode or ["default"],
                 "max_sessions": args.max_sessions}
        err = config.validate_entry(entry)
        if err:
            print(f"relay: 허용 목록 거절 — {err}", file=sys.stderr)
            return 2
        config.save_allow([e for e in entries if e.get("alias") != args.alias] + [entry])
        _out({"status": "ok", "entry": entry})
        return 0
    if args.cmd in ("pause", "resume"):
        state = config.read_json("relay-state.json", {})
        state["paused"] = args.cmd == "pause"
        config.write_json("relay-state.json", state)
        _out({"status": "ok", "paused": state["paused"]})
        return 0
    if args.cmd == "status":
        cfg = config.read_json("relay.json", {})
        _out({"registered": bool(cfg.get("host_id")) and config.read_token() is not None,
              **{k: cfg.get(k) for k in ("hub", "host_id", "project_id", "name", "harnesses")},
              "paused": bool(config.read_json("relay-state.json", {}).get("paused")),
              "allow": [e.get("alias") for e in config.load_allow()],
              "adapters": {h: adapters.get(h).probe() for h in (cfg.get("harnesses") or [])}})
        return 0
    from workflow_kit.relay.runner import Relay

    return Relay(log=lambda m: print(f"relay: {m}", file=sys.stderr, flush=True)).serve(once=args.once, wait_s=args.wait,
                                                                                                    ui_port=args.ui_port)


if __name__ == "__main__":
    sys.exit(main())
