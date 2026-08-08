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

REPO_ROOT = Path(__file__).resolve().parents[2]
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
            print(f"  - {h.host_id} @ {h.endpoint}  (added {h.added_at})")
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
