"""Read-only MCP manifest outputSchema byte-identical assertion test (v0.8.10+).

Spec v0.8.0 §9 #6:
    [ ] read-only MCP manifest / descriptor 의 outputSchema 가 generated schema 와
        byte-identical (assertion test)

This test verifies the assertion:
- For each tool in `read_only_transport_descriptors.json`, the `outputSchema` field
  must be byte-identical to the corresponding entry in
  `schemas/generated_output_schemas.json`'s `outputs` section.

이전에는 모델 없는 4 family(summarize_git_history / rotate_workflow_logs /
assess_milestone_progress / apply_robust_patch)의 generic fallback 을 *기대값*으로 고정했다.
그 fallback 은 결함이었다 — family 가 없으면 invoke_tool 이 성공 응답을 `Unknown family` 로 죽인다
(TASK-2026-11-04-main-002). 이제 모든 도구가 모델을 갖고, generic fallback 이 하나라도 나오면 red 다.

Pass criteria (4 tests):
1. Every descriptor tool (registry count) has an `outputSchema` field
2. Every tool has byte-identical `outputSchema` to gen.outputs[name]
3. No descriptor tool uses the generic "unmodeled family" fallback
4. No descriptor tool is missing from gen.outputs (drift check)
"""
from __future__ import annotations

#: 이 검사의 입력 표면 (spec `core/test_impact_tiering_spec.md` §2).
#: 게이트 채취 실측에서 뽑아 넓은 쪽으로 올렸다 — 좁으면 meta-watch 가 red 로 잡는다.
WATCHES = (
    "workflow-source/schemas/*",
    # 도구 수를 registry 에서 파생한다 — registry 를 import 하면 패키지 전체가 입력이다.
    "workflow-source/pyproject.toml",
    "workflow-source/workflow_kit/*",
)

import json
import sys
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[1]
DESCRIPTOR = SOURCE_ROOT / "schemas" / "read_only_transport_descriptors.json"
GENERATED = SOURCE_ROOT / "schemas" / "generated_output_schemas.json"

# 모델 없는 family 는 허용하지 않는다 — 비어 있어야 한다 (TASK-2026-11-04-main-002).
UNMODELED_FAMILIES: frozenset[str] = frozenset()

GENERIC_SCHEMA_PATTERN: dict[str, object] = {
    "description": "Generic schema for unmodeled family '{family}'.",
    "type": "object",
}


def _load_json(path: Path) -> dict[str, object]:
    with path.open(encoding="utf-8") as fh:
        result: dict[str, object] = json.load(fh)
    return result


def _expected_generic_schema(family: str) -> dict[str, object]:
    """The descriptor-side generic schema for an unmodeled family.

    Note: the description is filled in per family, not a literal string template.
    """
    return {
        "description": f"Generic schema for unmodeled family '{family}'.",
        "type": "object",
    }


def test_descriptor_tools_have_output_schema_v0_8_10() -> None:
    """Every descriptor tool has an outputSchema field (v0.8.10+).

    도구 수는 registry 에서 파생한다 — 손으로 적은 13 은 도구를 더할 때마다 낡는 사본이었다 (M-029 MCP 두 도구).
    """
    from workflow_kit.server.read_only_registry import BUNDLE_ALL, tool_specs_for_bundle

    desc = _load_json(DESCRIPTOR)
    tools = desc.get("tools", [])
    assert isinstance(tools, list)
    expected = len(tool_specs_for_bundle(BUNDLE_ALL))
    assert len(tools) == expected, f"expected {expected} descriptor tools (registry), got {len(tools)}"
    for tool in tools:
        name = tool.get("name", "<unnamed>")
        assert "outputSchema" in tool, f"tool {name!r} missing outputSchema"


def test_modeled_tools_byte_identical_v0_8_10() -> None:
    """Modeled descriptor tools have byte-identical outputSchema vs gen.outputs (v0.8.10+)."""
    desc = _load_json(DESCRIPTOR)
    gen = _load_json(GENERATED)
    gen_outputs = gen.get("outputs", {})
    assert isinstance(gen_outputs, dict)
    tools = desc.get("tools", [])
    assert isinstance(tools, list)

    mismatches: list[str] = []
    for tool in tools:
        name = tool.get("name", "<unnamed>")
        if name in UNMODELED_FAMILIES:
            continue  # unmodeled — checked in test_unmodeled_tools_use_generic_schema
        desc_output = tool.get("outputSchema")
        gen_output = gen_outputs.get(name)
        if gen_output is None:
            mismatches.append(
                f"{name}: missing in generated.outputs (descriptor has schema but contract not modeled)"
            )
            continue
        if desc_output != gen_output:
            mismatches.append(f"{name}: descriptor outputSchema != gen.outputs[{name!r}]")
    if mismatches:
        raise AssertionError(
            f"{len(mismatches)} modeled tool(s) NOT byte-identical:\n  "
            + "\n  ".join(mismatches)
        )


def test_unmodeled_tools_use_generic_schema_v0_8_10() -> None:
    """No descriptor tool falls back to the generic "unmodeled family" schema.

    generic fallback 은 family 미등록의 표지다 — 그 도구의 성공 응답은 invoke_tool 에서 죽는다.
    """
    assert not UNMODELED_FAMILIES, f"모델 없는 family 예외가 다시 생겼다: {sorted(UNMODELED_FAMILIES)}"
    desc = _load_json(DESCRIPTOR)
    tools = desc.get("tools", [])
    assert isinstance(tools, list)
    generic = [
        tool.get("name") for tool in tools
        if tool.get("outputSchema") == _expected_generic_schema(str(tool.get("name")))
    ]
    assert not generic, f"generic fallback outputSchema 를 쓰는 도구: {generic}"


def test_no_descriptor_orphans_v0_8_10() -> None:
    """Descriptor tools must have a corresponding gen.outputs contract (no orphans, v0.8.10+).

    The reverse direction (gen.outputs superset of descriptor) is *expected* — the
    descriptor is a subset (read-only bundle). Only check the descriptor → gen
    direction: each descriptor tool that *claims* an outputSchema must have a
    matching gen.outputs contract (or be marked as unmodeled).
    """
    desc = _load_json(DESCRIPTOR)
    gen = _load_json(GENERATED)
    gen_outputs = gen.get("outputs", {})
    assert isinstance(gen_outputs, dict)
    tools = desc.get("tools", [])
    assert isinstance(tools, list)

    orphans: list[str] = []
    for tool in tools:
        name = tool.get("name", "<unnamed>")
        if name in UNMODELED_FAMILIES:
            continue  # unmodeled — generic schema acceptable
        if name not in gen_outputs:
            orphans.append(name)
    if orphans:
        raise AssertionError(
            f"{len(orphans)} descriptor tool(s) missing gen.outputs contract: "
            + ", ".join(orphans)
        )


def main() -> int:
    test_funcs = [
        test_descriptor_tools_have_output_schema_v0_8_10,
        test_modeled_tools_byte_identical_v0_8_10,
        test_unmodeled_tools_use_generic_schema_v0_8_10,
        test_no_descriptor_orphans_v0_8_10,
    ]
    failed: list[str] = []
    for fn in test_funcs:
        name = fn.__name__
        try:
            fn()
            print(f"  PASS  {name}")
        except Exception as e:
            print(f"  FAIL  {name}: {type(e).__name__}: {e}")
            failed.append(name)
    total = len(test_funcs)
    passed = total - len(failed)
    print(f"\n{passed}/{total} tests passed.")
    if failed:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
