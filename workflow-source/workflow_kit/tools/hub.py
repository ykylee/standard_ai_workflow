"""``python -m workflow_kit hub`` — 워크플로우 허브 (2.0) 서버 명령 (hub_spec §2.1).

    hub serve  --db PATH [--bind 127.0.0.1] [--port 8770] [--public-url URL]
    hub backup --db PATH --out PATH
    hub admin  --db PATH token issue --role {web,admin} --name NAME
    hub admin  --db PATH token revoke --name NAME
    hub admin  --db PATH callsign revoke --project ID --callsign NAME
    hub admin  --db PATH guide set --project ID --file PATH [--actor NAME]

``admin`` 은 DB 파일에 직접 접근하는 로컬 명령이다 — 네트워크로 열지 않는다.
허브 쪽 의존(``mcp`` · ASGI 서버)은 ``workflow_kit[hub]`` 로 깐다 (DS1).
"""

from __future__ import annotations

import argparse
import ipaddress
import json
import sys
from pathlib import Path

from workflow_kit.common.stdio import force_utf8_stdio


def _is_loopback(bind: str) -> bool:
    if bind == "localhost":
        return True
    try:
        return ipaddress.ip_address(bind).is_loopback
    except ValueError:
        return False


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="python -m workflow_kit hub", description="워크플로우 허브 (2.0) 서버")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("serve", help="허브를 띄운다 (DB 이관 후)")
    s.add_argument("--db", required=True, type=Path)
    s.add_argument("--bind", default="127.0.0.1")
    s.add_argument("--port", type=int, default=8770)
    s.add_argument("--public-url", default=None, help="허브의 공개 주소 — 기본은 http://<bind>:<port>")

    b = sub.add_parser("backup", help="돌고 있는 허브의 DB 를 일관되게 복사한다")
    b.add_argument("--db", required=True, type=Path)
    b.add_argument("--out", required=True, type=Path)

    a = sub.add_parser("admin", help="로컬 관리 (토큰 · 콜사인)")
    a.add_argument("--db", required=True, type=Path)
    asub = a.add_subparsers(dest="what", required=True)
    tok = asub.add_parser("token")
    tsub = tok.add_subparsers(dest="action", required=True)
    ti = tsub.add_parser("issue")
    ti.add_argument("--role", required=True, choices=["web", "admin"])
    ti.add_argument("--name", required=True)
    tr = tsub.add_parser("revoke")
    tr.add_argument("--name", required=True)
    gd = asub.add_parser("guide")
    gsub = gd.add_subparsers(dest="action", required=True)
    gs = gsub.add_parser("set", help="프로젝트 지침 새 판 (제안 · 승인 흐름은 M-037)")
    gs.add_argument("--project", required=True)
    gs.add_argument("--file", required=True, type=Path)
    gs.add_argument("--actor", default="hub-admin")
    cs = asub.add_parser("callsign")
    csub = cs.add_subparsers(dest="action", required=True)
    cr = csub.add_parser("revoke")
    cr.add_argument("--project", required=True)
    cr.add_argument("--callsign", required=True)
    return p


def main(argv: list[str] | None = None) -> int:
    force_utf8_stdio()
    args = _parser().parse_args(argv)
    try:
        from workflow_kit.hub import db as hubdb
        from workflow_kit.hub.errors import HubError
        from workflow_kit.hub.store import Ctx, Store
    except ImportError as exc:  # pragma: no cover - 설치 안내
        print(f"hub: 허브 의존이 없다 — `pip install 'workflow_kit[hub]'` ({exc})", file=sys.stderr)
        return 2
    from workflow_kit.hub.app import utc_now

    now = utc_now()
    try:
        if args.cmd == "backup":
            hubdb.backup(args.db, args.out)
            print(json.dumps({"status": "ok", "backup": str(args.out)}, ensure_ascii=False))
            return 0
        copies = hubdb.open_db(args.db, now=now)
        store = Store(args.db)
        if args.cmd == "admin":
            if args.what == "token" and args.action == "issue":
                token = store.issue_hub_token(args.role, args.name, now)
                print(json.dumps({"status": "ok", "name": args.name, "role": args.role, "token": token}, ensure_ascii=False))
            elif args.what == "token":
                store.revoke_hub_token(args.name, now)
                print(json.dumps({"status": "ok", "revoked": args.name}, ensure_ascii=False))
            elif args.what == "guide":
                from workflow_kit.hub.setup import Setup

                out = Setup(store, "").set_guide(Ctx(now=now, via="admin"), args.project,
                                                 args.file.read_text(encoding="utf-8"), args.actor)
                print(json.dumps({"status": "ok", **out}, ensure_ascii=False))
            else:
                out = store.revoke_callsign(Ctx(now=now, via="admin"), args.project, args.callsign)
                print(json.dumps({"status": "ok", **out}, ensure_ascii=False))
            return 0
        # serve
        try:
            import uvicorn
        except ImportError:  # pragma: no cover
            print("hub: uvicorn 이 없다 — `pip install 'workflow_kit[hub]'`", file=sys.stderr)
            return 2
        from workflow_kit.hub.app import build_app

        loopback = _is_loopback(args.bind)
        public_url = args.public_url or f"http://{args.bind}:{args.port}"
        if not loopback:
            print(
                f"hub: 경고 — loopback 이 아닌 {args.bind} 에 bind 한다. 이 허브에 닿는 누구나 프로젝트를 등록할 수 있다 "
                "(요구 R3.4 · R13.3). 바깥 노출은 프록시 뒤에서 한다.",
                file=sys.stderr,
            )
        for c in copies:
            print(f"hub: 이관 전 사본 {c}", file=sys.stderr)
        app = build_app(store, public_url=public_url, exposure="loopback" if loopback else "non-loopback")
        print(json.dumps({"status": "serving", "url": f"http://{args.bind}:{args.port}", "public_url": public_url,
                          "db_version": store.db_version()}, ensure_ascii=False), flush=True)
        uvicorn.run(app, host=args.bind, port=args.port, log_level="warning")
        return 0
    except HubError as e:
        print(json.dumps({"status": "error", **e.payload()}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    sys.exit(main())
