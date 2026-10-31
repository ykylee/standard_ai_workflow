#!/usr/bin/env python3
"""Smoke test the code-index-update prototype."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

SOURCE_ROOT_FOR_IMPORT = Path(__file__).resolve().parents[2] / "workflow-source"
if str(SOURCE_ROOT_FOR_IMPORT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT_FOR_IMPORT))

from workflow_kit.common.output_contracts import validate_output_payload


REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
SCRIPT_PATH = SOURCE_ROOT / "skills" / "code-index-update" / "scripts" / "run_code_index_update.py"


def _posix(text: str) -> str:
    """경로 구분자만 POSIX 형식으로 정규화한다 — 판정은 경로 **내용**이 아니라 끝부분을 본다.

    산출물의 후보 경로는 OS 네이티브 표기다 (Windows 는 백슬래시). 그대로 접미사를
    비교하면 Windows 에서만 "선언된 문서 홈이 우선 후보가 아니다" 로 red 가 된다
    (2026-10-31 실측: 후보는 실제로 `...\\docs\\README.md` 였음). 경로 자체는 바꾸지
    않고 **구분자만** 정규화해 두 플랫폼에서 같은 판정이 나게 한다.
    """
    return text.replace("\\", "/")


def run_index_update(example_name: str, changed_files: list[str], change_summary: str) -> dict[str, object]:
    example_root = SOURCE_ROOT / "examples" / example_name
    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT_PATH),
            "--project-profile-path",
            str(example_root / "PROJECT_PROFILE.md"),
            "--work-backlog-index-path",
            str(example_root / "work_backlog.md"),
            "--session-handoff-path",
            str(example_root / "session_handoff.md"),
            *sum([["--changed-file", item] for item in changed_files], []),
            "--change-summary",
            change_summary,
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=True,
    )
    return json.loads(completed.stdout)


def main() -> int:
    acme_payload = run_index_update(
        "acme_delivery_platform",
        [
            "app/jobs/delivery_sync.py",
            "docs/operations/runbooks/delivery-sync.md",
        ],
        "delivery sync 재시도 로직과 운영 runbook 동시 수정",
    )
    output_errors = validate_output_payload(acme_payload, family="code_index_update")
    if output_errors:
        raise AssertionError(f"Acme code-index-update payload violated output contract: {output_errors}")
    acme_priorities = set(acme_payload["priority_index_candidates"])
    if not any(_posix(item).endswith("docs/README.md") for item in acme_priorities):
        raise AssertionError("Acme example should elevate the declared document home as a priority index candidate.")
    if not any(_posix(item).endswith("docs/operations/README.md") for item in acme_priorities):
        raise AssertionError("Acme example should elevate the operations README candidate.")
    if not acme_payload["stale_index_warnings"]:
        raise AssertionError("Acme example should produce at least one stale index warning.")

    research_payload = run_index_update(
        "research_eval_hub",
        [
            "evals/pipelines/report_builder.py",
            "docs/evals/reports/release-report-v2.md",
        ],
        "evaluation report builder 로직과 release report 동시 수정",
    )
    output_errors = validate_output_payload(research_payload, family="code_index_update")
    if output_errors:
        raise AssertionError(f"Research code-index-update payload violated output contract: {output_errors}")
    research_candidates = set(research_payload["index_update_candidates"])
    if not any(_posix(item).endswith("docs/evals/README.md") for item in research_candidates):
        raise AssertionError("Research example should include the evals README candidate.")
    if not research_payload["document_structure_signals"]:
        raise AssertionError("Research example should include document structure signals.")

    workflow_meta_payload = run_index_update(
        "acme_delivery_platform",
        [
            "ai-workflow/memory/active/sessions",
        ],
        "workflow 상태 문서만 수정",
    )
    if workflow_meta_payload["source_context"]["changed_files"]:
        raise AssertionError("Code-index-update should ignore ai-workflow metadata paths in changed_files.")

    with tempfile.TemporaryDirectory() as tmpdir:
        repo_root = Path(tmpdir) / "repo"
        workflow_project = repo_root / "ai-workflow" / "project"
        workflow_project.mkdir(parents=True, exist_ok=True)
        (repo_root / "docs" / "operations").mkdir(parents=True, exist_ok=True)
        (repo_root / "README.md").write_text("# Repo\n", encoding="utf-8")
        (repo_root / "docs" / "README.md").write_text("# Docs\n", encoding="utf-8")
        (repo_root / "docs" / "operations" / "README.md").write_text("# Operations\n", encoding="utf-8")
        (workflow_project / "PROJECT_PROFILE.md").write_text(
            (
                "# Project Workflow Profile\n\n"
                "## 1. 프로젝트 개요\n\n"
                "- 프로젝트명:\n- `Temp Repo`\n\n"
                "## 2. 문서 구조\n\n"
                "- 문서 위키 홈:\n- `docs/README.md`\n"
                "- 운영 문서 위치:\n- `docs/operations/`\n"
                "- 백로그 위치:\n- `docs/operations/backlog/`\n"
                "- 세션 인계 문서 위치:\n- `docs/operations/session_handoff.md`\n"
                "- 환경 기록 위치:\n- `docs/operations/environments/`\n"
            ),
            encoding="utf-8",
        )
        completed = subprocess.run(
            [
                sys.executable,
                str(SCRIPT_PATH),
                "--project-profile-path",
                str(workflow_project / "PROJECT_PROFILE.md"),
                "--changed-file",
                "docs/operations/runbooks/foo.md",
                "--change-summary",
                "runbook 수정",
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=True,
        )
        payload = json.loads(completed.stdout)
        if not any(_posix(item).endswith("/docs/README.md") for item in payload["priority_index_candidates"]):
            raise AssertionError("Project docs should resolve from repository root, not ai-workflow/memory.")
        if any("/ai-workflow/memory/docs/" in _posix(item) for item in payload["index_update_candidates"]):
            raise AssertionError("Project doc candidates should not resolve under ai-workflow/memory/docs.")

    print("Code-index-update smoke check passed.")
    return 0


def test_case_1() -> None:
    assert main() == 0, "case_1 smoke FAIL"


def test_case_2() -> None:
    assert main() == 0, "case_2 smoke FAIL"


def test_case_3() -> None:
    assert main() == 0, "case_3 smoke FAIL"


def test_case_4() -> None:
    assert main() == 0, "case_4 smoke FAIL"


def test_case_5() -> None:
    assert main() == 0, "case_5 smoke FAIL"



if __name__ == "__main__":
    raise SystemExit(main())
