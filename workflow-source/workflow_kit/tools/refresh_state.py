#!/usr/bin/env python3
"""`wk refresh-state` — state.json 을 정본 생성기로 재생성/검증하는 소비자 창구.

## 왜 필요한가 (TASK-2026-08-11-main-018)

`state.json` 은 **생성물**이다 — SSOT 는 `backlog/tasks/` + `session_handoff.md` 이고,
생성기는 `workflow_kit.common.workflow_state.refresh_workflow_state_cache` 하나다.
그런데 세션 종료 절차에 생성기를 부르는 단계가 없어서 에이전트가 state.json 을 손으로
썼고, 생성기 출력과 계속 갈라졌다 (TASK-017 §2 실측). 이 도구가 그 호출 단계다:

- `wk refresh-state`          — 재생성 (세션 종료 절차, 정본 §11)
- `wk refresh-state --check`  — drift 판정만 (쓰지 않음, 검사·CI 용. drift 시 exit 1)

인자 없이 호출하면 cwd 에서 workspace 를 자동 탐색한다 (`wk session-start` 와 같은
규약). 경로 해석은 전부 `workflow_kit.common.paths` 의 branch-scoped 규약을 따른다.
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from datetime import date
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from workflow_kit import __version__ as TOOL_VERSION
from workflow_kit.common.paths import (
    discover_project_profile_path,
    project_workspace_root,
    workflow_state_path,
)
from workflow_kit.common.state.roadmap import (
    generate_roadmap_state,
    state_matches_regeneration,
    state_path as roadmap_state_path,
)
from workflow_kit.common.workflow_state import refresh_workflow_state_cache


def _drift_keys(current: dict[str, Any], regenerated: dict[str, Any]) -> list[str]:
    """최상위 key 단위로 어긋난 곳을 보고한다 — '다르다' 만으로는 못 고친다."""
    keys = sorted(set(current) | set(regenerated))
    return [k for k in keys if current.get(k) != regenerated.get(k)]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--project-profile-path", default=None,
                        help="미지정 시 cwd 상위에서 자동 탐색")
    parser.add_argument("--check", action="store_true",
                        help="drift 판정만 한다 (state.json 을 쓰지 않음). drift 시 exit 1")
    parser.add_argument("--memory-index-dir", default=None)
    parser.add_argument("--generated-at", default=None,
                        help="기본: 재생성은 오늘, --check 는 현재 파일의 generated_at (날짜 차이를 drift 로 오판하지 않도록)")
    args = parser.parse_args()

    profile_raw = args.project_profile_path
    if not profile_raw:
        discovered = discover_project_profile_path()
        if discovered is None:
            print(json.dumps({
                "status": "error",
                "tool_version": TOOL_VERSION,
                "error": "PROJECT_PROFILE.md 를 cwd 상위에서 찾지 못했다. --project-profile-path 로 명시하라.",
                "error_code": "missing_required_document",
            }, ensure_ascii=False, indent=2))
            return 2
        profile_raw = str(discovered)
    project_profile_path = Path(profile_raw).resolve()
    if not project_profile_path.is_file():
        print(json.dumps({
            "status": "error",
            "tool_version": TOOL_VERSION,
            "error": f"PROJECT_PROFILE.md 가 없다: {project_profile_path}",
            "error_code": "missing_required_document",
        }, ensure_ascii=False, indent=2))
        return 2

    memory_index_dir = Path(args.memory_index_dir).resolve() if args.memory_index_dir else None
    state_path = workflow_state_path(project_profile_path)

    workspace_root = project_workspace_root(project_profile_path)

    if not args.check:
        refresh_result = refresh_workflow_state_cache(
            project_profile_path=project_profile_path,
            generated_at=args.generated_at or date.today().isoformat(),
            memory_index_dir=memory_index_dir,
        )
        # ADR-027 M-003: roadmap 이 있으면 roadmap_state.json 도 같은 호출에서
        # 재생성한다 — 별도 명령을 만들지 않는다 (스펙 §7.1). 부재는 실패가
        # 아니라 해당 없음이다.
        roadmap_state = generate_roadmap_state(workspace_root)
        print(json.dumps({
            "status": "ok" if refresh_result["status"] == "refreshed" else "warning",
            "tool_version": TOOL_VERSION,
            "mode": "refresh",
            "state_cache_status": refresh_result["status"],
            "state_path": refresh_result["state_path"],
            "refresh_command": refresh_result["refresh_command"],
            "missing_paths": refresh_result.get("missing_paths", []),
            "roadmap_state_status": "refreshed" if roadmap_state is not None else "not_applicable",
            "roadmap_state_path": str(roadmap_state_path(workspace_root)) if roadmap_state is not None else "",
            "roadmap_issues": len(roadmap_state.issues) if roadmap_state is not None else 0,
            "warnings": refresh_result.get("deprecation_warnings", []),
        }, ensure_ascii=False, indent=2))
        return 0

    # --check: 현재 파일 vs 같은 입력으로 재생성한 출력.
    if not state_path.is_file():
        print(json.dumps({
            "status": "error",
            "tool_version": TOOL_VERSION,
            "mode": "check",
            "error": f"state.json 이 없다: {state_path}. `wk refresh-state` 로 먼저 생성하라.",
            "error_code": "missing_state_json",
        }, ensure_ascii=False, indent=2))
        return 2
    try:
        current = json.loads(state_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(json.dumps({
            "status": "error",
            "tool_version": TOOL_VERSION,
            "mode": "check",
            "error": f"state.json 이 JSON 이 아니다: {exc}",
            "error_code": "invalid_state_json",
        }, ensure_ascii=False, indent=2))
        return 2

    # 날짜만 다른 것은 내용 drift 가 아니다 — 현재 파일의 generated_at 로 재생성해 비교.
    generated_at = args.generated_at or str(current.get("generated_at", date.today().isoformat()))
    with tempfile.TemporaryDirectory(prefix="wk-refresh-state-check-") as tmp:
        tmp_output = Path(tmp) / "state.json"
        refresh_result = refresh_workflow_state_cache(
            project_profile_path=project_profile_path,
            output_path=tmp_output,
            generated_at=generated_at,
            memory_index_dir=memory_index_dir,
        )
        if refresh_result["status"] != "refreshed":
            print(json.dumps({
                "status": "error",
                "tool_version": TOOL_VERSION,
                "mode": "check",
                "error": "생성기가 재생성에 실패했다 (입력 문서 부재).",
                "error_code": "state_refresh_skipped",
                "missing_paths": refresh_result.get("missing_paths", []),
            }, ensure_ascii=False, indent=2))
            return 2
        regenerated = json.loads(tmp_output.read_text(encoding="utf-8"))

    drifted = _drift_keys(current, regenerated)
    # ADR-027 M-003: roadmap_state.json 도 같은 --check 에서 drift 판정한다.
    # 부재 프로젝트는 (True, "해당 없음") 이라 기존 동작이 변하지 않는다.
    roadmap_ok, roadmap_reason = state_matches_regeneration(workspace_root)
    any_drift = bool(drifted) or not roadmap_ok
    print(json.dumps({
        "status": "ok" if not any_drift else "error",
        "tool_version": TOOL_VERSION,
        "mode": "check",
        "state_path": str(state_path),
        "drift": bool(drifted),
        "drifted_keys": drifted,
        "roadmap_drift": not roadmap_ok,
        "roadmap_drift_reason": "" if roadmap_ok else roadmap_reason,
        "generated_at_used": generated_at,
        "refresh_command": refresh_result["refresh_command"],
        "recovery_hint": "" if not any_drift else "state.json / roadmap_state.json 은 생성물이다 — 손으로 고치지 말고 `wk refresh-state` 로 재생성하라 (정본 §11, ADR-027 §7).",
    }, ensure_ascii=False, indent=2))
    return 0 if not any_drift else 1


if __name__ == "__main__":
    raise SystemExit(main())
