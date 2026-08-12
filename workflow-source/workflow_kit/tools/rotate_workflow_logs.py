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
python3 workflow-source/tools/rotate_workflow_logs.py

# max_done_items 변경 (default 10)
python3 workflow-source/tools/rotate_workflow_logs.py --max-done-items 5

# 특정 handoff 파일 + JSON
python3 workflow-source/tools/rotate_workflow_logs.py --handoff-path /path/to/handoff.md --json
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
from workflow_kit.common.paths import memory_active_dir  # noqa: E402
from workflow_kit.common.read_only_bundle import (  # noqa: E402
    rotate_workflow_logs_payload,
)


DEFAULT_HANDOFF = (
    memory_active_dir(REPO_ROOT) / "main" / "session_handoff.md"
)


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
        default=DEFAULT_HANDOFF,
        help=f"session_handoff.md 경로 (default: {DEFAULT_HANDOFF})",
    )
    p.add_argument("--max-done-items", type=int, default=10, help="max done items (default 10)")
    p.add_argument("--json", action="store_true", help="JSON 출력")
    args = p.parse_args(argv)

    payload = rotate_workflow_logs_payload(
        handoff_path=str(args.handoff_path),
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
