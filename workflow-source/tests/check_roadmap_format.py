#!/usr/bin/env python3
"""ADR-027 roadmap SSOT 형식 검사 (M-002, TASK-2026-08-25-main-003).

주장 3가지:
1. **이 저장소의 씨앗이 자기 파서를 통과한다** (56차 규칙 — 심는 것이 읽히는지
   확인하지 않으면 소비자는 첫날부터 파싱 안 되는 상태를 받는다).
2. **어휘는 전수 버킷이다** — sdlc_phase 6개 / status 4개(task 어휘와 동일).
   어휘 밖 값은 조용히 기본값으로 뭉개지지 않고 issue 가 된다.
3. **형식 위반(순서 불일치 · WBS id 중복 · 마일스톤 번호 불일치 · index 참조
   깨짐)은 되주입하면 red 다** — 도달 불가능한 분기는 검사되지 않은 분기다.
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from workflow_kit.common.project_docs import TASK_STATUSES  # noqa: E402
from workflow_kit.common.schemas.roadmap import RoadmapItemStatus, SdlcPhase  # noqa: E402
from workflow_kit.common.state.roadmap import load_roadmap, parse_milestone_text  # noqa: E402

FAILURES: list[str] = []


def _record(case: str, ok: bool, detail: str = "") -> None:
    if ok:
        print(f"PASS: {case}")
    else:
        print(f"FAIL: {case}{(' — ' + detail) if detail else ''}")
        FAILURES.append(case)


INDEX_TEXT = """# Roadmap — fixture

## Milestones

- **M-001** [concept] 컨셉 — status: done
  - path: [`./M-001-concept.md`](./M-001-concept.md)
- **M-002** [design] 설계 — status: in_progress
  - path: [`./M-002-design.md`](./M-002-design.md)
"""

M1_TEXT = """---
id: M-001
title: 컨셉
sdlc_phase: concept
status: done
order: 1
parallel_allowed: []
deliverables: []
---

# M-001

## WBS

- **WBS-1.1** 컨셉 노트
"""

M2_TEXT = """---
id: M-002
title: 설계
sdlc_phase: design
status: in_progress
order: 2
parallel_allowed: []
deliverables: []
---

# M-002

## WBS

- **WBS-2.1** 설계 문서
  - **WBS-2.1.1** ADR
- **WBS-2.2** 리뷰
"""


def _write_fixture(root: Path, index: str = INDEX_TEXT, m1: str = M1_TEXT, m2: str = M2_TEXT) -> Path:
    roadmap = root / "ai-workflow" / "memory" / "active" / "roadmap"
    roadmap.mkdir(parents=True)
    (roadmap / "index.md").write_text(index, encoding="utf-8")
    (roadmap / "M-001-concept.md").write_text(m1, encoding="utf-8")
    (roadmap / "M-002-design.md").write_text(m2, encoding="utf-8")
    return root


def test_repo_seed_parses_clean() -> None:
    """이 저장소의 roadmap/ 이 자기 파서를 통과한다 — format issue 0."""
    roadmap, issues = load_roadmap(REPO_ROOT)
    problems: list[str] = []
    if roadmap is None:
        problems.append("저장소 roadmap/ 을 읽지 못했다 (index.md 부재?)")
    else:
        if issues:
            problems.append(f"format issues: {[(i.code, i.detail) for i in issues]}")
        if len(roadmap.milestones) < 2:
            problems.append(f"마일스톤이 {len(roadmap.milestones)}개뿐이다 — 씨앗은 M-001~M-006 을 선언한다")
        if not any(m.wbs for m in roadmap.milestones):
            problems.append("WBS 를 하나도 파싱하지 못했다")
    _record("test_repo_seed_parses_clean", not problems, "; ".join(problems))


def test_vocabulary_is_exhaustive_and_pinned() -> None:
    """어휘 계약: sdlc 6개 전수, status 는 task 어휘(project_docs)와 동일 집합.

    개수가 아니라 **집합**을 대조한다 — 이름이 어긋난 채 통과하는 것을 막는다.
    """
    problems: list[str] = []
    expected_phases = {"concept", "requirements", "design", "implementation", "stabilization", "release"}
    actual_phases = {p.value for p in SdlcPhase}
    if actual_phases != expected_phases:
        problems.append(f"sdlc_phase 집합 어긋남: {sorted(actual_phases ^ expected_phases)}")
    if {s.value for s in RoadmapItemStatus} != set(TASK_STATUSES):
        problems.append(f"status 어휘가 task 어휘와 갈린다: {sorted({s.value for s in RoadmapItemStatus} ^ set(TASK_STATUSES))}")
    _record("test_vocabulary_is_exhaustive_and_pinned", not problems, "; ".join(problems))


def test_vocab_outside_becomes_issue_not_default() -> None:
    """되주입: 어휘 밖 sdlc_phase 는 issue 다 — 조용한 기본값 금지."""
    bad = M1_TEXT.replace("sdlc_phase: concept", "sdlc_phase: banana")
    milestone, issues = parse_milestone_text(bad, "M-001-concept.md")
    ok = milestone is None and any(i.code == "milestone_parse_error" for i in issues)
    _record("test_vocab_outside_becomes_issue_not_default", ok, f"milestone={milestone!r} issues={[i.code for i in issues]}")


def test_order_mismatch_detected() -> None:
    """되주입: index 위치와 frontmatter order 가 갈리면 red."""
    with tempfile.TemporaryDirectory() as tmp:
        root = _write_fixture(Path(tmp), m2=M2_TEXT.replace("order: 2", "order: 5"))
        _, issues = load_roadmap(root)
        ok = any(i.code == "order_mismatch" for i in issues)
    _record("test_order_mismatch_detected", ok, f"issues={[i.code for i in issues]}")


def test_index_status_mismatch_detected() -> None:
    """되주입: index status 와 frontmatter status 가 갈리면 red — 두 선언 자리를 대조한다."""
    with tempfile.TemporaryDirectory() as tmp:
        root = _write_fixture(Path(tmp), m1=M1_TEXT.replace("status: done", "status: in_progress"))
        _, issues = load_roadmap(root)
        ok = any(i.code == "index_status_mismatch" for i in issues)
    _record("test_index_status_mismatch_detected", ok, f"issues={[i.code for i in issues]}")


def test_duplicate_wbs_id_detected() -> None:
    """되주입: WBS id 중복."""
    dup = M2_TEXT.replace("**WBS-2.2**", "**WBS-2.1**")
    _, issues = parse_milestone_text(dup, "M-002-design.md")
    ok = any(i.code == "duplicate_wbs_id" for i in issues)
    _record("test_duplicate_wbs_id_detected", ok, f"issues={[i.code for i in issues]}")


def test_wbs_milestone_number_mismatch_detected() -> None:
    """되주입: M-001 파일 안의 WBS-9.x 는 red — 첫 세그먼트가 마일스톤 번호다."""
    bad = M1_TEXT.replace("**WBS-1.1**", "**WBS-9.1**")
    _, issues = parse_milestone_text(bad, "M-001-concept.md")
    ok = any(i.code == "wbs_milestone_number_mismatch" for i in issues)
    _record("test_wbs_milestone_number_mismatch_detected", ok, f"issues={[i.code for i in issues]}")


def test_index_reference_breakage_detected() -> None:
    """되주입 양방향: index 가 없는 파일을 가리키거나, 파일이 index 에 없으면 red."""
    problems: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        root = _write_fixture(Path(tmp))
        (root / "ai-workflow" / "memory" / "active" / "roadmap" / "M-002-design.md").unlink()
        _, issues = load_roadmap(root)
        if not any(i.code == "index_missing_file" for i in issues):
            problems.append(f"index_missing_file 미검출: {[i.code for i in issues]}")
    with tempfile.TemporaryDirectory() as tmp:
        index_short = "\n".join(line for line in INDEX_TEXT.splitlines() if "M-002" not in line) + "\n"
        root = _write_fixture(Path(tmp), index=index_short)
        _, issues = load_roadmap(root)
        if not any(i.code == "index_entry_missing_for_file" for i in issues):
            problems.append(f"index_entry_missing_for_file 미검출: {[i.code for i in issues]}")
    _record("test_index_reference_breakage_detected", not problems, "; ".join(problems))


def test_wbs_nesting_parses() -> None:
    """들여쓰기 2칸 = 1단계 — 중첩이 트리로 읽힌다."""
    milestone, issues = parse_milestone_text(M2_TEXT, "M-002-design.md")
    problems: list[str] = []
    if milestone is None or issues:
        problems.append(f"파싱 실패: {[i.code for i in issues]}")
    else:
        roots = [n.id for n in milestone.wbs]
        if roots != ["WBS-2.1", "WBS-2.2"]:
            problems.append(f"루트 노드 어긋남: {roots}")
        elif [c.id for c in milestone.wbs[0].children] != ["WBS-2.1.1"]:
            problems.append(f"중첩 어긋남: {[c.id for c in milestone.wbs[0].children]}")
    _record("test_wbs_nesting_parses", not problems, "; ".join(problems))


def main() -> int:
    cases = [
        test_repo_seed_parses_clean,
        test_vocabulary_is_exhaustive_and_pinned,
        test_vocab_outside_becomes_issue_not_default,
        test_order_mismatch_detected,
        test_index_status_mismatch_detected,
        test_duplicate_wbs_id_detected,
        test_wbs_milestone_number_mismatch_detected,
        test_index_reference_breakage_detected,
        test_wbs_nesting_parses,
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
