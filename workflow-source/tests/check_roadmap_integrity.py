#!/usr/bin/env python3
"""ADR-027 roadmap ↔ task 참조 무결성 + 파생 계약 검사 (M-002).

주장:
1. **이 저장소의 roadmap 은 무결하다** — dangling 0, 선언·파생 불일치 0.
2. **파생은 스펙 §7.2 그대로다**: 분모는 선언한 leaf 수(링크를 지우면 진척이
   내려가지 떠오르지 않는다), done 판정은 WBS 완료 + deliverable 실재 둘 다.
3. **불일치는 자동 수정이 아니라 보고다** — declared_derived_mismatch ·
   done_milestone_open_task · deliverable_missing · exempt_without_reason 이
   되주입에서 red 로 잡힌다.
"""
from __future__ import annotations

#: 이 검사의 입력 표면 (spec `core/test_impact_tiering_spec.md` §2).
#: 게이트 채취 실측에서 뽑아 넓은 쪽으로 올렸다 — 좁으면 meta-watch 가 red 로 잡는다.
WATCHES = (
    "ai-workflow/memory/active/*",
    "workflow-source/pyproject.toml",
    "workflow-source/workflow_kit/*",
)

import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from workflow_kit.common.state.roadmap import build_roadmap_state  # noqa: E402

FAILURES: list[str] = []


def _record(case: str, ok: bool, detail: str = "") -> None:
    if ok:
        print(f"PASS: {case}")
    else:
        print(f"FAIL: {case}{(' — ' + detail) if detail else ''}")
        FAILURES.append(case)


INDEX_TEXT = """# Roadmap — fixture

## Milestones

- **M-001** [concept] 컨셉 — status: {m1_status}
  - path: [`./M-001-concept.md`](./M-001-concept.md)
"""

M1_TEXT = """---
id: M-001
title: 컨셉
sdlc_phase: concept
status: {m1_status}
order: 1
parallel_allowed: []
deliverables:
{deliverables}---

# M-001

## WBS

- **WBS-1.1** 컨셉 노트
- **WBS-1.2** 리뷰
"""

TASK_TEXT = """---
id: {task_id}
status: {status}
created_at: 2026-08-25
kind: generic
{extra}---

# {task_id} — fixture task
"""


def _fixture(root: Path, *, m1_status: str = "in_progress", deliverables: str = "  - README.md\n",
             tasks: list[tuple[str, str, str]] | None = None) -> Path:
    """tasks: (task_id, status, extra frontmatter lines)."""
    roadmap = root / "ai-workflow" / "memory" / "active" / "roadmap"
    roadmap.mkdir(parents=True)
    (roadmap / "index.md").write_text(INDEX_TEXT.format(m1_status=m1_status), encoding="utf-8")
    (roadmap / "M-001-concept.md").write_text(
        M1_TEXT.format(m1_status=m1_status, deliverables=deliverables), encoding="utf-8")
    (root / "README.md").write_text("fixture\n", encoding="utf-8")
    tasks_dir = root / "ai-workflow" / "memory" / "active" / "main" / "backlog" / "tasks"
    tasks_dir.mkdir(parents=True)
    for task_id, status, extra in (tasks or []):
        (tasks_dir / f"{task_id}.md").write_text(
            TASK_TEXT.format(task_id=task_id, status=status, extra=extra), encoding="utf-8")
    return root


def test_repo_roadmap_is_clean() -> None:
    """이 저장소: issue 0 — 무결성 결함을 안고 push 하지 않는다."""
    state = build_roadmap_state(REPO_ROOT)
    problems: list[str] = []
    if state is None:
        problems.append("저장소 roadmap 부재")
    elif state.issues:
        problems.append(f"issues: {[(i.code, i.detail) for i in state.issues]}")
    _record("test_repo_roadmap_is_clean", not problems, "; ".join(problems))


NESTED_M1_TEXT = """---
id: M-001
title: 컨셉
sdlc_phase: concept
status: in_progress
order: 1
parallel_allowed: []
deliverables: []
---

# M-001

## WBS

- **WBS-1.1** 부모
  - **WBS-1.1.1** 자식
- **WBS-1.2** 리뷰
"""


def test_dangling_and_non_leaf_links_detected() -> None:
    """되주입 3종: 없는 참조 → dangling, 중간 노드 참조 → not_leaf, 형식 위반 → ref_format."""
    problems: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        root = _fixture(Path(tmp), tasks=[
            ("TASK-2026-08-25-main-001", "in_progress", "wbs: M-001/WBS-1.9\n"),
            ("TASK-2026-08-25-main-002", "in_progress", "wbs: banana\n"),
            ("TASK-2026-08-25-main-003", "in_progress", "wbs: M-001/WBS-1.1\n"),
        ])
        (root / "ai-workflow" / "memory" / "active" / "roadmap" / "M-001-concept.md").write_text(
            NESTED_M1_TEXT, encoding="utf-8")
        state = build_roadmap_state(root)
        codes = [i.code for i in state.issues] if state else []
        if "wbs_dangling_link" not in codes:
            problems.append(f"dangling 미검출: {codes}")
        if "wbs_ref_format" not in codes:
            problems.append(f"형식 위반 참조 미검출: {codes}")
        if "wbs_link_not_leaf" not in codes:
            problems.append(f"중간 노드 참조 미검출: {codes}")
    _record("test_dangling_and_non_leaf_links_detected", not problems, "; ".join(problems))


def test_denominator_is_declared_leaves() -> None:
    """분모는 선언 leaf 수다 — 링크가 0 이어도 leaf 2개가 분모에 남는다 (50차 규칙)."""
    problems: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        root = _fixture(Path(tmp), tasks=[
            ("TASK-2026-08-25-main-001", "done", "wbs: M-001/WBS-1.1\n"),
        ])
        state = build_roadmap_state(root)
        m1 = state.milestones[0] if state and state.milestones else None
        if m1 is None:
            problems.append("파생 실패")
        else:
            if m1.total_leaves != 2 or m1.done_leaves != 1:
                problems.append(f"분모/분자 어긋남: {m1.done_leaves}/{m1.total_leaves} (기대 1/2)")
            if abs(m1.progress - 0.5) > 1e-9:
                problems.append(f"progress {m1.progress} ≠ 0.5")
    with tempfile.TemporaryDirectory() as tmp:
        root = _fixture(Path(tmp))  # 링크 0
        state = build_roadmap_state(root)
        m1 = state.milestones[0] if state and state.milestones else None
        if m1 is not None and (m1.total_leaves != 2 or m1.progress != 0.0):
            problems.append(f"링크 0 인데 분모가 줄었다: {m1.done_leaves}/{m1.total_leaves}")
    _record("test_denominator_is_declared_leaves", not problems, "; ".join(problems))


def test_done_needs_wbs_and_deliverables_both() -> None:
    """done 은 WBS 완료 + deliverable 실재 **둘 다**다 — 산출물이 없으면 100% 여도 done 이 아니다."""
    problems: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        root = _fixture(Path(tmp), m1_status="done", deliverables="  - missing/file.md\n", tasks=[
            ("TASK-2026-08-25-main-001", "done", "wbs: M-001/WBS-1.1\n"),
            ("TASK-2026-08-25-main-002", "done", "wbs: M-001/WBS-1.2\n"),
        ])
        state = build_roadmap_state(root)
        codes = [i.code for i in state.issues] if state else []
        m1 = state.milestones[0] if state and state.milestones else None
        if m1 is None:
            problems.append("파생 실패")
        else:
            if m1.derived_status.value == "done":
                problems.append("산출물 부재인데 파생이 done 이다")
            if "deliverable_missing" not in codes:
                problems.append(f"deliverable_missing 미보고: {codes}")
            if "declared_derived_mismatch" not in codes:
                problems.append(f"선언 done ≠ 파생 의 불일치 미보고: {codes}")
    _record("test_done_needs_wbs_and_deliverables_both", not problems, "; ".join(problems))


def test_done_milestone_open_task_detected() -> None:
    """되주입: done 선언 마일스톤 아래 열린 task — 역행이 보고된다."""
    with tempfile.TemporaryDirectory() as tmp:
        root = _fixture(Path(tmp), m1_status="done", tasks=[
            ("TASK-2026-08-25-main-001", "done", "wbs: M-001/WBS-1.1\n"),
            ("TASK-2026-08-25-main-002", "in_progress", "wbs: M-001/WBS-1.2\n"),
        ])
        state = build_roadmap_state(root)
        codes = [i.code for i in state.issues] if state else []
        ok = "done_milestone_open_task" in codes
    _record("test_done_milestone_open_task_detected", ok, f"issues={codes}")


def test_exempt_is_counted_and_needs_reason() -> None:
    """게이트 우회는 침묵이 아니라 선언이다 — exempt 는 세어지고, 사유 없는 exempt 는 issue."""
    problems: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        root = _fixture(Path(tmp), tasks=[
            ("TASK-2026-08-25-main-001", "in_progress", "wbs: exempt\nwbs_exempt_reason: CI red 긴급 수리\n"),
            ("TASK-2026-08-25-main-002", "in_progress", "wbs: exempt\n"),
        ])
        state = build_roadmap_state(root)
        if state is None:
            problems.append("파생 실패")
        else:
            if len(state.exempt_tasks) != 2:
                problems.append(f"exempt 집계 {len(state.exempt_tasks)} ≠ 2")
            reasonless = [i for i in state.issues if i.code == "exempt_without_reason"]
            if len(reasonless) != 1:
                problems.append(f"사유 없는 exempt 검출 {len(reasonless)} ≠ 1")
    _record("test_exempt_is_counted_and_needs_reason", not problems, "; ".join(problems))


def main() -> int:
    cases = [
        test_repo_roadmap_is_clean,
        test_dangling_and_non_leaf_links_detected,
        test_denominator_is_declared_leaves,
        test_done_needs_wbs_and_deliverables_both,
        test_done_milestone_open_task_detected,
        test_exempt_is_counted_and_needs_reason,
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
