#!/usr/bin/env python3
"""ADR-027 M-005 — bootstrap SDLC 로드맵 씨앗 검사.

주장:
1. **씨앗이 자기 파서를 통과한다** (56차 규칙) — 렌더 결과와 실제 bootstrap
   산출물 모두 issues 0 이고, 게이트 판정까지 첫날부터 동작한다.
2. **신규는 컨셉부터**: M-001(concept)만 in_progress — 온보딩 기본 흐름이
   씨앗에 실린다.
3. **기존은 지어내지 않는다**: 전부 planned + draft 표기 — 현재 단계는
   소유자가 선언한다.
4. **재실행이 사용자 로드맵을 덮지 않는다** — `memory/active` 는 보존 경로다.
5. 씨앗 직후 위양성 0 (파생 불일치는 done 경계에서만 — 스펙 §7.2).
"""
from __future__ import annotations

#: 이 검사의 입력 표면 (spec `core/test_impact_tiering_spec.md` §2).
#: 게이트 채취 실측에서 뽑아 넓은 쪽으로 올렸다 — 좁으면 meta-watch 가 red 로 잡는다.
WATCHES = (
    "workflow-source/pyproject.toml",
    "workflow-source/workflow_kit/*",
)

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from workflow_kit.bootstrap_lib.roadmap_seed import render_roadmap_seed  # noqa: E402
from workflow_kit.common.state.roadmap import (  # noqa: E402
    build_roadmap_state,
    evaluate_wbs_gate,
)

FAILURES: list[str] = []


def _record(case: str, ok: bool, detail: str = "") -> None:
    if ok:
        print(f"PASS: {case}")
    else:
        print(f"FAIL: {case}{(' — ' + detail) if detail else ''}")
        FAILURES.append(case)


def _seed_args() -> argparse.Namespace:
    return argparse.Namespace(kit_dir="ai-workflow", project_name="Seed Fixture", today="2026-01-01")


def _write_seed(root: Path, *, draft: bool) -> None:
    roadmap = root / "ai-workflow" / "memory" / "active" / "roadmap"
    roadmap.mkdir(parents=True)
    for rel, content in render_roadmap_seed(_seed_args(), draft=draft).items():
        (roadmap / rel).write_text(content, encoding="utf-8")


def _bootstrap(root: Path, mode: str) -> subprocess.CompletedProcess[str]:
    env = {**dict(os.environ), "PYTHONPATH": str(SOURCE_ROOT)}
    return subprocess.run(
        [sys.executable, "-m", "workflow_kit.bootstrap_lib",
         "--target-root", str(root), "--project-slug", "seedfx",
         "--project-name", "Seed Fixture", "--adoption-mode", mode,
         "--harness", "claude-code", "--no-interactive"],
        capture_output=True, text=True, timeout=180, env=env, cwd=str(root),
    )


def test_new_seed_parses_and_gates_from_day_one() -> None:
    """렌더 씨앗: issues 0 · concept 만 in_progress · 게이트 3판정 동작."""
    problems: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp).resolve()
        _write_seed(root, draft=False)
        state = build_roadmap_state(root)
        if state is None or state.issues:
            problems.append(f"파싱 실패 또는 issues: {[i.code for i in (state.issues if state else [])]}")
        elif state.current_milestone_id != "M-001":
            problems.append(f"current ≠ M-001: {state.current_milestone_id}")
        else:
            open_ms = [m.id for m in state.milestones if m.declared_status.value == "in_progress"]
            if open_ms != ["M-001"]:
                problems.append(f"concept 외가 열려 있다: {open_ms}")
        for wbs, expect in ((None, "wbs_required"), ("M-001/WBS-1.1", "linked"), ("M-003/WBS-3.1", "sdlc_order")):
            verdict = evaluate_wbs_gate(root, wbs=wbs)
            if verdict.code != expect:
                problems.append(f"게이트 {wbs!r}: 기대 {expect}, 실제 {verdict.code}")
    _record("test_new_seed_parses_and_gates_from_day_one", not problems, "; ".join(problems))


def test_existing_seed_declares_nothing() -> None:
    """draft 씨앗: 전부 planned, current 없음, index 에 draft 표기."""
    problems: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp).resolve()
        _write_seed(root, draft=True)
        state = build_roadmap_state(root)
        if state is None or state.issues:
            problems.append(f"파싱 실패 또는 issues: {[i.code for i in (state.issues if state else [])]}")
        else:
            if state.current_milestone_id is not None:
                problems.append(f"기존 모드가 현재 단계를 지어냈다: {state.current_milestone_id}")
            if any(m.declared_status.value != "planned" for m in state.milestones):
                problems.append("planned 아닌 마일스톤이 있다")
        index_text = (root / "ai-workflow" / "memory" / "active" / "roadmap" / "index.md").read_text(encoding="utf-8")
        if "draft" not in index_text or "소유자" not in index_text:
            problems.append("draft/소유자 선언 표기가 없다")
        # draft 초안은 게이트를 발동시키지 않는다 (스펙 §6) — 추정이 강제가 되면
        # draft 가 draft 가 아니다.
        verdict = evaluate_wbs_gate(root, wbs=None)
        if not verdict.allowed or verdict.code != "draft_roadmap":
            problems.append(f"draft 씨앗이 게이트를 발동시켰다: {verdict.code}")
    _record("test_existing_seed_declares_nothing", not problems, "; ".join(problems))


def test_bootstrap_emits_seed_and_state() -> None:
    """실제 bootstrap(신규): roadmap 씨앗 + roadmap_state.json 이 나온다."""
    problems: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp).resolve()
        proc = _bootstrap(root, "new")
        if proc.returncode != 0:
            problems.append(f"bootstrap rc={proc.returncode}: {(proc.stderr or proc.stdout)[-300:]}")
        else:
            roadmap = root / "ai-workflow" / "memory" / "active" / "roadmap"
            expected = {"index.md", "M-001-concept.md", "M-002-requirements.md",
                        "M-003-design.md", "M-004-implementation.md", "roadmap_state.json"}
            actual = {p.name for p in roadmap.glob("*")} if roadmap.is_dir() else set()
            if not expected <= actual:
                problems.append(f"산출물 부족: {sorted(expected - actual)}")
            state = build_roadmap_state(root)
            if state is None or state.issues:
                problems.append(f"bootstrap 씨앗 issues: {[i.code for i in (state.issues if state else [])]}")
    _record("test_bootstrap_emits_seed_and_state", not problems, "; ".join(problems))


def test_rerun_preserves_user_roadmap() -> None:
    """재실행이 사용자 수정 로드맵을 덮지 않는다 — memory/active 는 보존 경로다."""
    problems: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp).resolve()
        proc = _bootstrap(root, "new")
        if proc.returncode != 0:
            problems.append(f"1차 bootstrap rc={proc.returncode}")
        index = root / "ai-workflow" / "memory" / "active" / "roadmap" / "index.md"
        user_edit = index.read_text(encoding="utf-8") + "\n<!-- 사용자 수정 -->\n"
        index.write_text(user_edit, encoding="utf-8")
        proc = _bootstrap(root, "new")
        if proc.returncode != 0:
            problems.append(f"2차 bootstrap rc={proc.returncode}")
        if index.read_text(encoding="utf-8") != user_edit:
            problems.append("재실행이 사용자 수정을 덮었다")
    _record("test_rerun_preserves_user_roadmap", not problems, "; ".join(problems))


def test_fresh_seed_has_no_false_mismatch() -> None:
    """되주입 양방향: 씨앗 직후 declared_derived_mismatch 0 (in_progress+링크0 은
    정상 시작 상태) — 반대로 done 경계 불일치는 여전히 잡힌다."""
    problems: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp).resolve()
        _write_seed(root, draft=False)
        state = build_roadmap_state(root)
        codes = [i.code for i in state.issues] if state else ["<none>"]
        if "declared_derived_mismatch" in codes:
            problems.append(f"씨앗 직후 위양성: {codes}")
        m1 = root / "ai-workflow" / "memory" / "active" / "roadmap" / "M-001-concept.md"
        m1.write_text(m1.read_text(encoding="utf-8").replace("status: in_progress", "status: done", 1), encoding="utf-8")
        index = root / "ai-workflow" / "memory" / "active" / "roadmap" / "index.md"
        index.write_text(index.read_text(encoding="utf-8").replace("컨셉 정리 — status: in_progress", "컨셉 정리 — status: done", 1), encoding="utf-8")
        state = build_roadmap_state(root)
        codes = [i.code for i in state.issues] if state else []
        if "declared_derived_mismatch" not in codes:
            problems.append(f"done 경계 불일치 미검출: {codes}")
    _record("test_fresh_seed_has_no_false_mismatch", not problems, "; ".join(problems))


def main() -> int:
    cases = [
        test_new_seed_parses_and_gates_from_day_one,
        test_existing_seed_declares_nothing,
        test_bootstrap_emits_seed_and_state,
        test_rerun_preserves_user_roadmap,
        test_fresh_seed_has_no_false_mismatch,
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
