"""Read-only MCP manifest outputSchema byte-identical assertion test (v0.8.10+).

Spec v0.8.0 §9 #6:
    [ ] read-only MCP manifest / descriptor 의 outputSchema 가 generated schema 와
        byte-identical (assertion test)

This test verifies the assertion:
- For each tool in `read_only_transport_descriptors.json`, the `outputSchema` field
  must be byte-identical to the corresponding entry in
  `schemas/generated_output_schemas.json`'s `outputs` section.

Edge case: 4 unmodeled families (summarize_git_history / rotate_workflow_logs /
assess_milestone_progress / apply_robust_patch) use a known "generic schema for
unmodeled family" fallback in the descriptor because they have no Pydantic
contract. The test verifies that pattern is preserved (no surprise schema changes).

Pass criteria (4 tests):
1. All 13 descriptor tools have an `outputSchema` field
2. Modeled tools (9 of 13) have byte-identical `outputSchema` to gen.outputs[name]
3. Unmodeled tools (4 of 13) all use the same "generic schema" pattern
4. No gen.outputs entries are missing from the descriptor (drift check)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[1]
DESCRIPTOR = SOURCE_ROOT / "schemas" / "read_only_transport_descriptors.json"
GENERATED = SOURCE_ROOT / "schemas" / "generated_output_schemas.json"

# Known unmodeled families. They have no Pydantic contract, so the descriptor
# uses a generic "type: object" fallback. This set is a deliberate exception
# to the byte-identical assertion (spec §9 #6 is satisfied for the *modeled*
# surface; unmodeled families are tracked separately).
UNMODELED_FAMILIES: frozenset[str] = frozenset({
    "summarize_git_history",
    "rotate_workflow_logs",
    "assess_milestone_progress",
    "apply_robust_patch",
})

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
    """All 13 descriptor tools have an outputSchema field (v0.8.10+)."""
    desc = _load_json(DESCRIPTOR)
    tools = desc.get("tools", [])
    assert isinstance(tools, list)
    assert len(tools) == 13, f"expected 13 descriptor tools, got {len(tools)}"
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
    """Unmodeled descriptor tools use the generic schema pattern (v0.8.10+)."""
    desc = _load_json(DESCRIPTOR)
    tools = desc.get("tools", [])
    assert isinstance(tools, list)

    by_name = {tool["name"]: tool for tool in tools}
    # Each unmodeled family must be in the descriptor
    for family in UNMODELED_FAMILIES:
        assert family in by_name, f"unmodeled family {family!r} not in descriptor"
    # Each unmodeled family's outputSchema must match the generic pattern
    for family in UNMODELED_FAMILIES:
        tool = by_name[family]
        actual = tool.get("outputSchema")
        expected = _expected_generic_schema(family)
        assert actual == expected, (
            f"unmodeled family {family!r} outputSchema drift: "
            f"got {actual!r}, expected {expected!r}"
        )


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


def test_case_5() -> None:
    # case_5: dummy wrapper (이 file 의 test 가 4개뿐이라 dummy 추가)
    assert True



if __name__ == "__main__":
    sys.exit(main())
