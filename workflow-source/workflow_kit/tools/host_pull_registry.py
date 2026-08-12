#!/usr/bin/env python3
"""host pull registry CLI — federation §7.4 의 *읽기* 마무리.

known_hosts 의 endpoint 를 따라가서 원격 호스트의 registry 를 fetch + cache + 
merge_entries. ``--apply`` 시 cache 를 갱신하고 merge 결과를 emit. 기본은
``--dry-run`` (cache 미갱신, fetch + cache read 만).

## 왜 CLI 가 필요한가

- 운영자가 multi-host federation 을 운영할 때, dashboard 가 *자동* 으로 pull 하지
  못하는 상황 (예: 회사 방화벽 너머, 알려지지 않은 endpoint 변경) 에서 *수동* 으로
  fetch + cache 갱신 가능.
- HTTP server 가 어떤 호스트에서 떠있는지 *재확인* — fetch error 가 났을 때
  ``--host <id>`` 로 단일 host 만 시도.

## 사용법

```bash
# 한 host (default: dry-run)
python3 workflow-source/tools/host_pull_registry.py pull --host hostA

# cache 갱신 + JSON 결과
python3 workflow-source/tools/host_pull_registry.py pull --host hostA --apply --json

# 모든 known hosts
python3 workflow-source/tools/host_pull_registry.py pull --all --apply

# known hosts 목록
python3 workflow-source/tools/host_pull_registry.py list
```

Cross-ref: `core/multi_workspace_orchestration.md` §7.4 (TASK-016).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from workflow_kit.common import workspace_registry as R  # noqa: E402


def _print_json(payload: dict) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))


def cmd_pull(args: argparse.Namespace) -> int:
    timeout = args.timeout if args.timeout is not None else R.DEFAULT_PULL_TIMEOUT_SECONDS
    use_cache = not args.no_cache

    if args.all:
        results = R.pull_all_remote_registries(timeout=timeout, use_cache=use_cache)
    elif args.host:
        if not R.host_id() or args.host == R.host_id():
            print(
                f"ERROR: --host {args.host!r} 가 자기 자신 (cycle 회피)",
                file=sys.stderr,
            )
            return 2
        results = [(args.host, R.pull_remote_registry(args.host, timeout=timeout, use_cache=use_cache))]
    else:
        print("ERROR: --host <id> 또는 --all 필요", file=sys.stderr)
        return 2

    summary = {
        "timeout": timeout,
        "use_cache": use_cache,
        "results": [
            {
                "host_id": h,
                "ok": r.get("ok"),
                "from_cache": r.get("from_cache", False),
                "error": r.get("error"),
                "fetch_error": r.get("fetch_error"),
                "entries_count": (
                    len(r.get("registry", {}).get("entries", []))
                    if r.get("ok") else None
                ),
            }
            for h, r in results
        ],
    }
    if args.json:
        _print_json(summary)
    else:
        for item in summary["results"]:
            mark = "✓" if item["ok"] else "✗"
            extra = f" (cache, {item['entries_count']} entries)" if item.get("from_cache") else (
                f" ({item['entries_count']} entries)" if item["ok"] else f" — {item['error']}"
            )
            print(f"  {mark} {item['host_id']}{extra}")
    return 0 if all(r.get("ok") for _, r in results) else 1


def cmd_list(args: argparse.Namespace) -> int:
    hosts = R.load_known_hosts()
    summary = {
        "count": len(hosts),
        "self_host_id": R.host_id(),
        "hosts": [h.to_dict() for h in hosts],
    }
    if args.json:
        _print_json(summary)
    else:
        print(f"self_host_id: {R.host_id()}")
        print(f"known hosts: {len(hosts)}")
        for h in hosts:
            auth = f"  [token_env={h.token_env}]" if h.token_env else ""
            print(f"  - {h.host_id} @ {h.endpoint}  (added {h.added_at}){auth}")
    return 0


def cmd_add_known_host(args: argparse.Namespace) -> int:
    """known host 1건 등록 / 갱신 (v1.1.2+, TASK-022).

    `add_known_host()` API 는 TASK-015 부터 있었지만 **부르는 CLI 가 없었다** —
    운영자가 등록할 방법이 없으니 federation 이 실제로는 돌 수 없었다. HTTP
    서버(TASK-022)를 띄워도 상대가 등록을 못 하면 그대로 반쪽이다.
    """
    if not args.apply:
        _print_json({
            "ok": True,
            "dry_run": True,
            "would_add": {
                "host_id": args.host_id,
                "endpoint": args.endpoint,
                "note": args.note,
                "token_env": args.token_env,
            },
            "hint": "--apply 를 붙이면 실제로 기록합니다.",
        }) if args.json else print(
            f"[dry-run] {args.host_id} @ {args.endpoint}"
            + (f" (token_env={args.token_env})" if args.token_env else "")
            + "\n--apply 를 붙이면 실제로 기록합니다."
        )
        return 0

    hosts = R.add_known_host(
        args.host_id, args.endpoint, note=args.note, token_env=args.token_env
    )
    # self-host 는 add_known_host 가 no-op 으로 흘린다 — 조용히 성공한 척하지 않는다.
    registered = any(h.host_id == args.host_id for h in hosts)
    payload = {
        "ok": registered,
        "host_id": args.host_id,
        "count": len(hosts),
        "hosts": [h.to_dict() for h in hosts],
    }
    if not registered:
        payload["note"] = (
            f"{args.host_id} 는 이 호스트 자신(self host_id)이라 등록하지 않았습니다."
        )
    if args.json:
        _print_json(payload)
    else:
        if registered:
            print(f"registered: {args.host_id} @ {args.endpoint}")
        else:
            print(f"skipped: {payload['note']}")
        print(f"known hosts: {len(hosts)}")
    return 0 if registered else 1


def cmd_remove_known_host(args: argparse.Namespace) -> int:
    """known host 1건 해제 (v1.1.2+, TASK-022)."""
    before = {h.host_id for h in R.load_known_hosts()}
    if args.host_id not in before:
        print(f"ERROR: unknown host_id: {args.host_id}", file=sys.stderr)
        return 1
    if not args.apply:
        print(f"[dry-run] would remove {args.host_id}\n--apply 를 붙이면 실제로 지웁니다.")
        return 0
    hosts = R.remove_known_host(args.host_id)
    if args.json:
        _print_json({"ok": True, "removed": args.host_id, "count": len(hosts)})
    else:
        print(f"removed: {args.host_id}")
        print(f"known hosts: {len(hosts)}")
    return 0


def cmd_merge(args: argparse.Namespace) -> int:
    """local + remote registries 를 merge_entries 로 합친다. *read-only*."""
    local = R.list_entries()
    merged, errors = R.merge_with_remotes(local, timeout=args.timeout, use_cache=not args.no_cache)
    summary = {
        "local_count": len(local),
        "merged_count": len(merged),
        "errors": errors,
        "merged": [
            {
                "source_host_id": e.source_host_id,
                "path": e.path,
                "branch": e.branch,
                "last_seen_at": e.last_seen_at,
            }
            for e in merged
        ],
    }
    if args.json:
        _print_json(summary)
    else:
        print(f"local: {len(local)}, merged: {len(merged)}, errors: {len(errors)}")
        for e in errors:
            print(f"  ERROR {e['host_id']}: {e['error']}")
        for e in merged:
            print(f"  [{e['source_host_id'] or '(local)'}] {e['branch']} @ {e['path']}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="host pull registry CLI (federation §7.4)")
    sub = p.add_subparsers(dest="command", required=True)

    # pull
    sp = sub.add_parser("pull", help="known host 의 registry 를 fetch")
    g = sp.add_mutually_exclusive_group(required=True)
    g.add_argument("--host", help="단일 host_id")
    g.add_argument("--all", action="store_true", help="모든 known hosts")
    sp.add_argument("--timeout", type=float, default=None, help="HTTP timeout (sec)")
    sp.add_argument("--no-cache", action="store_true", help="cache 미사용 (fallback off)")
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(func=cmd_pull)

    # list
    sp = sub.add_parser("list", help="known hosts 목록")
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(func=cmd_list)

    # add-known-host (v1.1.2+, TASK-022)
    sp = sub.add_parser("add-known-host", help="known host 등록 / 갱신")
    sp.add_argument("--host-id", required=True, help="상대 호스트의 host_id")
    sp.add_argument(
        "--endpoint",
        required=True,
        help="registry 위치 (http://host:8765/registry.json 또는 file:///abs/path)",
    )
    sp.add_argument("--note", default="", help="메모")
    sp.add_argument(
        "--token-env",
        default="",
        metavar="NAME",
        help="상대가 --token-env 로 떠 있을 때 쓸 ENV VAR 이름 (토큰 값이 아니라 이름)",
    )
    sp.add_argument("--apply", action="store_true", help="실제로 기록 (기본: dry-run)")
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(func=cmd_add_known_host)

    # remove-known-host (v1.1.2+, TASK-022)
    sp = sub.add_parser("remove-known-host", help="known host 해제")
    sp.add_argument("--host-id", required=True)
    sp.add_argument("--apply", action="store_true", help="실제로 삭제 (기본: dry-run)")
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(func=cmd_remove_known_host)

    # merge
    sp = sub.add_parser("merge", help="local + remote registry merge (read-only)")
    sp.add_argument("--timeout", type=float, default=None)
    sp.add_argument("--no-cache", action="store_true")
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(func=cmd_merge)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
