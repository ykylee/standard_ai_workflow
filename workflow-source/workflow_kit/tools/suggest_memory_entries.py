#!/usr/bin/env python3
"""memory_index entry 승격 후보 제안 (ADR-006 W-1, advisory only).

세션이 남긴 완료 작업 (handoff §4 *최근 완료 작업*) 의 제목을 기존 entry
corpus 와 대조해 **index 가 모르는 작업** 을 entry 후보로 제안한다.

**아무것도 쓰지 않는다.** entry 의 primary_abstraction / value_digest 는
"무엇이 기억할 가치가 있는가" 라는 판단이고, 도구가 대신 쓰면 거짓이 된다
(release note 누적 수치 검증과 같은 원칙). 후보에는 스키마 모양 skeleton 이
붙는다 — 채워서 `memory_index/entries/MEM-*.json` 으로 저장하는 건 사람/
에이전트다.

사용 시점: 세션 종료 순서의 memory 갱신 단계에서 advisory 로 한 번 돌린다.

```bash
# 현재 handoff (main 브랜치 기준)
wk suggest-memory-entries

# 특정 handoff + JSON
wk suggest-memory-entries \
    --handoff-path /path/to/session_handoff.md --json
```
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from workflow_kit import __version__ as TOOL_VERSION  # noqa: E402
from workflow_kit.common.paths import memory_active_dir  # noqa: E402
from workflow_kit.common.state.memory_index import (  # noqa: E402
    SUGGESTION_COVERAGE_THRESHOLD,
    load_memory_index,
    suggest_memory_entry_candidates,
)

DEFAULT_HANDOFF = memory_active_dir(REPO_ROOT) / "main" / "session_handoff.md"


def build_payload(
    *,
    workspace_root: Path,
    handoff_path: Path,
    date_str: str,
    threshold: float,
    max_candidates: int,
) -> dict[str, Any]:
    if not handoff_path.is_file():
        return {
            "status": "error",
            "tool_version": TOOL_VERSION,
            "error": f"handoff 부재: {handoff_path}",
            "written_paths": [],
        }
    entries = load_memory_index(workspace_root)
    result = suggest_memory_entry_candidates(
        entries,
        handoff_path.read_text(encoding="utf-8"),
        date_str=date_str,
        threshold=threshold,
        max_candidates=max_candidates,
    )
    return {
        "status": "ok",
        "tool_version": TOOL_VERSION,
        "advisory": (
            "후보 제안일 뿐 자동 적재하지 않는다. skeleton 을 채워 "
            "memory_index/entries/ 에 저장할지는 사람/에이전트가 결정한다."
        ),
        "handoff_path": str(handoff_path),
        "written_paths": [],
        **result,
    }


def _print_human(payload: dict[str, Any]) -> None:
    if payload.get("status") != "ok":
        print(f"  ✗ {payload.get('error', 'unknown error')}", file=sys.stderr)
        return
    print(
        f"  §4 작업 {payload['compared']}건 중 기존 entry 로 덮인 것 "
        f"{payload['covered']}건, 후보 {payload['candidates_total']}건 "
        f"(threshold {payload['threshold']})"
    )
    for c in payload["candidates"]:
        print(f"  ▸ {c['task_id']} (coverage {c['best_coverage']})")
        print(f"    {c['title']}")
        print(f"    cue 제안: {', '.join(c['suggested_cue_anchors'])}")
    if payload["candidates"]:
        print(f"\n  skeleton 은 --json 출력의 candidates[].skeleton 에 있다 (advisory).")


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="suggest_memory_entries",
        description="memory_index entry 승격 후보 제안 (advisory, 무-write)",
    )
    parser.add_argument("--handoff-path", default=str(DEFAULT_HANDOFF),
                        help=f"session_handoff.md 경로 (default: {DEFAULT_HANDOFF})")
    parser.add_argument("--workspace-root", default=str(REPO_ROOT),
                        help="memory_index 를 읽을 workspace root (default: repo root)")
    parser.add_argument("--date", default=None,
                        help="skeleton id 의 날짜 YYYY-MM-DD (default: 오늘 UTC)")
    parser.add_argument("--threshold", type=float, default=SUGGESTION_COVERAGE_THRESHOLD,
                        help="coverage 임계 (default: %(default)s)")
    parser.add_argument("--max-candidates", type=int, default=5,
                        help="제안 상한 (default: %(default)s)")
    parser.add_argument("--json", action="store_true", help="JSON 출력")
    args = parser.parse_args()

    date_str = args.date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    payload = build_payload(
        workspace_root=Path(args.workspace_root),
        handoff_path=Path(args.handoff_path),
        date_str=date_str,
        threshold=args.threshold,
        max_candidates=args.max_candidates,
    )
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        _print_human(payload)
    return 0 if payload.get("status") == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
