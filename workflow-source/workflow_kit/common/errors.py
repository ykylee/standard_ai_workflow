"""Shared error payload helpers for workflow kit scripts."""

from __future__ import annotations

from typing import Any


def build_error_result(
    *,
    tool_version: str,
    error: str,
    error_code: str,
    warnings: list[str],
    source_context: dict[str, Any],
    recovery_hint: str | None = None,
) -> dict[str, Any]:
    result = {
        "status": "error",
        "tool_version": tool_version,
        "error": error,
        "error_code": error_code,
        "warnings": warnings,
        "source_context": source_context,
    }
    if recovery_hint:
        result["recovery_hint"] = recovery_hint
    return result


_MESSAGE_CAP = 2000
_ERRORS_CAP = 20


def exception_context(exc: BaseException) -> dict[str, Any]:
    """catch-all 오류 결과의 ``source_context`` 에 실을 예외 원인.

    이름만 실으면 원인이 사라진다 — pydantic ``ValidationError`` 가 어느 필드의
    어떤 제약(예: 200자 상한)에 걸렸는지가 그렇게 숨었다. 메시지와, 검증
    오류라면 필드 위치 · 메시지 목록을 같이 싣는다.
    """
    context: dict[str, Any] = {
        "exception_type": type(exc).__name__,
        "exception_message": str(exc)[:_MESSAGE_CAP],
    }
    errors_fn = getattr(exc, "errors", None)
    if callable(errors_fn):
        try:
            raw = errors_fn()
        except Exception:  # noqa: BLE001 — errors() 가 없는 서명이면 메시지만 남긴다
            raw = None
        if isinstance(raw, list):
            items: list[dict[str, str]] = []
            for item in raw[:_ERRORS_CAP]:
                if not isinstance(item, dict):
                    continue
                loc = " -> ".join(str(part) for part in item.get("loc", ()))
                items.append({"loc": loc, "msg": str(item.get("msg", ""))})
            if items:
                context["exception_errors"] = items
    return context


def describe_exception(exc: BaseException) -> str:
    """사람이 읽는 ``error`` 문안 끝에 붙일 첫 원인 한 줄."""
    context = exception_context(exc)
    errors = context.get("exception_errors")
    if errors:
        first = errors[0]
        cause = f"{first['loc']}: {first['msg']}" if first["loc"] else first["msg"]
        more = f" 외 {len(errors) - 1}건" if len(errors) > 1 else ""
        model = getattr(exc, "title", None)
        name = f"{context['exception_type']}({model})" if isinstance(model, str) and model else context["exception_type"]
        return f"{name} — {cause}{more}"
    message = context["exception_message"].strip().splitlines()
    first_line = message[0] if message else ""
    return f"{context['exception_type']}: {first_line}" if first_line else context["exception_type"]
