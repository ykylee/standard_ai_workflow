"""Main entry point for output contracts, re-exporting modularized definitions."""

from __future__ import annotations

from workflow_kit.common.contracts.base import (
    COMMON_REQUIRED_KEYS,
    OutputFieldShape,
    output_field_shape_to_schema,
    json_schema_for_shape as _json_schema_for_shape,
)
from workflow_kit.common.contracts.read_only import (
    READ_ONLY_SUCCESS_CONTRACTS,
    READ_ONLY_FIELD_SHAPES,
)
from workflow_kit.common.contracts.high_value import (
    HIGH_VALUE_SUCCESS_CONTRACTS,
    HIGH_VALUE_FIELD_SHAPES,
)
from workflow_kit.common.contracts.errors import (
    ERROR_SUCCESS_CONTRACTS,
    ERROR_FIELD_SHAPES,
)

SUCCESS_PATH_CONTRACTS: dict[str, frozenset[str]] = {
    **READ_ONLY_SUCCESS_CONTRACTS,
    **HIGH_VALUE_SUCCESS_CONTRACTS,
}

ERROR_PATH_CONTRACTS: dict[str, frozenset[str]] = ERROR_SUCCESS_CONTRACTS

OUTPUT_FIELD_SHAPES: dict[str, dict[str, OutputFieldShape]] = {
    **READ_ONLY_FIELD_SHAPES,
    **HIGH_VALUE_FIELD_SHAPES,
}

ERROR_OUTPUT_FIELD_SHAPES: dict[str, dict[str, OutputFieldShape]] = ERROR_FIELD_SHAPES


def required_output_keys(family: str, *, status: str) -> frozenset[str]:
    """Return required keys for a payload family and status."""
    if status == "error":
        return COMMON_REQUIRED_KEYS | ERROR_PATH_CONTRACTS.get(family, frozenset())
    return COMMON_REQUIRED_KEYS | SUCCESS_PATH_CONTRACTS.get(family, frozenset())


def validate_output_payload(payload: dict[str, object], *, family: str) -> list[str]:
    """Validate a payload against the shared output contracts."""
    errors: list[str] = []
    status = str(payload.get("status") or "")
    if status not in {"ok", "warning", "error"}:
        errors.append("`status` 는 `ok`, `warning`, `error` 중 하나여야 한다.")
        return errors

    required_keys = required_output_keys(family, status=status)
    for key in sorted(required_keys):
        if key not in payload:
            errors.append(f"`{family}` output 에 `{key}` 필드가 없다.")
    
    errors.extend(validate_output_payload_shape(payload, family=family, status=status))
    return errors


def output_json_schema_bundle() -> dict[str, dict[str, object]]:
    """Return a bundle of all output and error schemas."""
    return {
        "outputs": output_field_shapes_schema(),
        "errors": output_error_field_shapes_schema(),
    }


def output_json_schema_for_family(family: str) -> dict[str, object]:
    """Return a single JSON schema representing the full output for a family."""
    shapes = OUTPUT_FIELD_SHAPES.get(family, {})
    required_keys = required_output_keys(family, status="ok")
    
    properties = {
        field_name: _json_schema_for_shape(shape)
        for field_name, shape in sorted(shapes.items())
    }
    
    # Add common status/tool_version/warnings
    properties.update({
        "status": {"type": "string", "enum": ["ok", "warning", "error"]},
        "tool_version": {"type": "string"},
        "warnings": {"type": "array", "items": {"type": "string"}}
    })

    return {
        "type": "object",
        "required": sorted(required_keys),
        "properties": properties
    }


def validate_output_payload_shape(
    payload: dict[str, object], *, family: str, status: str
) -> list[str]:
    """Validate the types and nested structure of a payload."""
    errors: list[str] = []
    shapes = ERROR_OUTPUT_FIELD_SHAPES if status == "error" else OUTPUT_FIELD_SHAPES
    family_shapes = shapes.get(family, {})

    for field_name, shape in family_shapes.items():
        if field_name not in payload:
            continue
        value = payload[field_name]
        errors.extend(_validate_field_shape(value, shape, f"{family}.{field_name}"))
    return errors


def _validate_field_shape(value: object, shape: OutputFieldShape, context: str) -> list[str]:
    errors: list[str] = []
    if value is None:
        if not shape.allow_null:
            errors.append(f"`{context}` 는 null 일 수 없다.")
        return errors

    if shape.kind == "string" and not isinstance(value, str):
        errors.append(f"`{context}` 는 string 이어야 한다.")
    elif shape.kind == "boolean" and not isinstance(value, bool):
        errors.append(f"`{context}` 는 boolean 이어야 한다.")
    elif shape.kind == "integer" and not isinstance(value, int):
        errors.append(f"`{context}` 는 integer 이어야 한다.")
    elif shape.kind == "list":
        if not isinstance(value, list):
            errors.append(f"`{context}` 는 list 이어야 한다.")
        elif shape.item_kind:
            for idx, item in enumerate(value):
                item_context = f"{context}[{idx}]"
                if shape.item_kind == "string" and not isinstance(item, str):
                    errors.append(f"`{item_context}` 는 string 이어야 한다.")
                elif shape.item_kind == "object" and isinstance(item, dict):
                    for req_key in shape.required_keys:
                        if req_key not in item:
                            errors.append(f"`{item_context}` 에 필수 필드 `{req_key}` 가 없다.")
                elif shape.item_kind == "object" and not isinstance(item, dict):
                    errors.append(f"`{item_context}` 는 object 이어야 한다.")
    elif shape.kind == "object":
        if not isinstance(value, dict):
            errors.append(f"`{context}` 는 object 이어야 한다.")
        else:
            for req_key in shape.required_keys:
                if req_key not in value:
                    errors.append(f"`{context}` 에 필수 필드 `{req_key}` 가 없다.")
            for prop_name, prop_shape in shape.properties.items():
                if prop_name in value:
                    errors.extend(
                        _validate_field_shape(value[prop_name], prop_shape, f"{context}.{prop_name}")
                    )
    return errors


def output_field_shapes_schema() -> dict[str, dict[str, dict[str, object]]]:
    """Return a JSON-serializable view of the nested output field shapes."""
    return {
        family: {
            field_name: output_field_shape_to_schema(shape)
            for field_name, shape in field_shapes.items()
        }
        for family, field_shapes in OUTPUT_FIELD_SHAPES.items()
    }


def output_error_field_shapes_schema() -> dict[str, dict[str, dict[str, object]]]:
    """Return a JSON-serializable view of error-only output field shapes."""
    return {
        family: {
            field_name: output_field_shape_to_schema(shape)
            for field_name, shape in field_shapes.items()
        }
        for family, field_shapes in ERROR_OUTPUT_FIELD_SHAPES.items()
    }
