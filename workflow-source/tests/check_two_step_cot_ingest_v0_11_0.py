"""Acceptance test for v0.11.0 two-step CoT ingest (R-A follow-up cycle 3).

6 acceptance test:
1. test_extract_raw_purpose_v0_11_0 — extract_raw_purpose SSOT (frontmatter + 4 sections + 5 case)
2. test_build_structured_purpose_v0_11_0 — build_structured_purpose 4-element parse
3. test_emit_cot_trace_v0_11_0 — CoT trace 의 2-step 본문 ≤800 char
4. test_cross_reference_validate_v0_11_0 — [[mention]] ↔ wiki concepts 매칭
5. test_run_two_step_cot_ingest_graceful_v0_11_0 — unified entry 의 graceful skip
6. test_ingest_purpose_cli_registered_v0_11_0 — CLI subcommand 등록 + dry-run verify
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
WORKSPACE_ROOT = REPO_ROOT


def _ensure_sys_path() -> None:
    """workflow_kit 모듈 import 가능하도록 sys.path 보강."""
    if str(SOURCE_ROOT) not in sys.path:
        sys.path.insert(0, str(SOURCE_ROOT))


_ensure_sys_path()


# ---------------------------------------------------------------------------
# Acceptance test 1: extract_raw_purpose SSOT
# ---------------------------------------------------------------------------


def test_extract_raw_purpose_v0_11_0() -> None:
    """extract_raw_purpose SSOT 검증 — 5 case."""
    from workflow_kit.common.purpose_ingest import (
        extract_raw_purpose,
        RawPurposeExtract,
    )

    # case 1: 정상 PURPOSE.md (frontmatter + 4 sections)
    with tempfile.TemporaryDirectory() as tmpdir:
        ws = Path(tmpdir)
        purpose_path = ws / "PURPOSE.md"
        purpose_path.write_text(
            "---\npurpose_version: 1\nlast_purpose_review: 2026-06-26\n---\n\n"
            "# Title\n\n## 1. Goals\n\n- **G1**: foo\n- **G2**: bar\n\n"
            "## 2. Key Questions\n\n- **Q1**: baz?\n\n"
            "## 3. Research Scope\n\n### 포함\n- x\n\n### 제외\n- y\n\n"
            "## 4. Evolving Thesis\n\nhypothesis: X\n",
            encoding="utf-8",
        )
        raw = extract_raw_purpose(purpose_path)
        assert raw.missing is False
        assert raw.purpose_version == 1
        assert raw.last_purpose_review == "2026-06-26"
        assert "G1" in raw.section_1_goals_raw
        assert "Q1" in raw.section_2_questions_raw
        assert "포함" in raw.section_3_scope_raw
        assert "hypothesis" in raw.section_4_thesis_raw
        assert raw.warnings == []
        print("  case 1 (정상): PASS")

    # case 2: PURPOSE.md 부재
    with tempfile.TemporaryDirectory() as tmpdir:
        raw = extract_raw_purpose(Path(tmpdir) / "nonexistent.md")
        assert raw.missing is True
        assert raw.warnings and "PURPOSE.md 부재" in raw.warnings[0]
        print("  case 2 (부재): PASS")

    # case 3: frontmatter 없음
    with tempfile.TemporaryDirectory() as tmpdir:
        purpose_path = Path(tmpdir) / "PURPOSE.md"
        purpose_path.write_text(
            "# Title\n\n## 1. Goals\n\n- **G1**: foo\n",
            encoding="utf-8",
        )
        raw = extract_raw_purpose(purpose_path)
        assert raw.missing is False
        assert raw.purpose_version is None
        assert raw.last_purpose_review is None
        assert any("purpose_version 부재" in w for w in raw.warnings)
        print("  case 3 (frontmatter 없음): PASS")

    # case 4: §1 empty
    with tempfile.TemporaryDirectory() as tmpdir:
        purpose_path = Path(tmpdir) / "PURPOSE.md"
        purpose_path.write_text(
            "---\npurpose_version: 1\nlast_purpose_review: 2026-06-26\n---\n\n"
            "# Title\n\n## 1. Goals\n\n(empty)\n\n## 2. Key Questions\n\n- **Q1**: ?\n\n"
            "## 3. Research Scope\n\n### 포함\n- x\n\n## 4. Evolving Thesis\n\nh: X\n",
            encoding="utf-8",
        )
        raw = extract_raw_purpose(purpose_path)
        assert raw.missing is False
        # section_1_goals_raw 는 '(empty)' 만 포함, parse 시 goals=[]
        print("  case 4 (§1 empty): PASS")

    # case 5: unicode 한국어 본문
    with tempfile.TemporaryDirectory() as tmpdir:
        purpose_path = Path(tmpdir) / "PURPOSE.md"
        purpose_path.write_text(
            "---\npurpose_version: 1\nlast_purpose_review: 2026-06-26\n---\n\n"
            "# Title\n\n## 1. Goals\n\n- **G1**: 한국어 목표 설명\n\n"
            "## 2. Key Questions\n\n- **Q1**: 핵심 질문\n\n"
            "## 3. Research Scope\n\n### 포함\n- 한글 영역\n\n## 4. Evolving Thesis\n\n가설: 한국어\n",
            encoding="utf-8",
        )
        raw = extract_raw_purpose(purpose_path)
        assert raw.missing is False
        assert "한국어" in raw.body_full
        print("  case 5 (unicode 한국어): PASS")


# ---------------------------------------------------------------------------
# Acceptance test 2: build_structured_purpose
# ---------------------------------------------------------------------------


def test_build_structured_purpose_v0_11_0() -> None:
    """build_structured_purpose 4-element parse + validation error."""
    from workflow_kit.common.purpose_ingest import (
        extract_raw_purpose,
        build_structured_purpose,
        StructuredPurposeValidationError,
    )

    # 정상 case
    with tempfile.TemporaryDirectory() as tmpdir:
        purpose_path = Path(tmpdir) / "PURPOSE.md"
        purpose_path.write_text(
            "---\npurpose_version: 1\nlast_purpose_review: 2026-06-26\n---\n\n"
            "## 1. Goals\n\n- **G1**: a\n- **G2**: b\n- **G3**: c\n\n"
            "## 2. Key Questions\n\n- **Q1**: q1?\n- **Q2**: q2?\n- **Q3**: q3?\n\n"
            "## 3. Research Scope\n\n### 포함\n- included1\n- included2\n\n### 제외\n- excluded1\n\n"
            "## 4. Evolving Thesis\n\nhypothesis: working theory\n",
            encoding="utf-8",
        )
        raw = extract_raw_purpose(purpose_path)
        sp = build_structured_purpose(raw)
        assert len(sp.goals) == 3
        assert sp.goals[0] == "G1: a"
        assert sp.goals[2] == "G3: c"
        assert len(sp.questions) == 3
        assert sp.questions[0] == "Q1: q1?"
        assert len(sp.scope_included) == 2
        assert "included1" in sp.scope_included
        assert len(sp.scope_excluded) == 1
        assert sp.scope_excluded[0] == "excluded1"
        assert "hypothesis" in sp.thesis
        print("  4-element parse (3+3+2+1): PASS")

    # validation error case (§1 Goals empty)
    with tempfile.TemporaryDirectory() as tmpdir:
        purpose_path = Path(tmpdir) / "PURPOSE.md"
        purpose_path.write_text(
            "---\npurpose_version: 1\nlast_purpose_review: 2026-06-26\n---\n\n"
            "## 1. Goals\n\n(empty)\n\n## 2. Key Questions\n\n- **Q1**: ?\n\n"
            "## 3. Research Scope\n\n### 포함\n- x\n\n## 4. Evolving Thesis\n\nh: X\n",
            encoding="utf-8",
        )
        raw = extract_raw_purpose(purpose_path)
        try:
            build_structured_purpose(raw)
            raise AssertionError("StructuredPurposeValidationError expected but not raised")
        except StructuredPurposeValidationError as e:
            assert "Goals" in str(e)
            print("  validation error (empty goals): PASS")

    # missing case
    from workflow_kit.common.purpose_ingest import RawPurposeExtract
    raw_missing = RawPurposeExtract(purpose_path=None, missing=True)
    try:
        build_structured_purpose(raw_missing)
        raise AssertionError("StructuredPurposeValidationError expected but not raised")
    except StructuredPurposeValidationError as e:
        assert "missing" in str(e)
        print("  validation error (raw missing): PASS")


# ---------------------------------------------------------------------------
# Acceptance test 3: emit_cot_trace
# ---------------------------------------------------------------------------


def test_emit_cot_trace_v0_11_0() -> None:
    """CoT trace 2-step: step1 ≤800 char, step2 4-element summary."""
    from workflow_kit.common.purpose_ingest import (
        extract_raw_purpose,
        build_structured_purpose,
        emit_cot_trace,
        COT_STEP1_MAX_CHARS,
    )

    # 정상 case
    with tempfile.TemporaryDirectory() as tmpdir:
        purpose_path = Path(tmpdir) / "PURPOSE.md"
        # 1500 char 본문 → truncated=True
        long_body = "Lorem ipsum dolor sit amet. " * 60  # ~1380 char
        purpose_path.write_text(
            "---\npurpose_version: 1\nlast_purpose_review: 2026-06-26\n---\n\n"
            "## 1. Goals\n\n- **G1**: 표준 워크플로우 제공\n\n"
            "## 2. Key Questions\n\n- **Q1**: 어떻게?\n\n"
            "## 3. Research Scope\n\n### 포함\n- 영역\n\n## 4. Evolving Thesis\n\nh: " + long_body + "\n",
            encoding="utf-8",
        )
        raw = extract_raw_purpose(purpose_path)
        sp = build_structured_purpose(raw)
        cot = emit_cot_trace(raw, sp)
        assert cot.step1_char_count <= COT_STEP1_MAX_CHARS
        assert cot.step1_truncated is True
        assert "G1=" in cot.step2_structured_summary
        assert "questions=" in cot.step2_structured_summary
        assert "scope_included=" in cot.step2_structured_summary
        print(f"  step1 ≤800 char (actual={cot.step1_char_count}, truncated={cot.step1_truncated}): PASS")
        print(f"  step2 summary: {cot.step2_structured_summary[:80]}: PASS")

    # structured unavailable case (missing)
    from workflow_kit.common.purpose_ingest import RawPurposeExtract
    raw_missing = RawPurposeExtract(purpose_path=None, missing=True, body_full="")
    cot = emit_cot_trace(raw_missing, None)
    assert "unavailable" in cot.step2_structured_summary
    print("  step2 (structured unavailable): PASS")


# ---------------------------------------------------------------------------
# Acceptance test 4: cross_reference_validate
# ---------------------------------------------------------------------------


def test_cross_reference_validate_v0_11_0() -> None:
    """PURPOSE.md `[[mention]]` ↔ wiki concepts filename 매칭."""
    from workflow_kit.common.purpose_ingest import (
        cross_reference_validate,
        StructuredPurpose,
    )

    # case 1: matched (PURPOSE.md 본문에 [[known-concept]] 있고 concepts/ 에 known-concept.md 존재)
    with tempfile.TemporaryDirectory() as tmpdir:
        ws = Path(tmpdir)
        concepts_dir = ws / "ai-workflow" / "wiki" / "concepts"
        concepts_dir.mkdir(parents=True, exist_ok=True)
        (concepts_dir / "known-concept.md").write_text("# known", encoding="utf-8")
        (concepts_dir / "another-concept.md").write_text("# another", encoding="utf-8")

        sp = StructuredPurpose(
            purpose_path=None,
            purpose_version=1,
            last_purpose_review="2026-06-26",
            goals=["G1: foo"],
            questions=["Q1: bar?"],
            scope_included=[],
            scope_excluded=[],
            thesis="See [[known-concept]] and [[another-concept]].",
        )
        result = cross_reference_validate(sp, ws)
        assert "known-concept" in result.matched
        assert "another-concept" in result.matched
        assert result.missing_refs == []
        print(f"  matched 2/2 (matched={result.matched}): PASS")

    # case 2: mismatch (mentioned but file not present)
    with tempfile.TemporaryDirectory() as tmpdir:
        ws = Path(tmpdir)
        concepts_dir = ws / "ai-workflow" / "wiki" / "concepts"
        concepts_dir.mkdir(parents=True, exist_ok=True)
        (concepts_dir / "known.md").write_text("# k", encoding="utf-8")

        sp = StructuredPurpose(
            purpose_path=None,
            purpose_version=1,
            last_purpose_review="2026-06-26",
            goals=["G1: foo"],
            questions=["Q1: bar?"],
            scope_included=[],
            scope_excluded=[],
            thesis="See [[known]] and [[unknown]].",
        )
        result = cross_reference_validate(sp, ws)
        assert "known" in result.matched
        assert "unknown" in result.missing_refs
        assert any("unmatched" in w for w in result.warnings)
        print(f"  matched 1/2 (missing={result.missing_refs}): PASS")

    # case 3: 부재 (structured None)
    result = cross_reference_validate(None, Path("/tmp"))
    assert result.matched == []
    assert "structured unavailable" in result.warnings[0]
    print("  부재 (structured None): PASS")


# ---------------------------------------------------------------------------
# Acceptance test 5: run_two_step_cot_ingest graceful skip
# ---------------------------------------------------------------------------


def test_run_two_step_cot_ingest_graceful_v0_11_0() -> None:
    """unified entry 의 graceful skip — 부재 / workspace_root 부재 / corrupted."""
    from workflow_kit.common.purpose_ingest import run_two_step_cot_ingest

    # case 1: workspace_root 부재 (no PURPOSE.md)
    with tempfile.TemporaryDirectory() as tmpdir:
        ws = Path(tmpdir)
        result = run_two_step_cot_ingest(workspace_root=ws)
        assert result.raw.missing is True
        assert result.structured is None
        assert result.overall_warnings
        assert "PURPOSE.md 부재" in result.overall_warnings[0]
        print("  case 1 (no PURPOSE.md): PASS")

    # case 2: PURPOSE.md 존재하지만 §1 empty → structured validation error
    with tempfile.TemporaryDirectory() as tmpdir:
        ws = Path(tmpdir)
        purpose_path = ws / "PURPOSE.md"
        purpose_path.write_text(
            "---\npurpose_version: 1\nlast_purpose_review: 2026-06-26\n---\n\n"
            "## 1. Goals\n\n(empty)\n\n## 2. Key Questions\n\n- **Q1**: ?\n\n"
            "## 3. Research Scope\n\n### 포함\n- x\n\n## 4. Evolving Thesis\n\nh: X\n",
            encoding="utf-8",
        )
        result = run_two_step_cot_ingest(workspace_root=ws)
        assert result.raw.missing is False
        assert result.structured is None
        assert any("structured build 실패" in w for w in result.overall_warnings)
        print("  case 2 (§1 empty → validation fail): PASS")

    # case 3: 정상 PURPOSE.md
    with tempfile.TemporaryDirectory() as tmpdir:
        ws = Path(tmpdir)
        purpose_path = ws / "PURPOSE.md"
        purpose_path.write_text(
            "---\npurpose_version: 1\nlast_purpose_review: 2026-06-26\n---\n\n"
            "## 1. Goals\n\n- **G1**: 표준 워크플로우 제공\n\n"
            "## 2. Key Questions\n\n- **Q1**: 어떻게?\n\n"
            "## 3. Research Scope\n\n### 포함\n- 영역\n\n## 4. Evolving Thesis\n\nhypothesis: X\n",
            encoding="utf-8",
        )
        # wiki concepts 디렉토리 생성 (cross_ref 부재 warning 방지)
        concepts_dir = ws / "ai-workflow" / "wiki" / "concepts"
        concepts_dir.mkdir(parents=True, exist_ok=True)
        (concepts_dir / "dummy.md").write_text("# dummy", encoding="utf-8")
        result = run_two_step_cot_ingest(workspace_root=ws)
        assert result.raw.missing is False
        assert result.structured is not None
        assert len(result.structured.goals) == 1
        assert result.overall_warnings == []
        print("  case 3 (정상): PASS")

    # case 4: corrupted frontmatter (graceful skip)
    with tempfile.TemporaryDirectory() as tmpdir:
        ws = Path(tmpdir)
        purpose_path = ws / "PURPOSE.md"
        purpose_path.write_text(
            "this is not a valid PURPOSE.md file\n",
            encoding="utf-8",
        )
        result = run_two_step_cot_ingest(workspace_root=ws)
        # No frontmatter + No ## 1. Goals section → raw exists with warnings, structured fail
        assert result.raw.missing is False
        assert result.structured is None
        assert any("§" in w and "section 부재" in w for w in result.overall_warnings)
        print("  case 4 (corrupted): PASS")


# ---------------------------------------------------------------------------
# Acceptance test 6: cmd_ingest_purpose CLI 등록 + dry-run
# ---------------------------------------------------------------------------


def test_ingest_purpose_cli_registered_v0_11_0() -> None:
    """CLI subcommand 등록 + dry-run subprocess verify (state.json 미변경)."""
    # dispatcher registry 에 ingest-purpose 등록 확인
    from workflow_kit.workflow_kit_cli import COMMANDS
    assert "ingest-purpose" in COMMANDS, "ingest-purpose subcommand not registered"
    print(f"  CLI registered (subcommand 33, total {len(COMMANDS)} commands): PASS")

    # dry-run subprocess verify (state.json 미변경)
    state_path = REPO_ROOT / "ai-workflow" / "memory" / "active" / "state.json"
    if state_path.exists():
        before = state_path.read_text(encoding="utf-8")
    else:
        before = ""

    env = {"PYTHONPATH": str(SOURCE_ROOT), "PATH": __import__("os").environ.get("PATH", "")}
    result = subprocess.run(
        [sys.executable, "-m", "workflow_kit.workflow_kit_cli", "--command=ingest-purpose"],
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    # state.json 미변경 확인
    if state_path.exists():
        after = state_path.read_text(encoding="utf-8")
        assert before == after, "state.json should NOT change in dry-run"
        print(f"  dry-run subprocess verify (state.json preserved, {len(after)} bytes): PASS")
    else:
        print("  dry-run subprocess verify (state.json not present, skipped): PASS")

    # 출력에 핵심 field 포함 확인
    assert "Two-step CoT ingest result" in result.stdout
    assert "raw.missing" in result.stdout
    assert "cot.step2_summary" in result.stdout
    print("  output field completeness: PASS")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    """6 acceptance test 순차 실행. 1 fail = exit 1."""
    print("=== v0.11.0 two-step CoT ingest (R-A follow-up cycle 3) acceptance test ===")
    tests = [
        ("test_extract_raw_purpose_v0_11_0", test_extract_raw_purpose_v0_11_0),
        ("test_build_structured_purpose_v0_11_0", test_build_structured_purpose_v0_11_0),
        ("test_emit_cot_trace_v0_11_0", test_emit_cot_trace_v0_11_0),
        ("test_cross_reference_validate_v0_11_0", test_cross_reference_validate_v0_11_0),
        ("test_run_two_step_cot_ingest_graceful_v0_11_0", test_run_two_step_cot_ingest_graceful_v0_11_0),
        ("test_ingest_purpose_cli_registered_v0_11_0", test_ingest_purpose_cli_registered_v0_11_0),
    ]
    passed = 0
    failed = 0
    for name, fn in tests:
        print(f"\n[{name}]")
        try:
            fn()
            passed += 1
            print(f"  ✓ {name} PASS")
        except AssertionError as e:
            failed += 1
            print(f"  ✗ {name} FAIL: {e}")
        except Exception as e:
            failed += 1
            print(f"  ✗ {name} ERROR: {type(e).__name__}: {e}")

    print(f"\n=== Result: {passed}/{passed+failed} PASS ===")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
