#!/usr/bin/env python3
"""state.json 은 생성물이다 — 생성기 출력과의 정합을 강제한다 (TASK-2026-08-11-main-018).

계보: TASK-017 §2 에서 state.json 이 생성기 출력과 갈라진 채 아무 검사도 그것을
오류로 보지 않았다. 근본 원인은 (1) 어느 쪽이 정본인지 미선언, (2) 세션 종료
절차에 생성기 호출 단계 부재. 처방은 정본 §11 선언 + `wk refresh-state` 창구 +
이 검사다.

- case 1: fixture 에서 refresh → --check 왕복이 무drift (기준 동작).
- case 2: **되주입** — state.json 을 손으로 오염시키면 --check 가 exit 1 로 잡고,
  drifted_keys 가 오염 지점을 가리킨다 (가짜를 심었는데 통과하면 검사가 죽은 것).
- case 3: 오염 후 refresh 재실행이 드리프트를 해소한다 (복구 경로).
- case 4: state.json 부재는 drift 가 아니라 별도 오류다 (exit 2, 미분류 fallback 금지).
- case 5: **이 저장소 자신** 의 state.json 이 생성기 출력과 일치한다 (자기 적용,
  §8.4). 손 편집이 커밋되면 여기서 red 가 난다.
- case 6: 선언과 창구의 정합 — 정본 §11 이 `wk refresh-state` 를 안내하고,
  TOOL_MODULES 가 실제로 그 명령을 노출한다 (안내만 있고 실행 경로가 없으면
  TASK-020 의 결함이 재발한 것).

case 5 가 저장소의 살아있는 memory 문서를 관찰하므로 정숙 구간에서 돈다.
"""
from __future__ import annotations

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

REQUIRES_QUIET_REPO = True

TOOL_PATH = SOURCE_ROOT / "workflow_kit" / "tools" / "refresh_state.py"
BRANCH = "main"


def _run_tool(args: list[str], cwd: Path | None = None) -> tuple[int, dict]:
    env = dict(os.environ)
    env["CODEX_WORKFLOW_BRANCH"] = BRANCH
    proc = subprocess.run(
        [sys.executable, str(TOOL_PATH), *args],
        capture_output=True, text=True, timeout=120,
        cwd=str(cwd) if cwd else None, env=env,
    )
    try:
        payload = json.loads(proc.stdout) if proc.stdout.strip() else {}
    except json.JSONDecodeError:
        raise AssertionError(f"tool 출력이 JSON 이 아니다:\n{proc.stdout}\n{proc.stderr}")
    return proc.returncode, payload


def _build_fixture(root: Path) -> Path:
    """profile + branch-scoped 메모리 최소 세트. Returns profile path."""
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
        "kind: generic\n---\n\n# TASK-2026-01-01-main-001 — fixture task\n",
        encoding="utf-8",
    )
    return profile


def case_1_roundtrip(profile: Path) -> Path:
    rc, payload = _run_tool(["--project-profile-path", str(profile)])
    assert rc == 0 and payload.get("state_cache_status") == "refreshed", f"refresh 실패: {payload}"
    state_path = Path(payload["state_path"])
    assert state_path.is_file(), f"state.json 미생성: {state_path}"
    rc, payload = _run_tool(["--project-profile-path", str(profile), "--check"])
    assert rc == 0 and payload.get("drift") is False, f"무drift 여야 한다: {payload}"
    return state_path


def case_2_reinjection(profile: Path, state_path: Path) -> None:
    data = json.loads(state_path.read_text(encoding="utf-8"))
    data["session"]["recent_done_items"] = ["TASK-9999-99-99-fake-001 — 손으로 끼워 넣은 완료 항목"]
    state_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    rc, payload = _run_tool(["--project-profile-path", str(profile), "--check"])
    assert rc == 1, f"오염을 심었는데 통과했다 — 검사가 죽었다: {payload}"
    assert "session" in payload.get("drifted_keys", []), f"drift 지점 미보고: {payload}"


def case_3_recovery(profile: Path) -> None:
    rc, payload = _run_tool(["--project-profile-path", str(profile)])
    assert rc == 0, f"복구 refresh 실패: {payload}"
    rc, payload = _run_tool(["--project-profile-path", str(profile), "--check"])
    assert rc == 0 and payload.get("drift") is False, f"refresh 후에도 drift: {payload}"


def case_4_missing_state(profile: Path, state_path: Path) -> None:
    state_path.unlink()
    rc, payload = _run_tool(["--project-profile-path", str(profile), "--check"])
    assert rc == 2 and payload.get("error_code") == "missing_state_json", (
        f"부재는 drift 가 아니라 별도 오류여야 한다: rc={rc} {payload}"
    )


def case_5_self_application() -> None:
    profile = REPO_ROOT / "docs" / "PROJECT_PROFILE.md"
    state_path = REPO_ROOT / "ai-workflow" / "memory" / "active" / BRANCH / "state.json"
    if not profile.is_file() or not state_path.is_file():
        raise AssertionError("자기 적용 대상 문서가 없다 (profile 또는 state.json 부재)")
    rc, payload = _run_tool(["--project-profile-path", str(profile), "--check"])
    assert rc == 0, (
        "이 저장소의 state.json 이 생성기 출력과 갈라졌다. state.json 은 생성물이다 — "
        f"`wk refresh-state` 로 재생성하라 (정본 §11). drifted_keys={payload.get('drifted_keys')}"
    )


def case_6_declaration_matches_exposure() -> None:
    standard = (SOURCE_ROOT / "core" / "global_workflow_standard.md").read_text(encoding="utf-8")
    assert "`wk refresh-state`" in standard, "정본 §11 에 wk refresh-state 안내가 없다"
    assert "생성물" in standard, "정본 §11 에 state.json 생성물 선언이 없다"
    from workflow_kit.common.tool_dispatch import TOOL_MODULES
    assert TOOL_MODULES.get("refresh-state") == "workflow_kit.tools.refresh_state", (
        "정본이 안내하는 wk refresh-state 가 TOOL_MODULES 에 없다 — 안내만 있고 실행 경로가 없다 (TASK-020 재발)"
    )


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="check-state-json-generated-") as tmp:
        root = Path(tmp).resolve()  # macOS /private symlink (TASK-017)
        profile = _build_fixture(root)
        state_path = case_1_roundtrip(profile)
        case_2_reinjection(profile, state_path)
        case_3_recovery(profile)
        case_4_missing_state(profile, state_path)
    case_5_self_application()
    case_6_declaration_matches_exposure()
    print("state.json generated-artifact check passed (6 cases)")
    return 0


def test_case_1() -> None:
    with tempfile.TemporaryDirectory(prefix="check-state-json-generated-") as tmp:
        profile = _build_fixture(Path(tmp).resolve())
        case_1_roundtrip(profile)


def test_case_2() -> None:
    with tempfile.TemporaryDirectory(prefix="check-state-json-generated-") as tmp:
        profile = _build_fixture(Path(tmp).resolve())
        state_path = case_1_roundtrip(profile)
        case_2_reinjection(profile, state_path)


def test_case_3() -> None:
    with tempfile.TemporaryDirectory(prefix="check-state-json-generated-") as tmp:
        profile = _build_fixture(Path(tmp).resolve())
        state_path = case_1_roundtrip(profile)
        case_2_reinjection(profile, state_path)
        case_3_recovery(profile)


def test_case_4() -> None:
    with tempfile.TemporaryDirectory(prefix="check-state-json-generated-") as tmp:
        profile = _build_fixture(Path(tmp).resolve())
        state_path = case_1_roundtrip(profile)
        case_4_missing_state(profile, state_path)


def test_case_5() -> None:
    case_5_self_application()


def test_case_6() -> None:
    case_6_declaration_matches_exposure()


if __name__ == "__main__":
    raise SystemExit(main())
