#!/usr/bin/env python3
"""Smoke test the create_backlog_entry MCP prototype."""

from __future__ import annotations

#: 이 검사의 입력 표면 (spec `core/test_impact_tiering_spec.md` §2).
#: 게이트 채취 실측에서 뽑아 넓은 쪽으로 올렸다 — 좁으면 meta-watch 가 red 로 잡는다.
WATCHES = (
    "workflow-source/mcp_servers/create-backlog-entry/scripts/*",
    "workflow-source/mcp_servers/lib/*",
    "workflow-source/pyproject.toml",
    "workflow-source/workflow_kit/*",
)

import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
SCRIPT_PATH = SOURCE_ROOT / "mcp_servers" / "create-backlog-entry" / "scripts" / "run_create_backlog_entry.py"

if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from workflow_kit.common.output_contracts import validate_output_payload


def main() -> int:
    # ADR-027 M-004 이후 이 도구는 workspace 의 roadmap 게이트를 거친다. 이 검사가
    # 재는 것은 **초안 생성**이므로 roadmap 없는 임시 cwd 에서 돌린다 (게이트
    # 자체는 check_roadmap_gates 가 잰다) — repo cwd 로 돌리면 이 저장소의
    # 게이트가 정당하게 거부한다.
    import tempfile

    with tempfile.TemporaryDirectory() as neutral_cwd:
        completed = subprocess.run(
            [
                sys.executable,
                str(SCRIPT_PATH),
                "--task-id",
                "TASK-099",
                "--task-name",
                "출력 샘플 정리",
                "--request-date",
                "2026-04-20",
            ],
            cwd=neutral_cwd,
            capture_output=True,
            text=True,
            check=True,
        )
    payload = json.loads(completed.stdout)
    output_errors = validate_output_payload(payload, family="create_backlog_entry")
    if output_errors:
        raise AssertionError(f"create_backlog_entry payload violated output contract: {output_errors}")
    if not payload["draft_entry"]:
        raise AssertionError("Expected non-empty draft_entry lines.")
    if not payload["draft_entry"][0].startswith("## TASK-099"):
        raise AssertionError("Expected backlog heading to include the provided task id.")

    print("Create-backlog-entry smoke check passed.")
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
