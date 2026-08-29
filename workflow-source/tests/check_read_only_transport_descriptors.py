#!/usr/bin/env python3
"""Verify checked-in read-only transport descriptors stay aligned with registry output."""

from __future__ import annotations

#: 이 검사의 입력 표면 (spec `core/test_impact_tiering_spec.md` §2).
#: 게이트 채취 실측에서 뽑아 넓은 쪽으로 올렸다 — 좁으면 meta-watch 가 red 로 잡는다.
WATCHES = (
    "workflow-source/pyproject.toml",
    "workflow-source/schemas/*",
    "workflow-source/scripts/*",
    "workflow-source/workflow_kit/*",
)

import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
SCRIPT_PATH = SOURCE_ROOT / "scripts" / "generate_read_only_transport_descriptors.py"
DESCRIPTOR_PATH = SOURCE_ROOT / "schemas" / "read_only_transport_descriptors.json"

if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from workflow_kit.common.output_contracts import output_json_schema_for_family
from workflow_kit.server.read_only_registry import build_transport_tool_descriptors


def main() -> int:
    checked_in = json.loads(DESCRIPTOR_PATH.read_text(encoding="utf-8"))
    runtime = build_transport_tool_descriptors()
    if checked_in != runtime:
        raise AssertionError("Checked-in read_only_transport_descriptors.json is out of date with registry output.")

    completed = subprocess.run(
        [sys.executable, str(SCRIPT_PATH)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    script_output = json.loads(completed.stdout)
    if script_output != runtime:
        raise AssertionError("generate_read_only_transport_descriptors.py output does not match registry output.")

    if checked_in["descriptor_target"] != "mcp_tools_list_draft":
        raise AssertionError("Expected mcp_tools_list_draft descriptor target.")
    # registry 는 transport 사실을 선언하지 않는다 (§1.3 세 축). 예전에는
    # `transport_ready=false` 를 요구했는데, registry 는 어느 bridge 가 자기를
    # 서빙할지 모르므로 그 필드는 참·거짓을 가릴 명제가 아니었다.
    if "transport_ready" in checked_in:
        raise AssertionError("registry descriptor 는 transport_ready 를 내지 않아야 한다 (§1.3).")

    latest_backlog = next((tool for tool in checked_in["tools"] if tool["name"] == "latest_backlog"), None)
    if latest_backlog is None:
        raise AssertionError("Expected latest_backlog descriptor.")
    if latest_backlog["outputSchema"] != output_json_schema_for_family("latest_backlog"):
        raise AssertionError("Expected latest_backlog outputSchema to come from runtime output contract.")
    if latest_backlog["inputSchema"].get("anyOf") != [
        {"required": ["backlog_dir_path"]},
        {"required": ["work_backlog_index_path"]},
    ]:
        raise AssertionError("Expected latest_backlog descriptor to preserve anyOf input requirements.")

    print("Read-only transport descriptor generation check passed.")
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
