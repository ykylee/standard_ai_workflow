#!/usr/bin/env python3
"""Verify checked-in read-only harness MCP examples stay aligned with descriptors."""

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
SCRIPT_PATH = SOURCE_ROOT / "scripts" / "generate_read_only_harness_mcp_examples.py"
EXAMPLES_PATH = SOURCE_ROOT / "schemas" / "read_only_harness_mcp_examples.json"

if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from scripts.generate_read_only_harness_mcp_examples import build_harness_mcp_examples
from workflow_kit.server.read_only_registry import build_transport_tool_descriptors


def main() -> int:
    checked_in = json.loads(EXAMPLES_PATH.read_text(encoding="utf-8"))
    runtime = build_harness_mcp_examples()
    if checked_in != runtime:
        raise AssertionError("Checked-in read_only_harness_mcp_examples.json is out of date.")

    completed = subprocess.run(
        [sys.executable, str(SCRIPT_PATH)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    script_output = json.loads(completed.stdout)
    if script_output != runtime:
        raise AssertionError("generate_read_only_harness_mcp_examples.py output does not match runtime output.")

    descriptors = build_transport_tool_descriptors()
    if checked_in["descriptor_target"] != descriptors["descriptor_target"]:
        raise AssertionError("Harness examples should preserve descriptor target.")
    # 예전에는 `transport_ready=false` 를 요구했다. 그 플래그는 능력·단계·정책을
    # 한 boolean 에 섞고 있어 판정 불가였고 §6.2 로 제거됐다 — 이제 근거는
    # `transport_phase`(단계)와 per-harness `apply_mode`(정책) 두 축이다.
    if "transport_ready" in checked_in:
        raise AssertionError("transport_ready 는 제거된 필드다 (§6.2).")
    if checked_in.get("transport_phase") != "jsonrpc_draft":
        raise AssertionError("harness 예시는 transport_phase=jsonrpc_draft 를 밝혀야 한다.")
    if checked_in["tool_names"] != [tool["name"] for tool in descriptors["tools"]]:
        raise AssertionError("Harness examples should list descriptor tool names in registry order.")

    examples = checked_in["harness_examples"]
    for harness in ("codex", "opencode"):
        example = examples[harness]
        if example["apply_mode"] != "manual_review_only":
            raise AssertionError(f"{harness} example should be manual-review-only.")
        content = example["content"]
        if example["bridge_entrypoint"] != "workflow_kit.server.read_only_jsonrpc":
            raise AssertionError(f"{harness} example should name the JSON-RPC draft bridge.")
        if "apply_mode=manual_review_only" not in content:
            raise AssertionError(f"{harness} example 은 apply_mode 를 본문에 밝혀야 한다.")
        if "read_only_transport_descriptors.json" not in content:
            raise AssertionError(f"{harness} example should point back to the descriptor file.")
        if "workflow_kit.server.read_only_jsonrpc" not in content:
            raise AssertionError(f"{harness} example should name the current JSON-RPC draft bridge.")

    print("Read-only harness MCP example generation check passed.")
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
