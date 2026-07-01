#!/usr/bin/env python3
"""Smoke test the robust-patcher skill (v0.11.21 stable 2nd batch)."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
SCRIPT_PATH = SOURCE_ROOT / "skills" / "robust_patcher" / "scripts" / "run_robust_patcher.py"

if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from workflow_kit.common.output_contracts import validate_output_payload


def run_patcher(*, expect_success: bool, args: list[str]) -> tuple[int, dict[str, object]]:
    completed = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if expect_success and completed.returncode != 0:
        raise AssertionError(f"Expected robust-patcher success but got {completed.returncode}: {completed.stderr}")
    if not expect_success and completed.returncode == 0:
        raise AssertionError("Expected robust-patcher failure path but command succeeded.")
    return completed.returncode, json.loads(completed.stdout)


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp_dir:
        # ----- Case 1: Exact-match SEARCH/REPLACE block — success path -----
        target_path = Path(tmp_dir) / "module.py"
        original_source = (
            "def greet(name):\n"
            "    return 'hello ' + name\n"
            "\n"
            "\n"
            "def farewell(name):\n"
            "    return 'bye ' + name\n"
        )
        target_path.write_text(original_source, encoding="utf-8")

        patch_path = Path(tmp_dir) / "patch.txt"
        patch_path.write_text(
            "<<<<<<< SEARCH\n"
            "def greet(name):\n"
            "    return 'hello ' + name\n"
            "=======\n"
            "def greet(name):\n"
            "    return f'hello {name}'\n"
            ">>>>>>> REPLACE\n",
            encoding="utf-8",
        )

        _, payload = run_patcher(
            expect_success=True,
            args=["--file", str(target_path), "--patch-file", str(patch_path)],
        )
        output_errors = validate_output_payload(payload, family="robust_patcher")
        if output_errors:
            raise AssertionError(
                f"Robust-patcher success payload violated output contract: {output_errors}"
            )
        if payload["status"] != "ok":
            raise AssertionError(f"Expected ok status, got {payload['status']}")
        if payload["dry_run"] is not False:
            raise AssertionError("Expected dry_run=False when not requested.")
        if not payload["applied_blocks"]:
            raise AssertionError("Expected at least one applied_block entry.")
        if not payload["applied_blocks"][0]["matched"]:
            raise AssertionError("Expected first block to be matched.")
        if payload["applied_blocks"][0]["fuzzy_score"] != 1.0:
            raise AssertionError(
                f"Expected exact-match fuzzy_score=1.0, got {payload['applied_blocks'][0]['fuzzy_score']}"
            )
        if not payload["syntax_validated"]:
            raise AssertionError("Expected syntax_validated=True for valid .py patch.")
        if "validation-plan" not in (payload.get("stage_completion", {}).get("next_stage") or ""):
            raise AssertionError(
                "Expected stage_completion.next_stage = 'validation-plan' (catalog wiring)."
            )

        # Verify the file was actually patched
        new_text = target_path.read_text(encoding="utf-8")
        if "f'hello {name}'" not in new_text:
            raise AssertionError(f"Target file was not patched. Got:\n{new_text}")

        # ----- Case 2: Dry-run (preview only, no write) -----
        target2 = Path(tmp_dir) / "module2.py"
        target2.write_text(original_source, encoding="utf-8")
        patch2 = Path(tmp_dir) / "patch2.txt"
        patch2.write_text(
            "<<<<<<< SEARCH\n"
            "def farewell(name):\n"
            "    return 'bye ' + name\n"
            "=======\n"
            "def farewell(name):\n"
            "    return f'bye {name}'\n"
            ">>>>>>> REPLACE\n",
            encoding="utf-8",
        )

        _, dry_payload = run_patcher(
            expect_success=True,
            args=[
                "--file", str(target2),
                "--patch-file", str(patch2),
                "--dry-run",
            ],
        )
        if dry_payload["status"] != "ok":
            raise AssertionError("Expected dry-run success.")
        if dry_payload["dry_run"] is not True:
            raise AssertionError("Expected dry_run=True in --dry-run mode.")
        # File should NOT have been modified
        if target2.read_text(encoding="utf-8") != original_source:
            raise AssertionError("Dry-run should not modify the target file.")

        # ----- Case 3: fuzzy_match_failed — SEARCH block doesn't exist -----
        target3 = Path(tmp_dir) / "module3.py"
        target3.write_text(original_source, encoding="utf-8")
        patch3 = Path(tmp_dir) / "patch3.txt"
        patch3.write_text(
            "<<<<<<< SEARCH\n"
            "def nonexistent_function():\n"
            "    return 'this code is not in target'\n"
            "=======\n"
            "def nonexistent_function():\n"
            "    return 'replaced'\n"
            ">>>>>>> REPLACE\n",
            encoding="utf-8",
        )

        failure_code, failure_payload = run_patcher(
            expect_success=False,
            args=["--file", str(target3), "--patch-file", str(patch3)],
        )
        if failure_payload["error_code"] != "fuzzy_match_failed":
            raise AssertionError(
                f"Expected fuzzy_match_failed error_code, got {failure_payload['error_code']}"
            )
        # File should NOT have been modified (atomic semantics)
        if target3.read_text(encoding="utf-8") != original_source:
            raise AssertionError(
                "Failed patch should leave the target file untouched (atomic semantics)."
            )

        # ----- Case 4: malformed_patch_block — no valid SEARCH/REPLACE block -----
        target4 = Path(tmp_dir) / "module4.py"
        target4.write_text(original_source, encoding="utf-8")
        patch4 = Path(tmp_dir) / "patch4.txt"
        patch4.write_text(
            "# Just a comment, no SEARCH/REPLACE markers\n",
            encoding="utf-8",
        )

        mal_code, mal_payload = run_patcher(
            expect_success=False,
            args=["--file", str(target4), "--patch-file", str(patch4)],
        )
        if mal_payload["error_code"] != "malformed_patch_block":
            raise AssertionError(
                f"Expected malformed_patch_block error_code, got {mal_payload['error_code']}"
            )

        # ----- Case 5: missing_required_document — patch file missing -----
        missing_code, missing_payload = run_patcher(
            expect_success=False,
            args=["--file", str(target4), "--patch-file", "/tmp/missing-patch-file-xyz.txt"],
        )
        if missing_payload["error_code"] != "missing_required_document":
            raise AssertionError(
                f"Expected missing_required_document error_code, got {missing_payload['error_code']}"
            )

    print("Robust-patcher smoke check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())