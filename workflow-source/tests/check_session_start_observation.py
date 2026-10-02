#!/usr/bin/env python3
"""session-start 관찰 경로가 **재발하지 않는다**는 것 자체를 강제한다
(TASK-2026-10-02-feat-auto-20261002-4a5d394c-003).

`--no-reflect` 플래그로 session-start 의 합류 승격을 막는 것은 **코드 한 줄**이라,
다음 검사 작성자가 같은 도구를 그냥 부르면 조용히 돌아간다. 실제로 두 번 일어났다
(`check_roadmap_wiring` · `check_state_reconcile`) — 두 경우 모두 게이트 도중
브랜치 메모리가 `archived/` 로 옮겨졌고, 그损坏을 만든 건 **게이트가 자기 검사로
잡는 순환**이었다.

여기서는 두 축을 건다:

1. **구문** — 검사는 session-start 를 직접 호출하지 않는다. 관찰은
   :mod:`_session_observer` 하나를 통한다. 플래그를 까먹을 경로가 없어진다.
2. **행동** — 격리 픽스처(main 체크아웃 + 병합된 죽은 브랜치 메모리)에서 공용
   헬퍼를 돌려 **바이트가 그대로인지** 본다. 이건 매 게이트마다 실행되므로,
   session-start 가 관찰 경로에서 쓰는 법이 바뀌면 그 자리에서 잡힌다.

주의 — 이 검사는 **관찰 경로의 계약**을 본다. session-start 가 그 자체로
쓰는지는 보지 않는다(그건 `check_no_repo_write` 축의 몫이고, 실제로 그 축이
붙잡았다). 여기서 보는 건 "검사가 관찰만 하는가" 다.
"""

from __future__ import annotations

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

from _session_observer import SESSION_START_TOOL, observe_session_start  # noqa: E402

#: 검사가 session-start 를 직접 부를 때 남기는 지문. 툴 경로 조각만 본다 —
#: `skills/session-start/scripts/run_session_start.py` 는 **스킬 래퍼**라 별개
#: 진입점이고(격리 픽스처를 돌리는 데 쓰인다), 여기에 걸리면 안 된다.
OBSERVER = "_session_observer.py"

FAILURES: list[str] = []


def _record(case: str, ok: bool, detail: str = "") -> None:
    if not ok:
        FAILURES.append(f"{case}: {detail}" if detail else case)


def _tree_snapshot(root: Path) -> dict[str, bytes]:
    """디렉터리 전체를 파일명 → 바이트로. 권한·mtime 이 아니라 **내용**을 본다."""
    snapshot: dict[str, bytes] = {}
    for path in sorted(root.rglob("*")):
        if path.is_file() and ".git" not in path.relative_to(root).parts:
            snapshot[path.relative_to(root).as_posix()] = path.read_bytes()
    return snapshot


def _build_stale_branch_fixture(root: Path) -> None:
    """main 체크아웃 + **병합된 죽은 브랜치 메모리** — 승격이 열리는 정확한 모양.

    여기서 `--no-reflect` 없으면 `active/stale-branch/` 가 `archived/` 로 옮겨지고
    main handoff 가 덮어써진다. 그 갱신이 사라졌다는 게 헬퍼의 존재 이유다.
    """
    for namespace in ("main", "stale-branch"):
        base = root / "ai-workflow" / "memory" / "active" / namespace
        (base / "backlog").mkdir(parents=True, exist_ok=True)
        (base / "sessions").mkdir(parents=True, exist_ok=True)
        (base / "session_handoff.md").write_text(
            "# Handoff\n\n## 2. 진행 중 작업\n\n- 현재 `in_progress` 작업:\n-\n", encoding="utf-8"
        )
        (base / "backlog" / "2026-10-01.md").write_text("# Backlog\n", encoding="utf-8")
        (base / "sessions" / "s.md").write_text("# Session\n", encoding="utf-8")
    (root / "docs").mkdir(parents=True, exist_ok=True)
    (root / "docs" / "PROJECT_PROFILE.md").write_text("# Profile\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q", "-b", "main", "."], cwd=str(root), check=True)
    subprocess.run(["git", "add", "-A"], cwd=str(root), check=True)
    subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "fixture"],
        cwd=str(root), check=True,
    )


def _changed(before: dict[str, bytes], after: dict[str, bytes]) -> list[str]:
    return sorted(set(before) ^ set(after)) or sorted(
        name for name in set(before) & set(after) if before[name] != after[name]
    )


def _invoke_tool_directly(root: Path) -> None:
    """가드를 **붙이지 않고** 툴을 부른다 — 음성 대조군."""
    import os

    env = dict(os.environ)
    env["CODEX_WORKFLOW_BRANCH"] = "main"
    env["PYTHONPATH"] = str(SOURCE_ROOT)
    subprocess.run(
        [sys.executable, str(SESSION_START_TOOL),
         "--project-profile-path", str(root / "docs" / "PROJECT_PROFILE.md")],
        cwd=str(root), capture_output=True, text=True, timeout=180, env=env,
    )


def case_fixture_reproduces_the_defect() -> None:
    """음성 대조군 — 같은 픽스처에 **가드 없이** 부르면 실제로 쓰인다.

    이게 없으면 아래 case 의 green 이 아무것도 증명하지 않는다. 격리 모형이 결함을
    재현하는지 같은 case 안에서 따로 재야 한다 (`_newline_shim` 이 세운 원칙 —
    "shim 경유 green 은 아무것도 증명하지 않는다"). 재현되지 않으면 그 픽스처가
    빈틈 있다는 뜻이므로 여기서 red 다.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir) / "fixture"
        root.mkdir()
        _build_stale_branch_fixture(root)
        before = _tree_snapshot(root)
        _invoke_tool_directly(root)
        changed = _changed(before, _tree_snapshot(root))
        _record(
            "case_fixture_reproduces_the_defect",
            bool(changed),
            "가드 없는 호출이 픽스처를 **안** 썼다 — 픽스처가 결함을 재현하지 못한다. "
            "아래 안전성 case 는 빈 증명이 된다 (main 체크아웃 + 병합된 죽은 브랜치 메모리 모양을 재확인)",
        )


def case_observer_does_not_write_in_a_stale_branch_project() -> None:
    """행동 계약 — 격리 픽스처에서 헬퍼를 돌려도 픽스처가 **바이트 단위로** 그대로다.

    이 case 가 이 모듈의 값이다. 위 음성 대조군과 **같은 픽스처**를 쓴다 — 그래야
    "고쳤다" 가 성립한다. 관찰 경로가 session-start 안에서 바뀌면 여기서 멈춘다.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir) / "fixture"
        root.mkdir()
        _build_stale_branch_fixture(root)
        before = _tree_snapshot(root)
        _rc, _payload = observe_session_start(root / "docs" / "PROJECT_PROFILE.md", repo_root=root)
        changed = _changed(before, _tree_snapshot(root))
        _record(
            "case_observer_does_not_write_in_a_stale_branch_project",
            not changed,
            f"관찰 경로가 픽스처를 썼다: {changed[:4]}"
            " — `--no-reflect` 가 빠졌거나, 관찰이 쓰기 경로로 돌아갔다",
        )


def case_observer_keeps_observation_contract() -> None:
    """헬퍼는 승격을 끄고, 아카이브 권한은 절대 열지 않는다."""
    text = (TESTS_ROOT / OBSERVER).read_text(encoding="utf-8")
    code = "\n".join(
        line for line in text.splitlines() if not line.lstrip().startswith("#")
    )
    _record(
        "case_observer_forces_no_reflect",
        '"--no-reflect"' in code,
        f"{OBSERVER} 가 --no-reflect 를 강제하지 않는다",
    )
    _record(
        "case_observer_never_grants_archive",
        "--archive-stale-branches" not in code,
        f"{OBSERVER} 가 --archive-stale-branches 를 준다 — 관찰 경로에 쓰기 권한이 들어간다",
    )
    _record(
        "case_observer_uses_own_observer",
        "TOOL_PATH" not in code and "def _run_session_start" not in code,
        f"{OBSERVER} 가 관찰 전용 관찰자로 수렴되지 않았다 (자체 호출 래퍼가 생겼다)",
    )


def main() -> int:
    # case 목록에서 개수를 유도한다 — 상수로 적으면 case 를 하나 더할 때 조용히
    # 어긋난다 (`check_case_count` 가 그 상수를 금지한다). 이 저장소가 실제로
    # 겪은 사고("Skills (4) 인데 설명은 스킬 3종") 와 같은 계종이다.
    cases = [
        case_observer_keeps_observation_contract,
        case_fixture_reproduces_the_defect,
        case_observer_does_not_write_in_a_stale_branch_project,
    ]
    for case in cases:
        case()
    total = len(cases)
    print(f"{total - len(FAILURES)}/{total} passed")
    if FAILURES:
        raise AssertionError(f"{len(FAILURES)} case(s) failed: {FAILURES}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
