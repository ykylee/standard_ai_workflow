#!/usr/bin/env python3
"""Smoke test — v0.14.0+ append-only memory layout 무결성 검증 (7 cases).

본 smoke 는 다음 layout 의 SSOT 무결성을 검증:
  ai-workflow/memory/active/
    state.json (read-only snapshot, builder 가 rebuild)
    backlog/                       ← per-day index (append-only)
      YYYY-MM-DD.md
      tasks/
        TASK-<date>-<NNN>.md       ← per-task SSOT
    sessions/                      ← per-session file

7 cases:
  1) layout existence: backlog/, backlog/tasks/, sessions/ 모두 존재 + 비어있지 않음
  2) legacy absent: active/work_backlog.md 부재 (.bak fallback 은 OK)
  3) state.json source_of_truth: daily_backlog_dir / tasks_dir / sessions_dir 모두 dir path
  4) daily index links: TASK-* link 가 모두 backlog/tasks/TASK-*.md 로 resolve
  5) task frontmatter: MEMORY_GOVERNANCE.md §2 정합 (6 keys 모두 존재)
  6) sessions cross-ref: sessions/*.md 1+ 파일 존재
  7) task ID 유일성: 한 브랜치 backlog 안에서 같은 TASK ID 가 두 번 등록되지 않음

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
sys.path.insert(0, str(REPO_ROOT / "workflow-source"))

# task ID 패턴은 project_docs 가 단일 출처 — 여기서 따로 들고 있으면 갈라진다.
from workflow_kit.common.paths import branch_for_workspace  # noqa: E402
from workflow_kit.common.project_docs import TASK_ID_PATTERN, TASK_STATUSES  # noqa: E402

ACTIVE_DIR = REPO_ROOT / "ai-workflow" / "memory" / "active"


def _resolve_layout_root() -> Path:
    """v1.0.0 branch-scoped: layout 검증의 기준 디렉터리를 찾는다.

    메모리는 `active/<branch>/` 로 분리되므로 layout 은 그 하위에 있다. 아직
    마이그레이션하지 않은 저장소(`active/backlog` 가 직접 존재)는 legacy 로 취급한다.

    **현재 브랜치를 먼저 겨눈다.** 브랜치 디렉터리가 둘 이상이면 (작업 브랜치가
    자기 것을 갖는 정상 상태) 아래 scan 은 알파벳 첫 번째를 잡는다 — 검증 대상이
    브랜치 이름에 따라 조용히 바뀐다. 이름 순서가 답을 바꾸면 안 된다.
    """
    if (ACTIVE_DIR / "backlog").is_dir():
        return ACTIVE_DIR
    current = ACTIVE_DIR / branch_for_workspace(REPO_ROOT)
    if (current / "backlog").is_dir():
        return current
    for cand in sorted(ACTIVE_DIR.rglob("*")):
        if cand.is_dir() and (cand / "backlog").is_dir():
            return cand
    return ACTIVE_DIR


LAYOUT_ROOT = _resolve_layout_root()

# MEMORY_GOVERNANCE.md §2 Task Detail 템플릿 정합 — TASK-*.md frontmatter 필수 keys
TASK_FRONTMATTER_KEYS = frozenset({
    "id", "created_at", "source_anchor", "source_path", "kind",
})

# `status` 는 **진행 상태 축**이라 판정 근거가 있을 때만 쓴다 (v1.0.3 §2.39). 근거가 없어
# 비운 task 는 대신 **출처 축**(`provenance`)을 밝혀야 한다 — 둘 다 없으면 그 파일이 왜
# 판정을 못 했는지 아무 데도 안 남는다. `status` 를 무조건 요구하면 도구가 근거 없이
# 채우게 되고, 그게 `status: recorded` → daily fallback → "완료로 날조" 의 출발점이었다.
TASK_JUDGMENT_KEYS = ("status", "provenance")

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
    link_re = re.compile(rf"\*\*({TASK_ID_PATTERN})\*\*\s*\[([^\]]+)\]")
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
                            f"[daily-index] {daily_file.name} → {current_task_id} "
                            f"session 매핑 부재: {session_path}"
                        )
                else:
                    errors.append(
                        f"[daily-index] {daily_file.name} → {current_task_id} "
                        f"session kind 인데 source path 부재"
                    )
            else:
                # release / generic → tasks/TASK-<id>.md
                task_path = tasks_dir / f"{current_task_id}.md"
                if not task_path.exists():
                    errors.append(
                        f"[daily-index] {daily_file.name} → {current_task_id} 부재: {task_path}"
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
        frontmatter = fm_match.group(1)
        keys = set(key_re.findall(frontmatter))
        missing = TASK_FRONTMATTER_KEYS - keys
        if missing:
            errors.append(f"[task-fm] {task_file.name} keys 부재: {sorted(missing)}")
        if not keys.intersection(TASK_JUDGMENT_KEYS):
            errors.append(
                f"[task-fm] {task_file.name} 에 `status` 도 `provenance` 도 없다 — "
                f"판정하지 않았다면 출처를 밝힐 것"
            )
        status_match = re.search(r"^status:\s*(\S+)\s*$", frontmatter, re.M)
        if status_match is not None and status_match.group(1) not in TASK_STATUSES:
            errors.append(
                f"[task-fm] {task_file.name} status `{status_match.group(1)}` 는 표준 어휘 밖 "
                f"({'/'.join(TASK_STATUSES)}) — 출처는 `provenance` 로 적을 것"
            )


def _check_session_cross_ref() -> None:
    """6) sessions/*.md 가 1개 이상 존재 (cross-ref SSOT 부재 검증)."""
    sessions_dir = LAYOUT_ROOT / "sessions"
    if not sessions_dir.is_dir():
        return
    real = [f for f in sessions_dir.glob("*.md") if f.name != ".gitkeep"]
    if not real:
        errors.append(f"[sessions] sessions/ 가 비어 있음 (cross-ref SSOT 부재)")


def _check_task_id_unique() -> None:
    """7) 한 브랜치의 backlog 안에서 task ID 가 유일한가.

    ID 는 브랜치별로 매겨지는데(`branch-scoped-memory`), 같은 브랜치를 목적지로
    두 세션이 **각자** 다음 번호를 발급하면 같은 ID 두 개가 태어난다. 2026-08-13 에
    실제로 그랬다: `main` 과 `feat/plugin-harness-distribution` 이 같은 날 각각
    `TASK-2026-08-13-main-008` 을 만들었다.

    이 결함이 위험한 이유는 **조용해서**다. 병합할 때 daily index 는 서로 다른
    줄이라 conflict 없이 auto-merge 되어 같은 ID bullet 두 개가 남고, task 파일만
    add/add conflict 를 낸다. 한쪽으로 해소하면 남은 bullet 이 *다른 작업을 설명하는
    파일*을 가리키고, 사라진 쪽 기록은 아무 데도 남지 않는다. 실측으로 확인했다 —
    이 case 가 생기기 전 backlog 검사 4종도 `generate_workflow_state.py` 도
    중복을 하나도 검출하지 못했고, 생성된 state.json 은 한쪽만 담은 채 `ok` 였다.

    **정상적인 재등장과 구분해야 한다.** index 는 append-only 라, 하루를 넘긴 task 는
    다음 날 index 에 *같은 제목으로* 다시 실려 상태만 갱신된다 (실제 예:
    `TASK-2026-08-12-main-016` 이 08-12 `planned` → 08-13 `done`). 그건 충돌이 아니다.
    충돌의 표지는 둘 중 하나다:

    - 같은 ID 가 **한 daily index 안에** 두 번 (한 파일 안에서 두 번 발급된 자리)
    - 같은 ID 가 **서로 다른 제목**으로 (같은 번호에 다른 작업이 붙은 자리)

    제목이 같은 재등장만 남기면 위양성이 없다 — 위양성을 내는 검사는 무시당한다.
    """
    backlog_dir = LAYOUT_ROOT / "backlog"
    if not backlog_dir.is_dir():
        return  # 1) 에서 이미 error
    bullet_re = re.compile(rf"^\s*-\s+\*\*({TASK_ID_PATTERN})\*\*\s*(.*)$")
    #: task_id → {제목: [출처 …]}
    seen: dict[str, dict[str, list[str]]] = {}
    for daily_file in sorted(backlog_dir.glob("[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9].md")):
        try:
            text = daily_file.read_text(encoding="utf-8")
        except OSError as exc:
            errors.append(f"[task-id-unique] {daily_file.name} read fail: {exc}")
            continue
        per_file: dict[str, int] = {}
        for line in text.splitlines():
            m = bullet_re.match(line)
            if not m:
                continue
            task_id, title = m.group(1), m.group(2).strip()
            per_file[task_id] = per_file.get(task_id, 0) + 1
            seen.setdefault(task_id, {}).setdefault(title, []).append(daily_file.name)
        for task_id, count in sorted(per_file.items()):
            if count > 1:
                errors.append(
                    f"[task-id-unique] {task_id} 가 {daily_file.name} 안에 {count}번 등록됐다"
                )
    for task_id, by_title in sorted(seen.items()):
        if len(by_title) > 1:
            detail = " | ".join(
                f"{title!r} ({', '.join(where)})" for title, where in sorted(by_title.items())
            )
            errors.append(
                f"[task-id-unique] {task_id} 에 서로 다른 작업 {len(by_title)}개가 붙어 있다 — "
                "두 세션이 같은 번호를 각자 발급한 자리다. 나중 것을 다음 번호로 "
                "재발급할 것 (index bullet + 파일명 + frontmatter `id` + "
                f"`source_anchor` 를 함께 옮긴다). 발생: {detail}"
            )


def main() -> int:
    _check_layout_existence()
    _check_legacy_absent()
    _check_state_json_source_of_truth()
    _check_daily_index_links_resolve()
    _check_task_frontmatter_schema()
    _check_session_cross_ref()
    _check_task_id_unique()

    if errors:
        for e in errors:
            print(f"[FAIL] {e}")
        print(f"\n=== FAIL: {len(errors)} violation(s) ===")
        return 1

    n_backlog = len(list((LAYOUT_ROOT / "backlog").glob("[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9].md")))
    n_tasks = len(list((LAYOUT_ROOT / "backlog" / "tasks").glob("TASK-*.md")))
    n_sessions = len([f for f in (LAYOUT_ROOT / "sessions").glob("*.md") if f.name != ".gitkeep"])

    print("=== PASS: 7/7 ===")
    print(f"  1) layout existence: backlog/{n_backlog}d, backlog/tasks/{n_tasks}, sessions/{n_sessions}")
    print(f"  2) legacy absent: work_backlog.md 부재 (.bak fallback 보존)")
    print(f"  3) state.json source_of_truth: daily_backlog_dir / tasks_dir / sessions_dir 모두 dir path")
    print(f"  4) daily index links: TASK-* link 모두 tasks/ file 로 resolve")
    print(
        "  5) task frontmatter: "
        + "/".join(sorted(TASK_FRONTMATTER_KEYS))
        + " 모두 존재 + status|provenance 중 1개 + status 는 표준 어휘 안"
    )
    print(f"  6) sessions cross-ref: per-session file {n_sessions}개")
    print(f"  7) task ID 유일성: 중복 등록 0건 ({n_tasks}개 task)")

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