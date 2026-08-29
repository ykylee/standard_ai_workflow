#!/usr/bin/env python3
"""ADR-027 M-003 배선 검사 — refresh-state 통합 · session-start 보고 · MCP 교체.

주장:
1. `wk refresh-state` 는 roadmap 이 있으면 `roadmap_state.json` 을 **같은 호출**에서
   재생성하고, `--check` 는 roadmap 손편집을 drift 로 판정한다. roadmap 부재
   프로젝트는 기존 동작 그대로다 (additive).
2. session-start 는 현재 마일스톤·SDLC 단계·다음 WBS 후보를 보고하고, 문서
   단계(concept/requirements/design)의 산출물 부재를 권고로 만든다.
3. 데모 휴리스틱 `common/milestones.py` 는 **정적으로 부재**하고 (49차 규칙 —
   은퇴는 함수까지 지운다), MCP `assess_milestone_progress` 는 roadmap 층을 읽는다.
"""
from __future__ import annotations

#: 이 검사의 입력 표면 (spec `core/test_impact_tiering_spec.md` §2).
#: 게이트 채취 실측에서 뽑아 넓은 쪽으로 올렸다 — 좁으면 meta-watch 가 red 로 잡는다.
WATCHES = (
    "ai-workflow/memory/active/*",
    "workflow-source/pyproject.toml",
    "workflow-source/workflow_kit/*",
)

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from workflow_kit.common.read_only_bundle import assess_milestone_progress_payload  # noqa: E402
from workflow_kit.common.state.roadmap import build_session_roadmap_context  # noqa: E402

REFRESH_TOOL = SOURCE_ROOT / "workflow_kit" / "tools" / "refresh_state.py"
SESSION_TOOL = SOURCE_ROOT / "workflow_kit" / "tools" / "session_start.py"
BRANCH = "main"

FAILURES: list[str] = []


def _record(case: str, ok: bool, detail: str = "") -> None:
    if ok:
        print(f"PASS: {case}")
    else:
        print(f"FAIL: {case}{(' — ' + detail) if detail else ''}")
        FAILURES.append(case)


def _run_tool(tool: Path, args: list[str], cwd: Path | None = None) -> tuple[int, dict]:
    env = dict(os.environ)
    env["CODEX_WORKFLOW_BRANCH"] = BRANCH
    env["PYTHONPATH"] = str(SOURCE_ROOT)
    proc = subprocess.run(
        [sys.executable, str(tool), *args],
        capture_output=True, text=True, timeout=120,
        cwd=str(cwd) if cwd else None, env=env,
    )
    try:
        payload = json.loads(proc.stdout) if proc.stdout.strip() else {}
    except json.JSONDecodeError:
        raise AssertionError(f"tool 출력이 JSON 이 아니다:\n{proc.stdout[:500]}\n{proc.stderr[:500]}")
    return proc.returncode, payload


def _build_fixture(root: Path, *, with_roadmap: bool) -> Path:
    """state fixture (check_state_json_generated 와 동일 최소 세트) + 선택적 roadmap."""
    (root / "docs").mkdir(parents=True)
    profile = root / "docs" / "PROJECT_PROFILE.md"
    profile.write_text("# profile\n", encoding="utf-8")
    branch_dir = root / "ai-workflow" / "memory" / "active" / BRANCH
    (branch_dir / "backlog" / "tasks").mkdir(parents=True)
    (branch_dir / "sessions").mkdir(parents=True)
    (branch_dir / "session_handoff.md").write_text(
        "# Session Handoff\n\n"
        "## 1. 현재 작업 요약\n\n- 현재 기준선: fixture baseline\n\n"
        "## 2. 진행 중 작업\n\n- 현재 `in_progress` 작업:\n- TASK-2026-01-01-main-001 — fixture task\n\n"
        "## 3. 차단 작업\n\n- 현재 `blocked` 작업:\n-\n\n"
        "## 4. 최근 완료 작업\n\n- 최근 완료 작업 목록:\n-\n",
        encoding="utf-8",
    )
    (branch_dir / "backlog" / "2026-01-01.md").write_text(
        "# Daily Backlog — 2026-01-01\n\n"
        "- **TASK-2026-01-01-main-001** [generic] fixture task\n"
        "  - path: [`./tasks/TASK-2026-01-01-main-001.md`](./tasks/TASK-2026-01-01-main-001.md)\n"
        "  - status: in_progress\n",
        encoding="utf-8",
    )
    (branch_dir / "backlog" / "tasks" / "TASK-2026-01-01-main-001.md").write_text(
        "---\nid: TASK-2026-01-01-main-001\nstatus: in_progress\ncreated_at: 2026-01-01\n"
        "source_anchor: generic-task-2026-01-01-main-001\nsource_path: backlog/2026-01-01.md\n"
        "kind: generic\nwbs: M-001/WBS-1.1\n---\n\n# TASK-2026-01-01-main-001 — fixture task\n",
        encoding="utf-8",
    )
    if with_roadmap:
        roadmap = root / "ai-workflow" / "memory" / "active" / "roadmap"
        roadmap.mkdir(parents=True)
        (roadmap / "index.md").write_text(
            "# Roadmap — fixture\n\n## Milestones\n\n"
            "- **M-001** [concept] 컨셉 — status: in_progress\n"
            "  - path: [`./M-001-concept.md`](./M-001-concept.md)\n",
            encoding="utf-8",
        )
        (roadmap / "M-001-concept.md").write_text(
            "---\nid: M-001\ntitle: 컨셉\nsdlc_phase: concept\nstatus: in_progress\norder: 1\n"
            "parallel_allowed: []\ndeliverables:\n  - docs/CONCEPT.md\n---\n\n# M-001\n\n"
            "## WBS\n\n- **WBS-1.1** 컨셉 노트\n- **WBS-1.2** 리뷰\n",
            encoding="utf-8",
        )
    return profile


def test_refresh_regenerates_and_checks_roadmap_state() -> None:
    """refresh 가 roadmap_state 를 함께 재생성하고, --check 가 손편집을 drift 로 잡는다."""
    problems: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp).resolve()
        profile = _build_fixture(root, with_roadmap=True)
        rc, payload = _run_tool(REFRESH_TOOL, ["--project-profile-path", str(profile)])
        if rc != 0 or payload.get("roadmap_state_status") != "refreshed":
            problems.append(f"refresh 미동작: rc={rc} {payload.get('roadmap_state_status')}")
        state_file = root / "ai-workflow" / "memory" / "active" / "roadmap" / "roadmap_state.json"
        if not state_file.is_file():
            problems.append("roadmap_state.json 미생성")
        else:
            rc, payload = _run_tool(REFRESH_TOOL, ["--project-profile-path", str(profile), "--check"])
            if rc != 0 or payload.get("roadmap_drift") is not False:
                problems.append(f"무drift 여야 한다: rc={rc} {payload.get('roadmap_drift_reason')}")
            raw = json.loads(state_file.read_text(encoding="utf-8"))
            raw["milestones"][0]["progress"] = 1.0
            state_file.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
            rc, payload = _run_tool(REFRESH_TOOL, ["--project-profile-path", str(profile), "--check"])
            if rc != 1 or payload.get("roadmap_drift") is not True:
                problems.append(f"되주입 drift 미검출: rc={rc} {payload}")
    _record("test_refresh_regenerates_and_checks_roadmap_state", not problems, "; ".join(problems))


def test_refresh_without_roadmap_is_additive() -> None:
    """roadmap 부재 프로젝트: not_applicable 이고 파일을 만들지 않으며 --check 는 기존 그대로."""
    problems: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp).resolve()
        profile = _build_fixture(root, with_roadmap=False)
        rc, payload = _run_tool(REFRESH_TOOL, ["--project-profile-path", str(profile)])
        if rc != 0 or payload.get("roadmap_state_status") != "not_applicable":
            problems.append(f"not_applicable 이어야 한다: rc={rc} {payload.get('roadmap_state_status')}")
        state_file = root / "ai-workflow" / "memory" / "active" / "roadmap" / "roadmap_state.json"
        if state_file.exists():
            problems.append("부재 프로젝트에 roadmap_state.json 을 만들었다")
        rc, payload = _run_tool(REFRESH_TOOL, ["--project-profile-path", str(profile), "--check"])
        if rc != 0 or payload.get("roadmap_drift") is not False:
            problems.append(f"--check 가 부재를 결함으로 오판: rc={rc}")
    _record("test_refresh_without_roadmap_is_additive", not problems, "; ".join(problems))


def test_session_context_builder_recommends_doc_phase_deliverables() -> None:
    """concept 단계 + 산출물 부재 → '산출물부터' 권고. roadmap 부재 → present=False."""
    problems: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp).resolve()
        _build_fixture(root, with_roadmap=True)
        ctx = build_session_roadmap_context(root)
        if not ctx.present or ctx.current_milestone_id != "M-001":
            problems.append(f"현재 마일스톤 미보고: {ctx.current_milestone_id}")
        if "산출물부터" not in ctx.recommendation:
            problems.append(f"doc 단계 산출물 권고 부재: {ctx.recommendation!r}")
        if ctx.total_leaves != 2:
            problems.append(f"leaf 분모 어긋남: {ctx.total_leaves}")
    with tempfile.TemporaryDirectory() as tmp:
        ctx = build_session_roadmap_context(Path(tmp).resolve())
        if ctx.present:
            problems.append("부재인데 present=True")
    _record("test_session_context_builder_recommends_doc_phase_deliverables", not problems, "; ".join(problems))


def test_repo_session_start_reports_roadmap() -> None:
    """이 저장소에서 session-start 출력에 roadmap_context 가 실린다 (읽기 전용 관찰)."""
    rc, payload = _run_tool(SESSION_TOOL, [], cwd=REPO_ROOT)
    ctx = payload.get("roadmap_context") or {}
    ok = rc == 0 and ctx.get("present") is True and ctx.get("issues_count") == 0
    _record("test_repo_session_start_reports_roadmap", ok,
            f"rc={rc} present={ctx.get('present')} issues={ctx.get('issues_count')}")


def test_demo_heuristic_is_retired_and_mcp_reads_roadmap() -> None:
    """milestones.py 정적 부재 + MCP payload 가 roadmap 을 읽는다 (부재 시 해당 없음)."""
    problems: list[str] = []
    if (SOURCE_ROOT / "workflow_kit" / "common" / "milestones.py").exists():
        problems.append("common/milestones.py 가 아직 있다 — 은퇴는 함수까지 지운다")
    result = assess_milestone_progress_payload(workspace_root=str(REPO_ROOT), tool_version="test")
    if result.get("roadmap_present") is not True or result.get("status") != "ok":
        problems.append(f"저장소 roadmap 미인식: {result.get('roadmap_present')}")
    with tempfile.TemporaryDirectory() as tmp:
        result = assess_milestone_progress_payload(workspace_root=tmp, tool_version="test")
        if result.get("roadmap_present") is not False:
            problems.append("부재 workspace 를 해당 없음으로 말하지 않는다")
    _record("test_demo_heuristic_is_retired_and_mcp_reads_roadmap", not problems, "; ".join(problems))


def main() -> int:
    cases = [
        test_refresh_regenerates_and_checks_roadmap_state,
        test_refresh_without_roadmap_is_additive,
        test_session_context_builder_recommends_doc_phase_deliverables,
        test_repo_session_start_reports_roadmap,
        test_demo_heuristic_is_retired_and_mcp_reads_roadmap,
    ]
    for case in cases:
        case()
    total = len(cases)
    print(f"\n{total - len(FAILURES)}/{total} passed")
    if FAILURES:
        raise AssertionError(f"{len(FAILURES)} case(s) failed: {FAILURES}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
