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
    # 관찰은 공용 헬퍼를 통한다 — 이 줄을 안 넣으면 meta-watch 가 "선언 밖 접근" 으로
    # 잡는다 (`check_deploy_doctor` 의 `_newline_shim.py` 선언과 같은 계종).
    "workflow-source/tests/_session_observer.py",
)

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
TESTS_ROOT = Path(__file__).resolve().parent
for _entry in (str(SOURCE_ROOT), str(TESTS_ROOT)):
    if _entry not in sys.path:
        sys.path.insert(0, _entry)

from _session_observer import observe_session_start  # noqa: E402

from workflow_kit.common.read_only_bundle import assess_milestone_progress_payload  # noqa: E402
from workflow_kit.common.state.roadmap import (  # noqa: E402
    build_session_roadmap_context,
    state_matches_regeneration,
    state_path as roadmap_state_path,
)

REFRESH_TOOL = SOURCE_ROOT / "workflow_kit" / "tools" / "refresh_state.py"
BACKLOG_TOOL = SOURCE_ROOT / "workflow_kit" / "tools" / "backlog_update.py"
BRANCH = "main"

FAILURES: list[str] = []


def _record(case: str, ok: bool, detail: str = "") -> None:
    if ok:
        print(f"PASS: {case}")
    else:
        print(f"FAIL: {case}{(' — ' + detail) if detail else ''}")
        FAILURES.append(case)


def _repo_branch() -> str:
    """이 저장소를 관찰할 때 강제할 브랜치 — 실제 checkout 브랜치, 네임스페이스가 없으면 `BRANCH`.

    `main` 을 강제하면 worktree 에서 현재 브랜치가 "HEAD 에 병합된 브랜치" 로 보여
    session-start 가 합류 반영 · 아카이브를 **실제 저장소에** 실행했다 (115차 실측 —
    게이트 도중 자기 브랜치 메모리가 archived/ 로 옮겨졌다). 네임스페이스가 없는
    브랜치(CI detached HEAD · slash 컨텍스트)를 그대로 넘기면 seed 가 쓰므로 그때만 `BRANCH`.
    """
    proc = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=str(REPO_ROOT),
                          capture_output=True, text=True, encoding="utf-8")
    name = proc.stdout.strip()
    if proc.returncode == 0 and name and name != "HEAD" \
            and (REPO_ROOT / "ai-workflow" / "memory" / "active" / name / "session_handoff.md").is_file():
        return name
    return BRANCH


def _memory_status() -> str:
    proc = subprocess.run(["git", "status", "--porcelain", "--", "ai-workflow/memory"],
                          cwd=str(REPO_ROOT), capture_output=True, text=True, encoding="utf-8")
    return proc.stdout


def _run_tool(tool: Path, args: list[str], cwd: Path | None = None,
              branch: str = BRANCH) -> tuple[int, dict]:
    env = dict(os.environ)
    env["CODEX_WORKFLOW_BRANCH"] = branch
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


def test_backlog_update_apply_regenerates_roadmap_state() -> None:
    """`backlog-update --apply` 는 task frontmatter 를 쓰는 층이므로 roadmap_state 도 같이 재생성한다.

    task frontmatter(`wbs` · status)가 roadmap_state.json 의 SSOT 다. 이 도구가 그것을
    쓰고도 파생물을 안 따라가게 두면, 뒤처짐이 push 게이트의
    `check_roadmap_state_generated` 에서야 드러난다 (2026-09-17 · 2026-09-18 이틀에
    두 번 실측). 판정은 **산출물**을 잰다 — 재생성 호출이 사라지면 여기가 red 다.

    - 재생성이 실제로 일어나고, 그 write 가 `written_paths` 에 보인다.
    - `--apply` 없는 draft 는 여전히 아무것도 쓰지 않는다 (dry-run 오염 금지, v1.0.1).
    - roadmap 부재 프로젝트에서는 파일을 만들지 않는다 (additive).
    """
    problems: list[str] = []
    create_args = ["--task-name", "배선 fixture task", "--task-brief", "배선 시험", "--mode", "create"]
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp).resolve()
        profile = _build_fixture(root, with_roadmap=True)
        _run_tool(REFRESH_TOOL, ["--project-profile-path", str(profile)])
        state_file = roadmap_state_path(root)
        if not state_file.is_file():
            problems.append("사전 조건: roadmap_state.json 미생성")
        rc, payload = _run_tool(BACKLOG_TOOL, [
            "--project-profile-path", str(profile), *create_args,
            "--wbs", "M-001/WBS-1.2", "--apply",
        ])
        if rc != 0:
            problems.append(f"backlog-update 실패: rc={rc} {payload.get('error')}")
        ok, reason = state_matches_regeneration(root)
        if not ok:
            problems.append(f"task 를 쓰고도 roadmap_state 가 뒤처졌다: {reason}")
        if str(state_file) not in payload.get("written_paths", []):
            problems.append("roadmap_state.json write 가 written_paths 에 안 보인다")
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp).resolve()
        profile = _build_fixture(root, with_roadmap=True)
        rc, _ = _run_tool(BACKLOG_TOOL, [
            "--project-profile-path", str(profile), *create_args,
            "--wbs", "M-001/WBS-1.2",
        ])
        if roadmap_state_path(root).exists():
            problems.append("--apply 없는 draft 가 roadmap_state.json 을 썼다")
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp).resolve()
        profile = _build_fixture(root, with_roadmap=False)
        rc, _ = _run_tool(BACKLOG_TOOL, [
            "--project-profile-path", str(profile), *create_args, "--apply",
        ])
        if rc != 0:
            problems.append(f"roadmap 부재에서 backlog-update 실패: rc={rc}")
        if roadmap_state_path(root).exists():
            problems.append("roadmap 부재 프로젝트에 roadmap_state.json 을 만들었다")
    _record("test_backlog_update_apply_regenerates_roadmap_state", not problems, "; ".join(problems))


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
    """이 저장소에서 session-start 출력에 roadmap_context 가 실린다 (읽기 전용 관찰).

    관찰에는 두 겹의 방어가 필요하고 둘은 **다른 환경에서만** 서로를 대신한다.
    worktree 에서 `main` 을 강제하면 자기 브랜치가 "HEAD 에 병합된" 것으로 보여
    합류 반영이 열린다 — 그래서 **환경** 층은 `branch=_repo_branch()`
    (TASK-2026-10-02-claude-remote-sync-status-1ce0a3-003 실측).

    그 갱신은 worktree 밖에서 그대로 열린다. **main 체크아웃 + 병합된 죽은 브랜치
    메모리** 픽스처 실측(2026-10-02, filesystem 직접 비교):

        --no-reflect 없음 → active/ 에서 stale-branch 가 사라지고 archived/ 로
                           옮겨졌고, main/session_handoff.md 가 4 → 332 byte 로
                           덮어써졌다 (합류 반영이 본 브랜치 메모리를 씀).
        --no-reflect 있음 → active/ 그대로, archived/ 없음, handoff 4 byte 그대로.

    그 가드가 죽은 브랜치를 `keep` 에 넣어 자기 브랜치를 지켜내는 것과 달리,
    여기서 사라지는 대상은 **체크아웃된 브랜치가 아니다**. 그래서 도구 층 방어는
    이 시나리오를 덮지 못하고, **의도** 층인 `--no-reflect` 만 남는다 — 관찰만
    원하는 호출자에게 쓰는 면이 없으면 확인할 사람 없는 갱신이 되기 때문이다
    (TASK-2026-10-02-feat-auto-20261002-4a5d394c-002).
    """
    before = _memory_status()
    rc, payload = observe_session_start(REPO_ROOT / "docs" / "PROJECT_PROFILE.md", repo_root=REPO_ROOT)
    after = _memory_status()
    ctx = payload.get("roadmap_context") or {}
    ok = (rc == 0 and ctx.get("present") is True and ctx.get("issues_count") == 0
          and before == after)
    _record("test_repo_session_start_reports_roadmap", ok,
            f"rc={rc} present={ctx.get('present')} issues={ctx.get('issues_count')}"
            + ("" if before == after else f" — 관찰이 저장소 메모리를 바꿨다:\n{after}"))


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
        test_backlog_update_apply_regenerates_roadmap_state,
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
