#!/usr/bin/env python3
"""v1.0.0: branch-scoped memory + 종료 브랜치 자동 아카이브 smoke (8 cases).

검증 대상:
  1) path helper 가 `active/<branch>/` 를 반환한다
  2) legacy fallback — 미마이그레이션 저장소(`active/backlog/`)는 깨지지 않는다
  3) task ID 가 `TASK-<date>-<slug>-<NNN>` 이고 **연도를 순번으로 오인하지 않는다**
     (기존 `TASK-(\\d+)` 정규식이 `TASK-2026-07-20-001` → `TASK-2027` 을 만들던 버그)
  4) 다른 브랜치의 task 번호는 순번에 영향을 주지 않는다 (동시 작업 충돌 0)
  5) branch slug 정규화 (`feature/x` → `feature-x`)
  6) 아카이버가 git 에 없는 브랜치를 탐지한다
  7) 아카이버가 살아있는 브랜치 / 현재 브랜치는 건드리지 않는다
  8) 아카이브 결과에 `.archived.json` 메타(task_ids 포함)가 남는다

Refs:
  - workflow-source/MEMORY_GOVERNANCE.md §2 (Branch-scoped layout)
  - ai-workflow/memory/active/README.md §1
  - workflow-source/tools/archive_branch_memory.py
"""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from workflow_kit.common import paths as P  # noqa: E402

ARCHIVER = SOURCE_ROOT / "tools" / "archive_branch_memory.py"


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def _make_profile(root: Path, *, branch_scoped: bool, branch: str = "main") -> Path:
    """temp 저장소에 PROJECT_PROFILE.md + layout 을 만든다."""
    active = root / "ai-workflow" / "memory" / "active"
    base = (active / branch) if branch_scoped else active
    (base / "backlog" / "tasks").mkdir(parents=True, exist_ok=True)
    (base / "sessions").mkdir(parents=True, exist_ok=True)
    (base / "state.json").write_text("{}", encoding="utf-8")
    profile = active / "PROJECT_PROFILE.md"
    profile.write_text("# profile\n", encoding="utf-8")
    return profile


# --- case 1: branch-scoped 해석 ---
def case_1_branch_scoped_paths() -> bool:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        profile = _make_profile(root, branch_scoped=True, branch=P.get_current_branch())
        backlog = P.workflow_backlog_dir(profile)
        if backlog.parent.name != P.get_current_branch():
            print(f"  FAIL: backlog 가 branch dir 하위가 아님: {backlog}")
            return False
        if P.workflow_tasks_dir(profile) != backlog / "tasks":
            print("  FAIL: tasks_dir 불일치")
            return False
        print(f"  PASS: active/<branch>/backlog 로 해석 ({backlog.parent.name})")
        return True


# --- case 2: legacy fallback ---
def case_2_legacy_fallback() -> bool:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        profile = _make_profile(root, branch_scoped=False)
        backlog = P.workflow_backlog_dir(profile)
        if backlog.name != "backlog" or backlog.parent.name != "active":
            print(f"  FAIL: legacy fallback 실패: {backlog}")
            return False
        state = P.workflow_state_path(profile)
        if state.parent.name != "active":
            print(f"  FAIL: state legacy fallback 실패: {state}")
            return False
        print("  PASS: 미마이그레이션 저장소는 legacy(active/) 로 fallback")
        return True


# --- case 3~5: task ID ---
def _backlog_mod():
    return _load(SOURCE_ROOT / "skills" / "backlog-update" / "scripts" / "run_backlog_update.py",
                 "_bu_mod")


def case_3_task_id_no_year_confusion() -> bool:
    m = _backlog_mod()
    got = m.suggest_next_task_id([{"task_id": "TASK-2026-07-20-001"}], target_date="2026-07-20")
    if got.startswith("TASK-2027") or "-2027" in got:
        print(f"  FAIL: 연도를 순번으로 오인: {got}")
        return False
    if not got.endswith("-002"):
        print(f"  FAIL: 같은 날짜 legacy ID 다음은 002 여야 함: {got}")
        return False
    print(f"  PASS: 연도 오인 없음 ({got})")
    return True


def case_4_other_branch_does_not_bump() -> bool:
    m = _backlog_mod()
    slug = m.branch_slug()
    other = [{"task_id": f"TASK-2026-07-21-someotherbranch-007"}]
    got = m.suggest_next_task_id(other, target_date="2026-07-21")
    if not got.endswith("-001"):
        print(f"  FAIL: 다른 브랜치 번호가 순번에 영향: {got}")
        return False
    if slug not in got:
        print(f"  FAIL: 현재 브랜치 slug 미포함: {got}")
        return False
    print(f"  PASS: 다른 브랜치는 순번에 영향 없음 ({got})")
    return True


def case_5_branch_slug_normalization() -> bool:
    m = _backlog_mod()
    if m.branch_slug("feature/x") != "feature-x":
        print(f"  FAIL: slug 정규화 실패: {m.branch_slug('feature/x')}")
        return False
    if "/" in m.branch_slug("a/b/c"):
        print("  FAIL: slug 에 '/' 잔존")
        return False
    print("  PASS: branch slug 정규화 (feature/x → feature-x)")
    return True


# --- case 6~8: 아카이버 ---
def _run_archiver(memory_root: Path, *args: str) -> dict:
    proc = subprocess.run(
        [sys.executable, str(ARCHIVER), "--memory-root", str(memory_root), "--json", *args],
        capture_output=True, text=True, timeout=60,
    )
    return json.loads(proc.stdout) if proc.stdout.strip() else {}


def _seed_branch(memory_root: Path, branch: str) -> None:
    d = memory_root / "active" / branch / "backlog" / "tasks"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"TASK-2026-07-21-{branch}-001.md").write_text("# t\n", encoding="utf-8")


def case_6_detect_dead_branch() -> bool:
    with tempfile.TemporaryDirectory() as tmp:
        mr = Path(tmp)
        _seed_branch(mr, "definitely-not-a-real-branch-xyz")
        res = _run_archiver(mr)
        acts = [c for c in res.get("candidates", []) if c["action"] == "archive"]
        if not any("definitely-not-a-real-branch-xyz" == c["branch"] for c in acts):
            print(f"  FAIL: 종료 브랜치 미탐지: {res.get('candidates')}")
            return False
        print("  PASS: git 에 없는 브랜치를 아카이브 대상으로 탐지")
        return True


def case_7_keep_current_and_live() -> bool:
    with tempfile.TemporaryDirectory() as tmp:
        mr = Path(tmp)
        current = P.get_current_branch()
        _seed_branch(mr, current)
        res = _run_archiver(mr)
        for c in res.get("candidates", []):
            if c["branch"] == current and c["action"] == "archive":
                print(f"  FAIL: 현재 브랜치를 아카이브 대상으로 판정: {c}")
                return False
        print(f"  PASS: 현재/살아있는 브랜치는 보존 ({current})")
        return True


def case_8_archive_emits_metadata() -> bool:
    with tempfile.TemporaryDirectory() as tmp:
        mr = Path(tmp)
        branch = "gone-branch-for-smoke"
        _seed_branch(mr, branch)
        _run_archiver(mr, "--apply")
        dst = mr / "archived" / branch
        meta = dst / ".archived.json"
        if not meta.is_file():
            print(f"  FAIL: .archived.json 부재 ({dst})")
            return False
        data = json.loads(meta.read_text(encoding="utf-8"))
        if data.get("branch") != branch or data.get("task_count") != 1:
            print(f"  FAIL: 메타데이터 불일치: {data}")
            return False
        if (mr / "active" / branch).exists():
            print("  FAIL: 원본이 active/ 에 남아있음")
            return False
        print(f"  PASS: archived/{branch}/ 이동 + 메타(task_ids {data['task_ids']})")
        return True


def main() -> int:
    print("=" * 60)
    print("branch-scoped memory + 자동 아카이브 smoke (v1.0.0)")
    print("=" * 60)
    cases = [
        case_1_branch_scoped_paths,
        case_2_legacy_fallback,
        case_3_task_id_no_year_confusion,
        case_4_other_branch_does_not_bump,
        case_5_branch_slug_normalization,
        case_6_detect_dead_branch,
        case_7_keep_current_and_live,
        case_8_archive_emits_metadata,
    ]
    passed = 0
    for c in cases:
        print(f"\n{c.__name__}:")
        try:
            if c():
                passed += 1
        except Exception as exc:  # noqa: BLE001
            print(f"  FAIL: {type(exc).__name__}: {exc}")
    print()
    print("=" * 60)
    print(f"Result: {passed}/{len(cases)} PASS")
    print("=" * 60)
    return 0 if passed == len(cases) else 1


if __name__ == "__main__":
    sys.exit(main())
