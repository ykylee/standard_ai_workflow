#!/usr/bin/env python3
"""rotate_workflow_logs CLI — dual mode wrapper for MCP `rotate_workflow_logs` tool.

`session_handoff.md` 의 §4 *최근 완료 작업* 항목이 `max_done_items` 초과 시 *오래된*
항목들을 *baseline* 섹션으로 rotate. underlying 함수는 `rotate_handoff_tasks()` 로
`workflow_kit.common.rotation` 에 있고, MCP server `standardAiWorkflowReadOnly` 의
`rotate_workflow_logs` tool 이 같은 함수를 부른다 — 본 CLI 는 그 함수에 *직접* 연결
(LLM inline 호출 우회). cron hook / 운영자 수동 실행용.

**idempotent** — `max_done_items` 이하이면 *변경 없음* (`rotated=False`). 두 번
연속 호출해도 *추가* rotate 없음. → --apply 불필요, dry-run default 의미 없음.
함수 자체가 self-decide.

## 사용법

```bash
# 현재 handoff
wk rotate-workflow-logs

# max_done_items 변경 (default 10)
wk rotate-workflow-logs --max-done-items 5

# 특정 handoff 파일 + JSON
wk rotate-workflow-logs --handoff-path /path/to/handoff.md --json
```

Cross-ref: `core/multi_workspace_orchestration.md` §0.7 dual mode (TASK-017).
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

from workflow_kit import __version__ as TOOL_VERSION  # noqa: E402
from workflow_kit.common.paths import (  # noqa: E402
    discover_project_profile_path,
    workflow_branch_dir,
)
from workflow_kit.common.read_only_bundle import (  # noqa: E402
    rotate_workflow_logs_payload,
)


def _default_handoff() -> Path | None:
    """cwd 의 workspace 에서 branch-scoped handoff 를 찾는다. 못 찾으면 None.

    2026-08-18 실측: 원래 기본값은 ``memory_active_dir(REPO_ROOT)/"main"/…`` 였다.
    ``REPO_ROOT`` 는 **이 모듈 파일 위치에서 역산**한 것이라, 소비자가 wheel 로
    설치하면 ``<venv>/lib/python3.x/ai-workflow/…`` 를 열려다 ``FileNotFoundError``
    가 났다 (editable 설치인 개발 호스트에서는 우연히 맞아 안 드러났다). 브랜치도
    ``"main"`` 하드코딩이라 branch-scoped 규약과 어긋났다. 이제 다른 도구와 같은
    규약을 쓴다 — cwd 상위에서 ``PROJECT_PROFILE.md`` 를 찾고, branch 는 그
    workspace 의 git 에서 얻는다.
    """
    profile = discover_project_profile_path()
    if profile is None:
        return None
    return workflow_branch_dir(profile) / "session_handoff.md"


def _print_human(payload: dict) -> None:
    status = payload.get("status", "?")
    if status != "ok":
        print(f"  ✗ status={status}", file=sys.stderr)
        return
    if payload.get("rotated"):
        print(f"  ✓ rotated_count={payload.get('rotated_count')} "
              f"→ remaining_count={payload.get('remaining_count')}")
        for p in payload.get("written_paths", []):
            print(f"    written: {p}")
    else:
        print(f"  = no rotation needed (items <= {payload.get('remaining_count')})")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="rotate workflow logs (dual mode CLI)")
    p.add_argument(
        "--handoff-path",
        type=Path,
        default=None,
        help="session_handoff.md 경로 (기본: cwd 의 workspace 에서 branch-scoped 자동 탐색)",
    )
    p.add_argument("--max-done-items", type=int, default=10, help="max done items (default 10)")
    p.add_argument("--json", action="store_true", help="JSON 출력")
    args = p.parse_args(argv)

    handoff_path = args.handoff_path or _default_handoff()
    if handoff_path is None:
        err = {
            "status": "error",
            "tool_version": TOOL_VERSION,
            "error": "PROJECT_PROFILE.md 를 cwd 상위에서 찾지 못했다. --handoff-path 로 명시하라.",
            "error_code": "missing_required_document",
        }
        print(json.dumps(err, ensure_ascii=False, indent=2) if args.json
              else f"ERROR: {err['error']}", file=sys.stderr)
        return 2

    payload = rotate_workflow_logs_payload(
        handoff_path=str(handoff_path),
        max_done_items=args.max_done_items,
        tool_version=TOOL_VERSION,
    )
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        _print_human(payload)
    return 0 if payload.get("status") == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())
