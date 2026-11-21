"""허브 오류 형식 (hub_spec §4.3)."""

from __future__ import annotations

from typing import Any


class HubError(Exception):
    """도구 · HTTP 가 같은 모양으로 돌려주는 오류.

    ``status`` 는 HTTP 상태, ``code`` 는 안정된 ``error_code`` 다.
    """

    def __init__(self, status: int, code: str, message: str, detail: dict[str, Any] | None = None) -> None:
        super().__init__(f"{code}: {message}")
        self.status = status
        self.code = code
        self.message = message
        self.detail = detail or {}

    def payload(self) -> dict[str, Any]:
        return {"error_code": self.code, "message": self.message, "detail": self.detail}


def unauthorized(message: str = "토큰이 없거나 틀렸거나 거둔 토큰이다") -> HubError:
    return HubError(401, "unauthorized", message)


def forbidden(message: str) -> HubError:
    return HubError(403, "forbidden", message)


def not_found(message: str) -> HubError:
    return HubError(404, "not_found", message)


def invalid_field(field: str, message: str) -> HubError:
    return HubError(400, "invalid_field", f"{field}: {message}", {"field": field})


def unknown_field(fields: list[str]) -> HubError:
    return HubError(400, "unknown_field", f"모르는 필드: {', '.join(sorted(fields))}", {"fields": sorted(fields)})


def version_conflict(current_version: int, current: dict[str, Any]) -> HubError:
    return HubError(
        409, "version_conflict", f"version 이 다르다 — 지금 {current_version}",
        {"current_version": current_version, "current": current},
    )
