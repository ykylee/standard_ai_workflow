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
from workflow_kit.common.paths import (  # noqa: E402
    discover_project_profile_path,
    memory_active_dir,
    project_workspace_root,
    workflow_branch_dir,
)
from workflow_kit.common.state.memory_index import (  # noqa: E402
    SUGGESTION_COVERAGE_THRESHOLD,
    load_memory_index,
    suggest_memory_entry_candidates,
)


def _resolve_defaults() -> tuple[Path, Path, str]:
    """무인자 실행의 기준 경로를 **cwd 의 작업 저장소**에서 해석한다.

    이전 기본값은 모듈 위치 파생(`REPO_ROOT`)뿐이라 uv tool 설치에서는
    `<venv>/lib/python3.13/ai-workflow/...` 을 가리켰다 — '자기 설치 위치를
    대상으로 오인' 결함족 (TASK-2026-08-25-main-023, main-022 의 local_mypy 와
    같은 축). 다른 무인자 명령(session-start / refresh-state)과 같은
    `discover_project_profile_path()` 로 cwd 에서 workspace 를 찾고, handoff 는
    브랜치 인식 경로(`workflow_branch_dir`)로 조립한다 — 이전의 `"main"`
    하드코딩도 브랜치 컨텍스트에서 틀린 값이었다.

    cwd 에서 못 찾으면 모듈 위치로 폴백하되, 무엇을 근거로 골랐는지
    세 번째 값(`path_source`)으로 돌려준다 — 폴백은 조용히 하지 않는다.

    Returns:
        (workspace_root, default_handoff, path_source) —
        path_source ∈ {"cwd_project_profile", "module_location_fallback"}
    """
    profile = discover_project_profile_path()
    if profile is not None:
        workspace = project_workspace_root(profile)
        handoff = workflow_branch_dir(profile) / "session_handoff.md"
        return workspace, handoff, "cwd_project_profile"
    fallback_handoff = memory_active_dir(REPO_ROOT) / "main" / "session_handoff.md"
    return REPO_ROOT, fallback_handoff, "module_location_fallback"


def build_payload(
    *,
    workspace_root: Path,
    handoff_path: Path,
    date_str: str,
    threshold: float,
    max_candidates: int,
    path_source: str = "explicit",
) -> dict[str, Any]:
    if not handoff_path.is_file():
        return {
            "status": "error",
            "tool_version": TOOL_VERSION,
            "error": (
                f"handoff 부재: {handoff_path} (경로 근거: {path_source}) — "
                "작업 저장소 안에서 실행하거나 --handoff-path 로 명시한다."
            ),
            "path_source": path_source,
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
        "path_source": path_source,
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
    default_workspace, default_handoff, default_source = _resolve_defaults()
    parser.add_argument("--handoff-path", default=str(default_handoff),
                        help=f"session_handoff.md 경로 (default: {default_handoff})")
    parser.add_argument("--workspace-root", default=str(default_workspace),
                        help="memory_index 를 읽을 workspace root "
                             f"(default: {default_workspace} — {default_source})")
    parser.add_argument("--date", default=None,
                        help="skeleton id 의 날짜 YYYY-MM-DD (default: 오늘 UTC)")
    parser.add_argument("--threshold", type=float, default=SUGGESTION_COVERAGE_THRESHOLD,
                        help="coverage 임계 (default: %(default)s)")
    parser.add_argument("--max-candidates", type=int, default=5,
                        help="제안 상한 (default: %(default)s)")
    parser.add_argument("--json", action="store_true", help="JSON 출력")
    args = parser.parse_args()

    date_str = args.date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    path_source = default_source if args.handoff_path == str(default_handoff) else "explicit"
    payload = build_payload(
        workspace_root=Path(args.workspace_root),
        handoff_path=Path(args.handoff_path),
        date_str=date_str,
        threshold=args.threshold,
        max_candidates=args.max_candidates,
        path_source=path_source,
    )
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        _print_human(payload)
    return 0 if payload.get("status") == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
