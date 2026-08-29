#!/usr/bin/env python3
"""`roadmap_state.json` 이 생성물이라는 계약의 검사 (M-002, 스펙 §7.1).

`check_state_json_generated` 와 같은 부류다: SSOT(roadmap/ + task frontmatter)에서
재생성한 결과와 저장본을 대조해 손편집·미재생성을 잡는다. `generated_at` 은
대조에서 제외한다 — 매일 바뀌는 값을 물면 그 검사는 내일 red 다 (56차 규칙).

저장소 전역 상태(여러 파일의 조합)를 관찰하므로 정숙 구간에서 돈다.
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
import sys
import tempfile
from pathlib import Path

REQUIRES_QUIET_REPO = True

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from workflow_kit.common.state.roadmap import (  # noqa: E402
    generate_roadmap_state,
    state_matches_regeneration,
    state_path,
)

FAILURES: list[str] = []


def _record(case: str, ok: bool, detail: str = "") -> None:
    if ok:
        print(f"PASS: {case}")
    else:
        print(f"FAIL: {case}{(' — ' + detail) if detail else ''}")
        FAILURES.append(case)


INDEX_TEXT = """# Roadmap — fixture

## Milestones

- **M-001** [concept] 컨셉 — status: in_progress
  - path: [`./M-001-concept.md`](./M-001-concept.md)
"""

M1_TEXT = """---
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

- **WBS-1.1** 컨셉 노트
"""


def _fixture(root: Path) -> Path:
    roadmap = root / "ai-workflow" / "memory" / "active" / "roadmap"
    roadmap.mkdir(parents=True)
    (roadmap / "index.md").write_text(INDEX_TEXT, encoding="utf-8")
    (roadmap / "M-001-concept.md").write_text(M1_TEXT, encoding="utf-8")
    return root


def test_repo_state_matches_regeneration() -> None:
    """이 저장소의 저장본 = 재생성 결과 (generated_at 제외). 어긋나면 미재생성이거나 손편집이다."""
    ok, reason = state_matches_regeneration(REPO_ROOT)
    _record("test_repo_state_matches_regeneration", ok, reason)


def test_hand_edit_detected() -> None:
    """되주입: 저장본의 파생 값을 손으로 바꾸면 red."""
    with tempfile.TemporaryDirectory() as tmp:
        root = _fixture(Path(tmp))
        generate_roadmap_state(root)
        saved = state_path(root)
        raw = json.loads(saved.read_text(encoding="utf-8"))
        raw["milestones"][0]["progress"] = 1.0
        saved.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")
        ok, reason = state_matches_regeneration(root)
        detected = not ok and "다르다" in reason
    _record("test_hand_edit_detected", detected, reason)


def test_generated_at_is_excluded_from_comparison() -> None:
    """generated_at 만 바뀐 저장본은 일치로 판정한다 — 날짜는 계약이 아니다."""
    with tempfile.TemporaryDirectory() as tmp:
        root = _fixture(Path(tmp))
        generate_roadmap_state(root)
        saved = state_path(root)
        raw = json.loads(saved.read_text(encoding="utf-8"))
        raw["generated_at"] = "1999-01-01"
        saved.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")
        ok, reason = state_matches_regeneration(root)
    _record("test_generated_at_is_excluded_from_comparison", ok, reason)


def test_absent_roadmap_is_not_applicable() -> None:
    """roadmap 부재 = 해당 없음(통과) / 부재인데 state 만 남으면 red — 잔재를 잡는다."""
    problems: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        ok, reason = state_matches_regeneration(root)
        if not ok:
            problems.append(f"부재인데 red: {reason}")
        state_file = state_path(root)
        state_file.parent.mkdir(parents=True)
        state_file.write_text("{}", encoding="utf-8")
        ok, reason = state_matches_regeneration(root)
        if ok:
            problems.append("roadmap 없이 남은 state 파일을 통과시켰다")
    _record("test_absent_roadmap_is_not_applicable", not problems, "; ".join(problems))


def test_missing_state_file_is_red() -> None:
    """roadmap 은 있는데 저장본이 없으면 red — 재생성을 잊은 상태다."""
    with tempfile.TemporaryDirectory() as tmp:
        root = _fixture(Path(tmp))
        ok, reason = state_matches_regeneration(root)
        detected = not ok and "재생성" in reason
    _record("test_missing_state_file_is_red", detected, reason)


def main() -> int:
    cases = [
        test_repo_state_matches_regeneration,
        test_hand_edit_detected,
        test_generated_at_is_excluded_from_comparison,
        test_absent_roadmap_is_not_applicable,
        test_missing_state_file_is_red,
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
