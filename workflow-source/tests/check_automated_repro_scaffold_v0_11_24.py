"""Smoke test for automated-repro-scaffold skill (v0.11.24 stable 승격).

검증:
  1. script 파일 존재 (scripts/run_automated_repro_scaffold.py 표준화 정공법)
  2. Pydantic schema 정합 (AutomatedReproScaffoldOutput + Status enum)
  3. error_code 4종 정의 (report_file_not_found / output_dir_unwritable /
     template_render_failed / runtime_error)
  4. dry-run mode 동작 (write 안 함)
  5. success envelope 의 repro_script_lines 정합

skill_beta_criteria.md §3.1 의 stable 정합 6 조건 smoke.
"""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Iterator

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "workflow-source" / "skills" / "automated-repro-scaffold" / "scripts" / "run_automated_repro_scaffold.py"
SCHEMA_FILE = REPO / "workflow-source" / "workflow_kit" / "common" / "schemas" / "automated_repro_scaffold.py"


# ---------------------------------------------------------------------------
# case 1 — script 존재 + 표준 진입점 (scripts/run_*.py)
# ---------------------------------------------------------------------------

def test_case_1_script_at_standard_location() -> None:
    """scripts/run_automated_repro_scaffold.py 표준 위치에 존재."""
    assert SCRIPT.exists(), f"script not found at standard location: {SCRIPT}"
    content = SCRIPT.read_text(encoding="utf-8")
    # argparse 4개 정의 (--report, --output, --dry-run, --json).
    for arg in ("--report", "--output", "--dry-run", "--json"):
        assert arg in content, f"missing argparse argument: {arg}"


# ---------------------------------------------------------------------------
# case 2 — Pydantic schema 정합 (AutomatedReproScaffoldOutput)
# ---------------------------------------------------------------------------

def test_case_2_pydantic_schema_valid() -> None:
    """AutomatedReproScaffoldOutput 이 Pydantic BaseOutput 상속 + status enum 정합."""
    sys.path.insert(0, str(REPO / "workflow-source"))
    try:
        from workflow_kit.common.schemas.automated_repro_scaffold import (
            AutomatedReproScaffoldOutput,
            AutomatedReproScaffoldSourceContext,
        )
        from workflow_kit.common.schemas.base import Status
    except ImportError as exc:  # noqa: BLE001
        raise AssertionError(f"schema import failed: {exc}") from exc

    # valid instance
    ctx = AutomatedReproScaffoldSourceContext(
        report_path="bug.md", output_path="tests/repro_bug.py"
    )
    out = AutomatedReproScaffoldOutput(
        tool_version="v0.11.24-beta",
        repro_script_path="tests/repro_bug.py",
        repro_script_lines=42,
        execution_command="python3 tests/repro_bug.py",
        next_stage="validation-plan",
        source_context=ctx,
    )
    assert out.status == Status.OK
    assert out.repro_script_lines == 42
    assert out.source_context.report_path == "bug.md"
    # JSON serialization round-trip
    d = json.loads(out.model_dump_json())
    assert d["status"] == "ok"
    assert d["repro_script_lines"] == 42


# ---------------------------------------------------------------------------
# case 3 — error_code 4종 정의 (string literal + argparse 사용)
# ---------------------------------------------------------------------------

def test_case_3_error_codes_defined() -> None:
    """4종 error_code literal 이 script 내에 정의되어 있다."""
    content = SCRIPT.read_text(encoding="utf-8")
    expected_codes = [
        "automated_repro_scaffold_report_file_not_found",
        "automated_repro_scaffold_output_dir_unwritable",
        "automated_repro_scaffold_template_render_failed",
        "automated_repro_scaffold_runtime_error",
    ]
    for code in expected_codes:
        assert code in content, f"missing error_code literal: {code}"


# ---------------------------------------------------------------------------
# case 4 — dry-run mode (write 안 함, preview 만 출력)
# ---------------------------------------------------------------------------

def test_case_4_dry_run_no_write() -> None:
    """--dry-run 으로 실행 시, output file 이 write 안 되고 preview 만 stdout 으로."""
    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        report = td_path / "report.md"
        output = td_path / "repro_test.py"
        report.write_text("Bug: foo returns None instead of 42.\n", encoding="utf-8")
        assert not output.exists(), "precondition: output must not exist"

        proc = subprocess.run(
            [
                sys.executable, str(SCRIPT),
                "--report", str(report),
                "--output", str(output),
                "--dry-run",
            ],
            cwd=str(REPO),
            capture_output=True,
            text=True,
            timeout=30,
            env={**os.environ, "PYTHONPATH": str(REPO / "workflow-source")},
        )
        assert proc.returncode == 0, f"dry-run failed: {proc.stderr}"
        assert not output.exists(), "dry-run should not write the output file"
        result = json.loads(proc.stdout)
        assert result.get("mode") == "dry-run"
        assert result.get("would_write_to") == str(output)
        assert "preview_first_500" in result


# ---------------------------------------------------------------------------
# case 5 — 정상 실행 (success envelope + repro_script_lines 정합)
# ---------------------------------------------------------------------------

def test_case_5_success_envelope_and_line_count() -> None:
    """정상 실행 시 status=ok, repro_script_lines > 0, source_context.report_path 정합."""
    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        report = td_path / "bug.md"
        output = td_path / "repro_success.py"
        report.write_text(
            "# Bug Report\n\n## Steps\n1. Run foo()\n2. Expect 42\n3. Actual: None\n",
            encoding="utf-8",
        )

        proc = subprocess.run(
            [
                sys.executable, str(SCRIPT),
                "--report", str(report),
                "--output", str(output),
            ],
            cwd=str(REPO),
            capture_output=True,
            text=True,
            timeout=30,
            env={**os.environ, "PYTHONPATH": str(REPO / "workflow-source")},
        )
        assert proc.returncode == 0, f"script failed: {proc.stderr}"
        result = json.loads(proc.stdout)
        assert result.get("status") == "ok"
        assert result.get("repro_script_path") == str(output)
        assert result.get("repro_script_lines", 0) > 0
        assert result.get("execution_command") == f"python3 {output}"
        assert result.get("next_stage") == "validation-plan"
        assert result.get("source_context", {}).get("report_path") == str(report)
        # 실제 file 이 생성됐고 import 가능한지 확인.
        assert output.exists()
        assert "import unittest" in output.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# runner
# ---------------------------------------------------------------------------

def _run_all() -> Iterator[tuple[str, bool, str]]:
    cases = [
        ("test_case_1_script_at_standard_location", test_case_1_script_at_standard_location),
        ("test_case_2_pydantic_schema_valid", test_case_2_pydantic_schema_valid),
        ("test_case_3_error_codes_defined", test_case_3_error_codes_defined),
        ("test_case_4_dry_run_no_write", test_case_4_dry_run_no_write),
        ("test_case_5_success_envelope_and_line_count", test_case_5_success_envelope_and_line_count),
    ]
    for name, fn in cases:
        try:
            fn()
            yield name, True, ""
        except AssertionError as exc:
            yield name, False, str(exc)
        except Exception as exc:  # noqa: BLE001
            yield name, False, f"{type(exc).__name__}: {exc}"


def main() -> int:
    print("=== automated-repro-scaffold (v0.11.24 stable) ===")
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