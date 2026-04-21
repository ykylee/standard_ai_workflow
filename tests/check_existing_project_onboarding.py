#!/usr/bin/env python3
"""Smoke test the existing-project onboarding runner."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP_SCRIPT = REPO_ROOT / "scripts" / "bootstrap_workflow_kit.py"
ONBOARDING_SCRIPT = REPO_ROOT / "scripts" / "run_existing_project_onboarding.py"


def run_json(cmd: list[str], cwd: Path) -> dict[str, object]:
    completed = subprocess.run(
        [sys.executable, *cmd],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(completed.stdout)


def run_json_allow_failure(cmd: list[str], cwd: Path) -> tuple[int, dict[str, object]]:
    completed = subprocess.run(
        [sys.executable, *cmd],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    return completed.returncode, json.loads(completed.stdout)


def main() -> int:
    with tempfile.TemporaryDirectory() as tmpdir:
        target_root = Path(tmpdir) / "existing-repo"
        (target_root / "docs").mkdir(parents=True, exist_ok=True)
        (target_root / "src").mkdir(parents=True, exist_ok=True)
        (target_root / "tests").mkdir(parents=True, exist_ok=True)
        (target_root / "README.md").write_text("# Existing Repo\n", encoding="utf-8")
        (target_root / "docs" / "README.md").write_text("# Docs\n", encoding="utf-8")
        (target_root / "package.json").write_text(
            json.dumps(
                {
                    "name": "existing-repo",
                    "scripts": {
                        "dev": "node server.js",
                        "test": "vitest",
                        "test:unit": "vitest run",
                        "test:smoke": "playwright test",
                    },
                }
            ),
            encoding="utf-8",
        )

        bootstrap_payload = run_json(
            [
                str(BOOTSTRAP_SCRIPT),
                "--target-root",
                str(target_root),
                "--project-slug",
                "existing_repo",
                "--project-name",
                "Existing Repo",
                "--adoption-mode",
                "existing",
                "--copy-core-docs",
            ],
            REPO_ROOT,
        )
        generated = bootstrap_payload["generated_files"]
        project_dir = Path(generated["project_profile"]).parent

        onboarding_payload = run_json(
            [
                str(ONBOARDING_SCRIPT),
                "--project-profile-path",
                str(generated["project_profile"]),
                "--session-handoff-path",
                str(generated["session_handoff"]),
                "--work-backlog-index-path",
                str(generated["work_backlog"]),
                "--backlog-dir-path",
                str(project_dir / "backlog"),
                "--repository-assessment-path",
                str(generated["repository_assessment"]),
                "--change-summary",
                "기존 프로젝트 도입 초안과 추정 명령/문서 구조를 실제 저장소 기준으로 정렬한다.",
            ],
            REPO_ROOT,
        )

        if onboarding_payload["onboarding_mode"] != "existing_project_followup":
            raise AssertionError("Unexpected onboarding mode.")
        if onboarding_payload["repository_assessment"]["summary"]["primary_stack"] != "node":
            raise AssertionError("Expected node primary stack from repository assessment.")
        if not onboarding_payload["session_start"]["summary"]:
            raise AssertionError("Expected session_start summary in onboarding output.")
        if not onboarding_payload["validation_plan"]["recommended_validation_levels"]:
            raise AssertionError("Expected validation plan levels in onboarding output.")
        if not onboarding_payload["code_index_update"]["index_update_candidates"]:
            raise AssertionError("Expected code-index-update candidates in onboarding output.")
        if len(onboarding_payload["onboarding_summary"]["recommended_next_steps"]) < 3:
            raise AssertionError("Expected multiple onboarding next steps.")
        if onboarding_payload["orchestration_plan"]["model_split"]["orchestrator"] != "main":
            raise AssertionError("Expected main orchestrator model split in onboarding output.")
        if not onboarding_payload["source_context"]["project_profile_path"]:
            raise AssertionError("Expected onboarding source_context to include project_profile_path.")

        failure_code, failure_payload = run_json_allow_failure(
            [
                str(ONBOARDING_SCRIPT),
                "--project-profile-path",
                "/tmp/missing-profile.md",
                "--session-handoff-path",
                str(generated["session_handoff"]),
                "--work-backlog-index-path",
                str(generated["work_backlog"]),
                "--backlog-dir-path",
                str(project_dir / "backlog"),
            ],
            REPO_ROOT,
        )
        if failure_code == 0:
            raise AssertionError("Expected onboarding runner failure for missing profile path.")
        if failure_payload["status"] != "error":
            raise AssertionError("Expected structured error payload for onboarding failure.")
        if failure_payload["error_code"] != "missing_required_document":
            raise AssertionError("Expected missing_required_document error code.")
        if failure_payload["source_context"]["project_profile_path"] != "/private/tmp/missing-profile.md":
            raise AssertionError("Expected source_context to retain the missing project profile path.")

    print("Existing-project onboarding smoke check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
