"""``python -m workflow_kit hub`` — 워크플로우 허브 (2.0) 서버 명령 (hub_spec §2.1).

    hub serve  --db PATH [--bind 127.0.0.1] [--port 8770] [--public-url URL] [--web-token-name NAME]
    hub backup --db PATH --out PATH
    hub admin  --db PATH token issue --role {web,admin} --name NAME
    hub admin  --db PATH project export --project ID --out FILE [--seal-to URL] | import --file FILE | seal --project ID --to URL | unseal --project ID
    hub admin  --db PATH token revoke --name NAME
    hub admin  --db PATH callsign {revoke|delete} --project ID --callsign NAME
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
    p = argparse.ArgumentParser(
        prog="python -m workflow_kit hub", description="워크플로우 허브 (2.0) 서버"
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("serve", help="허브를 띄운다 (DB 이관 후)")
    s.add_argument("--db", required=True, help="SQLite DB 경로 또는 PostgreSQL URL")
    s.add_argument("--bind", default="127.0.0.1")
    s.add_argument("--port", type=int, default=8770)
    s.add_argument(
        "--public-url", default=None, help="허브의 공개 주소 — 기본은 http://<bind>:<port>"
    )
    s.add_argument(
        "--web-token-name",
        default=None,
        help="화면 공용 web 토큰 이름 — 주면 토큰 없는 화면 요청이 읽기 · 콜사인 등록 권한으로 돈다 (기본 꺼짐)",
    )

    m = sub.add_parser("migrate", help="기존 SQLite 허브를 빈 PostgreSQL 대상으로 복사한다")
    m.add_argument("--from-sqlite", required=True, type=Path)
    m.add_argument("--to-postgres", required=True, help="postgresql:// 또는 postgres:// URL")

    sub.add_parser(
        "relay",
        help="PC 중계 (2.1) — init · allow · serve · pause · resume · status (`hub relay -h`)",
    )
    b = sub.add_parser("backup", help="돌고 있는 허브의 DB 를 일관되게 복사한다")
    b.add_argument("--db", required=True, help="SQLite DB 경로")
    b.add_argument("--out", required=True, type=Path)

    a = sub.add_parser("admin", help="로컬 관리 (토큰 · 콜사인)")
    a.add_argument("--db", required=True, help="SQLite DB 경로 또는 PostgreSQL URL")
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
    for cs_action in ("revoke", "delete"):  # delete 는 활동이 없는 콜사인만
        cr = csub.add_parser(cs_action)
        cr.add_argument("--project", required=True)
        cr.add_argument("--callsign", required=True)
    # 허브 서버 간 프로젝트 이전 (M-039 WBS-39.4) — 묶음 파일 · 원본 봉인
    pj = asub.add_parser("project", help="허브 간 프로젝트 이전 — export · import · seal · unseal")
    psub = pj.add_subparsers(dest="action", required=True)
    pe = psub.add_parser(
        "export", help="프로젝트 묶음을 파일로 (권장: --seal-to 로 먼저 봉인해 그 뒤 쓰기를 막는다)"
    )
    pe.add_argument("--project", required=True)
    pe.add_argument("--out", required=True, type=Path)
    pe.add_argument("--seal-to", default=None, help="새 허브 주소 — 주면 봉인한 뒤 묶음을 뜬다")
    pe.add_argument("--public-url", default="", help="이 허브의 공개 주소 (묶음의 출처 기록)")
    pi = psub.add_parser(
        "import", help="묶음을 이 허브에 들인다 (봉인된 같은 프로젝트가 있으면 되옮기기로 교체)"
    )
    pi.add_argument("--file", required=True, type=Path)
    ps = psub.add_parser("seal", help="봉인 — 그 프로젝트의 호출에 410 project_moved + 새 주소")
    ps.add_argument("--project", required=True)
    ps.add_argument("--to", required=True)
    pu = psub.add_parser("unseal", help="봉인을 푼다 (이전을 되돌릴 때)")
    pu.add_argument("--project", required=True)
    pv = psub.add_parser(
        "invite", help="이 허브로 들일 프로젝트의 일회용 초대 코드 (HTTP 이전 — hub_client.py move)"
    )
    pv.add_argument("--project", required=True, help="들일 프로젝트 ID (원본 허브의 ID 그대로)")
    pv.add_argument("--hours", type=int, default=24)
    pv.add_argument("--note", default="")
    return p


def main(argv: list[str] | None = None) -> int:
    force_utf8_stdio()
    raw = list(sys.argv[1:] if argv is None else argv)
    if raw and raw[0] == "relay":
        # PC 중계 (2.1, hub_orchestration_spec §9.1) — 허브 서버 의존(mcp 등) 없이 표준 라이브러리만으로 돈다.
        from workflow_kit.relay.cli import main as relay_main

        return relay_main(raw[1:])
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
        if args.cmd == "migrate":
            hubdb.open_db(args.to_postgres, now=now)
            result = hubdb.copy_sqlite_to_postgres(args.from_sqlite, args.to_postgres, now=now)
            print(json.dumps(result, ensure_ascii=False))
            return 0
        if args.cmd == "backup":
            if hubdb.is_postgres(args.db):
                raise HubError(
                    400,
                    "postgres_backup_external",
                    "PostgreSQL 백업은 서버 운영 도구(pg_dump 또는 managed snapshot)를 사용한다",
                )
            hubdb.backup(Path(args.db), args.out)
            print(json.dumps({"status": "ok", "backup": str(args.out)}, ensure_ascii=False))
            return 0
        copies = hubdb.open_db(args.db, now=now)
        store = Store(args.db)
        if args.cmd == "admin":
            if args.what == "token" and args.action == "issue":
                token = store.issue_hub_token(args.role, args.name, now)
                print(
                    json.dumps(
                        {"status": "ok", "name": args.name, "role": args.role, "token": token},
                        ensure_ascii=False,
                    )
                )
            elif args.what == "token":
                store.revoke_hub_token(args.name, now)
                print(json.dumps({"status": "ok", "revoked": args.name}, ensure_ascii=False))
            elif args.what == "project":
                from workflow_kit.hub.transfer import Transfer, write_bundle

                t = Transfer(store)
                if args.action == "export":
                    sealed = t.seal(args.project, args.seal_to, now) if args.seal_to else None
                    bundle = t.export(args.project, now, args.public_url)
                    write_bundle(bundle, args.out)
                    print(
                        json.dumps(
                            {
                                "status": "ok",
                                "out": str(args.out),
                                "digest": bundle["digest"],
                                "counts": bundle["counts"],
                                "sealed": sealed,
                            },
                            ensure_ascii=False,
                        )
                    )
                elif args.action == "import":
                    if copies:
                        print(
                            json.dumps(
                                {"status": "info", "pre_migration_copies": [str(c) for c in copies]}
                            ),
                            file=sys.stderr,
                        )
                    import secrets  # noqa: PLC0415

                    if hubdb.is_postgres(args.db):
                        print(
                            "hub: PostgreSQL 묶음 import는 원자 transaction으로 처리한다 — 운영 백업은 서버 도구로 먼저 남긴다",
                            file=sys.stderr,
                        )
                    else:
                        db_file = Path(args.db)
                        hubdb.backup(
                            db_file,
                            db_file.with_name(
                                f"{db_file.name}.pre-import-{now.strftime('%Y%m%dT%H%M%SZ')}-{secrets.token_hex(3)}"
                            ),
                        )
                    out = t.import_bundle(json.loads(args.file.read_text(encoding="utf-8")), now)
                    print(json.dumps({"status": "ok", **out}, ensure_ascii=False))
                elif args.action == "invite":
                    from workflow_kit.hub.transfer import issue_invite

                    out = issue_invite(store, args.project, now, args.hours, args.note)
                    print(
                        json.dumps(
                            {
                                "status": "ok",
                                **out,
                                "note": "코드는 지금 한 번만 보인다 — 소유자에게 전한다",
                            },
                            ensure_ascii=False,
                        )
                    )
                elif args.action == "seal":
                    print(
                        json.dumps(
                            {"status": "ok", **t.seal(args.project, args.to, now)},
                            ensure_ascii=False,
                        )
                    )
                else:
                    print(
                        json.dumps(
                            {"status": "ok", **t.unseal(args.project, now)}, ensure_ascii=False
                        )
                    )
            elif args.what == "guide":
                from workflow_kit.hub.setup import Setup

                out = Setup(store, "").set_guide(
                    Ctx(now=now, via="admin"),
                    args.project,
                    args.file.read_text(encoding="utf-8"),
                    args.actor,
                )
                print(json.dumps({"status": "ok", **out}, ensure_ascii=False))
            else:
                admin_ctx = Ctx(now=now, via="admin")
                if args.action == "delete":
                    out = store.delete_callsign(admin_ctx, args.project, args.callsign, args.callsign)
                else:
                    out = store.revoke_callsign(admin_ctx, args.project, args.callsign)
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
        if args.web_token_name and store.web_principal(args.web_token_name) is None:
            print(
                f"hub: 화면 공용 토큰이 없다: {args.web_token_name} — `hub admin token issue --role web --name …` 로 먼저 발급한다",
                file=sys.stderr,
            )
            return 2
        app = build_app(
            store,
            public_url=public_url,
            exposure="loopback" if loopback else "non-loopback",
            web_token_name=args.web_token_name,
        )
        print(
            json.dumps(
                {
                    "status": "serving",
                    "url": f"http://{args.bind}:{args.port}",
                    "public_url": public_url,
                    "db_version": store.db_version(),
                },
                ensure_ascii=False,
            ),
            flush=True,
        )
        uvicorn.run(app, host=args.bind, port=args.port, log_level="warning")
        return 0
    except HubError as e:
        print(json.dumps({"status": "error", **e.payload()}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    sys.exit(main())
