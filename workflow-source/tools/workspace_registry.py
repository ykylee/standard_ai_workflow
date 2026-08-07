#!/usr/bin/env python3
"""workspace registry CLI — 표준 §10.2 §7.1 의 workspace registry 조작.

워크스페이스(브랜치)를 *host-scoped* registry 에 등록/해제해, dashboard Panel 5
등이 in-flight 워크스페이스를 가로질러 볼 수 있게 한다. registry 는 git-tracked
가 아니다 — 호스트 외부 (``~/.cache/workflow_kit/registry.json``) 에 단일 file 로
저장된다. 배타 제어 / lease 같은 동적 상태는 §5D 가 git 으로 대신한다.

## 왜 CLI 가 필요한가

워크플로우 도입자가 (a) 새 worktree 를 만들 때마다 registry 에 등록하고, (b) 종료
시 정리하는 것이 운영 형태다. seed/claim 도구가 자기 자신을 *register* 까지 같이
해주면 좋지만, 그 결합은 별도 task 로 미룬다 (후속). 본 CLI 는 *수동* 등록·조회
수단만 제공한다.

Usage:
    # 등록
    python3 workflow-source/tools/workspace_registry.py register \
        --path /path/to/worktree --branch feat-login --harness codex --apply

    # 조회
    python3 workflow-source/tools/workspace_registry.py list
    python3 workflow-source/tools/workspace_registry.py paths

    # 해제 (path / branch / all)
    python3 workflow-source/tools/workspace_registry.py unregister --path /path/to/wt --apply
    python3 workflow-source/tools/workspace_registry.py unregister --branch feat-login --apply
    python3 workflow-source/tools/workspace_registry.py unregister --all --apply

    # JSON 출력
    python3 workflow-source/tools/workspace_registry.py list --json

    # host_id 확인
    python3 workflow-source/tools/workspace_registry.py host-id

기본은 ``--dry-run``. 실제 변경은 ``--apply``.

Cross-ref: `core/multi_workspace_orchestration.md` §7.1, §5A.3, §0.4.
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


def cmd_register(args: argparse.Namespace) -> int:
    if not args.path:
        print("ERROR: --path is required", file=sys.stderr)
        return 2
    if not args.branch:
        print("ERROR: --branch is required", file=sys.stderr)
        return 2
    summary = {
        "status": "ok" if args.apply else "dry_run",
        "action": "register",
        "path": str(Path(args.path).expanduser()),
        "branch": args.branch,
        "harness": args.harness,
        "endpoint": args.endpoint,
        "registry_path": str(R.registry_path()),
        "host_id": R.host_id(),
    }
    if args.apply:
        reg = R.register(
            args.path,
            branch=args.branch,
            harness=args.harness,
            endpoint=args.endpoint,
        )
        summary["entries_after"] = len(reg.entries)
    if args.json:
        _print_json(summary)
    else:
        print(f"[{summary['status']}] register {summary['path']} ({summary['branch']})")
        print(f"  registry: {summary['registry_path']}")
        print(f"  host_id:  {summary['host_id']}")
    return 0


def cmd_unregister(args: argparse.Namespace) -> int:
    if not (args.path or args.branch or args.all):
        print("ERROR: --path, --branch, or --all is required", file=sys.stderr)
        return 2
    before = len(R.list_entries())
    summary = {
        "status": "ok" if args.apply else "dry_run",
        "action": "unregister",
        "path": args.path,
        "branch": args.branch,
        "all": bool(args.all),
        "registry_path": str(R.registry_path()),
    }
    if args.apply:
        reg = R.unregister(path=args.path, branch=args.branch, all=args.all)
        summary["entries_after"] = len(reg.entries)
        summary["entries_removed"] = before - len(reg.entries)
    else:
        summary["entries_after"] = before  # 변경 없음이라 가정
    if args.json:
        _print_json(summary)
    else:
        print(f"[{summary['status']}] unregister path={args.path} branch={args.branch} all={args.all}")
        print(f"  registry: {summary['registry_path']}")
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    entries = R.list_entries()
    if args.json:
        _print_json({
            "host_id": R.host_id(),
            "registry_path": str(R.registry_path()),
            "update_stale": R.is_stale,
            "entries": [e.to_dict() for e in entries],
        })
        return 0
    print(f"host_id: {R.host_id()}")
    print(f"registry: {R.registry_path()}")
    print(f"entries: {len(entries)}")
    for e in entries:
        stale = " (stale)" if R.is_stale(e) else ""
        print(f"  - {e.branch} @ {e.path}{stale}")
    return 0


def cmd_paths(args: argparse.Namespace) -> int:
    paths = R.registry_paths()
    if args.json:
        _print_json({"paths": [str(p) for p in paths]})
        return 0
    for p in paths:
        print(p)
    return 0


def cmd_host_id(args: argparse.Namespace) -> int:
    print(R.host_id())
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="workspace registry CLI (표준 §10.2 §7.1)")
    sub = p.add_subparsers(dest="command", required=True)

    sp = sub.add_parser("register", help="workspace 등록")
    sp.add_argument("--path", required=True)
    sp.add_argument("--branch", required=True)
    sp.add_argument("--harness", default=None)
    sp.add_argument("--endpoint", default=None)
    sp.add_argument("--apply", action="store_true")
    sp.add_argument("--dry-run", action="store_true", help="기본 (물리적 default)")
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(func=cmd_register)

    sp = sub.add_parser("unregister", help="workspace 해제")
    sp.add_argument("--path", default=None)
    sp.add_argument("--branch", default=None)
    sp.add_argument("--all", action="store_true")
    sp.add_argument("--apply", action="store_true")
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(func=cmd_unregister)

    sp = sub.add_parser("list", help="전체 entry 출력")
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(func=cmd_list)

    sp = sub.add_parser("paths", help="registry 의 모든 path 만")
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(func=cmd_paths)

    sp = sub.add_parser("host-id", help="이 호스트의 host_id 출력")
    sp.set_defaults(func=cmd_host_id)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
