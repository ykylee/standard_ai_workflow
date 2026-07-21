#!/usr/bin/env python3
"""Smoke test — v0.14.0+ append-only memory layout 무결성 검증 (6 cases).

본 smoke 는 다음 layout 의 SSOT 무결성을 검증:
  ai-workflow/memory/active/
    state.json (read-only snapshot, builder 가 rebuild)
    backlog/                       ← per-day index (append-only)
      YYYY-MM-DD.md
      tasks/
        TASK-<date>-<NNN>.md       ← per-task SSOT
    sessions/                      ← per-session file

6 cases:
  1) layout existence: backlog/, backlog/tasks/, sessions/ 모두 존재 + 비어있지 않음
  2) legacy absent: active/work_backlog.md 부재 (.bak fallback 은 OK)
  3) state.json source_of_truth: daily_backlog_dir / tasks_dir / sessions_dir 모두 dir path
  4) daily index links: TASK-* link 가 모두 backlog/tasks/TASK-*.md 로 resolve
  5) task frontmatter: MEMORY_GOVERNANCE.md §2 정합 (6 keys 모두 존재)
  6) sessions cross-ref: sessions/*.md 1+ 파일 존재

Refs:
  - workflow-source/MEMORY_GOVERNANCE.md §2 (Standard Templates)
  - ai-workflow/memory/active/README.md (운영 가이드)
  - ADR-003 (deprecation cycle pattern)
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
ACTIVE_DIR = REPO_ROOT / "ai-workflow" / "memory" / "active"


def _resolve_layout_root() -> Path:
    """v1.0.0 branch-scoped: layout 검증의 기준 디렉터리를 찾는다.

    메모리는 `active/<branch>/` 로 분리되므로 layout 은 그 하위에 있다. 아직
    마이그레이션하지 않은 저장소(`active/backlog` 가 직접 존재)는 legacy 로 취급한다.
    """
    if (ACTIVE_DIR / "backlog").is_dir():
        return ACTIVE_DIR
    for cand in sorted(ACTIVE_DIR.rglob("*")):
        if cand.is_dir() and (cand / "backlog").is_dir():
            return cand
    return ACTIVE_DIR


LAYOUT_ROOT = _resolve_layout_root()

# MEMORY_GOVERNANCE.md §2 Task Detail 템플릿 정합 — TASK-*.md frontmatter 필수 keys
TASK_FRONTMATTER_KEYS = frozenset({
    "id", "status", "created_at", "source_anchor", "source_path", "kind",
})

errors: list[str] = []
warnings: list[str] = []


def _check_layout_existence() -> None:
    """1) backlog/, backlog/tasks/, sessions/ 디렉토리 존재 + 최소 1 file."""
    required_dirs = {
        "backlog": LAYOUT_ROOT / "backlog",
        "backlog/tasks": LAYOUT_ROOT / "backlog" / "tasks",
        "sessions": LAYOUT_ROOT / "sessions",
    }
    for name, path in required_dirs.items():
        if not path.is_dir():
            errors.append(f"[layout] {name}/ 디렉토리 부재: {path}")
            continue
        # .gitkeep 만 있고 실제 file 이 없을 수 있음 → 최소 1 file check
        files = [f for f in path.iterdir() if f.name != ".gitkeep"]
        if not files:
            errors.append(f"[layout] {name}/ 가 비어 있음: {path}")


def _check_legacy_absent() -> None:
    """2) legacy `active/work_backlog.md` 부재 (`.bak` fallback 은 OK, v0.14.1+ warning 단계).

    v0.14.0 1st cycle: `.bak` 보존 (silent read fallback).
    v0.14.1 1st cycle 종결: `.bak` 존재 시 warning 단계. 본 smoke 는 errors 와
    warnings 분리 — `.bak` 부재 = PASS, `.bak` 존재 = WARNING (별도 메시지).
    """
    legacy = ACTIVE_DIR / "work_backlog.md"
    if legacy.exists():
        errors.append(f"[legacy] {legacy} 가 여전히 존재 (1st deprecation cycle 단계)")

    # v0.14.1: .bak fallback 의 1st cycle 종결 — warning 단계
    bak = ACTIVE_DIR / "work_backlog.md.bak"
    if bak.exists():
        # WARNING 단계 — error 아님 (errors list 에 추가 안 함)
        # main() 에서 errors 와 별도로 출력
        warnings.append(
            f"[legacy] {bak} 보존 중 (1st deprecation cycle). "
            f"v0.14.5 부터 --legacy-memory opt-out flag 필요, v0.15.0 에서 drop."
        )


def _check_state_json_source_of_truth() -> None:
    """3) state.json.source_of_truth 의 신규 dir 3개 모두 dir path."""
    state_json = LAYOUT_ROOT / "state.json"
    if not state_json.exists():
        errors.append(f"[state_json] {state_json} 부재")
        return
    try:
        data = json.loads(state_json.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f"[state_json] JSON parse fail: {exc}")
        return
    sot = data.get("source_of_truth", {})
    for key in ("daily_backlog_dir", "tasks_dir", "sessions_dir"):
        val = sot.get(key)
        if not val:
            errors.append(f"[state_json] source_of_truth.{key} 부재 (v0.14.0+ append-only layout)")
            continue
        # file path (.md) 가 아닌 directory path 여야 함
        if val.endswith(".md"):
            errors.append(f"[state_json] source_of_truth.{key} 가 file path (.md) — directory 여야 함: {val!r}")
            continue
        resolved = (ACTIVE_DIR / val).resolve()
        if not resolved.is_dir():
            # v0.15.17 fix: state.json 의 path 가 *repo-relative* 로 emit 될 수도 있음
            # (generate_workflow_state.py --workspace-root . 사용 시). 둘 다 시도.
            resolved = (REPO_ROOT / val).resolve()
        if not resolved.is_dir():
            errors.append(f"[state_json] source_of_truth.{key} → {val!r} 가 dir 아님 ({resolved})")


def _check_daily_index_links_resolve() -> None:
    """4) daily index 의 `**TASK-*` link 가 tasks/ 또는 sessions/ 의 file 로 resolve.

    session kind entry 는 `tasks/` 가 아닌 `sessions/<raw_path_stem>.md` 에 저장됨
    (migration script 가 raw_path stem 그대로 사용 → 같은 session 의 두 entry 가
    overwrite 되지 않도록). daily index 의 `source: [[<path>]] {#anchor}` 라인의
    path stem 으로 session file 매칭.
    """
    backlog_dir = LAYOUT_ROOT / "backlog"
    if not backlog_dir.is_dir():
        return  # 1) 에서 이미 error
    tasks_dir = LAYOUT_ROOT / "backlog" / "tasks"
    sessions_dir = LAYOUT_ROOT / "sessions"
    link_re = re.compile(r"\*\*TASK-(\d{4}-\d{2}-\d{2}-\d{3})\*\*\s*\[([^\]]+)\]")
    source_re = re.compile(r"\[\[([^\]]+)\]\]\s+\{#([^}]+)\}")

    for daily_file in sorted(backlog_dir.glob("[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9].md")):
        try:
            text = daily_file.read_text(encoding="utf-8")
        except OSError as exc:
            errors.append(f"[daily-index] {daily_file.name} read fail: {exc}")
            continue

        # section 단위 parsing: link + kind_marker + source_path 추출
        current_task_id: str | None = None
        current_kind: str | None = None
        current_source: str | None = None

        def _verify() -> None:
            if current_task_id is None:
                return
            if current_kind and "session" in current_kind:
                # session entry → sessions/<raw_path_stem>.md
                if current_source:
                    stem = Path(current_source).stem
                    session_path = sessions_dir / f"{stem}.md"
                    if not session_path.exists():
                        errors.append(
                            f"[daily-index] {daily_file.name} → TASK-{current_task_id} "
                            f"session 매핑 부재: {session_path}"
                        )
                else:
                    errors.append(
                        f"[daily-index] {daily_file.name} → TASK-{current_task_id} "
                        f"session kind 인데 source path 부재"
                    )
            else:
                # release / generic → tasks/TASK-<id>.md
                task_path = tasks_dir / f"TASK-{current_task_id}.md"
                if not task_path.exists():
                    errors.append(
                        f"[daily-index] {daily_file.name} → TASK-{current_task_id} 부재: {task_path}"
                    )

        for line in text.splitlines():
            link_m = link_re.search(line)
            if link_m:
                _verify()
                current_task_id = link_m.group(1)
                current_kind = link_m.group(2)
                current_source = None
                continue
            src_m = source_re.search(line)
            if src_m and current_task_id:
                current_source = src_m.group(1)
        _verify()  # 마지막 entry


def _check_task_frontmatter_schema() -> None:
    """5) TASK-*.md 의 frontmatter 가 MEMORY_GOVERNANCE.md §2 정합 (6 keys 모두 존재)."""
    tasks_dir = LAYOUT_ROOT / "backlog" / "tasks"
    if not tasks_dir.is_dir():
        return
    fm_re = re.compile(r"^---\n(.+?)\n---", re.S)
    key_re = re.compile(r"^([a-z_]+):", re.M)
    for task_file in sorted(tasks_dir.glob("TASK-*.md")):
        try:
            text = task_file.read_text(encoding="utf-8")
        except OSError as exc:
            errors.append(f"[task-fm] {task_file.name} read fail: {exc}")
            continue
        fm_match = fm_re.match(text)
        if not fm_match:
            errors.append(f"[task-fm] {task_file.name} frontmatter 부재")
            continue
        keys = set(key_re.findall(fm_match.group(1)))
        missing = TASK_FRONTMATTER_KEYS - keys
        if missing:
            errors.append(f"[task-fm] {task_file.name} keys 부재: {sorted(missing)}")


def _check_session_cross_ref() -> None:
    """6) sessions/*.md 가 1개 이상 존재 (cross-ref SSOT 부재 검증)."""
    sessions_dir = LAYOUT_ROOT / "sessions"
    if not sessions_dir.is_dir():
        return
    real = [f for f in sessions_dir.glob("*.md") if f.name != ".gitkeep"]
    if not real:
        errors.append(f"[sessions] sessions/ 가 비어 있음 (cross-ref SSOT 부재)")


def main() -> int:
    _check_layout_existence()
    _check_legacy_absent()
    _check_state_json_source_of_truth()
    _check_daily_index_links_resolve()
    _check_task_frontmatter_schema()
    _check_session_cross_ref()

    if errors:
        for e in errors:
            print(f"[FAIL] {e}")
        print(f"\n=== FAIL: {len(errors)} violation(s) ===")
        return 1

    n_backlog = len(list((LAYOUT_ROOT / "backlog").glob("[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9].md")))
    n_tasks = len(list((LAYOUT_ROOT / "backlog" / "tasks").glob("TASK-*.md")))
    n_sessions = len([f for f in (LAYOUT_ROOT / "sessions").glob("*.md") if f.name != ".gitkeep"])

    print("=== PASS: 6/6 ===")
    print(f"  1) layout existence: backlog/{n_backlog}d, backlog/tasks/{n_tasks}, sessions/{n_sessions}")
    print(f"  2) legacy absent: work_backlog.md 부재 (.bak fallback 보존)")
    print(f"  3) state.json source_of_truth: daily_backlog_dir / tasks_dir / sessions_dir 모두 dir path")
    print(f"  4) daily index links: TASK-* link 모두 tasks/ file 로 resolve")
    print(f"  5) task frontmatter: id/status/created_at/source_anchor/source_path/kind 모두 존재")
    print(f"  6) sessions cross-ref: per-session file {n_sessions}개")

    # v0.14.1: 1st deprecation cycle 종결 warning
    if warnings:
        print()
        print(f"=== WARNINGS ({len(warnings)}): ===")
        for w in warnings:
            print(f"[WARN] {w}")
        print()
        print("(warnings 는 errors 가 아니므로 PASS 유지. v0.14.5 부터는 --legacy-memory flag 필요, v0.15.0 drop.)")

    return 0


def test_case_1() -> None:
    assert main() == 0, "case_1 smoke FAIL"


def test_case_2() -> None:
    assert main() == 0, "case_2 smoke FAIL"


def test_case_3() -> None:
    assert main() == 0, "case_3 smoke FAIL"


def test_case_4() -> None:
    assert main() == 0, "case_4 smoke FAIL"


def test_case_5() -> None:
    assert main() == 0, "case_5 smoke FAIL"



if __name__ == "__main__":
    raise SystemExit(main())