#!/usr/bin/env python3
"""Smoke test — apply-robust-patch MCP (v0.14.2+ 2nd batch stable) 5 case PASS.

skill_beta_criteria §3.1 의 6 condition 중 smoke_test_5_cases 정공법 적용.
본 MCP 는 **쓰기 작업** (file modify) — smoke test 시 `tempfile.TemporaryDirectory`
로 격리하여 side-effect 차단. dry-run mode 가 정합의 기본 권장.

5 cases:
  1) CLI 도움말 (--help): argparse exit 0 + description 포함
  2) 정상 patch 적용: status=ok + patches_applied=1 + 실제 file 의 SEARCH 가 REPLACE 로 교체됨
  3) 부재 file_path: status=error + error_code='file_not_found'
  4) malformed patch (SEARCH/REPLACE delimiter 부재): status=error + error_code='malformed_patch_block'
  5) Pydantic schema validate: output dict 가 ApplyRobustPatchOutput 으로 model_validate 가능 + 4 error code 정의 정합
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "workflow-source" / "mcp_servers" / "apply_robust_patch" / "scripts" / "run_apply_robust_patch.py"


def _run(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = (
        f"{REPO_ROOT / 'workflow-source'}"
        + (os.pathsep + existing_pythonpath if existing_pythonpath else "")
    )
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=str(cwd or REPO_ROOT), env=env, capture_output=True, text=True, timeout=30,
    )


def case_1_help() -> bool:
    """1) --help 정상 동작."""
    proc = _run("--help")
    if proc.returncode != 0:
        print(f"  FAIL: --help returncode={proc.returncode}")
        return False
    if "patch" not in proc.stdout.lower():
        print(f"  FAIL: --help output missing 'patch' description")
        return False
    return True


def case_2_valid_patch() -> bool:
    """2) 정상 patch 적용 — SEARCH 가 REPLACE 로 교체됨."""
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "sample.txt"
        target.write_text("hello world\nsecond line\n", encoding="utf-8")
        patch = (
            "<<<<<<< SEARCH\n"
            "hello world\n"
            "=======\n"
            "hello CLAUDE\n"
            ">>>>>>> REPLACE"
        )
        proc = _run("--file-path", str(target), "--patch-content", patch)
        if proc.returncode != 0:
            print(f"  FAIL: patch returncode={proc.returncode}, stderr={proc.stderr[:200]}")
            return False
        try:
            payload = json.loads(proc.stdout)
        except json.JSONDecodeError as exc:
            print(f"  FAIL: JSON parse: {exc}")
            return False
        if payload.get("status") != "ok":
            print(f"  FAIL: status={payload.get('status')!r}")
            return False
        if payload.get("patches_applied") != 1:
            print(f"  FAIL: patches_applied={payload.get('patches_applied')!r}")
            return False
        # 실제 file 의 SEARCH 가 REPLACE 로 교체 검증 (쓰기 작업 정합)
        if "hello CLAUDE" not in target.read_text(encoding="utf-8"):
            print(f"  FAIL: file content unchanged (patch write not applied)")
            return False
    return True


def case_3_file_not_found() -> bool:
    """3) 부재 file_path → status=error + error_code='file_not_found'."""
    proc = _run(
        "--file-path", "/tmp/this_file_definitely_does_not_exist_99999.txt",
        "--patch-content", "<<<<<<< SEARCH\nx\n=======\ny\n>>>>>>> REPLACE",
    )
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        print(f"  FAIL: JSON parse: {exc}")
        return False
    if payload.get("status") != "error":
        print(f"  FAIL: status={payload.get('status')!r} (expected error)")
        return False
    if payload.get("error_code") != "file_not_found":
        print(f"  FAIL: error_code={payload.get('error_code')!r} (expected file_not_found)")
        return False
    return True


def case_4_malformed_patch() -> bool:
    """4) malformed patch (SEARCH/REPLACE delimiter 부재) → status=error + error_code='malformed_patch_block'."""
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "sample.txt"
        target.write_text("hello world\n", encoding="utf-8")
        # No SEARCH/REPLACE delimiters
        proc = _run(
            "--file-path", str(target),
            "--patch-content", "this is not a valid patch",
        )
        try:
            payload = json.loads(proc.stdout)
        except json.JSONDecodeError as exc:
            print(f"  FAIL: JSON parse: {exc}")
            return False
        if payload.get("status") != "error":
            print(f"  FAIL: status={payload.get('status')!r} (expected error)")
            return False
        if payload.get("error_code") != "malformed_patch_block":
            print(f"  FAIL: error_code={payload.get('error_code')!r} (expected malformed_patch_block)")
            return False
    return True


def case_5_pydantic_validate() -> bool:
    """5) Pydantic schema validate + 4 error code 정의 정합."""
    try:
        sys.path.insert(0, str(REPO_ROOT / "workflow-source"))
        from workflow_kit.common.schemas.apply_robust_patch import (
            ApplyRobustPatchOutput,
            APPLY_ROBUST_PATCH_ERROR_CODES,
        )
    except ImportError as exc:
        print(f"  FAIL: schema import: {exc}")
        return False

    # 4 종 error code 정의 정합 (skill_beta_criteria §3.1 3rd condition)
    expected_codes = {
        "missing_required_argument",
        "file_not_found",
        "malformed_patch_block",
        "apply_robust_patch_runtime_error",
    }
    actual_codes = set(APPLY_ROBUST_PATCH_ERROR_CODES)
    if actual_codes != expected_codes:
        print(f"  FAIL: error_codes mismatch (expected={expected_codes}, actual={actual_codes})")
        return False

    # sample dict validate
    sample_ok = {
        "status": "ok",
        "tool_version": "v0.14.2-beta",
        "warnings": [],
        "file_path": "/tmp/x.py",
        "message": "patched",
        "patches_applied": 1,
        "patches_failed": 0,
        "dry_run": False,
        "applied_blocks": [],
    }
    try:
        out = ApplyRobustPatchOutput.model_validate(sample_ok)
    except Exception as exc:
        print(f"  FAIL: Pydantic validate (ok): {exc}")
        return False
    if out.patches_applied != 1 or out.file_path != "/tmp/x.py":
        print(f"  FAIL: field mismatch (ok)")
        return False

    # error sample validate
    sample_err = {
        "status": "error",
        "tool_version": "v0.14.2-beta",
        "warnings": ["file not found"],
        "file_path": "/tmp/missing.py",
        "message": "file not found",
        "patches_applied": 0,
        "patches_failed": 0,
        "dry_run": False,
        "applied_blocks": [],
        "error": "file not found",
        "error_code": "file_not_found",
        "source_context": {"file_path": "/tmp/missing.py"},
    }
    try:
        out_err = ApplyRobustPatchOutput.model_validate(sample_err)
    except Exception as exc:
        print(f"  FAIL: Pydantic validate (error): {exc}")
        return False
    if out_err.error_code != "file_not_found":
        print(f"  FAIL: error_code mismatch")
        return False
    return True


def main() -> int:
    cases = [
        ("case_1_help", case_1_help),
        ("case_2_valid_patch", case_2_valid_patch),
        ("case_3_file_not_found", case_3_file_not_found),
        ("case_4_malformed_patch", case_4_malformed_patch),
        ("case_5_pydantic_validate", case_5_pydantic_validate),
    ]
    results: list[tuple[str, bool]] = []
    for name, fn in cases:
        results.append((name, fn()))
    passed = sum(1 for _, ok in results if ok)
    for name, ok in results:
        marker = "PASS" if ok else "FAIL"
        print(f"  [{marker}] {name}")
    print(f"\n=== {passed}/{len(cases)} PASS ===")
    if passed != len(cases):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())