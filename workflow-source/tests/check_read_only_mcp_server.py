#!/usr/bin/env python3
"""Smoke test the draft read-only MCP server entrypoint."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
ENTRYPOINT = SOURCE_ROOT / "workflow_kit" / "server" / "read_only_entrypoint.py"

if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from workflow_kit.common.output_contracts import output_json_schema_for_family, validate_output_payload
from workflow_kit.server.read_only_registry import WRITE_CAPABLE_TOOL_NAMES, get_tool_spec


def run_json(args: list[str], *, expect_success: bool = True) -> tuple[int, dict[str, object]]:
    completed = subprocess.run(
        [sys.executable, str(ENTRYPOINT), *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if expect_success and completed.returncode != 0:
        raise AssertionError(f"Entrypoint failed unexpectedly: {completed.stderr}\n{completed.stdout}")
    return completed.returncode, json.loads(completed.stdout)


def main() -> int:
    # v1.2.0 (2nd cycle, TASK-2026-08-13-main-005): `--bundle` 미지정 기본값이
    # read-only 다 — 기본 manifest 에 write 도구가 실리면 default flip 회귀다.
    _, manifest = run_json(["--list-tools"])
    if manifest["server_name"] != "workflow_read_only_bundle":
        raise AssertionError("Unexpected read-only server name.")
    if manifest["tool_count"] < 5:
        raise AssertionError("Expected at least five bundled read-only tools.")
    default_names = {tool["name"] for tool in manifest["tools"]}
    if default_names & WRITE_CAPABLE_TOOL_NAMES:
        raise AssertionError(
            "--bundle 미지정 기본값이 read-only 가 아니다 (v1.2.0 default flip 회귀): "
            f"{sorted(default_names & WRITE_CAPABLE_TOOL_NAMES)}"
        )
    if manifest["transport"]["descriptor_target"] != "mcp_tools_list_draft":
        raise AssertionError("Expected draft transport descriptor target in manifest.")
    for tool_spec in manifest["tools"]:
        tool_name = tool_spec["name"]
        output_schema = tool_spec["output_schema"]
        if output_schema["json_schema_draft"] != "2020-12":
            raise AssertionError(f"Expected {tool_name} generated JSON Schema draft metadata.")
        if output_schema["json_schema"] != output_json_schema_for_family(tool_name):
            raise AssertionError(f"Expected {tool_name} manifest JSON Schema to come from runtime contracts.")
        descriptor = tool_spec["transport_descriptor"]
        if descriptor["name"] != tool_name:
            raise AssertionError(f"Expected {tool_name} transport descriptor name to match tool name.")
        if descriptor["outputSchema"] != output_json_schema_for_family(tool_name):
            raise AssertionError(f"Expected {tool_name} transport descriptor output schema to come from runtime contracts.")
        # v1.1.7 (TASK-2026-08-11-main-024): readOnlyHint 는 registry 의 read_only
        # 선언과 일치해야 한다. 이전에는 전 도구에 True 를 요구해, 파일을 쓰는
        # 도구까지 read-only 로 광고되는 허위를 검사 스스로가 강제했다.
        spec = get_tool_spec(tool_name)
        if spec is None:
            raise AssertionError(f"Manifest tool {tool_name} is missing from the registry.")
        if descriptor["annotations"]["readOnlyHint"] is not spec.read_only:
            raise AssertionError(
                f"Expected {tool_name} readOnlyHint to match registry declaration ({spec.read_only})."
            )
        # 사실 목록 대조: write 도구는 정확히 WRITE_CAPABLE_TOOL_NAMES 여야 한다.
        # 새 write 도구가 read_only=True 로 광고되거나, read-only 도구가 write 로
        # 표시되면 여기서 잡힌다.
        if (tool_name in WRITE_CAPABLE_TOOL_NAMES) != (not spec.read_only):
            raise AssertionError(
                f"{tool_name}: read_only={spec.read_only} 가 WRITE_CAPABLE_TOOL_NAMES 사실 목록과 어긋난다."
            )
        # v1.1.7 (TASK-2026-08-11-main-025): manifest 가 광고하는 script_path 는
        # 실물이어야 한다 — rotate/milestone 2종이 registry 에만 등록되고
        # 디렉터리가 없어 유령 경로를 광고했고, 아무 검사도 resolve 하지 않았다.
        if not spec.script_path.is_file():
            raise AssertionError(f"{tool_name}: manifest 의 script_path 가 실물이 아니다: {spec.script_path}")

    _, transport_descriptors = run_json(["--list-transport-tools"])
    if transport_descriptors["descriptor_target"] != "mcp_tools_list_draft":
        raise AssertionError("Expected draft transport descriptor target.")
    if transport_descriptors["tool_count"] != manifest["tool_count"]:
        raise AssertionError("Expected transport descriptor tool_count to match manifest tool_count.")

    # v1.1.8+ bundle 분리 (TASK-2026-08-12-main-003): read-only 서버는 write 도구를
    # 싣지도, 부르지도 못해야 한다. 분리가 이름만 남으면 ADR-003 의 긴장이 재발한다.
    _, ro_manifest = run_json(["--list-tools", "--bundle", "read-only"])
    ro_names = {tool["name"] for tool in ro_manifest["tools"]}
    if ro_manifest["server_name"] != "workflow_read_only_bundle" or ro_names & WRITE_CAPABLE_TOOL_NAMES:
        raise AssertionError(f"read-only bundle 에 write 도구가 실렸다: {sorted(ro_names & WRITE_CAPABLE_TOOL_NAMES)}")
    _, w_manifest = run_json(["--list-tools", "--bundle", "write"])
    w_names = {tool["name"] for tool in w_manifest["tools"]}
    if w_manifest["server_name"] != "workflow_write_bundle" or w_names != set(WRITE_CAPABLE_TOOL_NAMES):
        raise AssertionError(f"write bundle 구성이 사실 목록과 다르다: {sorted(w_names)}")
    # all 은 v1.2.0 부터 명시 opt-in — 합집합 판정의 기준면도 명시 all 로 뜬다.
    _, all_manifest = run_json(["--list-tools", "--bundle", "all"])
    if ro_names | w_names != {tool["name"] for tool in all_manifest["tools"]}:
        raise AssertionError("read-only ∪ write ≠ all — bundle 분리가 도구를 흘리거나 중복시켰다.")
    blocked_code, blocked_payload = run_json(
        ["--tool", "apply_robust_patch", "--payload-json", "{}", "--bundle", "read-only"],
        expect_success=False,
    )
    if blocked_code == 0 or blocked_payload.get("error_code") != "unknown_read_only_tool":
        raise AssertionError("read-only bundle 이 write 도구 호출을 막지 못했다.")

    latest_backlog_spec = next((tool for tool in manifest["tools"] if tool["name"] == "latest_backlog"), None)
    if latest_backlog_spec is None:
        raise AssertionError("Expected latest_backlog tool in manifest.")
    if "input_schema" not in latest_backlog_spec:
        raise AssertionError("Expected input_schema in read-only tool manifest.")
    if latest_backlog_spec["input_schema"]["requires_any_of"] != ["backlog_dir_path", "work_backlog_index_path"]:
        raise AssertionError("Expected latest_backlog any-of schema requirements.")
    if latest_backlog_spec["bundle_phase"] != "direct_call_adapter":
        raise AssertionError("Expected direct_call_adapter bundle phase.")
    if latest_backlog_spec["output_schema"]["success_required_keys"] != ["candidates", "latest_backlog_path"]:
        raise AssertionError("Expected latest_backlog success output schema.")
    if latest_backlog_spec["output_schema"]["error_required_keys"] != ["error", "error_code", "source_context"]:
        raise AssertionError("Expected latest_backlog error output schema.")
    if latest_backlog_spec["output_schema"]["json_schema"]["properties"]["status"]["enum"] != [
        "ok",
        "warning",
        "error",
    ]:
        raise AssertionError("Expected latest_backlog manifest JSON Schema status enum to include ok/warning/error.")
    latest_backlog_shape = latest_backlog_spec["output_schema"]["field_shapes"]["latest_backlog_path"]
    if latest_backlog_shape["kind"] != "string" or not latest_backlog_shape["allow_null"]:
        raise AssertionError("Expected nullable string shape for latest_backlog_path.")
    candidates_shape = latest_backlog_spec["output_schema"]["field_shapes"]["candidates"]
    if candidates_shape["kind"] != "list" or candidates_shape["item_kind"] != "string":
        raise AssertionError("Expected list[string] shape for latest_backlog candidates.")
    if not latest_backlog_spec["payload_example"]:
        raise AssertionError("Expected payload example in read-only tool manifest.")
    latest_transport = next((tool for tool in transport_descriptors["tools"] if tool["name"] == "latest_backlog"), None)
    if latest_transport is None:
        raise AssertionError("Expected latest_backlog transport descriptor.")
    if latest_transport["inputSchema"]["anyOf"] != [
        {"required": ["backlog_dir_path"]},
        {"required": ["work_backlog_index_path"]},
    ]:
        raise AssertionError("Expected latest_backlog transport descriptor anyOf input requirements.")

    latest_backlog_payload = {
        "work_backlog_index_path": str(SOURCE_ROOT / "examples" / "acme_delivery_platform" / "work_backlog.md")
    }
    _, latest_backlog = run_json(
        ["--tool", "latest_backlog", "--payload-json", json.dumps(latest_backlog_payload, ensure_ascii=False)]
    )
    if latest_backlog["status"] != "ok":
        raise AssertionError("Expected latest_backlog tool dispatch to succeed.")
    if not latest_backlog["latest_backlog_path"]:
        raise AssertionError("Expected latest_backlog tool dispatch to return a path.")

    metadata_payload = {
        "doc_dir_path": str(SOURCE_ROOT / "examples" / "acme_delivery_platform")
    }
    _, metadata_result = run_json(
        ["--tool", "check_doc_metadata", "--payload-json", json.dumps(metadata_payload, ensure_ascii=False)]
    )
    if metadata_result["status"] != "ok":
        raise AssertionError("Expected check_doc_metadata dispatch to succeed.")
    if "checked_files" not in metadata_result:
        raise AssertionError("Expected check_doc_metadata dispatch to return checked_files.")
    if any(not isinstance(path, str) for path in metadata_result["checked_files"]):
        raise AssertionError("Expected check_doc_metadata checked_files to be list[str].")
    if any(
        not isinstance(item, dict) or "path" not in item or "missing_fields" not in item
        for item in metadata_result["missing_metadata"]
    ):
        raise AssertionError("Expected check_doc_metadata missing_metadata items to match object shape.")

    schema_failure_code, schema_failure_payload = run_json(
        ["--tool", "check_doc_metadata", "--payload-json", json.dumps({}, ensure_ascii=False)],
        expect_success=False,
    )
    if schema_failure_code == 0:
        raise AssertionError("Expected schema-invalid payload dispatch to fail.")
    if schema_failure_payload["error_code"] != "invalid_tool_payload_schema":
        raise AssertionError("Expected invalid_tool_payload_schema error code.")
    if validate_output_payload(schema_failure_payload, family="read_only_entrypoint"):
        raise AssertionError("Expected schema failure payload to match read_only_entrypoint output contract.")
    if schema_failure_payload["source_context"]["action"] != "tool":
        raise AssertionError("Expected schema failure source_context action to be tool.")
    if "allowed_fields" not in schema_failure_payload["source_context"]:
        raise AssertionError("Expected schema failure source_context to include allowed_fields.")

    missing_path_code, missing_path_payload = run_json(
        ["--tool", "check_doc_metadata", "--payload-json", json.dumps({"doc_dir_path": "/tmp/does-not-exist"}, ensure_ascii=False)],
        expect_success=False,
    )
    if missing_path_code == 0:
        raise AssertionError("Expected missing path dispatch to fail.")
    if missing_path_payload["error_code"] != "missing_tool_input_path":
        raise AssertionError("Expected missing_tool_input_path error code.")
    if validate_output_payload(missing_path_payload, family="read_only_entrypoint"):
        raise AssertionError("Expected missing path payload to match read_only_entrypoint output contract.")

    failure_code, failure_payload = run_json(["--tool", "unknown_tool", "--payload-json", "{}"], expect_success=False)
    if failure_code == 0:
        raise AssertionError("Expected unknown tool dispatch to fail.")
    if failure_payload["error_code"] != "unknown_read_only_tool":
        raise AssertionError("Expected unknown_read_only_tool error code.")
    if validate_output_payload(failure_payload, family="read_only_entrypoint"):
        raise AssertionError("Expected unknown tool payload to match read_only_entrypoint output contract.")

    missing_action_code, missing_action_payload = run_json([], expect_success=False)
    if missing_action_code == 0:
        raise AssertionError("Expected missing action dispatch to fail.")
    if missing_action_payload["error_code"] != "missing_server_action":
        raise AssertionError("Expected missing_server_action error code.")
    if validate_output_payload(missing_action_payload, family="read_only_entrypoint"):
        raise AssertionError("Expected missing action payload to match read_only_entrypoint output contract.")

    print("Read-only MCP server smoke check passed.")
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
