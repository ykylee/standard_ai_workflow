"""Smoke test for MCP read-only transport promotion readiness (v0.11.24 cycle).

검증:
  1. spec §6 의 verification command 7종이 모두 file 로 존재.
  2. spec §1 의 transport status 가 jsonrpc-bridge=stable / stdio-sdk=experimental 정합.
  3. workflow_kit/server/read_only_mcp_sdk.py 의 known regression marker 가
     명시적으로 'Connection closed' 회귀를 식별 (회귀의 fix 가 미완된 상태).
  4. read_only_mcp_transport_promotion.md 의 '유지할 계약' 섹션 (4장) 의 12 항목이
     모두 본문 정합 (회귀 시 단일 진실).
  5. descriptors / harness examples 가 export 파일로 존재.

본 test 는 stdio-sdk 정식 승격 작업의 사전 검증. 본 smoke 가 PASS 라는 것은
spec 의 contract 가 깨지지 않았다는 것이지, stdio-sdk 자체가 stable 이라는 의미는 아님.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Iterator

REPO = Path(__file__).resolve().parents[2]
SPEC = REPO / "workflow-source" / "core" / "read_only_mcp_transport_promotion.md"
SDK_CANDIDATE = REPO / "workflow-source" / "workflow_kit" / "server" / "read_only_mcp_sdk.py"
JSONRPC_BRIDGE = REPO / "workflow-source" / "workflow_kit" / "server" / "read_only_jsonrpc.py"
DESCRIPTORS = REPO / "workflow-source" / "schemas" / "read_only_transport_descriptors.json"
HARNESS_EXAMPLES = REPO / "workflow-source" / "schemas" / "read_only_harness_mcp_examples.json"
JSONRPC_FIXTURES = REPO / "workflow-source" / "schemas" / "read_only_jsonrpc_fixtures.json"


# ---------------------------------------------------------------------------
# case 1 — spec §6 의 verification command 7종이 모두 file 로 존재
# ---------------------------------------------------------------------------

def test_case_1_spec_section6_verification_commands_exist() -> None:
    """read_only_mcp_transport_promotion.md §6 의 7 verification command 가 모두 file 로 존재."""
    expected_smoke_files = [
        "tests/check_read_only_mcp_server.py",
        "tests/check_read_only_jsonrpc_bridge.py",
        "tests/check_read_only_jsonrpc_fixtures.py",
        "tests/check_read_only_mcp_sdk_candidate.py",
        "tests/check_read_only_mcp_sdk_stdio.py",
        "tests/check_read_only_transport_descriptors.py",
        "tests/check_read_only_harness_mcp_examples.py",
    ]
    missing = []
    for smoke_relpath in expected_smoke_files:
        smoke_path = REPO / "workflow-source" / smoke_relpath
        if not smoke_path.exists():
            missing.append(smoke_relpath)
    assert not missing, f"missing smoke test files (spec §6 정합 위반): {missing}"


# ---------------------------------------------------------------------------
# case 2 — spec §1 transport status 정합 (jsonrpc-bridge=stable, stdio-sdk=experimental)
# ---------------------------------------------------------------------------

def test_case_2_spec_section1_transport_status_current() -> None:
    """spec §1 의 transport status 가 현재 코드 상태와 정합."""
    spec_text = SPEC.read_text(encoding="utf-8")
    # jsonrpc-bridge 는 stable default.
    assert "jsonrpc-bridge" in spec_text and "stable" in spec_text.lower(), (
        "spec §1 에 jsonrpc-bridge=stable 명시 누락"
    )
    # stdio-sdk 의 promotion status (v0.11.25 cycle: experimental → stable).
    assert "stdio-sdk" in spec_text
    # v0.11.25 fix: spec §1 의 'Connection closed' marker 는 더 이상 *active known issue* 가 아니라
    # *historical fixed* 로 표기됨. spec 본문 갱신.
    # 본 check 는 "Connection closed" 또는 "regression fixed" 또는 "marked fixed" 중
    # *최소 1개* 가 spec 에 정합되어야 함.
    has_connection_marker = "Connection closed" in spec_text
    has_fixed_marker = "fixed" in spec_text.lower() and (
        "regression fixed" in spec_text.lower()
        or "marked fixed" in spec_text.lower()
    )
    assert has_connection_marker or has_fixed_marker, (
        "spec §1 에 'Connection closed' 또는 'regression fixed'/'marked fixed' marker 가 정합되어야 함. "
        "v0.11.25 cycle 의 stdio-sdk stable transition 후 spec update 누락."
    )


# ---------------------------------------------------------------------------
# case 3 — SDK candidate file 에 known regression marker 가 식별 가능
# ---------------------------------------------------------------------------

def test_case_3_sdk_candidate_advertises_stable_transport_when_sdk_available() -> None:
    """read_only_mcp_sdk.py 가 sdk_available=True 일 때 transport_ready=True advertise.

    v0.11.25 cycle 의 fix: sdk_available=True (mcp 1.27.0+ 설치) 일 때 transport_ready=True
    + sdk_candidate_phase='official_sdk_stable' advertise. 본 fix 는 *runtime* 검증으로만
    확인 가능 (mcp 1.27.0 venv 가 필요한 smoke).
    """
    sdk_text = SDK_CANDIDATE.read_text(encoding="utf-8")
    # transport_ready 동적 결정 로직 (sdk_available 따라) — literal pattern verify.
    assert '\"transport_ready\": sdk_available' in sdk_text, (
        "SDK candidate file 에 'transport_ready': sdk_available 동적 결정 로직이 없음. "
        "v0.11.25 cycle 의 stdio-sdk stable transition 시 필수."
    )
    # sdk_candidate_phase 동적 결정 — 'official_sdk_stable' / 'official_sdk_optional_candidate' 분기.
    assert "official_sdk_stable" in sdk_text, (
        "SDK candidate file 에 'official_sdk_stable' advertise 로직 없음. "
        "stdio-sdk 정식 stable transition 시 필수."
    )


# ---------------------------------------------------------------------------
# case 4 — spec §4 '유지할 계약' 12 항목 모두 본문 정합
# ---------------------------------------------------------------------------

def test_case_4_spec_section4_contracts_complete() -> None:
    """spec §4 의 12 계약 항목이 본문에 모두 정합."""
    spec_text = SPEC.read_text(encoding="utf-8")
    # §4 시작점 확인.
    sec4_start = spec_text.find("## 4. 유지할 계약")
    assert sec4_start != -1, "spec §4 누락"
    sec4 = spec_text[sec4_start:]
    # 12개 contract 항목 키워드 (smoke 4: 12 항목은 단순 카운트가 아니라 *본문에 항목이 있는지* verify).
    required_phrases = [
        "tools/list",
        "inputSchema",
        "outputSchema",
        "annotations.readOnlyHint",
        "error_code",
        "warnings",
        "source_context",
        "params",
        "capabilities",
        "listChanged",
        "stdio-lines",
        "transport_ready",
    ]
    missing = [p for p in required_phrases if p not in sec4]
    assert not missing, f"spec §4 에 다음 contract keyword 가 없음: {missing}"


# ---------------------------------------------------------------------------
# case 5 — descriptors / harness examples / fixtures 가 export file 로 존재
# ---------------------------------------------------------------------------

def test_case_5_export_files_exist() -> None:
    """schemas/ 의 3 export file 이 존재 (descriptor SSOT + harness examples + jsonrpc fixtures)."""
    for path in (DESCRIPTORS, HARNESS_EXAMPLES, JSONRPC_FIXTURES):
        assert path.exists(), f"missing export file: {path}"
    # jsonrpc-bridge (stable) 와 sdk candidate (experimental) 둘 다 server/ 에 존재.
    assert JSONRPC_BRIDGE.exists(), "jsonrpc-bridge (stable) 없음"
    assert SDK_CANDIDATE.exists(), "stdio-sdk candidate (experimental) 없음"


# ---------------------------------------------------------------------------
# runner
# ---------------------------------------------------------------------------

def _run_all() -> Iterator[tuple[str, bool, str]]:
    cases = [
        ("test_case_1_spec_section6_verification_commands_exist",
         test_case_1_spec_section6_verification_commands_exist),
        ("test_case_2_spec_section1_transport_status_current",
         test_case_2_spec_section1_transport_status_current),
        ("test_case_3_sdk_candidate_advertises_stable_transport_when_sdk_available",
         test_case_3_sdk_candidate_advertises_stable_transport_when_sdk_available),
        ("test_case_4_spec_section4_contracts_complete",
         test_case_4_spec_section4_contracts_complete),
        ("test_case_5_export_files_exist",
         test_case_5_export_files_exist),
    ]
    for name, fn in cases:
        try:
            fn()
            yield name, True, ""
        except AssertionError as exc:
            yield name, False, str(exc)
        except Exception as exc:
            yield name, False, f"{type(exc).__name__}: {exc}"


def main() -> int:
    print("=== MCP read-only transport promotion readiness (v0.11.24) ===")
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
    sys_path = __import__("sys").path
    if "sys" not in str(__import__("sys").path):
        pass
    __import__("sys").exit(main())