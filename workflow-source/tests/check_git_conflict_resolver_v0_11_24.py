"""Smoke test for git-conflict-resolver skill (v0.11.24 beta/stable).

검증:
  1. script 존재 + argparse 정의 (--file / --handoff-path / --apply / --dry-run)
  2. Pydantic schema 정합 (GitConflictResolverOutput + ConflictPoint + ResolutionStrategy)
  3. error_code 4종 정의
  4. conflict detection 동작 (<<<<<<< >>>>>>> pattern parsing)
  5. dry-run + handoff-path 정상 케이스 동작

skill_beta_criteria.md §3.1 의 stable 정합 6 조건 smoke.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Iterator

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "workflow-source" / "skills" / "git-conflict-resolver" / "scripts" / "run_git_conflict_resolver.py"
SCHEMA_FILE = REPO / "workflow-source" / "workflow_kit" / "common" / "schemas" / "git.py"


# ---------------------------------------------------------------------------
# case 1 — script 존재 + argparse 정의
# ---------------------------------------------------------------------------

def test_case_1_script_with_argparse() -> None:
    """script 존재 + 5개 argparse 정의."""
    assert SCRIPT.exists(), f"script not found: {SCRIPT}"
    content = SCRIPT.read_text(encoding="utf-8")
    for arg in ("--file", "--handoff-path", "--apply", "--dry-run"):
        assert arg in content, f"missing argparse argument: {arg}"


# ---------------------------------------------------------------------------
# case 2 — Pydantic schema 정합
# ---------------------------------------------------------------------------

def test_case_2_pydantic_schema_valid() -> None:
    """GitConflictResolverOutput Pydantic schema + ResolutionStrategy enum 정합."""
    sys.path.insert(0, str(REPO / "workflow-source"))
    try:
        from workflow_kit.common.schemas import (
            GitConflictResolverOutput,
            ConflictPoint,
            ResolutionStrategy,
            Status,
        )
    except ImportError as exc:
        raise AssertionError(f"schema import failed: {exc}") from exc

    cp = ConflictPoint(
        file_path="src/foo.py",
        our_content="print('ours')",
        their_content="print('theirs')",
        resolution_strategy=ResolutionStrategy.MERGE,
        resolution_note="intelligent merge required",
    )
    out = GitConflictResolverOutput(
        tool_version="v0.11.24-beta",
        conflict_count=1,
        resolved_count=1,
        resolution_summary="1 conflict processed",
        conflicts=[cp],
        source_context={"files": "['src/foo.py']", "handoff_path": "N/A"},
    )
    assert out.status == Status.OK
    assert len(out.conflicts) == 1
    assert out.conflicts[0].resolution_strategy == ResolutionStrategy.MERGE
    # JSON round-trip
    d = json.loads(out.model_dump_json())
    assert d["conflict_count"] == 1
    assert d["conflicts"][0]["resolution_strategy"] == "merge"


# ---------------------------------------------------------------------------
# case 3 — error_code 4종 정의
# ---------------------------------------------------------------------------

def test_case_3_error_codes_defined() -> None:
    """4종 error_code literal 이 script 내에 정의되어 있다."""
    content = SCRIPT.read_text(encoding="utf-8")
    expected_codes = [
        "git_conflict_resolver_handoff_parse_failed",
        "git_conflict_resolver_file_unreadable",
        "git_conflict_resolver_resolution_invalid",
        "git_conflict_resolver_runtime_error",
    ]
    for code in expected_codes:
        assert code in content, f"missing error_code literal: {code}"


# ---------------------------------------------------------------------------
# case 4 — conflict detection 동작 (<<<<<<< / >>>>>>> pattern)
# ---------------------------------------------------------------------------

def test_case_4_conflict_detection_in_file() -> None:
    """conflict marker 가 들어 있는 file 에 대해 script 가 정상 detection + resolution_summary 출력."""
    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        conf_file = td_path / "conflicted.py"
        conf_file.write_text(
            "# Section\n"
            "<<<<<<< HEAD\n"
            "x = 1\n"
            "=======\n"
            "x = 2\n"
            ">>>>>>> branch-feature\n",
            encoding="utf-8",
        )
        proc = subprocess.run(
            [
                sys.executable, str(SCRIPT),
                "--file", str(conf_file),
                "--dry-run",
            ],
            cwd=str(REPO),
            capture_output=True,
            text=True,
            timeout=30,
            env={**os.environ, "PYTHONPATH": str(REPO / "workflow-source")},
        )
        assert proc.returncode == 0, f"script failed: {proc.stderr}"
        result = json.loads(proc.stdout)
        assert result.get("mode") == "dry-run"
        assert result.get("conflict_count") == 1
        assert result.get("resolved_count") == 0  # handoff 없으므로 context_keywords 비어있음
        assert "conflicts" in result
        assert result["conflicts"][0]["file_path"] == str(conf_file)
        assert "x = 1" in result["conflicts"][0]["our_content"]
        assert "x = 2" in result["conflicts"][0]["their_content"]


# ---------------------------------------------------------------------------
# case 5 — handoff-path 정상 케이스 (context keyword resolution)
# ---------------------------------------------------------------------------

def test_case_5_handoff_path_no_crash_with_unparseable_input() -> None:
    """--handoff-path 가 parse 실패해도 script 가 structured error envelope 출력."""
    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        conf_file = td_path / "conflicted.py"
        conf_file.write_text(
            "# Section\n"
            "<<<<<<< HEAD\n"
            "x = 1\n"
            "=======\n"
            "x = 2\n"
            ">>>>>>> branch\n",
            encoding="utf-8",
        )
        # 본 handoff 는 parse_handoff 가 인식하지 못하는 형식이지만, file 자체는 존재.
        # v0.11.24 의 refactor: parse 실패 시 graceful fallback (warnings 만, error envelope 안 emit).
        handoff = td_path / "handoff.md"
        handoff.write_text(
            "# Session Handoff\n- current_axis: special_value\n",
            encoding="utf-8",
        )

        proc = subprocess.run(
            [
                sys.executable, str(SCRIPT),
                "--file", str(conf_file),
                "--handoff-path", str(handoff),
            ],
            cwd=str(REPO),
            capture_output=True,
            text=True,
            timeout=30,
            env={**os.environ, "PYTHONPATH": str(REPO / "workflow-source")},
        )
        # 본 시점: parse_handoff 가 unrecognized handoff format 에서 RuntimeError raise 시
        # handoff_parse_failed error_code emit, returncode 1. parse 성공 시 status=ok, returncode 0.
        # 둘 다 "structured envelope" 의 형태 (json.dumps on stdout).
        assert proc.returncode in (0, 1), f"unexpected returncode: {proc.returncode} stderr={proc.stderr}"
        try:
            result = json.loads(proc.stdout)
        except json.JSONDecodeError as exc:
            raise AssertionError(
                f"non-JSON output (parse failure 미스): {proc.stdout[:500]!r}"
            ) from exc
        # status field 존재 검증.
        assert "status" in result, f"missing status field: {result}"
        # conflict_count 가 1 이상 (file 의 conflict marker 가 인식됨).
        assert result.get("conflict_count", 0) >= 1
        # source_context.handoff_path 일치.
        assert result.get("source_context", {}).get("handoff_path") == str(handoff)


# ---------------------------------------------------------------------------
# runner
# ---------------------------------------------------------------------------

def _run_all() -> Iterator[tuple[str, bool, str]]:
    cases = [
        ("test_case_1_script_with_argparse", test_case_1_script_with_argparse),
        ("test_case_2_pydantic_schema_valid", test_case_2_pydantic_schema_valid),
        ("test_case_3_error_codes_defined", test_case_3_error_codes_defined),
        ("test_case_4_conflict_detection_in_file", test_case_4_conflict_detection_in_file),
        ("test_case_5_handoff_path_no_crash_with_unparseable_input", test_case_5_handoff_path_no_crash_with_unparseable_input),
    ]
    for name, fn in cases:
        try:
            fn()
            yield name, True, ""
        except AssertionError as exc:
            yield name, False, str(exc)
        except Exception as exc:
            yield name, False, f"{type(exc).__name__}: {exc}"


def main() -> int:
    print("=== git-conflict-resolver (v0.11.24 beta/stable) ===")
    failures = 0
    for name, ok, msg in _run_all():
        if ok:
            print(f"  PASS: {name}")
        else:
            print(f"  FAIL: {name}\n    {msg}")
            failures += 1
    print(f"=== {'PASS' if failures == 0 else 'FAIL'}: {5 - failures}/5 ===")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())