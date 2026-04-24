#!/usr/bin/env python3
"""Smoke test the workflow bootstrap scaffold."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP_SCRIPT = REPO_ROOT / "scripts" / "bootstrap_workflow_kit.py"


def run_bootstrap(args: list[str]) -> dict[str, object]:
    completed = subprocess.run(
        [sys.executable, str(BOOTSTRAP_SCRIPT), *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(completed.stdout)


def assert_exists(raw_path: str) -> None:
    path = Path(raw_path)
    if not path.exists():
        raise AssertionError(f"Missing generated file: {path}")


def check_new_project_mode() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        target_root = Path(tmpdir) / "sample-repo"
        target_root.mkdir(parents=True, exist_ok=True)
        payload = run_bootstrap(
            [
                "--target-root",
                str(target_root),
                "--project-slug",
                "sample_api",
                "--project-name",
                "Sample API",
                "--harness",
                "codex",
                "--harness",
                "opencode",
                "--copy-core-docs",
            ]
        )
        generated = payload["generated_files"]
        for key in ("readme", "project_profile", "workflow_state", "session_handoff", "work_backlog", "daily_backlog"):
            assert_exists(str(generated[key]))

        copied_core_docs = payload["copied_core_docs"]
        if len(copied_core_docs) != 7:
            raise AssertionError("Expected seven copied core docs in new project mode.")
        for raw_path in copied_core_docs:
            assert_exists(str(raw_path))

        harness_files = payload["generated_harness_files"]
        snippet_candidates = payload["global_snippet_candidates"]
        for key in (
            "codex_agents",
            "codex_config_example",
            "opencode_config",
            "opencode_skill",
            "opencode_agent",
            "opencode_worker_agent",
            "opencode_doc_worker_agent",
            "opencode_code_worker_agent",
            "opencode_validation_worker_agent",
        ):
            assert_exists(str(harness_files[key]))
        for harness in ("codex", "opencode"):
            if harness not in snippet_candidates:
                raise AssertionError(f"Missing global snippet metadata for {harness}.")
            assert_exists(str(snippet_candidates[harness]["readme"]))
            assert_exists(str(snippet_candidates[harness]["snippet"]))

        readme_text = Path(str(generated["readme"])).read_text(encoding="utf-8")
        if "Sample API" not in readme_text:
            raise AssertionError("Generated README does not mention the project name.")
        if "사용자에게 직접 보이는 작업 보고" not in readme_text:
            raise AssertionError("Generated workflow README should include the Korean reporting rule.")

        profile_text = Path(str(generated["project_profile"])).read_text(encoding="utf-8")
        if "docs/operations/" not in profile_text:
            raise AssertionError("Generated profile did not include the default operations dir.")

        workflow_state = json.loads(Path(str(generated["workflow_state"])).read_text(encoding="utf-8"))
        if workflow_state["schema_version"] != "1":
            raise AssertionError("Generated workflow state should carry schema version 1.")
        if workflow_state["session"]["current_focus"] != "TASK-001 표준 AI 워크플로우 초기 도입":
            raise AssertionError("Generated workflow state should expose the current focus for fast agent reads.")

        handoff_text = Path(str(generated["session_handoff"])).read_text(encoding="utf-8")
        if "이 문서는 다음 세션이 바로 이어받는 데 필요한 핵심 사실만 간결하게 남긴다." not in handoff_text:
            raise AssertionError("Generated handoff should include the context-saving rule.")

        daily_backlog_text = Path(str(generated["daily_backlog"])).read_text(encoding="utf-8")
        if "작업 기록은 한국어를 기본으로 작성한다." not in daily_backlog_text:
            raise AssertionError("Generated daily backlog should include the Korean reporting rule.")


def check_existing_project_mode() -> None:
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
        payload = run_bootstrap(
            [
                "--target-root",
                str(target_root),
                "--project-slug",
                "existing_repo",
                "--project-name",
                "Existing Repo",
                "--adoption-mode",
                "existing",
                "--harness",
                "codex",
                "--copy-core-docs",
            ]
        )
        generated = payload["generated_files"]
        for key in (
            "readme",
            "project_profile",
            "workflow_state",
            "session_handoff",
            "work_backlog",
            "daily_backlog",
            "repository_assessment",
        ):
            assert_exists(str(generated[key]))

        if payload["adoption_mode"] != "existing":
            raise AssertionError("Expected existing adoption mode in payload.")
        if payload["harnesses"] != ["codex"]:
            raise AssertionError("Expected only the codex harness in existing project mode.")

        profile_text = Path(str(generated["project_profile"])).read_text(encoding="utf-8")
        if "npm install" not in profile_text:
            raise AssertionError("Existing project mode did not infer npm install.")
        if "docs/operations/" not in profile_text:
            raise AssertionError("Existing project mode did not infer docs/operations/.")

        harness_files = payload["generated_harness_files"]
        assert_exists(str(harness_files["codex_agents"]))
        assert_exists(str(harness_files["codex_config_example"]))
        snippet_candidates = payload["global_snippet_candidates"]
        if "codex" not in snippet_candidates:
            raise AssertionError("Missing codex global snippet metadata.")

        assessment_text = Path(str(generated["repository_assessment"])).read_text(encoding="utf-8")
        if "existing" not in assessment_text or "dev, test, test:smoke, test:unit" not in assessment_text:
            raise AssertionError("Repository assessment is missing inferred script details.")

        readme_text = Path(str(generated["readme"])).read_text(encoding="utf-8")
        if "내부 사고 과정과 중간 분류는 모델이 가장 효율적인 형태로 처리" not in readme_text:
            raise AssertionError("Existing project workflow README should include the context-saving rule.")


def check_opencode_only_mode() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        target_root = Path(tmpdir) / "opencode-only-repo"
        target_root.mkdir(parents=True, exist_ok=True)
        payload = run_bootstrap(
            [
                "--target-root",
                str(target_root),
                "--project-slug",
                "opencode_only",
                "--project-name",
                "OpenCode Only Repo",
                "--harness",
                "opencode",
                "--copy-core-docs",
            ]
        )
        if payload["harnesses"] != ["opencode"]:
            raise AssertionError("Expected only the opencode harness in opencode-only mode.")
        harness_files = payload["generated_harness_files"]
        generated = payload["generated_files"]
        for key in (
            "codex_agents",
            "opencode_config",
            "opencode_skill",
            "opencode_agent",
            "opencode_worker_agent",
            "opencode_doc_worker_agent",
            "opencode_code_worker_agent",
            "opencode_validation_worker_agent",
        ):
            assert_exists(str(harness_files[key]))
        snippet_candidates = payload["global_snippet_candidates"]
        if "opencode" not in snippet_candidates:
            raise AssertionError("Missing opencode global snippet metadata.")
        workflow_state = json.loads(Path(str(generated["workflow_state"])).read_text(encoding="utf-8"))
        if not workflow_state["next_documents"]:
            raise AssertionError("Generated workflow state should include next_documents.")

        agents_text = Path(str(harness_files["codex_agents"])).read_text(encoding="utf-8")
        if "사용자에게 직접 보이는 작업 보고" not in agents_text:
            raise AssertionError("AGENTS.md should include the Korean reporting rule.")
        if "ai-workflow/project/state.json" not in agents_text:
            raise AssertionError("AGENTS.md should direct agents to the workflow state cache.")

        skill_text = Path(str(harness_files["opencode_skill"])).read_text(encoding="utf-8")
        if "Write user-facing status updates, work reports, and document drafts in Korean by default." not in skill_text:
            raise AssertionError("OpenCode skill should include the Korean reporting rule.")
        if "ai-workflow/project/state.json" not in skill_text:
            raise AssertionError("OpenCode skill should read the workflow state cache.")

        agent_text = Path(str(harness_files["opencode_agent"])).read_text(encoding="utf-8")
        if "Write visible work reports, summaries, and document drafts in Korean by default." not in agent_text:
            raise AssertionError("OpenCode agent should include the Korean reporting rule.")
        if "read-mostly coordinator" not in agent_text:
            raise AssertionError("OpenCode orchestrator should describe the coordinator role.")
        if "ai-workflow/project/state.json" not in agent_text:
            raise AssertionError("OpenCode orchestrator should read the workflow state cache.")
        if "Do not call direct tools yourself. Use only task delegation" not in agent_text:
            raise AssertionError("OpenCode orchestrator should require task delegation instead of direct tool calls.")
        if "edit: deny" not in agent_text or "bash: deny" not in agent_text or "webfetch: deny" not in agent_text:
            raise AssertionError("OpenCode orchestrator should deny direct edit/bash/webfetch access.")
        if "Ask the user only when a missing decision is genuinely blocking" not in agent_text:
            raise AssertionError("OpenCode orchestrator should minimize user asks.")

        worker_text = Path(str(harness_files["opencode_worker_agent"])).read_text(encoding="utf-8")
        if "You are a workflow worker for this repository." not in worker_text:
            raise AssertionError("OpenCode worker agent should be generated.")
        if "Stay within the assigned file or task scope." not in worker_text:
            raise AssertionError("OpenCode worker should describe bounded execution.")
        if "edit: allow" not in worker_text or "bash: allow" not in worker_text or "webfetch: allow" not in worker_text:
            raise AssertionError("OpenCode worker should allow bounded execution without repeated asks.")
        if "Minimize asks during execution." not in worker_text:
            raise AssertionError("OpenCode worker should explicitly minimize asks.")

        doc_worker_text = Path(str(harness_files["opencode_doc_worker_agent"])).read_text(encoding="utf-8")
        if "document-focused workflow worker" not in doc_worker_text:
            raise AssertionError("OpenCode doc worker should be generated.")
        if "Minimize asks during execution" not in doc_worker_text:
            raise AssertionError("OpenCode doc worker should minimize asks.")

        code_worker_text = Path(str(harness_files["opencode_code_worker_agent"])).read_text(encoding="utf-8")
        if "implementation and build-focused workflow worker" not in code_worker_text:
            raise AssertionError("OpenCode code worker should be generated.")
        if "build-oriented checks" not in code_worker_text:
            raise AssertionError("OpenCode code worker should cover implementation/build verification work.")
        if "Minimize asks during execution." not in code_worker_text:
            raise AssertionError("OpenCode code worker should minimize asks.")

        validation_worker_text = Path(str(harness_files["opencode_validation_worker_agent"])).read_text(encoding="utf-8")
        if "validation-focused workflow worker" not in validation_worker_text:
            raise AssertionError("OpenCode validation worker should be generated.")
        if "Minimize asks during execution" not in validation_worker_text:
            raise AssertionError("OpenCode validation worker should minimize asks.")

        opencode_config_text = Path(str(harness_files["opencode_config"])).read_text(encoding="utf-8")
        opencode_config = json.loads(opencode_config_text)
        if "\"AGENTS.md\"" not in opencode_config_text:
            raise AssertionError("OpenCode config should continue to reference AGENTS.md.")
        if "state.json" not in opencode_config_text:
            raise AssertionError("OpenCode config should reference the workflow state cache.")
        if "model" in opencode_config or "provider" in opencode_config:
            raise AssertionError("OpenCode config should not set model/provider defaults.")
        if "permission" in opencode_config:
            raise AssertionError("OpenCode config should not override top-level permission defaults.")
        assert_exists(str(snippet_candidates["opencode"]["snippet"]))


def main() -> int:
    check_new_project_mode()
    check_existing_project_mode()
    check_opencode_only_mode()
    print("Bootstrap scaffold smoke check passed for new and existing project modes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
